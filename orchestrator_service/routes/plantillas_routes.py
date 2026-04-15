"""
Plantillas de Mensajes Routes — SPEC-02
CRUD endpoints for reusable message templates.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core.security import verify_admin_token, get_resolved_tenant_id
from services.plantillas_service import (
    plantillas_service,
    DuplicateTemplateNameError,
    VALID_CATEGORIES,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/plantillas", tags=["Plantillas"])


# ─── Models ───────────────────────────────────────────────────────────────────

class PlantillaCreateRequest(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    categoria: str = Field(default="whatsapp")
    contenido: str = Field(..., min_length=1, max_length=4000)


class PlantillaUpdateRequest(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    categoria: str = Field(default="whatsapp")
    contenido: str = Field(..., min_length=1, max_length=4000)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("")
async def list_plantillas(
    categoria: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """List templates with optional category filter and search."""
    result = await plantillas_service.list(
        tenant_id=tenant_id,
        categoria=categoria,
        q=q,
        skip=skip,
        limit=limit,
    )
    return {
        "items": [_serialize(p) for p in result["items"]],
        "total": result["total"],
    }


@router.get("/{plantilla_id}")
async def get_plantilla(
    plantilla_id: str,
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """Get template detail."""
    p = await plantillas_service.get(tenant_id=tenant_id, plantilla_id=plantilla_id)
    if not p:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    return _serialize(p)


@router.post("", status_code=201)
async def create_plantilla(
    body: PlantillaCreateRequest,
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """Create a new template. Variables are auto-extracted from content."""
    if body.categoria not in VALID_CATEGORIES:
        raise HTTPException(status_code=422, detail=f"Categoria invalida: {body.categoria}")

    try:
        user_id = int(user_data.user_id) if user_data.user_id else None
    except (ValueError, TypeError):
        user_id = None

    try:
        p = await plantillas_service.create(
            tenant_id=tenant_id,
            nombre=body.nombre,
            categoria=body.categoria,
            contenido=body.contenido,
            created_by=user_id,
        )
        return _serialize(p)
    except DuplicateTemplateNameError:
        raise HTTPException(
            status_code=409,
            detail="Ya existe una plantilla con ese nombre en tu organizacion",
        )


@router.put("/{plantilla_id}")
async def update_plantilla(
    plantilla_id: str,
    body: PlantillaUpdateRequest,
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """Update a template. Variables are re-extracted from content."""
    if body.categoria not in VALID_CATEGORIES:
        raise HTTPException(status_code=422, detail=f"Categoria invalida: {body.categoria}")

    try:
        p = await plantillas_service.update(
            tenant_id=tenant_id,
            plantilla_id=plantilla_id,
            nombre=body.nombre,
            categoria=body.categoria,
            contenido=body.contenido,
        )
        if not p:
            raise HTTPException(status_code=404, detail="Plantilla no encontrada")
        return _serialize(p)
    except DuplicateTemplateNameError:
        raise HTTPException(
            status_code=409,
            detail="Ya existe una plantilla con ese nombre en tu organizacion",
        )


@router.delete("/{plantilla_id}", status_code=204)
async def delete_plantilla(
    plantilla_id: str,
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """Delete a template."""
    deleted = await plantillas_service.delete(
        tenant_id=tenant_id, plantilla_id=plantilla_id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    return None


@router.post("/{plantilla_id}/uso")
async def increment_uso(
    plantilla_id: str,
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """Atomically increment usage counter."""
    new_count = await plantillas_service.increment_uso(
        tenant_id=tenant_id, plantilla_id=plantilla_id
    )
    if new_count is None:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    return {"uso_count": new_count}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _serialize(p: dict) -> dict:
    return {
        "id": str(p["id"]),
        "nombre": p["nombre"],
        "categoria": p["categoria"],
        "contenido": p["contenido"],
        "variables": list(p.get("variables", [])),
        "uso_count": p.get("uso_count", 0),
        "created_by": str(p["created_by"]) if p.get("created_by") else None,
        "created_at": str(p.get("created_at", "")),
        "updated_at": str(p.get("updated_at", "")),
    }
