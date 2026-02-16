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
from core.security import verify_admin_token, get_resolved_tenant_id, get_allowed_tenant_ids, ADMIN_TOKEN
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
    calendar_provider: Optional[str] = None  # 'local' | 'google'

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
async def get_pending_users(user_data = Depends(verify_admin_token)):
    if user_data.role not in ['ceo', 'secretary']: raise HTTPException(status_code=403, detail="Forbidden")
    users = await db.fetch("SELECT id, email, role, status, created_at, first_name, last_name FROM users WHERE status = 'pending' ORDER BY created_at DESC")
    return [dict(u) for u in users]

@router.get("/users", tags=["Usuarios"])
async def get_all_users(user_data = Depends(verify_admin_token)):
    if user_data.role not in ['ceo', 'secretary']: raise HTTPException(status_code=403, detail="Forbidden")
    users = await db.fetch("SELECT id, email, role, status, created_at, updated_at, first_name, last_name FROM users ORDER BY status ASC, created_at DESC")
    return [dict(u) for u in users]

@router.post("/users/{user_id}/status", tags=["Usuarios"])
async def update_user_status(user_id: str, payload: StatusUpdate, user_data = Depends(verify_admin_token)):
    if user_data.role != 'ceo': raise HTTPException(status_code=403, detail="CEO only")
    await db.execute("UPDATE users SET status = $1, updated_at = NOW() WHERE id = $2", payload.status, user_id)
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
    business_number = os.getenv("YCLOUD_Phone_Number_ID") or "default"
    background_tasks.add_task(send_to_whatsapp_task, payload.phone, payload.message, business_number)
    return {"status": "sent", "correlation_id": correlation_id}

@router.put("/chat/sessions/{phone}/read", dependencies=[Depends(verify_admin_token)], tags=["Chat"])
async def mark_chat_session_read(phone: str, tenant_id: int, allowed_ids: List[int] = Depends(get_allowed_tenant_ids)):
    if tenant_id not in allowed_ids: raise HTTPException(status_code=403)
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
    try:
        rows = await db.pool.fetch("""
            SELECT l.id, TRIM(COALESCE(l.first_name,'') || ' ' || COALESCE(l.last_name,'')) as lead_name, l.phone_number as phone,
                   'NORMAL' as urgency_level, 'Lead reciente' as reason, l.updated_at as timestamp
            FROM leads l WHERE l.tenant_id = $1 ORDER BY l.updated_at DESC NULLS LAST LIMIT $2
        """, tenant_id, limit)
        return [
            {"id": str(r["id"]), "patient_name": r["lead_name"], "phone": r["phone"], "urgency_level": r["urgency_level"], "reason": r["reason"], "timestamp": r["timestamp"].strftime("%d/%m %H:%M") if r.get("timestamp") and hasattr(r["timestamp"], "strftime") else str(r.get("timestamp") or "")}
            for r in rows
        ]
    except Exception as e:
        logger.error(f"Error fetching urgencies: {e}")
        return []

# --- RUTAS DE CONFIGURACIÓN / TENANTS ---
@router.get("/tenants", tags=["Sedes"])
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
async def update_clinic_settings(payload: ClinicSettingsUpdate, resolved_tenant_id: int = Depends(get_resolved_tenant_id)):
    if payload.ui_language:
        await db.pool.execute("UPDATE tenants SET config = jsonb_set(COALESCE(config, '{}'), '{ui_language}', to_jsonb($1::text)) WHERE id = $2", payload.ui_language, resolved_tenant_id)
    # Single-niche: only crm_sales; ignore niche_type changes from client
    out = {"status": "ok"}
    return out

@router.get("/internal/credentials/{name}", tags=["Internal"])
async def get_internal_credential(name: str, x_internal_token: str = Header(None)):
    if x_internal_token != INTERNAL_API_TOKEN: raise HTTPException(status_code=401)
    val = os.getenv(name)
    if not val: raise HTTPException(status_code=404)
    return {"name": name, "value": val}

@router.get("/config/deployment", dependencies=[Depends(verify_admin_token)], tags=["Configuración"])
async def get_deployment_config(request: Request):
    host = request.headers.get("host", "localhost:8000")
    base_url = f"https://{host}"
    return {"orchestrator_url": base_url, "environment": os.getenv("ENVIRONMENT", "development")}
