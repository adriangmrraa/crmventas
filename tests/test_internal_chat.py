"""
Tests for SPEC-04: Internal Team Chat
Covers DM canonical ID, message sending, access control, tenant isolation.
"""

import os
import uuid
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

os.environ.setdefault("POSTGRES_DSN", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("OPENAI_API_KEY", "test_openai_key")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("YCLOUD_API_KEY", "test")
os.environ.setdefault("YCLOUD_WEBHOOK_SECRET", "test")
os.environ.setdefault("INTERNAL_API_TOKEN", "test")

from services.internal_chat_service import (
    InternalChatService,
    dm_canal_id,
    FIXED_CHANNELS,
)


# ─── DM Canonical ID ─────────────────────────────────────────────────────────

def test_dm_canal_id_idempotent():
    """SC-02: Same canal_id regardless of who initiates."""
    a = "aaaa-1111"
    b = "zzzz-9999"
    assert dm_canal_id(a, b) == dm_canal_id(b, a)


def test_dm_canal_id_format():
    """DM canal_id follows dm_<min>_<max> pattern."""
    result = dm_canal_id("bbb", "aaa")
    assert result == "dm_aaa_bbb"


def test_dm_canal_id_same_user():
    """DM with self produces valid canonical ID."""
    result = dm_canal_id("abc", "abc")
    assert result == "dm_abc_abc"


# ─── Fixed Channels ──────────────────────────────────────────────────────────

def test_fixed_channels():
    assert "general" in FIXED_CHANNELS
    assert "ventas" in FIXED_CHANNELS
    assert "operaciones" in FIXED_CHANNELS
    assert len(FIXED_CHANNELS) == 3


# ─── Service Tests ────────────────────────────────────────────────────────────

@pytest.fixture
def service():
    return InternalChatService()


@pytest.fixture
def mock_db():
    with patch("services.internal_chat_service.db") as mock:
        mock.pool = MagicMock()
        conn = AsyncMock()
        mock.pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
        mock.pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        yield mock, conn


@pytest.fixture
def mock_sio():
    with patch("services.internal_chat_service.sio") as mock:
        mock.emit = AsyncMock()
        mock.enter_room = AsyncMock()
        mock.leave_room = AsyncMock()
        yield mock


@pytest.mark.asyncio
async def test_enviar_mensaje_canal(service, mock_db, mock_sio):
    """SC-01: Send message to fixed channel."""
    db_mock, conn = mock_db
    msg_id = uuid.uuid4()
    conn.fetchrow.return_value = {
        "id": msg_id,
        "canal_id": "general",
        "autor_id": "user-1",
        "autor_nombre": "Juan",
        "autor_rol": "vendedor",
        "contenido": "Hola equipo",
        "tipo": "mensaje",
        "metadata": None,
        "created_at": "2025-04-14T10:00:00Z",
    }

    result = await service.enviar_mensaje(
        tenant_id=1,
        canal_id="general",
        autor_id="user-1",
        autor_nombre="Juan",
        autor_rol="vendedor",
        contenido="Hola equipo",
    )

    assert result["contenido"] == "Hola equipo"
    assert result["canal_id"] == "general"

    # Socket.IO emission
    mock_sio.emit.assert_called()
    call_args = mock_sio.emit.call_args_list[0]
    assert call_args[0][0] == "chat:nuevo_mensaje"
    assert "chat:1:general" in str(call_args)


@pytest.mark.asyncio
async def test_enviar_mensaje_dm_updates_badge(service, mock_db, mock_sio):
    """SC-01 DM: Send DM message updates unread badge."""
    db_mock, conn = mock_db
    msg_id = uuid.uuid4()
    conn.fetchrow.side_effect = [
        {  # Insert message
            "id": msg_id, "canal_id": "dm_aaa_bbb", "autor_id": "aaa",
            "autor_nombre": "Ana", "autor_rol": "vendedor",
            "contenido": "Hola", "tipo": "mensaje", "metadata": None,
            "created_at": "2025-04-14T10:00:00Z",
        },
    ]
    conn.execute.return_value = "INSERT 0 1"
    conn.fetchval.return_value = 3  # new unread count

    result = await service.enviar_mensaje(
        tenant_id=1,
        canal_id="dm_aaa_bbb",
        autor_id="aaa",
        autor_nombre="Ana",
        autor_rol="vendedor",
        contenido="Hola",
    )

    # Should emit both nuevo_mensaje and dm_badge_update
    assert mock_sio.emit.call_count >= 2
    events = [c[0][0] for c in mock_sio.emit.call_args_list]
    assert "chat:nuevo_mensaje" in events
    assert "chat:dm_badge_update" in events


@pytest.mark.asyncio
async def test_get_mensajes_dm_forbidden(service, mock_db):
    """SC-03: Vendedor cannot see DM they're not part of."""
    db_mock, conn = mock_db

    result = await service.get_mensajes(
        tenant_id=1,
        canal_id="dm_xxx_yyy",
        user_id="zzz",  # Not a participant
        user_role="vendedor",
    )

    assert result is None  # Forbidden


@pytest.mark.asyncio
async def test_get_mensajes_dm_ceo_allowed(service, mock_db):
    """SC-04: CEO can see any DM in their tenant."""
    db_mock, conn = mock_db
    conn.fetch.return_value = [
        {"id": uuid.uuid4(), "canal_id": "dm_xxx_yyy", "autor_id": "xxx",
         "autor_nombre": "X", "autor_rol": "vendedor", "contenido": "msg",
         "tipo": "mensaje", "metadata": None, "created_at": "2025-01-01"},
    ]

    result = await service.get_mensajes(
        tenant_id=1,
        canal_id="dm_xxx_yyy",
        user_id="ceo-user",
        user_role="ceo",
    )

    assert result is not None
    assert len(result) == 1


@pytest.mark.asyncio
async def test_message_length_limit():
    """SC-06: Messages > 2000 chars should be rejected by validation."""
    # This is enforced at the route level (Pydantic max_length=2000)
    from routes.internal_chat_routes import SendMessageRequest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        SendMessageRequest(
            canal_id="general",
            contenido="A" * 2001,
            tipo="mensaje",
        )


@pytest.mark.asyncio
async def test_marcar_dm_leido(service, mock_db, mock_sio):
    """SC-07: Mark DM as read clears badge."""
    db_mock, conn = mock_db
    conn.execute.return_value = "UPDATE 1"

    await service.marcar_dm_leido(
        tenant_id=1, canal_id="dm_aaa_bbb", user_id="bbb"
    )

    conn.execute.assert_called_once()
    mock_sio.emit.assert_called_once()
    assert mock_sio.emit.call_args[0][0] == "chat:badge_clear"


@pytest.mark.asyncio
async def test_iniciar_dm_upsert(service, mock_db):
    """SC-02: Initiate DM creates conversation with canonical ID."""
    db_mock, conn = mock_db
    conn.execute.return_value = "INSERT 0 1"

    canal_id = await service.iniciar_dm(
        tenant_id=1, user_id="bbb", destinatario_id="aaa"
    )

    assert canal_id == "dm_aaa_bbb"  # Sorted
    conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_enviar_notificacion_llamada(service, mock_db, mock_sio):
    """SC-08: Call notification in #general with metadata."""
    db_mock, conn = mock_db
    msg_id = uuid.uuid4()
    conn.fetchrow.return_value = {
        "id": msg_id, "canal_id": "general", "autor_id": "user-1",
        "autor_nombre": "Juan", "autor_rol": "vendedor",
        "contenido": "Se agendo una llamada con ACME",
        "tipo": "notificacion_llamada",
        "metadata": {"cliente_nombre": "ACME", "descripcion": "Demo", "url": "/leads/123"},
        "created_at": "2025-04-14T10:00:00Z",
    }

    result = await service.enviar_mensaje(
        tenant_id=1,
        canal_id="general",
        autor_id="user-1",
        autor_nombre="Juan",
        autor_rol="vendedor",
        contenido="Se agendo una llamada con ACME",
        tipo="notificacion_llamada",
        metadata={"cliente_nombre": "ACME", "descripcion": "Demo", "url": "/leads/123"},
    )

    assert result["tipo"] == "notificacion_llamada"
    assert result["metadata"]["cliente_nombre"] == "ACME"


@pytest.mark.asyncio
async def test_ensure_channels_exist(service, mock_db):
    """Fixed channels are created for the tenant."""
    db_mock, conn = mock_db
    conn.execute.return_value = "INSERT 0 1"

    await service.ensure_channels_exist(tenant_id=1)

    assert conn.execute.call_count == 3  # general, ventas, operaciones
