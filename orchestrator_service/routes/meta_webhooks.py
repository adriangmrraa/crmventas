import os
import hmac
import hashlib
import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from fastapi import APIRouter, Request, HTTPException, Query, BackgroundTasks, Header

import httpx

from db import db
from core.socket_manager import sio

logger = logging.getLogger("meta_webhooks")
router = APIRouter()

# Meta Graph API Config
GRAPH_API_VERSION = os.getenv("META_GRAPH_API_VERSION", "v19.0")
VERIFY_TOKEN = os.getenv("META_WEBHOOK_VERIFY_TOKEN", "nexus_meta_secret_token")
META_APP_SECRET = os.getenv("META_APP_SECRET", "")
INTERNAL_API_TOKEN = os.getenv("INTERNAL_API_TOKEN", "internal-secret-token")
ORCHESTRATOR_BASE_URL = os.getenv("ORCHESTRATOR_BASE_URL", "http://localhost:8000")


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
# Signature Verification (X-Hub-Signature-256)
# ---------------------------------------------------------------------------
async def _verify_signature(request: Request) -> bytes:
    """
    Verify Meta webhook payload signature using HMAC-SHA256.
    Returns the raw body bytes on success, raises HTTPException on failure.
    If META_APP_SECRET is not configured, verification is skipped (dev mode).
    """
    body_bytes = await request.body()
    if not META_APP_SECRET:
        return body_bytes  # Skip verification in dev mode

    signature_header = request.headers.get("x-hub-signature-256", "")
    if not signature_header:
        logger.warning("Meta webhook: Missing X-Hub-Signature-256 header")
        raise HTTPException(status_code=401, detail="Missing signature")

    expected = "sha256=" + hmac.new(
        META_APP_SECRET.encode("utf-8"),
        body_bytes,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature_header):
        logger.warning("Meta webhook: Invalid signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    return body_bytes


# ---------------------------------------------------------------------------
# Tenant Resolution Helpers
# ---------------------------------------------------------------------------
async def _resolve_tenant_by_channel_binding(
    provider: str, channel_id: str
) -> Optional[int]:
    """Resolve tenant_id via channel_bindings table."""
    try:
        row = await db.fetchrow(
            "SELECT tenant_id FROM channel_bindings "
            "WHERE provider = $1 AND channel_id = $2 AND is_active = true LIMIT 1",
            provider, str(channel_id),
        )
        if row:
            return int(row["tenant_id"])
    except Exception as e:
        logger.warning(f"channel_bindings lookup failed: {e}")
    return None


async def _resolve_tenant_by_page_id(page_id: str) -> Optional[int]:
    """Resolve tenant via meta_tokens.page_id or business_assets."""
    try:
        # Try meta_tokens first (backward-compatible)
        row = await db.fetchrow(
            "SELECT tenant_id FROM meta_tokens WHERE page_id = $1 LIMIT 1",
            str(page_id),
        )
        if row:
            return int(row["tenant_id"])

        # Try business_assets
        row = await db.fetchrow(
            "SELECT tenant_id FROM business_assets "
            "WHERE external_id = $1 AND is_active = true LIMIT 1",
            str(page_id),
        )
        if row:
            return int(row["tenant_id"])
    except Exception as e:
        logger.warning(f"page_id tenant resolution failed: {e}")
    return None


async def _resolve_tenant_by_phone_number_id(phone_number_id: str) -> Optional[int]:
    """Resolve tenant via channel_bindings for WhatsApp phone_number_id."""
    return await _resolve_tenant_by_channel_binding("meta_whatsapp", phone_number_id)


# ---------------------------------------------------------------------------
# Normalized Message Format + Forward to /chat
# ---------------------------------------------------------------------------
async def _forward_to_chat(normalized: Dict[str, Any], tenant_id: int):
    """
    Forward a normalized messaging payload to POST /chat.
    Uses the same internal token mechanism as whatsapp_service.
    """
    chat_payload = {
        "provider": normalized.get("provider", "meta"),
        "event_id": normalized.get("event_id", ""),
        "provider_message_id": normalized.get("event_id", ""),
        "from_number": normalized["from_number"],
        "text": normalized.get("text", ""),
        "customer_name": normalized.get("customer_name"),
        "to_number": normalized.get("to_number"),
        "tenant_id": tenant_id,
        "channel_source": normalized.get("channel_source"),
        "media": normalized.get("media"),
        "referral": normalized.get("referral"),
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{ORCHESTRATOR_BASE_URL}/chat",
                json=chat_payload,
                headers={"X-Internal-Token": INTERNAL_API_TOKEN},
            )
            if resp.status_code != 200:
                logger.error(
                    f"Forward to /chat failed ({resp.status_code}): {resp.text[:300]}"
                )
            else:
                logger.info(
                    f"Forwarded {normalized['channel_source']} message from "
                    f"{normalized['from_number']} to /chat (tenant={tenant_id})"
                )
            return resp.json()
    except Exception as e:
        logger.error(f"Error forwarding to /chat: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}


# ---------------------------------------------------------------------------
# WhatsApp Cloud API Message Extraction
# ---------------------------------------------------------------------------
def _extract_whatsapp_messages(body: dict) -> List[Dict[str, Any]]:
    """
    Extract normalized messages from a WhatsApp Cloud API webhook payload.
    Handles text, image, video, audio, document, location, sticker, and reaction types.
    """
    results = []
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            metadata = value.get("metadata", {})
            phone_number_id = metadata.get("phone_number_id", "")
            display_phone = metadata.get("display_phone_number", "")

            # Contact info
            contacts = value.get("contacts", [])
            contact_name = ""
            if contacts:
                profile = contacts[0].get("profile", {})
                contact_name = profile.get("name", "")

            for msg in value.get("messages", []):
                msg_type = msg.get("type", "text")
                msg_id = msg.get("id", "")
                from_number = msg.get("from", "")
                timestamp = msg.get("timestamp", "")

                text = ""
                media_list = []

                if msg_type == "text":
                    text = msg.get("text", {}).get("body", "")
                elif msg_type in ("image", "video", "audio", "document", "sticker"):
                    media_obj = msg.get(msg_type, {})
                    media_list.append({
                        "type": msg_type,
                        "url": media_obj.get("link") or media_obj.get("url", ""),
                        "mime_type": media_obj.get("mime_type", ""),
                        "media_id": media_obj.get("id", ""),
                        "caption": media_obj.get("caption", ""),
                    })
                    text = media_obj.get("caption", f"[{msg_type}]")
                elif msg_type == "location":
                    loc = msg.get("location", {})
                    text = f"[location: {loc.get('latitude')},{loc.get('longitude')}]"
                elif msg_type == "reaction":
                    reaction = msg.get("reaction", {})
                    text = f"[reaction: {reaction.get('emoji', '')}]"
                elif msg_type == "interactive":
                    interactive = msg.get("interactive", {})
                    itype = interactive.get("type", "")
                    if itype == "button_reply":
                        text = interactive.get("button_reply", {}).get("title", "")
                    elif itype == "list_reply":
                        text = interactive.get("list_reply", {}).get("title", "")
                else:
                    text = msg.get("text", {}).get("body", "") if isinstance(msg.get("text"), dict) else str(msg.get("text", ""))

                # Check for referral (CTWA - Click to WhatsApp Ad)
                referral = None
                if msg.get("referral"):
                    ref = msg["referral"]
                    referral = {
                        "ad_id": ref.get("source_id"),
                        "headline": ref.get("headline"),
                        "body": ref.get("body"),
                        "source_url": ref.get("source_url"),
                        "source_type": ref.get("source_type"),
                    }

                normalized = {
                    "provider": "meta_direct",
                    "channel_source": "whatsapp",
                    "from_number": from_number,
                    "to_number": display_phone,
                    "text": text,
                    "event_id": msg_id,
                    "customer_name": contact_name,
                    "phone_number_id": phone_number_id,
                    "timestamp": timestamp,
                    "message_type": msg_type,
                }
                if media_list:
                    normalized["media"] = media_list
                if referral:
                    normalized["referral"] = referral

                results.append(normalized)

    return results


# ---------------------------------------------------------------------------
# Instagram DM Message Extraction
# ---------------------------------------------------------------------------
def _extract_instagram_messages(body: dict) -> List[Dict[str, Any]]:
    """Extract normalized messages from Instagram Messaging webhook payload."""
    results = []
    for entry in body.get("entry", []):
        page_id = entry.get("id", "")
        for messaging_event in entry.get("messaging", []):
            sender_id = messaging_event.get("sender", {}).get("id", "")
            recipient_id = messaging_event.get("recipient", {}).get("id", "")
            timestamp = messaging_event.get("timestamp", "")

            message = messaging_event.get("message", {})
            if not message:
                continue  # Skip non-message events (read receipts, etc.)

            msg_id = message.get("mid", "")
            text = message.get("text", "")

            media_list = []
            for att in message.get("attachments", []):
                att_type = att.get("type", "")
                payload_data = att.get("payload", {})
                media_list.append({
                    "type": att_type,
                    "url": payload_data.get("url", ""),
                })
                if not text:
                    text = f"[{att_type}]"

            normalized = {
                "provider": "meta",
                "channel_source": "instagram",
                "from_number": sender_id,
                "to_number": recipient_id,
                "text": text,
                "event_id": msg_id,
                "customer_name": "",  # IG doesn't include name; resolved later
                "page_id": page_id,
                "timestamp": str(timestamp),
                "message_type": "text" if not media_list else "media",
            }
            if media_list:
                normalized["media"] = media_list

            results.append(normalized)

    return results


# ---------------------------------------------------------------------------
# Facebook Messenger Message Extraction
# ---------------------------------------------------------------------------
def _extract_facebook_messages(body: dict) -> List[Dict[str, Any]]:
    """Extract normalized messages from Facebook Messenger webhook payload."""
    results = []
    for entry in body.get("entry", []):
        page_id = entry.get("id", "")
        for messaging_event in entry.get("messaging", []):
            sender_id = messaging_event.get("sender", {}).get("id", "")
            recipient_id = messaging_event.get("recipient", {}).get("id", "")
            timestamp = messaging_event.get("timestamp", "")

            message = messaging_event.get("message", {})
            if not message:
                continue  # Skip delivery, read, postback events handled elsewhere

            msg_id = message.get("mid", "")
            text = message.get("text", "")

            media_list = []
            for att in message.get("attachments", []):
                att_type = att.get("type", "")
                payload_data = att.get("payload", {})
                media_list.append({
                    "type": att_type,
                    "url": payload_data.get("url", ""),
                })
                if not text:
                    text = f"[{att_type}]"

            # Referral from Messenger ads
            referral = None
            if messaging_event.get("referral"):
                ref = messaging_event["referral"]
                referral = {
                    "ad_id": ref.get("ad_id"),
                    "source": ref.get("source"),
                    "type": ref.get("type"),
                    "ref": ref.get("ref"),
                }

            normalized = {
                "provider": "meta",
                "channel_source": "facebook",
                "from_number": sender_id,
                "to_number": recipient_id,
                "text": text,
                "event_id": msg_id,
                "customer_name": "",  # Resolved via Graph API later
                "page_id": page_id,
                "timestamp": str(timestamp),
                "message_type": "text" if not media_list else "media",
            }
            if media_list:
                normalized["media"] = media_list
            if referral:
                normalized["referral"] = referral

            results.append(normalized)

    return results


# ---------------------------------------------------------------------------
# WhatsApp Status Updates Handler
# ---------------------------------------------------------------------------
async def _process_whatsapp_statuses(body: dict):
    """
    Handle WhatsApp message status updates (sent, delivered, read, failed).
    Updates chat_messages with delivery status metadata.
    """
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for status in value.get("statuses", []):
                wa_message_id = status.get("id", "")
                status_value = status.get("status", "")  # sent | delivered | read | failed
                timestamp = status.get("timestamp", "")
                recipient_id = status.get("recipient_id", "")
                errors = status.get("errors", [])

                logger.info(
                    f"WhatsApp status: {status_value} for msg={wa_message_id} "
                    f"recipient={recipient_id}"
                )

                try:
                    # Update delivery status in chat_messages via platform_message_id
                    await db.execute(
                        """
                        UPDATE chat_messages
                        SET delivery_status = $1,
                            delivery_timestamp = to_timestamp($2::bigint),
                            updated_at = NOW()
                        WHERE platform_message_id = $3
                        """,
                        status_value,
                        int(timestamp) if timestamp else 0,
                        wa_message_id,
                    )
                except Exception:
                    # delivery_status column may not exist yet; log but don't fail
                    try:
                        await db.execute(
                            """
                            INSERT INTO message_status_log
                                (provider_message_id, status, recipient, timestamp, errors)
                            VALUES ($1, $2, $3, to_timestamp($4::bigint), $5)
                            ON CONFLICT DO NOTHING
                            """,
                            wa_message_id,
                            status_value,
                            recipient_id,
                            int(timestamp) if timestamp else 0,
                            json.dumps(errors) if errors else None,
                        )
                    except Exception as e2:
                        logger.debug(f"Could not log message status: {e2}")


# ---------------------------------------------------------------------------
# Sender Name Resolution (Graph API)
# ---------------------------------------------------------------------------
async def _resolve_sender_name(
    sender_id: str, recipient_id: str, platform: str, tenant_id: int
) -> str:
    """
    Fetch sender display name from Meta Graph API.
    Used for Instagram and Facebook where the webhook doesn't include the name.
    """
    try:
        token_row = await db.fetchrow(
            "SELECT access_token FROM meta_tokens WHERE page_id = $1 LIMIT 1",
            str(recipient_id),
        )
        if not token_row:
            token_row = await db.fetchrow(
                "SELECT access_token FROM meta_tokens WHERE tenant_id = $1 LIMIT 1",
                tenant_id,
            )
        if not token_row:
            return ""

        access_token = token_row["access_token"]

        async with httpx.AsyncClient(timeout=5.0) as client:
            if platform == "instagram":
                resp = await client.get(
                    f"https://graph.facebook.com/{GRAPH_API_VERSION}/{sender_id}",
                    params={
                        "fields": "name,username",
                        "access_token": access_token,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("name") or data.get("username") or ""

            elif platform == "facebook":
                # Try conversations endpoint first (more reliable in v13+)
                resp = await client.get(
                    f"https://graph.facebook.com/{GRAPH_API_VERSION}/{recipient_id}/conversations",
                    params={
                        "fields": "participants",
                        "user_id": sender_id,
                        "access_token": access_token,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    convs = data.get("data", [])
                    if convs:
                        for p in convs[0].get("participants", {}).get("data", []):
                            if p.get("id") == sender_id:
                                return p.get("name", "")

                # Fallback: direct profile fetch
                resp2 = await client.get(
                    f"https://graph.facebook.com/{GRAPH_API_VERSION}/{sender_id}",
                    params={
                        "fields": "first_name,last_name",
                        "access_token": access_token,
                    },
                )
                if resp2.status_code == 200:
                    data2 = resp2.json()
                    first = data2.get("first_name", "")
                    last = data2.get("last_name", "")
                    return f"{first} {last}".strip()

    except Exception as e:
        logger.warning(f"Failed to resolve sender name ({platform}): {e}")
    return ""


# ---------------------------------------------------------------------------
# Background Processor for Messaging Webhooks
# ---------------------------------------------------------------------------
async def _process_messaging_webhook(
    normalized_messages: List[Dict[str, Any]],
    url_tenant_id: Optional[int] = None,
):
    """
    Process extracted messaging events:
    1. Resolve tenant
    2. Resolve sender name if missing
    3. Forward each message to /chat
    """
    for msg in normalized_messages:
        try:
            channel_source = msg.get("channel_source", "")
            tenant_id = url_tenant_id

            # Resolve tenant if not provided in URL
            if not tenant_id:
                if channel_source == "whatsapp":
                    phone_number_id = msg.get("phone_number_id", "")
                    tenant_id = await _resolve_tenant_by_phone_number_id(phone_number_id)
                    if not tenant_id:
                        # Fallback: try display phone number in tenants table
                        display_phone = msg.get("to_number", "")
                        if display_phone:
                            row = await db.fetchrow(
                                "SELECT id FROM tenants WHERE bot_phone_number = $1 LIMIT 1",
                                display_phone.replace("+", ""),
                            )
                            if row:
                                tenant_id = int(row["id"])
                else:
                    # Instagram / Facebook — resolve by page_id
                    page_id = msg.get("page_id", "") or msg.get("to_number", "")
                    if page_id:
                        tenant_id = await _resolve_tenant_by_page_id(page_id)

            if not tenant_id:
                logger.warning(
                    f"No tenant found for {channel_source} message from {msg.get('from_number')}"
                )
                continue

            # Resolve sender name for IG/FB if missing
            if not msg.get("customer_name") and channel_source in ("instagram", "facebook"):
                sender_name = await _resolve_sender_name(
                    msg["from_number"],
                    msg.get("to_number", msg.get("page_id", "")),
                    channel_source,
                    tenant_id,
                )
                if sender_name:
                    msg["customer_name"] = sender_name

            # Forward to /chat
            await _forward_to_chat(msg, tenant_id)

        except Exception as e:
            logger.error(
                f"Error processing {msg.get('channel_source')} message: {e}",
                exc_info=True,
            )


# ---------------------------------------------------------------------------
# POST /meta  |  /meta/{tenant_id}  -- Unified Meta Webhook Handler
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
    Unified Meta webhook handler.
    Receives:
      - LeadGen notifications (existing)
      - WhatsApp Cloud API messages (object=whatsapp_business_account)
      - Instagram DM messages (object=instagram)
      - Facebook Messenger messages (object=page with messaging)
      - Custom flattened payloads (n8n/LeadsBridge)
    Always returns 200 quickly (Meta requires fast response).
    """
    # Signature verification (reads body once; parse JSON from bytes)
    try:
        body_bytes = await _verify_signature(request)
        body = json.loads(body_bytes)
    except HTTPException:
        raise
    except Exception:
        return {"status": "error", "message": "invalid_json"}

    # Route based on `object` field
    obj_type = body.get("object", "") if isinstance(body, dict) else ""

    # ----- WhatsApp Cloud API -----
    if obj_type == "whatsapp_business_account":
        # Check for status updates
        has_statuses = any(
            "statuses" in change.get("value", {})
            for entry in body.get("entry", [])
            for change in entry.get("changes", [])
        )
        if has_statuses:
            background_tasks.add_task(_process_whatsapp_statuses, body)

        # Check for actual messages
        messages = _extract_whatsapp_messages(body)
        if messages:
            logger.info(
                f"WhatsApp Cloud: {len(messages)} message(s) from "
                f"{messages[0].get('from_number')}"
            )
            background_tasks.add_task(
                _process_messaging_webhook, messages, tenant_id
            )

        return {"status": "received", "type": "whatsapp_cloud"}

    # ----- Instagram DM -----
    if obj_type == "instagram":
        messages = _extract_instagram_messages(body)
        if messages:
            logger.info(
                f"Instagram DM: {len(messages)} message(s) from "
                f"{messages[0].get('from_number')}"
            )
            background_tasks.add_task(
                _process_messaging_webhook, messages, tenant_id
            )
        return {"status": "received", "type": "instagram_dm"}

    # ----- Facebook Messenger -----
    if obj_type == "page":
        # Check if this is a messaging event vs leadgen
        has_messaging = any(
            "messaging" in entry
            for entry in body.get("entry", [])
        )
        has_leadgen = any(
            change.get("field") == "leadgen"
            for entry in body.get("entry", [])
            for change in entry.get("changes", [])
        )

        if has_messaging:
            messages = _extract_facebook_messages(body)
            if messages:
                logger.info(
                    f"Facebook Messenger: {len(messages)} message(s) from "
                    f"{messages[0].get('from_number')}"
                )
                background_tasks.add_task(
                    _process_messaging_webhook, messages, tenant_id
                )

        if has_leadgen:
            # Fall through to existing LeadGen processing below
            pass
        elif has_messaging:
            return {"status": "received", "type": "facebook_messenger"}

    # ----- Case A: Standard Meta Webhook (LeadGen entry based) -----
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

    # ----- Case B: Custom Flattened Payload (n8n/LeadsBridge Style) -----
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
