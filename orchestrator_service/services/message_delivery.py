"""
Unified Message Delivery -- Provider Abstraction Layer.

Routes outbound messages to the correct provider (YCloud or Meta Direct API)
based on channel type and tenant configuration (channel_bindings + credentials).

Usage:
    from services.message_delivery import delivery

    await delivery.send(
        tenant_id=1,
        to="5491155551234",
        text="Hola!",
        channel="whatsapp",          # whatsapp | instagram | facebook
        provider=None,               # auto-detect from channel_bindings / credentials
        images=["https://example.com/img.jpg"],
        correlation_id="abc-123",
    )

Backward-compatible: the old ``unified_message_delivery()`` function is still
exported and delegates to ``delivery.send()``.
"""
import logging
import os
import uuid
from typing import List, Optional

import httpx

from db import db
from core.credentials import get_tenant_credential
from services.meta_messaging_client import meta_client

logger = logging.getLogger(__name__)

WHATSAPP_SERVICE_URL = os.getenv("WHATSAPP_SERVICE_URL", "http://whatsapp_service:8002")
INTERNAL_API_TOKEN = os.getenv("INTERNAL_API_TOKEN", "internal-secret-token")


class UnifiedMessageDelivery:
    """Thin router that decides *how* to send each outbound message."""

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    async def send(
        self,
        tenant_id: int,
        to: str,
        text: str,
        channel: str = "whatsapp",
        provider: Optional[str] = None,
        images: Optional[List[str]] = None,
        correlation_id: str = "",
        *,
        # Optional overrides for the Meta path (avoids extra DB queries when
        # the caller already resolved these).
        meta_phone_number_id: Optional[str] = None,
        meta_page_id: Optional[str] = None,
        meta_access_token: Optional[str] = None,
    ) -> dict:
        """
        Send a message through the appropriate provider.

        Returns a dict with at least {"status": "sent"|"error", ...}.
        """
        images = images or []
        channel = (channel or "whatsapp").lower()

        if not provider:
            provider = await self._get_provider_for_channel(tenant_id, channel)

        logger.info(
            "unified_delivery tenant=%s channel=%s provider=%s to=%s text_len=%d images=%d cid=%s",
            tenant_id, channel, provider, to, len(text or ""), len(images), correlation_id,
        )

        try:
            if provider == "meta":
                return await self._send_via_meta(
                    tenant_id=tenant_id,
                    to=to,
                    text=text,
                    channel=channel,
                    images=images,
                    correlation_id=correlation_id,
                    phone_number_id_override=meta_phone_number_id,
                    page_id_override=meta_page_id,
                    access_token_override=meta_access_token,
                )
            else:
                # Default: ycloud (backward compatible)
                return await self._send_via_ycloud(
                    tenant_id=tenant_id,
                    to=to,
                    text=text,
                    images=images,
                    correlation_id=correlation_id,
                )
        except Exception as exc:
            logger.error(
                "unified_delivery_error tenant=%s provider=%s error=%s",
                tenant_id, provider, exc,
            )
            return {"status": "error", "provider": provider, "error": str(exc)}

    # ------------------------------------------------------------------
    # Provider resolution
    # ------------------------------------------------------------------
    async def _get_provider_for_channel(self, tenant_id: int, channel: str) -> str:
        """
        Determine which provider to use for a given channel.

        Priority:
        1. channel_bindings table (explicit mapping per tenant)
        2. Heuristic based on available credentials
        """
        # 1. Check channel_bindings for an active binding
        try:
            row = await db.fetchrow(
                """
                SELECT provider
                FROM channel_bindings
                WHERE tenant_id = $1
                  AND channel_type = $2
                  AND is_active = true
                ORDER BY created_at DESC
                LIMIT 1
                """,
                tenant_id,
                channel,
            )
            if row and row["provider"]:
                return row["provider"]
        except Exception as exc:
            logger.warning(
                "channel_binding_lookup_failed tenant=%s channel=%s error=%s",
                tenant_id, channel, exc,
            )

        # 2. Heuristic fallback
        if channel in ("instagram", "facebook"):
            # These channels can ONLY go through Meta
            return "meta"

        if channel == "whatsapp":
            # Check if tenant has Meta WA credentials
            meta_token = await get_tenant_credential(tenant_id, "META_WA_ACCESS_TOKEN")
            meta_phone = await get_tenant_credential(tenant_id, "META_WA_PHONE_NUMBER_ID")
            if meta_token and meta_phone:
                return "meta"

            # Fallback to ycloud
            return "ycloud"

        # Unknown channel -- default to ycloud
        return "ycloud"

    # ------------------------------------------------------------------
    # YCloud path (relay through whatsapp_service or direct)
    # ------------------------------------------------------------------
    async def _send_via_ycloud(
        self,
        tenant_id: int,
        to: str,
        text: str,
        images: List[str],
        correlation_id: str,
    ) -> dict:
        """
        Send via YCloud.

        Strategy: relay through whatsapp_service /send endpoint (it already
        handles API key resolution and formatting). For images, call YCloud
        API directly since /send only supports text and templates.
        """
        results: List[dict] = []

        # Send images first (if any)
        for img_url in images:
            res = await self._ycloud_direct_image(
                tenant_id=tenant_id,
                to=to,
                image_url=img_url,
                correlation_id=correlation_id,
            )
            results.append(res)

        # Then send text
        if text:
            if WHATSAPP_SERVICE_URL:
                res = await self._ycloud_relay_send(
                    tenant_id=tenant_id,
                    to=to,
                    text=text,
                    correlation_id=correlation_id,
                )
            else:
                res = await self._ycloud_direct_text(
                    tenant_id=tenant_id,
                    to=to,
                    text=text,
                    correlation_id=correlation_id,
                )
            results.append(res)

        return {
            "status": "sent",
            "provider": "ycloud",
            "results": results,
        }

    async def _ycloud_relay_send(
        self,
        tenant_id: int,
        to: str,
        text: str,
        correlation_id: str,
    ) -> dict:
        """Call whatsapp_service /send endpoint for text messages."""
        url = f"{WHATSAPP_SERVICE_URL}/send?tenant_id={tenant_id}"
        payload = {
            "to": to,
            "type": "text",
            "text": text,
        }
        headers = {
            "X-Correlation-Id": correlation_id,
            "X-Internal-Token": INTERNAL_API_TOKEN,
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=5.0)) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:
            logger.error("ycloud_relay_failed to=%s error=%s", to, exc)
            # Fallback to direct YCloud send
            logger.info("Falling back to direct YCloud text send")
            return await self._ycloud_direct_text(tenant_id, to, text, correlation_id)

    async def _ycloud_direct_text(
        self,
        tenant_id: int,
        to: str,
        text: str,
        correlation_id: str,
    ) -> dict:
        """Send text directly via YCloud API."""
        api_key, business_number = await self._resolve_ycloud_creds(tenant_id)
        url = "https://api.ycloud.com/v2/whatsapp/messages/sendDirectly"
        headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
        payload = {
            "from": business_number,
            "to": to,
            "type": "text",
            "text": {"body": text, "preview_url": True},
        }
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=5.0)) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def _ycloud_direct_image(
        self,
        tenant_id: int,
        to: str,
        image_url: str,
        correlation_id: str,
    ) -> dict:
        """Send image directly via YCloud API."""
        api_key, business_number = await self._resolve_ycloud_creds(tenant_id)
        url = "https://api.ycloud.com/v2/whatsapp/messages/sendDirectly"
        headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
        payload = {
            "from": business_number,
            "to": to,
            "type": "image",
            "image": {"link": image_url},
        }
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=5.0)) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def _resolve_ycloud_creds(self, tenant_id: int):
        """Resolve YCloud API key and business number for tenant."""
        api_key = await get_tenant_credential(tenant_id, "YCLOUD_API_KEY")
        if not api_key:
            api_key = os.getenv("YCLOUD_API_KEY")
        if not api_key:
            raise ValueError(f"No YCLOUD_API_KEY found for tenant {tenant_id}")

        business_number = await get_tenant_credential(tenant_id, "YCLOUD_WHATSAPP_NUMBER")
        if not business_number:
            business_number = os.getenv("YCLOUD_WHATSAPP_NUMBER", "")

        return api_key, business_number

    # ------------------------------------------------------------------
    # Meta direct path
    # ------------------------------------------------------------------
    async def _send_via_meta(
        self,
        tenant_id: int,
        to: str,
        text: str,
        channel: str,
        images: List[str],
        correlation_id: str,
        phone_number_id_override: Optional[str] = None,
        page_id_override: Optional[str] = None,
        access_token_override: Optional[str] = None,
    ) -> dict:
        """Route to the correct Meta Graph API based on channel type."""
        if channel == "whatsapp":
            return await self._meta_send_whatsapp(
                tenant_id, to, text, images, correlation_id,
                phone_number_id_override, access_token_override,
            )
        elif channel in ("instagram", "facebook"):
            return await self._meta_send_messenger_or_ig(
                tenant_id, to, text, channel, images, correlation_id,
                page_id_override, access_token_override,
            )
        else:
            raise ValueError(f"Unsupported Meta channel: {channel}")

    async def _meta_send_whatsapp(
        self,
        tenant_id: int,
        to: str,
        text: str,
        images: List[str],
        correlation_id: str,
        phone_number_id_override: Optional[str] = None,
        access_token_override: Optional[str] = None,
    ) -> dict:
        """Send WhatsApp messages via Meta Cloud API."""
        phone_number_id = phone_number_id_override or await get_tenant_credential(
            tenant_id, "META_WA_PHONE_NUMBER_ID"
        )
        access_token = access_token_override or await get_tenant_credential(
            tenant_id, "META_WA_ACCESS_TOKEN"
        )
        if not phone_number_id or not access_token:
            raise ValueError(
                f"Missing META_WA_PHONE_NUMBER_ID or META_WA_ACCESS_TOKEN for tenant {tenant_id}"
            )

        results: List[dict] = []

        # Images first
        for img_url in images:
            res = await meta_client.send_whatsapp_image(
                phone_number_id, to, img_url, access_token
            )
            results.append(res)

        # Then text
        if text:
            res = await meta_client.send_whatsapp_text(
                phone_number_id, to, text, access_token
            )
            results.append(res)

        return {"status": "sent", "provider": "meta", "channel": "whatsapp", "results": results}

    async def _meta_send_messenger_or_ig(
        self,
        tenant_id: int,
        to: str,
        text: str,
        channel: str,
        images: List[str],
        correlation_id: str,
        page_id_override: Optional[str] = None,
        access_token_override: Optional[str] = None,
    ) -> dict:
        """Send Facebook Messenger or Instagram DM messages via Meta Send API."""
        page_id = page_id_override
        page_token = access_token_override

        if not page_id or not page_token:
            # Try channel_bindings to get the channel_id (= page_id)
            try:
                binding = await db.fetchrow(
                    """
                    SELECT channel_id
                    FROM channel_bindings
                    WHERE tenant_id = $1
                      AND channel_type = $2
                      AND provider = 'meta'
                      AND is_active = true
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    tenant_id,
                    channel,
                )
                if binding:
                    page_id = page_id or binding["channel_id"]
            except Exception as exc:
                logger.warning("channel_binding_fetch_error: %s", exc)

            # Resolve page token from credentials
            if channel == "instagram":
                page_token = page_token or await get_tenant_credential(
                    tenant_id, "META_IG_PAGE_TOKEN"
                )
                # Fallback: Instagram uses the Facebook Page token linked to IG account
                if not page_token:
                    page_token = await get_tenant_credential(tenant_id, "META_PAGE_TOKEN")
            else:
                page_token = page_token or await get_tenant_credential(
                    tenant_id, "META_PAGE_TOKEN"
                )

        if not page_id or not page_token:
            raise ValueError(
                f"Missing page_id or page_token for {channel} on tenant {tenant_id}"
            )

        results: List[dict] = []

        # Pick the right sender based on channel
        if channel == "instagram":
            send_text_fn = meta_client.send_instagram_text
            send_image_fn = meta_client.send_instagram_image
        else:
            send_text_fn = meta_client.send_messenger_text
            send_image_fn = meta_client.send_messenger_image

        # Images first
        for img_url in images:
            res = await send_image_fn(page_id, to, img_url, page_token)
            results.append(res)

        # Then text
        if text:
            res = await send_text_fn(page_id, to, text, page_token)
            results.append(res)

        return {"status": "sent", "provider": "meta", "channel": channel, "results": results}


# Module-level singleton
delivery = UnifiedMessageDelivery()


# ------------------------------------------------------------------
# Backward-compatible function (old callers use this)
# ------------------------------------------------------------------
async def unified_message_delivery(
    tenant_id: int,
    phone: str,
    text: str,
    channel: str = "whatsapp",
    provider: str = "ycloud",
) -> dict:
    """
    Legacy wrapper. Delegates to delivery.send().

    Kept for backward compatibility with existing callers that import
    ``from services.message_delivery import unified_message_delivery``.
    """
    correlation_id = f"manual_{uuid.uuid4().hex[:12]}"
    return await delivery.send(
        tenant_id=tenant_id,
        to=phone,
        text=text,
        channel=channel,
        provider=provider if provider != "ycloud" else None,  # None = auto-detect
        correlation_id=correlation_id,
    )
