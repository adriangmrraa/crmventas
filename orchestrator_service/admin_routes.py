import os
import uuid
import json
import logging
import httpx
from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks, Header
from pydantic import BaseModel

from db import db
from core.credentials import (
    get_tenant_credential, save_tenant_credential, 
    YCLOUD_API_KEY, YCLOUD_WEBHOOK_SECRET
)
from core.security import verify_admin_token, get_resolved_tenant_id, get_allowed_tenant_ids, ADMIN_TOKEN, audit_access
from core.utils import normalize_phone, ARG_TZ

from core.services.chat_service import ChatService

logger = logging.getLogger(__name__)

# Configuración
INTERNAL_API_TOKEN = os.getenv("INTERNAL_API_TOKEN", "internal-secret-token")
WHATSAPP_SERVICE_URL = os.getenv("WHATSAPP_SERVICE_URL", "http://whatsapp:8002")

router = APIRouter(prefix="/admin/core", tags=["Core Admin"])

# ... (MODELS and HELPERS remain unchanged) ...

# --- MODELS ---
class StatusUpdate(BaseModel):
    status: str

class HumanInterventionToggle(BaseModel):
    phone: str
    tenant_id: int
    activate: bool
    duration: Optional[int] = 86400000

class ChatSendMessage(BaseModel):
    phone: str
    tenant_id: int
    message: str

class ClinicSettingsUpdate(BaseModel):
    ui_language: Optional[str] = None
    niche_type: Optional[str] = None  # 'dental' | 'crm_sales' — switches tenant mode and UI

class TenantUpdate(BaseModel):
    clinic_name: Optional[str] = None
    bot_phone_number: Optional[str] = None
    calendar_provider: Optional[str] = None  # 'local' | 'google' — stored in config

class TenantCreate(BaseModel):
    clinic_name: str
    bot_phone_number: str
    calendar_provider: Optional[str] = None

class CredentialItem(BaseModel):
    name: str
    value: str
    category: str = "general"

class IntegrationPayload(BaseModel):
    ycloud_api_key: Optional[str] = None
    ycloud_webhook_secret: Optional[str] = None  # 'local' | 'google'

# --- HELPERS ---
async def emit_appointment_event(event_type: str, data: Dict[str, Any], request: Request):
    if hasattr(request.app.state, 'emit_appointment_event'):
        await request.app.state.emit_appointment_event(event_type, data)

async def send_to_whatsapp_task(phone: str, message: str, business_number: str):
    normalized = normalize_phone(phone)
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            await client.post(
                f"{WHATSAPP_SERVICE_URL}/send",
                json={"to": normalized, "message": message},
                headers={"X-Internal-Token": INTERNAL_API_TOKEN, "X-Correlation-Id": str(uuid.uuid4())},
                params={"from_number": business_number}
            )
    except Exception as e:
        logger.error(f"WhatsApp send failed: {e}")

# --- RUTAS DE USUARIOS ---
@router.get("/users/pending", tags=["Usuarios"])
@audit_access("read_pending_users")
async def get_pending_users(user_data = Depends(verify_admin_token)):
    if user_data.role not in ['ceo', 'secretary']: raise HTTPException(status_code=403, detail="Forbidden")
    users = await db.fetch("SELECT id, email, role, status, created_at, first_name, last_name FROM users WHERE status = 'pending' ORDER BY created_at DESC")
    return [dict(u) for u in users]

@router.get("/users", tags=["Usuarios"])
@audit_access("list_users")
async def get_all_users(user_data = Depends(verify_admin_token)):
    if user_data.role not in ['ceo', 'secretary']: raise HTTPException(status_code=403, detail="Forbidden")
    users = await db.fetch("SELECT id, email, role, status, created_at, updated_at, first_name, last_name FROM users ORDER BY status ASC, created_at DESC")
    return [dict(u) for u in users]

@router.post("/users/{user_id}/status", tags=["Usuarios"])
@audit_access("update_user_status", resource_param="user_id")
async def update_user_status(user_id: str, payload: StatusUpdate, user_data = Depends(verify_admin_token)):
    if user_data.role != 'ceo': raise HTTPException(status_code=403, detail="CEO only")
    
    # Update user status
    await db.execute("UPDATE users SET status = $1, updated_at = NOW() WHERE id = $2", payload.status, user_id)
    
    # Activation logic for Sellers/Professionals
    if payload.status == 'active':
        uid = uuid.UUID(user_id)
        user = await db.fetchrow("SELECT first_name, last_name, email, role, tenant_id FROM users WHERE id = $1", user_id)
        
        if user:
            # Roles elegibles para el módulo de ventas
            SELLER_ROLES = ('seller', 'closer', 'setter', 'secretary', 'ceo', 'professional')
            
            if user['role'] in SELLER_ROLES:
                # Upsert en sellers
                await db.pool.execute("""
                    INSERT INTO sellers (user_id, tenant_id, first_name, last_name, email, is_active, updated_at)
                    VALUES ($1, $2, $3, $4, $5, TRUE, NOW())
                    ON CONFLICT (user_id) DO UPDATE 
                    SET is_active = TRUE, 
                        updated_at = NOW(),
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        email = EXCLUDED.email
                """, uid, user['tenant_id'], user['first_name'], user['last_name'], user['email'])
            
            # Activate in professionals (Legacy/Dental fallback)
            if user['role'] == 'professional':
                await db.pool.execute("UPDATE professionals SET is_active = TRUE, updated_at = NOW() WHERE user_id = $1", uid)
        
    return {"status": "updated"}

# --- RUTAS DE CHAT ---
@router.get("/chat/tenants", dependencies=[Depends(verify_admin_token)], tags=["Chat"])
async def get_chat_tenants(allowed_ids: List[int] = Depends(get_allowed_tenant_ids)):
    if not allowed_ids: return []
    rows = await db.pool.fetch("SELECT id, clinic_name FROM tenants WHERE id = ANY($1::int[]) ORDER BY id ASC", allowed_ids)
    return [{"id": r["id"], "clinic_name": r["clinic_name"]} for r in rows]

@router.get("/chat/sessions", dependencies=[Depends(verify_admin_token)], tags=["Chat"])
async def get_chat_sessions(tenant_id: int, allowed_ids: List[int] = Depends(get_allowed_tenant_ids)):
    if tenant_id not in allowed_ids: raise HTTPException(status_code=403)
    # Abstraction: Use ChatService to get sessions (resolves patients/leads internally)
    return await ChatService.get_chat_sessions(tenant_id)

@router.get("/chat/messages/{phone}", dependencies=[Depends(verify_admin_token)], tags=["Chat"])
async def get_chat_messages(phone: str, tenant_id: int, limit: int = 50, offset: int = 0, allowed_ids: List[int] = Depends(get_allowed_tenant_ids)):
    if tenant_id not in allowed_ids: raise HTTPException(status_code=403)
    rows = await db.pool.fetch("SELECT * FROM chat_messages WHERE from_number = $1 AND tenant_id = $2 ORDER BY created_at DESC LIMIT $3 OFFSET $4", phone, tenant_id, limit, offset)
    return sorted([dict(r) | {"created_at": str(r["created_at"])} for r in rows], key=lambda x: x['created_at'])

@router.post("/chat/send", dependencies=[Depends(verify_admin_token)], tags=["Chat"])
async def send_chat_message(payload: ChatSendMessage, request: Request, background_tasks: BackgroundTasks, allowed_ids: List[int] = Depends(get_allowed_tenant_ids)):
    if payload.tenant_id not in allowed_ids: raise HTTPException(status_code=403)
    correlation_id = str(uuid.uuid4())
    await db.append_chat_message(from_number=payload.phone, role="assistant", content=payload.message, correlation_id=correlation_id, tenant_id=payload.tenant_id)
    # B-03: Obtener bot_phone_number del tenant (multi-tenant)
    tenant_row = await db.pool.fetchrow(
        "SELECT bot_phone_number FROM tenants WHERE id = $1", payload.tenant_id
    )
    business_number = (
        tenant_row["bot_phone_number"]
        if tenant_row and tenant_row["bot_phone_number"]
        else os.getenv("YCLOUD_Phone_Number_ID") or ""
    )
    if not business_number:
        raise HTTPException(status_code=400, detail="No hay número de WhatsApp configurado para este tenant.")
    background_tasks.add_task(send_to_whatsapp_task, payload.phone, payload.message, business_number)
    return {"status": "sent", "correlation_id": correlation_id}

@router.put("/chat/sessions/{phone}/read", dependencies=[Depends(verify_admin_token)], tags=["Chat"])
async def mark_chat_session_read(phone: str, tenant_id: int, allowed_ids: List[int] = Depends(get_allowed_tenant_ids)):
    if tenant_id not in allowed_ids: raise HTTPException(status_code=403)
    # C-02: Persistir lectura en DB — actualiza updated_at del lead
    norm_phone = normalize_phone(phone)
    await db.pool.execute("""
        UPDATE leads SET updated_at = NOW()
        WHERE tenant_id = $1 AND (phone_number = $2 OR phone_number = $3)
    """, tenant_id, norm_phone, phone)
    return {"status": "ok", "phone": phone, "tenant_id": tenant_id}

@router.post("/chat/human-intervention", dependencies=[Depends(verify_admin_token)], tags=["Chat"])
async def toggle_human_intervention(payload: HumanInterventionToggle, request: Request, allowed_ids: List[int] = Depends(get_allowed_tenant_ids)):
    if payload.tenant_id not in allowed_ids: raise HTTPException(status_code=403)
    norm_phone = normalize_phone(payload.phone)
    if payload.activate:
        override_until = datetime.now(ARG_TZ) + timedelta(milliseconds=payload.duration or 86400000)
        await db.pool.execute("""
            UPDATE leads SET human_handoff_requested = TRUE, human_override_until = $1, updated_at = NOW()
            WHERE tenant_id = $2 AND (phone_number = $3 OR phone_number = $4)
        """, override_until, payload.tenant_id, norm_phone, payload.phone)
        await emit_appointment_event("HUMAN_OVERRIDE_CHANGED", {"phone_number": payload.phone, "tenant_id": payload.tenant_id, "enabled": True, "until": override_until.isoformat()}, request)
        return {"status": "activated", "phone": payload.phone, "tenant_id": payload.tenant_id, "until": override_until.isoformat()}
    else:
        await db.pool.execute("""
            UPDATE leads SET human_handoff_requested = FALSE, human_override_until = NULL, updated_at = NOW()
            WHERE tenant_id = $1 AND (phone_number = $2 OR phone_number = $3)
        """, payload.tenant_id, norm_phone, payload.phone)
        await emit_appointment_event("HUMAN_OVERRIDE_CHANGED", {"phone_number": payload.phone, "tenant_id": payload.tenant_id, "enabled": False}, request)
        return {"status": "deactivated", "phone": payload.phone, "tenant_id": payload.tenant_id}

class RemoveSilencePayload(BaseModel):
    phone: str
    tenant_id: int

@router.post("/chat/remove-silence", dependencies=[Depends(verify_admin_token)], tags=["Chat"])
async def remove_silence(payload: RemoveSilencePayload, request: Request, allowed_ids: List[int] = Depends(get_allowed_tenant_ids)):
    if payload.tenant_id not in allowed_ids: raise HTTPException(status_code=403)
    norm_phone = normalize_phone(payload.phone)
    await db.pool.execute("""
        UPDATE leads SET human_handoff_requested = FALSE, human_override_until = NULL, updated_at = NOW()
        WHERE tenant_id = $1 AND (phone_number = $2 OR phone_number = $3)
    """, payload.tenant_id, norm_phone, payload.phone)
    await emit_appointment_event("HUMAN_OVERRIDE_CHANGED", {"phone_number": payload.phone, "tenant_id": payload.tenant_id, "enabled": False}, request)
    return {"status": "removed", "phone": payload.phone, "tenant_id": payload.tenant_id}

# --- DASHBOARD (paridad Clínicas) ---
@router.get("/stats/summary", tags=["Estadísticas"])
async def get_dashboard_stats(
    range: str = "weekly",
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    days = 7 if range == "weekly" else 30
    try:
        ia_conversations = await db.pool.fetchval("""
            SELECT COUNT(DISTINCT m.from_number) FROM chat_messages m
            JOIN leads l ON m.from_number = l.phone_number AND l.tenant_id = m.tenant_id
            WHERE m.tenant_id = $1 AND m.created_at >= CURRENT_DATE - INTERVAL '1 day' * $2
        """, tenant_id, days) or 0
        ia_events = await db.pool.fetchval("""
            SELECT COUNT(*) FROM seller_agenda_events e
            WHERE e.tenant_id = $1 AND e.start_datetime >= CURRENT_DATE - INTERVAL '1 day' * $2
        """, tenant_id, days) or 0
        growth_rows = await db.pool.fetch("""
            SELECT DATE(start_datetime) as date, COUNT(*) as completed_events
            FROM seller_agenda_events WHERE tenant_id = $1 AND start_datetime >= CURRENT_DATE - INTERVAL '1 day' * $2
            GROUP BY DATE(start_datetime) ORDER BY date ASC
        """, tenant_id, days)
        growth_data = [{"date": (r["date"].strftime("%Y-%m-%d") if hasattr(r["date"], "strftime") else str(r["date"])), "ia_referrals": 0, "completed_appointments": r["completed_events"]} for r in growth_rows]
        if not growth_data:
            growth_data = [{"date": date.today().isoformat(), "ia_referrals": 0, "completed_appointments": 0}]
        return {
            "ia_conversations": ia_conversations,
            "ia_appointments": ia_events,
            "active_urgencies": 0,
            "total_revenue": 0.0,
            "growth_data": growth_data,
        }
    except Exception as e:
        logger.error(f"Error en get_dashboard_stats: {e}")
        raise HTTPException(status_code=500, detail="Error al cargar estadísticas.")

@router.get("/chat/urgencies", dependencies=[Depends(verify_admin_token)], tags=["Chat"])
async def get_recent_urgencies(limit: int = 10, tenant_id: int = Depends(get_resolved_tenant_id)):
    # C-01: Solo retorna leads con human_handoff_requested = TRUE (intervención humana activa)
    try:
        rows = await db.pool.fetch("""
            SELECT l.id, TRIM(COALESCE(l.first_name,'') || ' ' || COALESCE(l.last_name,'')) as lead_name, l.phone_number as phone,
                   'URGENT' as urgency_level, 'Intervención humana activa' as reason, l.updated_at as timestamp
            FROM leads l
            WHERE l.tenant_id = $1 AND l.human_handoff_requested = TRUE
            ORDER BY l.updated_at DESC NULLS LAST LIMIT $2
        """, tenant_id, limit)
        return [
            {"id": str(r["id"]), "lead_name": r["lead_name"], "phone": r["phone"], "urgency_level": r["urgency_level"], "reason": r["reason"], "timestamp": r["timestamp"].strftime("%d/%m %H:%M") if r.get("timestamp") and hasattr(r["timestamp"], "strftime") else str(r.get("timestamp") or "")}
            for r in rows
        ]
    except Exception as e:
        logger.error(f"Error fetching urgencies: {e}")
        return []

# --- RUTAS DE CONFIGURACIÓN / TENANTS ---
@router.get("/tenants", tags=["Sedes"])
@audit_access("list_tenants")
async def get_tenants(user_data=Depends(verify_admin_token)):
    if user_data.role != 'ceo': raise HTTPException(status_code=403)
    rows = await db.pool.fetch("SELECT id, clinic_name, bot_phone_number, config FROM tenants ORDER BY id ASC")
    return [dict(r) for r in rows]

@router.put("/tenants/{tenant_id}", tags=["Sedes"])
async def update_tenant(tenant_id: int, payload: TenantUpdate, user_data=Depends(verify_admin_token)):
    if user_data.role != 'ceo': raise HTTPException(status_code=403)
    existing = await db.pool.fetchrow("SELECT id FROM tenants WHERE id = $1", tenant_id)
    if not existing: raise HTTPException(status_code=404, detail="Tenant not found")
    updates, params = [], []
    pos = 1
    if payload.clinic_name is not None:
        updates.append(f"clinic_name = ${pos}"); params.append(payload.clinic_name); pos += 1
    if payload.bot_phone_number is not None:
        updates.append(f"bot_phone_number = ${pos}"); params.append(payload.bot_phone_number); pos += 1
    if payload.calendar_provider is not None and payload.calendar_provider in ("local", "google"):
        updates.append("config = jsonb_set(COALESCE(config, '{}'), '{calendar_provider}', to_jsonb($%s::text))" % pos)
        params.append(payload.calendar_provider); pos += 1
    if not updates:
        return {"status": "ok"}
    params.append(tenant_id)
    query = "UPDATE tenants SET " + ", ".join(updates) + f", updated_at = NOW() WHERE id = ${pos}"
    await db.pool.execute(query, *params)
    return {"status": "ok"}

@router.post("/tenants", tags=["Sedes"])
@audit_access("create_tenant")
async def create_tenant(payload: TenantCreate, user_data=Depends(verify_admin_token)):
    if user_data.role != 'ceo': raise HTTPException(status_code=403)
    cp = payload.calendar_provider if payload.calendar_provider in ("local", "google") else "local"
    config = json.dumps({"calendar_provider": cp})
    try:
        await db.pool.execute(
            "INSERT INTO tenants (clinic_name, bot_phone_number, config) VALUES ($1, $2, $3::jsonb)",
            payload.clinic_name, payload.bot_phone_number, config
        )
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=400, detail="bot_phone_number already in use")
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "created"}

@router.delete("/tenants/{tenant_id}", tags=["Sedes"])
@audit_access("delete_tenant", resource_param="tenant_id")
async def delete_tenant(tenant_id: int, user_data=Depends(verify_admin_token)):
    if user_data.role != 'ceo': raise HTTPException(status_code=403)
    existing = await db.pool.fetchrow("SELECT id FROM tenants WHERE id = $1", tenant_id)
    if not existing: raise HTTPException(status_code=404, detail="Tenant not found")
    count = await db.pool.fetchval("SELECT COUNT(*) FROM tenants")
    if count <= 1: raise HTTPException(status_code=400, detail="Cannot delete the last tenant")
    await db.pool.execute("DELETE FROM tenants WHERE id = $1", tenant_id)
    return {"status": "deleted"}

def _config_as_dict(config):  # config from DB can be dict (JSONB) or str
    if config is None:
        return {}
    if isinstance(config, dict):
        return config
    if isinstance(config, str):
        try:
            return json.loads(config) if config.strip() else {}
        except (json.JSONDecodeError, AttributeError):
            return {}
    return {}


@router.get("/settings/clinic", dependencies=[Depends(verify_admin_token)], tags=["Configuración"])
@audit_access("view_settings")
async def get_clinic_settings(resolved_tenant_id: int = Depends(get_resolved_tenant_id)):
    row = await db.pool.fetchrow(
        "SELECT clinic_name, config, COALESCE(niche_type, 'crm_sales') AS niche_type FROM tenants WHERE id = $1",
        resolved_tenant_id
    )
    if not row: return {}
    config = _config_as_dict(row.get("config"))
    return {
        "name": row["clinic_name"],
        "ui_language": config.get("ui_language", "en"),
        "niche_type": row["niche_type"] or "crm_sales",
    }

@router.patch("/settings/clinic", dependencies=[Depends(verify_admin_token)], tags=["Configuración"])
@audit_access("update_settings")
async def update_clinic_settings(payload: ClinicSettingsUpdate, resolved_tenant_id: int = Depends(get_resolved_tenant_id)):
    if payload.ui_language:
        await db.pool.execute("UPDATE tenants SET config = jsonb_set(COALESCE(config, '{}'::jsonb), '{ui_language}', to_jsonb($1::text)) WHERE id = $2", payload.ui_language, resolved_tenant_id)
    # Single-niche: only crm_sales; ignore niche_type changes from client
    out = {"status": "ok"}
    return out

@router.get("/internal/credentials/{name}", tags=["Internal"])
async def get_internal_credential(name: str, tenant_id: Optional[int] = None, x_internal_token: str = Header(None)):
    if x_internal_token != INTERNAL_API_TOKEN: raise HTTPException(status_code=401, detail="Internal token invalid")
    
    # Nexus Isolation: Credential must belong to a tenant context
    actual_tenant_id = tenant_id if tenant_id is not None else 1
    
    val = await get_tenant_credential(actual_tenant_id, name)
        
    if not val: 
        raise HTTPException(status_code=404, detail=f"Credential {name} not found for tenant {actual_tenant_id}")
        
    return {"name": name, "value": val}


@router.get("/config/deployment", dependencies=[Depends(verify_admin_token)], tags=["Configuración"])
async def get_deployment_config(request: Request):
    """Retorna la configuración de despliegue, incluyendo URLs de webhooks para integración externa."""
    # Intentamos obtener protocol y host desde las cabeceras (cuando se usa proxy reverso)
    protocol = "https" if request.headers.get("x-forwarded-proto") == "https" else "http"
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or getattr(request.url, "netloc", "localhost:8000")
    
    # URL base para webhooks dinámicos (usualmente el dominio público)
    # Permite override manual de la URL mediante la variable de entorno PUBLIC_WEBHOOK_URL
    public_webhook_url = os.getenv("PUBLIC_WEBHOOK_URL")
    if public_webhook_url:
        base_url = public_webhook_url.rstrip('/')
    else:
        base_url = f"{protocol}://{host}"
    
    return {
        "webhook_ycloud_url": f"{base_url}/webhook/ycloud",
        "webhook_meta_url": f"{base_url}/webhooks/meta",
        "orchestrator_url": base_url,
        "environment": os.getenv("ENVIRONMENT", "production")
    }

# --- CREDENTIALS MANAGEMENT (Otras & YCloud Tabs) ---

@router.get("/credentials", dependencies=[Depends(verify_admin_token)], tags=["Configuración"])
async def get_credentials(tenant_id_filter: Optional[int] = None, include_integrations: bool = False, user_data=Depends(verify_admin_token)):
    """Retorna las credenciales genéricas (category != 'integration' por defecto). CEO ve todas o filtra por tenant_id."""
    # Validación de acceso basada en rol
    role = user_data.role
    user_tenant = user_data.tenant_id
    
    query = "SELECT id, tenant_id, name, '***' as value, category, updated_at FROM credentials WHERE 1=1"
    if not include_integrations:
        query += " AND category != 'integration'"
        
    params = []
    
    if role == "ceo":
        # CEO puede ver todo, o filtrar si pasa tenant_id_filter
        if tenant_id_filter:
            params.append(tenant_id_filter)
            query += f" AND tenant_id = ${len(params)}"
    else:
        # Secretary / Professional solo ven las de su tenant
        params.append(user_tenant)
        query += f" AND tenant_id = ${len(params)}"
        
    query += " ORDER BY tenant_id ASC, name ASC"
    
    rows = await db.pool.fetch(query, *params)
    return [dict(r) for r in rows]

@router.post("/credentials", dependencies=[Depends(verify_admin_token)], tags=["Configuración"])
async def save_credential(payload: CredentialItem, tenant_id: int = Depends(get_resolved_tenant_id), user_data=Depends(verify_admin_token)):
    """Guarda o actualiza una credencial cruda para un tenant. Solo para la pestaña 'Otras'."""
    if user_data.role != "ceo":
        raise HTTPException(status_code=403, detail="Forbidden")
        
    try:
        await save_tenant_credential(tenant_id, payload.name, payload.value, payload.category)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving credential: {str(e)}")

@router.delete("/credentials/{cred_id}", dependencies=[Depends(verify_admin_token)], tags=["Configuración"])
async def delete_credential(cred_id: int, user_data=Depends(verify_admin_token), tenant_id: int = Depends(get_resolved_tenant_id)):
    """Elimina una credencial específica por su ID. Validado por tenant_id a menos que sea CEO."""
    role = user_data.role
    
    if role == "ceo":
        result = await db.pool.execute("DELETE FROM credentials WHERE id = $1", cred_id)
    else:
        result = await db.pool.execute("DELETE FROM credentials WHERE id = $1 AND tenant_id = $2", cred_id, tenant_id)
        
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Credential not found or access denied")
    return {"status": "ok"}

@router.get("/settings/integration/{provider}/{tenant_id}", dependencies=[Depends(verify_admin_token)], tags=["Configuración"])
async def get_integration_settings(provider: str, tenant_id: str, user_data=Depends(verify_admin_token), resolved_tenant: int = Depends(get_resolved_tenant_id)):
    """Obtiene la configuración específica de una integración (ej. YCloud). tenant_id puede ser 'global' o numérico."""
    # Validación de acceso (CEO vs Otros) - Manejo de 'global'
    actual_tenant_id = None
    if tenant_id != "global":
        try:
            actual_tenant_id = int(tenant_id)
            if user_data.role != "ceo" and actual_tenant_id != resolved_tenant:
                raise HTTPException(status_code=403, detail="Forbidden")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid tenant_id")
    else:
        if user_data.role != "ceo":
             raise HTTPException(status_code=403, detail="Only CEO can access global integration settings")

    if provider == "ycloud":
        # target_tenant_id is None if 'global', else the integer ID
        api_key = await get_tenant_credential(actual_tenant_id, YCLOUD_API_KEY)
        webhook_secret = await get_tenant_credential(actual_tenant_id, YCLOUD_WEBHOOK_SECRET)
        
        return {
            "ycloud_api_key": "***" if api_key else "",
            "ycloud_webhook_secret": "***" if webhook_secret else ""
        }
    else:
        raise HTTPException(status_code=400, detail="Provider not supported")

@router.post("/settings/integration/{provider}/{tenant_id}", dependencies=[Depends(verify_admin_token)], tags=["Configuración"])
async def save_integration_settings(provider: str, tenant_id: str, payload: IntegrationPayload, user_data=Depends(verify_admin_token), resolved_tenant: int = Depends(get_resolved_tenant_id)):
    """Guarda configuración específica de YCloud u otro provider para un tenant dado."""
    actual_tenant_id = None
    if tenant_id != "global":
        try:
            actual_tenant_id = int(tenant_id)
            if user_data.role != "ceo" and actual_tenant_id != resolved_tenant:
                raise HTTPException(status_code=403, detail="Forbidden")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid tenant_id")
    else:
        if user_data.role != "ceo":
             raise HTTPException(status_code=403, detail="Only CEO can save global integration settings")

    if provider == "ycloud":
        try:
            if payload.ycloud_api_key and payload.ycloud_api_key != "***":
                await save_tenant_credential(actual_tenant_id, YCLOUD_API_KEY, payload.ycloud_api_key, "integration")
            if payload.ycloud_webhook_secret and payload.ycloud_webhook_secret != "***":
                await save_tenant_credential(actual_tenant_id, YCLOUD_WEBHOOK_SECRET, payload.ycloud_webhook_secret, "integration")
            return {"status": "ok"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail="Provider not supported or missing tenant_id")

# --- MANTENIMIENTO ---

@router.post("/maintenance/clean-media", dependencies=[Depends(verify_admin_token)], tags=["Mantenimiento"])
async def clean_media(request: Request, user_data=Depends(verify_admin_token)):
    """Mock endpoint para el botón de limpieza de archivos en UI. (No-op por ahora al no usar Chatwoot local storage exhaustivo)"""
    if user_data.get("role") != "ceo":
        raise HTTPException(status_code=403, detail="Only CEO can run maintenance tasks")
        
    return {"status": "ok", "message": "Limpieza de archivos completada exitosamente. (Mock)"}


@router.get("/audit/logs", tags=["Seguridad"])
async def get_audit_logs(
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Obtiene logs de auditoría (solo CEO).
    """
    if user_data.role != 'ceo':
        raise HTTPException(status_code=403, detail="Acceso denegado: Solo CEOs pueden consultar auditoría.")
    
    query = """
        SELECT id, event_type, severity, message, payload, occurred_at
        FROM system_events
        WHERE 1=1
    """
    params = []
    
    if event_type:
        query += f" AND event_type = ${len(params)+1}"
        params.append(event_type)
    
    if severity:
        query += f" AND severity = ${len(params)+1}"
        params.append(severity)
    
    query += f" ORDER BY occurred_at DESC LIMIT ${len(params)+1} OFFSET ${len(params)+2}"
    params.extend([limit, offset])
    
    try:
        logs = await db.pool.fetch(query, *params)
        total = await db.pool.fetchval("SELECT COUNT(*) FROM system_events")
        
        return {
            "logs": [
                {
                    "id": log["id"],
                    "event_type": log["event_type"],
                    "severity": log["severity"],
                    "message": log["message"],
                    "payload": log["payload"],
                    "occurred_at": log["occurred_at"].isoformat() if log["occurred_at"] else None
                }
                for log in logs
            ],
            "total": total
        }
    except Exception as e:
        logger.error(f"Error fetching audit logs: {e}")
        raise HTTPException(status_code=500, detail="Error al consultar logs de auditoría.")
