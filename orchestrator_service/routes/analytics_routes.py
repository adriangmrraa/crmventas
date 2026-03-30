"""
Analytics Routes Module
======================
Integrated from Dashboard_Analytics_Sovereign
Protected endpoints for CRM Analytics Dashboard with tenant isolation.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from uuid import UUID

from services.analytics.service import AnalyticsService
from core.security import get_current_user

router = APIRouter(prefix="/admin/analytics", tags=["Analytics"])


@router.get("/ceo")
async def get_ceo_dashboard(current_user: dict = Depends(get_current_user)):
    """
    Returns strategic data for the CEO role.
    Requires CEO role and tenant_id from JWT.
    """
    if current_user.get("role") != "ceo":
        raise HTTPException(
            status_code=403, detail="Only CEOs can access this endpoint"
        )

    tenant_id = current_user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant not found")

    try:
        data = await AnalyticsService.get_ceo_metrics(
            None, UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/secretary")
async def get_secretary_dashboard(current_user: dict = Depends(get_current_user)):
    """
    Returns operational data for the Secretary role.
    Requires secretary or CEO role.
    """
    role = current_user.get("role")
    if role not in ["ceo", "secretary"]:
        raise HTTPException(
            status_code=403, detail="Only CEOs and Secretaries can access this endpoint"
        )

    tenant_id = current_user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant not found")

    try:
        data = await AnalyticsService.get_secretary_metrics(
            None, UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
