"""
Lead Timeline Service — DEV-45: Unified timeline for all lead events.
Merges 4 sources server-side: chat_messages, lead_notes, lead_status_history, activity_events.
Supports cursor-based pagination and real-time WebSocket emission.
"""
import base64
import heapq
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from db import db

logger = logging.getLogger("orchestrator")

# ─────────────────────────────────────────────────────────────────────────────
# EVENT TYPE CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

ACTIVITY_EVENT_TYPE_MAP: Dict[str, str] = {
    "call_logged": "call_logged",
    "hsm_sent": "hsm_sent",
    "lead_assigned": "assignment_change",
    "lead_reassigned": "assignment_change",
    "lead_handoff": "assignment_change",
}

ACTIVITY_EVENT_TYPES_FILTER = tuple(ACTIVITY_EVENT_TYPE_MAP.keys())

VISIBILITY_MAP: Dict[str, str] = {
    "all": "public",
    "setter_closer": "internal",
    "private": "private",
}

# ─────────────────────────────────────────────────────────────────────────────
# CURSOR ENCODING / DECODING
# ─────────────────────────────────────────────────────────────────────────────

def _encode_cursor(timestamp: datetime, source_table: str, source_id: str) -> str:
    """Encode a cursor as base64(timestamp_iso|source_table|source_id)."""
    ts = timestamp.isoformat() if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc).isoformat()
    raw = f"{ts}|{source_table}|{source_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> Optional[tuple]:
    """
    Decode cursor. Returns (timestamp, source_table, source_id) or None on error.
    Raises ValueError with a clear message on invalid input.
    """
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        parts = raw.split("|", 2)
        if len(parts) != 3:
            raise ValueError("Invalid cursor format")
        ts_str, source_table, source_id = parts
        ts = datetime.fromisoformat(ts_str)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts, source_table, source_id
    except Exception as exc:
        raise ValueError(f"Invalid cursor: {exc}") from exc


# ─────────────────────────────────────────────────────────────────────────────
# TIMESTAMP NORMALIZATION HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# ─────────────────────────────────────────────────────────────────────────────
# PER-SOURCE NORMALIZERS
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_chat_message(row: dict) -> dict:
    ts = _ensure_utc(row["created_at"])
    platform = row.get("platform") or "whatsapp"
    event_type = f"{platform}_message"
    content = row.get("content") or ""
    role = row.get("role") or "user"
    if role == "user":
        actor_name = "Cliente"
        actor_role = "user"
        actor_id = None
    elif role == "assistant":
        actor_name = "Agente/Bot"
        actor_role = "assistant"
        actor_id = str(row["assigned_seller_id"]) if row.get("assigned_seller_id") else None
    else:
        # system/tool — excluded upstream, but defensive fallback
        actor_name = "Sistema"
        actor_role = "system"
        actor_id = None

    summary = content[:80] + ("..." if len(content) > 80 else "")
    return {
        "id": f"cm_{row['id']}",
        "event_type": event_type,
        "timestamp": ts.isoformat(),
        "_ts": ts,
        "actor": {"id": actor_id, "name": actor_name, "role": actor_role},
        "content": {
            "summary": summary,
            "detail": content,
            "structured": None,
        },
        "visibility": "public",
        "source_table": "chat_messages",
        "source_id": str(row["id"]),
        "metadata": {
            "platform": platform,
            "correlation_id": row.get("correlation_id"),
            "role": role,
        },
    }


def _normalize_lead_note(row: dict, author_cache: dict) -> dict:
    ts = _ensure_utc(row["created_at"])
    author_id = str(row["author_id"]) if row.get("author_id") else None
    author_info = author_cache.get(author_id, {}) if author_id else {}
    author_name = author_info.get("name") or "Desconocido"
    author_role = author_info.get("role") or ""
    note_type = row.get("note_type") or "internal"
    content = row.get("content") or ""
    visibility_raw = row.get("visibility") or "all"
    visibility = VISIBILITY_MAP.get(visibility_raw, "internal")
    summary_prefix = f"{note_type}: " if note_type else ""
    summary = summary_prefix + content[:80] + ("..." if len(content) > 80 else "")
    return {
        "id": f"ln_{row['id']}",
        "event_type": "note",
        "timestamp": ts.isoformat(),
        "_ts": ts,
        "actor": {"id": author_id, "name": author_name, "role": author_role},
        "content": {
            "summary": summary,
            "detail": content,
            "structured": row.get("structured_data") or {},
        },
        "visibility": visibility,
        "source_table": "lead_notes",
        "source_id": str(row["id"]),
        "metadata": {"note_type": note_type},
    }


def _normalize_status_history(row: dict) -> dict:
    ts = _ensure_utc(row["created_at"])
    from_code = row.get("from_status_code") or "inicio"
    to_code = row.get("to_status_code") or "?"
    changed_by_id = str(row["changed_by_user_id"]) if row.get("changed_by_user_id") else None
    changed_by_name = row.get("changed_by_name") or "Sistema"
    changed_by_role = row.get("changed_by_role") or ""
    comment = row.get("comment")
    summary = f"{from_code} → {to_code}"
    return {
        "id": f"sh_{row['id']}",
        "event_type": "status_change",
        "timestamp": ts.isoformat(),
        "_ts": ts,
        "actor": {"id": changed_by_id, "name": changed_by_name, "role": changed_by_role},
        "content": {
            "summary": summary,
            "detail": comment,
            "structured": None,
        },
        "visibility": "public",
        "source_table": "lead_status_history",
        "source_id": str(row["id"]),
        "metadata": {
            "from_status": from_code,
            "to_status": to_code,
            "source": row.get("source"),
            "reason_code": row.get("reason_code"),
        },
    }


def _normalize_activity_event(row: dict, actor_cache: dict) -> dict:
    ts = _ensure_utc(row["created_at"])
    event_type_raw = row.get("event_type") or ""
    event_type = ACTIVITY_EVENT_TYPE_MAP.get(event_type_raw, event_type_raw)
    actor_id = str(row["actor_id"]) if row.get("actor_id") else None
    actor_info = actor_cache.get(actor_id, {}) if actor_id else {}
    actor_name = actor_info.get("name") or "Sistema"
    actor_role = actor_info.get("role") or ""
    meta = row.get("metadata") or {}
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except Exception:
            meta = {}

    # Build summary from event type
    if event_type_raw in ("lead_assigned", "lead_reassigned", "lead_handoff"):
        from_s = meta.get("from_seller") or "?"
        to_s = meta.get("to_seller") or "?"
        summary = f"{from_s} → {to_s}"
    elif event_type_raw == "hsm_sent":
        tname = meta.get("template_name") or "template"
        summary = f"Template HSM enviado: {tname}"
    elif event_type_raw == "call_logged":
        summary = "Llamada registrada"
    else:
        summary = event_type_raw.replace("_", " ").title()

    detail = meta.get("notes") or meta.get("reason") or meta.get("template_body")

    return {
        "id": f"ae_{row['id']}",
        "event_type": event_type,
        "timestamp": ts.isoformat(),
        "_ts": ts,
        "actor": {"id": actor_id, "name": actor_name, "role": actor_role},
        "content": {
            "summary": summary,
            "detail": detail,
            "structured": meta,
        },
        "visibility": "internal",
        "source_table": "activity_events",
        "source_id": str(row["id"]),
        "metadata": meta,
    }


def _normalize_task(row: dict, event_suffix: str) -> dict:
    """
    event_suffix: 'created' or 'completed'.
    For 'created': timestamp = created_at.
    For 'completed': timestamp = completed_at.
    """
    if event_suffix == "created":
        ts = _ensure_utc(row["created_at"])
        event_type = "task_created"
        summary = f"Tarea creada: {row.get('title', '')}"
    else:
        ts = _ensure_utc(row["completed_at"])
        event_type = "task_completed"
        summary = f"Tarea completada: {row.get('title', '')}"

    return {
        "id": f"lt_{event_suffix}_{row['id']}",
        "event_type": event_type,
        "timestamp": ts.isoformat(),
        "_ts": ts,
        "actor": {"id": None, "name": "Sistema", "role": "system"},
        "content": {
            "summary": summary,
            "detail": row.get("description"),
            "structured": {
                "status": row.get("status"),
                "priority": row.get("priority"),
                "due_date": str(row.get("due_date")) if row.get("due_date") else None,
            },
        },
        "visibility": "internal",
        "source_table": "lead_tasks",
        "source_id": str(row["id"]),
        "metadata": {"task_status": row.get("status"), "priority": row.get("priority")},
    }


# ─────────────────────────────────────────────────────────────────────────────
# MAIN SERVICE FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

async def get_lead_timeline(
    tenant_id: int,
    lead_id: UUID,
    event_types: Optional[List[str]] = None,
    cursor: Optional[str] = None,
    limit: int = 20,
) -> dict:
    """
    Fetch unified timeline for a lead.

    - tenant_id, lead_id: required for tenant isolation
    - event_types: optional filter list (whatsapp_message, instagram_message, note,
      status_change, task_created, task_completed, call_logged, hsm_sent, assignment_change)
    - cursor: opaque base64 pagination cursor
    - limit: page size (1–50)
    """
    import asyncio

    limit = max(1, min(50, limit))

    # Decode cursor
    cursor_ts: Optional[datetime] = None
    if cursor:
        cursor_ts, _, _ = _decode_cursor(cursor)

    # 1. Fetch lead info (phone_number + existence check)
    lead_row = await db.pool.fetchrow(
        "SELECT id, first_name, last_name, phone_number, status FROM leads WHERE id = $1 AND tenant_id = $2",
        lead_id, tenant_id,
    )
    if not lead_row:
        return None  # Caller raises 404

    phone_number = lead_row["phone_number"]
    lead_name = f"{lead_row['first_name'] or ''} {lead_row['last_name'] or ''}".strip() or phone_number

    # 2. Determine which sources to query
    all_types = event_types or []
    fetch_chat = not all_types or bool(
        {"whatsapp_message", "instagram_message", "facebook_message"} & set(all_types)
    )
    fetch_notes = not all_types or "note" in all_types
    fetch_status = not all_types or "status_change" in all_types
    fetch_tasks = not all_types or bool({"task_created", "task_completed"} & set(all_types))
    fetch_activity = not all_types or bool(
        {"call_logged", "hsm_sent", "assignment_change"} & set(all_types)
    )

    # Query limit: fetch limit+1 per source to detect has_more after merge
    q_limit = limit * 4 + 10  # generous fetch per source

    async def fetch_chat_messages():
        if not fetch_chat or not phone_number:
            return []
        # Join chat_messages to this specific lead via phone_number + tenant_id
        # Exclude system/tool messages
        extra = ""
        extra_args: list = []
        if cursor_ts:
            extra = " AND cm.created_at < $4"
            extra_args = [cursor_ts]
        rows = await db.pool.fetch(
            f"""
            SELECT cm.id, cm.from_number, cm.role, cm.content, cm.platform,
                   cm.assigned_seller_id, cm.correlation_id, cm.created_at
            FROM chat_messages cm
            WHERE cm.from_number = $1
              AND cm.tenant_id = $2
              AND cm.role IN ('user', 'assistant')
              {extra}
            ORDER BY cm.created_at DESC
            LIMIT $3
            """,
            phone_number, tenant_id, q_limit, *extra_args,
        )
        return [dict(r) for r in rows]

    async def fetch_lead_notes():
        if not fetch_notes:
            return []
        args = [lead_id, tenant_id, q_limit]
        extra = ""
        if cursor_ts:
            extra = " AND ln.created_at < $4"
            args.append(cursor_ts)
        rows = await db.pool.fetch(
            f"""
            SELECT ln.id, ln.author_id, ln.note_type, ln.content, ln.structured_data,
                   ln.visibility, ln.created_at
            FROM lead_notes ln
            WHERE ln.lead_id = $1 AND ln.tenant_id = $2
              AND (ln.is_deleted = FALSE OR ln.is_deleted IS NULL)
              {extra}
            ORDER BY ln.created_at DESC
            LIMIT $3
            """,
            lead_id, tenant_id, q_limit, *([cursor_ts] if cursor_ts else []),
        )
        return [dict(r) for r in rows]

    async def fetch_status_history():
        if not fetch_status:
            return []
        extra = ""
        extra_args = []
        if cursor_ts:
            extra = " AND h.created_at < $4"
            extra_args.append(cursor_ts)
        rows = await db.pool.fetch(
            f"""
            SELECT h.id, h.from_status_code, h.to_status_code,
                   h.changed_by_user_id, h.changed_by_name, h.changed_by_role,
                   h.comment, h.source, h.reason_code, h.created_at
            FROM lead_status_history h
            WHERE h.lead_id = $1 AND h.tenant_id = $2
              {extra}
            ORDER BY h.created_at DESC
            LIMIT $3
            """,
            lead_id, tenant_id, q_limit, *extra_args,
        )
        return [dict(r) for r in rows]

    async def fetch_tasks():
        if not fetch_tasks:
            return []
        extra = ""
        extra_args = []
        if cursor_ts:
            # We fetch tasks created before cursor OR completed before cursor
            extra = " AND t.created_at < $4"
            extra_args.append(cursor_ts)
        rows = await db.pool.fetch(
            f"""
            SELECT t.id, t.title, t.description, t.status, t.priority,
                   t.due_date, t.created_at, t.completed_at
            FROM lead_tasks t
            WHERE t.lead_id = $1 AND t.tenant_id = $2
              {extra}
            ORDER BY t.created_at DESC
            LIMIT $3
            """,
            lead_id, tenant_id, q_limit, *extra_args,
        )
        return [dict(r) for r in rows]

    async def fetch_activity_evts():
        if not fetch_activity:
            return []
        ae_types = list(ACTIVITY_EVENT_TYPES_FILTER)
        extra = ""
        extra_args = []
        if cursor_ts:
            extra = f" AND ae.created_at < ${len(ae_types) + 4}"
            extra_args.append(cursor_ts)
        # Build ANY($N) for event types
        type_placeholder = f"${3 + 1}"  # will be $4 since we have $1=entity_id, $2=tenant_id, $3=q_limit
        # Re-structure with explicit parameter indices
        type_idx = 4
        extra_idx = type_idx + len(ae_types)
        placeholders = ", ".join(f"${i}" for i in range(type_idx, type_idx + len(ae_types)))
        final_extra = ""
        final_extra_args: list = []
        if cursor_ts:
            final_extra = f" AND ae.created_at < ${extra_idx + 1}"
            final_extra_args.append(cursor_ts)

        rows = await db.pool.fetch(
            f"""
            SELECT ae.id, ae.actor_id, ae.event_type, ae.metadata, ae.created_at
            FROM activity_events ae
            WHERE ae.entity_id = $1 AND ae.entity_type = 'lead' AND ae.tenant_id = $2
              AND ae.event_type IN ({placeholders})
              {final_extra}
            ORDER BY ae.created_at DESC
            LIMIT $3
            """,
            str(lead_id), tenant_id, q_limit, *ae_types, *final_extra_args,
        )
        return [dict(r) for r in rows]

    # 3. Run all queries in parallel
    results = await asyncio.gather(
        fetch_chat_messages(),
        fetch_lead_notes(),
        fetch_status_history(),
        fetch_tasks(),
        fetch_activity_evts(),
        return_exceptions=True,
    )

    chat_rows, note_rows, status_rows, task_rows, activity_rows = results

    # Handle partial failures gracefully — log but don't fail the whole request
    def _safe(val, name):
        if isinstance(val, Exception):
            logger.warning(f"Timeline source '{name}' failed: {val}")
            return []
        return val or []

    chat_rows = _safe(chat_rows, "chat_messages")
    note_rows = _safe(note_rows, "lead_notes")
    status_rows = _safe(status_rows, "lead_status_history")
    task_rows = _safe(task_rows, "lead_tasks")
    activity_rows = _safe(activity_rows, "activity_events")

    # 4. Collect actor IDs to batch-fetch names
    actor_ids: set = set()
    for r in note_rows:
        if r.get("author_id"):
            actor_ids.add(str(r["author_id"]))
    for r in activity_rows:
        if r.get("actor_id"):
            actor_ids.add(str(r["actor_id"]))

    actor_cache: dict = {}
    if actor_ids:
        try:
            user_rows = await db.pool.fetch(
                "SELECT id, first_name, last_name, role FROM users WHERE id = ANY($1::uuid[])",
                list(actor_ids),
            )
            for u in user_rows:
                name = f"{u['first_name'] or ''} {u['last_name'] or ''}".strip()
                actor_cache[str(u["id"])] = {"name": name, "role": u["role"] or ""}
        except Exception as e:
            logger.warning(f"Could not fetch actor names: {e}")

    # 5. Normalize all rows
    events: list = []

    for r in chat_rows:
        try:
            events.append(_normalize_chat_message(r))
        except Exception as e:
            logger.debug(f"Error normalizing chat_message {r.get('id')}: {e}")

    for r in note_rows:
        try:
            events.append(_normalize_lead_note(r, actor_cache))
        except Exception as e:
            logger.debug(f"Error normalizing note {r.get('id')}: {e}")

    for r in status_rows:
        try:
            events.append(_normalize_status_history(r))
        except Exception as e:
            logger.debug(f"Error normalizing status_history {r.get('id')}: {e}")

    for r in task_rows:
        try:
            events.append(_normalize_task(r, "created"))
            if r.get("completed_at"):
                events.append(_normalize_task(r, "completed"))
        except Exception as e:
            logger.debug(f"Error normalizing task {r.get('id')}: {e}")

    for r in activity_rows:
        try:
            events.append(_normalize_activity_event(r, actor_cache))
        except Exception as e:
            logger.debug(f"Error normalizing activity_event {r.get('id')}: {e}")

    # 6. Sort by timestamp DESC, apply type filter if active
    if all_types:
        events = [e for e in events if e["event_type"] in all_types]

    # Remove internal _ts and sort — using negative timestamp for DESC
    events.sort(key=lambda e: e["_ts"], reverse=True)

    # 7. Slice: take limit+1 to detect has_more
    total_fetched = len(events)
    has_more = total_fetched > limit
    page = events[:limit]

    # 8. Strip internal _ts field
    for e in page:
        e.pop("_ts", None)

    # 9. Build next_cursor from last item
    next_cursor = None
    if has_more and page:
        last = page[-1]
        # Parse timestamp back for cursor encoding
        last_ts_str = last["timestamp"]
        try:
            last_ts = datetime.fromisoformat(last_ts_str)
            next_cursor = _encode_cursor(last_ts, last["source_table"], last["source_id"])
        except Exception:
            pass

    return {
        "lead": {
            "id": str(lead_id),
            "name": lead_name,
            "phone_number": phone_number,
            "status": lead_row["status"],
        },
        "items": page,
        "pagination": {
            "next_cursor": next_cursor,
            "has_more": has_more,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# REAL-TIME EMISSION HELPER
# ─────────────────────────────────────────────────────────────────────────────

async def emit_timeline_event(
    tenant_id: int,
    lead_id: str,
    event: dict,
) -> None:
    """
    Emit a single timeline event via Socket.IO to room lead:{lead_id}.
    Called by activity_service.record_event() for real-time updates.
    """
    try:
        from core.socket_manager import sio
        payload = {
            "tenant_id": tenant_id,
            "lead_id": lead_id,
            "event": event,
        }
        await sio.emit("lead_timeline:new_event", payload, room=f"lead:{lead_id}")
        logger.debug(f"Emitted lead_timeline:new_event for lead {lead_id}")
    except Exception as e:
        logger.warning(f"Could not emit lead_timeline:new_event: {e}")
