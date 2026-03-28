"""
DEV-29: User & Role Management Routes
Setup: crear usuarios y roles para setter y closer en el sistema.

Endpoints:
  POST /admin/setup/seed-team    — Seed default Codexy team (admin token only, no JWT)
  POST /admin/core/users         — Create a user (CEO only)
  GET  /admin/core/users         — List all users for tenant (CEO only)
"""
import os
import uuid
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Header, Request
from pydantic import BaseModel, EmailStr

from db import db
from auth_service import auth_service
from core.security import verify_admin_token, get_resolved_tenant_id, require_role

logger = logging.getLogger("user_management")

router = APIRouter(tags=["User Management"])

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

# Valid CRM roles (must match users_role_check constraint)
VALID_ROLES = {"ceo", "professional", "secretary", "setter", "closer"}


# ─── Pydantic Models ────────────────────────────────────────────────────────────

class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    role: str
    first_name: str
    last_name: Optional[str] = ""


class UserOut(BaseModel):
    id: str
    email: str
    role: str
    status: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    tenant_id: Optional[int] = None


# ─── Helper ──────────────────────────────────────────────────────────────────────

async def _create_user_and_seller(
    email: str,
    password: str,
    role: str,
    first_name: str,
    last_name: str,
    tenant_id: int,
) -> dict:
    """
    Creates a user + seller record. Returns dict with user info.
    Idempotent: if user with email already exists, returns existing user info.
    """
    # Check if user already exists
    existing = await db.fetchrow("SELECT id, email, role, status, first_name, last_name, tenant_id FROM users WHERE email = $1", email)
    if existing:
        return {
            "id": str(existing["id"]),
            "email": existing["email"],
            "role": existing["role"],
            "status": existing["status"],
            "first_name": existing["first_name"],
            "last_name": existing["last_name"],
            "tenant_id": existing["tenant_id"],
            "created": False,
        }

    user_id = uuid.uuid4()
    password_hash = auth_service.get_password_hash(password)

    await db.execute(
        """
        INSERT INTO users (id, email, password_hash, role, status, first_name, last_name, tenant_id)
        VALUES ($1, $2, $3, $4, 'active', $5, $6, $7)
        """,
        str(user_id), email, password_hash, role,
        first_name or "Usuario", last_name or "",
        tenant_id,
    )

    # Create seller record linking user_id to tenant
    try:
        await db.pool.execute(
            """
            INSERT INTO sellers (user_id, tenant_id, first_name, last_name, email, is_active, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, TRUE, NOW(), NOW())
            ON CONFLICT (user_id) DO NOTHING
            """,
            user_id, tenant_id,
            first_name or "Usuario", last_name or "",
            email,
        )
    except Exception as e:
        logger.warning(f"Could not create seller record for {email}: {e}")

    return {
        "id": str(user_id),
        "email": email,
        "role": role,
        "status": "active",
        "first_name": first_name,
        "last_name": last_name,
        "tenant_id": tenant_id,
        "created": True,
    }


# ─── 1. Seed Team Endpoint (admin token only, no JWT required) ──────────────────

@router.post("/admin/setup/seed-team")
async def seed_team(x_admin_token: str = Header(None)):
    """
    Seeds the default Codexy team: CEO, 2 Setters, 1 Closer.
    Protected by X-Admin-Token only (no JWT needed — used before any user exists).
    Idempotent: skips users that already exist.
    """
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=500, detail="ADMIN_TOKEN not configured on server.")
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid X-Admin-Token.")

    # Ensure tenant "Codexy" exists
    tenant_row = await db.fetchrow("SELECT id FROM tenants WHERE clinic_name = 'Codexy' LIMIT 1")
    if tenant_row:
        tenant_id = tenant_row["id"]
    else:
        # Create Codexy tenant
        tenant_id = await db.fetchval(
            """
            INSERT INTO tenants (clinic_name, bot_phone_number, owner_email)
            VALUES ('Codexy', '+0000000000', 'ceo@codexy.com')
            RETURNING id
            """
        )
        logger.info(f"Created tenant 'Codexy' with id={tenant_id}")

    # Define the team
    team = [
        {"email": "ceo@codexy.com",     "password": "Codexy2026!",  "role": "ceo",    "first_name": "CEO",     "last_name": "Codexy"},
        {"email": "setter1@codexy.com",  "password": "Setter2026!",  "role": "setter",  "first_name": "Setter",  "last_name": "Uno"},
        {"email": "setter2@codexy.com",  "password": "Setter2026!",  "role": "setter",  "first_name": "Setter",  "last_name": "Dos"},
        {"email": "closer1@codexy.com",  "password": "Closer2026!",  "role": "closer",  "first_name": "Closer",  "last_name": "Uno"},
    ]

    results = []
    for member in team:
        try:
            result = await _create_user_and_seller(
                email=member["email"],
                password=member["password"],
                role=member["role"],
                first_name=member["first_name"],
                last_name=member["last_name"],
                tenant_id=tenant_id,
            )
            results.append(result)
        except Exception as e:
            logger.error(f"Error creating user {member['email']}: {e}")
            results.append({"email": member["email"], "error": str(e)})

    created_count = sum(1 for r in results if r.get("created"))
    existing_count = sum(1 for r in results if r.get("created") is False)

    return {
        "success": True,
        "tenant": {"id": tenant_id, "name": "Codexy"},
        "summary": {
            "created": created_count,
            "already_existed": existing_count,
            "errors": len(results) - created_count - existing_count,
        },
        "users": [
            {k: v for k, v in r.items() if k != "created"}
            for r in results if "error" not in r
        ],
    }


# ─── 2. Create User (CEO only) ──────────────────────────────────────────────────

@router.post("/admin/core/users")
async def create_user(
    payload: CreateUserRequest,
    request: Request,
    user_data=Depends(require_role(["ceo"])),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """
    Creates a new user + seller record. CEO only.
    Validates role, hashes password, returns created user (without password).
    """
    if payload.role not in VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Rol invalido '{payload.role}'. Roles validos: {', '.join(sorted(VALID_ROLES))}",
        )

    # Check if email is taken
    existing = await db.fetchval("SELECT id FROM users WHERE email = $1", payload.email)
    if existing:
        raise HTTPException(status_code=409, detail=f"Ya existe un usuario con el email {payload.email}.")

    try:
        result = await _create_user_and_seller(
            email=payload.email,
            password=payload.password,
            role=payload.role,
            first_name=payload.first_name,
            last_name=payload.last_name or "",
            tenant_id=tenant_id,
        )
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail="Error interno al crear el usuario.")

    # Remove internal fields from response
    result.pop("created", None)

    return {"success": True, "user": result}


# ─── 3. List Users (CEO only) ────────────────────────────────────────────────────

@router.get("/admin/core/users")
async def list_users(
    request: Request,
    user_data=Depends(require_role(["ceo"])),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """
    Lists all users for the tenant with their roles and status. CEO only.
    """
    try:
        rows = await db.pool.fetch(
            """
            SELECT u.id, u.email, u.role, u.status, u.first_name, u.last_name, u.tenant_id, u.created_at,
                   s.is_active AS seller_is_active
            FROM users u
            LEFT JOIN sellers s ON s.user_id = u.id
            WHERE u.tenant_id = $1
            ORDER BY u.created_at ASC
            """,
            tenant_id,
        )
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener usuarios.")

    users = []
    for row in rows:
        users.append({
            "id": str(row["id"]),
            "email": row["email"],
            "role": row["role"],
            "status": row["status"],
            "first_name": row["first_name"],
            "last_name": row["last_name"],
            "tenant_id": row["tenant_id"],
            "seller_is_active": row["seller_is_active"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        })

    return {"success": True, "count": len(users), "users": users}
