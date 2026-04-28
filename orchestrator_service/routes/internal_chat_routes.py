"""
Internal Chat Routes — SPEC-04
Team chat: channels, DMs, messages, unread badges.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core.security import verify_admin_token, get_resolved_tenant_id, require_role
from services.internal_chat_service import chat_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/core/internal-chat", tags=["Internal Chat"])


# ─── Models ───────────────────────────────────────────────────────────────────

class SendMessageRequest(BaseModel):
    canal_id: str = Field(..., min_length=1)
    contenido: str = Field(..., min_length=1, max_length=2000)
    tipo: str = Field(default="mensaje")


class IniciarDMRequest(BaseModel):
    destinatario_id: str


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/canales")
async def get_canales(
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """Get fixed channels + user's DMs."""
    await chat_service.ensure_channels_exist(tenant_id)
    return await chat_service.get_canales(
        tenant_id=tenant_id, user_id=user_data.user_id
    )


@router.get("/mensajes/{canal_id}")
async def get_mensajes(
    canal_id: str,
    limit: int = Query(50, ge=1, le=200),
    before: Optional[str] = Query(None),
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """Get messages from a channel/DM."""
    result = await chat_service.get_mensajes(
        tenant_id=tenant_id,
        canal_id=canal_id,
        user_id=user_data.user_id,
        user_role=user_data.role,
        limit=limit,
        before=before,
    )
    if result is None:
        raise HTTPException(status_code=403, detail="No tenes acceso a esta conversacion")
    return result


@router.post("/mensajes", status_code=201)
async def send_message(
    body: SendMessageRequest,
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """Send a message to a channel/DM."""
    if body.tipo not in ("mensaje", "notificacion_tarea", "notificacion_llamada"):
        raise HTTPException(status_code=422, detail="Tipo de mensaje invalido")

    return await chat_service.enviar_mensaje(
        tenant_id=tenant_id,
        canal_id=body.canal_id,
        autor_id=user_data.user_id,
        autor_nombre=user_data.email.split("@")[0],
        autor_rol=user_data.role,
        contenido=body.contenido,
        tipo=body.tipo,
    )


@router.post("/dms/iniciar")
async def iniciar_dm(
    body: IniciarDMRequest,
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """Create or retrieve a DM channel."""
    canal_id = await chat_service.iniciar_dm(
        tenant_id=tenant_id,
        user_id=user_data.user_id,
        destinatario_id=body.destinatario_id,
    )
    return {"canal_id": canal_id}


@router.post("/dms/{canal_id}/leer")
async def marcar_dm_leido(
    canal_id: str,
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """Mark DM as read — reset unread counter."""
    await chat_service.marcar_dm_leido(
        tenant_id=tenant_id,
        canal_id=canal_id,
        user_id=user_data.user_id,
    )
    return {"ok": True}


@router.get("/dms/todos", dependencies=[Depends(require_role(["ceo", "admin"]))])
async def get_all_dms(
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """CEO supervision: get all DM conversations."""
    return await chat_service.get_all_dms(tenant_id)


@router.get("/admin/conversaciones", dependencies=[Depends(require_role(["ceo"]))])
async def get_admin_conversaciones(
    vendedor_id: Optional[str] = Query(None),
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
    tipo: Optional[str] = Query(None, pattern="^(canal|dm)$"),
    keyword: Optional[str] = Query(None),
    limit: int = Query(30, ge=1, le=100),
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """CEO admin panel: all team conversations with filters and last-message preview."""
    return await chat_service.get_admin_conversaciones(
        tenant_id=tenant_id,
        vendedor_id=vendedor_id,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        tipo=tipo,
        keyword=keyword,
        limit=limit,
    )


@router.get("/perfiles")
async def get_perfiles(
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """List all tenant users (for new DM dialog)."""
    return await chat_service.get_perfiles(tenant_id)
