"""
API Routes for advanced metrics and real-time analytics
"""
import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from core.security import verify_admin_token, get_resolved_tenant_id, require_role
from services.metrics_cache_service import metrics_cache_service
from services.seller_metrics_service import seller_metrics_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/core/metrics", tags=["Advanced Metrics"])

# ==================== MODELS ====================

class RealtimeMetricsRequest(BaseModel):
    seller_id: UUID = Field(..., description="ID of the seller")
    include_trends: bool = Field(default=True, description="Include performance trends")

class DailySummaryRequest(BaseModel):
    date: Optional[str] = Field(None, description="Date in YYYY-MM-DD format (default: today)")

class MetricsInsightsRequest(BaseModel):
    seller_id: UUID = Field(..., description="ID of the seller to analyze")

class SystemHealthResponse(BaseModel):
    database: bool
    redis: bool
    metrics_calculation: bool
    timestamp: str
    cache_hit_rate: Optional[float] = None
    error: Optional[str] = None

# ==================== REALTIME METRICS ====================

@router.get("/realtime/conversations/{seller_id}")
async def get_realtime_conversation_metrics(
    seller_id: UUID,
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_id: UUID = Depends(verify_admin_token)
):
    """
    Get real-time conversation metrics for a seller
    Optimized with Redis caching for frequent access
    """
    try:
        # Check permissions - seller can only see their own metrics
        # unless they're CEO
        from db import db
        user = await db.fetchrow("SELECT role FROM users WHERE id = $1", user_id)
        
        if user and user['role'] != 'ceo' and str(user_id) != str(seller_id):
            raise HTTPException(status_code=403, detail="Can only view your own metrics")
        
        metrics = await metrics_cache_service.get_realtime_conversation_metrics(
            seller_id=seller_id,
            tenant_id=tenant_id
        )
        
        return {
            "success": True,
            "metrics": metrics,
            "seller_id": str(seller_id),
            "cached": 'cached_at' in metrics
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting realtime conversation metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/realtime/team")
async def get_realtime_team_metrics(
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_id: UUID = Depends(verify_admin_token)
):
    """
    Get real-time metrics for all sellers in the team
    CEO only endpoint
    """
    try:
        # Only CEO can see team metrics
        await require_role(user_id, ["ceo"])
        
        from db import db
        
        # Get all active sellers
        sellers = await db.fetch("""
            SELECT id, first_name, last_name, role
            FROM users
            WHERE tenant_id = $1
            AND status = 'active'
            AND role IN ('setter', 'closer', 'professional', 'ceo')
        """, tenant_id)
        
        team_metrics = []
        for seller in sellers:
            metrics = await metrics_cache_service.get_realtime_conversation_metrics(
                seller_id=seller['id'],
                tenant_id=tenant_id
            )
            
            team_metrics.append({
                "seller_id": str(seller['id']),
                "first_name": seller['first_name'],
                "last_name": seller['last_name'],
                "role": seller['role'],
                "metrics": metrics
            })
        
        # Calculate team totals
        totals = {
            "total_active_conversations": sum(m['metrics'].get('active_conversations', 0) for m in team_metrics),
            "total_today_assignments": sum(m['metrics'].get('today_assignments', 0) for m in team_metrics),
            "total_unread_messages": sum(m['metrics'].get('unread_messages', 0) for m in team_metrics),
            "avg_response_time": sum(m['metrics'].get('avg_response_seconds', 0) for m in team_metrics) / max(len(team_metrics), 1),
            "seller_count": len(team_metrics)
        }
        
        return {
            "success": True,
            "team_metrics": team_metrics,
            "totals": totals,
            "seller_count": len(team_metrics)
        }
        
    except Exception as e:
        logger.error(f"Error getting realtime team metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== PERFORMANCE TRENDS ====================

@router.get("/trends/{seller_id}")
async def get_performance_trends(
    seller_id: UUID,
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze"),
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_id: UUID = Depends(verify_admin_token)
):
    """
    Get performance trends over time for a seller
    """
    try:
        # Check permissions
        from db import db
        user = await db.fetchrow("SELECT role FROM users WHERE id = $1", user_id)
        
        if user and user['role'] != 'ceo' and str(user_id) != str(seller_id):
            raise HTTPException(status_code=403, detail="Can only view your own trends")
        
        trends = await metrics_cache_service.get_performance_trends(
            seller_id=seller_id,
            tenant_id=tenant_id,
            days=days
        )
        
        return {
            "success": True,
            "trends": trends,
            "period_days": days,
            "seller_id": str(seller_id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting performance trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== DAILY SUMMARY ====================

@router.get("/daily/summary")
async def get_daily_metrics_summary(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format (default: today)"),
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_id: UUID = Depends(verify_admin_token)
):
    """
    Get daily metrics summary for CEO dashboard
    CEO only endpoint
    """
    try:
        # Only CEO can see daily summary
        await require_role(user_id, ["ceo"])
        
        summary = await metrics_cache_service.get_daily_metrics_summary(
            tenant_id=tenant_id,
            date=date
        )
        
        return {
            "success": True,
            "summary": summary,
            "cached": 'calculated_at' in summary
        }
        
    except Exception as e:
        logger.error(f"Error getting daily metrics summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== METRICS INSIGHTS ====================

@router.get("/insights/{seller_id}")
async def get_metrics_insights(
    seller_id: UUID,
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_id: UUID = Depends(verify_admin_token)
):
    """
    Get AI-powered insights from seller metrics
    """
    try:
        # Check permissions
        from db import db
        user = await db.fetchrow("SELECT role FROM users WHERE id = $1", user_id)
        
        if user and user['role'] != 'ceo' and str(user_id) != str(seller_id):
            raise HTTPException(status_code=403, detail="Can only view your own insights")
        
        insights = await metrics_cache_service.get_metrics_insights(
            seller_id=seller_id,
            tenant_id=tenant_id
        )
        
        return {
            "success": True,
            "insights": insights
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metrics insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== SYSTEM HEALTH ====================

@router.get("/system/health")
async def get_system_health(
    user_id: UUID = Depends(verify_admin_token)
):
    """
    Get system health metrics for monitoring
    Admin/CEO only endpoint
    """
    try:
        # Only admin/CEO can see system health
        await require_role(user_id, ["ceo", "admin"])
        
        health = await metrics_cache_service.get_system_health_metrics()
        
        return {
            "success": True,
            "health": health,
            "timestamp": health.get('timestamp')
        }
        
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== CACHE MANAGEMENT ====================

@router.post("/cache/invalidate/{seller_id}")
async def invalidate_metrics_cache(
    seller_id: UUID,
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_id: UUID = Depends(verify_admin_token)
):
    """
    Invalidate metrics cache for a seller
    Admin/CEO only endpoint
    """
    try:
        # Only admin/CEO can invalidate cache
        await require_role(user_id, ["ceo", "admin"])
        
        await metrics_cache_service.invalidate_metrics_cache(
            seller_id=seller_id,
            tenant_id=tenant_id
        )
        
        return {
            "success": True,
            "message": f"Cache invalidated for seller {seller_id}",
            "seller_id": str(seller_id)
        }
        
    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cache/cleanup")
async def cleanup_old_cache(
    days: int = Query(7, ge=1, le=30, description="Cleanup cache older than X days"),
    user_id: UUID = Depends(verify_admin_token)
):
    """
    Cleanup old cache entries
    Admin/CEO only endpoint
    """
    try:
        # Only admin/CEO can cleanup cache
        await require_role(user_id, ["ceo", "admin"])
        
        await metrics_cache_service.cleanup_old_cache(days=days)
        
        return {
            "success": True,
            "message": f"Cache cleanup initiated for entries older than {days} days"
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== COMPARATIVE ANALYTICS ====================

@router.get("/comparative/team")
async def get_comparative_team_analytics(
    metric: str = Query("conversion_rate", description="Metric to compare: conversion_rate, active_conversations, avg_response_time"),
    period_days: int = Query(7, ge=1, le=90, description="Period in days"),
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_id: UUID = Depends(verify_admin_token)
):
    """
    Get comparative analytics for the team
    CEO only endpoint
    """
    try:
        # Only CEO can see comparative analytics
        await require_role(user_id, ["ceo"])
        
        from db import db
        
        # Get all sellers with their latest metrics
        sellers = await db.fetch("""
            SELECT 
                u.id,
                u.first_name,
                u.last_name,
                u.role,
                sm.*
            FROM users u
            LEFT JOIN seller_metrics sm ON u.id = sm.seller_id
                AND sm.tenant_id = $1
                AND sm.metrics_period_start >= NOW() - INTERVAL '$2 days'
            WHERE u.tenant_id = $1
            AND u.status = 'active'
            AND u.role IN ('setter', 'closer', 'professional', 'ceo')
            ORDER BY 
                CASE WHEN sm.conversion_rate IS NULL THEN 1 ELSE 0 END,
                sm.conversion_rate DESC NULLS LAST
        """, tenant_id, period_days)
        
        # Prepare comparative data
        comparative_data = []
        valid_metric = False
        
        for seller in sellers:
            seller_data = dict(seller)
            metric