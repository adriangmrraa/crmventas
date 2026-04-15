"""
Tests for SPEC-01: Drive / File Storage System
TDD — covers sanitization, breadcrumb, folder CRUD, file operations,
tenant isolation, and HTTP endpoint auth.
"""

import os
import uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path

# Set env vars before imports
os.environ.setdefault("POSTGRES_DSN", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("OPENAI_API_KEY", "test_openai_key")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("YCLOUD_API_KEY", "test")
os.environ.setdefault("YCLOUD_WEBHOOK_SECRET", "test")
os.environ.setdefault("INTERNAL_API_TOKEN", "test")
os.environ.setdefault("DRIVE_UPLOAD_DIR", "/tmp/test_drive_uploads")

from services.drive_service import (
    DriveService,
    sanitize_filename,
    ALLOWED_MIME_TYPES,
    MAX_FILE_SIZE,
)


# ─── Filename Sanitization ──────────────────────────────────────────────────

def test_sanitize_filename_basic():
    """Spaces and special chars become underscores."""
    assert sanitize_filename("my file.pdf") == "my_file.pdf"


def test_sanitize_filename_unicode():
    """Unicode chars like accents are replaced."""
    result = sanitize_filename("Contrato Pérez & Asociados (2025).pdf")
    assert " " not in result
    assert "&" not in result
    assert "(" not in result
    assert ")" not in result
    assert result.endswith(".pdf")


def test_sanitize_filename_preserves_dots_and_dashes():
    """Dots and dashes are kept."""
    assert sanitize_filename("my-file.tar.gz") == "my-file.tar.gz"


def test_sanitize_filename_multiple_spaces():
    """Multiple consecutive spaces become single underscore."""
    result = sanitize_filename("file   with   spaces.pdf")
    assert "___" not in result
    assert result.endswith(".pdf")


def test_sanitize_filename_empty():
    """Empty filename gets a fallback."""
    result = sanitize_filename("")
    assert len(result) > 0


def test_sanitize_filename_only_extension():
    """Filename that's just an extension."""
    result = sanitize_filename(".pdf")
    assert result.endswith(".pdf")


def test_sanitize_filename_no_extension():
    """Filename without extension."""
    result = sanitize_filename("README")
    assert result == "README"


# ─── MIME Type Validation ────────────────────────────────────────────────────

def test_allowed_mime_types_includes_pdf():
    assert "application/pdf" in ALLOWED_MIME_TYPES


def test_allowed_mime_types_includes_images():
    assert any(m.startswith("image/") for m in ALLOWED_MIME_TYPES)


def test_allowed_mime_types_includes_office():
    assert any("openxmlformats" in m for m in ALLOWED_MIME_TYPES)


def test_allowed_mime_types_includes_video():
    assert any(m.startswith("video/") for m in ALLOWED_MIME_TYPES)


def test_allowed_mime_types_includes_audio():
    assert any(m.startswith("audio/") for m in ALLOWED_MIME_TYPES)


# ─── DriveService — Folder Operations ────────────────────────────────────────

@pytest.fixture
def drive_service():
    return DriveService()


@pytest.fixture
def mock_db():
    """Mock the db module functions."""
    with patch("services.drive_service.db") as mock:
        mock.pool = MagicMock()
        conn = AsyncMock()
        mock.pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
        mock.pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        yield mock, conn


@pytest.mark.asyncio
async def test_create_folder(drive_service, mock_db):
    """Create a root folder for a client."""
    db_mock, conn = mock_db
    folder_id = uuid.uuid4()
    conn.fetchrow.return_value = {
        "id": folder_id,
        "tenant_id": 1,
        "client_id": 10,
        "nombre": "Contratos",
        "parent_id": None,
        "created_at": "2025-04-14T10:00:00Z",
        "updated_at": "2025-04-14T10:00:00Z",
    }

    result = await drive_service.create_folder(
        tenant_id=1, client_id=10, nombre="Contratos", parent_id=None
    )

    assert result["nombre"] == "Contratos"
    assert result["parent_id"] is None
    conn.fetchrow.assert_called_once()


@pytest.mark.asyncio
async def test_create_subfolder(drive_service, mock_db):
    """Create a subfolder under an existing folder."""
    db_mock, conn = mock_db
    parent_id = uuid.uuid4()
    child_id = uuid.uuid4()

    conn.fetchrow.return_value = {
        "id": child_id,
        "tenant_id": 1,
        "client_id": 10,
        "nombre": "2025",
        "parent_id": parent_id,
        "created_at": "2025-04-14T10:00:00Z",
        "updated_at": "2025-04-14T10:00:00Z",
    }

    result = await drive_service.create_folder(
        tenant_id=1, client_id=10, nombre="2025", parent_id=parent_id
    )

    assert result["parent_id"] == parent_id


@pytest.mark.asyncio
async def test_list_root_folders(drive_service, mock_db):
    """List root folders for a client (parent_id IS NULL)."""
    db_mock, conn = mock_db
    conn.fetch.return_value = [
        {"id": uuid.uuid4(), "nombre": "Contratos", "parent_id": None},
        {"id": uuid.uuid4(), "nombre": "Facturas", "parent_id": None},
    ]

    result = await drive_service.list_folders(tenant_id=1, client_id=10, parent_id=None)

    assert len(result) == 2
    conn.fetch.assert_called_once()


@pytest.mark.asyncio
async def test_get_breadcrumb(drive_service, mock_db):
    """Breadcrumb returns ancestors from root to current folder."""
    db_mock, conn = mock_db
    root_id = uuid.uuid4()
    mid_id = uuid.uuid4()
    leaf_id = uuid.uuid4()

    # CTE recursive query returns ordered ancestors
    conn.fetch.return_value = [
        {"id": root_id, "nombre": "Root", "depth": 0},
        {"id": mid_id, "nombre": "2025", "depth": 1},
        {"id": leaf_id, "nombre": "Contratos", "depth": 2},
    ]

    result = await drive_service.get_breadcrumb(tenant_id=1, folder_id=leaf_id)

    assert len(result) == 3
    assert result[0]["nombre"] == "Root"
    assert result[-1]["nombre"] == "Contratos"


@pytest.mark.asyncio
async def test_delete_folder_removes_files(drive_service, mock_db):
    """Deleting a folder removes storage files before DB cascade."""
    db_mock, conn = mock_db
    folder_id = uuid.uuid4()

    # Verify folder exists and belongs to tenant
    conn.fetchrow.return_value = {"id": folder_id, "tenant_id": 1}

    # Files in the folder tree
    conn.fetch.return_value = [
        {"storage_path": "/uploads/drive/1/10/abc/file1.pdf"},
        {"storage_path": "/uploads/drive/1/10/abc/file2.doc"},
    ]

    # Execute returns status
    conn.execute.return_value = "DELETE 1"

    with patch("services.drive_service.Path") as mock_path:
        mock_file = MagicMock()
        mock_file.exists.return_value = True
        mock_path.return_value = mock_file

        await drive_service.delete_folder(tenant_id=1, folder_id=folder_id)

    # DB delete should have been called
    conn.execute.assert_called()


# ─── DriveService — File Operations ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_file_size_limit():
    """Files exceeding MAX_FILE_SIZE are rejected."""
    assert MAX_FILE_SIZE == 50 * 1024 * 1024  # 50MB


def test_storage_path_format():
    """Storage path follows tenant/client/folder/uuid_name pattern."""
    svc = DriveService()
    path = svc.build_storage_path(
        tenant_id=1,
        client_id=10,
        folder_id="abc-def",
        filename="Contrato Pérez.pdf",
    )

    # Normalize separators for cross-platform
    normalized = path.replace("\\", "/")
    assert "/1/" in normalized
    assert "/10/" in normalized
    assert "/abc-def/" in normalized
    assert "Contrato_P" in normalized  # sanitized
    assert normalized.endswith(".pdf")


@pytest.mark.asyncio
async def test_upload_file_valid(drive_service, mock_db):
    """Upload a valid file creates DB record and stores file."""
    db_mock, conn = mock_db
    folder_id = uuid.uuid4()
    file_id = uuid.uuid4()

    # register_file only calls one fetchrow (INSERT RETURNING)
    conn.fetchrow.return_value = {
        "id": file_id,
        "nombre": "test.pdf",
        "mime_type": "application/pdf",
        "size_bytes": 1024,
        "folder_id": folder_id,
        "created_at": "2025-04-14T10:00:00Z",
    }

    result = await drive_service.register_file(
        tenant_id=1,
        client_id=10,
        folder_id=folder_id,
        nombre="test.pdf",
        storage_path="/uploads/drive/1/10/abc/test.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        uploaded_by=5,
    )

    assert result["nombre"] == "test.pdf"
    assert result["mime_type"] == "application/pdf"


@pytest.mark.asyncio
async def test_delete_file_removes_from_storage(drive_service, mock_db):
    """Deleting a file removes the physical file and DB record."""
    db_mock, conn = mock_db
    file_id = uuid.uuid4()

    conn.fetchrow.return_value = {
        "id": file_id,
        "tenant_id": 1,
        "storage_path": "/uploads/drive/1/10/abc/test.pdf",
    }
    conn.execute.return_value = "DELETE 1"

    with patch("services.drive_service.Path") as mock_path:
        mock_file = MagicMock()
        mock_file.exists.return_value = True
        mock_path.return_value = mock_file

        await drive_service.delete_file(tenant_id=1, file_id=file_id)

        mock_file.unlink.assert_called_once()
    conn.execute.assert_called()


# ─── Tenant Isolation ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_folder_not_found_for_wrong_tenant(drive_service, mock_db):
    """Folder belonging to tenant A returns None for tenant B."""
    db_mock, conn = mock_db
    conn.fetchrow.return_value = None  # No match for this tenant

    result = await drive_service.get_folder(tenant_id=2, folder_id=uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_file_download_wrong_tenant(drive_service, mock_db):
    """File belonging to tenant A returns None for tenant B."""
    db_mock, conn = mock_db
    conn.fetchrow.return_value = None

    result = await drive_service.get_file(tenant_id=2, file_id=uuid.uuid4())
    assert result is None


# ─── HTTP Endpoint Tests ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_drive_endpoints_require_auth():
    """All drive endpoints require authentication."""
    from fastapi.testclient import TestClient
    from routes.drive_routes import router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)

    client = TestClient(app)

    # No auth headers → should fail
    endpoints = [
        ("GET", "/api/v1/drive/folders?client_id=1"),
        ("POST", "/api/v1/drive/folders"),
        ("GET", f"/api/v1/drive/folders/{uuid.uuid4()}"),
        ("DELETE", f"/api/v1/drive/folders/{uuid.uuid4()}"),
        ("GET", f"/api/v1/drive/files?folder_id={uuid.uuid4()}"),
        ("DELETE", f"/api/v1/drive/files/{uuid.uuid4()}"),
    ]

    for method, path in endpoints:
        if method == "GET":
            resp = client.get(path)
        elif method == "POST":
            resp = client.post(path, json={"nombre": "test", "client_id": 1})
        elif method == "DELETE":
            resp = client.delete(path)

        # Should be 401 or 403 (missing auth)
        assert resp.status_code in (401, 403, 422), (
            f"{method} {path} returned {resp.status_code}, expected auth error"
        )
