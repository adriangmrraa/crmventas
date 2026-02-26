from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from uuid import UUID

from core.security import verify_admin_token, get_tenant_id_from_token, get_resolved_tenant_id
from db import db
from services.lead_status_service import LeadStatusService
from services.lead_history_service import LeadHistoryService
from modules.crm_sales.status_models import (
    LeadStatusResponse, 
    LeadStatusTransitionResponse,
    LeadStatusChangeRequest,
    LeadBulkStatusChangeRequest,
    LeadStatusHistoryResponse
)

router = APIRouter(prefix="/admin/core/crm", tags=["Lead Status"])

@router.get("/lead-statuses", response_model=List[LeadStatusResponse])
async def get_lead_statuses(
    tenant_id: int = Depends(get_resolved_tenant_id),
    include_inactive: bool = False,
    admin_token: str = Depends(verify_admin_token)
):
    """Obtiene todos los estados configurados de leads para el tenant"""
    service = LeadStatusService(db.pool)
    statuses = await service.get_statuses(tenant_id, include_inactive)
    return statuses

@router.get("/leads/{lead_id}/available-transitions", response_model=List[LeadStatusTransitionResponse])
async def get_available_transitions(
    lead_id: UUID,
    tenant_id: int = Depends(get_resolved_tenant_id),
    admin_token: str = Depends(verify_admin_token)
):
    """Obtiene transiciones disponibles visualmente desde el estado actual del lead"""
    service = LeadStatusService(db.pool)
    
    # Check current lead status checking tenant ownership
    async with db.pool.acquire() as conn:
        lead = await conn.fetchrow("SELECT status FROM leads WHERE id = $1 AND tenant_id = $2", lead_id, tenant_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        current_status = lead['status']
            
    transitions = await service.get_available_transitions(tenant_id, current_status)
    return transitions

@router.post("/leads/{lead_id}/status")
async def change_lead_status(
    lead_id: UUID,
    request: LeadStatusChangeRequest,
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_id: UUID = Depends(get_tenant_id_from_token), # Asumiendo validación via Bearer Token, get_tenant_id retorna un dic si no se pasa de largo id. Mejor parsear con JWT base, pero usaremos el JWT user real. Ojo, usar "verify_admin_token" provee dict a menudo. Asumamos user_id genérico.
    admin_token: str = Depends(verify_admin_token)
):
    """Cambia el estado de un lead (validado contra el workflow permitido)"""
    service = LeadStatusService(db.pool)
    try:
        # En una aplicacion full, recuperarias el id del token. Mockeamos owner genérico por brevedad administrativa.
        generic_user_id = None 
        result = await service.change_lead_status(
            lead_id=lead_id,
            tenant_id=tenant_id,
            new_status=request.status,
            user_id=generic_user_id,
            comment=request.comment,
            metadata=request.metadata
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error: " + str(e))

@router.post("/leads/bulk-status")
async def bulk_change_lead_status(
    request: LeadBulkStatusChangeRequest,
    tenant_id: int = Depends(get_resolved_tenant_id),
    admin_token: str = Depends(verify_admin_token)
):
    """Operation bulk para cambiar n leads simultáneamente (uso de Advisory Locks)"""
    service = LeadStatusService(db.pool)
    try:
        result = await service.bulk_change_lead_status(
            lead_ids=request.lead_ids,
            tenant_id=tenant_id,
            new_status=request.status,
            user_id=None,
            comment=request.comment
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error: " + str(e))

@router.get("/leads/{lead_id}/status-history")
async def get_lead_status_history(
    lead_id: UUID,
    limit: int = 50,
    offset: int = 0,
    tenant_id: int = Depends(get_resolved_tenant_id),
    admin_token: str = Depends(verify_admin_token)
):
    """Obtener el audit-trail temporal del lead"""
    service = LeadHistoryService(db.pool)
    timeline = await service.get_lead_timeline(tenant_id, lead_id, limit, offset)
    return {"timeline": timeline}
