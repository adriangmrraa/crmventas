"""
Nexus Credential Vault — CRM Ventas
Basado en ClinicForge Nexus Security v7.6.
Encriptación/desencriptación Fernet para credenciales multi-tenant.
"""
import logging
import os
from typing import Optional
from cryptography.fernet import Fernet

# Configuración Global de Seguridad
CREDENTIALS_FERNET_KEY = os.getenv("CREDENTIALS_FERNET_KEY")

logger = logging.getLogger(__name__)

if not CREDENTIALS_FERNET_KEY:
    logger.warning(
        "⚠️ CREDENTIALS_FERNET_KEY no definida. "
        "Las credenciales se guardarán en texto plano hasta que se configure."
    )

# ─── Nombres de credenciales estándar CRM ─────────────────────────────────────
# WhatsApp / YCloud
YCLOUD_API_KEY = "YCLOUD_API_KEY"
YCLOUD_WEBHOOK_SECRET = "YCLOUD_WEBHOOK_SECRET"
YCLOUD_WHATSAPP_NUMBER = "YCLOUD_WHATSAPP_NUMBER"

# Chatwoot
CHATWOOT_API_TOKEN = "CHATWOOT_API_TOKEN"
CHATWOOT_ACCOUNT_ID = "CHATWOOT_ACCOUNT_ID"
CHATWOOT_BASE_URL = "CHATWOOT_BASE_URL"
WEBHOOK_ACCESS_TOKEN = "WEBHOOK_ACCESS_TOKEN"

# Meta / Facebook Ads
META_USER_LONG_TOKEN = "META_USER_LONG_TOKEN"
META_APP_ID = "META_APP_ID"
META_APP_SECRET = "META_APP_SECRET"
META_AD_ACCOUNT_ID = "META_AD_ACCOUNT_ID"

# OpenAI / IA
OPENAI_API_KEY = "OPENAI_API_KEY"

# ─── Encriptación ──────────────────────────────────────────────────────────────

def encrypt_value(value: str) -> str:
    """Encripta un valor usando Fernet si la clave está configurada."""
    if not CREDENTIALS_FERNET_KEY:
        return value
    try:
        key = CREDENTIALS_FERNET_KEY.encode("utf-8") if isinstance(CREDENTIALS_FERNET_KEY, str) else CREDENTIALS_FERNET_KEY
        f = Fernet(key)
        return f.encrypt(value.encode("utf-8")).decode("ascii")
    except Exception as e:
        logger.error(f"Error encrypting credential value: {e}")
        return value  # Fallback transparente


def decrypt_value(cipher: str) -> str:
    """
    Desencripta un valor usando Fernet si la clave está configurada.
    Si la desencriptación falla, asume texto plano (migración gradual).
    """
    if not CREDENTIALS_FERNET_KEY or not cipher:
        return cipher
    try:
        key = CREDENTIALS_FERNET_KEY.encode("utf-8") if isinstance(CREDENTIALS_FERNET_KEY, str) else CREDENTIALS_FERNET_KEY
        f = Fernet(key)
        return f.decrypt(cipher.strip().encode("ascii")).decode("utf-8")
    except Exception:
        # Fallback: asumir texto plano para migración gradual
        return cipher

# ─── CRUD de Credenciales ──────────────────────────────────────────────────────

from db import get_pool


async def get_tenant_credential(tenant_id: int, name: str) -> Optional[str]:
    """
    Obtiene el valor desencriptado de una credencial del tenant.
    Fallback: busca en variable de entorno global con el mismo nombre.
    """
    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT value FROM credentials WHERE tenant_id = $1 AND name = $2 LIMIT 1",
        tenant_id,
        name,
    )
    if not row or not row["value"]:
        # Nexus Resilience Protocol: fallback a env var global
        env_val = os.getenv(name)
        # Fallback específico para Meta Ads
        if not env_val and name == META_USER_LONG_TOKEN:
            env_val = os.getenv("META_ADS_TOKEN")
        return env_val.strip() if env_val else None

    # Intentar desencriptar (Fernet o texto plano)
    return decrypt_value(str(row["value"]))


async def get_tenant_credential_int(tenant_id: int, name: str) -> Optional[int]:
    """Conveniencia para credenciales numéricas (ej. CHATWOOT_ACCOUNT_ID)."""
    v = await get_tenant_credential(tenant_id, name)
    if v is None:
        return None
    try:
        return int(v)
    except ValueError:
        return None


async def resolve_tenant_from_webhook_token(access_token: str) -> Optional[int]:
    """Resuelve tenant_id desde WEBHOOK_ACCESS_TOKEN (webhook Chatwoot)."""
    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT tenant_id FROM credentials WHERE name = $1 AND value = $2 LIMIT 1",
        WEBHOOK_ACCESS_TOKEN,
        access_token.strip(),
    )
    return int(row["tenant_id"]) if row else None


async def save_tenant_credential(
    tenant_id: int, name: str, value: str, category: str = "general"
) -> bool:
    """
    Guarda o actualiza una credencial para un tenant.
    El valor se encripta automáticamente con Fernet si la clave está configurada.
    """
    pool = get_pool()
    final_value = encrypt_value(value)

    try:
        await pool.execute(
            """
            INSERT INTO credentials (tenant_id, name, value, category, updated_at)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (tenant_id, name)
            DO UPDATE SET value = $3, category = $4, updated_at = NOW()
            """,
            tenant_id,
            name,
            final_value,
            category,
        )
        logger.info(f"✅ Credential '{name}' saved for tenant {tenant_id} (encrypted={bool(CREDENTIALS_FERNET_KEY)})")
        return True
    except Exception as e:
        logger.error(f"Error saving credential '{name}' for tenant {tenant_id}: {e}")
        return False
