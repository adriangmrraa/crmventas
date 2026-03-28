"""
SLA Service — DEV-42: Alertas automáticas por SLA vencido.
Gestiona reglas SLA, verifica violaciones y envía notificaciones.
"""
import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from uuid import UUID, uuid4

from db import db

logger = logging.getLogger("orchestrator")


# ============================================
# CRUD SLA RULES
# ============================================

async def get_sla_rules(tenant_id: int) -> list:
    """Lista reglas SLA del tenant."""
    rows = await db.pool.fetch(
        """SELECT id, name, description, trigger_type, threshold_minutes,
                  applies_to_statuses, applies_to_roles, escalate_to_ceo,
                  escalate_after_minutes, is_active, created_at
           FROM sla_rules WHERE tenant_id = $1 ORDER BY created_at DESC""",
        tenant_id,
    )
    return [
        {
            "id": str(r["id"]),
            "name": r["name"],
            "description": r["description"],
            "trigger_type": r["trigger_type"],
            "threshold_minutes": r["threshold_minutes"],
            "applies_to_statuses": r["applies_to_statuses"],
            "applies_to_roles": r["applies_to_roles"],
            "escalate_to_ceo": r["escalate_to_ceo"],
            "escalate_after_minutes": r["escalate_after_minutes"],
            "is_active": r["is_active"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]


async def create_sla_rule(tenant_id: int, data: dict) -> dict:
    """Crear regla SLA."""
    rule_id = uuid4()
    row = await db.pool.fetchrow(
        """INSERT INTO sla_rules (id, tenant_id, name, description, trigger_type,
                  threshold_minutes, applies_to_statuses, applies_to_roles,
                  escalate_to_ceo, escalate_after_minutes, is_active)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
           RETURNING id, name, trigger_type, threshold_minutes, is_active, created_at""",
        rule_id, tenant_id,
        data["name"], data.get("description"),
        data["trigger_type"], data["threshold_minutes"],
        data.get("applies_to_statuses"), data.get("applies_to_roles"),
        data.get("escalate_to_ceo", True), data.get("escalate_after_minutes", 30),
        data.get("is_active", True),
    )
    return {
        "id": str(row["id"]),
        "name": row["name"],
        "trigger_type": row["trigger_type"],
        "threshold_minutes": row["threshold_minutes"],
        "is_active": row["is_active"],
        "created_at": row["created_at"].isoformat(),
    }


async def update_sla_rule(tenant_id: int, rule_id: UUID, data: dict) -> dict:
    """Actualizar regla SLA."""
    row = await db.pool.fetchrow(
        """UPDATE sla_rules SET
              name = COALESCE($3, name),
              description = COALESCE($4, description),
              trigger_type = COALESCE($5, trigger_type),
              threshold_minutes = COALESCE($6, threshold_minutes),
              applies_to_statuses = COALESCE($7, applies_to_statuses),
              applies_to_roles = COALESCE($8, applies_to_roles),
              escalate_to_ceo = COALESCE($9, escalate_to_ceo),
              escalate_after_minutes = COALESCE($10, escalate_after_minutes),
              is_active = COALESCE($11, is_active),
              updated_at = NOW()
           WHERE id = $1 AND tenant_id = $2
           RETURNING id, name, trigger_type, threshold_minutes, is_active""",
        rule_id, tenant_id,
        data.get("name"), data.get("description"),
        data.get("trigger_type"), data.get("threshold_minutes"),
        data.get("applies_to_statuses"), data.get("applies_to_roles"),
        data.get("escalate_to_ceo"), data.get("escalate_after_minutes"),
        data.get("is_active"),
    )
    if not row:
        return None
    return {"id": str(row["id"]), "name": row["name"], "updated": True}


async def delete_sla_rule(tenant_id: int, rule_id: UUID) -> bool:
    """Desactivar regla SLA (soft delete)."""
    result = await db.pool.execute(
        "UPDATE sla_rules SET is_active = false, updated_at = NOW() WHERE id = $1 AND tenant_id = $2",
        rule_id, tenant_id,
    )
    return "UPDATE 1" in result


# ============================================
# SLA VIOLATION CHECK (Background Job)
# ============================================

async def check_sla_violations(tenant_id: int) -> list:
    """Verifica violaciones de SLA para un tenant. Llamado por background job."""
    rules = await db.pool.fetch(
        "SELECT * FROM sla_rules WHERE tenant_id = $1 AND is_active = true",
        tenant_id,
    )

    violations = []
    now = datetime.now(timezone.utc)

    for rule in rules:
        trigger_type = rule["trigger_type"]
        threshold = timedelta(minutes=rule["threshold_minutes"])

        if trigger_type == "first_response":
            # Leads asignados sin ninguna actividad del vendedor
            leads = await db.pool.fetch(
                """SELECT l.id, l.first_name, l.last_name, l.phone_number,
                          l.assigned_seller_id, l.created_at AS assigned_at,
                          u.first_name AS seller_first, u.last_name AS seller_last
                   FROM leads l
                   LEFT JOIN users u ON u.id = l.assigned_seller_id
                   WHERE l.tenant_id = $1
                     AND l.assigned_seller_id IS NOT NULL
                     AND l.status NOT IN ('won', 'lost', 'closed_won', 'closed_lost')
                     AND l.created_at < $2
                     AND NOT EXISTS (
                         SELECT 1 FROM activity_events ae
                         WHERE ae.entity_id = l.id::text AND ae.tenant_id = $1
                           AND ae.actor_id = l.assigned_seller_id
                     )""",
                tenant_id, now - threshold,
            )

            for l in leads:
                lead_name = f"{l['first_name'] or ''} {l['last_name'] or ''}".strip() or l["phone_number"]
                seller_name = f"{l['seller_first'] or ''} {l['seller_last'] or ''}".strip()
                minutes_exceeded = int((now - l["assigned_at"].replace(tzinfo=timezone.utc)).total_seconds() / 60) if l["assigned_at"].tzinfo is None else int((now - l["assigned_at"]).total_seconds() / 60)

                violations.append({
                    "rule_id": str(rule["id"]),
                    "rule_name": rule["name"],
                    "trigger_type": trigger_type,
                    "lead_id": str(l["id"]),
                    "lead_name": lead_name,
                    "seller_id": str(l["assigned_seller_id"]) if l["assigned_seller_id"] else None,
                    "seller_name": seller_name,
                    "threshold_minutes": rule["threshold_minutes"],
                    "minutes_exceeded": minutes_exceeded,
                    "escalate_to_ceo": rule["escalate_to_ceo"],
                    "should_escalate": minutes_exceeded >= (rule["threshold_minutes"] + (rule["escalate_after_minutes"] or 30)),
                })

        elif trigger_type == "follow_up":
            # Leads con última actividad mayor al threshold
            leads = await db.pool.fetch(
                """SELECT l.id, l.first_name, l.last_name, l.phone_number,
                          l.assigned_seller_id,
                          u.first_name AS seller_first, u.last_name AS seller_last,
                          (SELECT MAX(ae.created_at) FROM activity_events ae
                           WHERE ae.entity_id = l.id::text AND ae.tenant_id = $1) AS last_activity
                   FROM leads l
                   LEFT JOIN users u ON u.id = l.assigned_seller_id
                   WHERE l.tenant_id = $1
                     AND l.assigned_seller_id IS NOT NULL
                     AND l.status NOT IN ('won', 'lost', 'closed_won', 'closed_lost')
                     AND NOT EXISTS (
                         SELECT 1 FROM activity_events ae
                         WHERE ae.entity_id = l.id::text AND ae.tenant_id = $1
                           AND ae.created_at > $2
                     )
                     AND l.created_at < $2""",
                tenant_id, now - threshold,
            )

            for l in leads:
                lead_name = f"{l['first_name'] or ''} {l['last_name'] or ''}".strip() or l["phone_number"]
                seller_name = f"{l['seller_first'] or ''} {l['seller_last'] or ''}".strip()
                last_act = l["last_activity"]
                if last_act and last_act.tzinfo is None:
                    last_act = last_act.replace(tzinfo=timezone.utc)
                minutes_exceeded = int((now - last_act).total_seconds() / 60) if last_act else 999

                violations.append({
                    "rule_id": str(rule["id"]),
                    "rule_name": rule["name"],
                    "trigger_type": trigger_type,
                    "lead_id": str(l["id"]),
                    "lead_name": lead_name,
                    "seller_id": str(l["assigned_seller_id"]) if l["assigned_seller_id"] else None,
                    "seller_name": seller_name,
                    "threshold_minutes": rule["threshold_minutes"],
                    "minutes_exceeded": minutes_exceeded,
                    "escalate_to_ceo": rule["escalate_to_ceo"],
                    "should_escalate": minutes_exceeded >= (rule["threshold_minutes"] + (rule["escalate_after_minutes"] or 30)),
                })

    return violations


async def get_active_violations(tenant_id: int) -> list:
    """Obtener violaciones activas para el endpoint."""
    # Get all tenants if called from background job, or specific tenant
    all_rules = await db.pool.fetch(
        "SELECT DISTINCT tenant_id FROM sla_rules WHERE is_active = true AND tenant_id = $1",
        tenant_id,
    )
    violations = []
    for row in all_rules:
        violations.extend(await check_sla_violations(row["tenant_id"]))
    return violations
