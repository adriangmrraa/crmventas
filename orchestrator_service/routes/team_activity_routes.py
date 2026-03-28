"""
Team Activity Routes — DEV-39 + DEV-40: Panel de Actividad y Log de Auditoría
Endpoints para el feed de actividad, estado de vendedores, alertas y auditoría.
Solo accesible por rol CEO.
"""
import csv
import io
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from core.security import verify_admin_token, get_resolved_tenant_id, require_role
from services.activity_service import (
    get_feed, get_seller_statuses, get_inactive_lead_alerts,
    get_audit_by_lead, get_audit_by_seller, get_feed_for_export,
    get_seller_performance,
)

logger = logging.getLogger("orchestrator")

router = APIRouter(prefix="/admin/core/team-activity", tags=["Team Activity"])


@router.get("/feed", dependencies=[Depends(require_role(["ceo"]))])
async def feed(
    tenant_id: int = Depends(get_resolved_tenant_id),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    seller_id: Optional[UUID] = Query(None),
    event_type: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
):
    """Feed paginado de actividad del equipo en tiempo real."""
    return await get_feed(
        tenant_id=tenant_id,
        limit=limit,
        offset=offset,
        seller_id=seller_id,
        event_type=event_type,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/seller-status", dependencies=[Depends(require_role(["ceo"]))])
async def seller_status(
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """Estado de cada vendedor: activo/idle/inactivo + metricas."""
    sellers = await get_seller_statuses(tenant_id)
    return {"sellers": sellers}


@router.get("/alerts", dependencies=[Depends(require_role(["ceo"]))])
async def alerts(
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """Leads sin actividad en las ultimas 2 horas."""
    alert_list = await get_inactive_lead_alerts(tenant_id)
    return {"alerts": alert_list}


# ============================================
# DEV-40: AUDIT LOG ENDPOINTS
# ============================================

@router.get("/audit/by-lead/{lead_id}", dependencies=[Depends(require_role(["ceo"]))])
async def audit_by_lead(
    lead_id: UUID,
    tenant_id: int = Depends(get_resolved_tenant_id),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Timeline completa de auditoría de un lead específico."""
    return await get_audit_by_lead(tenant_id, lead_id, limit, offset)


@router.get("/audit/by-seller/{user_id}", dependencies=[Depends(require_role(["ceo"]))])
async def audit_by_seller(
    user_id: UUID,
    tenant_id: int = Depends(get_resolved_tenant_id),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    event_type: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
):
    """Historial completo de acciones de un vendedor."""
    return await get_audit_by_seller(
        tenant_id, user_id, limit, offset, event_type, date_from, date_to
    )


@router.get("/audit/export", dependencies=[Depends(require_role(["ceo"]))])
async def audit_export_csv(
    tenant_id: int = Depends(get_resolved_tenant_id),
    seller_id: Optional[UUID] = Query(None),
    event_type: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
):
    """Exportar log de auditoría como CSV."""
    rows = await get_feed_for_export(
        tenant_id, seller_id=seller_id, event_type=event_type,
        date_from=date_from, date_to=date_to,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Fecha", "Vendedor", "Rol", "Tipo", "Lead/Entidad", "Detalle"])
    for r in rows:
        writer.writerow([
            r["created_at"], r["actor_name"], r["actor_role"],
            r["event_type"], r["entity_name"], r["detail"],
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_log.csv"},
    )


# ============================================
# DEV-41: SELLER PERFORMANCE ENDPOINT
# ============================================

@router.get("/seller/{user_id}/performance", dependencies=[Depends(require_role(["ceo"]))])
async def seller_performance(
    user_id: UUID,
    tenant_id: int = Depends(get_resolved_tenant_id),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
):
    """KPIs detallados de un vendedor con breakdown temporal y comparativa."""
    return await get_seller_performance(tenant_id, user_id, date_from, date_to)
