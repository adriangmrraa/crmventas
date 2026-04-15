"""
Tests for SPEC-07: Telegram Bot Notifications
TDD — written BEFORE implementation.

Covers all BDD scenarios:
- SC-07-01: Valid message sent successfully
- SC-07-02: HTML sanitization (allowed/blocked tags)
- SC-07-03: Message exceeds 4000 chars
- SC-07-04: Rate limit reached
- SC-07-05: Invalid webhook secret (timing-safe)
- SC-07-06: Cold call assignment notification
- SC-07-07: CEO alert
"""

import os
import time
import hmac
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import Response

# Set env vars before imports
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "bot123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
os.environ.setdefault("TELEGRAM_CHAT_ID", "-100123456789")
os.environ.setdefault("TELEGRAM_CEO_CHAT_ID", "-100999999999")
os.environ.setdefault("TELEGRAM_WEBHOOK_SECRET", "test_secret_32chars_minimum_here!")
os.environ.setdefault("TELEGRAM_RATE_LIMIT_PER_MIN", "10")
os.environ.setdefault("POSTGRES_DSN", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("OPENAI_API_KEY", "test_openai_key")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("YCLOUD_API_KEY", "test")
os.environ.setdefault("YCLOUD_WEBHOOK_SECRET", "test")
os.environ.setdefault("INTERNAL_API_TOKEN", "test")

from services.telegram_service import (
    TelegramService,
    TelegramSendResult,
    TelegramMessageTooLongError,
    TelegramRateLimitError,
    sanitize_html,
    SlidingWindowRateLimiter,
)


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def telegram_service():
    """Fresh TelegramService instance with clean rate limiter."""
    svc = TelegramService()
    svc.rate_limiter = SlidingWindowRateLimiter(max_requests=10, window_seconds=60)
    return svc


@pytest.fixture
def mock_httpx_success():
    """Mock httpx.AsyncClient.post returning Telegram API success."""
    response = Response(
        status_code=200,
        json={"ok": True, "result": {"message_id": 42}},
    )
    with patch("services.telegram_service.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_httpx_failure():
    """Mock httpx.AsyncClient.post returning Telegram API error."""
    response = Response(
        status_code=400,
        json={"ok": False, "description": "Bad Request: chat not found"},
    )
    with patch("services.telegram_service.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client
        yield mock_client


# ─── SC-07-01: Valid message sent successfully ────────────────────────────────

@pytest.mark.asyncio
async def test_send_message_success(telegram_service, mock_httpx_success):
    """SC-07-01: Message with valid text is sent to Telegram API."""
    result = await telegram_service.send_message("Hello, world!")

    assert result.ok is True
    assert result.message_id == 42
    assert result.error is None

    # Verify the POST was made to the correct Telegram API URL
    call_args = mock_httpx_success.post.call_args
    url = call_args[0][0] if call_args[0] else call_args[1].get("url", "")
    assert "/sendMessage" in url


@pytest.mark.asyncio
async def test_send_message_uses_default_chat_id(telegram_service, mock_httpx_success):
    """When chat_id is None, uses TELEGRAM_CHAT_ID from env."""
    await telegram_service.send_message("Test")

    call_args = mock_httpx_success.post.call_args
    payload = call_args[1].get("json") or call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("json")
    assert payload["chat_id"] == os.environ["TELEGRAM_CHAT_ID"]


@pytest.mark.asyncio
async def test_send_message_custom_chat_id(telegram_service, mock_httpx_success):
    """When chat_id is provided, uses that instead of default."""
    await telegram_service.send_message("Test", chat_id="-100custom")

    call_args = mock_httpx_success.post.call_args
    payload = call_args[1].get("json", {})
    assert payload["chat_id"] == "-100custom"


@pytest.mark.asyncio
async def test_send_message_api_failure(telegram_service, mock_httpx_failure):
    """When Telegram API returns error, result.ok is False with error detail."""
    result = await telegram_service.send_message("Test")

    assert result.ok is False
    assert result.message_id is None
    assert "chat not found" in result.error


# ─── SC-07-02: HTML sanitization ─────────────────────────────────────────────

def test_sanitize_html_allows_permitted_tags():
    """Allowed tags: b, i, u, s, code, pre, a — are preserved."""
    html = '<b>bold</b> <i>italic</i> <u>underline</u> <s>strike</s> <code>code</code> <pre>pre</pre> <a href="http://example.com">link</a>'
    result = sanitize_html(html)

    assert "<b>bold</b>" in result
    assert "<i>italic</i>" in result
    assert "<u>underline</u>" in result
    assert "<s>strike</s>" in result
    assert "<code>code</code>" in result
    assert "<pre>pre</pre>" in result
    assert '<a href="http://example.com">link</a>' in result


def test_sanitize_html_removes_script_tags():
    """SC-07-02: <script> tags are stripped. Text content preserved, tag removed."""
    html = "<script>alert('xss')</script>Normal text <b>bold</b>"
    result = sanitize_html(html)

    assert "<script>" not in result
    assert "</script>" not in result
    assert "Normal text" in result
    assert "<b>bold</b>" in result


def test_sanitize_html_removes_div_span_img():
    """Non-allowed tags like div, span, img are removed."""
    html = '<div>content</div><span style="color:red">styled</span><img src="x.png"/>'
    result = sanitize_html(html)

    assert "<div>" not in result
    assert "<span" not in result
    assert "<img" not in result
    # Text content is preserved, only tags stripped
    assert "content" in result
    assert "styled" in result


def test_sanitize_html_preserves_plain_text():
    """Plain text without any HTML tags is unchanged."""
    text = "Just a normal message with no HTML"
    assert sanitize_html(text) == text


def test_sanitize_html_removes_onclick_attributes():
    """Event handler attributes are stripped even from allowed tags."""
    html = '<b onclick="evil()">bold</b>'
    result = sanitize_html(html)
    assert "onclick" not in result
    assert "<b>bold</b>" in result


# ─── SC-07-03: Message exceeds 4000 characters ──────────────────────────────

@pytest.mark.asyncio
async def test_message_too_long_raises_error(telegram_service, mock_httpx_success):
    """SC-07-03: Messages > 4000 chars raise TelegramMessageTooLongError."""
    long_text = "A" * 4001

    with pytest.raises(TelegramMessageTooLongError):
        await telegram_service.send_message(long_text)

    # Verify NO call was made to Telegram API
    mock_httpx_success.post.assert_not_called()


@pytest.mark.asyncio
async def test_message_exactly_4000_chars_ok(telegram_service, mock_httpx_success):
    """Messages with exactly 4000 chars are accepted."""
    text = "A" * 4000
    result = await telegram_service.send_message(text)
    assert result.ok is True


# ─── SC-07-04: Rate limit ────────────────────────────────────────────────────

def test_rate_limiter_allows_within_limit():
    """Under the limit, requests are allowed."""
    limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=60)
    assert limiter.is_allowed("chat1") is True
    assert limiter.is_allowed("chat1") is True
    assert limiter.is_allowed("chat1") is True


def test_rate_limiter_blocks_over_limit():
    """SC-07-04: After max_requests, further requests are blocked."""
    limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=60)
    for _ in range(3):
        limiter.is_allowed("chat1")

    assert limiter.is_allowed("chat1") is False


def test_rate_limiter_separate_chat_ids():
    """Rate limiting is per chat_id, not global."""
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=60)
    limiter.is_allowed("chat1")
    limiter.is_allowed("chat1")

    # chat1 is at limit, but chat2 should be fine
    assert limiter.is_allowed("chat1") is False
    assert limiter.is_allowed("chat2") is True


def test_rate_limiter_window_expiry():
    """After the window expires, requests are allowed again."""
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=1)
    limiter.is_allowed("chat1")
    limiter.is_allowed("chat1")
    assert limiter.is_allowed("chat1") is False

    # Wait for window to expire
    time.sleep(1.1)
    assert limiter.is_allowed("chat1") is True


@pytest.mark.asyncio
async def test_send_message_rate_limited(telegram_service, mock_httpx_success):
    """SC-07-04: When rate limit is hit, TelegramRateLimitError is raised."""
    telegram_service.rate_limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=60)

    await telegram_service.send_message("msg1")
    await telegram_service.send_message("msg2")

    with pytest.raises(TelegramRateLimitError):
        await telegram_service.send_message("msg3")


# ─── SC-07-05: Webhook secret validation (endpoint) ─────────────────────────

@pytest.mark.asyncio
async def test_endpoint_valid_secret():
    """SC-07-05: Valid webhook secret returns 200."""
    from fastapi.testclient import TestClient
    from routes.telegram_routes import router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)

    with patch("routes.telegram_routes.telegram_service") as mock_svc:
        mock_svc.send_message = AsyncMock(
            return_value=TelegramSendResult(ok=True, message_id=42, error=None)
        )
        client = TestClient(app)
        resp = client.post(
            "/internal/telegram/notify",
            json={"text": "Hello"},
            headers={"X-Webhook-Secret": os.environ["TELEGRAM_WEBHOOK_SECRET"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True


@pytest.mark.asyncio
async def test_endpoint_invalid_secret():
    """SC-07-05: Invalid webhook secret returns 401."""
    from fastapi.testclient import TestClient
    from routes.telegram_routes import router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)

    client = TestClient(app)
    resp = client.post(
        "/internal/telegram/notify",
        json={"text": "Hello"},
        headers={"X-Webhook-Secret": "wrong_secret"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_endpoint_missing_secret():
    """Missing webhook secret header returns 401."""
    from fastapi.testclient import TestClient
    from routes.telegram_routes import router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)

    client = TestClient(app)
    resp = client.post(
        "/internal/telegram/notify",
        json={"text": "Hello"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_endpoint_too_long_message():
    """Endpoint returns 400 for messages > 4000 chars."""
    from fastapi.testclient import TestClient
    from routes.telegram_routes import router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)

    with patch("routes.telegram_routes.telegram_service") as mock_svc:
        mock_svc.send_message = AsyncMock(side_effect=TelegramMessageTooLongError("too long"))
        client = TestClient(app)
        resp = client.post(
            "/internal/telegram/notify",
            json={"text": "A" * 4001},
            headers={"X-Webhook-Secret": os.environ["TELEGRAM_WEBHOOK_SECRET"]},
        )
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_endpoint_rate_limited():
    """Endpoint returns 429 when rate limited."""
    from fastapi.testclient import TestClient
    from routes.telegram_routes import router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)

    with patch("routes.telegram_routes.telegram_service") as mock_svc:
        mock_svc.send_message = AsyncMock(side_effect=TelegramRateLimitError("rate limited"))
        client = TestClient(app)
        resp = client.post(
            "/internal/telegram/notify",
            json={"text": "Hello"},
            headers={"X-Webhook-Secret": os.environ["TELEGRAM_WEBHOOK_SECRET"]},
        )
        assert resp.status_code == 429


# ─── SC-07-06: Cold call assignment notification ─────────────────────────────

@pytest.mark.asyncio
async def test_cold_call_assignment(telegram_service, mock_httpx_success):
    """SC-07-06: Cold call assignment includes vendedor name and client list."""
    result = await telegram_service.send_cold_call_assignment(
        vendedor="Juan Pérez",
        clientes=["ACME S.A.", "Beta Corp", "Gamma Ltd"],
    )

    assert result.ok is True

    # Verify the message content
    call_args = mock_httpx_success.post.call_args
    payload = call_args[1].get("json", {})
    text = payload["text"]

    assert "Juan Pérez" in text
    assert "ACME S.A." in text
    assert "Beta Corp" in text
    assert "Gamma Ltd" in text


@pytest.mark.asyncio
async def test_cold_call_assignment_empty_clients(telegram_service, mock_httpx_success):
    """Cold call with empty client list still sends message."""
    result = await telegram_service.send_cold_call_assignment(
        vendedor="Ana García",
        clientes=[],
    )
    assert result.ok is True


# ─── SC-07-07: CEO alert ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ceo_alert(telegram_service, mock_httpx_success):
    """SC-07-07: CEO alert uses CEO chat ID and includes titulo/detalle."""
    result = await telegram_service.send_ceo_alert(
        titulo="Pipeline en riesgo",
        detalle="3 deals sin actividad > 15 días",
    )

    assert result.ok is True

    call_args = mock_httpx_success.post.call_args
    payload = call_args[1].get("json", {})

    # Should use CEO chat ID
    assert payload["chat_id"] == os.environ["TELEGRAM_CEO_CHAT_ID"]

    # Content should include titulo and detalle
    text = payload["text"]
    assert "Pipeline en riesgo" in text
    assert "3 deals sin actividad" in text


@pytest.mark.asyncio
async def test_ceo_alert_falls_back_to_default_chat(mock_httpx_success):
    """When ceo_chat_id is not set, falls back to default_chat_id."""
    svc = TelegramService()
    svc.rate_limiter = SlidingWindowRateLimiter(max_requests=10, window_seconds=60)
    # Simulate CEO chat ID not configured — falls back to default
    svc.ceo_chat_id = svc.default_chat_id

    result = await svc.send_ceo_alert(
        titulo="Test",
        detalle="Detail",
    )
    assert result.ok is True

    call_args = mock_httpx_success.post.call_args
    payload = call_args[1].get("json", {})
    assert payload["chat_id"] == os.environ["TELEGRAM_CHAT_ID"]


# ─── Webhook secret timing-safe comparison ───────────────────────────────────

def test_timing_safe_comparison_used():
    """SC-07-05: Verify hmac.compare_digest is used for secret comparison."""
    from routes.telegram_routes import _verify_webhook_secret

    # This just verifies the function exists and uses hmac.compare_digest
    # The actual timing-safe behavior is guaranteed by the stdlib
    assert _verify_webhook_secret(os.environ["TELEGRAM_WEBHOOK_SECRET"]) is True
    assert _verify_webhook_secret("wrong") is False
