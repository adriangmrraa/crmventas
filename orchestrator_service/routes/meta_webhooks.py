import os
import logging
import hmac
import hashlib
import json
import httpx
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, Request, HTTPException, Query, BackgroundTasks

from db import db
from core.socket_manager import sio

logger = logging.getLogger("meta_webhooks")
router = APIRouter()

# Meta App Secret for signature verification (if needed)
META_APP_SECRET = os.getenv("META_APP_SECRET", "")
GRAPH_API_VERSION = "v19.0"

@router.get("/meta")
async def verify_meta_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    """
    Verification endpoint for Meta Webhooks.
    """
    VERIFY_TOKEN = os.getenv("META_WEBHOOK_VERIFY_TOKEN", "nexus_meta_secret_token")
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        logger.info("✅ Meta Webhook verified successfully")
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")

@router.post("/meta")
async def receive_meta_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receives LeadGen notifications from Meta.
    """
    try:
        payload = await request.json()
    except:
        return {"status": "error", "message": "invalid_json"}

    # Meta LeadGen Payloads are usually lists in 'entry'
    entries = payload.get("entry", [])
    for entry in entries:
        changes = entry.get("changes", [])
        for change in changes:
            if change.get("field") == "leadgen":
                value = change.get("value", {})
                leadgen_id = value.get("leadgen_id")
                page_id = value.get("page_id")
                form_id = value.get("form_id")
                ad_id = value.get("ad_id")
                
                if leadgen_id:
                    logger.info(f"📥 New Meta Lead detected: {leadgen_id} (Form: {form_id}, Page: {page_id})")
                    background_tasks.add_task(process_meta_lead, leadgen_id, page_id, ad_id)

    return {"status": "received"}

async def process_meta_lead(leadgen_id: str, page_id: str, ad_id: str):
    """
    Fetches lead details from Meta Graph API and upserts into CRM.
    """
    try:
        # 1. Resolve Tenant from page_id
        # meta_tokens table stores tokens per page/tenant
        token_row = await db.fetchrow(
            "SELECT tenant_id, access_token FROM meta_tokens WHERE page_id = $1 LIMIT 1",
            page_id
        )
        if not token_row:
            logger.error(f"❌ No token found for Page ID {page_id}. Cannot process lead.")
            return

        tenant_id = token_row["tenant_id"]
        access_token = token_row["access_token"]

        # 2. Fetch Lead Details from Graph API
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://graph.facebook.com/{GRAPH_API_VERSION}/{leadgen_id}",
                params={"access_token": access_token}
            )
            resp.raise_for_status()
            lead_data = resp.json()

        # 3. Parse Lead Data (Name, Phone, Email)
        field_data = lead_data.get("field_data", [])
        extracted = {}
        for field in field_data:
            name = field.get("name")
            values = field.get("values", [])
            if values:
                extracted[name] = values[0]
        
        full_name = extracted.get("full_name") or f"{extracted.get('first_name', '')} {extracted.get('last_name', '')}".strip()
        phone = extracted.get("phone_number")
        email = extracted.get("email")

        if not phone:
            logger.warning(f"⚠️ Lead {leadgen_id} missing phone number. Skipping CRM ingestion.")
            return

        # 4. Upsert Lead in DB
        referral_mock = {
            "ad_id": ad_id,
            "headline": "Meta Lead Form",
            "body": f"Form ID: {lead_data.get('form_id')}"
        }
        
        lead = await db.ensure_lead_exists(
            tenant_id=tenant_id,
            phone_number=phone,
            customer_name=full_name,
            source="meta_lead_form",
            referral=referral_mock
        )
        
        if email:
            await db.execute("UPDATE leads SET email = $1 WHERE id = $2", email, lead["id"])

        # 5. Real-time Notification for CEO (Spec Mission 4)
        try:
            await sio.emit('META_LEAD_RECEIVED', {
                "tenant_id": tenant_id,
                "lead_id": str(lead["id"]),
                "phone_number": phone,
                "name": full_name,
                "email": email,
                "ad_id": ad_id,
                "source": "Meta Lead Form",
                "timestamp": datetime.now().isoformat()
            })
            logger.info(f"📡 Socket notification sent for Lead Form: {phone}")
        except Exception as sio_err:
            logger.error(f"⚠️ Notification error: {sio_err}")

    except Exception as e:
        logger.error(f"❌ Error processing Meta lead {leadgen_id}: {e}", exc_info=True)
