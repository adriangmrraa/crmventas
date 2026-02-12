import os
import uuid
import logging
from typing import List, Optional
from fastapi import Header, HTTPException, Depends, Request, status
from db import db

logger = logging.getLogger(__name__)

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "admin-secret-token")

async def verify_admin_token(
    request: Request,
    x_admin_token: str = Header(None),
    authorization: str = Header(None)
):
    """
    Implementa la validación de doble factor para administración:
    1. Validar Token JWT (Identidad y Sesión)
    2. Validar X-Admin-Token (Autorización Estática de Infraestructura)
    """
    # 1. Validar X-Admin-Token
    if not ADMIN_TOKEN:
        logger.warning("⚠️ ADMIN_TOKEN no configurado. Validación estática omitida.")
    elif x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Token de infraestructura (X-Admin-Token) inválido.")

    # 2. Validar JWT (Capa de Identidad)
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión no válida. Token JWT requerido.")
    
    token = authorization.split(" ")[1]
    # Importación tardía para evitar ciclos si auth_service importa algo de aquí (aunque no debería)
    from auth_service import auth_service
    user_data = auth_service.decode_token(token)
    
    if not user_data:
        raise HTTPException(status_code=401, detail="Token de sesión expirado o inválido.")
    
    # 3. Validar Rol (CEOs, Secretarias y Profesionales tienen acceso básico)
    if user_data.role not in ['ceo', 'secretary', 'professional', 'setter', 'closer']:
        raise HTTPException(status_code=403, detail="No tienes permisos suficientes para realizar esta acción.")

    # Inyectar datos del usuario en el request state para uso posterior
    request.state.user = user_data
    return user_data


async def get_resolved_tenant_id(user_data=Depends(verify_admin_token)) -> int:
    """
    Resuelve el tenant_id real consultando la tabla professionals mediante el UUID del current_user.
    Garantiza aislamiento total: nunca se usa tenant_id del JWT sin validar contra BD.
    - Si el usuario es professional: tenant_id de su fila en professionals.
    - Si es CEO/secretary (sin fila en professionals): primera clínica (tenants ORDER BY id LIMIT 1).
    """
    try:
        tid = await db.pool.fetchval(
            "SELECT tenant_id FROM professionals WHERE user_id = $1",
            uuid.UUID(user_data.user_id)
        )
        if tid is not None:
            return int(tid)
    except (ValueError, TypeError):
        pass
    except Exception:
        pass  # BD sin professionals o sin tenant_id
    try:
        first = await db.pool.fetchval("SELECT id FROM tenants ORDER BY id ASC LIMIT 1")
        return int(first) if first is not None else 1
    except Exception:
        return 1  # Fallback para no devolver 500 si tenants no existe


async def get_allowed_tenant_ids(user_data=Depends(verify_admin_token)) -> List[int]:
    """
    Lista de tenant_id que el usuario puede ver (chats, sesiones).
    CEO: todos los tenants. Secretary/Professional: solo su clínica resuelta.
    """
    try:
        if user_data.role == "ceo":
            rows = await db.pool.fetch("SELECT id FROM tenants ORDER BY id ASC")
            return [int(r["id"]) for r in rows] if rows else [1]
        try:
            tid = await db.pool.fetchval(
                "SELECT tenant_id FROM professionals WHERE user_id = $1",
                uuid.UUID(user_data.user_id),
            )
            if tid is not None:
                return [int(tid)]
        except (ValueError, TypeError):
            pass
        first = await db.pool.fetchval("SELECT id FROM tenants ORDER BY id ASC LIMIT 1")
        return [int(first)] if first is not None else [1]
    except Exception:
        return [1]  # Fallback para no devolver 500


async def get_current_user_context(user_data=Depends(verify_admin_token)) -> dict:
    """
    Retorna el contexto del usuario actual para usar en dependencias de FastAPI.
    """
    return {
        "user_id": user_data.user_id,
        "role": user_data.role,
        "tenant_id": await get_resolved_tenant_id(user_data),
    }
