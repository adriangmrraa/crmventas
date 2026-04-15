"""Vendor Tasks Routes — SPEC-06"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from core.security import verify_admin_token, get_resolved_tenant_id, require_role
from services.vendor_tasks_service import vendor_tasks_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/core/crm/vendor-tasks", tags=["Vendor Tasks"])

class CreateTaskRequest(BaseModel):
    vendor_id: int
    contenido: str = Field(..., min_length=1, max_length=2000)
    es_tarea: bool = False
    fecha_limite: Optional[str] = None

class CreatePersonalRequest(BaseModel):
    contenido: str = Field(..., min_length=1, max_length=2000)
    fecha_limite: Optional[str] = None

class ToggleRequest(BaseModel):
    completada: bool

@router.post("", status_code=201, dependencies=[Depends(require_role(["ceo", "admin"]))])
async def create_task(body: CreateTaskRequest, user_data=Depends(verify_admin_token), tenant_id: int = Depends(get_resolved_tenant_id)):
    try:
        uid = int(user_data.user_id)
    except (ValueError, TypeError):
        uid = 0
    return await vendor_tasks_service.create(tenant_id, body.vendor_id, uid, body.contenido, body.es_tarea, body.fecha_limite)

@router.get("", dependencies=[Depends(require_role(["ceo", "admin"]))])
async def list_tasks(vendor_id: Optional[int] = None, es_tarea: Optional[bool] = None, completada: Optional[bool] = None, user_data=Depends(verify_admin_token), tenant_id: int = Depends(get_resolved_tenant_id)):
    return await vendor_tasks_service.list_for_admin(tenant_id, vendor_id, es_tarea, completada)

@router.get("/mine")
async def get_mine(user_data=Depends(verify_admin_token), tenant_id: int = Depends(get_resolved_tenant_id)):
    try:
        uid = int(user_data.user_id)
    except (ValueError, TypeError):
        uid = 0
    return await vendor_tasks_service.get_mine(tenant_id, uid)

@router.post("/personal", status_code=201)
async def create_personal(body: CreatePersonalRequest, user_data=Depends(verify_admin_token), tenant_id: int = Depends(get_resolved_tenant_id)):
    try:
        uid = int(user_data.user_id)
    except (ValueError, TypeError):
        uid = 0
    return await vendor_tasks_service.create_personal(tenant_id, uid, body.contenido, body.fecha_limite)

@router.patch("/{task_id}/completar")
async def toggle_completada(task_id: str, body: ToggleRequest, user_data=Depends(verify_admin_token), tenant_id: int = Depends(get_resolved_tenant_id)):
    try:
        uid = int(user_data.user_id)
    except (ValueError, TypeError):
        uid = 0
    try:
        result = await vendor_tasks_service.toggle_completada(tenant_id, task_id, uid, body.completada)
        if not result:
            raise HTTPException(404, "Tarea no encontrada")
        return result
    except PermissionError:
        raise HTTPException(403, "No podes completar tareas de otro vendedor")

@router.delete("/{task_id}", status_code=204, dependencies=[Depends(require_role(["ceo", "admin"]))])
async def delete_task(task_id: str, user_data=Depends(verify_admin_token), tenant_id: int = Depends(get_resolved_tenant_id)):
    try:
        if not await vendor_tasks_service.delete(tenant_id, task_id):
            raise HTTPException(404, "Tarea no encontrada")
    except ValueError as e:
        raise HTTPException(409, str(e))

@router.get("/pending-count")
async def pending_count(user_data=Depends(verify_admin_token), tenant_id: int = Depends(get_resolved_tenant_id)):
    try:
        uid = int(user_data.user_id)
    except (ValueError, TypeError):
        uid = 0
    count = await vendor_tasks_service.pending_count(tenant_id, uid)
    return {"count": count}
