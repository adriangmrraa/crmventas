"""
Activity Service — DEV-39: Panel de Actividad del Equipo en Tiempo Real
Registra eventos de actividad y los emite via WebSocket al canal team_activity.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from db import db

logger = logging.getLogger("orchestrator")


async def record_event(
    tenant_id: int,
    actor_id: UUID,
    event_type: str,
    entity_type: str,
    entity_id: str,
    metadata: Optional[dict] = None,
) -> Optional[dict]:
    """
    Registra un evento de actividad y lo emite por WebSocket.
    Deduplicacion: ignora si ya existe un evento identico en los ultimos 5 segundos.
    """
    import json

    meta = metadata or {}

    # Deduplicacion: mismo actor, tipo, entidad en ventana de 5s
    dedup_check = await db.pool.fetchval(
        """
        SELECT id FROM activity_events
        WHERE tenant_id = $1 AND actor_id = $2 AND event_type = $3
          AND entity_type = $4 AND entity_id = $5
          AND created_at > NOW() - INTERVAL '5 seconds'
        LIMIT 1
        """,
        tenant_id, actor_id, event_type, entity_type, entity_id,
    )
    if dedup_check:
        logger.debug(f"Activity event dedup: {event_type} on {entity_type}:{entity_id} by {actor_id}")
        return None

    event_id = uuid4()
    row = await db.pool.fetchrow(
        """
        INSERT INTO activity_events (id, tenant_id, actor_id, event_type, entity_type, entity_id, metadata)
        VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
        RETURNING id, tenant_id, actor_id, event_type, entity_type, entity_id, metadata, created_at
        """,
        event_id, tenant_id, actor_id, event_type, entity_type, entity_id, json.dumps(meta),
    )

    if not row:
        return None

    # Obtener info del actor (filtro por tenant_id para soberania de datos)
    actor = await db.pool.fetchrow(
        "SELECT first_name, last_name, role FROM users WHERE id = $1 AND tenant_id = $2",
        actor_id, tenant_id,
    )
    actor_name = ""
    actor_role = ""
    if actor:
        actor_name = f"{actor['first_name'] or ''} {actor['last_name'] or ''}".strip()
        actor_role = actor["role"] or ""

    event_data = {
        "id": str(row["id"]),
        "actor": {"id": str(actor_id), "name": actor_name, "role": actor_role},
        "event_type": event_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "metadata": meta,
        "created_at": row["created_at"].isoformat(),
    }

    # Emit via WebSocket
    try:
        from core.socket_manager import sio
        await sio.emit("team_activity:new_event", event_data, room=f"team_activity:{tenant_id}")
    except Exception as e:
        logger.warning(f"Could not emit team_activity event: {e}")

    return event_data


async def get_feed(
    tenant_id: int,
    limit: int = 50,
    offset: int = 0,
    seller_id: Optional[UUID] = None,
    event_type: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> dict:
    """Feed paginado de actividad del equipo."""
    conditions = ["ae.tenant_id = $1"]
    params: list = [tenant_id]
    idx = 2

    if seller_id:
        conditions.append(f"ae.actor_id = ${idx}")
        params.append(seller_id)
        idx += 1

    if event_type:
        conditions.append(f"ae.event_type = ${idx}")
        params.append(event_type)
        idx += 1

    if date_from:
        conditions.append(f"ae.created_at >= ${idx}")
        params.append(date_from)
        idx += 1

    if date_to:
        conditions.append(f"ae.created_at <= ${idx}")
        params.append(date_to)
        idx += 1

    where = " AND ".join(conditions)

    # Total count
    total = await db.pool.fetchval(
        f"SELECT COUNT(*) FROM activity_events ae WHERE {where}",
        *params,
    )

    # Items with actor JOIN
    params.append(limit)
    limit_idx = idx
    idx += 1
    params.append(offset)
    offset_idx = idx

    rows = await db.pool.fetch(
        f"""
        SELECT ae.id, ae.actor_id, ae.event_type, ae.entity_type, ae.entity_id,
               ae.metadata, ae.created_at,
               u.first_name AS actor_first_name, u.last_name AS actor_last_name, u.role AS actor_role
        FROM activity_events ae
        LEFT JOIN users u ON u.id = ae.actor_id
        WHERE {where}
        ORDER BY ae.created_at DESC
        LIMIT ${limit_idx} OFFSET ${offset_idx}
        """,
        *params,
    )

    now = datetime.now(timezone.utc)
    items = []
    for r in rows:
        actor_name = f"{r['actor_first_name'] or ''} {r['actor_last_name'] or ''}".strip()
        delta = now - r["created_at"].replace(tzinfo=timezone.utc) if r["created_at"].tzinfo is None else now - r["created_at"]
        time_ago = _format_time_ago(delta)

        meta = r["metadata"] or {}
        entity_name = meta.get("lead_name", f"{r['entity_type']}:{r['entity_id']}")

        items.append({
            "id": str(r["id"]),
            "actor": {
                "id": str(r["actor_id"]),
                "name": actor_name,
                "role": r["actor_role"] or "",
            },
            "event_type": r["event_type"],
            "entity_type": r["entity_type"],
            "entity_id": str(r["entity_id"]),
            "entity_name": entity_name,
            "metadata": meta,
            "created_at": r["created_at"].isoformat(),
            "time_ago": time_ago,
        })

    return {
        "items": items,
        "total": total or 0,
        "has_more": (offset + limit) < (total or 0),
    }


async def get_seller_statuses(tenant_id: int) -> list:
    """Estado de cada vendedor: activo/idle/inactivo + metricas."""
    rows = await db.pool.fetch(
        """
        SELECT s.id AS seller_id, s.user_id, u.first_name, u.last_name, u.role,
               sm.last_activity_at,
               (SELECT COUNT(*) FROM leads l
                WHERE l.assigned_seller_id = s.user_id AND l.tenant_id = $1
                  AND l.status NOT IN ('won', 'lost', 'closed_won', 'closed_lost')
               ) AS active_leads_count,
               (SELECT COUNT(*) FROM leads l2
                WHERE l2.assigned_seller_id = s.user_id AND l2.tenant_id = $1
                  AND l2.status NOT IN ('won', 'lost', 'closed_won', 'closed_lost')
                  AND NOT EXISTS (
                      SELECT 1 FROM activity_events ae2
                      WHERE ae2.entity_id = l2.id::text AND ae2.tenant_id = $1
                        AND ae2.created_at > NOW() - INTERVAL '2 hours'
                  )
               ) AS leads_without_activity_2h
        FROM sellers s
        JOIN users u ON u.id = s.user_id
        LEFT JOIN seller_metrics sm ON sm.seller_id = s.user_id AND sm.tenant_id = $1
        WHERE s.tenant_id = $1 AND s.is_active = true
        ORDER BY u.first_name
        """,
        tenant_id,
    )

    now = datetime.now(timezone.utc)
    sellers = []
    for r in rows:
        last_act = r["last_activity_at"]
        if last_act:
            if last_act.tzinfo is None:
                last_act = last_act.replace(tzinfo=timezone.utc)
            delta_minutes = (now - last_act).total_seconds() / 60
            if delta_minutes < 15:
                status = "active"
            elif delta_minutes < 60:
                status = "idle"
            else:
                status = "inactive"
        else:
            status = "inactive"

        # Ultimo tipo de actividad
        last_event = await db.pool.fetchrow(
            """
            SELECT event_type FROM activity_events
            WHERE actor_id = $1 AND tenant_id = $2
            ORDER BY created_at DESC LIMIT 1
            """,
            r["user_id"], tenant_id,
        )

        # Tiempo promedio primera respuesta (hoy)
        avg_today = await db.pool.fetchval(
            """
            SELECT AVG(EXTRACT(EPOCH FROM (ae.created_at - l.created_at)))
            FROM activity_events ae
            JOIN leads l ON l.id::text = ae.entity_id AND l.tenant_id = $1
            WHERE ae.actor_id = $2 AND ae.tenant_id = $1
              AND ae.created_at::date = CURRENT_DATE
              AND ae.event_type IN ('note_added', 'chat_message_sent', 'call_logged')
              AND ae.id = (
                  SELECT id FROM activity_events ae2
                  WHERE ae2.entity_id = ae.entity_id AND ae2.actor_id = $2 AND ae2.tenant_id = $1
                  ORDER BY ae2.created_at ASC LIMIT 1
              )
            """,
            tenant_id, r["user_id"],
        )

        # Tiempo promedio primera respuesta (semana)
        avg_week = await db.pool.fetchval(
            """
            SELECT AVG(EXTRACT(EPOCH FROM (ae.created_at - l.created_at)))
            FROM activity_events ae
            JOIN leads l ON l.id::text = ae.entity_id AND l.tenant_id = $1
            WHERE ae.actor_id = $2 AND ae.tenant_id = $1
              AND ae.created_at >= NOW() - INTERVAL '7 days'
              AND ae.event_type IN ('note_added', 'chat_message_sent', 'call_logged')
              AND ae.id = (
                  SELECT id FROM activity_events ae2
                  WHERE ae2.entity_id = ae.entity_id AND ae2.actor_id = $2 AND ae2.tenant_id = $1
                  ORDER BY ae2.created_at ASC LIMIT 1
              )
            """,
            tenant_id, r["user_id"],
        )

        sellers.append({
            "id": str(r["seller_id"]),
            "user_id": str(r["user_id"]),
            "name": f"{r['first_name'] or ''} {r['last_name'] or ''}".strip(),
            "role": r["role"] or "",
            "status": status,
            "active_leads_count": r["active_leads_count"] or 0,
            "last_activity_at": last_act.isoformat() if last_act else None,
            "last_activity_type": last_event["event_type"] if last_event else None,
            "avg_first_response_today_seconds": round(avg_today) if avg_today else None,
            "avg_first_response_week_seconds": round(avg_week) if avg_week else None,
            "leads_without_activity_2h": r["leads_without_activity_2h"] or 0,
        })

    return sellers


async def get_inactive_lead_alerts(tenant_id: int) -> list:
    """Leads asignados sin actividad en las ultimas 2 horas."""
    rows = await db.pool.fetch(
        """
        SELECT l.id, l.first_name, l.last_name, l.phone_number, l.assigned_seller_id,
               u.first_name AS seller_first, u.last_name AS seller_last,
               COALESCE(
                   (SELECT MAX(ae.created_at) FROM activity_events ae
                    WHERE ae.entity_id = l.id::text AND ae.tenant_id = $1),
                   l.created_at
               ) AS last_activity_at
        FROM leads l
        LEFT JOIN users u ON u.id = l.assigned_seller_id
        WHERE l.tenant_id = $1
          AND l.assigned_seller_id IS NOT NULL
          AND l.status NOT IN ('won', 'lost', 'closed_won', 'closed_lost')
          AND NOT EXISTS (
              SELECT 1 FROM activity_events ae
              WHERE ae.entity_id = l.id::text AND ae.tenant_id = $1
                AND ae.created_at > NOW() - INTERVAL '2 hours'
          )
          AND l.created_at < NOW() - INTERVAL '2 hours'
        ORDER BY last_activity_at ASC
        LIMIT 50
        """,
        tenant_id,
    )

    now = datetime.now(timezone.utc)
    alerts = []
    for r in rows:
        last_act = r["last_activity_at"]
        if last_act and last_act.tzinfo is None:
            last_act = last_act.replace(tzinfo=timezone.utc)
        hours = round((now - last_act).total_seconds() / 3600, 1) if last_act else 999

        lead_name = f"{r['first_name'] or ''} {r['last_name'] or ''}".strip() or r["phone_number"]
        seller_name = f"{r['seller_first'] or ''} {r['seller_last'] or ''}".strip()

        alerts.append({
            "type": "lead_inactive",
            "severity": "critical" if hours > 4 else "warning",
            "lead_id": str(r["id"]),
            "lead_name": lead_name,
            "assigned_seller": seller_name,
            "hours_inactive": hours,
            "last_activity_at": last_act.isoformat() if last_act else None,
        })

    return alerts


# ============================================
# DEV-40: AUDIT LOG FUNCTIONS
# ============================================

async def get_audit_by_lead(tenant_id: int, lead_id: UUID, limit: int = 100, offset: int = 0) -> dict:
    """Timeline completa de un lead: activity_events + lead_status_history combinados."""
    # Activity events for this lead
    rows = await db.pool.fetch(
        """
        SELECT ae.id, ae.actor_id, ae.event_type, ae.entity_type, ae.entity_id,
               ae.metadata, ae.created_at,
               u.first_name AS actor_first_name, u.last_name AS actor_last_name, u.role AS actor_role
        FROM activity_events ae
        LEFT JOIN users u ON u.id = ae.actor_id
        WHERE ae.tenant_id = $1 AND ae.entity_id = $2::text AND ae.entity_type = 'lead'
        ORDER BY ae.created_at DESC
        LIMIT $3 OFFSET $4
        """,
        tenant_id, str(lead_id), limit, offset,
    )

    total = await db.pool.fetchval(
        "SELECT COUNT(*) FROM activity_events WHERE tenant_id = $1 AND entity_id = $2::text AND entity_type = 'lead'",
        tenant_id, str(lead_id),
    )

    # Lead info
    lead = await db.pool.fetchrow(
        "SELECT first_name, last_name, phone_number, status FROM leads WHERE id = $1 AND tenant_id = $2",
        lead_id, tenant_id,
    )
    lead_name = ""
    if lead:
        lead_name = f"{lead['first_name'] or ''} {lead['last_name'] or ''}".strip() or lead["phone_number"]

    now = datetime.now(timezone.utc)
    items = []
    for r in rows:
        actor_name = f"{r['actor_first_name'] or ''} {r['actor_last_name'] or ''}".strip()
        delta = now - (r["created_at"].replace(tzinfo=timezone.utc) if r["created_at"].tzinfo is None else r["created_at"])
        items.append({
            "id": str(r["id"]),
            "actor": {"id": str(r["actor_id"]), "name": actor_name, "role": r["actor_role"] or ""},
            "event_type": r["event_type"],
            "metadata": r["metadata"] or {},
            "created_at": r["created_at"].isoformat(),
            "time_ago": _format_time_ago(delta),
        })

    return {
        "lead": {"id": str(lead_id), "name": lead_name, "status": lead["status"] if lead else None},
        "items": items,
        "total": total or 0,
        "has_more": (offset + limit) < (total or 0),
    }


async def get_audit_by_seller(
    tenant_id: int, user_id: UUID, limit: int = 100, offset: int = 0,
    event_type: Optional[str] = None, date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> dict:
    """Historial completo de acciones de un vendedor."""
    conditions = ["ae.tenant_id = $1", "ae.actor_id = $2"]
    params: list = [tenant_id, user_id]
    idx = 3

    if event_type:
        conditions.append(f"ae.event_type = ${idx}")
        params.append(event_type)
        idx += 1
    if date_from:
        conditions.append(f"ae.created_at >= ${idx}")
        params.append(date_from)
        idx += 1
    if date_to:
        conditions.append(f"ae.created_at <= ${idx}")
        params.append(date_to)
        idx += 1

    where = " AND ".join(conditions)

    total = await db.pool.fetchval(f"SELECT COUNT(*) FROM activity_events ae WHERE {where}", *params)

    params.append(limit)
    limit_idx = idx
    idx += 1
    params.append(offset)
    offset_idx = idx

    rows = await db.pool.fetch(
        f"""
        SELECT ae.id, ae.event_type, ae.entity_type, ae.entity_id, ae.metadata, ae.created_at
        FROM activity_events ae
        WHERE {where}
        ORDER BY ae.created_at DESC
        LIMIT ${limit_idx} OFFSET ${offset_idx}
        """,
        *params,
    )

    # Seller info
    seller = await db.pool.fetchrow(
        "SELECT first_name, last_name, role FROM users WHERE id = $1 AND tenant_id = $2",
        user_id, tenant_id,
    )
    seller_name = f"{seller['first_name'] or ''} {seller['last_name'] or ''}".strip() if seller else ""

    now = datetime.now(timezone.utc)
    items = []
    for r in rows:
        meta = r["metadata"] or {}
        entity_name = meta.get("lead_name", f"{r['entity_type']}:{r['entity_id']}")
        delta = now - (r["created_at"].replace(tzinfo=timezone.utc) if r["created_at"].tzinfo is None else r["created_at"])
        items.append({
            "id": str(r["id"]),
            "event_type": r["event_type"],
            "entity_type": r["entity_type"],
            "entity_id": str(r["entity_id"]),
            "entity_name": entity_name,
            "metadata": meta,
            "created_at": r["created_at"].isoformat(),
            "time_ago": _format_time_ago(delta),
        })

    return {
        "seller": {"id": str(user_id), "name": seller_name, "role": seller["role"] if seller else ""},
        "items": items,
        "total": total or 0,
        "has_more": (offset + limit) < (total or 0),
    }


async def get_feed_for_export(
    tenant_id: int,
    seller_id: Optional[UUID] = None,
    event_type: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> list:
    """Feed completo para exportar como CSV (max 5000 rows)."""
    conditions = ["ae.tenant_id = $1"]
    params: list = [tenant_id]
    idx = 2

    if seller_id:
        conditions.append(f"ae.actor_id = ${idx}")
        params.append(seller_id)
        idx += 1
    if event_type:
        conditions.append(f"ae.event_type = ${idx}")
        params.append(event_type)
        idx += 1
    if date_from:
        conditions.append(f"ae.created_at >= ${idx}")
        params.append(date_from)
        idx += 1
    if date_to:
        conditions.append(f"ae.created_at <= ${idx}")
        params.append(date_to)
        idx += 1

    where = " AND ".join(conditions)

    rows = await db.pool.fetch(
        f"""
        SELECT ae.event_type, ae.entity_type, ae.entity_id, ae.metadata, ae.created_at,
               u.first_name AS actor_first, u.last_name AS actor_last, u.role AS actor_role
        FROM activity_events ae
        LEFT JOIN users u ON u.id = ae.actor_id
        WHERE {where}
        ORDER BY ae.created_at DESC
        LIMIT 5000
        """,
        *params,
    )

    result = []
    for r in rows:
        meta = r["metadata"] or {}
        actor_name = f"{r['actor_first'] or ''} {r['actor_last'] or ''}".strip()
        entity_name = meta.get("lead_name", f"{r['entity_type']}:{r['entity_id']}")

        detail_parts = []
        if meta.get("from_status"):
            detail_parts.append(f"{meta['from_status']} → {meta.get('to_status', '?')}")
        if meta.get("note_type"):
            detail_parts.append(f"tipo: {meta['note_type']}")
        if meta.get("from_seller"):
            detail_parts.append(f"de {meta['from_seller']} a {meta.get('to_seller', '?')}")

        result.append({
            "created_at": r["created_at"].isoformat() if r["created_at"] else "",
            "actor_name": actor_name,
            "actor_role": r["actor_role"] or "",
            "event_type": r["event_type"],
            "entity_name": entity_name,
            "detail": "; ".join(detail_parts) if detail_parts else "",
        })

    return result


# ============================================
# DEV-41: SELLER PERFORMANCE
# ============================================

async def get_seller_performance(
    tenant_id: int, user_id: UUID,
    date_from: Optional[datetime] = None, date_to: Optional[datetime] = None,
) -> dict:
    """KPIs detallados de un vendedor con breakdown temporal."""
    from datetime import timedelta as td

    if not date_from:
        date_from = datetime.now(timezone.utc) - td(days=30)
    if not date_to:
        date_to = datetime.now(timezone.utc)

    # Seller info
    seller = await db.pool.fetchrow(
        "SELECT first_name, last_name, role FROM users WHERE id = $1 AND tenant_id = $2",
        user_id, tenant_id,
    )
    if not seller:
        return {"error": "Vendedor no encontrado"}

    seller_name = f"{seller['first_name'] or ''} {seller['last_name'] or ''}".strip()

    # KPIs
    leads_assigned = await db.pool.fetchval(
        "SELECT COUNT(*) FROM leads WHERE assigned_seller_id = $1 AND tenant_id = $2 AND created_at >= $3 AND created_at <= $4",
        user_id, tenant_id, date_from, date_to,
    ) or 0

    leads_converted = await db.pool.fetchval(
        """SELECT COUNT(*) FROM leads WHERE assigned_seller_id = $1 AND tenant_id = $2
           AND status IN ('won', 'closed_won') AND updated_at >= $3 AND updated_at <= $4""",
        user_id, tenant_id, date_from, date_to,
    ) or 0

    conversion_rate = round((leads_converted / leads_assigned * 100), 1) if leads_assigned > 0 else 0

    # Event counts by type
    event_breakdown = await db.pool.fetch(
        """SELECT event_type, COUNT(*) AS cnt FROM activity_events
           WHERE actor_id = $1 AND tenant_id = $2 AND created_at >= $3 AND created_at <= $4
           GROUP BY event_type ORDER BY cnt DESC""",
        user_id, tenant_id, date_from, date_to,
    )
    event_type_breakdown = {r["event_type"]: r["cnt"] for r in event_breakdown}
    total_actions = sum(event_type_breakdown.values())

    # Active leads now
    active_leads_now = await db.pool.fetchval(
        """SELECT COUNT(*) FROM leads WHERE assigned_seller_id = $1 AND tenant_id = $2
           AND status NOT IN ('won', 'lost', 'closed_won', 'closed_lost')""",
        user_id, tenant_id,
    ) or 0

    # Avg first response
    avg_response = await db.pool.fetchval(
        """SELECT AVG(EXTRACT(EPOCH FROM (ae.created_at - l.created_at)))
           FROM activity_events ae
           JOIN leads l ON l.id::text = ae.entity_id AND l.tenant_id = $2
           WHERE ae.actor_id = $1 AND ae.tenant_id = $2
             AND ae.created_at >= $3 AND ae.created_at <= $4
             AND ae.event_type IN ('note_added', 'chat_message_sent', 'call_logged')""",
        user_id, tenant_id, date_from, date_to,
    )

    # Daily breakdown
    daily_rows = await db.pool.fetch(
        """SELECT ae.created_at::date AS day,
                  COUNT(*) AS actions,
                  COUNT(DISTINCT ae.entity_id) FILTER (WHERE ae.event_type = 'lead_assigned') AS leads_assigned,
                  COUNT(DISTINCT ae.entity_id) FILTER (WHERE ae.event_type = 'lead_status_changed'
                      AND (ae.metadata->>'to_status') IN ('won', 'closed_won')) AS leads_converted
           FROM activity_events ae
           WHERE ae.actor_id = $1 AND ae.tenant_id = $2 AND ae.created_at >= $3 AND ae.created_at <= $4
           GROUP BY ae.created_at::date ORDER BY day DESC""",
        user_id, tenant_id, date_from, date_to,
    )
    daily_breakdown = [
        {"date": str(r["day"]), "actions": r["actions"],
         "leads_assigned": r["leads_assigned"], "leads_converted": r["leads_converted"]}
        for r in daily_rows
    ]

    # Team averages for comparison
    team_conversion = await db.pool.fetchval(
        """SELECT CASE WHEN COUNT(*) > 0
                THEN ROUND(COUNT(*) FILTER (WHERE status IN ('won', 'closed_won'))::numeric / COUNT(*)::numeric * 100, 1)
                ELSE 0 END
           FROM leads WHERE tenant_id = $1 AND assigned_seller_id IS NOT NULL
             AND created_at >= $2 AND created_at <= $3""",
        tenant_id, date_from, date_to,
    ) or 0

    team_avg_response = await db.pool.fetchval(
        """SELECT AVG(EXTRACT(EPOCH FROM (ae.created_at - l.created_at)))
           FROM activity_events ae
           JOIN leads l ON l.id::text = ae.entity_id AND l.tenant_id = $1
           WHERE ae.tenant_id = $1 AND ae.created_at >= $2 AND ae.created_at <= $3
             AND ae.event_type IN ('note_added', 'chat_message_sent', 'call_logged')""",
        tenant_id, date_from, date_to,
    )

    return {
        "seller": {"id": str(user_id), "name": seller_name, "role": seller["role"] or ""},
        "period": {"from": date_from.isoformat(), "to": date_to.isoformat()},
        "kpis": {
            "leads_assigned": leads_assigned,
            "leads_converted": leads_converted,
            "conversion_rate": conversion_rate,
            "avg_first_response_seconds": round(avg_response) if avg_response else None,
            "total_actions": total_actions,
            "total_notes": event_type_breakdown.get("note_added", 0),
            "total_calls": event_type_breakdown.get("call_logged", 0),
            "total_messages": event_type_breakdown.get("chat_message_sent", 0),
            "active_leads_now": active_leads_now,
        },
        "daily_breakdown": daily_breakdown,
        "team_avg": {
            "conversion_rate": float(team_conversion),
            "avg_first_response_seconds": round(team_avg_response) if team_avg_response else None,
        },
        "event_type_breakdown": event_type_breakdown,
    }


def _format_time_ago(delta: timedelta) -> str:
    """Formato humano en espanol."""
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return "hace un momento"
    minutes = seconds // 60
    if minutes < 60:
        return f"hace {minutes} min"
    hours = minutes // 60
    if hours < 24:
        return f"hace {hours}h"
    days = hours // 24
    return f"hace {days}d"
