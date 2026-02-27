"""
API Routes for seller assignment and metrics management
"""
import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from core.security import verify_admin_token, get_resolved_tenant_id, require_role
from services.seller_assignment_service import seller_assignment_service
from services.seller_metrics_service import seller_metrics_service

logger = logging.getLogger(__name__)

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
    user_id: UUID = Depends(verify_admin_token)
):
    """
    Assign a conversation to a seller
    """
    try:
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
        
    except Exception as e:
        logger.error(f"Error assigning conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversations/{phone}/assignment")
async def get_conversation_assignment(
    phone: str,
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_id: UUID = Depends(verify_admin_token)
):
    """
    Get current assignment for a conversation
    """
    try:
        assignment = await seller_assignment_service.get_conversation_assignment(
            phone=phone,
            tenant_id=tenant_id
        )
        
        if not assignment:
            raise HTTPException(status_code=404, detail="No assignment found")
        
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
    user_id: UUID = Depends(verify_admin_token)
):
    """
    Reassign a conversation to a different seller
    """
    try:
        # Only CEO can reassign conversations
        await require_role(user_id, ["ceo"])
        
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
        
    except Exception as e:
        logger.error(f"Error reassigning conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/conversations/{phone}/auto-assign")
async def auto_assign_conversation(
    phone: str,
    lead_source: Optional[str] = Query(None, description="Lead source for rule filtering"),
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_id: UUID = Depends(verify_admin_token)
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
    user_id: UUID = Depends(verify_admin_token)
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
    user_id: UUID = Depends(verify_admin_token)
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
    user_id: UUID = Depends(verify_admin_token)
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

@router.get("/team/metrics")
async def get_team_metrics(
    request: MetricsRequest = Depends(),
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_id: UUID = Depends(verify_admin_token)
):
    """
    Get metrics for all sellers in the team
    """
    try:
        # Only CEO can see team metrics
        await require_role(user_id, ["ceo"])
        
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
    user_id: UUID = Depends(verify_admin_token)
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
    user_id: UUID = Depends(verify_admin_token)
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

@router.post("/rules")
async def create_assignment_rule(
    request: AssignmentRuleCreate,
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_id: UUID = Depends(verify_admin_token)
):
    """
    Create a new assignment rule
    """
    try:
        # Only CEO can create rules
        await require_role(user_id, ["ceo"])
        
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

@router.put("/rules/{rule_id}")
async def update_assignment_rule(
    rule_id: UUID,
    request: AssignmentRuleCreate,
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_id: UUID = Depends(verify_admin_token)
):
    """
    Update an assignment rule
    """
    try:
        # Only CEO can update rules
        await require_role(user_id, ["ceo"])
        
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

@router.delete("/rules/{rule_id}")
async def delete_assignment_rule(
    rule_id: UUID,
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_id: UUID = Depends(verify_admin_token)
):
    """
    Delete an assignment rule
    """
    try:
        # Only CEO can delete rules
        await require_role(user_id, ["ceo"])
        
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
    user_id: UUID = Depends(verify_admin_token)
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
    user_id: UUID = Depends(verify_admin_token)
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