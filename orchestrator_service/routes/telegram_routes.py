"""
Telegram Notification Routes — SPEC-07
External HTTP endpoint for triggering Telegram notifications.
Authenticated via X-Webhook-Secret (timing-safe comparison).
"""

import os
import hmac
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field

from services.telegram_service import (
    telegram_service,
    TelegramSendResult,
    TelegramMessageTooLongError,
    TelegramRateLimitError,
)

logger = logging.getLogger(__name__)

WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")

router = APIRouter(tags=["Telegram Notifications"])


# ─── Models ───────────────────────────────────────────────────────────────────

class TelegramNotifyRequest(BaseModel):
    text: str = Field(..., description="Message text (HTML allowed, max 4000 chars)")
    chat_id: Optional[str] = Field(None, description="Target chat ID (default: env TELEGRAM_CHAT_ID)")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _verify_webhook_secret(provided: str) -> bool:
    """Timing-safe comparison of webhook secret."""
    if not WEBHOOK_SECRET:
        return False
    return hmac.compare_digest(provided.encode(), WEBHOOK_SECRET.encode())


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/internal/telegram/notify")
async def send_telegram_notification(
    body: TelegramNotifyRequest,
    x_webhook_secret: Optional[str] = Header(None),
):
    """
    Send a Telegram notification. Requires X-Webhook-Secret header.

    Returns:
        200: {"ok": true, "message_id": int}
        400: Message too long
        401: Unauthorized
        429: Rate limit exceeded
    """
    # Auth: timing-safe secret check
    if not x_webhook_secret or not _verify_webhook_secret(x_webhook_secret):
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        result = await telegram_service.send_message(
            text=body.text,
            chat_id=body.chat_id,
        )
        return {"ok": result.ok, "message_id": result.message_id, "error": result.error}

    except TelegramMessageTooLongError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except TelegramRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
