"""
Telegram Bot Notification Service — SPEC-07
Internal service for sending Telegram notifications.
Used by cold call assignment, CEO alerts, and other internal services.
"""

import os
import hmac
import time
import logging
from typing import Literal, Optional

import httpx
import bleach
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ─── Configuration ────────────────────────────────────────────────────────────

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_CEO_CHAT_ID = os.getenv("TELEGRAM_CEO_CHAT_ID", "")
TELEGRAM_RATE_LIMIT_PER_MIN = int(os.getenv("TELEGRAM_RATE_LIMIT_PER_MIN", "10"))
TELEGRAM_API_BASE = "https://api.telegram.org"

# Telegram HTML mode allowed tags
ALLOWED_TAGS = ["b", "i", "u", "s", "code", "pre", "a"]
ALLOWED_ATTRIBUTES = {"a": ["href"]}

MAX_MESSAGE_LENGTH = 4000


# ─── Exceptions ───────────────────────────────────────────────────────────────

class TelegramMessageTooLongError(Exception):
    """Raised when message exceeds 4000 characters."""
    pass


class TelegramRateLimitError(Exception):
    """Raised when rate limit is exceeded for a chat_id."""
    pass


# ─── Models ───────────────────────────────────────────────────────────────────

class TelegramSendResult(BaseModel):
    ok: bool
    message_id: Optional[int] = None
    error: Optional[str] = None


# ─── HTML Sanitizer ──────────────────────────────────────────────────────────

def sanitize_html(text: str) -> str:
    """
    Sanitize HTML for Telegram: only allow b, i, u, s, code, pre, a tags.
    All other tags and attributes are stripped.
    """
    return bleach.clean(
        text,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True,
    )


# ─── Sliding Window Rate Limiter ─────────────────────────────────────────────

class SlidingWindowRateLimiter:
    """In-memory sliding window rate limiter per chat_id."""

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = {}

    def is_allowed(self, key: str) -> bool:
        """Check if a request is allowed and record it if so."""
        now = time.time()
        cutoff = now - self.window_seconds

        if key not in self._requests:
            self._requests[key] = []

        # Prune expired entries
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]

        if len(self._requests[key]) >= self.max_requests:
            return False

        self._requests[key].append(now)
        return True


# ─── Telegram Service ────────────────────────────────────────────────────────

class TelegramService:
    """Internal service for sending Telegram notifications."""

    def __init__(self):
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.default_chat_id = TELEGRAM_CHAT_ID
        self.ceo_chat_id = TELEGRAM_CEO_CHAT_ID or TELEGRAM_CHAT_ID
        self.rate_limiter = SlidingWindowRateLimiter(
            max_requests=TELEGRAM_RATE_LIMIT_PER_MIN,
            window_seconds=60,
        )

    async def send_message(
        self,
        text: str,
        chat_id: Optional[str] = None,
        parse_mode: Literal["HTML"] = "HTML",
    ) -> TelegramSendResult:
        """Send a message via Telegram Bot API."""
        target_chat_id = chat_id or self.default_chat_id

        # Validate length before sanitizing
        if len(text) > MAX_MESSAGE_LENGTH:
            raise TelegramMessageTooLongError(
                f"Mensaje excede {MAX_MESSAGE_LENGTH} caracteres ({len(text)})"
            )

        # Rate limit check
        if not self.rate_limiter.is_allowed(target_chat_id):
            raise TelegramRateLimitError(
                f"Rate limit exceeded for chat_id {target_chat_id}. Retry after 60s"
            )

        # Sanitize HTML
        sanitized_text = sanitize_html(text)

        # Send to Telegram API
        url = f"{TELEGRAM_API_BASE}/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": target_chat_id,
            "text": sanitized_text,
            "parse_mode": parse_mode,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                data = response.json()

                if data.get("ok"):
                    msg_id = data.get("result", {}).get("message_id")
                    logger.info(f"Telegram message sent: chat_id={target_chat_id}, message_id={msg_id}")
                    return TelegramSendResult(ok=True, message_id=msg_id)
                else:
                    error_desc = data.get("description", "Unknown error")
                    logger.error(f"Telegram API error: {error_desc}")
                    return TelegramSendResult(ok=False, error=error_desc)

        except httpx.HTTPError as e:
            logger.error(f"Telegram HTTP error: {e}")
            return TelegramSendResult(ok=False, error=str(e))

    async def send_cold_call_assignment(
        self,
        vendedor: str,
        clientes: list[str],
        chat_id: Optional[str] = None,
    ) -> TelegramSendResult:
        """Send grouped cold call assignment notification."""
        if clientes:
            client_list = "\n".join(f"  • {c}" for c in clientes)
            text = (
                f"<b>📞 Asignación de Llamadas Frías</b>\n\n"
                f"<b>Vendedor:</b> {vendedor}\n"
                f"<b>Clientes asignados ({len(clientes)}):</b>\n{client_list}"
            )
        else:
            text = (
                f"<b>📞 Asignación de Llamadas Frías</b>\n\n"
                f"<b>Vendedor:</b> {vendedor}\n"
                f"<i>Sin clientes asignados</i>"
            )

        return await self.send_message(text, chat_id=chat_id)

    async def send_ceo_alert(
        self,
        titulo: str,
        detalle: str,
    ) -> TelegramSendResult:
        """Send critical alert to CEO chat."""
        text = (
            f"🚨 <b>ALERTA: {titulo}</b>\n\n"
            f"{detalle}"
        )
        return await self.send_message(text, chat_id=self.ceo_chat_id)


# ─── Singleton ────────────────────────────────────────────────────────────────

telegram_service = TelegramService()
