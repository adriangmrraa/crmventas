"""
CRM Sales Module - FastAPI Routes
Endpoints for managing leads, WhatsApp connections, templates, campaigns, and sellers
"""
import uuid as uuid_lib
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from uuid import UUID

from .models import (
    LeadCreate, LeadUpdate, LeadResponse, LeadAssignRequest, LeadStageUpdateRequest,
    ClientCreate, ClientUpdate, ClientResponse,
    WhatsAppConnectionCreate, WhatsAppConnectionResponse,
    TemplateResponse, TemplateSyncRequest,
    CampaignCreate, CampaignUpdate, CampaignResponse, CampaignLaunchRequest,
    SellerCreate, SellerUpdate,
    AgendaEventCreate, AgendaEventUpdate,
)
from core.security import get_current_user_context, verify_admin_token, get_resolved_tenant_id, get_allowed_tenant_ids
from db import db

router = APIRouter(prefix="", tags=["CRM Sales"])

# ============================================
# LEADS ENDPOINTS
# ============================================

@router.get("/leads", response_model=List[LeadResponse])
async def list_leads(
    status: Optional[str] = None,
    assigned_seller_id: Optional[UUID] = None,
    search: Optional[str] = Query(None, description="Search by name, phone, email"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    context: dict = Depends(get_current_user_context)
):
    """
    List all leads for the current tenant with optional filters.
    Excludes soft-deleted (status='deleted'). Supports search by first_name, last_name, phone_number, email.
    """
    tenant_id = context["tenant_id"]
    
    query = """
        SELECT id, tenant_id, phone_number, first_name, last_name, email,
               status, stage_id, assigned_seller_id, source, meta_lead_id, tags,
               created_at, updated_at
        FROM leads
        WHERE tenant_id = $1 AND (status IS NULL OR status != 'deleted')
    """
    params: list = [tenant_id]
    param_idx = 2
    
    if status:
        query += f" AND status = ${param_idx}"
        params.append(status)
        param_idx += 1
    
    if assigned_seller_id:
        query += f" AND assigned_seller_id = ${param_idx}"
        params.append(assigned_seller_id)
        param_idx += 1
    
    if search and search.strip():
        query += f" AND (first_name ILIKE ${param_idx} OR last_name ILIKE ${param_idx} OR phone_number ILIKE ${param_idx} OR email ILIKE ${param_idx})"
        params.append(f"%{search.strip()}%")
        param_idx += 1
    
    query += f" ORDER BY created_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}"
    params.extend([limit, offset])
    
    rows = await db.pool.fetch(query, *params)
    return [dict(row) for row in rows]


@router.post("/leads", response_model=LeadResponse, status_code=201)
async def create_lead(
    lead: LeadCreate,
    context: dict = Depends(get_current_user_context)
):
    """
    Create a new lead for the current tenant.
    Phone number must be unique per tenant.
    """
    tenant_id = context["tenant_id"]
    
    # Check if lead already exists
    existing = await db.pool.fetchrow(
        "SELECT id FROM leads WHERE tenant_id = $1 AND phone_number = $2",
        tenant_id, lead.phone_number
    )
    if existing:
        raise HTTPException(status_code=400, detail="Lead with this phone number already exists")
    
    row = await db.pool.fetchrow("""
        INSERT INTO leads (tenant_id, phone_number, first_name, last_name, email, 
                          status, source, meta_lead_id, tags)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING id, tenant_id, phone_number, first_name, last_name, email,
                  status, stage_id, assigned_seller_id, source, meta_lead_id, tags,
                  created_at, updated_at
    """, tenant_id, lead.phone_number, lead.first_name, lead.last_name, lead.email,
        lead.status, lead.source, lead.meta_lead_id, lead.tags)
    
    return dict(row)


@router.get("/leads/phone/{phone}/context")
async def get_lead_context_by_phone(
    phone: str,
    tenant_id_override: Optional[int] = Query(None),
    context: dict = Depends(get_current_user_context),
    allowed_ids: List[int] = Depends(get_allowed_tenant_ids),
):
    """
    Returns lead context for Chats panel: lead data and upcoming event.
    If tenant_id_override is provided and allowed, use it; else use context tenant_id.
    """
    from core.utils import normalize_phone
    tenant_id = tenant_id_override if (tenant_id_override is not None and tenant_id_override in allowed_ids) else context["tenant_id"]
    norm_phone = normalize_phone(phone)
    lead_row = await db.pool.fetchrow("""
        SELECT id, first_name, last_name, phone_number, status, email
        FROM leads WHERE tenant_id = $1 AND (phone_number = $2 OR phone_number = $3) AND (status IS NULL OR status != 'deleted')
    """, tenant_id, norm_phone, phone)
    if not lead_row:
        return {"lead": None, "upcoming_event": None, "last_event": None, "is_guest": True}
    lead_id = lead_row["id"]
    upcoming = await db.pool.fetchrow("""
        SELECT id, title, start_datetime AS date, end_datetime, status
        FROM seller_agenda_events WHERE tenant_id = $1 AND lead_id = $2 AND start_datetime >= NOW() AND status != 'cancelled'
        ORDER BY start_datetime ASC LIMIT 1
    """, tenant_id, lead_id)
    last_ev = await db.pool.fetchrow("""
        SELECT id, title, start_datetime AS date, status
        FROM seller_agenda_events WHERE tenant_id = $1 AND lead_id = $2 AND start_datetime < NOW()
        ORDER BY start_datetime DESC LIMIT 1
    """, tenant_id, lead_id)
    def _serialize(d):
        if not d: return None
        r = dict(d)
        if r.get("date") and hasattr(r["date"], "isoformat"): r["date"] = r["date"].isoformat()
        if r.get("end_datetime") and hasattr(r["end_datetime"], "isoformat"): r["end_datetime"] = r["end_datetime"].isoformat()
        return r
    return {
        "lead": dict(lead_row),
        "upcoming_event": _serialize(upcoming),
        "last_event": _serialize(last_ev),
        "is_guest": False,
    }


@router.get("/leads/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: UUID,
    context: dict = Depends(get_current_user_context)
):
    """Get a specific lead by ID"""
    tenant_id = context["tenant_id"]
    
    row = await db.pool.fetchrow("""
        SELECT id, tenant_id, phone_number, first_name, last_name, email,
               status, stage_id, assigned_seller_id, source, meta_lead_id, tags,
               created_at, updated_at
        FROM leads
        WHERE id = $1 AND tenant_id = $2
    """, lead_id, tenant_id)
    
    if not row:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return dict(row)


@router.put("/leads/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: UUID,
    lead: LeadUpdate,
    context: dict = Depends(get_current_user_context)
):
    """Update a lead's information"""
    tenant_id = context["tenant_id"]
    
    # Build dynamic UPDATE query
    updates = []
    params = [lead_id, tenant_id]
    param_idx = 3
    
    for field, value in lead.dict(exclude_unset=True).items():
        updates.append(f"{field} = ${param_idx}")
        params.append(value)
        param_idx += 1
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    updates.append(f"updated_at = NOW()")
    
    query = f"""
        UPDATE leads
        SET {', '.join(updates)}
        WHERE id = $1 AND tenant_id = $2
        RETURNING id, tenant_id, phone_number, first_name, last_name, email,
                  status, stage_id, assigned_seller_id, source, meta_lead_id, tags,
                  created_at, updated_at
    """
    
    row = await db.pool.fetchrow(query, *params)
    if not row:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return dict(row)


@router.post("/leads/{lead_id}/assign", response_model=LeadResponse)
async def assign_lead(
    lead_id: UUID,
    request: LeadAssignRequest,
    context: dict = Depends(get_current_user_context)
):
    """Assign a lead to a seller (user_id; seller must be setter/closer with professional row in this tenant)."""
    tenant_id = context["tenant_id"]
    
    seller = await db.pool.fetchrow(
        "SELECT 1 FROM professionals p JOIN users u ON p.user_id = u.id AND u.role IN ('setter', 'closer') WHERE p.user_id = $1 AND p.tenant_id = $2",
        request.seller_id, tenant_id
    )
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found or not in this entity")
    
    row = await db.pool.fetchrow("""
        UPDATE leads
        SET assigned_seller_id = $1, updated_at = NOW()
        WHERE id = $2 AND tenant_id = $3
        RETURNING id, tenant_id, phone_number, first_name, last_name, email,
                  status, stage_id, assigned_seller_id, source, meta_lead_id, tags,
                  created_at, updated_at
    """, request.seller_id, lead_id, tenant_id)
    
    if not row:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return dict(row)


@router.put("/leads/{lead_id}/stage", response_model=LeadResponse)
async def update_lead_stage(
    lead_id: UUID,
    request: LeadStageUpdateRequest,
    context: dict = Depends(get_current_user_context)
):
    """Update a lead's stage/status"""
    tenant_id = context["tenant_id"]
    
    row = await db.pool.fetchrow("""
        UPDATE leads
        SET status = $1, updated_at = NOW()
        WHERE id = $2 AND tenant_id = $3
        RETURNING id, tenant_id, phone_number, first_name, last_name, email,
                  status, stage_id, assigned_seller_id, source, meta_lead_id, tags,
                  created_at, updated_at
    """, request.status, lead_id, tenant_id)
    
    if not row:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return dict(row)


@router.delete("/leads/{lead_id}", status_code=200)
async def delete_lead(
    lead_id: UUID,
    context: dict = Depends(get_current_user_context)
):
    """Soft-delete a lead (set status to 'deleted')."""
    tenant_id = context["tenant_id"]
    result = await db.pool.execute(
        "UPDATE leads SET status = 'deleted', updated_at = NOW() WHERE id = $1 AND tenant_id = $2",
        lead_id, tenant_id
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"status": "deleted", "id": str(lead_id)}


@router.post("/leads/{lead_id}/convert-to-client", response_model=ClientResponse, status_code=201)
async def convert_lead_to_client(
    lead_id: UUID,
    context: dict = Depends(get_current_user_context),
):
    """Convert a lead into a client. Creates the client from lead data and sets lead status to closed_won."""
    tenant_id = context["tenant_id"]
    lead = await db.pool.fetchrow(
        "SELECT id, tenant_id, phone_number, first_name, last_name, email FROM leads WHERE id = $1 AND tenant_id = $2",
        lead_id,
        tenant_id,
    )
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    existing = await db.pool.fetchrow(
        "SELECT id FROM clients WHERE tenant_id = $1 AND phone_number = $2",
        tenant_id,
        lead["phone_number"],
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Ya existe un cliente con ese teléfono. Podés editarlo desde la página de Clientes.",
        )
    row = await db.pool.fetchrow("""
        INSERT INTO clients (tenant_id, phone_number, first_name, last_name, email, status, notes, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, 'active', NULL, NOW(), NOW())
        RETURNING id, tenant_id, phone_number, first_name, last_name, email, status, notes, created_at, updated_at
    """,
        tenant_id,
        lead["phone_number"],
        (lead["first_name"] or "").strip() or None,
        (lead["last_name"] or "").strip() or None,
        (lead["email"] or "").strip() or None,
    )
    await db.pool.execute(
        "UPDATE leads SET status = 'closed_won', updated_at = NOW() WHERE id = $1 AND tenant_id = $2",
        lead_id,
        tenant_id,
    )
    return dict(row)


# ============================================
# CLIENTS ENDPOINTS (tabla clients - página Clientes)
# ============================================

@router.get("/clients", response_model=List[ClientResponse])
async def list_clients(
    search: Optional[str] = Query(None, description="Search by name, phone, email"),
    status: Optional[str] = None,
    limit: int = Query(100, le=200),
    offset: int = Query(0, ge=0),
    context: dict = Depends(get_current_user_context),
):
    """List clients for the current tenant. Excludes soft-deleted (status='deleted')."""
    tenant_id = context["tenant_id"]
    query = """
        SELECT id, tenant_id, phone_number, first_name, last_name, email, status, notes, created_at, updated_at
        FROM clients
        WHERE tenant_id = $1 AND (status IS NULL OR status != 'deleted')
    """
    params: list = [tenant_id]
    idx = 2
    if search and search.strip():
        query += f" AND (first_name ILIKE ${idx} OR last_name ILIKE ${idx} OR phone_number ILIKE ${idx} OR email ILIKE ${idx})"
        params.append(f"%{search.strip()}%")
        idx += 1
    if status:
        query += f" AND status = ${idx}"
        params.append(status)
        idx += 1
    query += f" ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx + 1}"
    params.extend([limit, offset])
    rows = await db.pool.fetch(query, *params)
    return [dict(r) for r in rows]


@router.post("/clients", response_model=ClientResponse, status_code=201)
async def create_client(
    payload: ClientCreate,
    context: dict = Depends(get_current_user_context),
):
    """Create a client. Phone must be unique per tenant."""
    tenant_id = context["tenant_id"]
    existing = await db.pool.fetchrow(
        "SELECT id FROM clients WHERE tenant_id = $1 AND phone_number = $2",
        tenant_id, payload.phone_number.strip()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un cliente con ese teléfono en esta entidad.")
    row = await db.pool.fetchrow("""
        INSERT INTO clients (tenant_id, phone_number, first_name, last_name, email, status, notes, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
        RETURNING id, tenant_id, phone_number, first_name, last_name, email, status, notes, created_at, updated_at
    """,
        tenant_id,
        payload.phone_number.strip(),
        (payload.first_name or "").strip() or None,
        (payload.last_name or "").strip() or None,
        (payload.email or "").strip() or None,
        (payload.status or "active").strip(),
        (payload.notes or "").strip() or None,
    )
    if payload.lead_id:
        await db.pool.execute(
            "UPDATE leads SET status = 'closed_won', updated_at = NOW() WHERE id = $1 AND tenant_id = $2",
            payload.lead_id,
            tenant_id,
        )
    return dict(row)


@router.get("/clients/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: int,
    context: dict = Depends(get_current_user_context),
):
    """Get one client by id."""
    tenant_id = context["tenant_id"]
    row = await db.pool.fetchrow(
        "SELECT id, tenant_id, phone_number, first_name, last_name, email, status, notes, created_at, updated_at FROM clients WHERE id = $1 AND tenant_id = $2",
        client_id, tenant_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return dict(row)


@router.put("/clients/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: int,
    payload: ClientUpdate,
    context: dict = Depends(get_current_user_context),
):
    """Update a client."""
    tenant_id = context["tenant_id"]
    updates = []
    params: list = []
    idx = 1
    if payload.first_name is not None:
        updates.append(f"first_name = ${idx}")
        params.append((payload.first_name or "").strip() or None)
        idx += 1
    if payload.last_name is not None:
        updates.append(f"last_name = ${idx}")
        params.append((payload.last_name or "").strip() or None)
        idx += 1
    if payload.email is not None:
        updates.append(f"email = ${idx}")
        params.append((payload.email or "").strip() or None)
        idx += 1
    if payload.phone_number is not None:
        updates.append(f"phone_number = ${idx}")
        params.append(payload.phone_number.strip())
        idx += 1
    if payload.status is not None:
        updates.append(f"status = ${idx}")
        params.append(payload.status.strip())
        idx += 1
    if payload.notes is not None:
        updates.append(f"notes = ${idx}")
        params.append((payload.notes or "").strip() or None)
        idx += 1
    if not updates:
        row = await db.pool.fetchrow(
            "SELECT id, tenant_id, phone_number, first_name, last_name, email, status, notes, created_at, updated_at FROM clients WHERE id = $1 AND tenant_id = $2",
            client_id, tenant_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        return dict(row)
    updates.append("updated_at = NOW()")
    params.append(client_id)
    params.append(tenant_id)
    where_id_placeholder = len(params) - 1
    where_tenant_placeholder = len(params)
    set_clause = ", ".join(updates)
    row = await db.pool.fetchrow(
        f"UPDATE clients SET {set_clause} WHERE id = ${where_id_placeholder} AND tenant_id = ${where_tenant_placeholder} RETURNING id, tenant_id, phone_number, first_name, last_name, email, status, notes, created_at, updated_at",
        *params
    )
    if not row:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return dict(row)


@router.delete("/clients/{client_id}", status_code=200)
async def delete_client(
    client_id: int,
    context: dict = Depends(get_current_user_context),
):
    """Soft-delete a client (set status to 'deleted')."""
    tenant_id = context["tenant_id"]
    result = await db.pool.execute(
        "UPDATE clients SET status = 'deleted', updated_at = NOW() WHERE id = $1 AND tenant_id = $2",
        client_id, tenant_id
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return {"status": "deleted", "id": client_id}


# ============================================
# WHATSAPP CONNECTIONS ENDPOINTS
# ============================================

@router.get("/whatsapp/connections", response_model=List[WhatsAppConnectionResponse])
async def list_whatsapp_connections(
    context: dict = Depends(get_current_user_context)
):
    """List all WhatsApp connections for the current tenant"""
    tenant_id = context["tenant_id"]
    
    rows = await db.pool.fetch("""
        SELECT id, tenant_id, seller_id, phonenumber_id, waba_id, 
               access_token_vault_id, status, friendly_name, created_at, updated_at
        FROM whatsapp_connections
        WHERE tenant_id = $1
        ORDER BY created_at DESC
    """, tenant_id)
    
    return [dict(row) for row in rows]


@router.post("/whatsapp/connections", response_model=WhatsAppConnectionResponse, status_code=201)
async def create_whatsapp_connection(
    connection: WhatsAppConnectionCreate,
    context: dict = Depends(get_current_user_context)
):
    """
    Create a new WhatsApp connection for the tenant.
    Note: access_token should be stored in Vault before calling this.
    """
    tenant_id = context["tenant_id"]
    
    row = await db.pool.fetchrow("""
        INSERT INTO whatsapp_connections (tenant_id, seller_id, phonenumber_id, waba_id, 
                                          access_token_vault_id, friendly_name, status)
        VALUES ($1, $2, $3, $4, $5, $6, 'active')
        RETURNING id, tenant_id, seller_id, phonenumber_id, waba_id, 
                  access_token_vault_id, status, friendly_name, created_at, updated_at
    """, tenant_id, connection.seller_id, connection.phonenumber_id, connection.waba_id,
        connection.access_token_vault_id, connection.friendly_name)
    
    return dict(row)


# ============================================
# TEMPLATES ENDPOINTS
# ============================================

@router.get("/templates", response_model=List[TemplateResponse])
async def list_templates(
    status: Optional[str] = Query(None, description="Filter by status: APPROVED, REJECTED, etc."),
    context: dict = Depends(get_current_user_context)
):
    """List all WhatsApp templates for the current tenant"""
    tenant_id = context["tenant_id"]
    
    query = """
        SELECT id, tenant_id, meta_template_id, name, language, category, 
               components, status, created_at, updated_at
        FROM templates
        WHERE tenant_id = $1
    """
    params = [tenant_id]
    
    if status:
        query += " AND status = $2"
        params.append(status)
    
    query += " ORDER BY created_at DESC"
    
    rows = await db.pool.fetch(query, *params)
    return [dict(row) for row in rows]


@router.post("/templates/sync")
async def sync_templates(
    request: TemplateSyncRequest,
    context: dict = Depends(get_current_user_context)
):
    """
    Sync templates from Meta API (placeholder).
    Future implementation will fetch from Meta Business API.
    """
    tenant_id = context["tenant_id"]
    
    # TODO: Implement Meta API integration
    return {
        "message": "Template sync not yet implemented",
        "tenant_id": tenant_id,
        "force": request.force
    }


# ============================================
# CAMPAIGNS ENDPOINTS
# ============================================

@router.get("/campaigns", response_model=List[CampaignResponse])
async def list_campaigns(
    status: Optional[str] = None,
    context: dict = Depends(get_current_user_context)
):
    """List all campaigns for the current tenant"""
    tenant_id = context["tenant_id"]
    
    query = """
        SELECT id, tenant_id, name, template_id, target_segment, status, stats,
               scheduled_at, started_at, completed_at, created_at, updated_at
        FROM campaigns
        WHERE tenant_id = $1
    """
    params = [tenant_id]
    
    if status:
        query += " AND status = $2"
        params.append(status)
    
    query += " ORDER BY created_at DESC"
    
    rows = await db.pool.fetch(query, *params)
    return [dict(row) for row in rows]


@router.post("/campaigns", response_model=CampaignResponse, status_code=201)
async def create_campaign(
    campaign: CampaignCreate,
    context: dict = Depends(get_current_user_context)
):
    """Create a new campaign"""
    tenant_id = context["tenant_id"]
    
    # Verify template exists
    template = await db.pool.fetchrow(
        "SELECT id FROM templates WHERE id = $1 AND tenant_id = $2",
        campaign.template_id, tenant_id
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    row = await db.pool.fetchrow("""
        INSERT INTO campaigns (tenant_id, name, template_id, target_segment, scheduled_at, status, stats)
        VALUES ($1, $2, $3, $4, $5, 'draft', '{}')
        RETURNING id, tenant_id, name, template_id, target_segment, status, stats,
                  scheduled_at, started_at, completed_at, created_at, updated_at
    """, tenant_id, campaign.name, campaign.template_id, campaign.target_segment, campaign.scheduled_at)
    
    return dict(row)


@router.post("/campaigns/{campaign_id}/launch", response_model=CampaignResponse)
async def launch_campaign(
    campaign_id: UUID,
    request: CampaignLaunchRequest,
    context: dict = Depends(get_current_user_context)
):
    """
    Launch a campaign (placeholder).
    Future implementation will queue messages for sending.
    """
    tenant_id = context["tenant_id"]
    
    row = await db.pool.fetchrow("""
        UPDATE campaigns
        SET status = 'sending', started_at = NOW()
        WHERE id = $1 AND tenant_id = $2
        RETURNING id, tenant_id, name, template_id, target_segment, status, stats,
                  scheduled_at, started_at, completed_at, created_at, updated_at
    """, campaign_id, tenant_id)
    
    if not row:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # TODO: Implement actual campaign launch logic (queue messages)
    
    return dict(row)


# ============================================
# SELLERS (Vendedores: setter/closer en professionals)
# ============================================

@router.get("/sellers")
async def list_sellers(
    allowed_ids: List[int] = Depends(get_allowed_tenant_ids),
    user_data=Depends(verify_admin_token),
):
    """
    Lista vendedores (professionals con user.role in setter, closer) de tenants CRM.
    Solo tenants con niche_type = 'crm_sales'.
    """
    crm_ids = await db.pool.fetch(
        "SELECT id FROM tenants WHERE id = ANY($1::int[]) AND COALESCE(niche_type, 'crm_sales') = 'crm_sales'",
        allowed_ids
    )
    crm_tenant_ids = [int(r["id"]) for r in crm_ids]
    if not crm_tenant_ids:
        return []
    rows = await db.pool.fetch("""
        SELECT p.id, p.tenant_id, p.user_id, p.first_name, p.last_name, p.email, p.phone_number, p.is_active, u.role
        FROM professionals p
        JOIN users u ON p.user_id = u.id AND u.role IN ('setter', 'closer')
        WHERE p.tenant_id = ANY($1::int[])
        ORDER BY p.tenant_id, p.first_name, p.last_name
    """, crm_tenant_ids)
    return [dict(row) for row in rows]


@router.get("/sellers/by-user/{user_id}")
async def get_sellers_by_user(
    user_id: str,
    allowed_ids: List[int] = Depends(get_allowed_tenant_ids),
    user_data=Depends(verify_admin_token),
):
    """Obtiene los registros de vendedor (professionals) para un user_id en tenants CRM."""
    try:
        uid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="user_id inválido")
    crm_ids = await db.pool.fetch(
        "SELECT id FROM tenants WHERE id = ANY($1::int[]) AND COALESCE(niche_type, 'crm_sales') = 'crm_sales'",
        allowed_ids
    )
    crm_tenant_ids = [int(r["id"]) for r in crm_ids]
    if not crm_tenant_ids:
        return []
    rows = await db.pool.fetch("""
        SELECT p.*, u.role
        FROM professionals p
        JOIN users u ON p.user_id = u.id AND u.role IN ('setter', 'closer')
        WHERE p.user_id = $1 AND p.tenant_id = ANY($2::int[])
    """, uid, crm_tenant_ids)
    return [dict(r) for r in rows]


@router.put("/sellers/{id}")
async def update_seller(
    id: int,
    payload: SellerUpdate,
    allowed_ids: List[int] = Depends(get_allowed_tenant_ids),
    user_data=Depends(verify_admin_token),
):
    """Actualiza datos del vendedor (tabla professionals). Solo en tenants CRM y si es setter/closer."""
    # Ensure this professional is a seller in a CRM tenant
    row = await db.pool.fetchrow("""
        SELECT p.id, p.tenant_id FROM professionals p
        JOIN users u ON p.user_id = u.id AND u.role IN ('setter', 'closer')
        JOIN tenants t ON t.id = p.tenant_id AND COALESCE(t.niche_type, 'dental') = 'crm_sales'
        WHERE p.id = $1 AND p.tenant_id = ANY($2::int[])
    """, id, allowed_ids)
    if not row:
        raise HTTPException(status_code=404, detail="Vendedor no encontrado")
    updates = []
    params = []
    idx = 1
    if payload.first_name is not None:
        updates.append(f"first_name = ${idx}")
        params.append(payload.first_name)
        idx += 1
    if payload.last_name is not None:
        updates.append(f"last_name = ${idx}")
        params.append(payload.last_name)
        idx += 1
    if payload.email is not None:
        updates.append(f"email = ${idx}")
        params.append(payload.email)
        idx += 1
    if payload.phone_number is not None:
        updates.append(f"phone_number = ${idx}")
        params.append(payload.phone_number)
        idx += 1
    if payload.is_active is not None:
        updates.append(f"is_active = ${idx}")
        params.append(payload.is_active)
        idx += 1
    if not updates:
        return {"id": id, "status": "unchanged"}
    params.append(id)
    updates.append("updated_at = NOW()")
    set_clause = ", ".join(updates)
    where_idx = len(params)
    await db.pool.execute(f"UPDATE professionals SET {set_clause} WHERE id = ${where_idx}", *params)
    return {"id": id, "status": "updated"}


@router.get("/sellers/{id}/analytics")
async def get_seller_analytics(
    id: int,
    tenant_id: int = Query(..., description="Tenant ID for scope"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    allowed_ids: List[int] = Depends(get_allowed_tenant_ids),
    user_data=Depends(verify_admin_token),
):
    """
    KPIs del vendedor para CRM: leads asignados, por estado, etc.
    id = professional id; tenant_id = scope; leads.assigned_seller_id = user_id del vendedor.
    """
    if tenant_id not in allowed_ids:
        raise HTTPException(status_code=403, detail="Sin acceso a este tenant")
    seller = await db.pool.fetchrow("""
        SELECT p.id, p.user_id, p.first_name, p.last_name
        FROM professionals p
        JOIN users u ON p.user_id = u.id AND u.role IN ('setter', 'closer')
        JOIN tenants t ON t.id = p.tenant_id AND COALESCE(t.niche_type, 'dental') = 'crm_sales'
        WHERE p.id = $1 AND p.tenant_id = $2
    """, id, tenant_id)
    if not seller:
        raise HTTPException(status_code=404, detail="Vendedor no encontrado")
    user_id = seller["user_id"]
    today = datetime.utcnow()
    if start_date and end_date:
        try:
            start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        except ValueError:
            start = today.replace(day=1)
            end = today
    else:
        start = today.replace(day=1)
        end = today
    # Leads asignados a este vendedor en el rango
    by_status = await db.pool.fetch("""
        SELECT status, COUNT(*) AS count
        FROM leads
        WHERE tenant_id = $1 AND assigned_seller_id = $2
        AND created_at BETWEEN $3 AND $4
        GROUP BY status
    """, tenant_id, user_id, start, end)
    total = await db.pool.fetchval("""
        SELECT COUNT(*) FROM leads
        WHERE tenant_id = $1 AND assigned_seller_id = $2
        AND created_at BETWEEN $3 AND $4
    """, tenant_id, user_id, start, end)
    return {
        "id": id,
        "user_id": str(user_id),
        "name": f"{seller['first_name'] or ''} {seller['last_name'] or ''}".strip(),
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "total_leads": total or 0,
        "by_status": {r["status"]: r["count"] for r in by_status},
    }


@router.post("/sellers", status_code=201)
async def create_seller(
    payload: SellerCreate,
    resolved_tenant_id: int = Depends(get_resolved_tenant_id),
    allowed_ids: List[int] = Depends(get_allowed_tenant_ids),
    user_data=Depends(verify_admin_token),
):
    """
    Crea un vendedor (user setter/closer + fila en professionals) en un tenant CRM.
    Solo en tenants con niche_type = crm_sales.
    """
    if payload.role not in ("setter", "closer"):
        raise HTTPException(status_code=400, detail="role debe ser setter o closer")
    tenant_id = int(payload.tenant_id) if payload.tenant_id is not None else resolved_tenant_id
    if tenant_id not in allowed_ids:
        raise HTTPException(status_code=403, detail="Sin acceso a este tenant")
    niche = await db.pool.fetchval("SELECT COALESCE(niche_type, 'crm_sales') FROM tenants WHERE id = $1", tenant_id)
    if niche != "crm_sales":
        raise HTTPException(status_code=400, detail="El tenant no es de tipo CRM ventas")
    existing_user = await db.pool.fetchrow("SELECT id FROM users WHERE email = $1", payload.email)
    if existing_user:
        uid = existing_user["id"]
        if await db.pool.fetchval("SELECT 1 FROM professionals WHERE user_id = $1 AND tenant_id = $2", uid, tenant_id):
            raise HTTPException(status_code=409, detail="Ese correo ya está vinculado como vendedor en esta entidad.")
    else:
        uid = uuid_lib.uuid4()
        await db.pool.execute(
            "INSERT INTO users (id, email, password_hash, role, first_name, last_name, status) VALUES ($1, $2, 'hash_placeholder', $3, $4, $5, 'active')",
            uid, payload.email, payload.role, (payload.first_name or "").strip(), (payload.last_name or "").strip()
        )
    first_name = (payload.first_name or "").strip() or "Vendedor"
    last_name = (payload.last_name or "").strip() or " "
    await db.pool.execute("""
        INSERT INTO professionals (tenant_id, user_id, first_name, last_name, email, phone_number, is_active, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, TRUE, NOW(), NOW())
    """, tenant_id, uid, first_name, last_name, payload.email, (payload.phone_number or "").strip() or None)
    return {"status": "created", "user_id": str(uid)}


# ============================================
# SELLER AGENDA (eventos por vendedor)
# ============================================

@router.get("/agenda/events")
async def list_agenda_events(
    start_date: str = Query(..., description="ISO start date"),
    end_date: str = Query(..., description="ISO end date"),
    seller_id: Optional[int] = Query(None, description="Filter by seller (professional) ID"),
    context: dict = Depends(get_current_user_context),
    allowed_ids: List[int] = Depends(get_allowed_tenant_ids),
):
    """List agenda events for the current tenant in the given date range. Optional filter by seller."""
    tenant_id = context["tenant_id"]
    if tenant_id not in allowed_ids:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Sin acceso a este tenant")
    try:
        start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="start_date and end_date must be valid ISO 8601 strings")
    query = """
        SELECT e.id, e.tenant_id, e.seller_id, e.title, e.start_datetime, e.end_datetime,
               e.lead_id, e.client_id, e.notes, e.source, e.status, e.created_at, e.updated_at,
               p.first_name AS seller_first_name, p.last_name AS seller_last_name
        FROM seller_agenda_events e
        JOIN professionals p ON p.id = e.seller_id
        JOIN users u ON u.id = p.user_id AND u.role IN ('setter', 'closer')
        JOIN tenants t ON t.id = e.tenant_id AND COALESCE(t.niche_type, 'dental') = 'crm_sales'
        WHERE e.tenant_id = $1 AND e.status != 'cancelled'
          AND e.start_datetime < $3 AND e.end_datetime > $2
    """
    params: list = [tenant_id, start_dt, end_dt]
    if seller_id is not None:
        query += " AND e.seller_id = $4"
        params.append(seller_id)
    query += " ORDER BY e.start_datetime ASC"
    rows = await db.pool.fetch(query, *params)
    return [
        {
            **dict(r),
            "seller_name": f"{r.get('seller_first_name') or ''} {r.get('seller_last_name') or ''}".strip(),
            "appointment_datetime": r["start_datetime"].isoformat() if r.get("start_datetime") else None,
            "end_datetime": r["end_datetime"].isoformat() if r.get("end_datetime") else None,
        }
        for r in rows
    ]


@router.post("/agenda/events", status_code=201)
async def create_agenda_event(
    payload: AgendaEventCreate,
    context: dict = Depends(get_current_user_context),
    allowed_ids: List[int] = Depends(get_allowed_tenant_ids),
):
    """Create an agenda event for a seller."""
    tenant_id = context["tenant_id"]
    if tenant_id not in allowed_ids:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Sin acceso a este tenant")
    # Verify seller belongs to this tenant and is setter/closer
    seller = await db.pool.fetchrow("""
        SELECT p.id FROM professionals p
        JOIN users u ON p.user_id = u.id AND u.role IN ('setter', 'closer')
        JOIN tenants t ON t.id = p.tenant_id AND COALESCE(t.niche_type, 'dental') = 'crm_sales'
        WHERE p.id = $1 AND p.tenant_id = $2
    """, payload.seller_id, tenant_id)
    if not seller:
        raise HTTPException(status_code=404, detail="Vendedor no encontrado en esta entidad")
    row = await db.pool.fetchrow("""
        INSERT INTO seller_agenda_events (tenant_id, seller_id, title, start_datetime, end_datetime, lead_id, client_id, notes, source, status)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'scheduled')
        RETURNING id, tenant_id, seller_id, title, start_datetime, end_datetime, lead_id, client_id, notes, source, status, created_at, updated_at
    """, tenant_id, payload.seller_id, payload.title, payload.start_datetime, payload.end_datetime,
        payload.lead_id, payload.client_id, payload.notes, payload.source)
    return dict(row)


@router.put("/agenda/events/{event_id}")
async def update_agenda_event(
    event_id: UUID,
    payload: AgendaEventUpdate,
    context: dict = Depends(get_current_user_context),
    allowed_ids: List[int] = Depends(get_allowed_tenant_ids),
):
    """Update an agenda event."""
    tenant_id = context["tenant_id"]
    if tenant_id not in allowed_ids:
        raise HTTPException(status_code=403, detail="Sin acceso a este tenant")
    existing = await db.pool.fetchrow(
        "SELECT id FROM seller_agenda_events WHERE id = $1 AND tenant_id = $2",
        event_id, tenant_id
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    updates, params = [], []
    pos = 1
    if payload.title is not None:
        updates.append(f"title = ${pos}"); params.append(payload.title); pos += 1
    if payload.start_datetime is not None:
        updates.append(f"start_datetime = ${pos}"); params.append(payload.start_datetime); pos += 1
    if payload.end_datetime is not None:
        updates.append(f"end_datetime = ${pos}"); params.append(payload.end_datetime); pos += 1
    if payload.lead_id is not None:
        updates.append(f"lead_id = ${pos}"); params.append(payload.lead_id); pos += 1
    if payload.client_id is not None:
        updates.append(f"client_id = ${pos}"); params.append(payload.client_id); pos += 1
    if payload.notes is not None:
        updates.append(f"notes = ${pos}"); params.append(payload.notes); pos += 1
    if payload.status is not None and payload.status in ("scheduled", "completed", "cancelled"):
        updates.append(f"status = ${pos}"); params.append(payload.status); pos += 1
    if not updates:
        return {"status": "ok"}
    params.extend([event_id, tenant_id])
    await db.pool.execute(
        "UPDATE seller_agenda_events SET " + ", ".join(updates) + f", updated_at = NOW() WHERE id = ${pos} AND tenant_id = ${pos + 1}",
        *params
    )
    return {"status": "ok"}


@router.delete("/agenda/events/{event_id}")
async def delete_agenda_event(
    event_id: UUID,
    context: dict = Depends(get_current_user_context),
    allowed_ids: List[int] = Depends(get_allowed_tenant_ids),
):
    """Cancel (soft) or delete an agenda event. We set status to cancelled."""
    tenant_id = context["tenant_id"]
    if tenant_id not in allowed_ids:
        raise HTTPException(status_code=403, detail="Sin acceso a este tenant")
    result = await db.pool.execute(
        "UPDATE seller_agenda_events SET status = 'cancelled', updated_at = NOW() WHERE id = $1 AND tenant_id = $2",
        event_id, tenant_id
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    return {"status": "cancelled"}
