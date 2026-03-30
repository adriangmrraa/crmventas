"""
DEV-50 — Deduplication Routes
Gestión de candidatos duplicados: revisión, fusión y descarte.
"""
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from db import db
from auth import verify_admin_token

router = APIRouter(prefix="/admin/core/crm/duplicates", tags=["Deduplication DEV-50"])
logger = logging.getLogger("deduplication_routes")


@router.get("")
async def list_duplicates(
    status: str = "pending",
    limit: int = 50,
    offset: int = 0,
    user=Depends(verify_admin_token),
):
    """DEV-50: Lista candidatos duplicados del tenant."""
    tenant_id = user.get("tenant_id", 1)
    rows = await db.pool.fetch(
        """
        SELECT dc.*,
               la.first_name AS a_first_name, la.last_name AS a_last_name,
               la.phone_number AS a_phone, la.email AS a_email, la.status AS a_status,
               lb.first_name AS b_first_name, lb.last_name AS b_last_name,
               lb.phone_number AS b_phone, lb.email AS b_email, lb.status AS b_status,
               u.first_name AS resolved_by_name
        FROM duplicate_candidates dc
        JOIN leads la ON la.id = dc.lead_a_id
        JOIN leads lb ON lb.id = dc.lead_b_id
        LEFT JOIN users u ON u.id = dc.resolved_by
        WHERE dc.tenant_id = $1 AND dc.status = $2
        ORDER BY dc.confidence DESC, dc.created_at DESC
        LIMIT $3 OFFSET $4
        """,
        tenant_id, status, limit, offset,
    )
    return [dict(r) for r in rows]


@router.get("/stats")
async def get_duplicate_stats(user=Depends(verify_admin_token)):
    """DEV-50: Estadísticas de duplicados."""
    tenant_id = user.get("tenant_id", 1)
    row = await db.pool.fetchrow(
        """
        SELECT
            COUNT(*) FILTER (WHERE status = 'pending') AS pending,
            COUNT(*) FILTER (WHERE status = 'merged') AS merged,
            COUNT(*) FILTER (WHERE status = 'dismissed') AS dismissed,
            AVG(confidence) FILTER (WHERE status = 'pending') AS avg_confidence
        FROM duplicate_candidates
        WHERE tenant_id = $1
        """,
        tenant_id,
    )
    return dict(row) if row else {}


@router.get("/{candidate_id}")
async def get_duplicate_detail(candidate_id: str, user=Depends(verify_admin_token)):
    """DEV-50: Detalle de un candidato duplicado con todos los campos de ambos leads."""
    tenant_id = user.get("tenant_id", 1)
    row = await db.pool.fetchrow(
        """
        SELECT dc.*,
               la.first_name AS a_first_name, la.last_name AS a_last_name,
               la.phone_number AS a_phone, la.email AS a_email, la.status AS a_status,
               la.company AS a_company, la.source AS a_source,
               la.created_at AS a_created_at, la.estimated_value AS a_value,
               la.tags AS a_tags, la.score AS a_score,
               lb.first_name AS b_first_name, lb.last_name AS b_last_name,
               lb.phone_number AS b_phone, lb.email AS b_email, lb.status AS b_status,
               lb.company AS b_company, lb.source AS b_source,
               lb.created_at AS b_created_at, lb.estimated_value AS b_value,
               lb.tags AS b_tags, lb.score AS b_score
        FROM duplicate_candidates dc
        JOIN leads la ON la.id = dc.lead_a_id
        JOIN leads lb ON lb.id = dc.lead_b_id
        WHERE dc.id = $1 AND dc.tenant_id = $2
        """,
        uuid.UUID(candidate_id), tenant_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Duplicate candidate not found")
    return dict(row)


@router.post("/{candidate_id}/merge")
async def merge_duplicate(candidate_id: str, body: dict, user=Depends(verify_admin_token)):
    """
    DEV-50: Fusiona los dos leads duplicados.
    body: {primary_id, secondary_id, field_overrides: {field: value, ...}}
    """
    tenant_id = user.get("tenant_id", 1)
    user_id = user.get("user_id") or user.get("id")

    primary_id = body.get("primary_id")
    secondary_id = body.get("secondary_id")
    if not primary_id or not secondary_id:
        raise HTTPException(status_code=400, detail="primary_id and secondary_id are required")

    # Verificar que el candidato existe y pertenece al tenant
    candidate = await db.pool.fetchrow(
        "SELECT id FROM duplicate_candidates WHERE id = $1 AND tenant_id = $2 AND status = 'pending'",
        uuid.UUID(candidate_id), tenant_id,
    )
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found or already resolved")

    from services.deduplication_service import merge_leads
    try:
        result = await merge_leads(
            tenant_id=tenant_id,
            primary_id=primary_id,
            secondary_id=secondary_id,
            field_overrides=body.get("field_overrides", {}),
            resolved_by_id=user_id,
            pool=db.pool,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"DEV-50: Merge error: {e}")
        raise HTTPException(status_code=500, detail="Error during merge")


@router.post("/{candidate_id}/dismiss")
async def dismiss_duplicate(candidate_id: str, user=Depends(verify_admin_token)):
    """DEV-50: Descartar un candidato (no son duplicados)."""
    tenant_id = user.get("tenant_id", 1)
    user_id = user.get("user_id") or user.get("id")

    result = await db.pool.execute(
        """
        UPDATE duplicate_candidates
        SET status = 'dismissed', resolved_by = $1, resolved_at = NOW()
        WHERE id = $2 AND tenant_id = $3 AND status = 'pending'
        """,
        uuid.UUID(user_id) if isinstance(user_id, str) else user_id,
        uuid.UUID(candidate_id),
        tenant_id,
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Candidate not found or already resolved")
    return {"status": "dismissed"}


@router.post("/leads/{lead_id}/find-duplicates")
async def find_duplicates_for_lead_endpoint(lead_id: str, user=Depends(verify_admin_token)):
    """DEV-50: Busca duplicados para un lead específico y los guarda como candidatos."""
    tenant_id = user.get("tenant_id", 1)
    try:
        lead_uuid = uuid.UUID(lead_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid lead ID")

    lead = await db.pool.fetchrow(
        "SELECT * FROM leads WHERE id = $1 AND tenant_id = $2",
        lead_uuid, tenant_id,
    )
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    from services.deduplication_service import find_duplicates_for_lead, create_duplicate_candidates
    duplicates = await find_duplicates_for_lead(
        tenant_id=tenant_id,
        lead_id=lead_id,
        phone=lead["phone_number"] or "",
        email=lead["email"],
        first_name=lead["first_name"] or "",
        last_name=lead["last_name"] or "",
        pool=db.pool,
    )
    if duplicates:
        await create_duplicate_candidates(tenant_id, lead_id, duplicates, db.pool)

    return {"found": len(duplicates), "candidates": duplicates}
