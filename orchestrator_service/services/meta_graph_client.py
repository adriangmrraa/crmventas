"""
Meta Graph API Client — CRM Ventas
Handles token exchange, asset discovery, and page subscription for the
Meta Embedded Signup / OAuth flow (WhatsApp, Instagram, Facebook Pages).
"""

import os
import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

META_APP_ID = os.getenv("META_APP_ID", "")
META_APP_SECRET = os.getenv("META_APP_SECRET", "")
META_GRAPH_API_VERSION = os.getenv("META_GRAPH_API_VERSION", "v19.0")
META_REDIRECT_URI = os.getenv("META_REDIRECT_URI", "").rstrip("/")

GRAPH_BASE = f"https://graph.facebook.com/{META_GRAPH_API_VERSION}"
TIMEOUT = 30.0


class MetaGraphClientError(Exception):
    """Raised when the Meta Graph API returns an error."""

    def __init__(self, message: str, status_code: int = 0, meta_error: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.meta_error = meta_error or {}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _get(url: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(url, params=params)
        data = resp.json()
        if "error" in data:
            err = data["error"]
            raise MetaGraphClientError(
                message=err.get("message", "Unknown Graph API error"),
                status_code=resp.status_code,
                meta_error=err,
            )
        return data


async def _post(url: str, data: Dict[str, Any] | None = None, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(url, data=data, params=params)
        result = resp.json()
        if "error" in result:
            err = result["error"]
            raise MetaGraphClientError(
                message=err.get("message", "Unknown Graph API error"),
                status_code=resp.status_code,
                meta_error=err,
            )
        return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def exchange_code(code: str) -> Dict[str, Any]:
    """Exchange an OAuth authorization code for a short-lived user access token."""
    url = f"{GRAPH_BASE}/oauth/access_token"
    params = {
        "client_id": META_APP_ID,
        "client_secret": META_APP_SECRET,
        "redirect_uri": META_REDIRECT_URI,
        "code": code,
    }
    data = await _get(url, params=params)
    logger.info("Exchanged OAuth code for short-lived token")
    return data  # {access_token, token_type, expires_in}


async def get_long_lived_token(short_token: str) -> Dict[str, Any]:
    """Exchange a short-lived token for a long-lived token (60 days)."""
    url = f"{GRAPH_BASE}/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": META_APP_ID,
        "client_secret": META_APP_SECRET,
        "fb_exchange_token": short_token,
    }
    data = await _get(url, params=params)
    logger.info("Exchanged short token for long-lived token (60 days)")
    return data  # {access_token, token_type, expires_in}


async def discover_pages(user_token: str) -> List[Dict[str, Any]]:
    """
    GET /me/accounts — returns Facebook Pages the user manages.
    For each page, also checks for an instagram_business_account.
    Returns: [{id, name, access_token, category, instagram_business_account: {id} | None}]
    """
    url = f"{GRAPH_BASE}/me/accounts"
    params = {
        "access_token": user_token,
        "fields": "id,name,access_token,category,instagram_business_account",
        "limit": 100,
    }
    pages: List[Dict[str, Any]] = []
    while url:
        data = await _get(url, params=params)
        for item in data.get("data", []):
            pages.append({
                "id": item["id"],
                "name": item.get("name", ""),
                "access_token": item.get("access_token", ""),
                "category": item.get("category", ""),
                "instagram_business_account": item.get("instagram_business_account"),
            })
        # Pagination
        paging = data.get("paging", {})
        url = paging.get("next")
        params = None  # next URL already contains params
    logger.info(f"Discovered {len(pages)} Facebook Pages")
    return pages


async def discover_wabas(user_token: str) -> List[Dict[str, Any]]:
    """
    GET /me/businesses then for each business GET /{biz_id}/owned_whatsapp_business_accounts
    Falls back to GET /me/whatsapp_business_accounts if the direct endpoint works.
    Returns: [{id, name, phone_numbers: [{id, display_phone_number, verified_name, quality_rating}]}]
    """
    wabas: List[Dict[str, Any]] = []

    # Try direct endpoint first (requires whatsapp_business_management scope)
    try:
        url = f"{GRAPH_BASE}/me/businesses"
        params = {"access_token": user_token, "fields": "id,name", "limit": 50}
        biz_data = await _get(url, params=params)
        businesses = biz_data.get("data", [])

        for biz in businesses:
            biz_id = biz["id"]
            try:
                waba_url = f"{GRAPH_BASE}/{biz_id}/owned_whatsapp_business_accounts"
                waba_params = {"access_token": user_token, "fields": "id,name", "limit": 50}
                waba_data = await _get(waba_url, params=waba_params)

                for waba in waba_data.get("data", []):
                    phone_numbers = await _get_waba_phones(waba["id"], user_token)
                    wabas.append({
                        "id": waba["id"],
                        "name": waba.get("name", ""),
                        "business_id": biz_id,
                        "business_name": biz.get("name", ""),
                        "phone_numbers": phone_numbers,
                    })
            except MetaGraphClientError as e:
                logger.warning(f"Could not fetch WABAs for business {biz_id}: {e}")
                continue
    except MetaGraphClientError as e:
        logger.warning(f"Could not list businesses, skipping WABA discovery: {e}")

    logger.info(f"Discovered {len(wabas)} WhatsApp Business Accounts")
    return wabas


async def _get_waba_phones(waba_id: str, token: str) -> List[Dict[str, Any]]:
    """GET /{waba_id}/phone_numbers"""
    url = f"{GRAPH_BASE}/{waba_id}/phone_numbers"
    params = {
        "access_token": token,
        "fields": "id,display_phone_number,verified_name,quality_rating,code_verification_status",
    }
    data = await _get(url, params=params)
    return [
        {
            "id": p["id"],
            "display_phone_number": p.get("display_phone_number", ""),
            "verified_name": p.get("verified_name", ""),
            "quality_rating": p.get("quality_rating", ""),
            "code_verification_status": p.get("code_verification_status", ""),
        }
        for p in data.get("data", [])
    ]


async def subscribe_page(page_id: str, page_token: str) -> bool:
    """
    POST /{page_id}/subscribed_apps — subscribe the app to receive
    webhooks for this page (messages, feed, etc.).
    """
    url = f"{GRAPH_BASE}/{page_id}/subscribed_apps"
    data = {
        "access_token": page_token,
        "subscribed_fields": "messages,messaging_postbacks,feed,mention",
    }
    try:
        result = await _post(url, data=data)
        success = result.get("success", False)
        logger.info(f"Page {page_id} webhook subscription: {success}")
        return success
    except MetaGraphClientError as e:
        logger.error(f"Failed to subscribe page {page_id}: {e}")
        return False


async def validate_token(token: str) -> Dict[str, Any]:
    """Debug-inspect a token via /debug_token."""
    url = f"{GRAPH_BASE}/debug_token"
    params = {
        "input_token": token,
        "access_token": f"{META_APP_ID}|{META_APP_SECRET}",
    }
    return await _get(url, params=params)
