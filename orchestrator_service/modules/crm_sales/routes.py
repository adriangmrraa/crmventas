"""
CRM Sales Module - FastAPI Routes
Endpoints for managing leads, WhatsApp connections, templates, campaigns, and sellers
"""
import uuid as uuid_lib
import os
import json
import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Request
from typing import List, Optional, Any
from uuid import UUID
import httpx
import logging
from core.rate_limiter import limiter

logger = logging.getLogger("orchestrator")

from modules.crm_sales.models import (
    LeadCreate, LeadUpdate, LeadResponse, LeadAssignRequest, LeadStageUpdateRequest,
    ClientCreate, ClientUpdate, ClientResponse,
    WhatsAppConnectionCreate, WhatsAppConnectionResponse,
    TemplateResponse, TemplateSyncRequest,
    CampaignCreate, CampaignUpdate, CampaignResponse, CampaignLaunchRequest,
    SellerCreate, SellerUpdate,
    AgendaEventCreate, AgendaEventUpdate,
    ProspectingScrapeRequest, ProspectingLeadResponse, ProspectingSendRequest,
    CrmDashboardStats,
)
from core.security import get_current_user_context, verify_admin_token, get_resolved_tenant_id, get_allowed_tenant_ids, audit_access
from core.utils import normalize_phone
from db import db

router = APIRouter(prefix="", tags=["CRM Sales"])
APIFY_ACTOR_URL = "https://api.apify.com/v2/acts/compass~crawler-google-places/run-sync-get-dataset-items"
INTERNAL_API_TOKEN = os.getenv("INTERNAL_API_TOKEN", "internal-secret-token")
WHATSAPP_SERVICE_URL = os.getenv("WHATSAPP_SERVICE_URL", "http://whatsapp_service:8002")

# ============================================
# ROUTERS AND DEPENDENCIES INCLUSION
# ============================================
from routes.lead_status_routes import router as lead_status_router
router.include_router(lead_status_router)

# ============================================
# LEADS ENDPOINTS
# ============================================

@router.get("/leads", response_model=List[LeadResponse])
@audit_access("list_leads")
@limiter.limit("100/minute")
async def list_leads(
    request: Request,
    status: Optional[str] = None,
    assigned_seller_id: Optional[UUID] = None,
    search: Optional[str] = Query(None, description="Search by name, phone, email"),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    context: dict = Depends(get_current_user_context)
):
    """
    List all leads for the current tenant with optional filters.
    Excludes soft-deleted (status='deleted'). Supports search by first_name, last_name, phone_number, email.
    """
    tenant_id = context["tenant_id"]
    role = context.get("role") or context.get("user_role") or ""
    user_id = context.get("user_id") or context.get("id")

    query = """
        SELECT id, tenant_id, phone_number, first_name, last_name, email,
               status, stage_id, assigned_seller_id, source, meta_lead_id, tags,
               apify_title, apify_category_name, apify_address, apify_city, apify_state, apify_country_code,
               apify_website, apify_place_id, apify_total_score, apify_reviews_count, apify_scraped_at,
               prospecting_niche, prospecting_location_query,
               outreach_message_sent, outreach_send_requested, outreach_last_requested_at, outreach_last_sent_at,
               created_at, updated_at
        FROM leads
        WHERE tenant_id = $1 AND (status IS NULL OR status != 'deleted')
    """
    params: list = [tenant_id]
    param_idx = 2

    # Role-based filtering: Setters and Closers only see assigned leads
    if role in ['setter', 'closer']:
        query += f" AND assigned_seller_id = ${param_idx}"
        params.append(UUID(user_id) if isinstance(user_id, str) else user_id)
        param_idx += 1
    
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
    role = context.get("role") or context.get("user_role") or ""
    user_id = context.get("user_id") or context.get("id")
    
    # Ownership Check: Setters and Closers can only edit their assigned leads
    if role in ["setter", "closer"]:
        existing_lead = await db.pool.fetchrow(
            "SELECT assigned_seller_id FROM leads WHERE id = $1 AND tenant_id = $2",
            lead_id, tenant_id
        )
        if not existing_lead:
            raise HTTPException(status_code=404, detail="Lead not found")
            
        assigned_id = existing_lead["assigned_seller_id"]
        if not assigned_id or str(assigned_id) != str(user_id):
            raise HTTPException(status_code=403, detail="No tienes permiso para editar este Lead")
    
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
@audit_access("list_clients")
@limiter.limit("100/minute")
async def list_clients(
    request: Request,
    search: Optional[str] = Query(None, description="Search by name, phone, email"),
    status: Optional[str] = None,
    limit: int = Query(100, le=200),
    offset: int = Query(0, ge=0),
    context: dict = Depends(get_current_user_context),
):
    """List clients for the current tenant. Excludes soft-deleted (status='deleted')."""
    tenant_id = context["tenant_id"]
    role = context.get("role") or context.get("user_role") or ""
    user_id = context.get("user_id") or context.get("id")

    query = """
        SELECT id, tenant_id, phone_number, first_name, last_name, email, status, notes, created_at, updated_at
        FROM clients
        WHERE tenant_id = $1 AND (status IS NULL OR status != 'deleted')
    """
    params: list = [tenant_id]
    idx = 2

    # Role-based filtering: Setters and Closers only see assigned clients? 
    # Usually clients are linked to leads. If clients has assigned_seller_id, we filter here.
    # checking schema... clients usually don't have assigned_seller_id in this schema yet, 
    # but based on prompt "access to clients but ONLY to theirs", we check if we need to filter by lead association.
    # For now, if the column exists or via join.
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
# CRM DASHBOARD STATS ENDPOINTS
# ============================================

@router.get("/stats/summary", response_model=CrmDashboardStats)
async def get_crm_dashboard_stats(
    range: str = Query("weekly", description="Time range: weekly, monthly"),
    context: dict = Depends(get_current_user_context)
):
    """
    Get CRM dashboard statistics for the current tenant.
    Returns metrics specific to CRM sales (leads, clients, revenue).
    """
    tenant_id = context["tenant_id"]
    role = context.get("role") or context.get("user_role") or ""
    user_id = context.get("user_id") or context.get("id")
    seller_uid = UUID(user_id) if isinstance(user_id, str) else user_id

    # Base WHERE clause
    where_base = "WHERE tenant_id = $1"
    where_params = [tenant_id]
    
    # If seller, restrict to their leads
    if role in ['setter', 'closer']:
        where_base += " AND assigned_seller_id = $2"
        where_params.append(seller_uid)

    try:
        # Determine days based on range
        days = 7 if range == "weekly" else 30
        interval = f"INTERVAL '{days} days'"
        
        # 1. Total leads (all time)
        total_leads = await db.pool.fetchval(f"""
            SELECT COUNT(*) FROM leads 
            {where_base} AND status != 'deleted'
        """, *where_params) or 0
        
        # 2. Total clients (all time)
        # Note: clients usually derived from won leads. 
        # For simplicity, if role is seller, we count clients linked to THEIR won leads.
        if role in ['setter', 'closer']:
            total_clients = await db.pool.fetchval("""
                SELECT COUNT(DISTINCT phone_number) FROM leads 
                WHERE tenant_id = $1 AND assigned_seller_id = $2 AND status = 'closed_won'
            """, tenant_id, seller_uid) or 0
        else:
            total_clients = await db.pool.fetchval("""
                SELECT COUNT(*) FROM clients 
                WHERE tenant_id = $1
            """, tenant_id) or 0
        
        # 3. Active leads (recent, not converted)
        active_leads = await db.pool.fetchval(f"""
            SELECT COUNT(*) FROM leads 
            {where_base} 
            AND status NOT IN ('closed_won', 'closed_lost', 'deleted')
            AND created_at >= NOW() - {interval}
        """, *where_params) or 0
        
        # 4. Converted leads (closed won in period)
        converted_leads = await db.pool.fetchval(f"""
            SELECT COUNT(*) FROM leads 
            {where_base} 
            AND status = 'closed_won'
            AND created_at >= NOW() - {interval}
        """, *where_params) or 0
        
        # 5. Total revenue (estimated from converted leads: $1000 per lead)
        total_revenue = converted_leads * 1000.0
        
        # 6. Conversion rate (based on period)
        period_leads = await db.pool.fetchval(f"""
            SELECT COUNT(*) FROM leads 
            {where_base} 
            AND status != 'deleted'
            AND created_at >= NOW() - {interval}
        """, *where_params) or 0
        
        conversion_rate = (converted_leads / period_leads * 100) if period_leads > 0 else 0.0
        
        # 7. Status distribution
        status_rows = await db.pool.fetch(f"""
            SELECT status, COUNT(*) as count FROM leads
            {where_base} AND status != 'deleted'
            GROUP BY status
        """, *where_params)
        
        status_colors = {
            'new': '#3b82f6',
            'contacted': '#f59e0b',
            'interested': '#8b5cf6',
            'negotiation': '#f97316',
            'closed_won': '#10b981',
            'closed_lost': '#ef4444'
        }
        
        status_distribution = [
            {"status": r["status"] or "new", "count": r["count"], "color": status_colors.get(r["status"], "#94a3b8")}
            for r in status_rows
        ]

        # 8. Revenue & Leads Trend (Last 6 months)
        # Using joins for trend to ensure seller filtering
        trend_rows = await db.pool.fetch(f"""
            WITH months AS (
                SELECT generate_series(
                    date_trunc('month', CURRENT_DATE - INTERVAL '5 months'),
                    date_trunc('month', CURRENT_DATE),
                    '1 month'::interval
                ) as month_start
            )
            SELECT 
                to_char(m.month_start, 'Mon') as month_label,
                COUNT(l.id) as leads_count,
                COALESCE(SUM(CASE WHEN l.status = 'closed_won' THEN 1000.0 ELSE 0 END), 0) as revenue
            FROM months m
            LEFT JOIN leads l ON date_trunc('month', l.created_at) = m.month_start 
              AND l.tenant_id = $1 AND l.status != 'deleted'
              { "AND l.assigned_seller_id = $2" if role in ['setter', 'closer'] else "" }
            GROUP BY m.month_start
            ORDER BY m.month_start ASC
        """, *where_params)
        
        revenue_leads_trend = [
            {"month": r["month_label"], "revenue": float(r["revenue"]), "leads": r["leads_count"]}
            for r in trend_rows
        ]

        # 9. Recent leads
        recent_leads = await db.pool.fetch("""
            SELECT id, first_name, last_name, phone_number, status, 
                   created_at, source, prospecting_niche
            FROM leads 
            WHERE tenant_id = $1 
            AND status != 'deleted'
            ORDER BY created_at DESC 
            LIMIT 5
        """, tenant_id)
        
        formatted_recent_leads = []
        for lead in recent_leads:
            name = f"{lead['first_name'] or ''} {lead['last_name'] or ''}".strip() or "Lead sin nombre"
            formatted_recent_leads.append({
                "id": str(lead["id"]),
                "name": name,
                "phone": lead["phone_number"] or "Sin teléfono",
                "status": lead["status"] or "new",
                "source": lead["source"] or "manual",
                "niche": lead["prospecting_niche"] or "General",
                "created_at": lead["created_at"].isoformat() if lead["created_at"] else None
            })
        
        return CrmDashboardStats(
            total_leads=total_leads,
            total_clients=total_clients,
            active_leads=active_leads,
            converted_leads=converted_leads,
            total_revenue=total_revenue,
            conversion_rate=round(conversion_rate, 1),
            status_distribution=status_distribution,
            revenue_leads_trend=revenue_leads_trend,
            recent_leads=formatted_recent_leads
        )
        
    except Exception as e:
        logger.error(f"Error getting CRM dashboard stats: {e}")
        return CrmDashboardStats(
            total_leads=0,
            total_clients=0,
            active_leads=0,
            converted_leads=0,
            total_revenue=0.0,
            conversion_rate=0.0,
            status_distribution=[],
            revenue_leads_trend=[],
            recent_leads=[]
        )


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
# PROSPECTING ENDPOINTS (APIFY)
# ============================================

# Country prefix table (longest prefix first for correct matching)
_COUNTRY_PREFIXES = [
    # NANP specifics
    ("1787", "PR"), ("1939", "PR"), ("1809", "DO"), ("1829", "DO"), ("1849", "DO"),
    # Hispanoamérica
    ("549", "AR"), ("54", "AR"), ("591", "BO"), ("56", "CL"), ("57", "CO"),
    ("506", "CR"), ("53", "CU"), ("593", "EC"), ("503", "SV"), ("502", "GT"),
    ("504", "HN"), ("521", "MX"), ("52", "MX"), ("505", "NI"), ("507", "PA"),
    ("595", "PY"), ("51", "PE"), ("598", "UY"), ("58", "VE"), ("34", "ES"),
    ("240", "GQ"),
    # LatAm no hispana
    ("55", "BR"), ("501", "BZ"), ("509", "HT"), ("592", "GY"), ("597", "SR"), ("594", "GF"),
    # NANP genérico
    ("1", "US"),
]

# Map country names / keywords to dial codes (for location inference)
_LOCATION_COUNTRY_MAP = {
    "argentina": "54", "ar": "54",
    "argentina": "54",
    "colombia": "57", "co": "57",
    "chile": "56", "cl": "56",
    "mexico": "52", "méxico": "52", "mx": "52",
    "peru": "51", "perú": "51", "pe": "51",
    "uruguay": "598", "uy": "598",
    "paraguay": "595", "py": "595",
    "bolivia": "591", "bo": "591",
    "ecuador": "593", "ec": "593",
    "venezuela": "58", "ve": "58",
    "brasil": "55", "brazil": "55", "br": "55",
    "españa": "34", "spain": "34", "es": "34",
    "costa rica": "506", "cr": "506",
    "panamá": "507", "panama": "507", "pa": "507",
    "guatemala": "502", "gt": "502",
    "honduras": "504", "hn": "504",
    "el salvador": "503", "sv": "503",
    "nicaragua": "505", "ni": "505",
    "cuba": "53",
    "united states": "1", "usa": "1", "us": "1",
    "estados unidos": "1",
    "puerto rico": "1787",
    "dominican republic": "1809", "república dominicana": "1809",
}


def _infer_country_code(location: str) -> str:
    """Infer dial code from a location query string (e.g. 'Medellín, Colombia' -> '57')."""
    location_lower = location.lower().strip()
    # Try multi-word matches first (e.g. "costa rica", "el salvador")
    for keyword in sorted(_LOCATION_COUNTRY_MAP.keys(), key=len, reverse=True):
        if keyword in location_lower:
            return _LOCATION_COUNTRY_MAP[keyword]
    return "54"  # Default: Argentina


def _normalize_phone_e164(raw: str, default_country_code: str = "54") -> Optional[str]:
    """
    Ports the phone normalization logic from the n8n workflow (Scrap Phones.json).
    Returns E.164 digits (without +) or None if invalid.
    """
    import re
    digits = re.sub(r"\D", "", raw or "")
    if not digits:
        return None

    # Check for garbage (repeating sequences like 0000000 or 1111111)
    if re.match(r"^(\d)\1{6,}$", digits):
        return None
    # Strip leading 00 (international prefix alternative to +)
    digits = re.sub(r"^00", "", digits)
    # Strip leading single 0 (local trunk)
    digits = re.sub(r"^0+", "", digits)

    # Already has a known country code?
    has_cc = False
    for cc, _ in sorted(_COUNTRY_PREFIXES, key=lambda x: len(x[0]), reverse=True):
        if digits.startswith(cc):
            has_cc = True
            break

    if not has_cc:
        # 10-digit NANP
        if len(digits) == 10:
            digits = "1" + digits
        else:
            digits = default_country_code + digits

    # Arg-specific: ensure 549 prefix for mobile
    if digits.startswith("54") and not digits.startswith("549"):
        digits = "54" + "9" + digits[2:]
    # Arg-specific: remove "15" after area code (e.g. 5492215... -> 5492 ...)
    import re as _re
    if digits.startswith("549"):
        digits = _re.sub(r"^(549\d{2,5})15", r"\1", digits)

    # Mex: ensure 521
    if digits.startswith("52") and not digits.startswith("521"):
        digits = "52" + "1" + digits[2:]

    # Validate E.164 length (8-15 digits)
    if len(digits) < 8 or len(digits) > 15:
        return None
    return digits


async def _extract_phone_from_website(url: str, default_cc: str = "54") -> Optional[str]:
    """
    Secondary scrape: visit the website and extract the best phone number.
    Ports the phone extraction regex logic from n8n Scrap Phones workflow.
    """
    import re
    if not url:
        return None
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; PhoneScraper/1.0)"})
            html = resp.text
    except Exception:
        return None

    # 1) Extract tel: and wa.me links (highest quality)
    link_phones = []
    for href in re.findall(r'href=["\']([^"\']+)["\']', html):
        tel_match = re.match(r'^tel:([\d\s\-\+\(\)]+)', href, re.IGNORECASE)
        if tel_match:
            link_phones.append(tel_match.group(1))
        wa_match = re.search(r'wa\.me/(\d{7,15})', href, re.IGNORECASE)
        if wa_match:
            link_phones.append(wa_match.group(1))

    # 2) Strip tags, extract text near phone-related keywords
    cleaned = re.sub(r'<script[\s\S]*?</script>', '', html, flags=re.IGNORECASE)
    cleaned = re.sub(r'<style[\s\S]*?</style>', '', cleaned, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', cleaned)
    text = re.sub(r'\s+', ' ', text)

    keyword_frags = [
        frag for frag in re.split(r'(?<=[.!?])\s+', text)
        if re.search(r'tel|teléfono|telefono|whatsapp|contacto|celular|llamanos', frag, re.IGNORECASE)
    ]
    raw_candidates = []
    for frag in keyword_frags:
        raw_candidates.extend(re.findall(r'(?:\+?\d[\d()\s\-]{6,}\d)', frag))
    raw_candidates.extend(link_phones)

    # 3) Normalize and validate candidates
    valid = []
    seen = set()
    for raw in raw_candidates:
        norm = _normalize_phone_e164(raw, default_cc)
        if norm and norm not in seen:
            seen.add(norm)
            valid.append(norm)

    if not valid:
        return None

    # 4) Prioritize by country prefix (same priority as n8n)
    def score(num: str) -> int:
        for i, (cc, _) in enumerate(sorted(_COUNTRY_PREFIXES, key=lambda x: len(x[0]), reverse=True)):
            if num.startswith(cc):
                return len(_COUNTRY_PREFIXES) - i
        return 0

    valid.sort(key=score, reverse=True)
    # n8n logic also prefers numbers that look like mobile (e.g. 549 in Arg)
    mobile_priority = [v for v in valid if v.startswith("549") or v.startswith("521")]
    return mobile_priority[0] if mobile_priority else valid[0]


def _extract_social_links(apify_item: dict) -> dict:
    """
    Extracts social media profile URLs (IG, FB, LI) from Apify's webResults.
    """
    socials = {}
    web_results = apify_item.get("webResults") or []
    for res in web_results:
        url = (res.get("url") or "").lower()
        if "instagram.com/" in url and not socials.get("instagram"):
            socials["instagram"] = res.get("url")
        elif "facebook.com/" in url and not socials.get("facebook"):
            socials["facebook"] = res.get("url")
        elif "linkedin.com/" in url and not socials.get("linkedin"):
            socials["linkedin"] = res.get("url")
    return socials


def _resolve_target_tenant_id(context: dict, allowed_ids: List[int], tenant_id: int) -> int:
    if tenant_id not in allowed_ids:
        raise HTTPException(status_code=403, detail="Sin acceso al tenant seleccionado")
    return tenant_id

async def _send_prospecting_outreach_background(
    tenant_id: int, 
    template_name: str, 
    language: str, 
    lead_ids: Optional[List[str]] = None,
    only_pending: bool = True
):
    """Background task to send bulk WhatsApp templates to leads."""
    logger.info(f"outreach_background_start: tenant_id={tenant_id}, template={template_name}")
    
    # 1. Fetch leads
    query = """
        SELECT id, phone_number, first_name, apify_city
        FROM leads
        WHERE tenant_id = $1 AND (status IS NULL OR status != 'deleted')
          AND ($2::bool = FALSE OR outreach_message_sent = FALSE)
          AND phone_number ~ '^\d{8,15}$'
    """
    params: List[Any] = [tenant_id, only_pending]
    if lead_ids:
        query += " AND id = ANY($3::uuid[])"
        params.append([uuid_lib.UUID(x) for x in lead_ids])
    
    leads = await db.pool.fetch(query, *params)
    logger.info(f"outreach_leads_found: count={len(leads)}, tenant_id={tenant_id}")

    # 2. Get business number
    bot_phone = await db.pool.fetchval("SELECT bot_phone_number FROM tenants WHERE id = $1", tenant_id)
    if not bot_phone:
        logger.error(f"outreach_failed_no_bot_phone: tenant_id={tenant_id}")
        return

    # 3. Send to each lead
    async with httpx.AsyncClient(timeout=20.0) as client:
        for lead in leads:
            phone = normalize_phone(lead["phone_number"])
            first_name = lead["first_name"] or " "
            city = lead["apify_city"] or " "
            
            # Map components: {{1}} = name, {{2}} = city
            components = [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": first_name},
                        {"type": "text", "text": city}
                    ]
                }
            ]
            
            try:
                payload = {
                    "to": phone,
                    "type": "template",
                    "template_name": template_name,
                    "language": language,
                    "components": components
                }
                
                resp = await client.post(
                    f"{WHATSAPP_SERVICE_URL}/send",
                    json=payload,
                    headers={"X-Internal-Token": INTERNAL_API_TOKEN, "X-Correlation-Id": str(uuid_lib.uuid4())},
                    params={"from_number": bot_phone}
                )
                
                if resp.status_code == 200:
                    # Mark as sent
                    await db.pool.execute(
                        "UPDATE leads SET outreach_message_sent = TRUE, outreach_last_sent_at = NOW(), outreach_message_content = $1 WHERE id = $2",
                        f"Template: {template_name}", lead["id"]
                    )
                    logger.info(f"outreach_sent_success: phone={phone}, lead_id={str(lead['id'])}")
                else:
                    logger.error(f"outreach_sent_failed: phone={phone}, status={resp.status_code}, body={resp.text[:200]}")
                    
            except Exception as e:
                logger.error(f"outreach_error: phone={phone}, error={str(e)}")
            
            # Rate limiting / Sleep to avoid spam blocks
            await asyncio.sleep(1.5)

    logger.info(f"outreach_background_complete: tenant_id={tenant_id}")


@router.post("/prospecting/scrape")
async def run_prospecting_scrape(
    payload: ProspectingScrapeRequest,
    context: dict = Depends(get_current_user_context),
    allowed_ids: List[int] = Depends(get_allowed_tenant_ids),
):
    """
    Runs Apify Google Places scrape and inserts leads by (tenant_id, phone_number).
    - Skips / preserves existing leads (ON CONFLICT DO NOTHING).
    - If Apify has no phone but has a website, scrapes the site for the phone.
    - Infers country dial code from the location query.
    CEO only.
    """
    role = context.get("role") or context.get("user_role") or ""
    if role != "ceo":
        raise HTTPException(status_code=403, detail="Solo el rol CEO puede ejecutar prospeccion")

    tenant_id = _resolve_target_tenant_id(context, allowed_ids, payload.tenant_id)
    logger.info(f"🚀 Iniciando prospección Apify: niche={payload.niche}, location={payload.location}, tenant={tenant_id}")

    apify_token = os.getenv("APIFY_API_TOKEN")
    if not apify_token:
        logger.error("❌ APIFY_API_TOKEN no encontrado en el entorno")
        raise HTTPException(status_code=500, detail="Missing APIFY_API_TOKEN in environment")

    default_cc = _infer_country_code(payload.location)
    logger.info(f"📍 Country code inferido: {default_cc}")

    apify_body = {
        "includeWebResults": True,
        "language": "en",
        "locationQuery": payload.location,
        "maxCrawledPlacesPerSearch": payload.max_places,
        "maxImages": 0,
        "maximumLeadsEnrichmentRecords": 0,
        "scrapeContacts": False,
        "scrapeDirectories": False,
        "scrapeImageAuthors": False,
        "scrapePlaceDetailPage": False,
        "scrapeReviewsPersonalData": True,
        "scrapeTableReservationProvider": False,
        "searchStringsArray": [payload.niche.lower().strip()],
        "skipClosedPlaces": False,
    }

    try:
        logger.info(f"📡 Iniciando Apify Run: {APIFY_ACTOR_URL.replace('/run-sync-get-dataset-items', '')}")
        # 1. Start Actor Run
        run_url = APIFY_ACTOR_URL.replace("/run-sync-get-dataset-items", "/runs")
        async with httpx.AsyncClient(timeout=310.0) as client:
            resp = await client.post(
                run_url,
                params={"token": apify_token},
                json=apify_body,
            )
            resp.raise_for_status()
            run_data = resp.json().get("data", {})
            run_id = run_data.get("id")
            dataset_id = run_data.get("defaultDatasetId")
            
            if not run_id:
                raise HTTPException(status_code=502, detail="Failed to start Apify run (no run_id)")

            # 2. Polling loop: Wait for SUCCEEDED (max 300s)
            import asyncio
            start_time = asyncio.get_event_loop().time()
            max_wait = 300
            run_status = run_data.get("status")

            logger.info(f"⏳ Esperando finalización de Apify Run {run_id} (status={run_status})...")
            
            while run_status not in ["SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"]:
                await asyncio.sleep(5) # Reduced from 10s to 5s for better responsiveness
                status_resp = await client.get(
                    f"https://api.apify.com/v2/actor-runs/{run_id}",
                    params={"token": apify_token}
                )
                status_resp.raise_for_status()
                run_data = status_resp.json().get("data", {})
                run_status = run_data.get("status")
                
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > max_wait:
                    logger.warning(f"⏰ Timeout alcanzado esperando Apify run {run_id} ({int(elapsed)}s)")
                    break
                
                # Log progress every 10s or on status change
                logger.info(f"🔄 Check Apify {run_id}: {run_status} ({int(elapsed)}s)")

            if run_status != "SUCCEEDED":
                logger.warning(f"⚠️ Apify run finalizó con estado: {run_status}. Intentando obtener items parciales...")
            
            if not dataset_id:
                dataset_id = run_data.get("defaultDatasetId")
            
            if not dataset_id:
                raise HTTPException(status_code=502, detail="Apify run did not provide a dataset ID")

            # 3. Get Dataset Items
            items_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items"
            items_resp = await client.get(items_url, params={"token": apify_token})
            items_resp.raise_for_status()
            items = items_resp.json() if isinstance(items_resp.json(), list) else []
            logger.info(f"✅ Apify respondió con {len(items)} items del dataset {dataset_id}")

    except httpx.HTTPError as e:
        logger.error(f"❌ Error en llamada a Apify: {e}")
        raise HTTPException(status_code=502, detail=f"Apify request failed: {e}")

    imported = 0
    skipped_no_phone = 0
    skipped_exists = 0
    fetched_from_web = 0

    for item in items:
        # 1) Get phone from Apify directly
        raw_phone = item.get("phoneUnformatted") or item.get("phone")
        phone = _normalize_phone_e164(raw_phone, default_cc) if raw_phone else None

        # 2) Website fallback
        if not phone:
            website = item.get("website") or ""
            if not website and item.get("webResults"):
                website = (item["webResults"][0] or {}).get("url", "")
            if website:
                phone = await _extract_phone_from_website(website, default_cc)
                if phone:
                    fetched_from_web += 1

        if not phone:
            skipped_no_phone += 1
            continue

        title = (item.get("title") or "").strip() or None
        first_name = title[:100] if title else None

        social_links = _extract_social_links(item)

        scraped_at_iso = item.get("scrapedAt")
        scraped_at = None
        if isinstance(scraped_at_iso, str) and scraped_at_iso:
            try:
                scraped_at = datetime.fromisoformat(scraped_at_iso.replace("Z", "+00:00"))
            except ValueError:
                pass

        # 3) UPSERT — Enrich if exists, preserve name if from WhatsApp
        # Source differentiation: we only overwrite 'source' if it was originally 'apify_scrape'
        # or if the existing record has no source.
        result = await db.pool.execute(
            """
            INSERT INTO leads (
                tenant_id, phone_number, first_name, email, status, source, tags, social_links,
                apify_title, apify_category_name, apify_address, apify_city, apify_state, apify_country_code,
                apify_website, apify_place_id, apify_total_score, apify_reviews_count, apify_scraped_at, apify_raw,
                apify_rating, apify_reviews,
                prospecting_niche, prospecting_location_query,
                outreach_message_sent, outreach_send_requested,
                created_at, updated_at
            )
            VALUES (
                $1, $2, $3, $19, 'new', 'apify_scrape', '[]'::jsonb, $18::jsonb,
                $4, $5, $6, $7, $8, $9,
                $10, $11, $12, $13, $14, $15::jsonb,
                $20, $21,
                $16, $17,
                FALSE, FALSE,
                NOW(), NOW()
            )
            ON CONFLICT (tenant_id, phone_number)
            DO UPDATE SET
                -- Enriquecimiento: Solo actualizamos si el campo actual está vacío o es de prospección
                social_links = CASE 
                    WHEN leads.social_links IS NULL OR leads.social_links = '{}'::jsonb THEN EXCLUDED.social_links 
                    ELSE leads.social_links || EXCLUDED.social_links 
                END,
                email = COALESCE(leads.email, EXCLUDED.email),
                apify_title = COALESCE(leads.apify_title, EXCLUDED.apify_title),
                apify_category_name = COALESCE(leads.apify_category_name, EXCLUDED.apify_category_name),
                apify_address = COALESCE(leads.apify_address, EXCLUDED.apify_address),
                apify_city = COALESCE(leads.apify_city, EXCLUDED.apify_city),
                apify_state = COALESCE(leads.apify_state, EXCLUDED.apify_state),
                apify_country_code = COALESCE(leads.apify_country_code, EXCLUDED.apify_country_code),
                apify_website = COALESCE(leads.apify_website, EXCLUDED.apify_website),
                apify_place_id = COALESCE(leads.apify_place_id, EXCLUDED.apify_place_id),
                apify_total_score = EXCLUDED.apify_total_score,
                apify_reviews_count = EXCLUDED.apify_reviews_count,
                apify_rating = EXCLUDED.apify_rating,
                apify_reviews = EXCLUDED.apify_reviews,
                apify_scraped_at = EXCLUDED.apify_scraped_at,
                apify_raw = EXCLUDED.apify_raw,
                prospecting_niche = COALESCE(leads.prospecting_niche, EXCLUDED.prospecting_niche),
                prospecting_location_query = COALESCE(leads.prospecting_location_query, EXCLUDED.prospecting_location_query),
                updated_at = NOW()
            """,
            tenant_id,
            phone,
            first_name,
            title,
            item.get("categoryName"),
            item.get("address"),
            item.get("city"),
            item.get("state"),
            item.get("countryCode"),
            item.get("website"),
            item.get("placeId"),
            item.get("totalScore"),
            item.get("reviewsCount"),
            scraped_at,
            json.dumps(item),
            payload.niche,
            payload.location,
            json.dumps(social_links),
            item.get("email"),
            item.get("totalScore"),
            item.get("reviewsCount")
        )
        if result == "INSERT 0 1":
            imported += 1
        elif result == "UPDATE 1":
            # Si se actualizó, técnicamente no es un 'bruto' nuevo, pero lo contamos como enriquecido
            imported += 1 
        else:
            skipped_exists += 1

    logger.info(f"🏁 Scraping finalizado: total={len(items)}, importados={imported}, sin_tel={skipped_no_phone}, duplicados={skipped_exists}")

    return {
        "tenant_id": tenant_id,
        "niche": payload.niche,
        "location": payload.location,
        "country_code_inferred": default_cc,
        "total_results": len(items),
        "imported": imported,
        "skipped_no_phone": skipped_no_phone,
        "skipped_already_exists": skipped_exists,
        "fetched_from_web": fetched_from_web,
    }


@router.get("/prospecting/leads", response_model=List[ProspectingLeadResponse])
async def list_prospecting_leads(
    tenant_id_override: int = Query(..., description="Tenant to query"),
    only_pending: bool = Query(True, description="Only leads with outreach_message_sent = false"),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    context: dict = Depends(get_current_user_context),
    allowed_ids: List[int] = Depends(get_allowed_tenant_ids),
):
    _ = context
    tenant_id = _resolve_target_tenant_id(context, allowed_ids, tenant_id_override)
    query = """
        SELECT id, tenant_id, phone_number, first_name, status, source,
               apify_title, apify_category_name, apify_address, apify_city, apify_state, apify_country_code,
               apify_website, apify_place_id, apify_total_score, apify_reviews_count, apify_scraped_at,
               prospecting_niche, prospecting_location_query,
               outreach_message_sent, outreach_send_requested, outreach_last_requested_at, outreach_last_sent_at,
               created_at, updated_at
        FROM leads
        WHERE tenant_id = $1
          AND source = 'apify_scrape'
          AND (status IS NULL OR status != 'deleted')
    """
    params: List[object] = [tenant_id]
    idx = 2
    if only_pending:
        query += " AND outreach_message_sent = FALSE"
    query += f" ORDER BY updated_at DESC LIMIT ${idx} OFFSET ${idx + 1}"
    params.extend([limit, offset])
    rows = await db.pool.fetch(query, *params)
    return [dict(r) for r in rows]


@router.get("/prospecting/templates")
async def get_prospecting_templates(
    context: dict = Depends(get_current_user_context),
    allowed_ids: List[int] = Depends(get_allowed_tenant_ids)
):
    """Proxy approved templates from whatsapp_service."""
    tenant_id = context["tenant_id"]
    # For multi-tenant, we should check if they can access another tenant via query param if needed
    # But for now use context
    bot_phone = await db.pool.fetchval("SELECT bot_phone_number FROM tenants WHERE id = $1", tenant_id)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{WHATSAPP_SERVICE_URL}/templates",
                params={"from_number": bot_phone},
                headers={"X-Internal-Token": INTERNAL_API_TOKEN, "X-Correlation-Id": str(uuid_lib.uuid4())}
            )
            if resp.status_code == 200:
                return resp.json()
            else:
                return {"items": [], "detail": f"WhatsApp service error: {resp.status_code}"}
    except Exception as e:
        logger.error(f"Error fetching prospecting templates: {e}")
        return {"items": [], "detail": str(e)}

@router.post("/prospecting/request-send")
async def request_prospecting_send(
    payload: ProspectingSendRequest,
    from_fastapi_bg: BackgroundTasks,
    context: dict = Depends(get_current_user_context),
    allowed_ids: List[int] = Depends(get_allowed_tenant_ids),
):
    """
    Marks leads as requested for template outreach and TRIGGERS the send if template_name is provided.
    CEO only.
    """
    import re
    role = context.get("role") or context.get("user_role") or ""
    if role != "ceo":
        raise HTTPException(status_code=403, detail="Solo el rol CEO puede solicitar envios de prospeccion")

    _ = context
    tenant_id = _resolve_target_tenant_id(context, allowed_ids, payload.tenant_id)

    # Phone validation predicate added to SQL for safety
    phone_e164_pattern = r"^\d{8,15}$"

    if payload.lead_ids:
        ids = [str(x) for x in payload.lead_ids]
        result = await db.pool.execute(
            """
            UPDATE leads
            SET outreach_send_requested = TRUE,
                outreach_last_requested_at = NOW(),
                updated_at = NOW()
            WHERE tenant_id = $1
              AND id = ANY($2::uuid[])
              AND (status IS NULL OR status != 'deleted')
              AND ($3::bool = FALSE OR outreach_message_sent = FALSE)
              AND phone_number ~ '^\d{8,15}$'
            """,
            tenant_id,
            ids,
            payload.only_pending,
        )
    else:
        result = await db.pool.execute(
            """
            UPDATE leads
            SET outreach_send_requested = TRUE,
                outreach_last_requested_at = NOW(),
                updated_at = NOW()
            WHERE tenant_id = $1
              AND source = 'apify_scrape'
              AND (status IS NULL OR status != 'deleted')
              AND ($2::bool = FALSE OR outreach_message_sent = FALSE)
              AND phone_number ~ '^\d{8,15}$'
            """,
            tenant_id,
            payload.only_pending,
        )

    updated_count = int(result.split(" ")[1]) if isinstance(result, str) and " " in result else 0
    
    # PHASE 3: If template_name is provided, trigger the background task
    if payload.template_name:
        from_fastapi_bg.add_task(
            _send_prospecting_outreach_background,
            tenant_id=tenant_id,
            template_name=payload.template_name,
            language=payload.language or "es_AR",
            lead_ids=[str(x) for x in payload.lead_ids] if payload.lead_ids else None,
            only_pending=payload.only_pending
        )
        return {"status": "sending", "tenant_id": tenant_id, "updated": updated_count, "template": payload.template_name}

    return {"status": "queued_placeholder", "tenant_id": tenant_id, "updated": updated_count}


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
        SELECT s.id, s.tenant_id, s.user_id, s.first_name, s.last_name, s.email, s.phone_number, s.is_active, u.role
        FROM sellers s
        JOIN users u ON s.user_id = u.id AND u.role IN ('setter', 'closer')
        WHERE s.tenant_id = ANY($1::int[])
        ORDER BY s.tenant_id, s.first_name, s.last_name
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
        SELECT s.*, u.role
        FROM sellers s
        JOIN users u ON s.user_id = u.id AND u.role IN ('setter', 'closer')
        WHERE s.user_id = $1 AND s.tenant_id = ANY($2::int[])
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
    # Ensure this seller is in a CRM tenant (using sellers table)
    row = await db.pool.fetchrow("""
        SELECT s.id, s.tenant_id FROM sellers s
        JOIN users u ON s.user_id = u.id AND u.role IN ('setter', 'closer')
        JOIN tenants t ON t.id = s.tenant_id AND COALESCE(t.niche_type, 'dental') = 'crm_sales'
        WHERE s.id = $1 AND s.tenant_id = ANY($2::int[])
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
    await db.pool.execute(f"UPDATE sellers SET {set_clause} WHERE id = ${where_idx}", *params)
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
        SELECT s.id, s.user_id, s.first_name, s.last_name
        FROM sellers s
        JOIN users u ON s.user_id = u.id AND u.role IN ('setter', 'closer')
        JOIN tenants t ON t.id = s.tenant_id AND COALESCE(t.niche_type, 'dental') = 'crm_sales'
        WHERE s.id = $1 AND s.tenant_id = $2
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
