"""
DEV-47 — Reactivation Routes
CRUD para secuencias de reactivación + stats.
"""
import uuid
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List

from db import db
from auth import verify_admin_token

router = APIRouter(prefix="/admin/core/crm/reactivation", tags=["Reactivation DEV-47"])
logger = logging.getLogger("reactivation_routes")


# ─── Sequences CRUD ──────────────────────────────────────────────────────────

@router.get("/sequences")
async def list_sequences(user=Depends(verify_admin_token)):
    tenant_id = user.get("tenant_id", 1)
    rows = await db.pool.fetch(
        """
        SELECT rs.*, COUNT(rsteps.id) AS step_count
        FROM reactivation_sequences rs
        LEFT JOIN reactivation_steps rsteps ON rsteps.sequence_id = rs.id
        WHERE rs.tenant_id = $1
        GROUP BY rs.id
        ORDER BY rs.created_at DESC
        """,
        tenant_id,
    )
    return [dict(r) for r in rows]


@router.post("/sequences", status_code=201)
async def create_sequence(body: dict, user=Depends(verify_admin_token)):
    tenant_id = user.get("tenant_id", 1)
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    row = await db.pool.fetchrow(
        """
        INSERT INTO reactivation_sequences
            (tenant_id, name, description, trigger_after_days, is_active, target_statuses)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING *
        """,
        tenant_id,
        name,
        body.get("description"),
        body.get("trigger_after_days", 7),
        body.get("is_active", True),
        body.get("target_statuses", ["sin_respuesta", "seguimiento_pendiente"]),
    )
    return dict(row)


@router.patch("/sequences/{sequence_id}")
async def update_sequence(sequence_id: str, body: dict, user=Depends(verify_admin_token)):
    tenant_id = user.get("tenant_id", 1)
    seq_uuid = uuid.UUID(sequence_id)
    sets, params = [], [tenant_id, seq_uuid]
    for field in ["name", "description", "trigger_after_days", "is_active", "target_statuses"]:
        if field in body:
            params.append(body[field])
            sets.append(f"{field} = ${len(params)}")
    if not sets:
        raise HTTPException(status_code=400, detail="No fields to update")
    sets.append("updated_at = NOW()")
    row = await db.pool.fetchrow(
        f"UPDATE reactivation_sequences SET {', '.join(sets)} WHERE tenant_id = $1 AND id = $2 RETURNING *",
        *params,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Sequence not found")
    return dict(row)


@router.delete("/sequences/{sequence_id}")
async def delete_sequence(sequence_id: str, user=Depends(verify_admin_token)):
    tenant_id = user.get("tenant_id", 1)
    result = await db.pool.execute(
        "DELETE FROM reactivation_sequences WHERE id = $1 AND tenant_id = $2",
        uuid.UUID(sequence_id), tenant_id,
    )
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Sequence not found")
    return {"status": "deleted"}


# ─── Steps CRUD ───────────────────────────────────────────────────────────────

@router.get("/sequences/{sequence_id}/steps")
async def list_steps(sequence_id: str, user=Depends(verify_admin_token)):
    tenant_id = user.get("tenant_id", 1)
    rows = await db.pool.fetch(
        """
        SELECT rs.* FROM reactivation_steps rs
        JOIN reactivation_sequences rseq ON rseq.id = rs.sequence_id
        WHERE rs.sequence_id = $1 AND rseq.tenant_id = $2
        ORDER BY rs.step_order ASC
        """,
        uuid.UUID(sequence_id), tenant_id,
    )
    return [dict(r) for r in rows]


@router.post("/sequences/{sequence_id}/steps", status_code=201)
async def create_step(sequence_id: str, body: dict, user=Depends(verify_admin_token)):
    tenant_id = user.get("tenant_id", 1)
    seq_uuid = uuid.UUID(sequence_id)

    # Verificar soberanía de la secuencia
    seq = await db.pool.fetchrow(
        "SELECT id FROM reactivation_sequences WHERE id = $1 AND tenant_id = $2",
        seq_uuid, tenant_id,
    )
    if not seq:
        raise HTTPException(status_code=404, detail="Sequence not found")

    row = await db.pool.fetchrow(
        """
        INSERT INTO reactivation_steps
            (sequence_id, tenant_id, step_order, delay_hours, message_type,
             template_id, template_name, template_params, free_text_message)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING *
        """,
        seq_uuid, tenant_id,
        body.get("step_order", 1),
        body.get("delay_hours", 24),
        body.get("message_type", "template"),
        uuid.UUID(body["template_id"]) if body.get("template_id") else None,
        body.get("template_name"),
        json.dumps(body.get("template_params", [])),
        body.get("free_text_message"),
    )
    return dict(row)


@router.delete("/sequences/{sequence_id}/steps/{step_id}")
async def delete_step(sequence_id: str, step_id: str, user=Depends(verify_admin_token)):
    tenant_id = user.get("tenant_id", 1)
    result = await db.pool.execute(
        """
        DELETE FROM reactivation_steps
        WHERE id = $1 AND sequence_id = $2
          AND sequence_id IN (SELECT id FROM reactivation_sequences WHERE tenant_id = $3)
        """,
        uuid.UUID(step_id), uuid.UUID(sequence_id), tenant_id,
    )
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Step not found")
    return {"status": "deleted"}


# ─── Logs ─────────────────────────────────────────────────────────────────────

@router.get("/logs")
async def get_reactivation_logs(
    sequence_id: Optional[str] = None,
    status: Optional[str] = None,
    lead_id: Optional[str] = None,
    limit: int = 50,
    user=Depends(verify_admin_token),
):
    tenant_id = user.get("tenant_id", 1)
    query = """
        SELECT rl.*, l.first_name, l.last_name, l.phone_number,
               rs.name AS sequence_name
        FROM reactivation_logs rl
        JOIN leads l ON l.id = rl.lead_id
        LEFT JOIN reactivation_sequences rs ON rs.id = rl.sequence_id
        WHERE rl.tenant_id = $1
    """
    params: list = [tenant_id]
    if sequence_id:
        params.append(uuid.UUID(sequence_id))
        query += f" AND rl.sequence_id = ${len(params)}"
    if status:
        params.append(status)
        query += f" AND rl.status = ${len(params)}"
    if lead_id:
        params.append(uuid.UUID(lead_id))
        query += f" AND rl.lead_id = ${len(params)}"
    query += f" ORDER BY rl.created_at DESC LIMIT ${len(params) + 1}"
    params.append(limit)
    rows = await db.pool.fetch(query, *params)
    return [dict(r) for r in rows]


# ─── Stats ────────────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_reactivation_stats(user=Depends(verify_admin_token)):
    tenant_id = user.get("tenant_id", 1)
    row = await db.pool.fetchrow(
        """
        SELECT
            COUNT(*) FILTER (WHERE status = 'pending') AS pending,
            COUNT(*) FILTER (WHERE status = 'sent') AS sent,
            COUNT(*) FILTER (WHERE status = 'failed') AS failed,
            COUNT(*) FILTER (WHERE status = 'responded') AS responded,
            COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled,
            COUNT(DISTINCT lead_id) FILTER (WHERE status = 'responded') AS leads_reactivated
        FROM reactivation_logs
        WHERE tenant_id = $1
        """,
        tenant_id,
    )
    return dict(row) if row else {}


# ─── Manual trigger ───────────────────────────────────────────────────────────

@router.post("/trigger")
async def manual_trigger(user=Depends(verify_admin_token)):
    """Dispara manualmente el check de secuencias de reactivación."""
    tenant_id = user.get("tenant_id", 1)
    from services.reactivation_service import check_and_trigger_sequences, execute_pending_steps
    await check_and_trigger_sequences(tenant_id, db.pool)
    await execute_pending_steps(tenant_id, db.pool)
    return {"status": "ok", "message": "Reactivation cycle triggered"}
