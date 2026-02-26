"""
Meta Ads Graph API Client.
Spec 04: Consulta la Graph API de Meta para enriquecer IDs opacos
(ad_id, campaign_id) con nombres legibles por humanos.

CRMV1.0 - Integración Meta Ads & CRM Ventas.
"""
import os
import logging
import json
from typing import Optional, Dict, Any, List

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = os.getenv("META_GRAPH_API_VERSION", "v21.0")
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"
REQUEST_TIMEOUT = float(os.getenv("META_API_TIMEOUT", "5.0"))


class MetaAuthError(Exception):
    """Token de Meta inválido o expirado (HTTP 401)."""
    pass


class MetaRateLimitError(Exception):
    """Rate limit alcanzado en la Graph API (HTTP 429)."""
    pass


class MetaNotFoundError(Exception):
    """Recurso no encontrado o sin permisos (HTTP 404)."""
    pass


class MetaAdsClient:
    """
    Cliente asíncrono para la Graph API de Meta.
    Diseñado para ser stateless; se instancia por llamada o como singleton.
    """

    def __init__(self, access_token: Optional[str] = None):
        self.access_token = (access_token or "").strip() or os.getenv("META_ADS_TOKEN", "")
        if not self.access_token:
            logger.warning("⚠️ META_ADS_TOKEN no configurado. El enriquecimiento de anuncios estará deshabilitado.")

    async def get_ad_details(self, ad_id: str) -> Dict[str, Any]:
        """
        Obtiene detalles de un anuncio desde la Graph API.

        Args:
            ad_id: ID del anuncio de Meta (ej. '123456789').

        Returns:
            Dict con claves: ad_id, ad_name, campaign_name, adset_name.

        Raises:
            MetaAuthError: Token inválido/expirado.
            MetaRateLimitError: Rate limit alcanzado.
            MetaNotFoundError: Anuncio no encontrado.
        """
        if not self.access_token:
            raise MetaAuthError("META_ADS_TOKEN no configurado.")

        if not ad_id or not str(ad_id).strip():
            raise ValueError("ad_id no puede estar vacío.")

        url = f"{GRAPH_API_BASE}/{ad_id}"
        params = {
            "fields": "name,campaign{name},adset{name}",
            "access_token": self.access_token,
        }

        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                response = await client.get(url, params=params)

            if response.status_code == 401:
                logger.error("🔒 Meta Graph API: Token inválido o expirado (401).")
                raise MetaAuthError("Token de Meta inválido o expirado.")

            if response.status_code == 429:
                logger.warning("🚦 Meta Graph API: Rate limit alcanzado (429).")
                raise MetaRateLimitError("Rate limit alcanzado en Meta Graph API.")

            if response.status_code == 404:
                logger.info(f"🔍 Meta Graph API: Anuncio {ad_id} no encontrado (404).")
                raise MetaNotFoundError(f"Anuncio {ad_id} no encontrado.")

            if response.status_code != 200:
                # Error genérico de la API
                error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                error_msg = error_data.get("error", {}).get("message", response.text[:200])
                logger.error(f"❌ Meta Graph API error ({response.status_code}): {error_msg}")
                raise Exception(f"Meta Graph API error {response.status_code}: {error_msg}")

            data = response.json()

            # Parsear respuesta según esquema esperado
            result = {
                "ad_id": ad_id,
                "ad_name": data.get("name"),
                "campaign_name": None,
                "adset_name": None,
            }

            campaign = data.get("campaign")
            if isinstance(campaign, dict):
                result["campaign_name"] = campaign.get("name")

            adset = data.get("adset")
            if isinstance(adset, dict):
                result["adset_name"] = adset.get("name")

            logger.info(f"✅ Meta Ads enriquecido: ad_id={ad_id}, ad_name={result['ad_name']}, campaign={result['campaign_name']}")
            return result

        except (MetaAuthError, MetaRateLimitError, MetaNotFoundError):
            raise  # Re-raise excepciones tipadas
        except httpx.TimeoutException:
            logger.error(f"⏰ Meta Graph API timeout ({REQUEST_TIMEOUT}s) para ad_id={ad_id}")
            raise
        except Exception as e:
            logger.error(f"❌ Error inesperado consultando Meta Graph API: {e}")
            raise

    async def get_ads_insights(self, ad_account_id: str, date_preset: str = "maximum", level: str = "ad", filtering: Optional[list] = None) -> list:
        """
        Obtiene métricas de rendimiento (gasto, leads, etc.) a nivel de anuncio (default)
        o cuenta/campaña si se especifica 'level'.
        """
        if not self.access_token:
            raise MetaAuthError("META_ADS_TOKEN no configurado.")
        
        if not ad_account_id:
            raise ValueError("ad_account_id es requerido para consultar insights.")

        # Asegurar prefijo 'act_' si no viene
        account_id = ad_account_id if ad_account_id.startswith("act_") else f"act_{ad_account_id}"
        
        if level == "account":
            fields = "spend,impressions,clicks,account_currency,account_id,account_name"
            # Nivel cuenta no soporta status filtering
        elif level == "campaign":
            fields = "campaign_id,campaign_name,spend,impressions,clicks,account_currency,effective_status"
            # Incluir campañas borradas/archivadas/pausadas
            if filtering is None:
                 filtering = [{'field': 'campaign.effective_status', 'operator': 'IN', 'value': [
                     'ACTIVE', 'PAUSED', 'DELETED', 'ARCHIVED', 'IN_PROCESS', 'WITH_ISSUES', 
                     'CAMPAIGN_PAUSED', 'ADSET_PAUSED'
                 ]}]
        else:
            fields = "ad_id,ad_name,campaign_id,campaign_name,spend,impressions,clicks,account_currency,effective_status"
            if filtering is None:
                filtering = [{'field': 'ad.effective_status', 'operator': 'IN', 'value': [
                    'ACTIVE', 'PAUSED', 'DELETED', 'ARCHIVED', 'IN_PROCESS', 'WITH_ISSUES', 
                    'CAMPAIGN_PAUSED', 'ADSET_PAUSED'
                ]}]

        url = f"{GRAPH_API_BASE}/{account_id}/insights"
        params = {
            "fields": fields,
            "date_preset": date_preset,
            "level": level,
            "access_token": self.access_token,
            "limit": 1000 # Aumentar límite para traer todo el historial
        }
        
        if filtering:
            params["filtering"] = json.dumps(filtering)
            
        logger.info(f"🔍 Meta Request: {url} | Level={level} | Preset={date_preset} | Filter={params.get('filtering')}")

        try:
            all_insights = []
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT * 2) as client:
                current_url = url
                while current_url:
                    response = await client.get(current_url, params=params if current_url == url else None)
                    
                    if response.status_code != 200:
                        error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {"error": {"message": response.text}}
                        error_msg = error_data.get("error", {}).get("message", "Unknown error")
                        error_code = error_data.get("error", {}).get("code", "N/A")
                        error_subcode = error_data.get("error", {}).get("error_subcode", "N/A")
                        
                        logger.error(f"❌ Meta API Error fetching insights for {account_id}: Code={error_code}, Subcode={error_subcode}, Msg='{error_msg}'")
                        return []

                    data = response.json()
                    all_insights.extend(data.get("data", []))
                    
                    # Pagination
                    paging = data.get("paging", {})
                    current_url = paging.get("next")
                    
                return all_insights
        except Exception as e:
            logger.error(f"❌ Error obteniendo insights de Meta para {account_id}: {e}")
            return []

    async def get_portfolios(self) -> list:
        """
        Lista los Business Managers (Portafolios) a los que el usuario tiene acceso.
        """
        url = f"{GRAPH_API_BASE}/me/businesses"
        params = {
            "fields": "name,id",
            "access_token": self.access_token,
        }
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json().get("data", [])
        except Exception as e:
            logger.error(f"❌ Error obteniendo portafolios de Meta: {e}")
            return []

    async def get_ad_accounts(self, portfolio_id: Optional[str] = None) -> list:
        """
        Lista las cuentas de anuncios. Si se provee portfolio_id, intenta obtener 
        tanto client_ad_accounts como owned_ad_accounts.
        """
        params = {
            "fields": "name,id,currency",
            "access_token": self.access_token,
        }
        all_accounts = []
        
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                if portfolio_id:
                    # 1. Intentar client_ad_accounts
                    url_client = f"{GRAPH_API_BASE}/{portfolio_id}/client_ad_accounts"
                    resp_client = await client.get(url_client, params=params)
                    if resp_client.status_code == 200:
                        all_accounts.extend(resp_client.json().get("data", []))
                    
                    # 2. Intentar owned_ad_accounts
                    url_owned = f"{GRAPH_API_BASE}/{portfolio_id}/owned_ad_accounts"
                    resp_owned = await client.get(url_owned, params=params)
                    if resp_owned.status_code == 200:
                        owned_data = resp_owned.json().get("data", [])
                        # Evitar duplicados por ID
                        existing_ids = {acc['id'] for acc in all_accounts}
                        all_accounts.extend([acc for acc in owned_data if acc['id'] not in existing_ids])
                else:
                    # Listado general de cuentas del usuario
                    url = f"{GRAPH_API_BASE}/me/adaccounts"
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    all_accounts = response.json().get("data", [])

            logger.info(f"📊 Meta Ads: Se encontraron {len(all_accounts)} cuentas para portfolio {portfolio_id or 'ME'}")
            return all_accounts
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo cuentas de anuncios de Meta: {e}")
            return []
    async def get_campaigns_with_insights(self, ad_account_id: str, date_preset: str = "maximum", filtering: list = None) -> list:
        """
        Estrategia 'Campaign-First': Lista campañas y expande el campo 'insights' para obtener 
        métricas incluso de las borradas/archivadas que el endpoint de /insights omite.
        """
        if not self.access_token:
            raise MetaAuthError("META_ADS_TOKEN no configurado.")
        
        account_id = ad_account_id if ad_account_id.startswith("act_") else f"act_{ad_account_id}"
        
        if filtering is None:
            filtering = [{'field': 'effective_status', 'operator': 'IN', 'value': [
                'ACTIVE', 'PAUSED', 'DELETED', 'ARCHIVED', 'IN_PROCESS', 'WITH_ISSUES', 
                'CAMPAIGN_PAUSED', 'ADSET_PAUSED'
            ]}]

        url = f"{GRAPH_API_BASE}/{account_id}/campaigns"
        
        # IMPORTANTE: Pedimos 'insights' como expansión de campo
        # Esto permite que campañas borradas/archivadas "arrastren" sus datos de gasto
        expand_insights = f"insights.date_preset({date_preset}){{spend,impressions,clicks,account_currency,account_id}}"
        
        params = {
            "fields": f"id,name,effective_status,{expand_insights}",
            "filtering": json.dumps(filtering),
            "access_token": self.access_token,
            "limit": 100
        }

        logger.info(f"🚀 Campaign-First Request: {url} | Preset={date_preset}")

        try:
            all_campaigns = []
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT * 2) as client:
                current_url = url
                while current_url:
                    response = await client.get(current_url, params=params if current_url == url else None)
                    response.raise_for_status()
                    
                    data = response.json()
                    all_campaigns.extend(data.get("data", []))
                    
                    paging = data.get("paging", {})
                    current_url = paging.get("next")
            
            return all_campaigns
        except Exception as e:
            logger.error(f"❌ Error en Campaign-First retrieval para {account_id}: {e}")
            return []

    async def get_ads_with_insights(self, ad_account_id: str, date_preset: str = "maximum", filtering: Optional[list] = None, include_insights: bool = True) -> list:
        """
        Versión a nivel de Anuncio (Creativo): Lista anuncios y opcionalmente expande 'insights'.
        Incluye el nombre de la campaña padre para facilitar el desglose en UI.
        """
        if not self.access_token:
            raise MetaAuthError("META_ADS_TOKEN no configurado.")
        
        account_id = ad_account_id if ad_account_id.startswith("act_") else f"act_{ad_account_id}"
        
        if filtering is None:
            filtering = [{'field': 'effective_status', 'operator': 'IN', 'value': [
                'ACTIVE', 'PAUSED', 'DELETED', 'ARCHIVED', 'IN_PROCESS', 'WITH_ISSUES', 
                'CAMPAIGN_PAUSED', 'ADSET_PAUSED', 'PENDING_REVIEW', 'DISAPPROVED', 'PREAPPROVED', 'PENDING_BILLING_INFO'
            ]}]

        url = f"{GRAPH_API_BASE}/{account_id}/ads"
        
        fields = "id,name,effective_status,campaign{id,name}"
        if include_insights:
            expand_insights = f"insights.date_preset({date_preset}){{spend,impressions,clicks,account_currency,account_id}}"
            fields += f",{expand_insights}"
        
        params = {
            "fields": fields,
            "filtering": json.dumps(filtering),
            "access_token": self.access_token,
            "limit": 100
        }

        logger.info(f"🎨 Ads Fetch: {url} | Insights={include_insights} | Preset={date_preset}")

        try:
            all_ads = []
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT * 2) as client:
                current_url = url
                while current_url:
                    response = await client.get(current_url, params=params if current_url == url else None)
                    response.raise_for_status()
                    
                    data = response.json()
                    all_ads.extend(data.get("data", []))
                    
                    paging = data.get("paging", {})
                    current_url = paging.get("next")
            
            return all_ads
        except Exception as e:
            logger.error(f"❌ Error en Ads retrieval para {account_id}: {e}")
            return []


class MetaOAuthService:
    """
    Servicio para manejar OAuth flow con Meta/Facebook.
    Maneja token exchange, refresh, y almacenamiento seguro.
    """
    
    @staticmethod
    async def exchange_code_for_token(tenant_id: int, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Intercambia código de autorización por access token.
        
        Args:
            tenant_id: ID del tenant
            code: Código de autorización de OAuth
            redirect_uri: URI de redirección configurada
            
        Returns:
            Dict con access_token, token_type, expires_in, etc.
        """
        import os
        from datetime import datetime, timedelta
        
        app_id = os.getenv("META_APP_ID")
        app_secret = os.getenv("META_APP_SECRET")
        
        if not app_id or not app_secret:
            raise ValueError("META_APP_ID y META_APP_SECRET deben estar configurados")
        
        url = f"{GRAPH_API_BASE}/oauth/access_token"
        params = {
            "client_id": app_id,
            "client_secret": app_secret,
            "redirect_uri": redirect_uri,
            "code": code,
            "grant_type": "authorization_code"
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                
                if response.status_code != 200:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                    logger.error(f"Error exchanging code for token: {error_msg}")
                    raise HTTPException(status_code=400, detail=f"Meta OAuth error: {error_msg}")
                
                token_data = response.json()
                
                # Calcular fecha de expiración
                expires_in = token_data.get("expires_in", 3600)  # Default 1 hour
                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                
                token_data["expires_at"] = expires_at.isoformat()
                token_data["tenant_id"] = tenant_id
                token_data["token_type"] = "META_USER_SHORT_TOKEN"
                
                logger.info(f"Successfully exchanged code for token for tenant {tenant_id}")
                return token_data
                
        except Exception as e:
            logger.error(f"Error in exchange_code_for_token: {e}", exc_info=True)
            raise
    
    @staticmethod
    async def get_long_lived_token(tenant_id: int, short_lived_token: str) -> Dict[str, Any]:
        """
        Obtiene long-lived token (60 días) desde short-lived token.
        
        Args:
            tenant_id: ID del tenant
            short_lived_token: Short-lived access token
            
        Returns:
            Dict con long-lived token y metadata
        """
        import os
        from datetime import datetime, timedelta
        
        app_id = os.getenv("META_APP_ID")
        app_secret = os.getenv("META_APP_SECRET")
        
        if not app_id or not app_secret:
            raise ValueError("META_APP_ID y META_APP_SECRET deben estar configurados")
        
        url = f"{GRAPH_API_BASE}/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": short_lived_token
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                
                if response.status_code != 200:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                    logger.error(f"Error getting long-lived token: {error_msg}")
                    raise HTTPException(status_code=400, detail=f"Meta OAuth error: {error_msg}")
                
                token_data = response.json()
                
                # Calcular fecha de expiración (60 días por defecto)
                expires_in = token_data.get("expires_in", 5184000)  # 60 días en segundos
                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                
                token_data["expires_at"] = expires_at.isoformat()
                token_data["tenant_id"] = tenant_id
                token_data["token_type"] = "META_USER_LONG_TOKEN"
                
                logger.info(f"Successfully obtained long-lived token for tenant {tenant_id}")
                return token_data
                
        except Exception as e:
            logger.error(f"Error in get_long_lived_token: {e}", exc_info=True)
            raise
    
    @staticmethod
    async def get_business_managers_with_token(tenant_id: int, access_token: str) -> List[Dict[str, Any]]:
        """
        Obtiene Business Managers asociados al token.
        
        Args:
            tenant_id: ID del tenant
            access_token: Access token válido
            
        Returns:
            Lista de Business Managers con metadata
        """
        url = f"{GRAPH_API_BASE}/me/businesses"
        params = {
            "fields": "id,name,created_time,updated_time,primary_page{id,name,category}",
            "access_token": access_token,
            "limit": 50
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                
                if response.status_code != 200:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                    logger.error(f"Error getting business managers: {error_msg}")
                    return []
                
                data = response.json()
                businesses = data.get("data", [])
                
                # Enriquecer con ad accounts
                enriched_businesses = []
                for business in businesses:
                    business_id = business.get("id")
                    
                    # Obtener ad accounts para este business
                    ad_accounts_url = f"{GRAPH_API_BASE}/{business_id}/owned_ad_accounts"
                    ad_accounts_params = {
                        "fields": "id,name,account_id,account_status,currency,timezone_name",
                        "access_token": access_token,
                        "limit": 50
                    }
                    
                    try:
                        ad_accounts_response = await client.get(ad_accounts_url, params=ad_accounts_params)
                        if ad_accounts_response.status_code == 200:
                            ad_accounts_data = ad_accounts_response.json()
                            business["ad_accounts"] = ad_accounts_data.get("data", [])
                        else:
                            business["ad_accounts"] = []
                    except Exception:
                        business["ad_accounts"] = []
                    
                    enriched_businesses.append(business)
                
                logger.info(f"Retrieved {len(enriched_businesses)} business managers for tenant {tenant_id}")
                return enriched_businesses
                
        except Exception as e:
            logger.error(f"Error in get_business_managers_with_token: {e}", exc_info=True)
            return []
    
    @staticmethod
    async def store_meta_token(tenant_id: int, token_data: Dict[str, Any]) -> bool:
        """
        Almacena token de Meta en base de datos.
        
        Args:
            tenant_id: ID del tenant
            token_data: Datos del token a almacenar
            
        Returns:
            True si se almacenó correctamente
        """
        try:
            from core.credentials import save_tenant_credential
            import json
            from datetime import datetime

            access_token = token_data.get("access_token")
            expires_at = token_data.get("expires_at")
            business_managers = token_data.get("business_managers", [])
            user_id = token_data.get("user_id")

            # Guardar token usando The Vault (encriptado con Fernet)
            await save_tenant_credential(
                tenant_id=tenant_id,
                name="META_USER_LONG_TOKEN",
                value=access_token,
                category="meta"
            )

            # Guardar metadatos (expires_at, user_id, business managers) como JSON
            meta_info = {
                "expires_at": expires_at,
                "user_id": user_id,
                "business_managers": business_managers,
                "connected_at": datetime.utcnow().isoformat()
            }
            await save_tenant_credential(
                tenant_id=tenant_id,
                name="META_CONNECTION_INFO",
                value=json.dumps(meta_info),
                category="meta"
            )

            # Guardar ID de la primera ad account si existe
            if business_managers:
                bm = business_managers[0]
                ad_accounts = bm.get("ad_accounts", [])
                if ad_accounts:
                    await save_tenant_credential(
                        tenant_id=tenant_id,
                        name="META_AD_ACCOUNT_ID",
                        value=ad_accounts[0].get("account_id", ""),
                        category="meta"
                    )

            logger.info(f"Stored Meta token in Vault for tenant {tenant_id}")
            return True

        except Exception as e:
            logger.error(f"Error storing Meta token: {e}", exc_info=True)
            return False
    
    @staticmethod
    async def remove_meta_token(tenant_id: int) -> bool:
        """
        Elimina token de Meta de la base de datos.
        
        Args:
            tenant_id: ID del tenant
            
        Returns:
            True si se eliminó correctamente
        """
        try:
            from db import db
 
            await db.execute(
                "DELETE FROM credentials WHERE tenant_id = $1 AND name IN ('META_USER_LONG_TOKEN', 'META_CONNECTION_INFO', 'META_AD_ACCOUNT_ID')",
                tenant_id
            )
            
            logger.info(f"Removed Meta credentials from Vault for tenant {tenant_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing Meta token: {e}", exc_info=True)
            return False
    
    @staticmethod
    async def validate_token(tenant_id: int, access_token: str) -> Dict[str, Any]:
        """
        Valida token de Meta haciendo una llamada simple a la API.
        
        Args:
            tenant_id: ID del tenant
            access_token: Token a validar
            
        Returns:
            Dict con información de validación
        """
        url = f"{GRAPH_API_BASE}/me"
        params = {
            "fields": "id,name",
            "access_token": access_token
        }
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url, params=params)
                
                if response.status_code == 200:
                    user_data = response.json()
                    return {
                        "valid": True,
                        "user_id": user_data.get("id"),
                        "user_name": user_data.get("name"),
                        "message": "Token is valid"
                    }
                else:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Invalid token")
                    return {
                        "valid": False,
                        "error": error_msg,
                        "message": "Token is invalid or expired"
                    }
                    
        except Exception as e:
            logger.error(f"Error validating token: {e}")
            return {
                "valid": False,
                "error": str(e),
                "message": "Error validating token"
            }
    
    @staticmethod
    async def get_business_managers(tenant_id: int) -> List[Dict[str, Any]]:
        """
        Obtiene Business Managers del tenant usando el token guardado en The Vault.
        Usado por el wizard de conexión.
        """
        from core.credentials import get_tenant_credential
        import json
        token = await get_tenant_credential(tenant_id, "META_USER_LONG_TOKEN")
        if not token:
            return []
        
        # Intentar obtener desde META_CONNECTION_INFO (ya guardado en el login OAuth)
        conn_info_str = await get_tenant_credential(tenant_id, "META_CONNECTION_INFO")
        if conn_info_str:
            try:
                conn_info = json.loads(conn_info_str)
                bms = conn_info.get("business_managers", [])
                if bms:
                    return bms
            except Exception:
                pass
        
        # Fallback: obtener en vivo desde la Graph API
        return await MetaAdsService.get_business_managers_with_token(tenant_id, token)

    @staticmethod
    async def get_ad_accounts(tenant_id: int, portfolio_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Obtiene Ad Accounts desde Meta usando el token guardado en The Vault.
        Si se pasa portfolio_id, filtra las cuentas del Business Manager.
        """
        from core.credentials import get_tenant_credential
        token = await get_tenant_credential(tenant_id, "META_USER_LONG_TOKEN")
        if not token:
            return []

        try:
            if portfolio_id:
                url = f"{GRAPH_API_BASE}/{portfolio_id}/owned_ad_accounts"
            else:
                url = f"{GRAPH_API_BASE}/me/adaccounts"
            
            params = {
                "fields": "id,name,account_id,account_status,currency,timezone_name",
                "access_token": token,
                "limit": 50
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    return response.json().get("data", [])
                logger.warning(f"Meta get_ad_accounts error: {response.text}")
                return []
        except Exception as e:
            logger.error(f"Error in get_ad_accounts: {e}", exc_info=True)
            return []

    @staticmethod
    async def connect_ad_account(tenant_id: int, account_id: str, account_name: str) -> Dict[str, Any]:
        """
        Guarda el Ad Account seleccionado en The Vault como la cuenta activa del tenant.
        """
        from core.credentials import save_tenant_credential
        # Normalizar: quitar el prefijo 'act_' si viene, luego guardar con y sin prefijo
        clean_id = account_id.replace("act_", "")
        await save_tenant_credential(tenant_id, "META_AD_ACCOUNT_ID", clean_id, "meta")
        logger.info(f"Connected ad account {clean_id} for tenant {tenant_id}")
        return {"connected": True, "account_id": clean_id, "account_name": account_name}

    @staticmethod
    async def test_connection(tenant_id: int) -> Dict[str, Any]:
        """
        Testea conexión con Meta API usando token almacenado.
        
        Args:
            tenant_id: ID del tenant
            
        Returns:
            Dict con resultados del test
        """
        try:
            from core.database import db
            
            # Obtener token del tenant
            token_data = await db.fetch_one(
                "SELECT access_token, expires_at FROM meta_tokens WHERE tenant_id = $1 AND token_type = 'META_USER_LONG_TOKEN'",
                tenant_id
            )
            
            if not token_data:
                return {
                    "connected": False,
                    "message": "No Meta token found for this tenant",
                    "has_token": False
                }
            
            access_token = token_data.get("access_token")
            expires_at = token_data.get("expires_at")
            
            # Validar token
            validation = await MetaOAuthService.validate_token(tenant_id, access_token)
            
            # Verificar expiración
            from datetime import datetime
            expires_datetime = datetime.fromisoformat(expires_at) if expires_at else None
            is_expired = expires_datetime and expires_datetime < datetime.utcnow()
            
            # Obtener información básica del usuario
            url = f"{GRAPH_API_BASE}/me"
            params = {
                "fields": "id,name,accounts{id,name}",
                "access_token": access_token
            }
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url, params=params)
                
                if response.status_code == 200:
                    user_info = response.json()
                    accounts = user_info.get("accounts", {}).get("data", [])
                    
                    return {
                        "connected": True,
                        "valid": validation.get("valid", False),
                        "expired": is_expired,
                        "user_id": user_info.get("id"),
                        "user_name": user_info.get("name"),
                        "ad_accounts_count": len(accounts),
                        "expires_at": expires_at,
                        "message": "Successfully connected to Meta API"
                    }
                else:
                    return {
                        "connected": False,
                        "valid": False,
                        "expired": is_expired,
                        "error": "Failed to fetch user info",
                        "message": "Token exists but API call failed"
                    }
                    
        except Exception as e:
            logger.error(f"Error testing Meta connection: {e}", exc_info=True)
            return {
                "connected": False,
                "error": str(e),
                "message": "Error testing Meta connection"
            }


# Alias para compatibilidad con código existente
MetaAdsService = MetaOAuthService

