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


# ---------------------------------------------------------------------------
# GET  /meta  |  /meta/{tenant_id}  -- Hub Challenge (Meta Verification)
# ---------------------------------------------------------------------------
@router.get("/meta")
@router.get("/meta/{tenant_id}")
@router.get("/meta/leadgen")
async def verify_meta_webhook(
    tenant_id: Optional[int] = None,
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    """
    Verification endpoint for Meta Webhooks (Hub Challenge).
    Supports:
      /webhooks/meta
      /webhooks/meta/{tenant_id}
      /webhooks/meta/leadgen
    """
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        logger.info("Meta Webhook verified successfully")
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


# ---------------------------------------------------------------------------
# POST /meta  |  /meta/{tenant_id}  -- Receive LeadGen Webhook
# ---------------------------------------------------------------------------
@router.post("/meta")
@router.post("/meta/{tenant_id}")
@router.post("/meta/leadgen")
async def receive_meta_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    tenant_id: Optional[int] = None,
):
    """
    Receives LeadGen notifications from Meta OR custom flattened payloads (n8n).
    Always returns 200 quickly (Meta requires fast response).
    """
    try:
        body = await request.json()
    except Exception:
        return {"status": "error", "message": "invalid_json"}

    # Case A: Standard Meta Webhook (entry based)
    if isinstance(body, dict) and "entry" in body:
        entries = body.get("entry", [])
        for entry in entries:
            page_id_entry = entry.get("id")  # page-level id from entry
            changes = entry.get("changes", [])
            for change in changes:
                if change.get("field") == "leadgen":
                    value = change.get("value", {})
                    leadgen_id = value.get("leadgen_id")
                    page_id = value.get("page_id") or page_id_entry
                    ad_id = value.get("ad_id")
                    form_id = value.get("form_id")
                    adgroup_id = value.get("adgroup_id")
                    if leadgen_id:
                        logger.info(f"New Meta LeadGen ID: {leadgen_id} | page={page_id} ad={ad_id} form={form_id}")
                        background_tasks.add_task(
                            process_standard_meta_lead,
                            leadgen_id=leadgen_id,
                            page_id=page_id,
                            ad_id=ad_id,
                            form_id=form_id,
                            adgroup_id=adgroup_id,
                            url_tenant_id=tenant_id,
                        )
        return {"status": "received", "type": "meta_standard"}

    # Case B: Custom Flattened Payload (n8n/LeadsBridge Style)
    data_list = body if isinstance(body, list) else [body]
    for item in data_list:
        payload = item.get("body") if isinstance(item, dict) and "body" in item else item
        if isinstance(payload, dict) and "phone_number" in payload:
            logger.info(f"Processing flattened lead ingestion: {payload.get('phone_number')} for tenant {tenant_id or 1}")
            background_tasks.add_task(process_flattened_lead, payload, tenant_id)

    return {"status": "received", "type": "meta_custom"}


# ---------------------------------------------------------------------------
# Helper: add "meta_ads" tag to a lead
# ---------------------------------------------------------------------------
async def _add_meta_ads_tag(conn, tenant_id: int, lead_id, lead_row=None):
    """Merge 'meta_ads' into the lead's tags array (idempotent)."""
    try:
        if lead_row is None:
            lead_row = await conn.fetchrow(
                "SELECT tags FROM leads WHERE id = $1", lead_id
            )
        existing_tags = lead_row["tags"] if lead_row and lead_row.get("tags") else []
        if isinstance(existing_tags, str):
            existing_tags = json.loads(existing_tags)
        if "meta_ads" not in existing_tags:
            merged = list(dict.fromkeys(existing_tags + ["meta_ads"]))
            await conn.execute(
                "UPDATE leads SET tags = $1, updated_at = NOW() WHERE id = $2",
                json.dumps(merged), lead_id,
            )
            # Log the tag addition
            try:
                await conn.execute(
                    "INSERT INTO lead_tag_log (tenant_id, lead_id, tags_added, reason, source) "
                    "VALUES ($1, $2, $3, $4, 'system_auto')",
                    tenant_id, lead_id, ["meta_ads"],
                    "Lead ingested from Meta Ads webhook",
                )
            except Exception:
                pass  # tag log table may not exist yet
    except Exception as e:
        logger.warning(f"Could not add meta_ads tag to lead {lead_id}: {e}")


# ---------------------------------------------------------------------------
# Helper: update meta-specific fields on the lead row
# ---------------------------------------------------------------------------
async def _update_meta_fields(conn, lead_id, *, meta_lead_id: str = None,
                               meta_campaign_id: str = None, meta_ad_id: str = None,
                               meta_ad_headline: str = None, meta_ad_body: str = None,
                               email: str = None):
    """Set Meta-specific columns on the lead row."""
    updates: Dict[str, Any] = {}
    if meta_lead_id:
        updates["meta_lead_id"] = meta_lead_id
    if meta_campaign_id:
        updates["meta_campaign_id"] = meta_campaign_id
    if meta_ad_id:
        updates["meta_ad_id"] = meta_ad_id
    if meta_ad_headline:
        updates["meta_ad_headline"] = meta_ad_headline
    if meta_ad_body:
        updates["meta_ad_body"] = meta_ad_body
    if email:
        updates["email"] = email
    if not updates:
        return
    updates["updated_at"] = datetime.utcnow()
    set_clauses = [f"{k} = ${i+1}" for i, k in enumerate(updates.keys())]
    query = f"UPDATE leads SET {', '.join(set_clauses)} WHERE id = ${len(updates)+1}"
    await conn.execute(query, *updates.values(), lead_id)


# ---------------------------------------------------------------------------
# Standard Meta LeadGen flow: fetch from Graph API
# ---------------------------------------------------------------------------
async def process_standard_meta_lead(
    leadgen_id: str,
    page_id: str,
    ad_id: str,
    form_id: str = None,
    adgroup_id: str = None,
    url_tenant_id: Optional[int] = None,
):
    """
    Standard flow: Fetch lead details from Graph API using page token,
    map fields, create/update lead, set meta fields, add tag, emit socket.
    """
    import httpx
    try:
        # 1. Resolve access token -- prefer URL tenant, then page-id lookup
        token_row = None
        if url_tenant_id:
            token_row = await db.fetchrow(
                "SELECT tenant_id, access_token FROM meta_tokens WHERE tenant_id = $1 LIMIT 1",
                url_tenant_id,
            )
        if not token_row and page_id:
            token_row = await db.fetchrow(
                "SELECT tenant_id, access_token FROM meta_tokens WHERE page_id = $1 LIMIT 1",
                page_id,
            )
        if not token_row:
            logger.error(f"No token found for Page ID {page_id} / tenant {url_tenant_id}")
            return

        tenant_id = token_row["tenant_id"]
        access_token = token_row["access_token"]

        # 2. Fetch lead details from Graph API: GET /{leadgen_id}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"https://graph.facebook.com/{GRAPH_API_VERSION}/{leadgen_id}",
                params={"access_token": access_token},
            )
            resp.raise_for_status()
            lead_data = resp.json()

            # 3. Optionally fetch ad-level info for campaign_id
            campaign_id = None
            ad_name = None
            if ad_id:
                try:
                    ad_resp = await client.get(
                        f"https://graph.facebook.com/{GRAPH_API_VERSION}/{ad_id}",
                        params={
                            "fields": "name,campaign_id,campaign{name}",
                            "access_token": access_token,
                        },
                    )
                    if ad_resp.status_code == 200:
                        ad_info = ad_resp.json()
                        campaign_id = ad_info.get("campaign_id")
                        ad_name = ad_info.get("name")
                except Exception as ad_err:
                    logger.warning(f"Could not fetch ad info for {ad_id}: {ad_err}")

        # 4. Parse field_data from the leadgen response
        field_data = lead_data.get("field_data", [])
        extracted = {f.get("name"): f.get("values", [None])[0] for f in field_data}

        full_name = (
            extracted.get("full_name")
            or f"{extracted.get('first_name', '')} {extracted.get('last_name', '')}".strip()
        )
        phone = extracted.get("phone_number")
        email = extracted.get("email")

        if not phone:
            logger.warning(f"LeadGen {leadgen_id}: no phone_number in field_data, skipping")
            return

        # 5. Build referral for ensure_lead_exists attribution
        referral = {
            "ad_id": ad_id,
            "campaign_id": campaign_id,
            "headline": "Meta Lead Form",
            "body": f"LeadGen ID: {leadgen_id}",
        }

        lead = await db.ensure_lead_exists(
            tenant_id=tenant_id,
            phone_number=phone,
            customer_name=full_name or "Lead Meta",
            source="meta_ads",
            referral=referral,
        )

        lead_id = lead["id"]

        # 6. Update meta-specific fields (meta_lead_id, campaign, ad, email)
        async with db.pool.acquire() as conn:
            await _update_meta_fields(
                conn,
                lead_id,
                meta_lead_id=leadgen_id,
                meta_campaign_id=campaign_id,
                meta_ad_id=ad_id,
                meta_ad_headline=ad_name,
                email=email,
            )
            # 7. Add "meta_ads" tag
            await _add_meta_ads_tag(conn, tenant_id, lead_id)

        # 8. Emit Socket.IO event
        await sio.emit("META_LEAD_RECEIVED", {
            "tenant_id": tenant_id,
            "lead_id": str(lead_id),
            "phone_number": phone,
            "name": full_name,
            "source": "meta_ads",
            "campaign_id": campaign_id,
            "ad_id": ad_id,
            "meta_lead_id": leadgen_id,
            "timestamp": datetime.utcnow().isoformat(),
        })
        logger.info(f"Meta lead processed: {phone} (leadgen={leadgen_id}, tenant={tenant_id})")

    except Exception as e:
        logger.error(f"Error processing standard lead {leadgen_id}: {e}", exc_info=True)


# ---------------------------------------------------------------------------
# Flattened payload flow (n8n / LeadsBridge / custom)
# ---------------------------------------------------------------------------
async def process_flattened_lead(data: Dict[str, Any], url_tenant_id: Optional[int] = None):
    """
    Directly ingests a lead from a pre-parsed payload (n8n style).
    No Graph API call needed -- all fields come in the payload.
    """
    try:
        tenant_id = url_tenant_id if url_tenant_id is not None else 1

        phone = str(data.get("phone_number", "")).strip()
        full_name = data.get("full_name") or "Lead Meta"
        email = data.get("email")
        meta_lead_id = data.get("leadgen_id") or data.get("meta_lead_id") or data.get("id")

        if not phone:
            return

        # Attribution referral
        campaign_id = data.get("campaign_id")
        ad_id = data.get("ad_id")
        referral = {
            "ad_id": ad_id,
            "ad_name": data.get("ad_name") or (ad_id if ad_id and not str(ad_id).isdigit() else None),
            "adset_id": data.get("adset_id"),
            "adset_name": data.get("adset_name") or (data.get("adset_id") if data.get("adset_id") and not str(data.get("adset_id")).isdigit() else None),
            "campaign_id": campaign_id,
            "campaign_name": data.get("campaign_name") or (campaign_id if campaign_id and not str(campaign_id).isdigit() else None),
            "headline": "Lead Form Ingestion",
            "body": f"Source: {data.get('executionMode', 'custom_webhook')}",
        }

        lead = await db.ensure_lead_exists(
            tenant_id=tenant_id,
            phone_number=phone,
            customer_name=full_name,
            source="meta_ads",
            referral=referral,
        )

        lead_id = lead["id"]

        # Update meta fields + email + tag
        async with db.pool.acquire() as conn:
            await _update_meta_fields(
                conn,
                lead_id,
                meta_lead_id=str(meta_lead_id) if meta_lead_id else None,
                meta_campaign_id=campaign_id,
                meta_ad_id=ad_id,
                email=email,
            )
            await _add_meta_ads_tag(conn, tenant_id, lead_id)

        # Notify UI
        await sio.emit("META_LEAD_RECEIVED", {
            "tenant_id": tenant_id,
            "lead_id": str(lead_id),
            "phone_number": phone,
            "name": full_name,
            "source": "meta_ads",
            "campaign_id": referral.get("campaign_id"),
            "campaign_name": referral.get("campaign_name"),
            "ad_id": ad_id,
            "meta_lead_id": str(meta_lead_id) if meta_lead_id else None,
            "timestamp": datetime.utcnow().isoformat(),
        })
        logger.info(f"Flattened meta lead processed: {phone} (tenant={tenant_id})")

    except Exception as e:
        logger.error(f"Error in flattened ingestion: {e}", exc_info=True)
