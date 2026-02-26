"""
Meta OAuth Routes for CRM Ventas
Handles Meta/Facebook OAuth flow for connecting ad accounts
"""

import os
import secrets
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from core.security import verify_admin_token, get_resolved_tenant_id, audit_access
from core.rate_limiter import limiter
from services.marketing.meta_ads_service import MetaAdsService

logger = logging.getLogger(__name__)
router = APIRouter()

# OAuth configuration
META_APP_ID = os.getenv("META_APP_ID", "YOUR_META_APP_ID")  # From environment variables
META_APP_SECRET = os.getenv("META_APP_SECRET", "YOUR_META_APP_SECRET")  # From environment variables
META_REDIRECT_URI = os.getenv("META_REDIRECT_URI", "").rstrip("/")
# Si la URI ya viene con el path completo, la dejamos como está (pero sin slash al final).
# Si no incluye /callback, se vuelve una URL parcial que el frontend o el backend podrían romper.
# Para CRM Ventas, el estándar es f"{ORCHESTRATOR_URL}/crm/auth/meta/callback"

META_SCOPES = [
    "ads_management",
    "ads_read",
    "business_management",
    "whatsapp_business_management",
    "whatsapp_business_messaging"
]
FRONTEND_URL = os.getenv("PLATFORM_URL", os.getenv("FRONTEND_URL", "")).rstrip("/")

# Store OAuth states (in production, use Redis)
oauth_states = {}

@router.get("/url")
@audit_access("get_meta_auth_url")
@limiter.limit("20/minute")
async def get_meta_auth_url(
    request: Request,
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
) -> Dict[str, Any]:
    """
    Generate Meta OAuth authorization URL.
    Returns URL for user to authorize the app.
    """
    try:
        # Generate secure state parameter
        state = f"tenant_{tenant_id}_{secrets.token_urlsafe(32)}"
        oauth_states[state] = {
            "tenant_id": tenant_id,
            "user_id": user_data.user_id,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Clean old states (in production, use TTL in Redis)
        current_time = datetime.utcnow()
        states_to_delete = []
        for s, data in oauth_states.items():
            created_at = datetime.fromisoformat(data["created_at"])
            if (current_time - created_at).total_seconds() > 300:  # 5 minutes
                states_to_delete.append(s)
        
        for s in states_to_delete:
            del oauth_states[s]
        
        # Build OAuth URL
        scopes_str = ",".join(META_SCOPES)
        auth_url = (
            f"https://www.facebook.com/v19.0/dialog/oauth?"
            f"client_id={META_APP_ID}"
            f"&redirect_uri={META_REDIRECT_URI}"
            f"&state={state}"
            f"&scope={scopes_str}"
            f"&response_type=code"
        )
        
        logger.info(f"Generated OAuth URL for tenant {tenant_id}, state: {state[:20]}...")
        
        return {
            "success": True,
            "data": {
                "auth_url": auth_url,
                "state": state,
                "expires_in": 300  # 5 minutes
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating Meta auth URL: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating Meta auth URL: {str(e)}")

@router.get("/callback")
async def meta_auth_callback(
    request: Request,
    code: str = Query(..., description="OAuth authorization code"),
    state: str = Query(..., description="OAuth state parameter"),
    error: Optional[str] = Query(None, description="OAuth error if any"),
    error_reason: Optional[str] = Query(None, description="Error reason"),
    error_description: Optional[str] = Query(None, description="Error description")
) -> Dict[str, Any]:
    """
    Meta OAuth callback handler.
    Exchanges authorization code for access token.
    """
    try:
        # Check for OAuth errors
        if error:
            logger.error(f"Meta OAuth error: {error}, reason: {error_reason}, description: {error_description}")
            return {
                "success": False,
                "error": error,
                "error_reason": error_reason,
                "error_description": error_description,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Validate state parameter
        if state not in oauth_states:
            logger.error(f"Invalid OAuth state: {state}")
            raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
        
        state_data = oauth_states[state]
        tenant_id = state_data["tenant_id"]
        user_id = state_data["user_id"]
        
        # Remove used state
        del oauth_states[state]
        
        logger.info(f"Processing OAuth callback for tenant {tenant_id}, user {user_id}")
        
        # Exchange code for access token
        token_data = await MetaAdsService.exchange_code_for_token(
            tenant_id=tenant_id,
            code=code,
            redirect_uri=META_REDIRECT_URI
        )
        
        # Get long-lived token (60 days)
        long_lived_token = await MetaAdsService.get_long_lived_token(
            tenant_id=tenant_id,
            short_lived_token=token_data.get("access_token")
        )
        
        # Get user's business managers and ad accounts
        business_managers = await MetaAdsService.get_business_managers_with_token(
            tenant_id=tenant_id,
            access_token=long_lived_token.get("access_token")
        )
        
        # Store token in credentials
        await MetaAdsService.store_meta_token(
            tenant_id=tenant_id,
            token_data={
                "access_token": long_lived_token.get("access_token"),
                "token_type": "META_USER_LONG_TOKEN",
                "expires_at": long_lived_token.get("expires_at"),
                "scopes": META_SCOPES,
                "business_managers": business_managers,
                "user_id": user_id,
                "connected_at": datetime.utcnow().isoformat()
            }
        )
        
        # Audit the connection
        logger.info(
            f"[AUDIT] meta_oauth_connected: tenant_id={tenant_id}, "
            f"user_id={user_id}, business_managers={len(business_managers)}"
        )
        
        logger.info(f"Successfully connected Meta account for tenant {tenant_id}")

        # Redirigir al CRM frontend en lugar de retornar JSON crudo
        if FRONTEND_URL:
            return RedirectResponse(url=f"{FRONTEND_URL}/crm/marketing?success=connected", status_code=302)
        
        # Fallback: retornar JSON si no hay PLATFORM_URL configurada
        return {
            "success": True,
            "data": {
                "connected": True,
                "business_managers": business_managers,
                "token_expires_at": long_lived_token.get("expires_at"),
                "message": "Meta account connected successfully"
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Meta OAuth callback: {e}", exc_info=True)
        if FRONTEND_URL:
            return RedirectResponse(url=f"{FRONTEND_URL}/crm/marketing?error=auth_failed", status_code=302)
        raise HTTPException(status_code=500, detail=f"Error in Meta OAuth callback: {str(e)}")

@router.post("/disconnect")
@audit_access("disconnect_meta_account")
@limiter.limit("10/minute")
async def disconnect_meta_account(
    request: Request,
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
) -> Dict[str, Any]:
    """
    Disconnect Meta account from CRM.
    Removes stored tokens and credentials.
    """
    try:
        # Remove Meta token from credentials
        await MetaAdsService.remove_meta_token(tenant_id)
        
        # Audit the disconnection
        logger.info(
            f"[AUDIT] meta_oauth_disconnected: tenant_id={tenant_id}, "
            f"user_id={user_data.user_id}"
        )
        
        logger.info(f"Successfully disconnected Meta account for tenant {tenant_id}")
        
        return {
            "success": True,
            "data": {
                "disconnected": True,
                "message": "Meta account disconnected successfully"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error disconnecting Meta account: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error disconnecting Meta account: {str(e)}")

@router.get("/debug/token")
@audit_access("debug_meta_token")
@limiter.limit("5/minute")
async def debug_meta_token(
    request: Request,
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
) -> Dict[str, Any]:
    """
    Debug endpoint to check Meta token status (development only).
    """
    try:
        from core.credentials import get_tenant_credential
        token = await get_tenant_credential(tenant_id, "META_USER_LONG_TOKEN")
        
        if not token:
            return {
                "success": True,
                "data": {
                    "connected": False,
                    "message": "No Meta token found"
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Try to validate token by making a simple API call
        validation_result = await MetaAdsService.validate_token(tenant_id, token)
        
        return {
            "success": True,
            "data": {
                "connected": True,
                "token_exists": True,
                "validation": validation_result,
                "message": "Meta token is valid"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error debugging Meta token: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/test-connection")
@audit_access("test_meta_connection")
@limiter.limit("5/minute")
async def test_meta_connection(
    request: Request,
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
) -> Dict[str, Any]:
    """
    Test Meta API connection with current token.
    """
    try:
        test_result = await MetaAdsService.test_connection(tenant_id)
        
        return {
            "success": True,
            "data": test_result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error testing Meta connection: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error testing Meta connection: {str(e)}")