"""
Lead Notes & Derivation Routes (DEV-21 + DEV-23)
Internal setter <-> closer communication channel within each lead.
Supports: CRUD notes, derivation handoff, real-time Socket.IO events.
"""
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core.security import verify_admin_token, get_resolved_tenant_id
from db import db

logger = logging.getLogger("orchestrator")

router = APIRouter(prefix="/admin/core/crm", tags=["Lead Notes & Derivation"])

# Edit window: notes can only be edited within 15 minutes of creation
EDIT_WINDOW_MINUTES = 15

try:
    from services.seller_notification_service import seller_notification_service, Notification
except Exception as e:
    logger.warning(f"Could not import seller_notification_service: {e}. Notifications will be disabled.")
    seller_notification_service = None
    Notification = None


# ============================================
# PYDANTIC MODELS
# ============================================

class StructuredContext(BaseModel):
    prospect_wants: Optional[str] = Field(None, description="What the prospect is looking for")
    budget: Optional[str] = Field(None, description="Prospect's budget or price range")
    objections: Optional[List[str]] = Field(default=[], description="Objections raised by the prospect")
    scheduled_call_date: Optional[str] = Field(None, description="Scheduled call date/time (ISO format)")
    next_steps: Optional[str] = Field(None, description="Recommended next steps for the closer")


class DeriveLeadRequest(BaseModel):
    closer_id: UUID = Field(..., description="ID of the closer to derive the lead to")
    handoff_note: str = Field(..., min_length=1, description="Handoff note with key context")
    structured_context: Optional[StructuredContext] = Field(
        default=None,
        description="Structured context: prospect wants, budget, objections, etc."
    )


class CreateNoteRequest(BaseModel):
    note_type: str = Field(
        default="internal",
        description="Note type: handoff, post_call, internal, follow_up"
    )
    content: str = Field(..., min_length=1, max_length=5000, description="Note content")
    structured_data: Optional[dict] = Field(default={}, description="Optional structured data (JSONB)")
    visibility: str = Field(
        default="setter_closer",
        description="Visibility: setter_closer, all, private"
    )


class UpdateNoteRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000, description="Updated note content")


class NoteResponse(BaseModel):
    id: str
    tenant_id: int
    lead_id: str
    author_id: Optional[str] = None
    author_name: Optional[str] = None
    author_role: Optional[str] = None
    note_type: str
    content: str
    structured_data: Optional[dict] = None
    visibility: str
    is_deleted: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================
# SOCKET.IO REAL-TIME HELPER (DEV-23)
# ============================================

async def _emit_note_event(event_name: str, lead_id: UUID, note_data: dict, tenant_id: int):
    """Emit a Socket.IO event for real-time note updates between setter and closer."""
    try:
        from core.socket_manager import sio
        payload = {
            "lead_id": str(lead_id),
            "tenant_id": tenant_id,
            "note": note_data,
        }
        # Emit to lead-specific room so both setter and closer watching this lead get it
        await sio.emit(event_name, payload, room=f"lead:{lead_id}")
        # Also broadcast to tenant notifications room as fallback
        await sio.emit(event_name, payload, room=f"notifications:{tenant_id}")
        logger.info(f"Emitted {event_name} for lead {lead_id}")
    except Exception as e:
        logger.warning(f"Could not emit {event_name}: {e}")


def _format_note_row(row) -> dict:
    """Format a database row (with joined author info) into a note response dict."""
    result = {
        "id": str(row["id"]),
        "tenant_id": row["tenant_id"],
        "lead_id": str(row["lead_id"]),
        "author_id": str(row["author_id"]) if row.get("author_id") else None,
        "author_name": None,
        "author_role": None,
        "note_type": row["note_type"],
        "content": row["content"],
        "structured_data": row.get("structured_data") or {},
        "visibility": row["visibility"],
        "is_deleted": row.get("is_deleted", False) or False,
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
    }
    # Author info from JOIN
    first = row.get("author_first_name") or ""
    last = row.get("author_last_name") or ""
    name = f"{first} {last}".strip()
    if name:
        result["author_name"] = name
    result["author_role"] = row.get("author_role")
    return result


# ============================================
# DERIVE LEAD (Setter -> Closer) — DEV-21
# ============================================

@router.post("/leads/{lead_id}/derive")
async def derive_lead_to_closer(
    lead_id: UUID,
    request: DeriveLeadRequest,
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_data=Depends(verify_admin_token)
):
    """
    Derive a lead from setter to closer with a handoff note and full context.
    Only setters and CEOs can derive leads.
    """
    try:
        author_id = UUID(user_data.user_id)
        author_role = user_data.role

        # 1. Validate permissions: only setter or ceo can derive
        if author_role not in ("setter", "ceo"):
            raise HTTPException(
                status_code=403,
                detail="Only setters and CEOs can derive leads to closers"
            )

        # 2. Validate lead exists and belongs to tenant
        lead = await db.fetchrow(
            "SELECT id, phone_number, first_name, last_name, status, assigned_seller_id, tags "
            "FROM leads WHERE id = $1 AND tenant_id = $2",
            lead_id, tenant_id
        )
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")

        # 3. Validate closer exists, is active, and has 'closer' role
        closer = await db.fetchrow(
            "SELECT id, first_name, last_name, role, status FROM users "
            "WHERE id = $1 AND tenant_id = $2 AND status = 'active'",
            request.closer_id, tenant_id
        )
        if not closer:
            raise HTTPException(status_code=404, detail="Closer not found or inactive")
        if closer["role"] != "closer":
            raise HTTPException(
                status_code=400,
                detail=f"Target user has role '{closer['role']}', expected 'closer'"
            )

        # 4. Get setter info for the handoff note
        setter = await db.fetchrow(
            "SELECT first_name, last_name FROM users WHERE id = $1",
            author_id
        )
        setter_name = f"{setter['first_name'] or ''} {setter['last_name'] or ''}".strip() if setter else "Unknown"

        # 5. Build structured data for the note
        structured_data = {}
        if request.structured_context:
            structured_data = request.structured_context.model_dump(exclude_none=True)
        structured_data["derived_by"] = str(author_id)
        structured_data["derived_by_name"] = setter_name
        structured_data["derived_to"] = str(request.closer_id)
        structured_data["derived_to_name"] = f"{closer['first_name'] or ''} {closer['last_name'] or ''}".strip()
        structured_data["previous_status"] = lead["status"]

        # 6. Create handoff note
        note_id = await db.fetchval("""
            INSERT INTO lead_notes (tenant_id, lead_id, author_id, note_type, content, structured_data, visibility)
            VALUES ($1, $2, $3, 'handoff', $4, $5, 'setter_closer')
            RETURNING id
        """, tenant_id, lead_id, author_id, request.handoff_note, structured_data)

        # 7. Reassign lead to closer
        await db.execute("""
            UPDATE leads SET
                assigned_seller_id = $1,
                status = 'en_cierre',
                status_changed_at = NOW(),
                status_changed_by = $2,
                status_metadata = jsonb_build_object(
                    'source', 'derive_to_closer',
                    'previous_seller', assigned_seller_id::text,
                    'handoff_note_id', $3::text
                ),
                assignment_history = COALESCE(assignment_history, '[]'::jsonb) || jsonb_build_array(
                    jsonb_build_object(
                        'seller_id', $1::text,
                        'assigned_at', NOW()::text,
                        'assigned_by', $2::text,
                        'source', 'derive_to_closer'
                    )
                ),
                updated_at = NOW()
            WHERE id = $4 AND tenant_id = $5
        """, request.closer_id, author_id, str(note_id), lead_id, tenant_id)

        # 8. Add "derivado_a_closer" tag
        existing_tags = lead.get("tags") or []
        if isinstance(existing_tags, str):
            existing_tags = json.loads(existing_tags)
        if "derivado_a_closer" not in existing_tags:
            existing_tags.append("derivado_a_closer")
            await db.execute(
                "UPDATE leads SET tags = $1 WHERE id = $2 AND tenant_id = $3",
                existing_tags, lead_id, tenant_id
            )
            try:
                await db.execute("""
                    INSERT INTO lead_tag_log (tenant_id, lead_id, tags_added, reason, source)
                    VALUES ($1, $2, $3, $4, 'derive_to_closer')
                """, tenant_id, lead_id, ["derivado_a_closer"], "Lead derived to closer (DEV-21)")
            except Exception:
                pass  # Non-critical

        # 9. Update chat_messages assignment
        phone = lead["phone_number"]
        if phone:
            await db.execute("""
                UPDATE chat_messages
                SET assigned_seller_id = $1,
                    assigned_at = NOW(),
                    assigned_by = $2,
                    assignment_source = 'derive_to_closer'
                WHERE from_number = $3 AND tenant_id = $4
            """, request.closer_id, author_id, phone, tenant_id)

        # 10. Log system event
        await db.execute("""
            INSERT INTO system_events
            (tenant_id, event_type, severity, message, payload)
            VALUES ($1, 'lead_derived_to_closer', 'info',
                    'Lead derived from setter to closer',
                    jsonb_build_object(
                        'lead_id', $2::text,
                        'from_seller_id', $3::text,
                        'to_closer_id', $4::text,
                        'handoff_note_id', $5::text
                    ))
        """, tenant_id, str(lead_id), str(author_id),
           str(request.closer_id), str(note_id))

        # 11. Send notification to closer
        lead_name = f"{lead.get('first_name') or ''} {lead.get('last_name') or ''}".strip() or phone
        await _notify_closer_handoff(
            tenant_id=tenant_id,
            closer_id=request.closer_id,
            closer_name=structured_data["derived_to_name"],
            setter_name=setter_name,
            lead_id=lead_id,
            lead_name=lead_name,
            handoff_note=request.handoff_note,
            structured_context=structured_data
        )

        # 12. Emit real-time event (DEV-23)
        await _emit_note_event("LEAD_NOTE_CREATED", lead_id, {
            "id": str(note_id),
            "lead_id": str(lead_id),
            "author_id": str(author_id),
            "author_name": setter_name,
            "author_role": author_role,
            "note_type": "handoff",
            "content": request.handoff_note,
            "structured_data": structured_data,
            "visibility": "setter_closer",
        }, tenant_id)

        # 13. DEV-39: Registrar evento de actividad (handoff)
        try:
            from services.activity_service import record_event
            lead_info = await db.fetchrow("SELECT first_name, last_name, phone_number FROM leads WHERE id = $1", lead_id)
            lead_name = f"{lead_info['first_name'] or ''} {lead_info['last_name'] or ''}".strip() if lead_info else str(lead_id)
            if not lead_name and lead_info:
                lead_name = lead_info["phone_number"] or str(lead_id)
            await record_event(
                tenant_id=tenant_id, actor_id=author_id,
                event_type="lead_handoff", entity_type="lead", entity_id=str(lead_id),
                metadata={"lead_name": lead_name, "from_seller": setter_name, "to_seller": structured_data["derived_to_name"]},
            )
        except Exception:
            pass  # Non-critical

        # 14. Return updated lead
        updated_lead = await db.fetchrow(
            "SELECT * FROM leads WHERE id = $1 AND tenant_id = $2",
            lead_id, tenant_id
        )

        return {
            "success": True,
            "message": f"Lead derived to closer {structured_data['derived_to_name']} successfully",
            "lead": dict(updated_lead) if updated_lead else None,
            "handoff_note_id": str(note_id),
            "closer": {
                "id": str(request.closer_id),
                "name": structured_data["derived_to_name"]
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deriving lead {lead_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# LEAD NOTES CRUD — DEV-23 (enhanced from DEV-21)
# ============================================

@router.get("/leads/{lead_id}/notes")
async def get_lead_notes(
    lead_id: UUID,
    note_type: Optional[str] = Query(None, description="Filter by note type"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_data=Depends(verify_admin_token)
):
    """
    List all notes for a lead chronologically (ascending).
    Includes author name and role. Respects visibility rules.
    Soft-deleted notes hidden for non-CEO users.
    """
    try:
        user_role = user_data.role
        user_id = UUID(user_data.user_id)

        # Validate lead exists
        lead_exists = await db.fetchval(
            "SELECT 1 FROM leads WHERE id = $1 AND tenant_id = $2",
            lead_id, tenant_id
        )
        if not lead_exists:
            raise HTTPException(status_code=404, detail="Lead not found")

        params: list = [lead_id, tenant_id]
        param_idx = 3

        # Build filters
        filters = []

        # Soft-delete filter: non-CEO users don't see deleted notes
        if user_role != "ceo":
            filters.append("(ln.is_deleted = FALSE OR ln.is_deleted IS NULL)")

        # Visibility filter
        if user_role != "ceo":
            filters.append(
                f"(ln.visibility IN ('all', 'setter_closer') "
                f"OR (ln.visibility = 'private' AND ln.author_id = ${param_idx}))"
            )
            params.append(user_id)
            param_idx += 1

        # Optional note_type filter
        if note_type:
            filters.append(f"ln.note_type = ${param_idx}")
            params.append(note_type)
            param_idx += 1

        where_extra = ""
        if filters:
            where_extra = " AND " + " AND ".join(filters)

        # Limit/offset
        limit_clause = f"LIMIT ${param_idx} OFFSET ${param_idx + 1}"
        params.extend([limit, offset])

        query = f"""
            SELECT
                ln.id, ln.tenant_id, ln.lead_id, ln.author_id, ln.note_type,
                ln.content, ln.structured_data, ln.visibility,
                ln.is_deleted, ln.created_at, ln.updated_at,
                u.first_name AS author_first_name,
                u.last_name AS author_last_name,
                u.role AS author_role
            FROM lead_notes ln
            LEFT JOIN users u ON ln.author_id = u.id
            WHERE ln.lead_id = $1 AND ln.tenant_id = $2
            {where_extra}
            ORDER BY ln.created_at ASC
            {limit_clause}
        """

        notes = await db.fetch(query, *params)

        result = [_format_note_row(n) for n in notes]

        return {
            "success": True,
            "notes": result,
            "count": len(result),
            "lead_id": str(lead_id)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting notes for lead {lead_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/leads/{lead_id}/notes")
async def create_lead_note(
    lead_id: UUID,
    request: CreateNoteRequest,
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_data=Depends(verify_admin_token)
):
    """
    Create a note on a lead. Any authenticated CRM role can create notes.
    Emits LEAD_NOTE_CREATED via Socket.IO for real-time updates.
    """
    try:
        author_id = UUID(user_data.user_id)

        # Validate lead exists
        lead_exists = await db.fetchval(
            "SELECT 1 FROM leads WHERE id = $1 AND tenant_id = $2",
            lead_id, tenant_id
        )
        if not lead_exists:
            raise HTTPException(status_code=404, detail="Lead not found")

        # Validate note_type
        valid_types = ("handoff", "post_call", "internal", "follow_up")
        if request.note_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid note_type. Must be one of: {', '.join(valid_types)}"
            )

        # Validate visibility
        valid_visibilities = ("setter_closer", "all", "private")
        if request.visibility not in valid_visibilities:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid visibility. Must be one of: {', '.join(valid_visibilities)}"
            )

        # Insert note (use json.dumps for structured_data to ensure JSONB compat)
        row = await db.fetchrow("""
            INSERT INTO lead_notes (tenant_id, lead_id, author_id, note_type, content, structured_data, visibility)
            VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7)
            RETURNING id, tenant_id, lead_id, author_id, note_type, content,
                      structured_data, visibility, is_deleted, created_at, updated_at
        """, tenant_id, lead_id, author_id, request.note_type,
           request.content.strip(), json.dumps(request.structured_data or {}), request.visibility)

        # Get author info
        author = await db.fetchrow(
            "SELECT first_name, last_name, role FROM users WHERE id = $1",
            author_id
        )

        note_data = {
            "id": str(row["id"]),
            "tenant_id": row["tenant_id"],
            "lead_id": str(row["lead_id"]),
            "author_id": str(row["author_id"]) if row["author_id"] else None,
            "author_name": f"{author['first_name'] or ''} {author['last_name'] or ''}".strip() if author else None,
            "author_role": author["role"] if author else None,
            "note_type": row["note_type"],
            "content": row["content"],
            "structured_data": row.get("structured_data") or {},
            "visibility": row["visibility"],
            "is_deleted": row.get("is_deleted", False) or False,
            "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
            "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
        }

        # Emit LEAD_NOTE_CREATED via Socket.IO (DEV-23)
        await _emit_note_event("LEAD_NOTE_CREATED", lead_id, note_data, tenant_id)

        # DEV-39: Registrar evento de actividad
        try:
            from services.activity_service import record_event
            lead_info = await db.fetchrow("SELECT first_name, last_name, phone_number FROM leads WHERE id = $1", lead_id)
            lead_name = f"{lead_info['first_name'] or ''} {lead_info['last_name'] or ''}".strip() if lead_info else str(lead_id)
            if not lead_name and lead_info:
                lead_name = lead_info["phone_number"] or str(lead_id)
            await record_event(
                tenant_id=tenant_id, actor_id=author_id,
                event_type="note_added", entity_type="lead", entity_id=str(lead_id),
                metadata={"lead_name": lead_name, "note_type": request.note_type},
            )
        except Exception as act_err:
            logger.warning(f"DEV-39: Could not record activity event: {act_err}")

        # DEV-43: Parsear @menciones y notificar
        mentions = []
        try:
            from services.mention_service import parse_and_notify_mentions
            lead_info_m = await db.fetchrow("SELECT first_name, last_name, phone_number FROM leads WHERE id = $1", lead_id)
            lead_name_m = f"{lead_info_m['first_name'] or ''} {lead_info_m['last_name'] or ''}".strip() if lead_info_m else str(lead_id)
            if not lead_name_m and lead_info_m:
                lead_name_m = lead_info_m["phone_number"] or str(lead_id)
            mentions = await parse_and_notify_mentions(
                content=request.content, tenant_id=tenant_id,
                note_id=UUID(str(row["id"])), author_id=author_id,
                lead_id=lead_id, lead_name=lead_name_m,
            )
        except Exception as mention_err:
            logger.warning(f"DEV-43: Could not process mentions: {mention_err}")

        return {
            "success": True,
            "message": "Note created successfully",
            "note": note_data,
            "mentions": mentions,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating note for lead {lead_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/leads/{lead_id}/notes/{note_id}")
async def update_lead_note(
    lead_id: UUID,
    note_id: UUID,
    request: UpdateNoteRequest,
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_data=Depends(verify_admin_token)
):
    """
    Edit a note's content. Only the author can edit, and only within
    15 minutes of creation. Emits LEAD_NOTE_UPDATED via Socket.IO.
    """
    try:
        author_id = UUID(user_data.user_id)

        # Fetch existing note
        note = await db.fetchrow(
            "SELECT * FROM lead_notes WHERE id = $1 AND lead_id = $2 AND tenant_id = $3",
            note_id, lead_id, tenant_id,
        )

        if not note:
            raise HTTPException(status_code=404, detail="Note not found")

        if note.get("is_deleted"):
            raise HTTPException(status_code=410, detail="Note has been deleted")

        # Only author can edit
        if note["author_id"] != author_id:
            raise HTTPException(
                status_code=403,
                detail="Only the author can edit their notes"
            )

        # Check 15-minute edit window
        created = note["created_at"]
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        if (now - created) > timedelta(minutes=EDIT_WINDOW_MINUTES):
            raise HTTPException(
                status_code=403,
                detail=f"Edit window expired. Notes can only be edited within {EDIT_WINDOW_MINUTES} minutes of creation."
            )

        # Update
        row = await db.fetchrow(
            """
            UPDATE lead_notes
            SET content = $1, updated_at = NOW()
            WHERE id = $2 AND lead_id = $3 AND tenant_id = $4
            RETURNING id, tenant_id, lead_id, author_id, note_type, content,
                      structured_data, visibility, is_deleted, created_at, updated_at
            """,
            request.content.strip(), note_id, lead_id, tenant_id,
        )

        # Get author info
        author = await db.fetchrow(
            "SELECT first_name, last_name, role FROM users WHERE id = $1",
            author_id,
        )

        note_data = {
            "id": str(row["id"]),
            "tenant_id": row["tenant_id"],
            "lead_id": str(row["lead_id"]),
            "author_id": str(row["author_id"]) if row["author_id"] else None,
            "author_name": f"{author['first_name'] or ''} {author['last_name'] or ''}".strip() if author else None,
            "author_role": author["role"] if author else None,
            "note_type": row["note_type"],
            "content": row["content"],
            "structured_data": row.get("structured_data") or {},
            "visibility": row["visibility"],
            "is_deleted": row.get("is_deleted", False) or False,
            "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
            "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
        }

        # Emit real-time event (DEV-23)
        await _emit_note_event("LEAD_NOTE_UPDATED", lead_id, note_data, tenant_id)

        return {
            "success": True,
            "message": "Note updated successfully",
            "note": note_data,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating note {note_id} for lead {lead_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/leads/{lead_id}/notes/{note_id}")
async def delete_lead_note(
    lead_id: UUID,
    note_id: UUID,
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_data=Depends(verify_admin_token)
):
    """
    Soft-delete a note. Only the author or CEO can delete.
    Emits LEAD_NOTE_DELETED via Socket.IO.
    """
    try:
        user_id = UUID(user_data.user_id)

        note = await db.fetchrow(
            "SELECT id, author_id, is_deleted FROM lead_notes WHERE id = $1 AND lead_id = $2 AND tenant_id = $3",
            note_id, lead_id, tenant_id,
        )

        if not note:
            raise HTTPException(status_code=404, detail="Note not found")

        if note.get("is_deleted"):
            raise HTTPException(status_code=410, detail="Note already deleted")

        # Only author or CEO can delete
        is_author = note["author_id"] == user_id
        is_ceo = user_data.role == "ceo"

        if not is_author and not is_ceo:
            raise HTTPException(
                status_code=403,
                detail="Only the author or CEO can delete notes"
            )

        await db.execute(
            """
            UPDATE lead_notes
            SET is_deleted = TRUE, deleted_at = NOW(), deleted_by = $1, updated_at = NOW()
            WHERE id = $2 AND lead_id = $3 AND tenant_id = $4
            """,
            user_id, note_id, lead_id, tenant_id,
        )

        # Emit real-time event (DEV-23)
        await _emit_note_event("LEAD_NOTE_DELETED", lead_id, {
            "id": str(note_id),
            "lead_id": str(lead_id),
            "deleted_by": str(user_id),
        }, tenant_id)

        return {
            "success": True,
            "detail": "Note deleted",
            "id": str(note_id),
            "lead_id": str(lead_id),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting note {note_id} for lead {lead_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# NOTIFICATION HELPER — DEV-21
# ============================================

async def _notify_closer_handoff(
    tenant_id: int,
    closer_id: UUID,
    closer_name: str,
    setter_name: str,
    lead_id: UUID,
    lead_name: str,
    handoff_note: str,
    structured_context: dict
):
    """Send notification to the closer about a new lead handoff."""
    if not seller_notification_service or not Notification:
        logger.warning("Notification service not available, skipping handoff notification")
        return

    try:
        timestamp = datetime.now(timezone.utc).timestamp()

        # Build a rich message with context summary
        context_lines = [f"Nota: {handoff_note}"]
        if structured_context.get("prospect_wants"):
            context_lines.append(f"Quiere: {structured_context['prospect_wants']}")
        if structured_context.get("budget"):
            context_lines.append(f"Presupuesto: {structured_context['budget']}")
        if structured_context.get("objections"):
            context_lines.append(f"Objeciones: {', '.join(structured_context['objections'])}")
        if structured_context.get("scheduled_call_date"):
            context_lines.append(f"Llamada: {structured_context['scheduled_call_date']}")

        message = " | ".join(context_lines)

        # Notification for the Closer
        closer_notif = Notification(
            id=f"handoff_{lead_id}_{closer_id}_{timestamp}",
            tenant_id=tenant_id,
            type="handoff",
            title=f"Nuevo lead derivado por {setter_name}",
            message=f"Lead: {lead_name}. {message}",
            priority="high",
            recipient_id=str(closer_id),
            related_entity_type="lead",
            related_entity_id=str(lead_id),
            metadata={
                "lead_id": str(lead_id),
                "lead_name": lead_name,
                "setter_name": setter_name,
                "handoff_note": handoff_note,
                "structured_context": structured_context
            }
        )

        notifications = [closer_notif]

        # Also notify CEO
        ceo = await db.fetchrow(
            "SELECT id FROM users WHERE tenant_id = $1 AND role = 'ceo' AND status = 'active' LIMIT 1",
            tenant_id
        )
        if ceo and str(ceo["id"]) != str(closer_id):
            ceo_notif = Notification(
                id=f"handoff_ceo_{lead_id}_{closer_id}_{timestamp}",
                tenant_id=tenant_id,
                type="handoff",
                title=f"Lead derivado: {lead_name}",
                message=f"{setter_name} derivo lead a {closer_name}. {handoff_note[:100]}",
                priority="medium",
                recipient_id=str(ceo["id"]),
                related_entity_type="lead",
                related_entity_id=str(lead_id),
                metadata={
                    "lead_id": str(lead_id),
                    "setter_name": setter_name,
                    "closer_name": closer_name
                }
            )
            notifications.append(ceo_notif)

        await seller_notification_service.save_notifications(notifications)
        await seller_notification_service.broadcast_notifications(notifications)

    except Exception as e:
        logger.error(f"Error sending handoff notification: {e}", exc_info=True)
