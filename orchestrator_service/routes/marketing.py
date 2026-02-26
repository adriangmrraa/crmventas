"""
Marketing Routes for CRM Ventas
Adapted from ClinicForge for CRM Sales context
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from core.security import verify_admin_token, get_resolved_tenant_id, audit_access
from core.rate_limiter import limiter
from services.marketing.marketing_service import MarketingService
from services.marketing.meta_ads_service import MetaAdsService
from services.marketing.automation_service import AutomationService

logger = logging.getLogger(__name__)
router = APIRouter()

# ==================== DASHBOARD ENDPOINTS ====================

@router.get("/stats")
@audit_access("get_marketing_stats")
@limiter.limit("100/minute")
async def get_marketing_stats(
    request: Request,
    time_range: str = Query("last_30d", description="Time range: last_30d, last_90d, this_year, yearly, lifetime"),
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
) -> Dict[str, Any]:
    """
    Get marketing dashboard statistics.
    """
    try:
        stats = await MarketingService.get_roi_stats(tenant_id, time_range)
        # Add meta_connected alias so the frontend's isMetaConnected detection works
        stats["meta_connected"] = stats.get("is_connected", False)
        campaign_stats = await MarketingService.get_campaign_stats(tenant_id, time_range)
        return {
            "success": True,
            "data": {
                "roi": stats,
                "campaigns": campaign_stats,
                "currency": stats.get("currency", "ARS"),
                "meta_connected": stats.get("is_connected", False)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting marketing stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting marketing stats: {str(e)}") 


@router.get("/stats/roi")
@audit_access("get_roi_details")
@limiter.limit("50/minute")
async def get_roi_details(
    request: Request,
    time_range: str = Query("last_30d", description="Time range for ROI details"),
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
) -> Dict[str, Any]:
    """
    Get detailed ROI breakdown.
    """
    try:
        details = await MarketingService.get_roi_stats(tenant_id, time_range)
        return {
            "success": True,
            "data": details,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting ROI details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting ROI details: {str(e)}")

@router.get("/token-status")
@audit_access("get_token_status")
@limiter.limit("30/minute")
async def get_token_status(
    request: Request,
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
) -> Dict[str, Any]:
    """
    Check Meta Ads token status and connection.
    """
    try:
        status = await MetaAdsService.check_token_status(tenant_id)
        return {
            "success": True,
            "data": status,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error checking token status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error checking token status: {str(e)}")

@router.get("/meta-portfolios")
@audit_access("get_meta_portfolios")
@limiter.limit("20/minute")
async def get_meta_portfolios(
    request: Request,
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
) -> Dict[str, Any]:
    """
    Get Meta Business Managers (portfolios).
    """
    try:
        portfolios = await MetaAdsService.get_business_managers(tenant_id)
        return {
            "success": True,
            "data": portfolios,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting Meta portfolios: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting Meta portfolios: {str(e)}")

@router.get("/meta-accounts")
@audit_access("get_meta_accounts")
@limiter.limit("20/minute")
async def get_meta_accounts(
    request: Request,
    portfolio_id: Optional[str] = Query(None, description="Business Manager ID"),
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
) -> Dict[str, Any]:
    """
    Get Meta Ad Accounts.
    """
    try:
        accounts = await MetaAdsService.get_ad_accounts(tenant_id, portfolio_id)
        return {
            "success": True,
            "data": accounts,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting Meta accounts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting Meta accounts: {str(e)}")

@router.post("/connect")
@audit_access("connect_meta_account")
@limiter.limit("10/minute")
async def connect_meta_account(
    request: Request,
    data: Dict[str, Any],
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
) -> Dict[str, Any]:
    """
    Connect Meta Ad Account to CRM.
    """
    try:
        account_id = data.get("account_id")
        account_name = data.get("account_name")
        
        if not account_id or not account_name:
            raise HTTPException(status_code=400, detail="account_id and account_name are required")
        
        result = await MetaAdsService.connect_ad_account(tenant_id, account_id, account_name)
        return {
            "success": True,
            "data": result,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error connecting Meta account: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error connecting Meta account: {str(e)}")

# ==================== HSM AUTOMATION ENDPOINTS ====================

@router.get("/automation-logs")
@audit_access("get_automation_logs")
@limiter.limit("50/minute")
async def get_automation_logs(
    request: Request,
    limit: int = Query(100, description="Number of logs to return"),
    offset: int = Query(0, description="Offset for pagination"),
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
) -> Dict[str, Any]:
    """
    Get HSM automation logs.
    """
    try:
        logs = await AutomationService.get_automation_logs(tenant_id, limit, offset)
        return {
            "success": True,
            "data": logs,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting automation logs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting automation logs: {str(e)}")

@router.get("/hsm/templates")
@audit_access("get_hsm_templates")
@limiter.limit("30/minute")
async def get_hsm_templates(
    request: Request,
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
) -> Dict[str, Any]:
    """
    Get WhatsApp HSM templates.
    """
    try:
        templates = await AutomationService.get_hsm_templates(tenant_id)
        return {
            "success": True,
            "data": templates,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting HSM templates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting HSM templates: {str(e)}")

@router.get("/automation/rules")
@audit_access("get_automation_rules")
@limiter.limit("30/minute")
async def get_automation_rules(
    request: Request,
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
) -> Dict[str, Any]:
    """
    Get automation rules configuration.
    """
    try:
        rules = await AutomationService.get_automation_rules(tenant_id)
        return {
            "success": True,
            "data": rules,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting automation rules: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting automation rules: {str(e)}")

@router.post("/automation/rules")
@audit_access("update_automation_rules")
@limiter.limit("10/minute")
async def update_automation_rules(
    request: Request,
    data: Dict[str, Any],
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
) -> Dict[str, Any]:
    """
    Update automation rules configuration.
    """
    try:
        rules = data.get("rules", {})
        result = await AutomationService.update_automation_rules(tenant_id, rules)
        return {
            "success": True,
            "data": result,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error updating automation rules: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error updating automation rules: {str(e)}")

# ==================== CAMPAIGN MANAGEMENT ====================

@router.get("/campaigns")
@audit_access("get_campaigns")
@limiter.limit("50/minute")
async def get_campaigns(
    request: Request,
    status: Optional[str] = Query(None, description="Filter by status: ACTIVE, PAUSED, ARCHIVED"),
    limit: int = Query(50, description="Number of campaigns to return"),
    offset: int = Query(0, description="Offset for pagination"),
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
) -> Dict[str, Any]:
    """
    Get Meta Ads campaigns with performance data.
    """
    try:
        campaigns = await MetaAdsService.get_campaigns_with_performance(tenant_id, status, limit, offset)
        return {
            "success": True,
            "data": campaigns,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting campaigns: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting campaigns: {str(e)}")

@router.get("/campaigns/{campaign_id}")
@audit_access("get_campaign_details")
@limiter.limit("30/minute")
async def get_campaign_details(
    request: Request,
    campaign_id: str,
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
) -> Dict[str, Any]:
    """
    Get detailed campaign information.
    """
    try:
        details = await MetaAdsService.get_campaign_details(tenant_id, campaign_id)
        return {
            "success": True,
            "data": details,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting campaign details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting campaign details: {str(e)}")

@router.get("/campaigns/{campaign_id}/insights")
@audit_access("get_campaign_insights")
@limiter.limit("30/minute")
async def get_campaign_insights(
    request: Request,
    campaign_id: str,
    time_range: str = Query("last_30d", description="Time range for insights"),
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
) -> Dict[str, Any]:
    """
    Get campaign insights and performance metrics.
    """
    try:
        insights = await MetaAdsService.get_campaign_insights(tenant_id, campaign_id, time_range)
        return {
            "success": True,
            "data": insights,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting campaign insights: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting campaign insights: {str(e)}")