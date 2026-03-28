"""
API Routes for seller assignment and metrics management
"""
import json
import logging
from enum import Enum
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query, Path
from pydantic import BaseModel, Field

from core.security import verify_admin_token, get_resolved_tenant_id, require_role

logger = logging.getLogger(__name__)

try:
    from services.seller_assignment_service import seller_assignment_service
except Exception as e:
    logger.error(f"Could not import seller_assignment_service: {e}")
    seller_assignment_service = None

try:
    from services.seller_metrics_service import seller_metrics_service
except Exception as e:
    logger.error(f"Could not import seller_metrics_service: {e}")
    seller_metrics_service = None

router = APIRouter(prefix="/admin/core/sellers", tags=["Seller Management"])

# ==================== MODELS ====================

class AssignConversationRequest(BaseModel):
    phone: str = Field(..., description="Phone number of the conversation")
    seller_id: UUID = Field(..., description="ID of the seller to assign")
    source: str = Field(default="manual", description="Assignment source: manual, auto, prospecting")

class ReassignConversationRequest(BaseModel):
    phone: str = Field(..., description="Phone number of the conversation")
    new_seller_id: UUID = Field(..., description="ID of the new seller")
    reason: Optional[str] = Field(None, description="Reason for reassignment")

class AssignmentRuleCreate(BaseModel):
    rule_name: str = Field(..., description="Name of the rule")
    rule_type: str = Field(..., description="Type: round_robin, performance, specialty, load_balance")
    config: dict = Field(default={}, description="Rule configuration")
    is_active: bool = Field(default=True, description="Whether the rule is active")
    priority: int = Field(default=0, description="Priority (0 = highest)")
    description: Optional[str] = None
    apply_to_lead_source: Optional[List[str]] = None
    apply_to_lead_status: Optional[List[str]] = None
    apply_to_seller_roles: Optional[List[str]] = None
    max_conversations_per_seller: Optional[int] = None
    min_response_time_seconds: Optional[int] = None

class MetricsRequest(BaseModel):
    period_days: int = Field(default=7, ge=1, le=90, description="Period in days for metrics")

# ==================== CONVERSATION ASSIGNMENT ====================

@router.post("/conversations/assign")
async def assign_conversation(
    request: AssignConversationRequest,
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_data=Depends(verify_admin_token)
):
    """
    Assign a conversation to a seller
    """
    try:
        if not seller_assignment_service:
            raise HTTPException(status_code=503, detail="Seller assignment service not available")
        user_id = UUID(user_data.user_id)
        result = await seller_assignment_service.assign_conversation_to_seller(
            phone=request.phone,
            seller_id=request.seller_id,
            assigned_by=user_id,
            tenant_id=tenant_id,
            source=request.source
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversations/{phone}/assignment")
async def get_conversation_assignment(
    phone: str,
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_data=Depends(verify_admin_token)
):
    """
    Get current assignment for a conversation
    """
    try:
        if not seller_assignment_service:
            raise HTTPException(status_code=503, detail="Seller assignment service not available")
        assignment = await seller_assignment_service.get_conversation_assignment(
            phone=phone,
            tenant_id=tenant_id
        )

        if not assignment:
            return {"success": False, "assignment": None, "message": "No assignment found"}

        return {"success": True, "assignment": assignment}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation assignment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/conversations/{phone}/reassign")
async def reassign_conversation(
    phone: str,
    request: ReassignConversationRequest,
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_data=Depends(verify_admin_token)
):
    """
    Reassign a conversation to a different seller
    """
    try:
        user_id = UUID(user_data.user_id)
        # Only CEO can reassign conversations
        if user_data.role not in ["ceo"]:
            raise HTTPException(status_code=403, detail="Only CEO can reassign conversations")

        result = await seller_assignment_service.reassign_conversation(
            phone=phone,
            new_seller_id=request.new_seller_id,
            reassigned_by=user_id,
            tenant_id=tenant_id,
            reason=request.reason
        )

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reassigning conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/conversations/{phone}/auto-assign")
async def auto_assign_conversation(
    phone: str,
    lead_source: Optional[str] = Query(None, description="Lead source for rule filtering"),
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_data=Depends(verify_admin_token)
):
    """
    Automatically assign conversation based on rules
    """
    try:
        result = await seller_assignment_service.auto_assign_conversation(
            phone=phone,
            tenant_id=tenant_id,
            lead_source=lead_source
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        
        return result
        
    except Exception as e:
        logger.error(f"Error auto assigning conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== SELLER MANAGEMENT ====================

@router.get("/available")
async def get_available_sellers(
    role: Optional[str] = Query(None, description="Filter by role: setter, closer, professional, ceo"),
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_data=Depends(verify_admin_token)
):
    """
    Get list of available sellers for assignment
    """
    try:
        sellers = await seller_assignment_service.get_available_sellers(
            tenant_id=tenant_id,
            role_filter=role
        )
        
        return {"success": True, "sellers": sellers, "count": len(sellers)}
        
    except Exception as e:
        logger.error(f"Error getting available sellers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{seller_id}/conversations")
async def get_seller_conversations(
    seller_id: UUID,
    active_only: bool = Query(True, description="Show only active conversations (last 7 days)"),
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_data=Depends(verify_admin_token)
):
    """
    Get all conversations assigned to a seller
    """
    try:
        conversations = await seller_assignment_service.get_seller_conversations(
            seller_id=seller_id,
            tenant_id=tenant_id,
            active_only=active_only
        )
        
        return {"success": True, "conversations": conversations, "count": len(conversations)}
        
    except Exception as e:
        logger.error(f"Error getting seller conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== METRICS & ANALYTICS ====================

@router.get("/{seller_id}/metrics")
async def get_seller_metrics(
    seller_id: UUID,
    request: MetricsRequest = Depends(),
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_data=Depends(verify_admin_token)
):
    """
    Get performance metrics for a seller
    """
    try:
        result = await seller_metrics_service.get_seller_metrics(
            seller_id=seller_id,
            tenant_id=tenant_id,
            period_days=request.period_days
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("message", "Error getting metrics"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting seller metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/team/metrics", dependencies=[Depends(require_role(["ceo"]))])
async def get_team_metrics(
    request: MetricsRequest = Depends(),
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_data=Depends(verify_admin_token)
):
    """
    Get metrics for all sellers in the team
    """
    try:
        
        result = await seller_metrics_service.get_team_metrics(
            tenant_id=tenant_id,
            period_days=request.period_days
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("message", "Error getting team metrics"))
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting team metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/leaderboard")
async def get_performance_leaderboard(
    metric: str = Query("conversion_rate", description="Metric for ranking: conversion_rate, leads_converted, total_conversations, total_messages_sent, avg_response_time_seconds"),
    limit: int = Query(10, ge=1, le=50, description="Number of sellers to return"),
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_data=Depends(verify_admin_token)
):
    """
    Get leaderboard of top performing sellers
    """
    try:
        leaderboard = await seller_metrics_service.get_performance_leaderboard(
            tenant_id=tenant_id,
            metric=metric,
            limit=limit
        )
        
        return {"success": True, "leaderboard": leaderboard, "metric": metric}
        
    except Exception as e:
        logger.error(f"Error getting performance leaderboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== ASSIGNMENT RULES ====================

@router.get("/rules")
async def get_assignment_rules(
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_data=Depends(verify_admin_token)
):
    """
    Get all assignment rules for the tenant
    """
    try:
        from db import db
        
        rules = await db.fetch("""
            SELECT * FROM assignment_rules 
            WHERE tenant_id = $1
            ORDER BY priority ASC, created_at DESC
        """, tenant_id)
        
        return {"success": True, "rules": [dict(rule) for rule in rules]}
        
    except Exception as e:
        logger.error(f"Error getting assignment rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rules", dependencies=[Depends(require_role(["ceo"]))])
async def create_assignment_rule(
    request: AssignmentRuleCreate,
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_data=Depends(verify_admin_token)
):
    """
    Create a new assignment rule
    """
    try:
        
        from db import db
        
        rule_id = await db.fetchval("""
            INSERT INTO assignment_rules (
                tenant_id, rule_name, rule_type, config, is_active, priority,
                description, apply_to_lead_source, apply_to_lead_status,
                apply_to_seller_roles, max_conversations_per_seller,
                min_response_time_seconds
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12
            ) RETURNING id
        """,
            tenant_id, request.rule_name, request.rule_type, request.config,
            request.is_active, request.priority, request.description,
            request.apply_to_lead_source, request.apply_to_lead_status,
            request.apply_to_seller_roles, request.max_conversations_per_seller,
            request.min_response_time_seconds
        )
        
        return {"success": True, "rule_id": str(rule_id), "message": "Rule created successfully"}
        
    except Exception as e:
        logger.error(f"Error creating assignment rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/rules/{rule_id}", dependencies=[Depends(require_role(["ceo"]))])
async def update_assignment_rule(
    rule_id: UUID,
    request: AssignmentRuleCreate,
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_data=Depends(verify_admin_token)
):
    """
    Update an assignment rule
    """
    try:
        
        from db import db
        
        updated = await db.execute("""
            UPDATE assignment_rules SET
                rule_name = $1,
                rule_type = $2,
                config = $3,
                is_active = $4,
                priority = $5,
                description = $6,
                apply_to_lead_source = $7,
                apply_to_lead_status = $8,
                apply_to_seller_roles = $9,
                max_conversations_per_seller = $10,
                min_response_time_seconds = $11,
                updated_at = NOW()
            WHERE id = $12 AND tenant_id = $13
        """,
            request.rule_name, request.rule_type, request.config,
            request.is_active, request.priority, request.description,
            request.apply_to_lead_source, request.apply_to_lead_status,
            request.apply_to_seller_roles, request.max_conversations_per_seller,
            request.min_response_time_seconds, rule_id, tenant_id
        )
        
        if updated == "UPDATE 0":
            raise HTTPException(status_code=404, detail="Rule not found")
        
        return {"success": True, "message": "Rule updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating assignment rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/rules/{rule_id}", dependencies=[Depends(require_role(["ceo"]))])
async def delete_assignment_rule(
    rule_id: UUID,
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_data=Depends(verify_admin_token)
):
    """
    Delete an assignment rule
    """
    try:
        
        from db import db
        
        deleted = await db.execute("""
            DELETE FROM assignment_rules 
            WHERE id = $1 AND tenant_id = $2
        """, rule_id, tenant_id)
        
        if deleted == "DELETE 0":
            raise HTTPException(status_code=404, detail="Rule not found")
        
        return {"success": True, "message": "Rule deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting assignment rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== DASHBOARD ENDPOINTS ====================

@router.get("/dashboard/overview")
async def get_seller_dashboard_overview(
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_data=Depends(verify_admin_token)
):
    """
    Get overview data for seller dashboard
    """
    try:
        from db import db
        
        # Get total sellers
        total_sellers = await db.fetchval("""
            SELECT COUNT(*) FROM users 
            WHERE tenant_id = $1 
            AND status = 'active'
            AND role IN ('setter', 'closer', 'professional', 'ceo')
        """, tenant_id) or 0
        
        # Get active conversations
        active_conversations = await db.fetchval("""
            SELECT COUNT(DISTINCT from_number)
            FROM chat_messages
            WHERE tenant_id = $1
            AND assigned_seller_id IS NOT NULL
            AND assigned_at >= NOW() - INTERVAL '24 hours'
        """, tenant_id) or 0
        
        # Get unassigned conversations
        unassigned_conversations = await db.fetchval("""
            SELECT COUNT(DISTINCT from_number)
            FROM chat_messages
            WHERE tenant_id = $1
            AND assigned_seller_id IS NULL
            AND created_at >= NOW() - INTERVAL '24 hours'
        """, tenant_id) or 0
        
        # Get today's assignments
        today_assignments = await db.fetchval("""
            SELECT COUNT(DISTINCT from_number)
            FROM chat_messages
            WHERE tenant_id = $1
            AND assigned_seller_id IS NOT NULL
            AND assigned_at::date = CURRENT_DATE
        """, tenant_id) or 0
        
        # Get recent activity
        recent_activity = await db.fetch("""
            SELECT 
                u.first_name,
                u.last_name,
                u.role,
                COUNT(DISTINCT cm.from_number) as active_conversations,
                MAX(cm.assigned_at) as last_assignment
            FROM users u
            LEFT JOIN chat_messages cm ON u.id = cm.assigned_seller_id
                AND cm.tenant_id = $1
                AND cm.assigned_at >= NOW() - INTERVAL '24 hours'
            WHERE u.tenant_id = $1
            AND u.status = 'active'
            AND u.role IN ('setter', 'closer', 'professional', 'ceo')
            GROUP BY u.id, u.first_name, u.last_name, u.role
            ORDER BY last_assignment DESC NULLS LAST
            LIMIT 10
        """, tenant_id)
        
        return {
            "success": True,
            "overview": {
                "total_sellers": total_sellers,
                "active_conversations": active_conversations,
                "unassigned_conversations": unassigned_conversations,
                "today_assignments": today_assignments,
                "recent_activity": [dict(activity) for activity in recent_activity]
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting seller dashboard overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/conversation-stats")
async def get_conversation_stats(
    days: int = Query(7, ge=1, le=30, description="Number of days to analyze"),
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_data=Depends(verify_admin_token)
):
    """
    Get conversation statistics for dashboard
    """
    try:
        from db import db
        
        # Get daily assignment stats
        daily_stats = await db.fetch("""
            SELECT 
                DATE(assigned_at) as date,
                COUNT(DISTINCT from_number) as conversations_assigned,
                COUNT(DISTINCT assigned_seller_id) as sellers_active
            FROM chat_messages
            WHERE tenant_id = $1
            AND assigned_at >= NOW() - INTERVAL '$2 days'
            AND assigned_seller_id IS NOT NULL
            GROUP BY DATE(assigned_at)
            ORDER BY date DESC
        """, tenant_id, days)
        
        # Get assignment by source
        source_stats = await db.fetch("""
            SELECT 
                assignment_source,
                COUNT(DISTINCT from_number) as count
            FROM chat_messages
            WHERE tenant_id = $1
            AND assigned_at >= NOW() - INTERVAL '$2 days'
            AND assigned_seller_id IS NOT NULL
            GROUP BY assignment_source
            ORDER BY count DESC
        """, tenant_id, days)
        
        # Get assignment by seller role
        role_stats = await db.fetch("""
            SELECT 
                u.role,
                COUNT(DISTINCT cm.from_number) as conversations_assigned
            FROM chat_messages cm
            JOIN users u ON cm.assigned_seller_id = u.id
            WHERE cm.tenant_id = $1
            AND cm.assigned_at >= NOW() - INTERVAL '$2 days'
            GROUP BY u.role
            ORDER BY conversations_assigned DESC
        """, tenant_id, days)
        
        return {
            "success": True,
            "stats": {
                "daily": [dict(stat) for stat in daily_stats],
                "by_source": [dict(stat) for stat in source_stats],
                "by_role": [dict(stat) for stat in role_stats],
                "period_days": days
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting conversation stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== SETTER QUEUE (DEV-20) ====================

PRIORITY_ORDER = {
    "hot": 0, "caliente": 0,
    "warm": 1, "tibio": 1,
    "derivado": 2,
    "cold": 3, "new": 4,
}

@router.get("/my-queue")
async def get_my_queue(
    status: Optional[str] = Query(None, description="Filter by lead status, e.g. 'derivado', 'contacted'"),
    tag: Optional[str] = Query(None, description="Filter by tag, e.g. 'caliente', 'derivado_por_ia'"),
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_data=Depends(verify_admin_token)
):
    """
    Returns leads assigned to the current seller (setter) with enriched info:
    lead data, tags, AI summary, upcoming meetings, and last 10 conversation messages.
    Ordered by priority (hot first), then by created_at.
    """
    try:
        from db import db

        seller_id = UUID(user_data.user_id)

        # Build query with optional filters
        query = """
            SELECT
                l.id,
                l.phone_number,
                l.first_name,
                l.last_name,
                l.email,
                l.company,
                l.status,
                l.source,
                l.lead_source,
                l.score,
                l.score_breakdown,
                l.tags,
                l.estimated_value,
                l.created_at,
                l.updated_at,
                l.status_changed_at,
                l.assignment_history
            FROM leads l
            WHERE l.tenant_id = $1
            AND l.assigned_seller_id = $2
        """
        params: list = [tenant_id, seller_id]
        param_idx = 3

        if status:
            query += f" AND l.status = ${param_idx}"
            params.append(status)
            param_idx += 1

        query += " ORDER BY l.updated_at DESC"

        leads_rows = await db.fetch(query, *params)

        # Post-process: filter by tag in Python (tags is jsonb array)
        leads = []
        for row in leads_rows:
            lead = dict(row)
            # Parse tags
            lead_tags = lead.get("tags") or []
            if isinstance(lead_tags, str):
                lead_tags = json.loads(lead_tags)
            lead["tags"] = lead_tags

            # Filter by tag if specified
            if tag and tag not in lead_tags:
                continue

            # Parse score_breakdown for AI summary
            breakdown = lead.get("score_breakdown") or {}
            if isinstance(breakdown, str):
                breakdown = json.loads(breakdown)
            lead["score_breakdown"] = breakdown
            lead["ai_summary"] = breakdown.get("ai_derivation", {}).get("summary")
            lead["derivation_reason"] = breakdown.get("ai_derivation", {}).get("reason")
            lead["derived_at"] = breakdown.get("ai_derivation", {}).get("derived_at")

            leads.append(lead)

        # Sort by priority (hot first), then by created_at desc
        def priority_key(lead_item):
            lead_status = (lead_item.get("status") or "new").lower()
            tags = lead_item.get("tags") or []
            # Check tags for temperature
            if "caliente" in tags or lead_status in ("hot", "caliente"):
                p = 0
            elif "urgente" in tags:
                p = 0
            elif "tibio" in tags or lead_status in ("warm", "tibio"):
                p = 1
            else:
                p = PRIORITY_ORDER.get(lead_status, 3)
            return (p, lead_item.get("created_at") or datetime.min)

        leads.sort(key=priority_key)

        # Enrich each lead with upcoming meetings and conversation history (last 10 messages)
        enriched_leads = []
        for lead in leads:
            lead_id = lead["id"]
            phone = lead["phone_number"]

            # Upcoming meetings
            meetings = await db.fetch("""
                SELECT sae.id, sae.title, sae.start_datetime, sae.end_datetime, sae.status,
                       p.first_name AS seller_first, p.last_name AS seller_last
                FROM seller_agenda_events sae
                LEFT JOIN professionals p ON p.id = sae.seller_id
                WHERE sae.tenant_id = $1 AND sae.lead_id = $2
                AND sae.status = 'scheduled'
                AND sae.start_datetime > NOW()
                ORDER BY sae.start_datetime ASC
                LIMIT 5
            """, tenant_id, lead_id)

            lead["upcoming_meetings"] = [dict(m) for m in meetings]

            # Conversation history (last 10 messages)
            messages = await db.fetch("""
                SELECT role, content, created_at
                FROM chat_messages
                WHERE tenant_id = $1 AND from_number = $2
                ORDER BY created_at DESC
                LIMIT 10
            """, tenant_id, phone)

            # Reverse to chronological order
            lead["conversation_history"] = [dict(m) for m in reversed(messages)]

            enriched_leads.append(lead)

        return {
            "success": True,
            "leads": enriched_leads,
            "count": len(enriched_leads),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting setter queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/my-queue/{lead_id}/take")
async def take_lead_from_queue(
    lead_id: UUID = Path(..., description="ID of the lead to take"),
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_data=Depends(verify_admin_token)
):
    """
    Setter formally takes a lead from their queue.
    Updates status from 'derivado' to 'contacted', adds tag 'tomado_por_setter',
    and logs the action.
    """
    try:
        from db import db

        seller_id = UUID(user_data.user_id)

        # 1. Verify lead exists, is assigned to this seller, and is in 'derivado' status
        lead = await db.fetchrow("""
            SELECT id, phone_number, first_name, last_name, status, assigned_seller_id, tags
            FROM leads
            WHERE id = $1 AND tenant_id = $2
        """, lead_id, tenant_id)

        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")

        if str(lead["assigned_seller_id"]) != str(seller_id):
            raise HTTPException(
                status_code=403,
                detail="This lead is not assigned to you"
            )

        if lead["status"] != "derivado":
            raise HTTPException(
                status_code=400,
                detail=f"Lead status is '{lead['status']}', expected 'derivado'. Cannot take."
            )

        phone = lead["phone_number"]
        name = f"{lead['first_name'] or ''} {lead['last_name'] or ''}".strip() or phone

        # 2. Update lead status to 'contacted'
        await db.execute("""
            UPDATE leads
            SET status = 'contacted',
                status_changed_at = NOW(),
                status_changed_by = $1,
                updated_at = NOW()
            WHERE id = $2 AND tenant_id = $3
        """, seller_id, lead_id, tenant_id)

        # 3. Add tag 'tomado_por_setter'
        existing_tags = lead["tags"] if lead["tags"] else []
        if isinstance(existing_tags, str):
            existing_tags = json.loads(existing_tags)
        if "tomado_por_setter" not in existing_tags:
            existing_tags.append("tomado_por_setter")

        await db.execute(
            "UPDATE leads SET tags = $1, updated_at = NOW() WHERE id = $2",
            existing_tags, lead_id,
        )

        # 4. Log the tag addition
        await db.execute(
            "INSERT INTO lead_tag_log (tenant_id, lead_id, tags_added, reason, source) VALUES ($1, $2, $3, $4, 'setter_action')",
            tenant_id, lead_id, ["tomado_por_setter"],
            f"Setter {user_data.email} tomó el lead desde el panel",
        )

        # 5. Log system event
        await db.execute("""
            INSERT INTO system_events
            (tenant_id, user_id, event_type, severity, message, payload)
            VALUES ($1, $2, 'lead_taken_by_setter', 'info',
                    'Lead tomado por setter desde panel de derivados',
                    jsonb_build_object(
                        'lead_id', $3::text,
                        'phone', $4,
                        'setter_id', $5::text,
                        'setter_email', $6
                    ))
        """, tenant_id, seller_id, str(lead_id), phone, str(seller_id), user_data.email)

        # 6. Emit Socket.IO event
        try:
            from core.socket_manager import sio
            await sio.emit("LEAD_TAKEN_BY_SETTER", {
                "tenant_id": tenant_id,
                "lead_id": str(lead_id),
                "phone": phone,
                "name": name,
                "setter_id": str(seller_id),
                "timestamp": datetime.utcnow().isoformat(),
            })
        except Exception as sio_err:
            logger.warning(f"Could not emit LEAD_TAKEN_BY_SETTER socket event: {sio_err}")

        logger.info(f"Lead {name} ({phone}) taken by setter {user_data.email}")
        return {
            "success": True,
            "message": f"Lead {name} tomado exitosamente. Estado actualizado a 'contacted'.",
            "lead_id": str(lead_id),
            "new_status": "contacted",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error taking lead from queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== FOLLOW-UP QUEUE (DEV-25) ====================

class CompleteFollowUpRequest(BaseModel):
    result: str = Field(..., description="Result of the follow-up: contacted, no_answer, rescheduled, completed, lost")
    notes: str = Field(..., description="Notes about the follow-up")
    reschedule_date: Optional[datetime] = Field(None, description="If rescheduling, the new date/time")


@router.get("/follow-up-queue")
async def get_follow_up_queue(
    filter: Optional[str] = Query(None, description="Filter: overdue, today, this_week"),
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_data=Depends(verify_admin_token)
):
    """
    Returns leads requiring follow-up for the current seller.
    A lead requires follow-up if it:
      - Has tag 'requiere_seguimiento', OR
      - Has a future seller_agenda_event with status 'scheduled'
    Ordered by next_contact_date ASC (overdue first, then soonest).
    """
    try:
        from db import db

        seller_id = UUID(user_data.user_id)

        # Main query: leads assigned to this seller that need follow-up
        # We use a CTE to compute next_contact_date from agenda events or lead_notes
        rows = await db.fetch("""
            WITH follow_up_leads AS (
                SELECT DISTINCT l.id
                FROM leads l
                WHERE l.tenant_id = $1
                  AND l.assigned_seller_id = $2
                  AND (
                    l.tags::jsonb ? 'requiere_seguimiento'
                    OR EXISTS (
                        SELECT 1 FROM seller_agenda_events sae
                        WHERE sae.lead_id = l.id
                          AND sae.tenant_id = $1
                          AND sae.status = 'scheduled'
                    )
                  )
            ),
            lead_next_contact AS (
                SELECT
                    fl.id AS lead_id,
                    LEAST(
                        (SELECT MIN(sae.start_datetime) FROM seller_agenda_events sae
                         WHERE sae.lead_id = fl.id AND sae.tenant_id = $1 AND sae.status = 'scheduled'),
                        (SELECT (ln.structured_data->>'next_contact_date')::timestamptz
                         FROM lead_notes ln
                         WHERE ln.lead_id = fl.id AND ln.tenant_id = $1
                           AND ln.note_type IN ('post_call', 'follow_up')
                           AND ln.structured_data->>'next_contact_date' IS NOT NULL
                         ORDER BY ln.created_at DESC LIMIT 1)
                    ) AS next_contact_date,
                    (SELECT ln.content FROM lead_notes ln
                     WHERE ln.lead_id = fl.id AND ln.tenant_id = $1
                     ORDER BY ln.created_at DESC LIMIT 1) AS last_note_content,
                    (SELECT ln.created_at FROM lead_notes ln
                     WHERE ln.lead_id = fl.id AND ln.tenant_id = $1
                     ORDER BY ln.created_at DESC LIMIT 1) AS last_note_at
                FROM follow_up_leads fl
            )
            SELECT
                l.id, l.phone_number, l.first_name, l.last_name, l.email,
                l.company, l.status, l.source, l.lead_source,
                l.score, l.tags, l.estimated_value,
                l.created_at, l.updated_at,
                lnc.next_contact_date,
                lnc.last_note_content,
                lnc.last_note_at,
                EXTRACT(DAY FROM NOW() - COALESCE(lnc.last_note_at, l.updated_at))::int AS days_since_last_contact,
                CASE WHEN lnc.next_contact_date < NOW() THEN TRUE ELSE FALSE END AS is_overdue
            FROM leads l
            JOIN lead_next_contact lnc ON lnc.lead_id = l.id
            WHERE l.tenant_id = $1
            ORDER BY
                CASE WHEN lnc.next_contact_date < NOW() THEN 0 ELSE 1 END ASC,
                lnc.next_contact_date ASC NULLS LAST
        """, tenant_id, seller_id)

        results = []
        now = datetime.utcnow()
        for row in rows:
            item = dict(row)

            # Parse tags
            lead_tags = item.get("tags") or []
            if isinstance(lead_tags, str):
                lead_tags = json.loads(lead_tags)
            item["tags"] = lead_tags

            # Fetch post-call notes for this lead (DEV-24 enrichment)
            post_call_notes = await db.fetch("""
                SELECT ln.id, ln.author_id, ln.note_type, ln.content, ln.structured_data, ln.visibility, ln.created_at,
                       u.first_name AS author_first_name, u.last_name AS author_last_name, u.role AS author_role
                FROM lead_notes ln
                LEFT JOIN users u ON ln.author_id = u.id
                WHERE ln.lead_id = $1 AND ln.tenant_id = $2 AND ln.note_type = 'post_call'
                ORDER BY ln.created_at DESC
                LIMIT 5
            """, item["id"], tenant_id)
            item["post_call_notes"] = [dict(n) for n in post_call_notes]

            # Apply filters
            next_dt = item.get("next_contact_date")
            is_overdue = item.get("is_overdue", False)

            if filter == "overdue":
                if not is_overdue:
                    continue
            elif filter == "today":
                if next_dt is None:
                    continue
                if hasattr(next_dt, 'date'):
                    if next_dt.date() != now.date():
                        continue
                else:
                    continue
            elif filter == "this_week":
                if next_dt is None:
                    continue
                if hasattr(next_dt, 'date'):
                    from datetime import timedelta
                    week_start = now.date() - timedelta(days=now.weekday())
                    week_end = week_start + timedelta(days=6)
                    if not (week_start <= next_dt.date() <= week_end):
                        continue
                else:
                    continue

            results.append(item)

        return {
            "success": True,
            "leads": results,
            "count": len(results),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting follow-up queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/follow-up-queue/{lead_id}/complete-followup")
async def complete_follow_up(
    lead_id: UUID = Path(..., description="ID of the lead"),
    request: CompleteFollowUpRequest = ...,
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_data=Depends(verify_admin_token)
):
    """
    Complete a follow-up for a lead:
    - Removes 'requiere_seguimiento' tag
    - Creates a lead_note with type 'follow_up'
    - If reschedule_date provided: creates new agenda event and re-adds tag
    - Updates lead status if result indicates completion or loss
    """
    try:
        from db import db

        seller_id = UUID(user_data.user_id)

        # 1. Verify lead exists and is assigned to this seller
        lead = await db.fetchrow("""
            SELECT id, phone_number, first_name, last_name, status, assigned_seller_id, tags
            FROM leads
            WHERE id = $1 AND tenant_id = $2
        """, lead_id, tenant_id)

        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")

        if str(lead["assigned_seller_id"]) != str(seller_id):
            raise HTTPException(status_code=403, detail="This lead is not assigned to you")

        phone = lead["phone_number"]
        name = f"{lead['first_name'] or ''} {lead['last_name'] or ''}".strip() or phone

        # 2. Remove 'requiere_seguimiento' tag
        existing_tags = lead["tags"] if lead["tags"] else []
        if isinstance(existing_tags, str):
            existing_tags = json.loads(existing_tags)

        tags_changed = False
        if "requiere_seguimiento" in existing_tags:
            existing_tags.remove("requiere_seguimiento")
            tags_changed = True

        # 3. Create lead_note with type 'follow_up'
        structured_data = {
            "result": request.result,
            "completed_at": datetime.utcnow().isoformat(),
        }
        if request.reschedule_date:
            structured_data["next_contact_date"] = request.reschedule_date.isoformat()

        await db.execute("""
            INSERT INTO lead_notes (tenant_id, lead_id, author_id, note_type, content, structured_data, visibility)
            VALUES ($1, $2, $3, 'follow_up', $4, $5, 'all')
        """, tenant_id, lead_id, seller_id, request.notes, structured_data)

        # 4. If reschedule_date: create new agenda event and re-add tag
        if request.reschedule_date:
            if "requiere_seguimiento" not in existing_tags:
                existing_tags.append("requiere_seguimiento")
                tags_changed = True

            # Find seller's professional id for agenda event
            professional_id = await db.fetchval("""
                SELECT p.id FROM professionals p
                JOIN users u ON u.professional_id = p.id
                WHERE u.id = $1 AND u.tenant_id = $2
            """, seller_id, tenant_id)

            if professional_id:
                from datetime import timedelta
                end_datetime = request.reschedule_date + timedelta(minutes=30)
                await db.execute("""
                    INSERT INTO seller_agenda_events
                    (tenant_id, seller_id, title, start_datetime, end_datetime, lead_id, notes, source, status)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, 'follow_up', 'scheduled')
                """, tenant_id, professional_id,
                    f"Seguimiento: {name}",
                    request.reschedule_date, end_datetime,
                    lead_id, f"Reagendado: {request.notes}")

        # 5. Update tags on lead
        if tags_changed:
            await db.execute(
                "UPDATE leads SET tags = $1::jsonb, updated_at = NOW() WHERE id = $2 AND tenant_id = $3",
                json.dumps(existing_tags), lead_id, tenant_id
            )

        # 6. Update lead status based on result
        new_status = None
        if request.result == "completed":
            new_status = "closed_won"
        elif request.result == "lost":
            new_status = "closed_lost"
        elif request.result == "contacted":
            new_status = "contacted"

        if new_status and new_status != lead["status"]:
            await db.execute("""
                UPDATE leads
                SET status = $1, status_changed_at = NOW(), status_changed_by = $2, updated_at = NOW()
                WHERE id = $3 AND tenant_id = $4
            """, new_status, seller_id, lead_id, tenant_id)

        # 7. Log tag changes
        if tags_changed:
            action_desc = "removed" if not request.reschedule_date else "rescheduled"
            await db.execute(
                "INSERT INTO lead_tag_log (tenant_id, lead_id, tags_added, reason, source) VALUES ($1, $2, $3, $4, 'follow_up_action')",
                tenant_id, lead_id, existing_tags,
                f"Follow-up {action_desc} by {user_data.email}: {request.result}",
            )

        # 8. Log system event
        await db.execute("""
            INSERT INTO system_events
            (tenant_id, event_type, severity, message, payload)
            VALUES ($1, 'follow_up_completed', 'info',
                    $2,
                    $3::jsonb)
        """, tenant_id,
            f"Follow-up completed for {name} by {user_data.email}",
            json.dumps({
                "lead_id": str(lead_id),
                "phone": phone,
                "result": request.result,
                "rescheduled": request.reschedule_date is not None,
                "seller_id": str(seller_id),
            })
        )

        logger.info(f"Follow-up completed for lead {name} ({phone}) by {user_data.email}, result: {request.result}")
        return {
            "success": True,
            "message": f"Seguimiento completado para {name}.",
            "lead_id": str(lead_id),
            "result": request.result,
            "rescheduled": request.reschedule_date is not None,
            "new_status": new_status,
            "tags": existing_tags,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing follow-up: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CLOSER PANEL (DEV-22) ====================

class CallResultEnum(str, Enum):
    closed_won = "closed_won"
    closed_lost = "closed_lost"
    follow_up_needed = "follow_up_needed"


class CompleteCallRequest(BaseModel):
    result: CallResultEnum = Field(..., description="Call outcome")
    notes: str = Field(..., min_length=1, max_length=2000, description="Post-call notes")


@router.get("/closer-panel", dependencies=[Depends(require_role(["closer", "ceo"]))])
async def get_closer_panel(
    status_filter: Optional[str] = Query(None, description="Filter by event status: scheduled, completed, cancelled"),
    date_from: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_data=Depends(verify_admin_token)
):
    """
    DEV-22: Closer panel — returns all assigned calls grouped by today/tomorrow/this_week/later.
    Each call includes prospect info, setter handoff notes, tags, and last 5 chat messages.
    """
    try:
        from db import db

        user_id = UUID(user_data.user_id)

        # Resolve the seller's professionals.id (seller_agenda_events.seller_id references professionals.id)
        seller_id = await db.fetchval(
            "SELECT id FROM professionals WHERE user_id = $1 AND tenant_id = $2",
            user_id, tenant_id
        )
        # Fallback: try sellers table if professionals doesn't have this user
        if seller_id is None:
            seller_id = await db.fetchval(
                "SELECT id FROM sellers WHERE user_id = $1 AND tenant_id = $2",
                user_id, tenant_id
            )

        if seller_id is None:
            return {
                "success": True,
                "groups": {"today": [], "tomorrow": [], "this_week": [], "later": []},
                "total": 0,
                "summary": {"today": 0, "tomorrow": 0, "this_week": 0, "later": 0},
            }

        # Build dynamic WHERE clause
        where_clauses = [
            "sae.seller_id = $1",
            "sae.tenant_id = $2",
        ]
        params: list = [seller_id, tenant_id]
        param_idx = 3

        if status_filter:
            where_clauses.append(f"sae.status = ${param_idx}")
            params.append(status_filter)
            param_idx += 1

        if date_from:
            where_clauses.append(f"sae.start_datetime >= ${param_idx}::date")
            params.append(date_from)
            param_idx += 1

        if date_to:
            where_clauses.append(f"sae.start_datetime < (${param_idx}::date + INTERVAL '1 day')")
            params.append(date_to)
            param_idx += 1

        where_sql = " AND ".join(where_clauses)

        # Main query: events + lead info
        events = await db.fetch(f"""
            SELECT
                sae.id AS event_id,
                sae.title,
                sae.start_datetime,
                sae.end_datetime,
                sae.notes AS event_notes,
                sae.source,
                sae.status AS event_status,
                sae.lead_id,
                sae.created_at AS event_created_at,
                -- Lead info
                l.first_name AS lead_first_name,
                l.last_name AS lead_last_name,
                l.phone_number AS lead_phone,
                l.email AS lead_email,
                l.tags AS lead_tags,
                l.score AS lead_score,
                l.status AS lead_status,
                l.source AS lead_source,
                l.company AS lead_company,
                l.estimated_value AS lead_estimated_value,
                -- Date grouping
                CASE
                    WHEN sae.start_datetime::date = CURRENT_DATE THEN 'today'
                    WHEN sae.start_datetime::date = CURRENT_DATE + 1 THEN 'tomorrow'
                    WHEN sae.start_datetime::date <= (CURRENT_DATE + INTERVAL '7 days') THEN 'this_week'
                    ELSE 'later'
                END AS date_group
            FROM seller_agenda_events sae
            LEFT JOIN leads l ON sae.lead_id = l.id AND l.tenant_id = $2
            WHERE {where_sql}
            ORDER BY sae.start_datetime ASC
        """, *params)

        # Collect lead_ids and event data for enrichment
        event_list = [dict(e) for e in events]
        lead_ids = [e["lead_id"] for e in event_list if e.get("lead_id")]

        # Fetch handoff notes for all relevant leads (batch)
        handoff_notes_map: dict = {}
        if lead_ids:
            notes_rows = await db.fetch("""
                SELECT ln.lead_id, ln.content, ln.note_type, ln.created_at,
                       u.first_name AS author_first_name,
                       u.last_name AS author_last_name,
                       u.role AS author_role
                FROM lead_notes ln
                LEFT JOIN users u ON ln.author_id = u.id
                WHERE ln.lead_id = ANY($1::uuid[])
                  AND ln.tenant_id = $2
                  AND ln.note_type IN ('handoff', 'post_call', 'follow_up')
                ORDER BY ln.created_at DESC
            """, lead_ids, tenant_id)

            for nr in notes_rows:
                lid = str(nr["lead_id"])
                if lid not in handoff_notes_map:
                    handoff_notes_map[lid] = []
                handoff_notes_map[lid].append({
                    "content": nr["content"],
                    "note_type": nr["note_type"],
                    "author": f"{nr['author_first_name'] or ''} {nr['author_last_name'] or ''}".strip(),
                    "author_role": nr["author_role"],
                    "created_at": nr["created_at"].isoformat() if nr["created_at"] else None,
                })

        # Fetch last 5 chat messages per lead phone (batch)
        chat_map: dict = {}
        phones = list(set(e["lead_phone"] for e in event_list if e.get("lead_phone")))
        if phones:
            for phone in phones:
                msgs = await db.fetch("""
                    SELECT role, content, created_at
                    FROM chat_messages
                    WHERE from_number = $1 AND tenant_id = $2
                    ORDER BY created_at DESC
                    LIMIT 5
                """, phone, tenant_id)
                chat_map[phone] = [
                    {
                        "role": m["role"],
                        "content": m["content"],
                        "created_at": m["created_at"].isoformat() if m["created_at"] else None,
                    }
                    for m in reversed(msgs)
                ]

        # Group events
        groups: dict = {"today": [], "tomorrow": [], "this_week": [], "later": []}
        for ev in event_list:
            lead_id_str = str(ev["lead_id"]) if ev.get("lead_id") else None
            phone = ev.get("lead_phone")

            entry = {
                "event_id": str(ev["event_id"]),
                "title": ev["title"],
                "start_datetime": ev["start_datetime"].isoformat() if ev["start_datetime"] else None,
                "end_datetime": ev["end_datetime"].isoformat() if ev["end_datetime"] else None,
                "event_notes": ev["event_notes"],
                "source": ev["source"],
                "status": ev["event_status"],
                "created_at": ev["event_created_at"].isoformat() if ev["event_created_at"] else None,
                "lead": {
                    "id": lead_id_str,
                    "first_name": ev.get("lead_first_name"),
                    "last_name": ev.get("lead_last_name"),
                    "phone": phone,
                    "email": ev.get("lead_email"),
                    "tags": ev.get("lead_tags") or [],
                    "score": ev.get("lead_score") or 0,
                    "status": ev.get("lead_status"),
                    "source": ev.get("lead_source"),
                    "company": ev.get("lead_company"),
                    "estimated_value": float(ev["lead_estimated_value"]) if ev.get("lead_estimated_value") else 0,
                } if lead_id_str else None,
                "handoff_notes": handoff_notes_map.get(lead_id_str, []) if lead_id_str else [],
                "recent_messages": chat_map.get(phone, []) if phone else [],
            }

            group_key = ev.get("date_group", "later")
            groups.setdefault(group_key, []).append(entry)

        total = sum(len(v) for v in groups.values())

        return {
            "success": True,
            "groups": groups,
            "total": total,
            "summary": {
                "today": len(groups.get("today", [])),
                "tomorrow": len(groups.get("tomorrow", [])),
                "this_week": len(groups.get("this_week", [])),
                "later": len(groups.get("later", [])),
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting closer panel: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/closer-panel/{event_id}/complete", dependencies=[Depends(require_role(["closer", "ceo"]))])
async def complete_closer_call(
    event_id: UUID,
    request: CompleteCallRequest,
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_data=Depends(verify_admin_token)
):
    """
    DEV-22: Mark a closer call as completed and update lead status accordingly.
    - closed_won  -> tag 'cerrado', lead status 'won'
    - closed_lost -> tag 'perdido', lead status 'lost'
    - follow_up_needed -> tag 'requiere_seguimiento', lead status 'follow_up'
    Creates a post_call note and notifies the original setter.
    """
    try:
        from db import db

        user_id = UUID(user_data.user_id)

        # 1. Get and validate the event
        event = await db.fetchrow("""
            SELECT sae.id, sae.seller_id, sae.lead_id, sae.status, sae.tenant_id,
                   l.phone_number AS lead_phone, l.tags AS lead_tags,
                   l.assigned_seller_id AS setter_user_id, l.status AS lead_status
            FROM seller_agenda_events sae
            LEFT JOIN leads l ON sae.lead_id = l.id
            WHERE sae.id = $1 AND sae.tenant_id = $2
        """, event_id, tenant_id)

        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        if event["status"] == "completed":
            raise HTTPException(status_code=400, detail="Event already completed")

        lead_id = event["lead_id"]
        call_result = request.result.value

        # 2. Determine new lead status and tag based on result
        RESULT_MAP = {
            "closed_won": {"lead_status": "won", "tag": "cerrado"},
            "closed_lost": {"lead_status": "lost", "tag": "perdido"},
            "follow_up_needed": {"lead_status": "follow_up", "tag": "requiere_seguimiento"},
        }
        mapping = RESULT_MAP[call_result]
        new_lead_status = mapping["lead_status"]
        new_tag = mapping["tag"]

        # 3. Update event status to completed
        await db.execute("""
            UPDATE seller_agenda_events
            SET status = 'completed',
                notes = COALESCE(notes, '') || E'\n[Resultado: ' || $2 || '] ' || $3,
                updated_at = NOW()
            WHERE id = $1
        """, event_id, call_result, request.notes)

        # 4. Update lead status and add tag
        if lead_id:
            current_tags = event["lead_tags"] or []
            if isinstance(current_tags, str):
                try:
                    current_tags = json.loads(current_tags)
                except Exception:
                    current_tags = []

            if new_tag not in current_tags:
                current_tags.append(new_tag)

            await db.execute("""
                UPDATE leads
                SET status = $2,
                    tags = $3::jsonb,
                    status_changed_at = NOW(),
                    status_changed_by = $4,
                    updated_at = NOW()
                WHERE id = $1 AND tenant_id = $5
            """, lead_id, new_lead_status, json.dumps(current_tags), user_id, tenant_id)

            # 5. Create post_call lead_note
            await db.execute("""
                INSERT INTO lead_notes (tenant_id, lead_id, author_id, note_type, content, structured_data, visibility)
                VALUES ($1, $2, $3, 'post_call', $4, $5::jsonb, 'all')
            """, tenant_id, lead_id, user_id, request.notes, json.dumps({
                "result": call_result,
                "event_id": str(event_id),
                "closer_user_id": str(user_id),
            }))

            # 6. Log tag change in lead_tag_log
            await db.execute("""
                INSERT INTO lead_tag_log (tenant_id, lead_id, tags_added, reason, source)
                VALUES ($1, $2, $3, $4, 'closer_panel')
            """, tenant_id, lead_id, [new_tag], f"Closer call result: {call_result}")

            # 7. Notify setter about the result
            setter_user_id = event.get("setter_user_id")
            if setter_user_id and str(setter_user_id) != str(user_id):
                try:
                    from services.seller_notification_service import seller_notification_service, Notification
                    import datetime as _dt

                    result_labels = {
                        "closed_won": "CERRADO - Ganado",
                        "closed_lost": "CERRADO - Perdido",
                        "follow_up_needed": "Requiere seguimiento",
                    }
                    timestamp = _dt.datetime.utcnow().timestamp()
                    lead_phone = event.get("lead_phone", "N/A")

                    notif = Notification(
                        id=f"closer_result_{event_id}_{timestamp}",
                        tenant_id=tenant_id,
                        type="assignment",
                        title=f"Resultado de llamada: {result_labels.get(call_result, call_result)}",
                        message=f"El closer completo la llamada con {lead_phone}. Resultado: {result_labels.get(call_result, call_result)}. Notas: {request.notes[:100]}",
                        priority="high",
                        recipient_id=str(setter_user_id),
                        sender_id=str(user_id),
                        related_entity_type="lead",
                        related_entity_id=str(lead_id),
                        metadata={"event_id": str(event_id), "result": call_result, "phone": lead_phone},
                    )
                    await seller_notification_service.save_notifications([notif])
                    await seller_notification_service.broadcast_notifications([notif])

                except Exception as notif_err:
                    logger.warning(f"Could not send setter notification: {notif_err}")

        return {
            "success": True,
            "message": f"Call marked as completed with result: {call_result}",
            "event_id": str(event_id),
            "lead_id": str(lead_id) if lead_id else None,
            "result": call_result,
            "new_lead_status": new_lead_status,
            "tag_added": new_tag,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing closer call: {e}")
        raise HTTPException(status_code=500, detail=str(e))