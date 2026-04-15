"""Lead Forms Routes — F-02: CRUD + public submission."""
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from core.security import verify_admin_token, get_resolved_tenant_id, require_role
from core.rate_limiter import limiter
from services.lead_forms_service import lead_forms_service

logger = logging.getLogger(__name__)

# Private router (authenticated)
router = APIRouter(prefix="/admin/core/crm/forms", tags=["Lead Forms"])

# Public router (no auth)
public_router = APIRouter(tags=["Lead Forms Public"])

class FormField(BaseModel):
    type: str = "text"
    label: str
    placeholder: str = ""
    required: bool = False
    options: Optional[List[str]] = None

class CreateFormRequest(BaseModel):
    name: str = Field(..., min_length=1)
    fields: List[FormField]
    thank_you_message: str = "Gracias por tu interes. Te contactaremos pronto."
    redirect_url: str = ""

class UpdateFormRequest(BaseModel):
    name: str = Field(..., min_length=1)
    fields: List[FormField]
    thank_you_message: str = ""
    redirect_url: str = ""
    active: bool = True

# ─── Private Endpoints ────────────────────────────────────────────────────────

@router.get("", dependencies=[Depends(require_role(["ceo", "secretary"]))])
async def list_forms(user_data=Depends(verify_admin_token), tenant_id: int = Depends(get_resolved_tenant_id)):
    return await lead_forms_service.list(tenant_id)

@router.get("/{form_id}", dependencies=[Depends(require_role(["ceo", "secretary"]))])
async def get_form(form_id: str, user_data=Depends(verify_admin_token), tenant_id: int = Depends(get_resolved_tenant_id)):
    form = await lead_forms_service.get(tenant_id, form_id)
    if not form: raise HTTPException(404, "Formulario no encontrado")
    return form

@router.post("", status_code=201, dependencies=[Depends(require_role(["ceo", "secretary"]))])
async def create_form(body: CreateFormRequest, user_data=Depends(verify_admin_token), tenant_id: int = Depends(get_resolved_tenant_id)):
    try: uid = int(user_data.user_id)
    except: uid = None
    return await lead_forms_service.create(tenant_id, body.name, [f.model_dump() for f in body.fields], body.thank_you_message, body.redirect_url, uid)

@router.put("/{form_id}", dependencies=[Depends(require_role(["ceo", "secretary"]))])
async def update_form(form_id: str, body: UpdateFormRequest, user_data=Depends(verify_admin_token), tenant_id: int = Depends(get_resolved_tenant_id)):
    result = await lead_forms_service.update(tenant_id, form_id, body.name, [f.model_dump() for f in body.fields], body.thank_you_message, body.redirect_url, body.active)
    if not result: raise HTTPException(404, "Formulario no encontrado")
    return result

@router.delete("/{form_id}", status_code=204, dependencies=[Depends(require_role(["ceo"]))])
async def delete_form(form_id: str, user_data=Depends(verify_admin_token), tenant_id: int = Depends(get_resolved_tenant_id)):
    if not await lead_forms_service.delete(tenant_id, form_id):
        raise HTTPException(404, "Formulario no encontrado")

@router.get("/{form_id}/stats", dependencies=[Depends(require_role(["ceo", "secretary"]))])
async def get_form_stats(form_id: str, user_data=Depends(verify_admin_token), tenant_id: int = Depends(get_resolved_tenant_id)):
    return await lead_forms_service.get_stats(tenant_id, form_id)

# ─── Public Endpoints (no auth) ──────────────────────────────────────────────

@public_router.get("/f/{slug}")
async def get_public_form(slug: str):
    form = await lead_forms_service.get_by_slug(slug)
    if not form: raise HTTPException(404, "Formulario no encontrado o inactivo")
    return {"name": form["name"], "fields": form["fields"], "thank_you_message": form["thank_you_message"]}

@public_router.post("/f/{slug}/submit")
@limiter.limit("5/minute")
async def submit_public_form(slug: str, request: Request):
    data = await request.json()
    ip = request.client.host if request.client else "unknown"
    result = await lead_forms_service.submit(slug, data, ip)
    if not result: raise HTTPException(404, "Formulario no encontrado o inactivo")
    return result
