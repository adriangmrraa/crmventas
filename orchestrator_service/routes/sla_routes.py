"""
SLA Rules Routes — DEV-42: Alertas automáticas por SLA vencido.
CRUD de reglas SLA + endpoint de violaciones activas.
Solo accesible por rol CEO.
"""
import logging
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core.security import verify_admin_token, get_resolved_tenant_id, require_role
from services.sla_service import (
    get_sla_rules, create_sla_rule, update_sla_rule, delete_sla_rule,
    get_active_violations,
)

logger = logging.getLogger("orchestrator")

router = APIRouter(prefix="/admin/core/sla-rules", tags=["SLA Rules"])


class SlaRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    trigger_type: str = Field(..., description="first_response | follow_up | status_change")
    threshold_minutes: int = Field(..., ge=1, le=10080)
    applies_to_statuses: Optional[List[str]] = None
    applies_to_roles: Optional[List[str]] = None
    escalate_to_ceo: bool = True
    escalate_after_minutes: int = 30
    is_active: bool = True


class SlaRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    trigger_type: Optional[str] = None
    threshold_minutes: Optional[int] = None
    applies_to_statuses: Optional[List[str]] = None
    applies_to_roles: Optional[List[str]] = None
    escalate_to_ceo: Optional[bool] = None
    escalate_after_minutes: Optional[int] = None
    is_active: Optional[bool] = None


@router.get("", dependencies=[Depends(require_role(["ceo"]))])
async def list_sla_rules(tenant_id: int = Depends(get_resolved_tenant_id)):
    """Lista reglas SLA del tenant."""
    rules = await get_sla_rules(tenant_id)
    return {"rules": rules}


@router.post("", dependencies=[Depends(require_role(["ceo"]))])
async def create_rule(
    data: SlaRuleCreate,
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """Crear regla SLA."""
    if data.trigger_type not in ("first_response", "follow_up", "status_change"):
        raise HTTPException(status_code=400, detail="trigger_type debe ser: first_response, follow_up, status_change")
    result = await create_sla_rule(tenant_id, data.model_dump())
    return {"success": True, "rule": result}


@router.put("/{rule_id}", dependencies=[Depends(require_role(["ceo"]))])
async def update_rule(
    rule_id: UUID,
    data: SlaRuleUpdate,
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """Actualizar regla SLA."""
    result = await update_sla_rule(tenant_id, rule_id, data.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(status_code=404, detail="Regla SLA no encontrada")
    return {"success": True, "rule": result}


@router.delete("/{rule_id}", dependencies=[Depends(require_role(["ceo"]))])
async def deactivate_rule(
    rule_id: UUID,
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """Desactivar regla SLA."""
    success = await delete_sla_rule(tenant_id, rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Regla SLA no encontrada")
    return {"success": True}


@router.get("/violations", dependencies=[Depends(require_role(["ceo"]))])
async def violations(tenant_id: int = Depends(get_resolved_tenant_id)):
    """Lista violaciones activas de SLA."""
    viols = await get_active_violations(tenant_id)
    return {"violations": viols, "total": len(viols)}
