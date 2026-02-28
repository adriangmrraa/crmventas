from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import Optional
import os
import uuid
import json
import logging
from db import db
from auth_service import auth_service
from core.security import audit_access
from core.rate_limiter import limiter

router = APIRouter(prefix="/auth", tags=["Nexus Auth"])
logger = logging.getLogger("auth_routes")

# Detectar entorno para configurar cookie.secure
IS_PRODUCTION = os.getenv("ENVIRONMENT", "production").lower() != "development"
ACCESS_TOKEN_MAX_AGE = 60 * 60 * 24 * 7  # 1 semana (igual que ACCESS_TOKEN_EXPIRE_MINUTES)

# --- MODELS ---

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    role: str = "professional"
    first_name: str
    last_name: Optional[str] = ""
    tenant_id: Optional[int] = None  # Obligatorio para professional/secretary
    specialty: Optional[str] = None
    phone_number: Optional[str] = None
    registration_id: Optional[str] = None  # Matrícula
    google_calendar_id: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

# --- ROUTES ---

def _default_working_hours():
    start = "09:00"
    end = "18:00"
    slot = {"start": start, "end": end}
    wh = {}
    for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
        is_working_day = day != "sunday"
        wh[day] = {"enabled": is_working_day, "slots": [slot] if is_working_day else []}
    return wh


@router.get("/companies")
async def list_companies_public():
    """
    Lista de empresas para el selector del formulario de registro.
    Público (sin autenticación). Solo id y nombre.
    """
    try:
        rows = await db.pool.fetch(
            "SELECT id, clinic_name FROM tenants ORDER BY id ASC"
        )
        return [{"id": r["id"], "clinic_name": r["clinic_name"]} for r in rows]
    except Exception as e:
        logger.warning(f"list_companies_public failed: {e}")
        return []


@router.post("/register")
@limiter.limit("3/minute")
async def register(request: Request, payload: UserRegister):
    """
    Registers a new user in 'pending' status.
    CRM mode: roles válidos son seller, closer, setter, secretary, admin, ceo.
    Para seller/closer/setter/secretary exige tenant_id. Crea fila en sellers con is_active=FALSE.
    """
    existing = await db.fetchval("SELECT id FROM users WHERE email = $1", payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="El correo ya se encuentra registrado.")

    CRM_TENANT_ROLES = ("seller", "closer", "setter", "secretary", "ceo", "professional")

    if payload.role in CRM_TENANT_ROLES:
        if payload.tenant_id is None:
            raise HTTPException(
                status_code=400,
                detail="Debés elegir una sede o empresa para registrarte.",
            )
        tenant_exists = await db.pool.fetchval("SELECT 1 FROM tenants WHERE id = $1", payload.tenant_id)
        if not tenant_exists:
            raise HTTPException(status_code=400, detail="La empresa elegida no existe.")

    password_hash = auth_service.get_password_hash(payload.password)
    user_id = str(uuid.uuid4())
    first_name = (payload.first_name or "").strip() or "Usuario"
    last_name = (payload.last_name or "").strip() or " "

    try:
        # Determine tenant_id (defaults to 1 for CEO/Admin if not provided, though they usually aren't registered this way)
        assigned_tenant_id = int(payload.tenant_id) if payload.tenant_id is not None else 1

        await db.execute("""
            INSERT INTO users (id, email, password_hash, role, status, first_name, last_name, tenant_id)
            VALUES ($1, $2, $3, $4, 'pending', $5, $6, $7)
        """, user_id, payload.email, password_hash, payload.role, first_name, last_name, assigned_tenant_id)

        # CRM: Crear fila en sellers para roles que requieren tenant
        if payload.role in CRM_TENANT_ROLES:
            tenant_id = int(payload.tenant_id)
            uid = uuid.UUID(user_id)
            phone_val = (payload.phone_number or "").strip() or None
            await db.pool.execute("""
                INSERT INTO sellers (user_id, tenant_id, first_name, last_name, email, phone_number, is_active, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, FALSE, NOW(), NOW())
                ON CONFLICT (user_id) DO NOTHING
            """, uid, tenant_id, first_name, last_name, payload.email, phone_val)

        activation_token = str(uuid.uuid4())
        auth_service.log_protocol_omega_activation(payload.email, activation_token)

        return {
            "success": True,
            "status": "pending",
            "message": "¡Registro exitoso! Tu cuenta ha sido creada y está pendiente de aprobación por el CEO. Recibirás un correo cuando sea activada.",
            "user_id": user_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        # Intentar limpiar si falló a mitad (aunque db.pool suele ser atómico si usas transacción, aquí son llamadas separadas)
        raise HTTPException(status_code=500, detail="Error interno durante el registro. Por favor, intenta de nuevo.")


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(request: Request, payload: UserLogin):
    """
    Autentica usuario y retorna JWT.
    Nexus Security v7.7: Rate limited (5/min) + HttpOnly Cookie.
    """
    # Fetch user
    user = await db.fetchrow("SELECT * FROM users WHERE email = $1", payload.email)

    if not user:
        raise HTTPException(status_code=401, detail="Credenciales inválidas.")

    if not auth_service.verify_password(payload.password, user['password_hash']):
        raise HTTPException(status_code=401, detail="Credenciales inválidas.")

    if user['status'] != 'active':
        raise HTTPException(
            status_code=403,
            detail=f"Tu cuenta está en estado '{user['status']}'. Contactá al administrador."
        )

    # Resolver tenant_id: sellers (CRM) → professionals (legacy) → primer tenant
    # Try/except porque sellers puede no existir en DB sin parche aplicado aún
    tenant_id = None
    try:
        tenant_id = await db.fetchval(
            "SELECT tenant_id FROM sellers WHERE user_id = $1", user['id']
        )
    except Exception:
        pass  # Tabla sellers no existe aún, continuar con fallback

    if tenant_id is None:
        try:
            tenant_id = await db.fetchval(
                "SELECT tenant_id FROM professionals WHERE user_id = $1", user['id']
            )
        except Exception:
            pass

    if tenant_id is None:
        tenant_id = await db.fetchval("SELECT id FROM tenants ORDER BY id ASC LIMIT 1") or 1
    tenant_id = int(tenant_id)


    niche_type = await db.fetchval(
        "SELECT COALESCE(niche_type, 'crm_sales') FROM tenants WHERE id = $1", tenant_id
    ) or "crm_sales"

    token_data = {
        "user_id": str(user['id']),
        "email": user['email'],
        "role": user['role'],
        "tenant_id": tenant_id,
        "niche_type": niche_type,
    }
    token = auth_service.create_access_token(token_data)

    user_profile = {
        "id": str(user['id']),
        "email": user['email'],
        "role": user['role'],
        "tenant_id": tenant_id,
        "niche_type": niche_type,
    }

    # Nexus Security v7.6: emitir Set-Cookie HttpOnly (mitigación XSS)
    response = JSONResponse(content={
        "access_token": token,   # Mantenido para compatibilidad durante transición
        "token_type": "bearer",
        "user": user_profile,
    })
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,         # No accesible via JavaScript
        secure=IS_PRODUCTION,  # Solo HTTPS en producción
        samesite="lax",        # Permite OAuth redirects (Meta, Google)
        max_age=ACCESS_TOKEN_MAX_AGE,
    )
    logger.info(f"✅ Login exitoso: {user['email']} (tenant_id={tenant_id}, role={user['role']})")
    return response


@router.get("/me")
@audit_access("verify_session")
async def get_me(request: Request):
    """
    Retorna el perfil del usuario autenticado.
    Nexus Security v7.6: acepta Bearer Token O Cookie HttpOnly.
    """
    # Capa 1: Bearer Token (legacy + clientes que no soporten cookies)
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    else:
        # Capa 2: Cookie HttpOnly (Nexus Security v7.6)
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado. Se requiere Bearer Token o Cookie de sesión."
        )

    token_data = auth_service.decode_token(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado o inválido."
        )

    return token_data


@router.post("/logout")
async def logout():
    """
    Cierra sesión del usuario limpiando la Cookie HttpOnly del servidor.
    El cliente debe también limpiar localStorage si almacena tokens.
    """
    response = JSONResponse(content={"status": "ok", "message": "Sesión cerrada exitosamente."})
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="lax",
    )
    return response

class ProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    google_calendar_id: Optional[str] = None

@router.get("/profile")
async def get_profile(request: Request):
    """ Returns the detailed clinical profile of the current professional/user. """
    user_data = await get_me(request)
    user_id = user_data.user_id
    
    # Base user data
    user = await db.fetchrow("SELECT id, email, role, first_name, last_name FROM users WHERE id = $1", user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    
    profile = dict(user)
    
    # Professional specific data
    if user['role'] == 'professional':
        prof = await db.fetchrow("SELECT google_calendar_id, is_active FROM professionals WHERE user_id = $1", uuid.UUID(user_id))
        if prof:
            profile.update(dict(prof))
            
    return profile

@router.patch("/profile")
async def update_profile(payload: ProfileUpdate, request: Request):
    """ Updates the clinical profile of the current professional/user. """
    user_data = await get_me(request)
    user_id = user_data.user_id
    
    # Update users table
    update_users_fields = []
    params = []
    if payload.first_name is not None:
        update_users_fields.append(f"first_name = ${len(params)+1}")
        params.append(payload.first_name)
    if payload.last_name is not None:
        update_users_fields.append(f"last_name = ${len(params)+1}")
        params.append(payload.last_name)
        
    if update_users_fields:
        params.append(user_id)
        query = f"UPDATE users SET {', '.join(update_users_fields)} WHERE id = ${len(params)}"
        await db.execute(query, *params)
        
    # Update professionals table if applicable
    if user_data.role == 'professional' and payload.google_calendar_id is not None:
        await db.execute("""
            UPDATE professionals 
            SET google_calendar_id = $1 
            WHERE user_id = $2
        """, payload.google_calendar_id, uuid.UUID(user_id))
        
    return {"message": "Perfil actualizado correctamente."}
