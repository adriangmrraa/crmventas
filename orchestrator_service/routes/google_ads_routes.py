"""
Google Ads Routes for CRM Ventas
Handles Google Ads API endpoints for campaigns, metrics, and data sync.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from core.security import verify_admin_token, get_resolved_tenant_id, audit_access
from core.rate_limiter import limiter
from services.marketing.google_ads_service import GoogleAdsService

logger = logging.getLogger(__name__)
router = APIRouter()

# ==================== GOOGLE ADS ENDPOINTS ====================

@router.get("/google/campaigns")
@audit_access("get_google_ads_campaigns")
@limiter.limit("30/minute")
async def get_google_ads_campaigns(
    request: Request,
    customer_id: str = Query(..., description="Google Ads customer ID"),
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
) -> Dict[str, Any]:
    """
    Get Google Ads campaigns for a customer.
    """
    try:
        campaigns = await GoogleAdsService.get_campaigns(tenant_id, customer_id)
        
        return {
            "success": True,
            "data": campaigns,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Google Ads campaigns: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting Google Ads campaigns: {str(e)}")

@router.get("/google/metrics")
@audit_access("get_google_ads_metrics")
@limiter.limit("30/minute")
async def get_google_ads_metrics(
    request: Request,
    customer_id: str = Query(..., description="Google Ads customer ID"),
    date_range: str = Query("LAST_30_DAYS", description="Date range preset"),
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
) -> Dict[str, Any]:
    """
    Get Google Ads metrics for a customer.
    """
    try:
        metrics = await GoogleAdsService.get_metrics(tenant_id, customer_id, date_range)
        
        return {
            "success": True,
            "data": metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Google Ads metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting Google Ads metrics: {str(e)}")

@router.get("/google/customers")
@audit_access("get_google_ads_customers")
@limiter.limit("20/minute")
async def get_google_ads_customers(
    request: Request,
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
) -> Dict[str, Any]:
    """
    Get accessible Google Ads customer accounts.
    """
    try:
        customer_ids = await GoogleAdsService.get_accessible_customers(tenant_id)
        
        return {
            "success": True,
            "data": customer_ids,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting Google Ads customers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting Google Ads customers: {str(e)}")

@router.post("/google/sync")
@audit_access("sync_google_ads_data")
@limiter.limit("10/minute")
async def sync_google_ads_data(
    request: Request,
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
) -> Dict[str, Any]:
    """
    Sync Google Ads data (background job).
    """
    try:
        sync_result = await GoogleAdsService.sync_google_ads_data(tenant_id)
        
        return {
            "success": True,
            "data": sync_result,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error syncing Google Ads data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error syncing Google Ads data: {str(e)}")

@router.get("/google/stats")
@audit_access("get_google_ads_stats")
@limiter.limit("30/minute")
async def get_google_ads_stats(
    request: Request,
    customer_id: Optional[str] = Query(None, description="Google Ads customer ID (optional)"),
    date_range: str = Query("LAST_30_DAYS", description="Date range preset"),
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
) -> Dict[str, Any]:
    """
    Get combined Google Ads stats (campaigns + metrics).
    """
    try:
        # Get connection status
        connection = await GoogleAdsService.test_connection(tenant_id)
        
        if not connection.get("connected") or not connection.get("customer_ids"):
            return {
                "success": True,
                "data": {
                    "connected": False,
                    "campaigns": [],
                    "metrics": {},
                    "customer_ids": [],
                    "message": "Google Ads not connected"
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Use provided customer_id or first accessible
        target_customer = customer_id or connection.get("customer_ids", [])[0]
        
        # Get campaigns and metrics
        campaigns = await GoogleAdsService.get_campaigns(tenant_id, target_customer)
        metrics = await GoogleAdsService.get_metrics(tenant_id, target_customer, date_range)
        
        return {
            "success": True,
            "data": {
                "connected": True,
                "campaigns": campaigns,
                "metrics": metrics,
                "customer_ids": connection.get("customer_ids", []),
                "current_customer": target_customer,
                "google_connected": True
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting Google Ads stats: {e}", exc_info=True)
        return {
            "success": True,
            "data": {
                "connected": False,
                "campaigns": [],
                "metrics": {},
                "customer_ids": [],
                "message": f"Error: {str(e)}"
            },
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/google/connection-status")
@audit_access("get_google_ads_connection_status")
@limiter.limit("20/minute")
async def get_google_ads_connection_status(
    request: Request,
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
) -> Dict[str, Any]:
    """
    Get Google Ads connection status.
    """
    try:
        status = await GoogleAdsService.test_connection(tenant_id)
        
        return {
            "success": True,
            "data": status,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting Google Ads connection status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting Google Ads connection status: {str(e)}")

@router.get("/combined-stats")
@audit_access("get_combined_marketing_stats")
@limiter.limit("30/minute")
async def get_combined_marketing_stats(
    request: Request,
    time_range: str = Query("last_30d", description="Time range for Meta stats"),
    google_date_range: str = Query("LAST_30_DAYS", description="Date range for Google stats"),
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
) -> Dict[str, Any]:
    """
    Get combined marketing stats from both Meta and Google.
    """
    try:
        from services.marketing.marketing_service import MarketingService
        
        # Get Meta stats
        meta_stats = await MarketingService.get_roi_stats(tenant_id, time_range)
        meta_campaign_stats = await MarketingService.get_campaign_stats(tenant_id, time_range)
        
        # Get Google stats
        google_connection = await GoogleAdsService.test_connection(tenant_id)
        google_connected = google_connection.get("connected", False)
        
        google_stats = {
            "connected": google_connected,
            "customer_ids": google_connection.get("customer_ids", []),
            "campaigns": [],
            "metrics": {}
        }
        
        if google_connected and google_connection.get("customer_ids"):
            try:
                target_customer = google_connection.get("customer_ids", [])[0]
                google_campaigns = await GoogleAdsService.get_campaigns(tenant_id, target_customer)
                google_metrics = await GoogleAdsService.get_metrics(tenant_id, target_customer, google_date_range)
                
                google_stats["campaigns"] = google_campaigns
                google_stats["metrics"] = google_metrics
                google_stats["current_customer"] = target_customer
            except Exception as e:
                logger.warning(f"Error fetching Google Ads data, returning empty: {e}")
        
        return {
            "success": True,
            "data": {
                "meta": {
                    "roi": meta_stats,
                    "campaigns": meta_campaign_stats,
                    "currency": meta_stats.get("currency", "ARS"),
                    "meta_connected": meta_stats.get("is_connected", False)
                },
                "google": google_stats,
                "combined": {
                    "meta_connected": meta_stats.get("is_connected", False),
                    "google_connected": google_connected,
                    "total_platforms": 1 + (1 if google_connected else 0)
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting combined marketing stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting combined marketing stats: {str(e)}")

@router.get("/google/debug")
@audit_access("debug_google_ads")
@limiter.limit("10/minute")
async def debug_google_ads(
    request: Request,
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
) -> Dict[str, Any]:
    """
    Debug endpoint for Google Ads integration.
    """
    try:
        from core.credentials import get_tenant_credential
        import json
        
        # Get token status
        token_json = await get_tenant_credential(tenant_id, "GOOGLE_ADS_TOKEN")
        token_exists = bool(token_json)
        
        # Test connection
        connection = await GoogleAdsService.test_connection(tenant_id)
        
        # Get environment info
        import os
        env_info = {
            "GOOGLE_CLIENT_ID": "Set" if os.getenv("GOOGLE_CLIENT_ID") else "Not set",
            "GOOGLE_DEVELOPER_TOKEN": "Set" if os.getenv("GOOGLE_DEVELOPER_TOKEN") else "Not set",
            "GOOGLE_ADS_API_VERSION": os.getenv("GOOGLE_ADS_API_VERSION", "v16")
        }
        
        return {
            "success": True,
            "data": {
                "environment": env_info,
                "token_exists": token_exists,
                "token_size": len(token_json) if token_json else 0,
                "connection": connection,
                "timestamp": datetime.utcnow().isoformat()
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error in Google Ads debug: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }