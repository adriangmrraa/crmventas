"""
Lead Timeline Routes — DEV-45: Unified timeline endpoint.
GET /admin/core/crm/leads/{lead_id}/timeline
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from core.security import verify_admin_token, get_resolved_tenant_id

logger = logging.getLogger("orchestrator")

router = APIRouter(prefix="/admin/core/crm", tags=["Lead Timeline"])


@router.get("/leads/{lead_id}/timeline")
async def get_lead_timeline(
    lead_id: UUID,
    types: Optional[str] = Query(
        None,
        description="Comma-separated event type filter, e.g. 'note,status_change,whatsapp_message'",
    ),
    cursor: Optional[str] = Query(None, description="Opaque pagination cursor (base64)"),
    limit: int = Query(20, ge=1, le=50, description="Items per page (1–50)"),
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_data=Depends(verify_admin_token),
):
    """
    Unified timeline for a lead: merges chat_messages, lead_notes,
    lead_status_history, activity_events, and lead_tasks ordered by
    timestamp DESC. Supports cursor-based infinite scroll pagination.

    Accessible by roles: ceo, setter, closer, secretary.
    """
    try:
        from services.lead_timeline_service import get_lead_timeline as _get_timeline, _decode_cursor

        # Validate cursor early for clean error message
        if cursor:
            try:
                _decode_cursor(cursor)
            except ValueError as ve:
                raise HTTPException(status_code=400, detail=str(ve))

        # Parse types filter
        event_types = None
        if types:
            event_types = [t.strip() for t in types.split(",") if t.strip()]

        result = await _get_timeline(
            tenant_id=tenant_id,
            lead_id=lead_id,
            event_types=event_types,
            cursor=cursor,
            limit=limit,
        )

        if result is None:
            raise HTTPException(status_code=404, detail="Lead not found")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching timeline for lead {lead_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
