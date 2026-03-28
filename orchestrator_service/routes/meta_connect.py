"""
Meta Embedded Signup — Full Connection Routes
Connects WhatsApp, Instagram and Facebook Pages to CRM Ventas.

Endpoints:
  POST   /admin/meta/connect          — Exchange code, discover assets, store tokens
  GET    /admin/meta/status            — Check connection status & assets
  DELETE /admin/meta/disconnect        — Remove all Meta credentials & assets
  POST   /admin/meta/select-channels   — Activate selected assets as channel bindings
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from core.security import verify_admin_token, get_resolved_tenant_id, audit_access
from core.rate_limiter import limiter
from core.credentials import (
    save_tenant_credential,
    get_tenant_credential,
    encrypt_value,
)
from db import db
from services.meta_graph_client import (
    exchange_code,
    get_long_lived_token,
    discover_pages,
    discover_wabas,
    subscribe_page,
    validate_token,
    MetaGraphClientError,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# DB helpers — business_assets & channel_bindings (auto-created)
# ---------------------------------------------------------------------------

_MIGRATION_APPLIED = False


async def _ensure_tables():
    """Idempotently create business_assets and channel_bindings tables."""
    global _MIGRATION_APPLIED
    if _MIGRATION_APPLIED:
        return
    await db.execute("""
        CREATE TABLE IF NOT EXISTS business_assets (
            id BIGSERIAL PRIMARY KEY,
            tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            platform VARCHAR(50) NOT NULL,        -- 'facebook', 'instagram', 'whatsapp'
            asset_type VARCHAR(50) NOT NULL,       -- 'page', 'instagram_account', 'waba', 'phone_number'
            asset_id VARCHAR(255) NOT NULL,
            asset_name TEXT,
            parent_asset_id VARCHAR(255),          -- e.g. page_id for instagram, waba_id for phone
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(tenant_id, platform, asset_id)
        );
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS channel_bindings (
            id BIGSERIAL PRIMARY KEY,
            tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            channel VARCHAR(50) NOT NULL,          -- 'whatsapp', 'instagram', 'facebook'
            asset_id VARCHAR(255) NOT NULL,
            asset_name TEXT,
            config JSONB DEFAULT '{}',
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(tenant_id, channel, asset_id)
        );
    """)
    _MIGRATION_APPLIED = True


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class MetaConnectRequest(BaseModel):
    code: str


class SelectChannelsRequest(BaseModel):
    asset_ids: List[str]


# ---------------------------------------------------------------------------
# POST /connect — Full Meta Embedded Signup flow
# ---------------------------------------------------------------------------

@router.post("/connect")
@audit_access("meta_embedded_connect")
@limiter.limit("10/minute")
async def meta_connect(
    request: Request,
    body: MetaConnectRequest,
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
) -> Dict[str, Any]:
    """
    Full Meta connection flow:
    1. Exchange code -> short-lived token
    2. Short-lived -> long-lived token (60 days)
    3. Discover Facebook Pages (+ Instagram business accounts)
    4. Discover WhatsApp Business Accounts + phone numbers
    5. Store tokens encrypted in credentials
    6. Store discovered assets in business_assets
    7. Auto-subscribe pages to webhooks
    8. Return sanitized asset list (no tokens)
    """
    await _ensure_tables()

    try:
        # 1. Exchange code for short-lived token
        token_data = await exchange_code(body.code)
        short_token = token_data.get("access_token")
        if not short_token:
            raise HTTPException(status_code=400, detail="Failed to obtain access token from Meta")

        # 2. Get long-lived token
        ll_data = await get_long_lived_token(short_token)
        long_token = ll_data.get("access_token")
        expires_in = ll_data.get("expires_in", 5184000)  # default 60 days
        if not long_token:
            raise HTTPException(status_code=400, detail="Failed to obtain long-lived token from Meta")

        # Store user long-lived token
        await save_tenant_credential(tenant_id, "META_USER_LONG_TOKEN", long_token, category="meta")

        # 3. Discover Facebook Pages
        pages = await discover_pages(long_token)

        # 4. Discover WABAs
        wabas = await discover_wabas(long_token)

        # 5. Store page tokens & assets
        sanitized_pages = []
        for page in pages:
            page_id = page["id"]
            page_token = page.get("access_token", "")

            # Store page access token
            if page_token:
                await save_tenant_credential(
                    tenant_id,
                    f"META_PAGE_TOKEN_{page_id}",
                    page_token,
                    category="meta",
                )

            # Store page asset
            ig = page.get("instagram_business_account")
            await _upsert_asset(
                tenant_id,
                platform="facebook",
                asset_type="page",
                asset_id=page_id,
                asset_name=page.get("name", ""),
                metadata={
                    "category": page.get("category", ""),
                    "has_instagram": ig is not None,
                    "instagram_account_id": ig["id"] if ig else None,
                },
            )

            sanitized_page = {
                "id": page_id,
                "name": page.get("name", ""),
                "category": page.get("category", ""),
                "platform": "facebook",
                "asset_type": "page",
            }

            # If page has Instagram business account, also store it
            if ig:
                ig_id = ig["id"]
                await _upsert_asset(
                    tenant_id,
                    platform="instagram",
                    asset_type="instagram_account",
                    asset_id=ig_id,
                    asset_name=f"IG for {page.get('name', '')}",
                    parent_asset_id=page_id,
                    metadata={"linked_page_id": page_id},
                )
                sanitized_page["instagram_account"] = {"id": ig_id}

            sanitized_pages.append(sanitized_page)

            # 6. Auto-subscribe page to webhooks
            if page_token:
                await subscribe_page(page_id, page_token)

        # 7. Store WABA assets
        sanitized_wabas = []
        for waba in wabas:
            waba_id = waba["id"]
            await _upsert_asset(
                tenant_id,
                platform="whatsapp",
                asset_type="waba",
                asset_id=waba_id,
                asset_name=waba.get("name", ""),
                metadata={
                    "business_id": waba.get("business_id", ""),
                    "business_name": waba.get("business_name", ""),
                },
            )

            phone_numbers_sanitized = []
            for phone in waba.get("phone_numbers", []):
                phone_id = phone["id"]
                await _upsert_asset(
                    tenant_id,
                    platform="whatsapp",
                    asset_type="phone_number",
                    asset_id=phone_id,
                    asset_name=phone.get("display_phone_number", ""),
                    parent_asset_id=waba_id,
                    metadata={
                        "verified_name": phone.get("verified_name", ""),
                        "quality_rating": phone.get("quality_rating", ""),
                    },
                )
                phone_numbers_sanitized.append({
                    "id": phone_id,
                    "display_phone_number": phone.get("display_phone_number", ""),
                    "verified_name": phone.get("verified_name", ""),
                    "quality_rating": phone.get("quality_rating", ""),
                })

            sanitized_wabas.append({
                "id": waba_id,
                "name": waba.get("name", ""),
                "platform": "whatsapp",
                "asset_type": "waba",
                "phone_numbers": phone_numbers_sanitized,
            })

        logger.info(
            f"[AUDIT] meta_embedded_connect: tenant={tenant_id}, "
            f"pages={len(sanitized_pages)}, wabas={len(sanitized_wabas)}"
        )

        return {
            "success": True,
            "data": {
                "connected": True,
                "token_expires_in": expires_in,
                "pages": sanitized_pages,
                "wabas": sanitized_wabas,
                "message": "Meta account connected successfully. Select channels to activate.",
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    except MetaGraphClientError as e:
        logger.error(f"Meta Graph API error during connect: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Meta API error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during meta connect: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error connecting Meta: {str(e)}")


# ---------------------------------------------------------------------------
# GET /status — Connection status
# ---------------------------------------------------------------------------

@router.get("/status")
@audit_access("meta_connection_status")
@limiter.limit("30/minute")
async def meta_status(
    request: Request,
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
) -> Dict[str, Any]:
    """Check Meta connection status: which channels are connected, asset list, token validity."""
    await _ensure_tables()

    token = await get_tenant_credential(tenant_id, "META_USER_LONG_TOKEN")
    if not token:
        return {
            "success": True,
            "data": {
                "connected": False,
                "channels": {"facebook": False, "instagram": False, "whatsapp": False},
                "assets": [],
                "bindings": [],
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    # Validate token
    token_valid = True
    token_info: Dict[str, Any] = {}
    try:
        debug = await validate_token(token)
        token_info = debug.get("data", {})
        token_valid = token_info.get("is_valid", False)
    except Exception:
        token_valid = False

    # Fetch assets
    rows = await db.fetch(
        "SELECT id, platform, asset_type, asset_id, asset_name, parent_asset_id, metadata "
        "FROM business_assets WHERE tenant_id = $1 ORDER BY platform, asset_type",
        tenant_id,
    )
    assets = [
        {
            "id": r["id"],
            "platform": r["platform"],
            "asset_type": r["asset_type"],
            "asset_id": r["asset_id"],
            "asset_name": r["asset_name"],
            "parent_asset_id": r["parent_asset_id"],
            "metadata": r["metadata"],
        }
        for r in rows
    ]

    # Fetch active bindings
    binding_rows = await db.fetch(
        "SELECT id, channel, asset_id, asset_name, active "
        "FROM channel_bindings WHERE tenant_id = $1",
        tenant_id,
    )
    bindings = [
        {
            "id": r["id"],
            "channel": r["channel"],
            "asset_id": r["asset_id"],
            "asset_name": r["asset_name"],
            "active": r["active"],
        }
        for r in binding_rows
    ]

    # Determine which channels are connected (have at least one active binding)
    active_channels = {b["channel"] for b in bindings if b["active"]}

    return {
        "success": True,
        "data": {
            "connected": True,
            "token_valid": token_valid,
            "token_expires_at": token_info.get("expires_at"),
            "token_scopes": token_info.get("scopes", []),
            "channels": {
                "facebook": "facebook" in active_channels,
                "instagram": "instagram" in active_channels,
                "whatsapp": "whatsapp" in active_channels,
            },
            "assets": assets,
            "bindings": bindings,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


# ---------------------------------------------------------------------------
# DELETE /disconnect — Remove Meta connection
# ---------------------------------------------------------------------------

@router.delete("/disconnect")
@audit_access("meta_disconnect_all")
@limiter.limit("5/minute")
async def meta_disconnect(
    request: Request,
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
) -> Dict[str, Any]:
    """Remove all Meta credentials, business assets, and channel bindings for this tenant."""
    await _ensure_tables()

    # 1. Delete Meta credentials (user token + all page tokens)
    await db.execute(
        "DELETE FROM credentials WHERE tenant_id = $1 AND (name = 'META_USER_LONG_TOKEN' OR name LIKE 'META_PAGE_TOKEN_%')",
        tenant_id,
    )

    # 2. Delete business assets for Meta platforms
    await db.execute(
        "DELETE FROM business_assets WHERE tenant_id = $1 AND platform IN ('facebook', 'instagram', 'whatsapp')",
        tenant_id,
    )

    # 3. Delete channel bindings for Meta channels
    await db.execute(
        "DELETE FROM channel_bindings WHERE tenant_id = $1 AND channel IN ('facebook', 'instagram', 'whatsapp')",
        tenant_id,
    )

    logger.info(f"[AUDIT] meta_disconnect_all: tenant={tenant_id}, user={user_data.user_id}")

    return {
        "success": True,
        "data": {
            "disconnected": True,
            "message": "Meta account fully disconnected. All tokens, assets, and bindings removed.",
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


# ---------------------------------------------------------------------------
# POST /select-channels — Activate selected assets
# ---------------------------------------------------------------------------

@router.post("/select-channels")
@audit_access("meta_select_channels")
@limiter.limit("20/minute")
async def meta_select_channels(
    request: Request,
    body: SelectChannelsRequest,
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
) -> Dict[str, Any]:
    """
    Activate selected Meta assets as channel bindings.
    Input: list of asset_ids (from business_assets) to activate.
    Deactivates any previously active bindings not in the new list.
    """
    await _ensure_tables()

    if not body.asset_ids:
        raise HTTPException(status_code=400, detail="asset_ids list cannot be empty")

    # Fetch all Meta assets for this tenant
    rows = await db.fetch(
        "SELECT asset_id, asset_name, platform, asset_type FROM business_assets "
        "WHERE tenant_id = $1 AND platform IN ('facebook', 'instagram', 'whatsapp')",
        tenant_id,
    )
    asset_map = {r["asset_id"]: r for r in rows}

    # Validate all requested asset_ids exist
    invalid = [aid for aid in body.asset_ids if aid not in asset_map]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Unknown asset IDs: {invalid}")

    # Deactivate all existing Meta bindings
    await db.execute(
        "DELETE FROM channel_bindings WHERE tenant_id = $1 AND channel IN ('facebook', 'instagram', 'whatsapp')",
        tenant_id,
    )

    # Create new bindings for selected assets
    activated = []
    for asset_id in body.asset_ids:
        asset = asset_map[asset_id]
        channel = asset["platform"]  # facebook, instagram, whatsapp
        await db.execute(
            """
            INSERT INTO channel_bindings (tenant_id, channel, asset_id, asset_name, active, created_at, updated_at)
            VALUES ($1, $2, $3, $4, TRUE, NOW(), NOW())
            ON CONFLICT (tenant_id, channel, asset_id)
            DO UPDATE SET active = TRUE, asset_name = $4, updated_at = NOW()
            """,
            tenant_id,
            channel,
            asset_id,
            asset["asset_name"],
        )
        activated.append({
            "asset_id": asset_id,
            "asset_name": asset["asset_name"],
            "channel": channel,
            "asset_type": asset["asset_type"],
        })

    logger.info(
        f"[AUDIT] meta_select_channels: tenant={tenant_id}, activated={len(activated)}"
    )

    return {
        "success": True,
        "data": {
            "activated": activated,
            "message": f"{len(activated)} channel(s) activated successfully.",
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _upsert_asset(
    tenant_id: int,
    platform: str,
    asset_type: str,
    asset_id: str,
    asset_name: str,
    parent_asset_id: Optional[str] = None,
    metadata: Optional[Dict] = None,
):
    """Insert or update a business asset."""
    import json as _json

    meta_json = _json.dumps(metadata or {})
    await db.execute(
        """
        INSERT INTO business_assets (tenant_id, platform, asset_type, asset_id, asset_name, parent_asset_id, metadata, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, NOW(), NOW())
        ON CONFLICT (tenant_id, platform, asset_id)
        DO UPDATE SET asset_name = $5, asset_type = $3, parent_asset_id = $6, metadata = $7::jsonb, updated_at = NOW()
        """,
        tenant_id,
        platform,
        asset_type,
        asset_id,
        asset_name,
        parent_asset_id,
        meta_json,
    )
