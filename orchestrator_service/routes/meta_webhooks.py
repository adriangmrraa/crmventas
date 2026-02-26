import os
import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from fastapi import APIRouter, Request, HTTPException, Query, BackgroundTasks

from db import db
from core.socket_manager import sio

logger = logging.getLogger("meta_webhooks")
router = APIRouter()

# Meta Graph API Config
GRAPH_API_VERSION = os.getenv("META_GRAPH_API_VERSION", "v19.0")
VERIFY_TOKEN = os.getenv("META_WEBHOOK_VERIFY_TOKEN", "nexus_meta_secret_token")

@router.get("/meta")
@router.get("/meta/{tenant_id}")
async def verify_meta_webhook(
    tenant_id: Optional[int] = None,
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    """
    Verification endpoint for Meta Webhooks (Hub Challenge).
    """
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        logger.info("✅ Meta Webhook verified successfully")
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")

@router.post("/meta")
@router.post("/meta/{tenant_id}")
async def receive_meta_webhook(
    request: Request, 
    background_tasks: BackgroundTasks,
    tenant_id: Optional[int] = None
):
    """
    Receives LeadGen notifications from Meta OR custom flattened payloads (n8n).
    """
    try:
        body = await request.json()
    except Exception:
        return {"status": "error", "message": "invalid_json"}

    # Case A: Standard Meta Webhook (entry based)
    if isinstance(body, dict) and "entry" in body:
        entries = body.get("entry", [])
        for entry in entries:
            changes = entry.get("changes", [])
            for change in changes:
                if change.get("field") == "leadgen":
                    value = change.get("value", {})
                    leadgen_id = value.get("leadgen_id")
                    page_id = value.get("page_id")
                    ad_id = value.get("ad_id")
                    if leadgen_id:
                        logger.info(f"📥 New Meta LeadGen ID: {leadgen_id}")
                        background_tasks.add_task(process_standard_meta_lead, leadgen_id, page_id, ad_id)
        return {"status": "received", "type": "meta_standard"}

    # Case B: Custom Flattened Payload (n8n/LeadsBridge Style)
    # The user provided a list containing an object with a 'body'
    data_list = body if isinstance(body, list) else [body]
    for item in data_list:
        payload = item.get("body") if isinstance(item, dict) and "body" in item else item
        if isinstance(payload, dict) and "phone_number" in payload:
            logger.info(f"🚀 Processing flattened lead ingestion: {payload.get('phone_number')} for tenant {tenant_id or 1}")
            background_tasks.add_task(process_flattened_lead, payload, tenant_id)

    return {"status": "received", "type": "meta_custom"}

async def process_flattened_lead(data: Dict[str, Any], url_tenant_id: Optional[int] = None):
    """
    Directly ingests a lead from a pre-parsed payload (n8n style).
    No Graph API call needed.
    """
    try:
        # 1. Logic for Tenant Discovery (Default to first active or mapping by Page ID if present)
        tenant_id = url_tenant_id if url_tenant_id is not None else 1 # Fallback or dynamic logic here
        
        phone = str(data.get("phone_number", "")).strip()
        full_name = data.get("full_name") or "Lead Meta"
        email = data.get("email")
        
        if not phone:
            return

        # 2. Attribution Referral
        referral = {
            "ad_id": data.get("ad_id"),
            "ad_name": data.get("ad_id") if not str(data.get("ad_id", "")).isdigit() else None,
            "adset_id": data.get("adset_id"),
            "adset_name": data.get("adset_id") if not str(data.get("adset_id", "")).isdigit() else None,
            "campaign_id": data.get("campaign_id"),
            "campaign_name": data.get("campaign_id") if not str(data.get("campaign_id", "")).isdigit() else None,
            "headline": "Lead Form Ingestion",
            "body": f"Source: {data.get('executionMode', 'custom_webhook')}"
        }

        # 3. Ingest
        lead = await db.ensure_lead_exists(
            tenant_id=tenant_id,
            phone_number=phone,
            customer_name=full_name,
            source="meta_lead_form",
            referral=referral
        )
        
        if email:
            await db.execute("UPDATE leads SET email = $1 WHERE id = $2", email, lead["id"])

        # 4. Notify UI
        await sio.emit('META_LEAD_RECEIVED', {
            "tenant_id": tenant_id,
            "lead_id": str(lead["id"]),
            "phone_number": phone,
            "name": full_name,
            "source": "Meta Ingestion",
            "campaign": referral["campaign_name"] or referral["campaign_id"],
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Error in flattened ingestion: {e}")

async def process_standard_meta_lead(leadgen_id: str, page_id: str, ad_id: str):
    """
    Standard flow: Fetch details from Graph API using page token.
    """
    import httpx
    try:
        token_row = await db.fetchrow(
            "SELECT tenant_id, access_token FROM meta_tokens WHERE page_id = $1 LIMIT 1",
            page_id
        )
        if not token_row:
            logger.error(f"❌ No token found for Page ID {page_id}")
            return

        tenant_id = token_row["tenant_id"]
        access_token = token_row["access_token"]

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://graph.facebook.com/{GRAPH_API_VERSION}/{leadgen_id}",
                params={"access_token": access_token}
            )
            resp.raise_for_status()
            lead_data = resp.json()

        field_data = lead_data.get("field_data", [])
        extracted = {f.get("name"): f.get("values", [None])[0] for f in field_data}
        
        full_name = extracted.get("full_name") or f"{extracted.get('first_name', '')} {extracted.get('last_name', '')}".strip()
        phone = extracted.get("phone_number")
        email = extracted.get("email")

        if not phone: return

        referral = {
            "ad_id": ad_id,
            "headline": "Meta Lead Form",
            "body": f"LeadGen ID: {leadgen_id}"
        }
        
        lead = await db.ensure_lead_exists(
            tenant_id=tenant_id,
            phone_number=phone,
            customer_name=full_name,
            source="meta_lead_form",
            referral=referral
        )
        
        if email:
            await db.execute("UPDATE leads SET email = $1 WHERE id = $2", email, lead["id"])

        await sio.emit('META_LEAD_RECEIVED', {
            "tenant_id": tenant_id,
            "phone_number": phone,
            "name": full_name,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"❌ Error processing standard lead {leadgen_id}: {e}")
