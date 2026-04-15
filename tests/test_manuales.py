"""Tests for SPEC-03: Knowledge Base / Manuales"""
import os, uuid, pytest
from unittest.mock import AsyncMock, patch, MagicMock

os.environ.setdefault("POSTGRES_DSN", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("YCLOUD_API_KEY", "test")
os.environ.setdefault("YCLOUD_WEBHOOK_SECRET", "test")
os.environ.setdefault("INTERNAL_API_TOKEN", "test")

from services.manuales_service import ManualesService, VALID_CATEGORIAS

@pytest.fixture
def svc(): return ManualesService()

@pytest.fixture
def mock_db():
    with patch("services.manuales_service.db") as m:
        m.pool = MagicMock()
        conn = AsyncMock()
        m.pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
        m.pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        yield m, conn

def test_valid_categorias():
    assert len(VALID_CATEGORIAS) == 6
    assert "general" in VALID_CATEGORIAS
    assert "guion_ventas" in VALID_CATEGORIAS
    assert "objeciones" in VALID_CATEGORIAS
    assert "onboarding" in VALID_CATEGORIAS

@pytest.mark.asyncio
async def test_create_manual(svc, mock_db):
    _, conn = mock_db
    mid = uuid.uuid4()
    conn.fetchrow.return_value = {"id": mid, "tenant_id": 1, "titulo": "Guion", "contenido": "# Intro\nTexto", "categoria": "guion_ventas", "autor": "Admin", "created_at": "2025-01-01", "updated_at": "2025-01-01"}
    result = await svc.create(1, "Guion", "# Intro\nTexto", "guion_ventas", "Admin")
    assert result["titulo"] == "Guion"
    assert result["categoria"] == "guion_ventas"

@pytest.mark.asyncio
async def test_list_with_search(svc, mock_db):
    _, conn = mock_db
    conn.fetchval.return_value = 2
    conn.fetch.return_value = []
    await svc.list(1, q="objeciones")
    call = conn.fetch.call_args[0][0]
    assert "plainto_tsquery" in call

@pytest.mark.asyncio
async def test_get_not_found(svc, mock_db):
    _, conn = mock_db
    conn.fetchrow.return_value = None
    result = await svc.get(1, str(uuid.uuid4()))
    assert result is None

@pytest.mark.asyncio
async def test_delete_success(svc, mock_db):
    _, conn = mock_db
    conn.execute.return_value = "DELETE 1"
    assert await svc.delete(1, str(uuid.uuid4())) is True

@pytest.mark.asyncio
async def test_delete_not_found(svc, mock_db):
    _, conn = mock_db
    conn.execute.return_value = "DELETE 0"
    assert await svc.delete(1, str(uuid.uuid4())) is False

@pytest.mark.asyncio
async def test_update_not_found(svc, mock_db):
    _, conn = mock_db
    conn.fetchrow.return_value = None
    result = await svc.update(1, str(uuid.uuid4()), titulo="New")
    assert result is None
