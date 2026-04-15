"""Knowledge Base Routes — SPEC-03"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from core.security import verify_admin_token, get_resolved_tenant_id, require_role
from services.manuales_service import manuales_service, VALID_CATEGORIAS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/core/manuales", tags=["Knowledge Base"])

class ManualCreate(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=300)
    contenido: str = Field(..., min_length=1)
    categoria: str = "general"
    autor: Optional[str] = None

class ManualUpdate(BaseModel):
    titulo: Optional[str] = Field(None, min_length=1, max_length=300)
    contenido: Optional[str] = Field(None, min_length=1)
    categoria: Optional[str] = None
    autor: Optional[str] = None

@router.get("")
async def list_manuales(categoria: Optional[str] = None, q: Optional[str] = None, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), user_data=Depends(verify_admin_token), tenant_id: int = Depends(get_resolved_tenant_id)):
    return await manuales_service.list(tenant_id, categoria, q, limit, offset)

@router.get("/{manual_id}")
async def get_manual(manual_id: str, user_data=Depends(verify_admin_token), tenant_id: int = Depends(get_resolved_tenant_id)):
    m = await manuales_service.get(tenant_id, manual_id)
    if not m: raise HTTPException(404, "Manual no encontrado")
    return m

@router.post("", status_code=201, dependencies=[Depends(require_role(["ceo", "secretary"]))])
async def create_manual(body: ManualCreate, user_data=Depends(verify_admin_token), tenant_id: int = Depends(get_resolved_tenant_id)):
    if body.categoria not in VALID_CATEGORIAS:
        raise HTTPException(400, f"Categoria invalida: {body.categoria}")
    return await manuales_service.create(tenant_id, body.titulo, body.contenido, body.categoria, body.autor)

@router.put("/{manual_id}", dependencies=[Depends(require_role(["ceo", "secretary"]))])
async def update_manual(manual_id: str, body: ManualUpdate, user_data=Depends(verify_admin_token), tenant_id: int = Depends(get_resolved_tenant_id)):
    if body.categoria and body.categoria not in VALID_CATEGORIAS:
        raise HTTPException(400, f"Categoria invalida: {body.categoria}")
    m = await manuales_service.update(tenant_id, manual_id, body.titulo, body.contenido, body.categoria, body.autor)
    if not m: raise HTTPException(404, "Manual no encontrado")
    return m

@router.delete("/{manual_id}", status_code=204, dependencies=[Depends(require_role(["ceo", "secretary"]))])
async def delete_manual(manual_id: str, user_data=Depends(verify_admin_token), tenant_id: int = Depends(get_resolved_tenant_id)):
    if not await manuales_service.delete(tenant_id, manual_id):
        raise HTTPException(404, "Manual no encontrado")
