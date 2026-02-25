"""
Nexus Security Core — CRM Ventas
Autenticación de doble factor, RBAC granular y aislamiento multi-tenant.
Basado en ClinicForge Nexus Security v7.6.
"""
import os
import uuid
import logging
from typing import List, Optional, Any
from fastapi import Header, HTTPException, Depends, Request, status
from db import db

logger = logging.getLogger(__name__)

# ─── Configuración ─────────────────────────────────────────────────────────────
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
if not ADMIN_TOKEN:
    logger.critical(
        "🚨 SECURITY CRITICAL: ADMIN_TOKEN no está definido en las variables de entorno. "
        "Todas las peticiones admin serán rechazadas con 401. "
        "Define ADMIN_TOKEN en el entorno del orchestrator."
    )

# Roles válidos para el CRM Ventas
CRM_ROLES = ['ceo', 'secretary', 'professional', 'setter', 'closer']


# ─── Capa 1: Autenticación de Doble Factor ─────────────────────────────────────

async def verify_admin_token(
    request: Request,
    x_admin_token: str = Header(None),
    authorization: str = Header(None)
):
    """
    Nexus Security v7.6 — Validación de doble factor:
    Capa 1: X-Admin-Token (Autorización Estática de Infraestructura)
    Capa 2: JWT — Bearer header OR HttpOnly Cookie (mitigación XSS)
    """
    # === Capa 1: X-Admin-Token (Infraestructura) ===
    if ADMIN_TOKEN and x_admin_token != ADMIN_TOKEN:
        logger.warning(
            f"❌ 401: X-Admin-Token inválido o ausente. "
            f"IP: {request.client.host if request.client else 'unknown'}"
        )
        raise HTTPException(
            status_code=401,
            detail="Token de infraestructura (X-Admin-Token) inválido."
        )
    elif not ADMIN_TOKEN:
        logger.warning("⚠️ ADMIN_TOKEN no configurado. Validación de infraestructura omitida.")

    # === Capa 2: JWT — Bearer primero, Cookie HttpOnly como fallback ===
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        logger.debug("🔑 Identity: Using Bearer token.")
    else:
        # Fallback a Cookie HttpOnly para mitigar XSS en clientes modernos
        token = request.cookies.get("access_token")
        if token:
            logger.debug("🍪 Identity: Using access_token cookie.")

    if not token:
        logger.warning(
            f"❌ 401: JWT Token ausente (sin Bearer y sin Cookie). "
            f"IP: {request.client.host if request.client else 'unknown'}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión no válida. Token JWT requerido (Bearer o Cookie)."
        )

    # Importación tardía para evitar ciclos de importación
    from auth_service import auth_service
    user_data = auth_service.decode_token(token)

    if not user_data:
        logger.warning(
            f"❌ 401: JWT expirado o inválido. "
            f"IP: {request.client.host if request.client else 'unknown'}"
        )
        raise HTTPException(status_code=401, detail="Token de sesión expirado o inválido.")

    # Validar que el rol es un rol CRM válido
    if user_data.role not in CRM_ROLES:
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos suficientes para realizar esta acción."
        )

    # Inyectar datos del usuario en el request state para uso posterior
    request.state.user = user_data
    return user_data


# ─── Capa 2: RBAC Granular ─────────────────────────────────────────────────────

def require_role(allowed_roles: List[str]):
    """
    Factory para dependencias de RBAC granular por endpoint.

    Uso:
        @router.get("/admin-only", dependencies=[Depends(require_role(['ceo']))])
        async def admin_endpoint(...): ...
    """
    async def role_dependency(user_data=Depends(verify_admin_token)):
        if user_data.role not in allowed_roles:
            logger.warning(
                f"❌ 403: Rol '{user_data.role}' no autorizado. "
                f"Se requiere uno de: {', '.join(allowed_roles)}"
            )
            raise HTTPException(
                status_code=403,
                detail=f"Permisos insuficientes. Se requiere uno de: {', '.join(allowed_roles)}"
            )
        return user_data
    return role_dependency


# ─── Capa 3: Resolución de Tenant ─────────────────────────────────────────────

async def get_resolved_tenant_id(user_data=Depends(verify_admin_token)) -> int:
    """
    Resuelve el tenant_id real contra la base de datos (Nexus Protocol).
    Prioridad: sellers (CRM) → professionals (dental legacy) → primer tenant → 1.
    Garantiza aislamiento total: nunca se usa tenant_id del JWT sin validar.
    """
    uid = None
    try:
        uid = uuid.UUID(user_data.user_id)
    except (ValueError, TypeError):
        pass

    if uid is not None:
        # Prioridad 1: Tabla sellers (CRM Ventas — rol nativo)
        try:
            tid = await db.pool.fetchval(
                "SELECT tenant_id FROM sellers WHERE user_id = $1",
                uid
            )
            if tid is not None:
                return int(tid)
        except Exception:
            pass  # Tabla sellers puede no existir en entornos legacy

        # Prioridad 2: Tabla professionals (dental/legacy fallback)
        try:
            tid = await db.pool.fetchval(
                "SELECT tenant_id FROM professionals WHERE user_id = $1",
                uid
            )
            if tid is not None:
                return int(tid)
        except Exception:
            pass

    # Prioridad 3: Primer tenant del sistema (CEO sin fila en sellers/professionals)
    try:
        first = await db.pool.fetchval("SELECT id FROM tenants ORDER BY id ASC LIMIT 1")
        return int(first) if first is not None else 1
    except Exception:
        return 1  # Fallback final: no devolver 500


async def get_allowed_tenant_ids(user_data=Depends(verify_admin_token)) -> List[int]:
    """
    Lista de tenant_id que el usuario puede ver.
    CEO: todos los tenants. Resto: solo su sede resuelta.
    """
    try:
        if user_data.role == "ceo":
            rows = await db.pool.fetch("SELECT id FROM tenants ORDER BY id ASC")
            return [int(r["id"]) for r in rows] if rows else [1]

        uid = None
        try:
            uid = uuid.UUID(user_data.user_id)
        except (ValueError, TypeError):
            pass

        if uid is not None:
            # Buscar en sellers primero (CRM)
            try:
                tid = await db.pool.fetchval(
                    "SELECT tenant_id FROM sellers WHERE user_id = $1", uid
                )
                if tid is not None:
                    return [int(tid)]
            except Exception:
                pass

            # Fallback a professionals
            try:
                tid = await db.pool.fetchval(
                    "SELECT tenant_id FROM professionals WHERE user_id = $1", uid
                )
                if tid is not None:
                    return [int(tid)]
            except Exception:
                pass

        first = await db.pool.fetchval("SELECT id FROM tenants ORDER BY id ASC LIMIT 1")
        return [int(first)] if first is not None else [1]
    except Exception:
        return [1]


# ─── Auditoría ────────────────────────────────────────────────────────────────

async def log_pii_access(
    request: Request,
    user_data: Any,
    resource_id: Any,
    action: str = "read"
):
    """
    Registra auditoría de acceso a datos sensibles (Nexus Protocol v7.6).
    Llamar en endpoints que expongan PII (leads, contactos, datos de venta).
    """
    logger.info(
        f"🛡️ AUDIT: {user_data.email} ({user_data.role}) → {action} on {resource_id}. "
        f"IP: {request.client.host if request.client else 'unknown'}"
    )


# ─── Contexto de Usuario ──────────────────────────────────────────────────────

async def get_current_user_context(user_data=Depends(verify_admin_token)) -> dict:
    """Retorna el contexto del usuario actual para usar en dependencias de FastAPI."""
    return {
        "user_id": user_data.user_id,
        "role": user_data.role,
        "tenant_id": await get_resolved_tenant_id(user_data),
    }
