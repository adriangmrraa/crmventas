"""
CRM Sales Module - FastAPI Routes
Endpoints for managing leads, WhatsApp connections, templates, and campaigns
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from uuid import UUID

from .models import (
    LeadCreate, LeadUpdate, LeadResponse, LeadAssignRequest, LeadStageUpdateRequest,
    WhatsAppConnectionCreate, WhatsAppConnectionResponse,
    TemplateResponse, TemplateSyncRequest,
    CampaignCreate, CampaignUpdate, CampaignResponse, CampaignLaunchRequest
)
from core.security import get_current_user_context
from db import db

router = APIRouter(prefix="", tags=["CRM Sales"])

# ============================================
# LEADS ENDPOINTS
# ============================================

@router.get("/leads", response_model=List[LeadResponse])
async def list_leads(
    status: Optional[str] = None,
    assigned_seller_id: Optional[UUID] = None,
    limit: int = Query(50, le=100 ),
    offset: int = Query(0, ge=0),
    context: dict = Depends(get_current_user_context)
):
    """
    List all leads for the current tenant with optional filters.
    Supports pagination and filtering by status and assigned seller.
    """
    tenant_id = context["tenant_id"]
    
    query = """
        SELECT id, tenant_id, phone_number, first_name, last_name, email,
               status, stage_id, assigned_seller_id, source, meta_lead_id, tags,
               created_at, updated_at
        FROM leads
        WHERE tenant_id = $1
    """
    params = [tenant_id]
    param_idx = 2
    
    if status:
        query += f" AND status = ${param_idx}"
        params.append(status)
        param_idx += 1
    
    if assigned_seller_id:
        query += f" AND assigned_seller_id = ${param_idx}"
        params.append(assigned_seller_id)
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
    """Assign a lead to a seller"""
    tenant_id = context["tenant_id"]
    
    # Verify seller exists and belongs to tenant
    seller = await db.pool.fetchrow(
        "SELECT id FROM users WHERE id = $1 AND tenant_id = $2",
        request.seller_id, tenant_id
    )
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    
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
