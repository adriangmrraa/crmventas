"""
Free-text Outbound Messaging Routes
Allows CRM dashboard users to send free-text messages to leads via WhatsApp.

Endpoints:
  POST /admin/core/chat/send  — Send a free-text message to a lead's phone number
"""

import os
import uuid
import logging
from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from db import db
from core.security import verify_admin_token, get_resolved_tenant_id, audit_access
from core.rate_limiter import limiter
from core.utils import normalize_phone
from core.socket_manager import sio
from services.message_delivery import unified_message_delivery

logger = logging.getLogger("chat_routes")
router = APIRouter()


# ─── Pydantic Schemas ────────────────────────────────────────────────────────────

class SendMessageRequest(BaseModel):
    phone: str = Field(..., description="Recipient phone number (lead's number)")
    message: str = Field(..., description="Free-text message content")
    channel: str = Field("whatsapp", description="Channel: whatsapp | instagram | facebook")
    tenant_id: Optional[int] = Field(None, description="Optional tenant override (CEO multi-tenant)")


# ─── Send Free-Text Message ─────────────────────────────────────────────────────

@router.post("/admin/core/chat/send")
@audit_access("send_free_text_message")
@limiter.limit("30/minute")
async def send_free_text_message(
    payload: SendMessageRequest,
    request: Request,
    user_data: Dict = Depends(verify_admin_token),
    jwt_tenant_id: int = Depends(get_resolved_tenant_id),
):
    """
    Send a free-text message from the CRM dashboard to a lead's WhatsApp.
    Steps:
      1. Resolve tenant_id (from payload or JWT)
      2. Normalize phone number
      3. Get bot phone number for this tenant
      4. Store message in chat_messages (role=assistant)
      5. Send via whatsapp_service relay or YCloud direct
      6. Emit Socket.IO NEW_MESSAGE event
      7. Return success
    """
    # 1. Resolve tenant
    tenant_id = payload.tenant_id or jwt_tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Could not resolve tenant_id")

    # 2. Normalize phone
    phone = normalize_phone(payload.phone)
    if not phone:
        raise HTTPException(status_code=400, detail="Invalid phone number")

    message_text = payload.message.strip()
    if not message_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # 3. Get bot phone (from_number) for the tenant
    bot_phone = None
    try:
        from core.credentials import get_tenant_credential, YCLOUD_WHATSAPP_NUMBER
        bot_phone = await get_tenant_credential(tenant_id, YCLOUD_WHATSAPP_NUMBER)
    except Exception:
        pass

    if not bot_phone:
        # Fallback: try tenants table
        tenant_row = await db.fetchrow(
            "SELECT bot_phone_number FROM tenants WHERE id = $1", tenant_id
        )
        if tenant_row:
            bot_phone = tenant_row.get("bot_phone_number") or ""

    correlation_id = f"manual_send_{uuid.uuid4().hex[:8]}"

    # 4. Store message in chat_messages (role=assistant, from bot to lead)
    try:
        await db.append_chat_message(
            from_number=phone,
            role="assistant",
            content=message_text,
            correlation_id=correlation_id,
            tenant_id=tenant_id,
        )
    except Exception as e:
        logger.error(f"Failed to store chat message: {e}")
        raise HTTPException(status_code=500, detail="Failed to store message")

    # 5. Send via delivery service
    delivery_result = None
    try:
        delivery_result = await unified_message_delivery(
            tenant_id=tenant_id,
            phone=phone,
            text=message_text,
            channel=payload.channel,
        )
    except Exception as e:
        logger.error(f"Message delivery failed: {e}", exc_info=True)
        # Message is stored but delivery failed - still return partial success
        # so the user knows the message was saved but not delivered
        try:
            await sio.emit("NEW_MESSAGE", {
                "phone_number": phone,
                "message": message_text,
                "role": "assistant",
                "tenant_id": tenant_id,
            })
        except Exception:
            pass

        return {
            "success": False,
            "error": f"Message stored but delivery failed: {str(e)}",
            "data": {
                "phone": phone,
                "message": message_text,
                "stored": True,
                "delivered": False,
                "correlation_id": correlation_id,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    # 6. Emit Socket.IO event for real-time update
    try:
        await sio.emit("NEW_MESSAGE", {
            "phone_number": phone,
            "message": message_text,
            "role": "assistant",
            "tenant_id": tenant_id,
        })
    except Exception as e:
        logger.warning(f"Socket.IO emit failed (non-critical): {e}")

    # DEV-39: Registrar evento de actividad (chat_message_sent por humano)
    try:
        from services.activity_service import record_event
        from uuid import UUID as _UUID
        sender_id = user_data.get("user_id") or user_data.get("id") if isinstance(user_data, dict) else getattr(user_data, "user_id", None)
        if sender_id:
            lead_row = await db.fetchrow(
                "SELECT id, first_name, last_name, phone_number FROM leads WHERE tenant_id = $1 AND phone_number = $2 LIMIT 1",
                tenant_id, phone
            )
            if lead_row:
                lead_name = f"{lead_row['first_name'] or ''} {lead_row['last_name'] or ''}".strip() or lead_row["phone_number"]
                await record_event(
                    tenant_id=tenant_id,
                    actor_id=_UUID(str(sender_id)),
                    event_type="chat_message_sent",
                    entity_type="lead",
                    entity_id=str(lead_row["id"]),
                    metadata={"lead_name": lead_name, "channel": payload.channel},
                )
    except Exception:
        pass  # Non-critical

    # 7. Return success
    return {
        "success": True,
        "data": {
            "phone": phone,
            "message": message_text,
            "stored": True,
            "delivered": True,
            "correlation_id": correlation_id,
            "delivery": delivery_result,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }
