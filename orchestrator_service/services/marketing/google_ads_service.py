"""
Google Ads API Client for CRM Ventas.
Handles Google Ads API integration for fetching campaigns, metrics, and managing OAuth tokens.

Based on Meta Ads Service structure for consistency.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Google Ads API configuration
GOOGLE_ADS_API_VERSION = os.getenv("GOOGLE_ADS_API_VERSION", "v16")
GOOGLE_ADS_API_BASE = f"https://googleads.googleapis.com/{GOOGLE_ADS_API_VERSION}"
GOOGLE_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
REQUEST_TIMEOUT = float(os.getenv("GOOGLE_API_TIMEOUT", "10.0"))

# Developer token (required for Google Ads API)
GOOGLE_DEVELOPER_TOKEN = os.getenv("GOOGLE_DEVELOPER_TOKEN", "")

class GoogleAdsAuthError(Exception):
    """Google OAuth token invalid or expired (HTTP 401)."""
    pass

class GoogleAdsRateLimitError(Exception):
    """Rate limit reached in Google Ads API (HTTP 429)."""
    pass

class GoogleAdsNotFoundError(Exception):
    """Resource not found or no permissions (HTTP 404)."""
    pass

class GoogleAdsClient:
    """
    Async client for Google Ads API.
    Stateless design - instantiate per call or as singleton.
    """

    def __init__(self, access_token: Optional[str] = None, developer_token: Optional[str] = None):
        self.access_token = (access_token or "").strip()
        self.developer_token = (developer_token or GOOGLE_DEVELOPER_TOKEN).strip()
        
        if not self.access_token:
            logger.warning("⚠️ Google Ads access token not configured. API calls will fail.")
        if not self.developer_token:
            logger.warning("⚠️ GOOGLE_DEVELOPER_TOKEN not configured. Google Ads API calls will fail.")

    async def get_campaigns(self, customer_id: str) -> List[Dict[str, Any]]:
        """
        Get campaigns for a Google Ads customer account.
        
        Args:
            customer_id: Google Ads customer ID (e.g., '1234567890')
            
        Returns:
            List of campaigns with details
        """
        if not self.access_token:
            raise GoogleAdsAuthError("Google Ads access token not configured.")
        if not self.developer_token:
            raise GoogleAdsAuthError("GOOGLE_DEVELOPER_TOKEN not configured.")
        if not customer_id:
            raise ValueError("customer_id is required")

        # GAQL query to get campaigns
        query = """
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type,
                campaign.start_date,
                campaign.end_date,
                campaign.budget_amount_micros,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions
            FROM campaign
            WHERE campaign.status != 'REMOVED'
            ORDER BY campaign.id
            LIMIT 1000
        """

        url = f"{GOOGLE_ADS_API_BASE}/customers/{customer_id}/googleAds:search"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "developer-token": self.developer_token,
            "Content-Type": "application/json",
            "login-customer-id": customer_id
        }
        
        data = {
            "query": query.strip()
        }

        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                response = await client.post(url, headers=headers, json=data)

            if response.status_code == 401:
                logger.error("🔒 Google Ads API: Invalid or expired token (401).")
                raise GoogleAdsAuthError("Google Ads token invalid or expired.")

            if response.status_code == 429:
                logger.warning("🚦 Google Ads API: Rate limit reached (429).")
                raise GoogleAdsRateLimitError("Rate limit reached in Google Ads API.")

            if response.status_code == 404:
                logger.info(f"🔍 Google Ads API: Customer {customer_id} not found (404).")
                raise GoogleAdsNotFoundError(f"Customer {customer_id} not found or no access.")

            if response.status_code != 200:
                error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                error_msg = error_data.get("error", {}).get("message", response.text[:200])
                logger.error(f"❌ Google Ads API error ({response.status_code}): {error_msg}")
                raise Exception(f"Google Ads API error {response.status_code}: {error_msg}")

            data = response.json()
            results = data.get("results", [])
            
            campaigns = []
            for result in results:
                campaign = result.get("campaign", {})
                metrics = result.get("metrics", {})
                
                campaigns.append({
                    "id": campaign.get("id"),
                    "name": campaign.get("name"),
                    "status": campaign.get("status"),
                    "channel_type": campaign.get("advertisingChannelType"),
                    "start_date": campaign.get("startDate"),
                    "end_date": campaign.get("endDate"),
                    "budget_micros": campaign.get("budgetAmountMicros"),
                    "budget": float(campaign.get("budgetAmountMicros", 0)) / 1000000 if campaign.get("budgetAmountMicros") else 0,
                    "impressions": metrics.get("impressions", 0),
                    "clicks": metrics.get("clicks", 0),
                    "cost_micros": metrics.get("costMicros", 0),
                    "cost": float(metrics.get("costMicros", 0)) / 1000000 if metrics.get("costMicros") else 0,
                    "conversions": metrics.get("conversions", 0)
                })
            
            logger.info(f"✅ Google Ads: Retrieved {len(campaigns)} campaigns for customer {customer_id}")
            return campaigns

        except httpx.TimeoutException:
            logger.error(f"⏰ Google Ads API timeout ({REQUEST_TIMEOUT}s) for customer {customer_id}")
            raise
        except (GoogleAdsAuthError, GoogleAdsRateLimitError, GoogleAdsNotFoundError):
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error querying Google Ads API: {e}")
            raise

    async def get_metrics(self, customer_id: str, date_range: str = "LAST_30_DAYS") -> Dict[str, Any]:
        """
        Get overall metrics for a Google Ads customer account.
        
        Args:
            customer_id: Google Ads customer ID
            date_range: Date range preset (LAST_7_DAYS, LAST_30_DAYS, THIS_MONTH, etc.)
            
        Returns:
            Dictionary with overall metrics
        """
        if not self.access_token:
            raise GoogleAdsAuthError("Google Ads access token not configured.")
        if not self.developer_token:
            raise GoogleAdsAuthError("GOOGLE_DEVELOPER_TOKEN not configured.")

        query = f"""
            SELECT
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value,
                metrics.average_cpc,
                metrics.ctr,
                metrics.all_conversions,
                metrics.all_conversions_value
            FROM customer
            WHERE segments.date DURING {date_range}
        """

        url = f"{GOOGLE_ADS_API_BASE}/customers/{customer_id}/googleAds:search"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "developer-token": self.developer_token,
            "Content-Type": "application/json",
            "login-customer-id": customer_id
        }
        
        data = {
            "query": query.strip()
        }

        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                response = await client.post(url, headers=headers, json=data)

            if response.status_code != 200:
                error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                error_msg = error_data.get("error", {}).get("message", response.text[:200])
                logger.error(f"❌ Google Ads API metrics error ({response.status_code}): {error_msg}")
                # Return empty metrics instead of raising for better UX
                return self._get_empty_metrics()

            data = response.json()
            results = data.get("results", [])
            
            if not results:
                return self._get_empty_metrics()
            
            metrics = results[0].get("metrics", {})
            
            return {
                "impressions": metrics.get("impressions", 0),
                "clicks": metrics.get("clicks", 0),
                "cost_micros": metrics.get("costMicros", 0),
                "cost": float(metrics.get("costMicros", 0)) / 1000000 if metrics.get("costMicros") else 0,
                "conversions": metrics.get("conversions", 0),
                "conversions_value": metrics.get("conversionsValue", 0),
                "average_cpc": float(metrics.get("averageCpc", 0)) / 1000000 if metrics.get("averageCpc") else 0,
                "ctr": metrics.get("ctr", 0),
                "all_conversions": metrics.get("allConversions", 0),
                "all_conversions_value": metrics.get("allConversionsValue", 0),
                "date_range": date_range,
                "customer_id": customer_id
            }

        except Exception as e:
            logger.error(f"❌ Error getting Google Ads metrics: {e}")
            return self._get_empty_metrics()

    def _get_empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics structure for error handling."""
        return {
            "impressions": 0,
            "clicks": 0,
            "cost_micros": 0,
            "cost": 0,
            "conversions": 0,
            "conversions_value": 0,
            "average_cpc": 0,
            "ctr": 0,
            "all_conversions": 0,
            "all_conversions_value": 0,
            "date_range": "LAST_30_DAYS",
            "customer_id": None
        }

    async def get_accessible_customers(self) -> List[str]:
        """
        Get list of Google Ads customer IDs accessible with current token.
        
        Returns:
            List of customer IDs
        """
        if not self.access_token:
            raise GoogleAdsAuthError("Google Ads access token not configured.")
        if not self.developer_token:
            raise GoogleAdsAuthError("GOOGLE_DEVELOPER_TOKEN not configured.")

        url = f"{GOOGLE_ADS_API_BASE}/customers:listAccessibleCustomers"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "developer-token": self.developer_token,
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                response = await client.get(url, headers=headers)

            if response.status_code != 200:
                error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                error_msg = error_data.get("error", {}).get("message", response.text[:200])
                logger.error(f"❌ Google Ads accessible customers error ({response.status_code}): {error_msg}")
                return []

            data = response.json()
            resource_names = data.get("resourceNames", [])
            
            # Extract customer IDs from resource names (customers/1234567890)
            customer_ids = []
            for resource in resource_names:
                if resource.startswith("customers/"):
                    customer_id = resource.replace("customers/", "")
                    customer_ids.append(customer_id)
            
            logger.info(f"✅ Google Ads: Found {len(customer_ids)} accessible customers")
            return customer_ids

        except Exception as e:
            logger.error(f"❌ Error getting accessible customers: {e}")
            return []


class GoogleAdsService:
    """
    Service layer for Google Ads operations.
    Handles OAuth token management, database operations, and business logic.
    """

    @staticmethod
    async def exchange_code_for_tokens(tenant_id: int, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchange OAuth authorization code for access and refresh tokens.
        
        Args:
            tenant_id: Tenant ID
            code: OAuth authorization code
            redirect_uri: Redirect URI used in authorization
            
        Returns:
            Token data including access_token, refresh_token, expires_in
        """
        from core.credentials import set_tenant_credential
        
        GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
        GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
        
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            raise HTTPException(status_code=500, detail="Google OAuth not configured properly")

        data = {
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }

        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                response = await client.post(GOOGLE_OAUTH_TOKEN_URL, data=data)

            if response.status_code != 200:
                error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                error_msg = error_data.get("error_description", error_data.get("error", response.text[:200]))
                logger.error(f"❌ Google OAuth token exchange failed: {error_msg}")
                raise HTTPException(status_code=400, detail=f"Google OAuth token exchange failed: {error_msg}")

            token_data = response.json()
            
            # Calculate expiration time
            expires_in = token_data.get("expires_in", 3600)  # Default 1 hour
            expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()
            
            token_data["expires_at"] = expires_at
            
            logger.info(f"✅ Google OAuth: Successfully exchanged code for tokens for tenant {tenant_id}")
            return token_data

        except Exception as e:
            logger.error(f"❌ Error exchanging Google OAuth code: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error exchanging Google OAuth code: {str(e)}")

    @staticmethod
    async def refresh_access_token(tenant_id: int) -> bool:
        """
        Refresh Google Ads access token using stored refresh token.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            True if refresh successful, False otherwise
        """
        from core.credentials import get_tenant_credential, set_tenant_credential
        
        GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
        GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
        
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            logger.error("Google OAuth not configured properly")
            return False

        # Get stored token data
        token_json = await get_tenant_credential(tenant_id, "GOOGLE_ADS_TOKEN")
        if not token_json:
            logger.error(f"No Google Ads token found for tenant {tenant_id}")
            return False
        
        try:
            token_data = json.loads(token_json) if isinstance(token_json, str) else token_json
            refresh_token = token_data.get("refresh_token")
            
            if not refresh_token:
                logger.error(f"No refresh token found for tenant {tenant_id}")
                return False

            data = {
                "refresh_token": refresh_token,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "grant_type": "refresh_token"
            }

            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                response = await client.post(GOOGLE_OAUTH_TOKEN_URL, data=data)

            if response.status_code != 200:
                error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                error_msg = error_data.get("error_description", error_data.get("error", response.text[:200]))
                logger.error(f"❌ Google OAuth token refresh failed: {error_msg}")
                return False

            new_token_data = response.json()
            
            # Update token data with new access token
            expires_in = new_token_data.get("expires_in", 3600)
            expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()
            
            token_data.update({
                "access_token": new_token_data.get("access_token"),
                "expires_at": expires_at,
                "refreshed_at": datetime.utcnow().isoformat()
            })
            
            # Keep the original refresh_token (Google doesn't return a new one on refresh)
            if "refresh_token" not in new_token_data:
                token_data["refresh_token"] = refresh_token
            
            # Save updated token
            await set_tenant_credential(
                tenant_id=tenant_id,
                name="GOOGLE_ADS_TOKEN",
                value=json.dumps(token_data),
                category="google_oauth"
            )
            
            logger.info(f"✅ Google OAuth: Successfully refreshed token for tenant {tenant_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Error refreshing Google OAuth token: {e}", exc_info=True)
            return False

    @staticmethod
    async def get_user_info(tenant_id: int, access_token: str) -> Dict[str, Any]:
        """
        Get user info from Google using access token.
        
        Args:
            tenant_id: Tenant ID
            access_token: Google OAuth access token
            
        Returns:
            User info including email, name, picture
        """
        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                response = await client.get(GOOGLE_USERINFO_URL, headers=headers)

            if response.status_code != 200:
                error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                error_msg = error_data.get("error_description", error_data.get("error", response.text[:200]))
                logger.error(f"❌ Google userinfo failed: {error_msg}")
                return {
                    "email": "unknown@example.com",
                    "name": "Google User",
                    "picture": None
                }

            user_info = response.json()
            
            return {
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "given_name": user_info.get("given_name"),
                "family_name": user_info.get("family_name"),
                "picture": user_info.get("picture"),
                "locale": user_info.get("locale"),
                "verified_email": user_info.get("email_verified", False)
            }

        except Exception as e:
            logger.error(f"❌ Error getting Google user info: {e}")
            return {
                "email": "error@example.com",
                "name": "Error fetching user info",
                "picture": None
            }

    @staticmethod
    async def store_google_tokens(tenant_id: int, token_data: Dict[str, Any]) -> bool:
        """
        Store Google OAuth tokens in database.
        
        Args:
            tenant_id: Tenant ID
            token_data: Token data including access_token, refresh_token, etc.
            
        Returns:
            True if successful
        """
        from core.credentials import set_tenant_credential
        
        try:
            # Encrypt sensitive data before storing
            import json
            token_json = json.dumps(token_data)
            
            await set_tenant_credential(
                tenant_id=tenant_id,
                name="GOOGLE_ADS_TOKEN",
                value=token_json,
                category="google_oauth"
            )
            
            logger.info(f"✅ Google OAuth: Stored tokens for tenant {tenant_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error storing Google tokens: {e}", exc_info=True)
            return False

    @staticmethod
    async def remove_google_tokens(tenant_id: int) -> bool:
        """
        Remove Google OAuth tokens from database.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            True if successful
        """
        from core.credentials import delete_tenant_credential
        
        try:
            await delete_tenant_credential(tenant_id, "GOOGLE_ADS_TOKEN")
            logger.info(f"✅ Google OAuth: Removed tokens for tenant {tenant_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error removing Google tokens: {e}", exc_info=True)
            return False

    @staticmethod
    async def get_accessible_customers(tenant_id: int) -> List[str]:
        """
        Get accessible Google Ads customer IDs for a tenant.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            List of customer IDs
        """
        from core.credentials import get_tenant_credential
        
        try:
            # Get stored token
            token_json = await get_tenant_credential(tenant_id, "GOOGLE_ADS_TOKEN")
            if not token_json:
                logger.warning(f"No Google Ads token found for tenant {tenant_id}")
                return []
            
            token_data = json.loads(token_json) if isinstance(token_json, str) else token_json
            access_token = token_data.get("access_token")
            
            if not access_token:
                logger.warning(f"No access token found for tenant {tenant_id}")
                return []
            
            # Create client and get accessible customers
            client = GoogleAdsClient(access_token=access_token)
            customer_ids = await client.get_accessible_customers()
            
            return customer_ids
            
        except Exception as e:
            logger.error(f"❌ Error getting accessible customers for tenant {tenant_id}: {e}")
            return []

    @staticmethod
    async def get_campaigns(tenant_id: int, customer_id: str) -> List[Dict[str, Any]]:
        """
        Get campaigns for a Google Ads customer.
        
        Args:
            tenant_id: Tenant ID
            customer_id: Google Ads customer ID
            
        Returns:
            List of campaigns
        """
        from core.credentials import get_tenant_credential
        
        try:
            # Get stored token
            token_json = await get_tenant_credential(tenant_id, "GOOGLE_ADS_TOKEN")
            if not token_json:
                raise HTTPException(status_code=400, detail="Google Ads not connected")
            
            token_data = json.loads(token_json) if isinstance(token_json, str) else token_json
            access_token = token_data.get("access_token")
            
            if not access_token:
                raise HTTPException(status_code=400, detail="Google Ads token invalid")
            
            # Check if token needs refresh
            expires_at = token_data.get("expires_at")
            if expires_at:
                expires_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                if datetime.utcnow() > expires_dt - timedelta(minutes=5):  # Refresh 5 minutes before expiry
                    logger.info(f"Token for tenant {tenant_id} needs refresh, refreshing...")
                    await GoogleAdsService.refresh_access_token(tenant_id)
                    # Get refreshed token
                    token_json = await get_tenant_credential(tenant_id, "GOOGLE_ADS_TOKEN")
                    token_data = json.loads(token_json) if isinstance(token_json, str) else token_json
                    access_token = token_data.get("access_token")
            
            # Create client and get campaigns
            client = GoogleAdsClient(access_token=access_token)
            campaigns = await client.get_campaigns(customer_id)
            
            return campaigns
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Error getting campaigns for tenant {tenant_id}, customer {customer_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Error getting Google Ads campaigns: {str(e)}")

    @staticmethod
    async def get_metrics(tenant_id: int, customer_id: str, date_range: str = "LAST_30_DAYS") -> Dict[str, Any]:
        """
        Get metrics for a Google Ads customer.
        
        Args:
            tenant_id: Tenant ID
            customer_id: Google Ads customer ID
            date_range: Date range preset
            
        Returns:
            Metrics dictionary
        """
        from core.credentials import get_tenant_credential
        
        try:
            # Get stored token
            token_json = await get_tenant_credential(tenant_id, "GOOGLE_ADS_TOKEN")
            if not token_json:
                raise HTTPException(status_code=400, detail="Google Ads not connected")
            
            token_data = json.loads(token_json) if isinstance(token_json, str) else token_json
            access_token = token_data.get("access_token")
            
            if not access_token:
                raise HTTPException(status_code=400, detail="Google Ads token invalid")
            
            # Check if token needs refresh
            expires_at = token_data.get("expires_at")
            if expires_at:
                expires_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                if datetime.utcnow() > expires_dt - timedelta(minutes=5):
                    await GoogleAdsService.refresh_access_token(tenant_id)
                    token_json = await get_tenant_credential(tenant_id, "GOOGLE_ADS_TOKEN")
                    token_data = json.loads(token_json) if isinstance(token_json, str) else token_json
                    access_token = token_data.get("access_token")
            
            # Create client and get metrics
            client = GoogleAdsClient(access_token=access_token)
            metrics = await client.get_metrics(customer_id, date_range)
            
            return metrics
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Error getting metrics for tenant {tenant_id}, customer {customer_id}: {e}")
            # Return empty metrics instead of raising for better UX
            client = GoogleAdsClient()
            return client._get_empty_metrics()

    @staticmethod
    async def test_connection(tenant_id: int) -> Dict[str, Any]:
        """
        Test Google Ads API connection.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            Test result
        """
        try:
            # Get accessible customers as connection test
            customer_ids = await GoogleAdsService.get_accessible_customers(tenant_id)
            
            if not customer_ids:
                return {
                    "connected": False,
                    "message": "No Google Ads accounts found",
                    "customer_ids": []
                }
            
            # Try to get metrics for first customer as deeper test
            first_customer = customer_ids[0]
            metrics = await GoogleAdsService.get_metrics(tenant_id, first_customer, "LAST_7_DAYS")
            
            return {
                "connected": True,
                "message": "Google Ads connection successful",
                "customer_ids": customer_ids,
                "test_customer": first_customer,
                "test_metrics": metrics
            }
            
        except Exception as e:
            logger.error(f"❌ Google Ads connection test failed for tenant {tenant_id}: {e}")
            return {
                "connected": False,
                "message": f"Connection test failed: {str(e)}",
                "customer_ids": []
            }

    @staticmethod
    async def sync_google_ads_data(tenant_id: int) -> Dict[str, Any]:
        """
        Sync Google Ads data for a tenant (background job).
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            Sync result
        """
        try:
            customer_ids = await GoogleAdsService.get_accessible_customers(tenant_id)
            
            if not customer_ids:
                return {
                    "success": False,
                    "message": "No Google Ads accounts found",
                    "synced_customers": 0,
                    "total_campaigns": 0
                }
            
            total_campaigns = 0
            sync_results = []
            
            for customer_id in customer_ids[:5]:  # Limit to 5 customers per sync
                try:
                    campaigns = await GoogleAdsService.get_campaigns(tenant_id, customer_id)
                    metrics = await GoogleAdsService.get_metrics(tenant_id, customer_id)
                    
                    # TODO: Store campaigns and metrics in database
                    # This would be implemented based on your data model
                    
                    sync_results.append({
                        "customer_id": customer_id,
                        "campaigns_count": len(campaigns),
                        "metrics": metrics
                    })
                    
                    total_campaigns += len(campaigns)
                    
                    logger.info(f"✅ Synced Google Ads data for tenant {tenant_id}, customer {customer_id}: {len(campaigns)} campaigns")
                    
                except Exception as e:
                    logger.error(f"❌ Error syncing customer {customer_id} for tenant {tenant_id}: {e}")
                    sync_results.append({
                        "customer_id": customer_id,
                        "error": str(e)
                    })
            
            return {
                "success": True,
                "message": f"Synced {len(sync_results)} Google Ads accounts",
                "synced_customers": len([r for r in sync_results if "error" not in r]),
                "total_campaigns": total_campaigns,
                "results": sync_results
            }
            
        except Exception as e:
            logger.error(f"❌ Error syncing Google Ads data for tenant {tenant_id}: {e}")
            return {
                "success": False,
                "message": f"Sync failed: {str(e)}",
                "synced_customers": 0,
                "total_campaigns": 0
            }