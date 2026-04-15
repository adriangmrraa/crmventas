"""
Daily Check-in Routes — SPEC-05
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from core.security import verify_admin_token, get_resolved_tenant_id, require_role
from services.daily_checkin_service import checkin_service, CheckinAlreadyExistsError, CheckinAlreadyClosedError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/core/checkin", tags=["Daily Check-in"])

class CheckinRequest(BaseModel):
    llamadas_planeadas: int = Field(..., gt=0)

class CheckoutRequest(BaseModel):
    llamadas_logradas: int = Field(..., ge=0)
    contactos_logrados: int = Field(0, ge=0)
    notas: Optional[str] = None

@router.post("/", status_code=201)
async def do_checkin(body: CheckinRequest, user_data=Depends(verify_admin_token), tenant_id: int = Depends(get_resolved_tenant_id)):
    try:
        return await checkin_service.checkin(user_data.user_id, tenant_id, body.llamadas_planeadas)
    except CheckinAlreadyExistsError:
        raise HTTPException(409, "Ya hiciste check-in hoy")

@router.post("/{checkin_id}/checkout")
async def do_checkout(checkin_id: str, body: CheckoutRequest, user_data=Depends(verify_admin_token), tenant_id: int = Depends(get_resolved_tenant_id)):
    try:
        result = await checkin_service.checkout(checkin_id, user_data.user_id, tenant_id, body.llamadas_logradas, body.contactos_logrados, body.notas)
        if not result:
            raise HTTPException(404, "Check-in no encontrado")
        return result
    except CheckinAlreadyClosedError:
        raise HTTPException(409, "Jornada ya cerrada")

@router.get("/today")
async def get_today(user_data=Depends(verify_admin_token), tenant_id: int = Depends(get_resolved_tenant_id)):
    return await checkin_service.get_today(user_data.user_id, tenant_id) or {}

@router.get("/ceo/today", dependencies=[Depends(require_role(["ceo", "admin"]))])
async def ceo_today(user_data=Depends(verify_admin_token), tenant_id: int = Depends(get_resolved_tenant_id)):
    return await checkin_service.get_ceo_today(tenant_id)

@router.get("/ceo/weekly", dependencies=[Depends(require_role(["ceo", "admin"]))])
async def ceo_weekly(weeks: int = Query(1, ge=1, le=4), user_data=Depends(verify_admin_token), tenant_id: int = Depends(get_resolved_tenant_id)):
    return await checkin_service.get_weekly(tenant_id, weeks)

@router.get("/history")
async def history(limit: int = Query(30, ge=1, le=100), user_data=Depends(verify_admin_token), tenant_id: int = Depends(get_resolved_tenant_id)):
    return await checkin_service.get_history(user_data.user_id, tenant_id, limit)
