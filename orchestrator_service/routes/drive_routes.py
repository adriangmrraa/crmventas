"""
Drive / File Storage Routes — SPEC-01
REST API for folder and file management with multi-tenant isolation.
All endpoints require JWT + X-Admin-Token authentication.
"""

import os
import logging
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from core.security import verify_admin_token, get_resolved_tenant_id
from services.drive_service import (
    drive_service,
    sanitize_filename,
    ALLOWED_MIME_TYPES,
    MAX_FILE_SIZE,
    is_mime_allowed,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/drive", tags=["Drive Storage"])


# ─── Request/Response Models ─────────────────────────────────────────────────

class CreateFolderRequest(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=255)
    client_id: int
    parent_id: Optional[str] = None


class FolderResponse(BaseModel):
    id: str
    nombre: str
    client_id: int
    parent_id: Optional[str] = None
    created_at: str
    updated_at: str


class FileResponse_(BaseModel):
    id: str
    nombre: str
    mime_type: str
    size_bytes: int
    folder_id: str
    created_at: str


class BreadcrumbItem(BaseModel):
    id: str
    nombre: str


# ─── Folder Endpoints ────────────────────────────────────────────────────────

@router.get("/folders")
async def list_folders(
    client_id: int = Query(...),
    parent_id: Optional[str] = Query(None),
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """List root folders or subfolders for a client."""
    folders = await drive_service.list_folders(
        tenant_id=tenant_id,
        client_id=client_id,
        parent_id=parent_id,
    )
    return [_serialize_folder(f) for f in folders]


@router.get("/folders/{folder_id}")
async def get_folder(
    folder_id: str,
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """Get folder details."""
    folder = await drive_service.get_folder(tenant_id=tenant_id, folder_id=folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Carpeta no encontrada")
    return _serialize_folder(folder)


@router.get("/folders/{folder_id}/breadcrumb")
async def get_breadcrumb(
    folder_id: str,
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """Get breadcrumb trail from root to this folder."""
    breadcrumb = await drive_service.get_breadcrumb(
        tenant_id=tenant_id, folder_id=folder_id
    )
    return {
        "breadcrumb": [
            {"id": str(item["id"]), "nombre": item["nombre"]}
            for item in breadcrumb
        ]
    }


@router.get("/folders/{folder_id}/children")
async def get_children(
    folder_id: str,
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """Get direct subfolders of a folder."""
    children = await drive_service.get_children_folders(
        tenant_id=tenant_id, folder_id=folder_id
    )
    return [_serialize_folder(f) for f in children]


@router.post("/folders", status_code=201)
async def create_folder(
    body: CreateFolderRequest,
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """Create a new folder."""
    try:
        folder = await drive_service.create_folder(
            tenant_id=tenant_id,
            client_id=body.client_id,
            nombre=body.nombre,
            parent_id=body.parent_id,
        )
        return _serialize_folder(folder)
    except Exception as e:
        logger.error(f"Error creating folder: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/folders/{folder_id}", status_code=204)
async def delete_folder(
    folder_id: str,
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """Delete a folder and all its contents recursively."""
    deleted = await drive_service.delete_folder(
        tenant_id=tenant_id, folder_id=folder_id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Carpeta no encontrada")
    return None


# ─── File Endpoints ──────────────────────────────────────────────────────────

@router.get("/files")
async def list_files(
    folder_id: str = Query(...),
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """List files in a folder."""
    files = await drive_service.list_files(
        tenant_id=tenant_id, folder_id=folder_id
    )
    return [_serialize_file(f) for f in files]


@router.post("/files/upload", status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    folder_id: str = Form(...),
    client_id: int = Form(...),
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """Upload a file to a folder."""
    # Validate MIME type
    if not file.content_type or not is_mime_allowed(file.content_type):
        raise HTTPException(
            status_code=422,
            detail=f"Tipo de archivo no permitido: {file.content_type}",
        )

    # Verify folder exists and belongs to tenant
    folder = await drive_service.get_folder(tenant_id=tenant_id, folder_id=folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Carpeta no encontrada")

    # Read file content with size check (chunked to avoid OOM)
    content = bytearray()
    chunk_size = 64 * 1024  # 64KB chunks
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        content.extend(chunk)
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=422,
                detail=f"Archivo excede el límite de {MAX_FILE_SIZE // (1024*1024)}MB",
            )

    size_bytes = len(content)
    if size_bytes == 0:
        raise HTTPException(status_code=422, detail="Archivo vacío")

    # Build storage path and save
    storage_path = drive_service.build_storage_path(
        tenant_id=tenant_id,
        client_id=client_id,
        folder_id=folder_id,
        filename=file.filename or "upload",
    )
    await drive_service.save_file_to_disk(storage_path, bytes(content))

    # Register in DB
    try:
        user_id = int(user_data.user_id) if user_data.user_id else None
    except (ValueError, TypeError):
        user_id = None

    result = await drive_service.register_file(
        tenant_id=tenant_id,
        client_id=client_id,
        folder_id=folder_id,
        nombre=file.filename or "upload",
        storage_path=storage_path,
        mime_type=file.content_type,
        size_bytes=size_bytes,
        uploaded_by=user_id,
    )

    return _serialize_file(result)


@router.get("/files/{file_id}/download")
async def download_file(
    file_id: str,
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """Download a file (streamed via proxy)."""
    file_record = await drive_service.get_file(
        tenant_id=tenant_id, file_id=file_id
    )
    if not file_record:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    file_path = Path(file_record["storage_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado en storage")

    return FileResponse(
        path=str(file_path),
        filename=file_record["nombre"],
        media_type=file_record.get("mime_type", "application/octet-stream"),
    )


@router.delete("/files/{file_id}", status_code=204)
async def delete_file(
    file_id: str,
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """Delete a file from storage and database."""
    deleted = await drive_service.delete_file(
        tenant_id=tenant_id, file_id=file_id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return None


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _serialize_folder(folder: dict) -> dict:
    """Serialize folder record for JSON response."""
    return {
        "id": str(folder["id"]),
        "nombre": folder["nombre"],
        "client_id": folder.get("client_id"),
        "parent_id": str(folder["parent_id"]) if folder.get("parent_id") else None,
        "created_at": str(folder.get("created_at", "")),
        "updated_at": str(folder.get("updated_at", "")),
    }


def _serialize_file(file: dict) -> dict:
    """Serialize file record for JSON response."""
    return {
        "id": str(file["id"]),
        "nombre": file["nombre"],
        "mime_type": file.get("mime_type", ""),
        "size_bytes": file.get("size_bytes", 0),
        "folder_id": str(file["folder_id"]) if file.get("folder_id") else None,
        "created_at": str(file.get("created_at", "")),
    }
