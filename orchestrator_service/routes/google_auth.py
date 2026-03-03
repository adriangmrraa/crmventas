"""
Google OAuth Routes for CRM Ventas
Handles Google OAuth flow for connecting Google Ads accounts and Google Login
"""

import os
import secrets
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from core.security import verify_admin_token, get_resolved_tenant_id, audit_access
from core.rate_limiter import limiter
from services.marketing.google_ads_service import GoogleAdsService
from services.auth.google_oauth_service import GoogleOAuthService

logger = logging.getLogger(__name__)
router = APIRouter()

# OAuth configuration for Google Ads
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "YOUR_GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "YOUR_GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "").rstrip("/")
GOOGLE_LOGIN_REDIRECT_URI = os.getenv("GOOGLE_LOGIN_REDIRECT_URI", "").rstrip("/")

# Scopes for Google Ads
GOOGLE_ADS_SCOPES = [
    "https://www.googleapis.com/auth/adwords",  # Full access to Google Ads
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile"
]

# Scopes for Google Login (basic profile)
GOOGLE_LOGIN_SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid"
]

FRONTEND_URL = os.getenv("PLATFORM_URL", os.getenv("FRONTEND_URL", "")).rstrip("/")

# Store OAuth states (in production, use Redis)
oauth_states = {}

@router.get("/ads/url")
@audit_access("get_google_ads_auth_url")
@limiter.limit("20/minute")
async def get_google_ads_auth_url(
    request: Request,
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
) -> Dict[str, Any]:
    """
    Generate Google OAuth authorization URL for Google Ads.
    Returns URL for user to authorize the app for Google Ads access.
    """
    try:
        # Generate secure state parameter
        state = f"tenant_{tenant_id}_ads_{secrets.token_urlsafe(32)}"
        oauth_states[state] = {
            "tenant_id": tenant_id,
            "user_id": user_data.user_id,
            "type": "ads",  # ads or login
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
        
        # Build OAuth URL for Google Ads
        scopes_str = " ".join(GOOGLE_ADS_SCOPES)
        auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={GOOGLE_CLIENT_ID}"
            f"&redirect_uri={GOOGLE_REDIRECT_URI}"
            f"&response_type=code"
            f"&scope={scopes_str}"
            f"&state={state}"
            f"&access_type=offline"  # IMPORTANT: Get refresh token
            f"&prompt=consent"       # Force consent screen for refresh token
        )
        
        logger.info(f"Generated Google Ads OAuth URL for tenant {tenant_id}, state: {state[:20]}...")
        
        return {
            "success": True,
            "data": {
                "auth_url": auth_url,
                "state": state,
                "expires_in": 300,  # 5 minutes
                "scopes": GOOGLE_ADS_SCOPES
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating Google Ads auth URL: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating Google Ads auth URL: {str(e)}")

@router.get("/ads/callback")
async def google_ads_auth_callback(
    request: Request,
    code: str = Query(..., description="OAuth authorization code"),
    state: str = Query(..., description="OAuth state parameter"),
    error: Optional[str] = Query(None, description="OAuth error if any"),
    error_description: Optional[str] = Query(None, description="Error description")
) -> Dict[str, Any]:
    """
    Google Ads OAuth callback handler.
    Exchanges authorization code for access token and refresh token.
    """
    try:
        # Check for OAuth errors
        if error:
            logger.error(f"Google OAuth error: {error}, description: {error_description}")
            if FRONTEND_URL:
                return RedirectResponse(url=f"{FRONTEND_URL}/crm/marketing?error=google_auth_failed&reason={error}", status_code=302)
            return {
                "success": False,
                "error": error,
                "error_description": error_description,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Validate state parameter
        if state not in oauth_states:
            logger.error(f"Invalid OAuth state: {state}")
            if FRONTEND_URL:
                return RedirectResponse(url=f"{FRONTEND_URL}/crm/marketing?error=invalid_state", status_code=302)
            raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
        
        state_data = oauth_states[state]
        if state_data.get("type") != "ads":
            logger.error(f"Invalid OAuth type for state {state}: expected 'ads', got {state_data.get('type')}")
            if FRONTEND_URL:
                return RedirectResponse(url=f"{FRONTEND_URL}/crm/marketing?error=invalid_oauth_type", status_code=302)
            raise HTTPException(status_code=400, detail="Invalid OAuth type")
        
        tenant_id = state_data["tenant_id"]
        user_id = state_data["user_id"]
        
        # Remove used state
        del oauth_states[state]
        
        logger.info(f"Processing Google Ads OAuth callback for tenant {tenant_id}, user {user_id}")
        
        # Exchange code for tokens (access_token + refresh_token)
        token_data = await GoogleAdsService.exchange_code_for_tokens(
            tenant_id=tenant_id,
            code=code,
            redirect_uri=GOOGLE_REDIRECT_URI
        )
        
        # Get user info to store with tokens
        user_info = await GoogleAdsService.get_user_info(
            tenant_id=tenant_id,
            access_token=token_data.get("access_token")
        )
        
        # Store tokens in credentials
        await GoogleAdsService.store_google_tokens(
            tenant_id=tenant_id,
            token_data={
                "access_token": token_data.get("access_token"),
                "refresh_token": token_data.get("refresh_token"),
                "token_type": "GOOGLE_ADS_TOKEN",
                "expires_at": token_data.get("expires_at"),
                "scopes": GOOGLE_ADS_SCOPES,
                "user_info": user_info,
                "user_id": user_id,
                "connected_at": datetime.utcnow().isoformat()
            }
        )
        
        # Get Google Ads accounts (customer IDs)
        try:
            customer_ids = await GoogleAdsService.get_accessible_customers(
                tenant_id=tenant_id
            )
            logger.info(f"Found {len(customer_ids)} Google Ads accounts for tenant {tenant_id}")
        except Exception as e:
            logger.warning(f"Could not fetch Google Ads accounts, will fetch later: {e}")
            customer_ids = []
        
        # Audit the connection
        logger.info(
            f"[AUDIT] google_ads_oauth_connected: tenant_id={tenant_id}, "
            f"user_id={user_id}, email={user_info.get('email')}, "
            f"accounts={len(customer_ids)}"
        )
        
        logger.info(f"Successfully connected Google Ads account for tenant {tenant_id}")

        # Redirect to CRM frontend
        if FRONTEND_URL:
            return RedirectResponse(url=f"{FRONTEND_URL}/crm/marketing?success=google_connected", status_code=302)
        
        # Fallback: return JSON if no FRONTEND_URL configured
        return {
            "success": True,
            "data": {
                "connected": True,
                "user_info": user_info,
                "customer_ids": customer_ids,
                "token_expires_at": token_data.get("expires_at"),
                "message": "Google Ads account connected successfully"
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Google Ads OAuth callback: {e}", exc_info=True)
        if FRONTEND_URL:
            return RedirectResponse(url=f"{FRONTEND_URL}/crm/marketing?error=google_auth_failed", status_code=302)
        raise HTTPException(status_code=500, detail=f"Error in Google Ads OAuth callback: {str(e)}")

@router.get("/login/url")
async def get_google_login_auth_url(
    request: Request,
    redirect_to: Optional[str] = Query(None, description="URL to redirect after login")
) -> Dict[str, Any]:
    """
    Generate Google OAuth authorization URL for login.
    Returns URL for user to login with Google.
    """
    try:
        # Generate secure state parameter
        state = f"login_{secrets.token_urlsafe(32)}"
        if redirect_to:
            state = f"{state}_redirect_{redirect_to}"
        
        oauth_states[state] = {
            "type": "login",
            "redirect_to": redirect_to,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Build OAuth URL for Google Login
        scopes_str = " ".join(GOOGLE_LOGIN_SCOPES)
        auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={GOOGLE_CLIENT_ID}"
            f"&redirect_uri={GOOGLE_LOGIN_REDIRECT_URI}"
            f"&response_type=code"
            f"&scope={scopes_str}"
            f"&state={state}"
            f"&access_type=online"  # No refresh token needed for login
            f"&prompt=select_account"  # Let user select account
        )
        
        logger.info(f"Generated Google Login OAuth URL, state: {state[:20]}...")
        
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
        logger.error(f"Error generating Google Login auth URL: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating Google Login auth URL: {str(e)}")

@router.get("/login/callback")
async def google_login_auth_callback(
    request: Request,
    code: str = Query(..., description="OAuth authorization code"),
    state: str = Query(..., description="OAuth state parameter"),
    error: Optional[str] = Query(None, description="OAuth error if any"),
    error_description: Optional[str] = Query(None, description="Error description")
) -> Dict[str, Any]:
    """
    Google Login OAuth callback handler.
    Exchanges authorization code for access token and creates/updates user.
    """
    try:
        # Check for OAuth errors
        if error:
            logger.error(f"Google Login OAuth error: {error}, description: {error_description}")
            if FRONTEND_URL:
                return RedirectResponse(url=f"{FRONTEND_URL}/login?error=google_login_failed&reason={error}", status_code=302)
            return {
                "success": False,
                "error": error,
                "error_description": error_description,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Validate state parameter
        if state not in oauth_states:
            logger.error(f"Invalid OAuth state: {state}")
            if FRONTEND_URL:
                return RedirectResponse(url=f"{FRONTEND_URL}/login?error=invalid_state", status_code=302)
            raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
        
        state_data = oauth_states[state]
        if state_data.get("type") != "login":
            logger.error(f"Invalid OAuth type for state {state}: expected 'login', got {state_data.get('type')}")
            if FRONTEND_URL:
                return RedirectResponse(url=f"{FRONTEND_URL}/login?error=invalid_oauth_type", status_code=302)
            raise HTTPException(status_code=400, detail="Invalid OAuth type")
        
        redirect_to = state_data.get("redirect_to")
        
        # Remove used state
        del oauth_states[state]
        
        logger.info(f"Processing Google Login OAuth callback")
        
        # Exchange code for access token
        token_data = await GoogleOAuthService.exchange_code_for_token(
            code=code,
            redirect_uri=GOOGLE_LOGIN_REDIRECT_URI
        )
        
        # Get user info from Google
        user_info = await GoogleOAuthService.get_user_info(
            access_token=token_data.get("access_token")
        )
        
        # Create or update user in database
        user_result = await GoogleOAuthService.create_or_update_user(user_info)
        
        # Create JWT session for the user
        jwt_token = await GoogleOAuthService.create_jwt_session(
            user_id=user_result["user_id"],
            tenant_id=user_result.get("tenant_id")
        )
        
        # Audit the login
        logger.info(
            f"[AUDIT] google_login_successful: user_id={user_result['user_id']}, "
            f"email={user_info.get('email')}, tenant_id={user_result.get('tenant_id')}"
        )
        
        logger.info(f"Successfully logged in user with Google: {user_info.get('email')}")

        # Redirect to frontend with JWT token
        if FRONTEND_URL:
            redirect_url = f"{FRONTEND_URL}/auth/callback?token={jwt_token}&provider=google"
            if redirect_to:
                redirect_url += f"&redirect_to={redirect_to}"
            return RedirectResponse(url=redirect_url, status_code=302)
        
        # Fallback: return JSON if no FRONTEND_URL configured
        return {
            "success": True,
            "data": {
                "user": user_result,
                "jwt_token": jwt_token,
                "message": "Logged in successfully with Google"
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Google Login OAuth callback: {e}", exc_info=True)
        if FRONTEND_URL:
            return RedirectResponse(url=f"{FRONTEND_URL}/login?error=google_login_failed", status_code=302)
        raise HTTPException(status_code=500, detail=f"Error in Google Login OAuth callback: {str(e)}")

@router.post("/ads/disconnect")
@audit_access("disconnect_google_ads_account")
@limiter.limit("10/minute")
async def disconnect_google_ads_account(
    request: Request,
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
) -> Dict[str, Any]:
    """
    Disconnect Google Ads account from CRM.
    Removes stored tokens and credentials.
    """
    try:
        # Remove Google tokens from credentials
        await GoogleAdsService.remove_google_tokens(tenant_id)
        
        # Audit the disconnection
        logger.info(
            f"[AUDIT] google_ads_disconnected: tenant_id={tenant_id}, "
            f"user_id={user_data.user_id}"
        )
        
        logger.info(f"Successfully disconnected Google Ads account for tenant {tenant_id}")
        
        return {
            "success": True,
            "data": {
                "disconnected": True,
                "message": "Google Ads account disconnected successfully"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error disconnecting Google Ads account: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error disconnecting Google Ads account: {str(e)}")

@router.get("/ads/refresh")
@audit_access("refresh_google_ads_token")
@limiter.limit("5/minute")
async def refresh_google_ads_token(
    request: Request,
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
) -> Dict[str, Any]:
    """
    Manually refresh Google Ads access token using refresh token.
    Usually handled automatically by the service.
    """
    try:
        refreshed = await GoogleAdsService.refresh_access_token(tenant_id)
        
        if refreshed:
            return {
                "success": True,
                "data": {
                    "refreshed": True,
                    "message": "Google Ads token refreshed successfully"
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "success": False,
                "error": "No refresh token available or refresh failed",
                "timestamp": datetime.utcnow().isoformat()
            }
        
    except Exception as e:
        logger.error(f"Error refreshing Google Ads token: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error refreshing Google Ads token: {str(e)}")

@router.get("/ads/debug/token")
@audit_access("debug_google_ads_token")
@limiter.limit("5/minute")
async def debug_google_ads_token(
    request: Request,
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
) -> Dict[str, Any]:
    """
    Debug endpoint to check Google Ads token status (development only).
    """
    try:
        from core.credentials import get_tenant_credential
        token_data = await get_tenant_credential(tenant_id, "GOOGLE_ADS_TOKEN")
        
        if not token_data:
            return {
                "success": True,
                "data": {
                    "connected": False,
                    "message": "No Google Ads token found"
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Parse token data
        import json
        token_info = json.loads(token_data) if isinstance(token_data, str) else token_data
        
        # Check if token is expired
        expires_at = token_info.get("expires_at")
        is_expired = False
        if expires_at:
            expires_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            is_expired = datetime.utcnow() > expires_dt
        
        return {
            "success": True,
            "data": {
                "connected": True,
                "token_exists": True,
                "is_expired": is_expired,
                "expires_at": expires_at,
                "has_refresh_token": "refresh_token" in token_info,
                "user_email": token_info.get("user_info", {}).get("email"),
                "message": "Google Ads token found"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error debugging Google Ads token: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/ads/test-connection")
@audit_access("test_google_ads_connection")
@limiter.limit("5/minute")
async def test_google_ads_connection(
    request: Request,
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
) -> Dict[str, Any]:
    """
    Test Google Ads API connection with current token.
    """
    try:
        test_result = await GoogleAdsService.test_connection(tenant_id)
        
        return {
            "success": True,
            "data": test_result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error testing Google Ads connection: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error testing Google Ads connection: {str(e)}")

@router.get("/login/debug")
async def debug_google_login(
    request: Request
) -> Dict[str, Any]:
    """
    Debug endpoint for Google Login (development only).
    """
    try:
        return {
            "success": True,
            "data": {
                "client_id": GOOGLE_CLIENT_ID[:10] + "..." if GOOGLE_CLIENT_ID else "Not set",
                "login_redirect_uri": GOOGLE_LOGIN_REDIRECT_URI,
                "ads_redirect_uri": GOOGLE_REDIRECT_URI,
                "frontend_url": FRONTEND_URL,
                "active_states": len(oauth_states),
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error in Google login debug: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }