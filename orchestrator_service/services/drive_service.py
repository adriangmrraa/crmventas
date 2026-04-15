"""
Drive / File Storage Service — SPEC-01
Manages folders and files with multi-tenant isolation.
Storage: local filesystem (swap to S3 via storage_path abstraction).
"""

import os
import re
import uuid
import logging
from pathlib import Path
from typing import Optional

from db import db

logger = logging.getLogger(__name__)

# ─── Configuration ────────────────────────────────────────────────────────────

DRIVE_UPLOAD_DIR = os.getenv("DRIVE_UPLOAD_DIR", os.path.join(os.getcwd(), "uploads", "drive"))
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

ALLOWED_MIME_TYPES = [
    # Images
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/svg+xml",
    # Video
    "video/mp4",
    "video/mpeg",
    "video/webm",
    "video/quicktime",
    # Audio
    "audio/mpeg",
    "audio/wav",
    "audio/ogg",
    "audio/mp4",
    "audio/webm",
    # Documents
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    # Archives
    "application/zip",
    "application/x-zip-compressed",
]


# ─── Utilities ────────────────────────────────────────────────────────────────

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename: replace non-alphanumeric chars (except . and -) with _.
    Collapse multiple underscores into one.
    """
    if not filename:
        return f"file_{uuid.uuid4().hex[:8]}"

    # Split name and extension
    parts = filename.rsplit(".", 1) if "." in filename else [filename]
    name = parts[0]
    ext = f".{parts[1]}" if len(parts) > 1 else ""

    # Replace anything that's not alphanumeric, dot, or dash
    name = re.sub(r"[^a-zA-Z0-9._\-]", "_", name)
    # Collapse multiple underscores
    name = re.sub(r"_+", "_", name)
    # Strip leading/trailing underscores
    name = name.strip("_")

    if not name:
        name = f"file_{uuid.uuid4().hex[:8]}"

    return f"{name}{ext}"


def is_mime_allowed(mime_type: str) -> bool:
    """Check if a MIME type is in the allowed list (supports wildcards)."""
    if mime_type in ALLOWED_MIME_TYPES:
        return True
    # Check wildcard patterns like image/*
    category = mime_type.split("/")[0]
    if f"{category}/*" in ALLOWED_MIME_TYPES:
        return True
    return False


# ─── Drive Service ────────────────────────────────────────────────────────────

class DriveService:
    """Service for managing drive folders and files."""

    # ── Folder Operations ──

    async def create_folder(
        self,
        tenant_id: int,
        client_id: int,
        nombre: str,
        parent_id: Optional[str] = None,
    ) -> dict:
        """Create a new folder."""
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO drive_folders (tenant_id, client_id, nombre, parent_id)
                VALUES ($1, $2, $3, $4)
                RETURNING id, tenant_id, client_id, nombre, parent_id, created_at, updated_at
                """,
                tenant_id,
                client_id,
                nombre,
                uuid.UUID(str(parent_id)) if parent_id else None,
            )
            return dict(row)

    async def list_folders(
        self,
        tenant_id: int,
        client_id: int,
        parent_id: Optional[str] = None,
    ) -> list:
        """List folders for a client. If parent_id is None, lists root folders."""
        async with db.pool.acquire() as conn:
            if parent_id:
                rows = await conn.fetch(
                    """
                    SELECT id, tenant_id, client_id, nombre, parent_id, created_at, updated_at
                    FROM drive_folders
                    WHERE tenant_id = $1 AND client_id = $2 AND parent_id = $3
                    ORDER BY nombre
                    """,
                    tenant_id,
                    client_id,
                    uuid.UUID(parent_id),
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT id, tenant_id, client_id, nombre, parent_id, created_at, updated_at
                    FROM drive_folders
                    WHERE tenant_id = $1 AND client_id = $2 AND parent_id IS NULL
                    ORDER BY nombre
                    """,
                    tenant_id,
                    client_id,
                )
            return [dict(r) for r in rows]

    async def get_folder(self, tenant_id: int, folder_id) -> Optional[dict]:
        """Get a single folder by ID, filtered by tenant."""
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, tenant_id, client_id, nombre, parent_id, created_at, updated_at
                FROM drive_folders
                WHERE id = $1 AND tenant_id = $2
                """,
                uuid.UUID(str(folder_id)),
                tenant_id,
            )
            return dict(row) if row else None

    async def get_breadcrumb(self, tenant_id: int, folder_id) -> list:
        """Get breadcrumb trail from root to the given folder using recursive CTE."""
        async with db.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                WITH RECURSIVE ancestors AS (
                    SELECT id, nombre, parent_id, 0 AS depth
                    FROM drive_folders
                    WHERE id = $1 AND tenant_id = $2
                    UNION ALL
                    SELECT f.id, f.nombre, f.parent_id, a.depth + 1
                    FROM drive_folders f
                    JOIN ancestors a ON f.id = a.parent_id
                    WHERE f.tenant_id = $2
                )
                SELECT id, nombre, depth
                FROM ancestors
                ORDER BY depth DESC
                """,
                uuid.UUID(str(folder_id)),
                tenant_id,
            )
            return [dict(r) for r in rows]

    async def get_children_folders(self, tenant_id: int, folder_id) -> list:
        """Get direct subfolders of a folder."""
        async with db.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, tenant_id, client_id, nombre, parent_id, created_at, updated_at
                FROM drive_folders
                WHERE tenant_id = $1 AND parent_id = $2
                ORDER BY nombre
                """,
                tenant_id,
                uuid.UUID(str(folder_id)),
            )
            return [dict(r) for r in rows]

    async def delete_folder(self, tenant_id: int, folder_id) -> bool:
        """
        Delete a folder and all its contents.
        First removes physical files from storage, then deletes DB records (CASCADE).
        """
        folder_uuid = uuid.UUID(str(folder_id))

        async with db.pool.acquire() as conn:
            # Verify ownership
            folder = await conn.fetchrow(
                "SELECT id, tenant_id FROM drive_folders WHERE id = $1 AND tenant_id = $2",
                folder_uuid,
                tenant_id,
            )
            if not folder:
                return False

            # Get ALL files in this folder tree (recursive)
            files = await conn.fetch(
                """
                WITH RECURSIVE folder_tree AS (
                    SELECT id FROM drive_folders WHERE id = $1 AND tenant_id = $2
                    UNION ALL
                    SELECT f.id FROM drive_folders f
                    JOIN folder_tree ft ON f.parent_id = ft.id
                )
                SELECT df.storage_path
                FROM drive_files df
                JOIN folder_tree ft ON df.folder_id = ft.id
                """,
                folder_uuid,
                tenant_id,
            )

            # Delete physical files
            for file_row in files:
                try:
                    file_path = Path(file_row["storage_path"])
                    if file_path.exists():
                        file_path.unlink()
                except Exception as e:
                    logger.warning(f"Could not delete file {file_row['storage_path']}: {e}")

            # Delete folder (CASCADE deletes subfolders and file records)
            await conn.execute(
                "DELETE FROM drive_folders WHERE id = $1 AND tenant_id = $2",
                folder_uuid,
                tenant_id,
            )

        return True

    # ── File Operations ──

    def build_storage_path(
        self,
        tenant_id: int,
        client_id: int,
        folder_id: str,
        filename: str,
    ) -> str:
        """Build the storage path for a file."""
        sanitized = sanitize_filename(filename)
        unique_name = f"{uuid.uuid4().hex[:8]}_{sanitized}"
        rel_path = os.path.join(
            str(tenant_id), str(client_id), str(folder_id), unique_name
        )
        return os.path.join(DRIVE_UPLOAD_DIR, rel_path)

    async def save_file_to_disk(self, storage_path: str, content: bytes) -> None:
        """Write file content to disk."""
        path = Path(storage_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    async def register_file(
        self,
        tenant_id: int,
        client_id: int,
        folder_id,
        nombre: str,
        storage_path: str,
        mime_type: str,
        size_bytes: int,
        uploaded_by: Optional[int] = None,
    ) -> dict:
        """Register a file in the database after upload."""
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO drive_files
                    (tenant_id, client_id, folder_id, nombre, storage_path, mime_type, size_bytes, uploaded_by)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id, nombre, mime_type, size_bytes, folder_id, created_at
                """,
                tenant_id,
                client_id,
                uuid.UUID(str(folder_id)),
                nombre,
                storage_path,
                mime_type,
                size_bytes,
                uploaded_by,
            )
            return dict(row)

    async def list_files(self, tenant_id: int, folder_id) -> list:
        """List files in a folder."""
        async with db.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, nombre, mime_type, size_bytes, folder_id, uploaded_by, created_at
                FROM drive_files
                WHERE tenant_id = $1 AND folder_id = $2
                ORDER BY nombre
                """,
                tenant_id,
                uuid.UUID(str(folder_id)),
            )
            return [dict(r) for r in rows]

    async def get_file(self, tenant_id: int, file_id) -> Optional[dict]:
        """Get file metadata by ID, filtered by tenant."""
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, tenant_id, client_id, folder_id, nombre, storage_path,
                       mime_type, size_bytes, uploaded_by, created_at
                FROM drive_files
                WHERE id = $1 AND tenant_id = $2
                """,
                uuid.UUID(str(file_id)),
                tenant_id,
            )
            return dict(row) if row else None

    async def delete_file(self, tenant_id: int, file_id) -> bool:
        """Delete a file from storage and database."""
        async with db.pool.acquire() as conn:
            file_record = await conn.fetchrow(
                "SELECT id, storage_path FROM drive_files WHERE id = $1 AND tenant_id = $2",
                uuid.UUID(str(file_id)),
                tenant_id,
            )
            if not file_record:
                return False

            # Delete physical file
            try:
                file_path = Path(file_record["storage_path"])
                if file_path.exists():
                    file_path.unlink()
            except Exception as e:
                logger.warning(f"Could not delete physical file: {e}")

            # Delete DB record
            await conn.execute(
                "DELETE FROM drive_files WHERE id = $1 AND tenant_id = $2",
                uuid.UUID(str(file_id)),
                tenant_id,
            )

        return True


# ─── Singleton ────────────────────────────────────────────────────────────────

drive_service = DriveService()
