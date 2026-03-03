"""
Google OAuth Service for CRM Ventas.
Handles Google OAuth login flow for user authentication.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "YOUR_GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "YOUR_GOOGLE_CLIENT_SECRET")
GOOGLE_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
REQUEST_TIMEOUT = float(os.getenv("GOOGLE_API_TIMEOUT", "10.0"))

# JWT configuration (use existing auth system)
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24


class GoogleOAuthService:
    """
    Service for Google OAuth login operations.
    """

    @staticmethod
    async def exchange_code_for_token(code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchange OAuth authorization code for access token.
        
        Args:
            code: OAuth authorization code
            redirect_uri: Redirect URI used in authorization
            
        Returns:
            Token data including access_token
        """
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
            
            logger.info("✅ Google OAuth: Successfully exchanged code for token")
            return token_data

        except Exception as e:
            logger.error(f"❌ Error exchanging Google OAuth code: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error exchanging Google OAuth code: {str(e)}")

    @staticmethod
    async def get_user_info(access_token: str) -> Dict[str, Any]:
        """
        Get user info from Google using access token.
        
        Args:
            access_token: Google OAuth access token
            
        Returns:
            User info including email, name, picture, google_id
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
                raise HTTPException(status_code=400, detail=f"Google userinfo failed: {error_msg}")

            user_info = response.json()
            
            return {
                "google_id": user_info.get("sub"),  # Unique Google ID
                "email": user_info.get("email"),
                "email_verified": user_info.get("email_verified", False),
                "name": user_info.get("name"),
                "given_name": user_info.get("given_name"),
                "family_name": user_info.get("family_name"),
                "picture": user_info.get("picture"),
                "locale": user_info.get("locale")
            }

        except Exception as e:
            logger.error(f"❌ Error getting Google user info: {e}")
            raise HTTPException(status_code=500, detail=f"Error getting Google user info: {str(e)}")

    @staticmethod
    async def create_or_update_user(user_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create or update user in database based on Google user info.
        
        Args:
            user_info: Google user info
            
        Returns:
            User data including user_id, tenant_id
        """
        from db import get_db_connection
        
        google_id = user_info.get("google_id")
        email = user_info.get("email")
        
        if not google_id or not email:
            raise HTTPException(status_code=400, detail="Invalid Google user info")
        
        try:
            async with get_db_connection() as conn:
                # Check if user exists by google_id
                user = await conn.fetchrow("""
                    SELECT id, email, full_name, role, tenant_id, google_id, google_email
                    FROM users 
                    WHERE google_id = $1 OR email = $2
                    LIMIT 1
                """, google_id, email)
                
                if user:
                    # Update existing user with Google info if needed
                    if not user["google_id"]:
                        await conn.execute("""
                            UPDATE users 
                            SET google_id = $1, google_email = $2, updated_at = NOW()
                            WHERE id = $3
                        """, google_id, email, user["id"])
                    
                    logger.info(f"✅ Google OAuth: Updated existing user {user['id']} with Google info")
                    
                    return {
                        "user_id": user["id"],
                        "email": user["email"],
                        "full_name": user["full_name"],
                        "role": user["role"],
                        "tenant_id": user["tenant_id"],
                        "google_id": google_id,
                        "action": "updated"
                    }
                else:
                    # Create new user
                    # Determine tenant_id (for now, create personal tenant or use default)
                    # In a real implementation, you might create a new tenant or use invitation system
                    
                    # First, check if we should create a new tenant
                    # For simplicity, we'll assign to a default tenant or create one
                    tenant = await conn.fetchrow("""
                        SELECT id FROM tenants WHERE is_default = true LIMIT 1
                    """)
                    
                    if not tenant:
                        # Create a personal tenant for the user
                        tenant_result = await conn.fetchrow("""
                            INSERT INTO tenants (name, is_default, created_at, updated_at)
                            VALUES ($1, false, NOW(), NOW())
                            RETURNING id
                        """, f"Personal - {email}")
                        tenant_id = tenant_result["id"]
                    else:
                        tenant_id = tenant["id"]
                    
                    # Create user
                    user_result = await conn.fetchrow("""
                        INSERT INTO users (
                            email, full_name, role, tenant_id, 
                            google_id, google_email, google_profile_picture,
                            created_at, updated_at
                        )
                        VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
                        RETURNING id, email, full_name, role, tenant_id
                    """, 
                    email,
                    user_info.get("name", email.split('@')[0]),
                    "user",  # Default role
                    tenant_id,
                    google_id,
                    email,
                    user_info.get("picture")
                    )
                    
                    logger.info(f"✅ Google OAuth: Created new user {user_result['id']}")
                    
                    return {
                        "user_id": user_result["id"],
                        "email": user_result["email"],
                        "full_name": user_result["full_name"],
                        "role": user_result["role"],
                        "tenant_id": user_result["tenant_id"],
                        "google_id": google_id,
                        "action": "created"
                    }
                    
        except Exception as e:
            logger.error(f"❌ Error creating/updating user with Google OAuth: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error creating/updating user: {str(e)}")

    @staticmethod
    async def create_jwt_session(user_id: int, tenant_id: Optional[int] = None) -> str:
        """
        Create JWT session token for authenticated user.
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID (optional)
            
        Returns:
            JWT token string
        """
        try:
            import jwt
            from datetime import datetime, timedelta
            
            # Create payload
            payload = {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
                "iat": datetime.utcnow(),
                "iss": "crm-ventas",
                "provider": "google"
            }
            
            # Create JWT token
            token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
            
            logger.info(f"✅ Google OAuth: Created JWT session for user {user_id}")
            return token
            
        except Exception as e:
            logger.error(f"❌ Error creating JWT token: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error creating session token: {str(e)}")

    @staticmethod
    async def validate_google_token(id_token: str) -> Dict[str, Any]:
        """
        Validate Google ID token (for frontend use).
        
        Args:
            id_token: Google ID token from frontend
            
        Returns:
            Validated token data
        """
        try:
            # In production, use Google's token validation endpoint
            # For now, we'll use a simple approach
            validation_url = "https://oauth2.googleapis.com/tokeninfo"
            
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                response = await client.get(validation_url, params={"id_token": id_token})
            
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Invalid Google ID token")
            
            token_info = response.json()
            
            # Verify audience
            if token_info.get("aud") != GOOGLE_CLIENT_ID:
                raise HTTPException(status_code=400, detail="Token audience mismatch")
            
            # Check expiration
            exp = int(token_info.get("exp", 0))
            if datetime.utcnow().timestamp() > exp:
                raise HTTPException(status_code=400, detail="Token expired")
            
            return token_info
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Error validating Google token: {e}")
            raise HTTPException(status_code=500, detail=f"Error validating token: {str(e)}")

    @staticmethod
    async def get_user_by_google_id(google_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user by Google ID.
        
        Args:
            google_id: Google user ID
            
        Returns:
            User data or None
        """
        from db import get_db_connection
        
        try:
            async with get_db_connection() as conn:
                user = await conn.fetchrow("""
                    SELECT id, email, full_name, role, tenant_id, google_id, google_email
                    FROM users 
                    WHERE google_id = $1
                    LIMIT 1
                """, google_id)
                
                if user:
                    return dict(user)
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting user by Google ID: {e}")
            return None

    @staticmethod
    async def link_existing_user_to_google(user_id: int, google_info: Dict[str, Any]) -> bool:
        """
        Link existing user account to Google.
        
        Args:
            user_id: Existing user ID
            google_info: Google user info
            
        Returns:
            True if successful
        """
        from db import get_db_connection
        
        google_id = google_info.get("google_id")
        email = google_info.get("email")
        
        if not google_id:
            return False
        
        try:
            async with get_db_connection() as conn:
                # Check if Google ID is already linked to another user
                existing = await conn.fetchrow("""
                    SELECT id FROM users WHERE google_id = $1 AND id != $2 LIMIT 1
                """, google_id, user_id)
                
                if existing:
                    logger.warning(f"Google ID {google_id} already linked to user {existing['id']}")
                    return False
                
                # Update user with Google info
                await conn.execute("""
                    UPDATE users 
                    SET google_id = $1, google_email = $2, 
                        google_profile_picture = $3, updated_at = NOW()
                    WHERE id = $4
                """, google_id, email, google_info.get("picture"), user_id)
                
                logger.info(f"✅ Linked user {user_id} to Google ID {google_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error linking user to Google: {e}")
            return False

    @staticmethod
    async def unlink_google_from_user(user_id: int) -> bool:
        """
        Unlink Google from user account.
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful
        """
        from db import get_db_connection
        
        try:
            async with get_db_connection() as conn:
                await conn.execute("""
                    UPDATE users 
                    SET google_id = NULL, google_email = NULL, 
                        google_profile_picture = NULL, updated_at = NOW()
                    WHERE id = $1
                """, user_id)
                
                logger.info(f"✅ Unlinked Google from user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error unlinking Google from user: {e}")
            return False