"""Tests for SPEC-06: Vendor Tasks"""
import os, uuid, pytest
from unittest.mock import AsyncMock, patch, MagicMock

os.environ.setdefault("POSTGRES_DSN", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("YCLOUD_API_KEY", "test")
os.environ.setdefault("YCLOUD_WEBHOOK_SECRET", "test")
os.environ.setdefault("INTERNAL_API_TOKEN", "test")

from services.vendor_tasks_service import VendorTasksService

@pytest.fixture
def svc(): return VendorTasksService()

@pytest.fixture
def mock_db():
    with patch("services.vendor_tasks_service.db") as m:
        m.pool = MagicMock()
        conn = AsyncMock()
        m.pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
        m.pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        yield m, conn

@pytest.fixture
def mock_sio():
    with patch("services.vendor_tasks_service.sio") as m:
        m.emit = AsyncMock()
        yield m

@pytest.mark.asyncio
async def test_create_task(svc, mock_db, mock_sio):
    _, conn = mock_db
    tid = uuid.uuid4()
    conn.fetchrow.return_value = {"id": tid, "tenant_id": 1, "vendor_id": 42, "created_by": 7, "contenido": "Llamar cliente", "es_tarea": True, "fecha_limite": None, "completada": False, "completada_at": None, "created_at": "2025-01-01T00:00:00Z"}
    result = await svc.create(1, 42, 7, "Llamar cliente", True)
    assert result["es_tarea"] == True
    mock_sio.emit.assert_called_once()

@pytest.mark.asyncio
async def test_create_note_no_socket(svc, mock_db, mock_sio):
    _, conn = mock_db
    conn.fetchrow.return_value = {"id": uuid.uuid4(), "tenant_id": 1, "vendor_id": 42, "created_by": 7, "contenido": "Info", "es_tarea": False, "fecha_limite": None, "completada": False, "completada_at": None, "created_at": "2025-01-01"}
    await svc.create(1, 42, 7, "Info", False)
    mock_sio.emit.assert_not_called()

@pytest.mark.asyncio
async def test_toggle_wrong_vendor(svc, mock_db, mock_sio):
    _, conn = mock_db
    conn.fetchrow.return_value = {"id": uuid.uuid4(), "vendor_id": 99}
    with pytest.raises(PermissionError):
        await svc.toggle_completada(1, str(uuid.uuid4()), 42, True)

@pytest.mark.asyncio
async def test_toggle_not_found(svc, mock_db, mock_sio):
    _, conn = mock_db
    conn.fetchrow.return_value = None
    result = await svc.toggle_completada(1, str(uuid.uuid4()), 42, True)
    assert result is None

@pytest.mark.asyncio
async def test_pending_count(svc, mock_db, mock_sio):
    _, conn = mock_db
    conn.fetchval.return_value = 3
    count = await svc.pending_count(1, 42)
    assert count == 3

@pytest.mark.asyncio
async def test_delete_completed_fails(svc, mock_db, mock_sio):
    _, conn = mock_db
    conn.fetchrow.return_value = {"completada": True}
    with pytest.raises(ValueError):
        await svc.delete(1, str(uuid.uuid4()))
