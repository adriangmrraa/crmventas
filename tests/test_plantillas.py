"""
Tests for SPEC-02: Plantillas de Mensajes
TDD — covers variable extraction, CRUD, tenant isolation, atomic uso_count.
"""

import os
import uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

os.environ.setdefault("POSTGRES_DSN", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("OPENAI_API_KEY", "test_openai_key")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("YCLOUD_API_KEY", "test")
os.environ.setdefault("YCLOUD_WEBHOOK_SECRET", "test")
os.environ.setdefault("INTERNAL_API_TOKEN", "test")

from services.plantillas_service import (
    extract_variables,
    render_preview,
    PlantillasService,
    DuplicateTemplateNameError,
    SAMPLE_DATA,
    VALID_CATEGORIES,
)


# ─── Variable Extraction ─────────────────────────────────────────────────────

def test_extract_variables_basic():
    assert extract_variables("Hola {{nombre}}") == ["nombre"]


def test_extract_variables_multiple():
    assert extract_variables("{{nombre}} de {{empresa}}") == ["nombre", "empresa"]


def test_extract_variables_dedup():
    assert extract_variables("{{nombre}} y {{nombre}}") == ["nombre"]


def test_extract_variables_none():
    assert extract_variables("Sin variables") == []


def test_extract_variables_custom():
    assert extract_variables("Texto {{mi_var_123}}") == ["mi_var_123"]


def test_extract_variables_preserves_order():
    result = extract_variables("{{c}} {{a}} {{b}}")
    assert result == ["c", "a", "b"]


def test_extract_variables_invalid_syntax():
    """Single braces and unclosed braces are NOT variables."""
    assert extract_variables("{name} and {{valid}} and {incomplete") == ["valid"]


# ─── Preview Rendering ───────────────────────────────────────────────────────

def test_render_preview_basic():
    result = render_preview("Hola {{nombre}}, de {{empresa}}")
    assert "Juan" in result
    assert "Soluciones CRM" in result


def test_render_preview_no_variables():
    text = "Texto sin variables"
    assert render_preview(text) == text


def test_render_preview_custom_data():
    result = render_preview("Hola {{nombre}}", {"nombre": "Ana"})
    assert result == "Hola Ana"


def test_render_preview_unknown_variable_unchanged():
    """Unknown variables stay as-is."""
    result = render_preview("Valor: {{custom_var}}")
    assert "{{custom_var}}" in result


# ─── Categories ───────────────────────────────────────────────────────────────

def test_valid_categories():
    assert "whatsapp" in VALID_CATEGORIES
    assert "email" in VALID_CATEGORIES
    assert "seguimiento" in VALID_CATEGORIES
    assert "prospeccion" in VALID_CATEGORIES
    assert "cierre" in VALID_CATEGORIES
    assert len(VALID_CATEGORIES) == 5


# ─── Service CRUD (mocked DB) ────────────────────────────────────────────────

@pytest.fixture
def service():
    return PlantillasService()


@pytest.fixture
def mock_db():
    with patch("services.plantillas_service.db") as mock:
        mock.pool = MagicMock()
        conn = AsyncMock()
        mock.pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
        mock.pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        yield mock, conn


@pytest.mark.asyncio
async def test_create_plantilla(service, mock_db):
    db_mock, conn = mock_db
    pid = uuid.uuid4()
    conn.fetchrow.return_value = {
        "id": pid,
        "nombre": "Saludo WhatsApp",
        "categoria": "whatsapp",
        "contenido": "Hola {{nombre}}, soy de {{empresa}}",
        "variables": ["nombre", "empresa"],
        "uso_count": 0,
        "created_by": None,
        "created_at": "2025-04-14T00:00:00Z",
        "updated_at": "2025-04-14T00:00:00Z",
    }

    result = await service.create(
        tenant_id=1,
        nombre="Saludo WhatsApp",
        categoria="whatsapp",
        contenido="Hola {{nombre}}, soy de {{empresa}}",
    )

    assert result["nombre"] == "Saludo WhatsApp"
    assert result["variables"] == ["nombre", "empresa"]
    assert result["uso_count"] == 0


@pytest.mark.asyncio
async def test_create_duplicate_name(service, mock_db):
    db_mock, conn = mock_db
    conn.fetchrow.side_effect = Exception("idx_plantillas_tenant_nombre")

    with pytest.raises(DuplicateTemplateNameError):
        await service.create(
            tenant_id=1,
            nombre="Duplicado",
            categoria="whatsapp",
            contenido="Texto",
        )


@pytest.mark.asyncio
async def test_list_plantillas(service, mock_db):
    db_mock, conn = mock_db
    conn.fetchval.return_value = 2
    conn.fetch.return_value = [
        {"id": uuid.uuid4(), "nombre": "A", "categoria": "whatsapp",
         "contenido": "...", "variables": [], "uso_count": 5,
         "created_by": None, "created_at": "2025-01-01", "updated_at": "2025-01-01"},
        {"id": uuid.uuid4(), "nombre": "B", "categoria": "email",
         "contenido": "...", "variables": [], "uso_count": 3,
         "created_by": None, "created_at": "2025-01-01", "updated_at": "2025-01-01"},
    ]

    result = await service.list(tenant_id=1)
    assert result["total"] == 2
    assert len(result["items"]) == 2


@pytest.mark.asyncio
async def test_list_with_category_filter(service, mock_db):
    db_mock, conn = mock_db
    conn.fetchval.return_value = 1
    conn.fetch.return_value = [
        {"id": uuid.uuid4(), "nombre": "A", "categoria": "email",
         "contenido": "...", "variables": [], "uso_count": 0,
         "created_by": None, "created_at": "2025-01-01", "updated_at": "2025-01-01"},
    ]

    result = await service.list(tenant_id=1, categoria="email")
    assert result["total"] == 1

    # Verify the SQL includes categoria filter
    call_args = conn.fetch.call_args
    assert "categoria" in call_args[0][0]


@pytest.mark.asyncio
async def test_list_with_search(service, mock_db):
    db_mock, conn = mock_db
    conn.fetchval.return_value = 1
    conn.fetch.return_value = []

    await service.list(tenant_id=1, q="demo")

    # Verify ILIKE search is in the query
    call_args = conn.fetch.call_args
    assert "ILIKE" in call_args[0][0]


@pytest.mark.asyncio
async def test_get_plantilla(service, mock_db):
    db_mock, conn = mock_db
    pid = uuid.uuid4()
    conn.fetchrow.return_value = {
        "id": pid, "nombre": "Test", "categoria": "whatsapp",
        "contenido": "Texto", "variables": [], "uso_count": 0,
        "created_by": None, "created_at": "2025-01-01", "updated_at": "2025-01-01",
    }

    result = await service.get(tenant_id=1, plantilla_id=pid)
    assert result["nombre"] == "Test"


@pytest.mark.asyncio
async def test_get_wrong_tenant(service, mock_db):
    db_mock, conn = mock_db
    conn.fetchrow.return_value = None

    result = await service.get(tenant_id=2, plantilla_id=uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_update_reextracts_variables(service, mock_db):
    db_mock, conn = mock_db
    pid = uuid.uuid4()
    conn.fetchrow.return_value = {
        "id": pid, "nombre": "Updated", "categoria": "email",
        "contenido": "Nuevo {{producto}} por {{precio}}",
        "variables": ["producto", "precio"], "uso_count": 5,
        "created_by": None, "created_at": "2025-01-01", "updated_at": "2025-01-01",
    }

    result = await service.update(
        tenant_id=1,
        plantilla_id=pid,
        nombre="Updated",
        categoria="email",
        contenido="Nuevo {{producto}} por {{precio}}",
    )

    assert "producto" in result["variables"]
    assert "precio" in result["variables"]


@pytest.mark.asyncio
async def test_delete_plantilla(service, mock_db):
    db_mock, conn = mock_db
    conn.execute.return_value = "DELETE 1"

    result = await service.delete(tenant_id=1, plantilla_id=uuid.uuid4())
    assert result is True


@pytest.mark.asyncio
async def test_delete_wrong_tenant(service, mock_db):
    db_mock, conn = mock_db
    conn.execute.return_value = "DELETE 0"

    result = await service.delete(tenant_id=2, plantilla_id=uuid.uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_increment_uso(service, mock_db):
    db_mock, conn = mock_db
    conn.fetchrow.return_value = {"uso_count": 6}

    count = await service.increment_uso(tenant_id=1, plantilla_id=uuid.uuid4())
    assert count == 6

    # Verify atomic update
    call_args = conn.fetchrow.call_args
    assert "uso_count + 1" in call_args[0][0]


@pytest.mark.asyncio
async def test_increment_uso_wrong_tenant(service, mock_db):
    db_mock, conn = mock_db
    conn.fetchrow.return_value = None

    count = await service.increment_uso(tenant_id=2, plantilla_id=uuid.uuid4())
    assert count is None
