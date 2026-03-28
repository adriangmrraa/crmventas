"""
DEV-35: Company/Tenant Profile Settings Routes
Configure business name, logo, contact info, WhatsApp, timezone, currency,
business hours, AI agent params, and more.
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from db import db
from core.security import verify_admin_token, get_resolved_tenant_id, require_role

logger = logging.getLogger(__name__)

# Settings router — mounted at /admin/core/settings
router = APIRouter(prefix="/admin/core/settings", tags=["Company Settings"])

# Setup router — mounted at /admin/setup
setup_router = APIRouter(prefix="/admin/setup", tags=["Setup"])

# ── Pydantic schemas ──────────────────────────────────────────────────────────

TENANT_PROFILE_FIELDS = [
    "clinic_name", "logo_url", "contact_email", "contact_phone",
    "whatsapp_number", "timezone", "currency", "business_hours_start",
    "business_hours_end", "ai_agent_name", "ai_agent_active", "website",
    "address", "industry", "bot_phone_number",
]


class TenantConfigureInput(BaseModel):
    """Input for POST /admin/setup/configure-tenant"""
    business_name: Optional[str] = None
    logo_url: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    whatsapp_number: Optional[str] = None
    timezone: Optional[str] = "America/Argentina/Buenos_Aires"
    currency: Optional[str] = "ARS"
    business_hours_start: Optional[str] = "09:00"
    business_hours_end: Optional[str] = "18:00"
    ai_agent_name: Optional[str] = "Asistente"
    ai_agent_active: Optional[bool] = True
    website: Optional[str] = None
    address: Optional[str] = None
    industry: Optional[str] = None


class CompanySettingsUpdate(BaseModel):
    """Input for PUT /admin/core/settings/company (CEO only)"""
    business_name: Optional[str] = None
    logo_url: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    whatsapp_number: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None
    business_hours_start: Optional[str] = None
    business_hours_end: Optional[str] = None
    ai_agent_name: Optional[str] = None
    ai_agent_active: Optional[bool] = None
    website: Optional[str] = None
    address: Optional[str] = None
    industry: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _fetch_tenant_profile(tenant_id: int) -> dict:
    """Fetch the full tenant profile row as a dict."""
    columns = ", ".join(TENANT_PROFILE_FIELDS)
    row = await db.fetchrow(
        f"SELECT id, {columns}, created_at, updated_at FROM tenants WHERE id = $1",
        tenant_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Tenant not found")
    result = dict(row)
    # Normalize: expose clinic_name as business_name for the API
    result["business_name"] = result.pop("clinic_name", None)
    # Stringify datetimes
    for key in ("created_at", "updated_at"):
        if result.get(key):
            result[key] = str(result[key])
    return result


def _build_update_sets(data: dict) -> tuple:
    """
    Build dynamic SET clause from non-None fields.
    Returns (set_clause, params_list) with $N placeholders starting at $2
    (since $1 is tenant_id).
    """
    # Map API field names to DB column names
    field_map = {
        "business_name": "clinic_name",
        "logo_url": "logo_url",
        "contact_email": "contact_email",
        "contact_phone": "contact_phone",
        "whatsapp_number": "whatsapp_number",
        "timezone": "timezone",
        "currency": "currency",
        "business_hours_start": "business_hours_start",
        "business_hours_end": "business_hours_end",
        "ai_agent_name": "ai_agent_name",
        "ai_agent_active": "ai_agent_active",
        "website": "website",
        "address": "address",
        "industry": "industry",
    }

    sets = []
    params = []
    idx = 2  # $1 reserved for tenant_id
    for api_field, db_col in field_map.items():
        value = data.get(api_field)
        if value is not None:
            sets.append(f"{db_col} = ${idx}")
            params.append(value)
            idx += 1

    # Always touch updated_at
    sets.append("updated_at = NOW()")
    return ", ".join(sets), params


# ── Setup Route ───────────────────────────────────────────────────────────────

@setup_router.post("/configure-tenant")
async def configure_tenant(
    payload: TenantConfigureInput,
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """
    POST /admin/setup/configure-tenant
    Configure tenant profile (initial setup or subsequent updates).
    Any authenticated admin role can call this during onboarding.
    """
    data = payload.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields provided")

    set_clause, params = _build_update_sets(data)
    query = f"UPDATE tenants SET {set_clause} WHERE id = $1"
    await db.execute(query, tenant_id, *params)

    logger.info(f"DEV-35: Tenant {tenant_id} configured by {user_data.email} — fields: {list(data.keys())}")
    return await _fetch_tenant_profile(tenant_id)


# ── Settings Routes ───────────────────────────────────────────────────────────

@router.get("/company")
async def get_company_settings(
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """
    GET /admin/core/settings/company
    Returns the current tenant/company configuration.
    """
    return await _fetch_tenant_profile(tenant_id)


@router.put("/company", dependencies=[Depends(require_role(["ceo"]))])
async def update_company_settings(
    payload: CompanySettingsUpdate,
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """
    PUT /admin/core/settings/company
    CEO-only: update tenant/company configuration.
    """
    data = payload.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields provided")

    set_clause, params = _build_update_sets(data)
    query = f"UPDATE tenants SET {set_clause} WHERE id = $1"
    await db.execute(query, tenant_id, *params)

    logger.info(f"DEV-35: Tenant {tenant_id} updated by CEO {user_data.email} — fields: {list(data.keys())}")
    return await _fetch_tenant_profile(tenant_id)
