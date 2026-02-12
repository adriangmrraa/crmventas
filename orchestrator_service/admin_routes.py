import os
import uuid
import json
import logging
import httpx
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks

from db import db
from core.security import verify_admin_token, get_resolved_tenant_id, get_allowed_tenant_ids, ADMIN_TOKEN
from core.utils import normalize_phone, ARG_TZ

from core.services.chat_service import ChatService

logger = logging.getLogger(__name__)

# Configuración
INTERNAL_API_TOKEN = os.getenv("INTERNAL_API_TOKEN", "internal-secret-token")
WHATSAPP_SERVICE_URL = os.getenv("WHATSAPP_SERVICE_URL", "http://whatsapp:8002")

router = APIRouter(prefix="/admin/core", tags=["Core Admin"])

# ... (MODELS and HELPERS remain unchanged) ...

# --- MODELS ---
class StatusUpdate(BaseModel):
    status: str

class HumanInterventionToggle(BaseModel):
    phone: str
    tenant_id: int
    activate: bool
    duration: Optional[int] = 86400000

class ChatSendMessage(BaseModel):
    phone: str
    tenant_id: int
    message: str

class ClinicSettingsUpdate(BaseModel):
    ui_language: Optional[str] = None

# --- HELPERS ---
async def emit_appointment_event(event_type: str, data: Dict[str, Any], request: Request):
    if hasattr(request.app.state, 'emit_appointment_event'):
        await request.app.state.emit_appointment_event(event_type, data)

async def send_to_whatsapp_task(phone: str, message: str, business_number: str):
    normalized = normalize_phone(phone)
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            await client.post(
                f"{WHATSAPP_SERVICE_URL}/send",
                json={"to": normalized, "message": message},
                headers={"X-Internal-Token": INTERNAL_API_TOKEN, "X-Correlation-Id": str(uuid.uuid4())},
                params={"from_number": business_number}
            )
    except Exception as e:
        logger.error(f"WhatsApp send failed: {e}")

# --- RUTAS DE USUARIOS ---
@router.get("/users/pending", tags=["Usuarios"])
async def get_pending_users(user_data = Depends(verify_admin_token)):
    if user_data.role not in ['ceo', 'secretary']: raise HTTPException(status_code=403, detail="Forbidden")
    users = await db.fetch("SELECT id, email, role, status, created_at, first_name, last_name FROM users WHERE status = 'pending' ORDER BY created_at DESC")
    return [dict(u) for u in users]

@router.get("/users", tags=["Usuarios"])
async def get_all_users(user_data = Depends(verify_admin_token)):
    if user_data.role not in ['ceo', 'secretary']: raise HTTPException(status_code=403, detail="Forbidden")
    users = await db.fetch("SELECT id, email, role, status, created_at, updated_at, first_name, last_name FROM users ORDER BY status ASC, created_at DESC")
    return [dict(u) for u in users]

@router.post("/users/{user_id}/status", tags=["Usuarios"])
async def update_user_status(user_id: str, payload: StatusUpdate, user_data = Depends(verify_admin_token)):
    if user_data.role != 'ceo': raise HTTPException(status_code=403, detail="CEO only")
    await db.execute("UPDATE users SET status = $1, updated_at = NOW() WHERE id = $2", payload.status, user_id)
    return {"status": "updated"}

# --- RUTAS DE CHAT ---
@router.get("/chat/tenants", dependencies=[Depends(verify_admin_token)], tags=["Chat"])
async def get_chat_tenants(allowed_ids: List[int] = Depends(get_allowed_tenant_ids)):
    if not allowed_ids: return []
    rows = await db.pool.fetch("SELECT id, clinic_name FROM tenants WHERE id = ANY($1::int[]) ORDER BY id ASC", allowed_ids)
    return [{"id": r["id"], "clinic_name": r["clinic_name"]} for r in rows]

@router.get("/chat/sessions", dependencies=[Depends(verify_admin_token)], tags=["Chat"])
async def get_chat_sessions(tenant_id: int, allowed_ids: List[int] = Depends(get_allowed_tenant_ids)):
    if tenant_id not in allowed_ids: raise HTTPException(status_code=403)
    # Abstraction: Use ChatService to get sessions (resolves patients/leads internally)
    return await ChatService.get_chat_sessions(tenant_id)

@router.get("/chat/messages/{phone}", dependencies=[Depends(verify_admin_token)], tags=["Chat"])
async def get_chat_messages(phone: str, tenant_id: int, limit: int = 50, offset: int = 0, allowed_ids: List[int] = Depends(get_allowed_tenant_ids)):
    if tenant_id not in allowed_ids: raise HTTPException(status_code=403)
    rows = await db.pool.fetch("SELECT * FROM chat_messages WHERE from_number = $1 AND tenant_id = $2 ORDER BY created_at DESC LIMIT $3 OFFSET $4", phone, tenant_id, limit, offset)
    return sorted([dict(r) | {"created_at": str(r["created_at"])} for r in rows], key=lambda x: x['created_at'])

@router.post("/chat/send", dependencies=[Depends(verify_admin_token)], tags=["Chat"])
async def send_chat_message(payload: ChatSendMessage, request: Request, background_tasks: BackgroundTasks, allowed_ids: List[int] = Depends(get_allowed_tenant_ids)):
    if payload.tenant_id not in allowed_ids: raise HTTPException(status_code=403)
    correlation_id = str(uuid.uuid4())
    await db.append_chat_message(from_number=payload.phone, role="assistant", content=payload.message, correlation_id=correlation_id, tenant_id=payload.tenant_id)
    business_number = os.getenv("YCLOUD_Phone_Number_ID") or "default"
    background_tasks.add_task(send_to_whatsapp_task, payload.phone, payload.message, business_number)
    return {"status": "sent", "correlation_id": correlation_id}

# --- RUTAS DE CONFIGURACIÓN / TENANTS ---
@router.get("/tenants", tags=["Sedes"])
async def get_tenants(user_data=Depends(verify_admin_token)):
    if user_data.role != 'ceo': raise HTTPException(status_code=403)
    rows = await db.pool.fetch("SELECT id, clinic_name, bot_phone_number, config FROM tenants ORDER BY id ASC")
    return [dict(r) for r in rows]

@router.get("/settings/clinic", dependencies=[Depends(verify_admin_token)], tags=["Configuración"])
async def get_clinic_settings(resolved_tenant_id: int = Depends(get_resolved_tenant_id)):
    row = await db.pool.fetchrow("SELECT clinic_name, config FROM tenants WHERE id = $1", resolved_tenant_id)
    if not row: return {}
    return {"name": row["clinic_name"], "ui_language": row["config"].get("ui_language", "en")}

@router.patch("/settings/clinic", dependencies=[Depends(verify_admin_token)], tags=["Configuración"])
async def update_clinic_settings(payload: ClinicSettingsUpdate, resolved_tenant_id: int = Depends(get_resolved_tenant_id)):
    if payload.ui_language:
        await db.pool.execute("UPDATE tenants SET config = jsonb_set(COALESCE(config, '{}'), '{ui_language}', to_jsonb($1::text)) WHERE id = $2", payload.ui_language, resolved_tenant_id)
    return {"status": "ok"}

@router.get("/internal/credentials/{name}", tags=["Internal"])
async def get_internal_credential(name: str, x_internal_token: str = Header(None)):
    if x_internal_token != INTERNAL_API_TOKEN: raise HTTPException(status_code=401)
    val = os.getenv(name)
    if not val: raise HTTPException(status_code=404)
    return {"name": name, "value": val}

@router.get("/config/deployment", dependencies=[Depends(verify_admin_token)], tags=["Configuración"])
async def get_deployment_config(request: Request):
    host = request.headers.get("host", "localhost:8000")
    base_url = f"https://{host}"
    return {"orchestrator_url": base_url, "environment": os.getenv("ENVIRONMENT", "development")}
