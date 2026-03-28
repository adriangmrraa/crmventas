"""
Channel Bindings & Multi-Channel Routing Routes
Maps external channel IDs (WABA IDs, Page IDs, IG account IDs) to tenants.
"""
import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, Header, Query
from pydantic import BaseModel, Field

from db import db
from core.security import get_current_user_context

logger = logging.getLogger("channel_routes")

# --- Internal token auth (same pattern as main.py) ---
INTERNAL_API_TOKEN = os.getenv("INTERNAL_API_TOKEN", "internal-secret-token")


def _verify_internal_token(x_internal_token: Optional[str] = Header(None)):
    if not x_internal_token or x_internal_token != INTERNAL_API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing internal token")
    return x_internal_token


# --- Redis helper (graceful fallback to no-cache) ---
_redis_client = None
_redis_init_done = False


async def _get_redis():
    global _redis_client, _redis_init_done
    if _redis_init_done:
        return _redis_client
    _redis_init_done = True
    try:
        import redis.asyncio as aioredis
        from config import Settings
        settings = Settings()
        if settings.REDIS_URL:
            _redis_client = aioredis.Redis.from_url(
                settings.REDIS_URL,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
            )
            # Test connection
            await _redis_client.ping()
            logger.info("Channel routes: Redis connected for routing cache")
        else:
            logger.warning("Channel routes: No REDIS_URL, routing cache disabled")
    except Exception as e:
        logger.warning(f"Channel routes: Redis unavailable ({e}), routing cache disabled")
        _redis_client = None
    return _redis_client


ROUTING_CACHE_TTL = 300  # 5 minutes


# ============================================================
# INTERNAL ROUTING ROUTER
# ============================================================
internal_router = APIRouter(prefix="/internal/routing", tags=["Internal Routing"])


class RoutingResponse(BaseModel):
    tenant_id: int
    tenant_name: str
    resolved_at: str


@internal_router.get("/resolve", response_model=RoutingResponse)
async def resolve_channel(
    provider: str = Query(..., description="Provider: ycloud, meta, chatwoot"),
    channel_id: str = Query(..., description="External channel ID (page_id, waba_id, phone_number_id)"),
    _token: str = Depends(_verify_internal_token),
):
    """
    Resolve a provider + channel_id to a tenant.
    Used internally by webhook processors to determine which tenant owns an inbound message.
    Results are cached in Redis for 5 minutes.
    """
    cache_key = f"channel_route:{provider}:{channel_id}"

    # 1. Try Redis cache
    redis = await _get_redis()
    if redis:
        try:
            cached = await redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                return RoutingResponse(**data)
        except Exception as e:
            logger.warning(f"Redis cache read error: {e}")

    # 2. Query DB
    row = await db.fetchrow(
        """
        SELECT cb.tenant_id, t.clinic_name AS tenant_name
        FROM channel_bindings cb
        JOIN tenants t ON t.id = cb.tenant_id
        WHERE cb.provider = $1 AND cb.channel_id = $2 AND cb.is_active = TRUE
        LIMIT 1
        """,
        provider, channel_id,
    )

    if not row:
        raise HTTPException(status_code=404, detail=f"No active binding for provider={provider} channel_id={channel_id}")

    result = {
        "tenant_id": row["tenant_id"],
        "tenant_name": row["tenant_name"],
        "resolved_at": datetime.now(timezone.utc).isoformat(),
    }

    # 3. Cache in Redis
    if redis:
        try:
            await redis.setex(cache_key, ROUTING_CACHE_TTL, json.dumps(result))
        except Exception as e:
            logger.warning(f"Redis cache write error: {e}")

    return RoutingResponse(**result)


# ============================================================
# ADMIN CHANNEL MANAGEMENT ROUTER
# ============================================================
admin_router = APIRouter(prefix="/admin/core/channels", tags=["Channel Management"])


# --- Pydantic schemas ---

class ChannelBindingCreate(BaseModel):
    provider: str = Field(..., pattern="^(ycloud|meta|chatwoot)$")
    channel_type: str = Field(..., pattern="^(whatsapp|instagram|facebook)$")
    channel_id: str = Field(..., min_length=1, max_length=255)
    label: Optional[str] = None


class ChannelBindingOut(BaseModel):
    id: int
    tenant_id: int
    provider: str
    channel_type: str
    channel_id: str
    label: Optional[str]
    is_active: bool
    created_at: str


class BusinessAssetOut(BaseModel):
    id: str
    tenant_id: int
    asset_type: str
    external_id: str
    name: Optional[str]
    metadata: Optional[dict]
    is_active: bool
    created_at: str


# --- Endpoints ---

@admin_router.get("", response_model=List[ChannelBindingOut])
async def list_channel_bindings(
    context: dict = Depends(get_current_user_context),
):
    """List all channel bindings for the current tenant."""
    tenant_id = context["tenant_id"]
    rows = await db.fetch(
        """
        SELECT id, tenant_id, provider, channel_type, channel_id, label, is_active, created_at
        FROM channel_bindings
        WHERE tenant_id = $1
        ORDER BY created_at DESC
        """,
        tenant_id,
    )
    return [
        ChannelBindingOut(
            id=r["id"],
            tenant_id=r["tenant_id"],
            provider=r["provider"],
            channel_type=r["channel_type"],
            channel_id=r["channel_id"],
            label=r["label"],
            is_active=r["is_active"],
            created_at=r["created_at"].isoformat() if r["created_at"] else "",
        )
        for r in rows
    ]


@admin_router.post("", response_model=ChannelBindingOut, status_code=201)
async def create_channel_binding(
    payload: ChannelBindingCreate,
    context: dict = Depends(get_current_user_context),
):
    """Bind an external channel to the current tenant."""
    tenant_id = context["tenant_id"]

    # Check for duplicate
    existing = await db.fetchrow(
        "SELECT id FROM channel_bindings WHERE provider = $1 AND channel_id = $2",
        payload.provider, payload.channel_id,
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Channel {payload.provider}:{payload.channel_id} is already bound (binding id={existing['id']})"
        )

    row = await db.fetchrow(
        """
        INSERT INTO channel_bindings (tenant_id, provider, channel_type, channel_id, label)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, tenant_id, provider, channel_type, channel_id, label, is_active, created_at
        """,
        tenant_id, payload.provider, payload.channel_type, payload.channel_id, payload.label,
    )

    # Invalidate routing cache for this channel
    redis = await _get_redis()
    if redis:
        try:
            await redis.delete(f"channel_route:{payload.provider}:{payload.channel_id}")
        except Exception:
            pass

    logger.info(f"Channel bound: tenant={tenant_id} provider={payload.provider} channel={payload.channel_id}")

    return ChannelBindingOut(
        id=row["id"],
        tenant_id=row["tenant_id"],
        provider=row["provider"],
        channel_type=row["channel_type"],
        channel_id=row["channel_id"],
        label=row["label"],
        is_active=row["is_active"],
        created_at=row["created_at"].isoformat() if row["created_at"] else "",
    )


@admin_router.delete("/{binding_id}")
async def delete_channel_binding(
    binding_id: int,
    context: dict = Depends(get_current_user_context),
):
    """Unbind (soft-delete) a channel from the current tenant."""
    tenant_id = context["tenant_id"]

    row = await db.fetchrow(
        "SELECT id, provider, channel_id FROM channel_bindings WHERE id = $1 AND tenant_id = $2",
        binding_id, tenant_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Channel binding not found")

    await db.execute(
        "UPDATE channel_bindings SET is_active = FALSE WHERE id = $1",
        binding_id,
    )

    # Invalidate routing cache
    redis = await _get_redis()
    if redis:
        try:
            await redis.delete(f"channel_route:{row['provider']}:{row['channel_id']}")
        except Exception:
            pass

    logger.info(f"Channel unbound: tenant={tenant_id} binding_id={binding_id}")
    return {"ok": True, "detail": f"Channel binding {binding_id} deactivated"}


@admin_router.get("/assets", response_model=List[BusinessAssetOut])
async def list_business_assets(
    context: dict = Depends(get_current_user_context),
):
    """List all business assets (FB pages, IG accounts, WABA) for the current tenant."""
    tenant_id = context["tenant_id"]
    rows = await db.fetch(
        """
        SELECT id, tenant_id, asset_type, external_id, name, metadata, is_active, created_at
        FROM business_assets
        WHERE tenant_id = $1 AND is_active = TRUE
        ORDER BY created_at DESC
        """,
        tenant_id,
    )
    return [
        BusinessAssetOut(
            id=str(r["id"]),
            tenant_id=r["tenant_id"],
            asset_type=r["asset_type"],
            external_id=r["external_id"],
            name=r["name"],
            metadata=r["metadata"] if r["metadata"] else {},
            is_active=r["is_active"],
            created_at=r["created_at"].isoformat() if r["created_at"] else "",
        )
        for r in rows
    ]
