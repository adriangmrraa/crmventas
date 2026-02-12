import os
import re
import logging
from datetime import timedelta, timezone
from typing import Optional
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

# Configuración Global
CREDENTIALS_FERNET_KEY = os.getenv("CREDENTIALS_FERNET_KEY")
ARG_TZ = timezone(timedelta(hours=-3))

def get_fernet() -> Optional[Fernet]:
    """Fernet instance for encrypting credentials. Uses CREDENTIALS_FERNET_KEY (url-safe base64)."""
    key = CREDENTIALS_FERNET_KEY
    if not key:
        return None
    if isinstance(key, str):
        key = key.encode("utf-8")
    try:
        return Fernet(key)
    except Exception as e:
        logger.warning(f"Invalid CREDENTIALS_FERNET_KEY: {e}")
        return None

def encrypt_credential(plain: str) -> Optional[str]:
    """Encrypt a credential value with Fernet (AES-256). Returns base64 ciphertext or None if key not configured."""
    f = get_fernet()
    if not f:
        return None
    try:
        return f.encrypt(plain.encode("utf-8")).decode("ascii")
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        return None

def normalize_phone(phone: str) -> str:
    """Asegura que el número tenga el formato +123456789 (E.164)"""
    if not phone:
        return ""
    clean = re.sub(r'\D', '', phone)
    if not phone.startswith('+'):
        return '+' + clean
    return '+' + clean
