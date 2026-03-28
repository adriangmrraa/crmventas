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


# ─── 4. Seed Demo Leads (admin token only) ─────────────────────────────────────

@router.post("/admin/setup/seed-demo-leads")
async def seed_demo_leads(x_admin_token: str = Header(None)):
    """
    Seeds 18 realistic demo leads spread across all pipeline statuses.
    Protected by X-Admin-Token only (no JWT needed).
    Idempotent: skips if leads already exist for the tenant.
    """
    import random
    from datetime import datetime, timedelta, timezone

    if not ADMIN_TOKEN:
        raise HTTPException(status_code=500, detail="ADMIN_TOKEN not configured on server.")
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid X-Admin-Token.")

    # Find Codexy tenant
    tenant_row = await db.fetchrow("SELECT id FROM tenants WHERE clinic_name = 'Codexy' LIMIT 1")
    if not tenant_row:
        raise HTTPException(status_code=404, detail="Tenant 'Codexy' not found. Run /admin/setup/seed-team first.")
    tenant_id = tenant_row["id"]

    # Idempotent check
    existing_count = await db.fetchval("SELECT COUNT(*) FROM leads WHERE tenant_id = $1", tenant_id)
    if existing_count and existing_count > 0:
        return {
            "success": True,
            "message": f"Leads already exist ({existing_count} found). Skipping seed.",
            "created": 0,
            "existing": existing_count,
        }

    # Get a seller for assignments (first active setter or any seller)
    seller_row = await db.fetchrow(
        """
        SELECT s.id AS seller_id, u.id AS user_id
        FROM sellers s JOIN users u ON s.user_id = u.id
        WHERE s.tenant_id = $1 AND s.is_active = TRUE
        ORDER BY u.role = 'setter' DESC, s.id ASC
        LIMIT 1
        """,
        tenant_id,
    )
    seller_user_id = str(seller_row["user_id"]) if seller_row else None

    # Get seeded tags
    tag_rows = await db.pool.fetch("SELECT name FROM lead_tags WHERE tenant_id = $1 AND is_active = TRUE", tenant_id)
    available_tags = [r["name"] for r in tag_rows] if tag_rows else []

    now = datetime.now(timezone.utc)

    # Demo leads data: (first_name, last_name, phone, email, company, source, status, score, estimated_value, days_ago)
    demo_leads = [
        # 4x nuevo
        ("Martín",   "González",   "+5491155001001", "martin.gonzalez@gmail.com",    "Estudio Contable MG",   "whatsapp_inbound", "nuevo",                 15, 0,       0),
        ("Lucía",    "Fernández",  "+5491155001002", "lucia.fernandez@hotmail.com",  "Boutique Lucía",        "meta_ads",         "nuevo",                 22, 0,       1),
        ("Santiago",  "López",     "+5491155001003", "santiago.lopez@outlook.com",   "López & Asociados",     "csv_import",       "nuevo",                 10, 0,       0),
        ("Valentina", "Martínez",  "+5491155001004", "valentina.m@gmail.com",        "VM Consultora",         "whatsapp_inbound", "nuevo",                 30, 0,       2),
        # 3x contactado
        ("Tomás",    "Rodríguez",  "+5491155001005", "tomas.rodriguez@gmail.com",    "TR Arquitectura",       "meta_ads",         "contactado",            45, 50000,   3),
        ("Camila",   "García",     "+5491155001006", "camila.garcia@yahoo.com",      "Peluquería Camila",     "whatsapp_inbound", "contactado",            55, 35000,   4),
        ("Nicolás",  "Díaz",       "+5491155001007", "nicolas.diaz@gmail.com",       "Díaz Seguros",          "meta_ads",         "contactado",            40, 80000,   5),
        # 2x calificado
        ("Florencia","Romero",     "+5491155001008", "florencia.romero@gmail.com",   "FR Marketing Digital",  "whatsapp_inbound", "calificado",            70, 120000,  7),
        ("Matías",   "Sánchez",    "+5491155001009", "matias.sanchez@empresa.com",   "Sánchez Inmobiliaria",  "csv_import",       "calificado",            65, 200000,  6),
        # 2x llamada_agendada
        ("Carolina", "Moreno",     "+5491155001010", "carolina.moreno@gmail.com",    "Moreno Odontología",    "meta_ads",         "llamada_agendada",      78, 150000, 10),
        ("Federico", "Álvarez",    "+5491155001011", "federico.alvarez@outlook.com", "Álvarez Abogados",      "whatsapp_inbound", "llamada_agendada",      80, 300000,  8),
        # 2x negociacion
        ("María",    "Torres",     "+5491155001012", "maria.torres@gmail.com",       "Torres Catering",       "meta_ads",         "negociacion",           85, 250000, 14),
        ("Andrés",   "Ruiz",       "+5491155001013", "andres.ruiz@empresa.com.ar",   "Ruiz Distribuciones",   "csv_import",       "negociacion",           90, 500000, 12),
        # 1x cerrado_ganado
        ("Paula",    "Herrera",    "+5491155001014", "paula.herrera@gmail.com",       "Herrera Clínica Vet",   "whatsapp_inbound", "cerrado_ganado",        95, 180000, 20),
        # 1x cerrado_perdido
        ("Diego",    "Giménez",    "+5491155001015", "diego.gimenez@hotmail.com",    "Giménez Automotores",   "meta_ads",         "cerrado_perdido",       25, 400000, 18),
        # 2x sin_respuesta
        ("Laura",    "Medina",     "+5491155001016", "laura.medina@gmail.com",       "Medina Spa",            "whatsapp_inbound", "sin_respuesta",         20, 60000,  15),
        ("Joaquín",  "Peralta",    "+5491155001017", "joaquin.peralta@yahoo.com.ar", "Peralta Gym",           "meta_ads",         "sin_respuesta",         18, 45000,  11),
        # 1x seguimiento_pendiente
        ("Sofía",    "Acosta",     "+5491155001018", "sofia.acosta@gmail.com",       "Acosta Estética",       "whatsapp_inbound", "seguimiento_pendiente", 60, 90000,  16),
    ]

    created_ids = []
    for (first, last, phone, email, company, source, status, score, est_value, days_ago) in demo_leads:
        created_at = now - timedelta(days=days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))
        # Pick 1-2 random tags
        lead_tags = random.sample(available_tags, min(random.randint(1, 2), len(available_tags))) if available_tags else []
        tags_json = f'[{",".join(f""""{t}" """ .strip() for t in lead_tags)}]'

        try:
            lead_id = await db.fetchval(
                """
                INSERT INTO leads (tenant_id, phone_number, first_name, last_name, email, company,
                                   status, source, score, estimated_value, tags,
                                   assigned_seller_id, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb, $12, $13, $13)
                ON CONFLICT (tenant_id, phone_number) DO NOTHING
                RETURNING id
                """,
                tenant_id, phone, first, last, email, company,
                status, source, score, est_value,
                f'[{",".join(chr(34) + t + chr(34) for t in lead_tags)}]',
                seller_user_id, created_at,
            )
            if lead_id:
                created_ids.append({"id": str(lead_id), "name": f"{first} {last}", "status": status})
        except Exception as e:
            logger.error(f"Error seeding lead {first} {last}: {e}")

    # Create lead_notes for the "negociacion" leads
    negociacion_leads = [l for l in created_ids if l["status"] == "negociacion"]
    notes_created = 0
    for lead_info in negociacion_leads:
        note_content = (
            f"El lead {lead_info['name']} mostró interés fuerte en el plan premium. "
            "Pidió descuento del 10% si cierra antes de fin de mes. Seguir contacto."
            if notes_created == 0 else
            f"Llamada con {lead_info['name']}: están comparando con la competencia. "
            "Necesitan propuesta formal con precios y condiciones de pago."
        )
        try:
            await db.pool.execute(
                """
                INSERT INTO lead_notes (tenant_id, lead_id, author_id, note_type, content, visibility, created_at)
                VALUES ($1, $2::uuid, $3::uuid, 'internal', $4, 'all', NOW())
                """,
                tenant_id, lead_info["id"], seller_user_id, note_content,
            )
            notes_created += 1
        except Exception as e:
            logger.warning(f"Could not create note for lead {lead_info['id']}: {e}")

    # Try to create seller_agenda_events for "llamada_agendada" leads
    agendada_leads = [l for l in created_ids if l["status"] == "llamada_agendada"]
    events_created = 0
    if seller_row:
        for i, lead_info in enumerate(agendada_leads):
            event_start = now + timedelta(days=i + 1, hours=10)
            event_end = event_start + timedelta(minutes=30)
            try:
                await db.pool.execute(
                    """
                    INSERT INTO seller_agenda_events (tenant_id, seller_id, title, start_datetime, end_datetime, lead_id, status)
                    VALUES ($1, $2, $3, $4, $5, $6::uuid, 'scheduled')
                    """,
                    tenant_id, seller_row["seller_id"],
                    f"Llamada con {lead_info['name']}",
                    event_start, event_end, lead_info["id"],
                )
                events_created += 1
            except Exception as e:
                logger.warning(f"Could not create agenda event for lead {lead_info['id']}: {e} (professionals table may be missing)")

    return {
        "success": True,
        "tenant_id": tenant_id,
        "summary": {
            "leads_created": len(created_ids),
            "notes_created": notes_created,
            "events_created": events_created,
        },
        "leads": created_ids,
    }
