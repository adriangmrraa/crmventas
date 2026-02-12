import json
import logging
import re
import uuid
from datetime import datetime, timedelta, date, timezone
from typing import Optional, List, Dict, Any

from langchain.tools import tool
from db import db
from gcal_service import gcal_service
from core.context import current_tenant_id, current_customer_phone, current_patient_id
from core.utils import ARG_TZ, normalize_phone
from core.socket_manager import sio
from core.tools import tool_registry

logger = logging.getLogger(__name__)

import os
CLINIC_HOURS_START = os.getenv("CLINIC_HOURS_START", "08:00")
CLINIC_HOURS_END = os.getenv("CLINIC_HOURS_END", "19:00")

# --- Helpers (Local for now to ensure self-containment) ---
def get_now_arg():
    return datetime.now(ARG_TZ)

def get_next_weekday(target_weekday: int) -> date:
    today = get_now_arg()
    days_ahead = target_weekday - today.weekday()
    if days_ahead <= 0: days_ahead += 7
    return (today + timedelta(days=days_ahead)).date()

from dateutil.parser import parse as dateutil_parse

def parse_date(date_query: str) -> date:
    query = date_query.lower().strip()
    today = get_now_arg().date()
    day_map = {
        'mañana': lambda: (get_now_arg() + timedelta(days=1)).date(),
        'tomorrow': lambda: (get_now_arg() + timedelta(days=1)).date(),
        'pasado mañana': lambda: (get_now_arg() + timedelta(days=2)).date(),
        'day after tomorrow': lambda: (get_now_arg() + timedelta(days=2)).date(),
        'hoy': lambda: today, 'today': lambda: today,
        'lunes': lambda: get_next_weekday(0), 'monday': lambda: get_next_weekday(0),
        'martes': lambda: get_next_weekday(1), 'tuesday': lambda: get_next_weekday(1),
        'miércoles': lambda: get_next_weekday(2), 'miercoles': lambda: get_next_weekday(2), 'wednesday': lambda: get_next_weekday(2),
        'jueves': lambda: get_next_weekday(3), 'thursday': lambda: get_next_weekday(3),
        'viernes': lambda: get_next_weekday(4), 'friday': lambda: get_next_weekday(4),
        'sábado': lambda: get_next_weekday(5), 'sabado': lambda: get_next_weekday(5), 'saturday': lambda: get_next_weekday(5),
        'domingo': lambda: get_next_weekday(6), 'sunday': lambda: get_next_weekday(6),
    }
    if "pasado mañana" in query or "day after tomorrow" in query: return (get_now_arg() + timedelta(days=2)).date()
    for key, func in day_map.items():
        if key in query: return func()
    try: return dateutil_parse(query, dayfirst=True).date()
    except: return get_now_arg().date()

def parse_datetime(datetime_query: str) -> datetime:
    query = datetime_query.lower().strip()
    target_date = None
    target_time = (14, 0)
    time_match = re.search(r'(\d{1,2})[:h](\d{2})', query)
    if time_match:
        target_time = (int(time_match.group(1)), int(time_match.group(2)))
    else:
        hour_only = re.search(r'(?:las?\s+)?(\d{1,2})\s*(?:hs?|horas?)?\b', query)
        if hour_only:
            h = int(hour_only.group(1))
            if 0 <= h <= 23: target_time = (h, 0)
        pm_am = re.search(r'(\d{1,2})\s*(am|pm|a\.m\.|p\.m\.)', query, re.IGNORECASE)
        if pm_am:
            h = int(pm_am.group(1))
            is_pm = 'p' in pm_am.group(2).lower()
            if h == 12: target_time = (0, 0) if not is_pm else (12, 0)
            elif is_pm: target_time = (h + 12, 0)
            else: target_time = (h, 0)
    
    words = query.split()
    for word in words:
        try:
            d = parse_date(word)
            if d != get_now_arg().date() or 'hoy' in query or 'today' in query:
                target_date = d
                break
        except: continue
    if not target_date:
        try:
            dt = dateutil_parse(query, dayfirst=True)
            if dt.year > 2000:
                target_date = dt.date()
                if not time_match: target_time = (dt.hour, dt.minute)
        except: target_date = (get_now_arg() + timedelta(days=1)).date()
    
    return datetime.combine(target_date, datetime.min.time()).replace(hour=target_time[0], minute=target_time[1], second=0, microsecond=0, tzinfo=ARG_TZ)

def is_time_in_working_hours(time_str: str, day_config: Dict[str, Any]) -> bool:
    if not day_config.get("enabled", False): return False
    try:
        th, tm = map(int, time_str.split(':'))
        current_m = th * 60 + tm
        for slot in day_config.get("slots", []):
            sh, sm = map(int, slot['start'].split(':'))
            eh, em = map(int, slot['end'].split(':'))
            start_m = sh * 60 + sm
            end_m = eh * 60 + em
            if start_m <= current_m < end_m: return True
    except: pass
    return False

def generate_free_slots(target_date: date, busy_intervals_by_prof: Dict[int, set], start_time_str="09:00", end_time_str="18:00", interval_minutes=30, duration_minutes=30, limit=20, time_preference: Optional[str] = None) -> List[str]:
    slots = []
    try:
        sh, sm = map(int, start_time_str.split(':'))
        eh, em = map(int, end_time_str.split(':'))
    except: sh, sm, eh, em = 9, 0, 18, 0
    current = datetime.combine(target_date, datetime.min.time()).replace(hour=sh, minute=sm, tzinfo=ARG_TZ)
    end_limit = datetime.combine(target_date, datetime.min.time()).replace(hour=eh, minute=em, tzinfo=ARG_TZ)
    now = get_now_arg()
    while current < end_limit:
        if target_date == now.date() and current <= now:
            current += timedelta(minutes=interval_minutes)
            continue
        if time_preference == 'mañana' and current.hour >= 13:
            current += timedelta(minutes=interval_minutes); continue
        if time_preference == 'tarde' and current.hour < 13:
            current += timedelta(minutes=interval_minutes); continue
        if current.hour >= 13 and current.hour < 14 and not time_preference:
            current += timedelta(minutes=interval_minutes); continue
        
        time_needed = current + timedelta(minutes=duration_minutes)
        if time_needed > end_limit:
            current += timedelta(minutes=interval_minutes); continue
        
        any_prof_free = False
        for prof_id, busy_set in busy_intervals_by_prof.items():
            slot_free = True
            check_time = current
            while check_time < time_needed:
                if check_time.strftime("%H:%M") in busy_set:
                    slot_free = False; break
                check_time += timedelta(minutes=30)
            if slot_free:
                any_prof_free = True; break
        if any_prof_free: slots.append(current.strftime("%H:%M"))
        if len(slots) >= limit: break
        current += timedelta(minutes=interval_minutes)
    return slots

def slots_to_ranges(slots: List[str], interval_minutes: int = 30) -> str:
    if not slots: return ""
    try:
        def to_minutes(hhmm: str) -> int: h, m = map(int, hhmm.split(":")); return h * 60 + m
        def to_hhmm(m: int) -> str: h, m = divmod(m, 60); return f"{h:02d}:{m:02d}"
        minutes_list = sorted(set(to_minutes(s) for s in slots))
        ranges = []
        i = 0
        while i < len(minutes_list):
            start = minutes_list[i]
            end = start + interval_minutes
            while i + 1 < len(minutes_list) and minutes_list[i + 1] == end:
                i += 1; end = minutes_list[i] + interval_minutes
            ranges.append((to_hhmm(start), to_hhmm(end)))
            i += 1
        if not ranges: return ""
        if len(ranges) == 1: return f"de {ranges[0][0]} a {ranges[0][1]}"
        return " y ".join(f"de {a} a {b}" for a, b in ranges)
    except: return ", ".join(slots)

def to_json_safe(data):
    if isinstance(data, dict): return {k: to_json_safe(v) for k, v in data.items()}
    elif isinstance(data, list): return [to_json_safe(i) for i in data]
    elif isinstance(data, uuid.UUID): return str(data)
    elif isinstance(data, (datetime, date)): return data.isoformat()
    return data

async def get_tenant_calendar_provider(tenant_id: int) -> str:
    row = await db.pool.fetchrow("SELECT config FROM tenants WHERE id = $1", tenant_id)
    if not row or row.get("config") is None: return "local"
    cfg = row["config"]
    if isinstance(cfg, str):
        try: cfg = json.loads(cfg)
        except: return "local"
    if not isinstance(cfg, dict): return "local"
    cp = (cfg.get("calendar_provider") or "local").lower()
    return cp if cp in ("google", "local") else "local"

# --- TOOLS ---

@tool
async def check_availability(date_query: str, professional_name: Optional[str] = None, treatment_name: Optional[str] = None, time_preference: Optional[str] = None):
    """
    Consulta la disponibilidad REAL de turnos para una fecha. Llamar UNA sola vez por pregunta del paciente.
    date_query: Día a consultar: 'mañana', 'lunes', 'martes', etc.
    professional_name: (Opcional) Nombre del profesional.
    treatment_name: (Opcional) Tratamiento ya definido.
    time_preference: (Opcional) 'mañana' o 'tarde'.
    """
    try:
        tenant_id = current_tenant_id.get()
        logger.info(f"📅 check_availability date={date_query} tenant={tenant_id} prof={professional_name}")
        
        clean_name = re.sub(r'^(dr|dra|doctor|doctora)\.?\s+', '', professional_name or '', flags=re.IGNORECASE).strip()
        
        query = "SELECT p.id, p.first_name, p.last_name, p.google_calendar_id, p.working_hours FROM professionals p INNER JOIN users u ON p.user_id = u.id AND u.role = 'professional' AND u.status = 'active' WHERE p.is_active = true AND p.tenant_id = $1"
        params = [tenant_id]
        if clean_name:
            query += " AND (p.first_name ILIKE $2 OR p.last_name ILIKE $2 OR (p.first_name || ' ' || COALESCE(p.last_name, '')) ILIKE $2)"
            params.append(f"%{clean_name}%")
        
        active_professionals = await db.pool.fetch(query, *params)
        if not active_professionals:
            return "❌ No encontré profesionales disponibles con ese criterio."

        target_date = parse_date(date_query)
        if target_date.weekday() == 6: return "La clínica está cerrada los domingos."

        duration = 30
        if treatment_name:
            t_data = await db.pool.fetchrow("SELECT default_duration_minutes FROM treatment_types WHERE tenant_id=$1 AND (name ILIKE $2 OR code ILIKE $2) AND is_active=true AND is_available_for_booking=true LIMIT 1", tenant_id, f"%{treatment_name}%")
            if t_data: duration = t_data['default_duration_minutes']
            else: return "Tratamiento no encontrado."

        calendar_provider = await get_tenant_calendar_provider(tenant_id)

        # GCal Sync JIT
        if calendar_provider == "google":
             existing_apt_gids = await db.pool.fetch("SELECT google_calendar_event_id FROM appointments WHERE google_calendar_event_id IS NOT NULL AND tenant_id = $1", tenant_id)
             apt_gids_set = {row["google_calendar_event_id"] for row in existing_apt_gids}
             for prof in active_professionals:
                 pid = prof['id']; cal_id = prof.get('google_calendar_id')
                 if not cal_id: continue
                 try:
                     g_events = gcal_service.get_events_for_day(calendar_id=cal_id, date_obj=target_date)
                     start_day = datetime.combine(target_date, datetime.min.time(), tzinfo=ARG_TZ)
                     end_day = datetime.combine(target_date, datetime.max.time(), tzinfo=ARG_TZ)
                     await db.pool.execute("DELETE FROM google_calendar_blocks WHERE professional_id=$1 AND start_datetime<$3 AND end_datetime>$2 AND tenant_id=$4", pid, start_day, end_day, tenant_id)
                     for evt in g_events:
                         if evt['id'] in apt_gids_set: continue
                         start = evt["start"].get("dateTime") or evt["start"].get("date")
                         end = evt["end"].get("dateTime") or evt["end"].get("date")
                         all_day = "date" in evt["start"]
                         s_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                         e_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
                         await db.pool.execute("""
                             INSERT INTO google_calendar_blocks (tenant_id, google_event_id, title, start_datetime, end_datetime, all_day, professional_id, sync_status)
                             VALUES ($1, $2, $3, $4, $5, $6, $7, 'synced') ON CONFLICT (google_event_id) DO NOTHING
                         """, tenant_id, evt['id'], evt.get('summary', 'Ocupado'), s_dt, e_dt, all_day, pid)
                 except Exception as e: logger.error(f"JIT GCal Fetch Error: {e}")

        prof_ids = [p["id"] for p in active_professionals]
        start_day = datetime.combine(target_date, datetime.min.time(), tzinfo=ARG_TZ)
        end_day = datetime.combine(target_date, datetime.max.time(), tzinfo=ARG_TZ)
        
        appointments = await db.pool.fetch("SELECT professional_id, appointment_datetime as start, duration_minutes FROM appointments WHERE tenant_id=$1 AND professional_id = ANY($2) AND status IN ('scheduled', 'confirmed') AND appointment_datetime >= $3 AND appointment_datetime <= $4", tenant_id, prof_ids, start_day, end_day)
        
        gcal_blocks = []
        if calendar_provider == "google":
            gcal_blocks = await db.pool.fetch("SELECT professional_id, start_datetime as start, end_datetime as end FROM google_calendar_blocks WHERE tenant_id=$1 AND (professional_id = ANY($2) OR professional_id IS NULL) AND start_datetime >= $3 AND end_datetime <= $4", tenant_id, prof_ids, start_day, end_day)

        busy_map = {pid: set() for pid in prof_ids}
        day_name_en = ['monday','tuesday','wednesday','thursday','friday','saturday','sunday'][target_date.weekday()]
        
        for prof in active_professionals:
            try: wh = json.loads(prof.get('working_hours') or '{}')
            except: wh = {}
            day_config = wh.get(day_name_en, {"enabled": False, "slots": []})
            if day_config.get("enabled") and day_config.get("slots"):
                 check = datetime.combine(target_date, datetime.min.time()).replace(hour=8, minute=0)
                 for _ in range(24):
                     if not is_time_in_working_hours(check.strftime("%H:%M"), day_config):
                         busy_map[prof['id']].add(check.strftime("%H:%M"))
                     check += timedelta(minutes=30)
                     if check.hour >= 20: break
        
        global_busy = set()
        for b in gcal_blocks:
             it = b['start'].astimezone(ARG_TZ)
             while it < b['end'].astimezone(ARG_TZ):
                 hm = it.strftime("%H:%M")
                 if b['professional_id'] and b['professional_id'] in busy_map: busy_map[b['professional_id']].add(hm)
                 elif not b['professional_id']: global_busy.add(hm)
                 it += timedelta(minutes=30)
        
        for a in appointments:
             it = a['start'].astimezone(ARG_TZ)
             end = it + timedelta(minutes=a['duration_minutes'])
             while it < end:
                 if a['professional_id'] in busy_map: busy_map[a['professional_id']].add(it.strftime("%H:%M"))
                 it += timedelta(minutes=30)
        
        for pid in busy_map: busy_map[pid].update(global_busy)
                 
        available_slots = generate_free_slots(target_date, busy_map, start_time_str=CLINIC_HOURS_START, end_time_str=CLINIC_HOURS_END, duration_minutes=duration, time_preference=time_preference)
        
        if available_slots:
            return f"Para {date_query} ({duration} min), disponibilidad: {slots_to_ranges(available_slots)}. Consultando con Dr/a. {professional_name}." if professional_name else f"Disponibilidad: {slots_to_ranges(available_slots)}."
        return "No encontré huecos libres."
    except Exception as e:
        logger.error(f"Availability check error: {e}")
        return "Error consultando disponibilidad."

@tool
async def book_appointment(date_time: str, treatment_reason: str, first_name: Optional[str] = None, last_name: Optional[str] = None, dni: Optional[str] = None, insurance_provider: Optional[str] = None, professional_name: Optional[str] = None):
    """
    Registra un turno en BD.
    date_time: 'miércoles 17:00'.
    treatment_reason: Motivo (ej. Consulta, Limpieza).
    """
    phone = current_customer_phone.get()
    tenant_id = current_tenant_id.get()
    if not phone: return "❌ Error: No pude identificar tu teléfono."
    
    try:
        apt_datetime = parse_datetime(date_time)
        if apt_datetime < get_now_arg(): return "❌ No se pueden agendar turnos en el pasado."
        
        t_data = await db.pool.fetchrow("SELECT code, default_duration_minutes FROM treatment_types WHERE tenant_id=$1 AND (name ILIKE $2 OR code ILIKE $2) AND is_active=true AND is_available_for_booking=true LIMIT 1", tenant_id, f"%{treatment_reason}%")
        if not t_data: return "❌ Ese tratamiento no está disponible para agendar."
        
        duration = t_data["default_duration_minutes"]
        treatment_code = t_data["code"]
        end_apt = apt_datetime + timedelta(minutes=duration)
        
        existing_patient = await db.pool.fetchrow("SELECT id FROM patients WHERE tenant_id=$1 AND phone_number=$2", tenant_id, phone)
        if existing_patient:
             patient_id = existing_patient['id']
             if first_name or last_name or dni or insurance_provider:
                 await db.pool.execute("UPDATE patients SET first_name=COALESCE($1, first_name), last_name=COALESCE($2, last_name), dni=COALESCE($3, dni), insurance_provider=COALESCE($4, insurance_provider) WHERE id=$5", first_name, last_name, dni, insurance_provider, patient_id)
        else:
             if not (first_name and last_name and dni): return "❌ Necesito Nombre, Apellido y DNI para pacientes nuevos."
             row = await db.pool.fetchrow("INSERT INTO patients (tenant_id, phone_number, first_name, last_name, dni, insurance_provider, status, created_at) VALUES ($1, $2, $3, $4, $5, $6, 'active', NOW()) RETURNING id", tenant_id, phone, first_name, last_name, dni, insurance_provider)
             patient_id = row['id']
        
        clean_p_name = re.sub(r"^(dr|dra|doctor|doctora)\.?\s+", "", professional_name or "", flags=re.IGNORECASE).strip()
        p_query = "SELECT p.id, p.first_name, p.last_name, p.google_calendar_id, p.working_hours FROM professionals p INNER JOIN users u ON p.user_id = u.id AND u.role = 'professional' AND u.status = 'active' WHERE p.tenant_id = $1 AND p.is_active = true"
        p_params = [tenant_id]
        if clean_p_name:
             p_query += " AND (p.first_name ILIKE $2 OR p.last_name ILIKE $2 OR (p.first_name || ' ' || COALESCE(p.last_name, '')) ILIKE $2)"
             p_params.append(f"%{clean_p_name}%")
        
        candidates = await db.pool.fetch(p_query, *p_params)
        if not candidates: return "❌ No encontré profesional disponible."
        
        calendar_provider = await get_tenant_calendar_provider(tenant_id)
        target_prof = None
        
        for cand in candidates:
             # Check collision (Simplified compared to main.py but functional)
             conflict = await db.pool.fetchval("""
                 SELECT EXISTS(
                     SELECT 1 FROM appointments WHERE tenant_id=$1 AND professional_id=$2 AND status IN ('scheduled', 'confirmed') AND (appointment_datetime < $4 AND appointment_datetime + interval '1 minute' * COALESCE(duration_minutes, 60) > $3)
                 )
             """, tenant_id, cand['id'], apt_datetime, end_apt)
             
             if not conflict and calendar_provider == "google":
                 # Check GCal blocks (assuming they are synced or we sync them now)
                 # For speed, strictly checking DB blocks (blocks should be synced by check_availability or background)
                 conflict = await db.pool.fetchval("SELECT EXISTS(SELECT 1 FROM google_calendar_blocks WHERE tenant_id=$1 AND (professional_id=$2 OR professional_id IS NULL) AND start_datetime < $4 AND end_datetime > $3)", tenant_id, cand['id'], apt_datetime, end_apt)
             
             if not conflict:
                 target_prof = cand
                 break
        
        if not target_prof: return "❌ Turno no disponible."
        
        apt_id = str(uuid.uuid4())
        await db.pool.execute("INSERT INTO appointments (id, tenant_id, patient_id, professional_id, appointment_datetime, duration_minutes, appointment_type, status, source, created_at) VALUES ($1, $2, $3, $4, $5, $6, $7, 'scheduled', 'ai', NOW())", apt_id, tenant_id, patient_id, target_prof['id'], apt_datetime, duration, treatment_code)
        
        if calendar_provider == "google" and target_prof.get('google_calendar_id'):
             try:
                 gcal_service.create_event(target_prof['google_calendar_id'], f"Cita AI: {first_name or 'Paciente'}", apt_datetime.isoformat(), end_apt.isoformat())
             except: pass
        
        try:
             await sio.emit("NEW_APPOINTMENT", to_json_safe({"id": apt_id, "patient_name": f"{first_name} {last_name}", "appointment_datetime": apt_datetime.isoformat(), "professional_name": target_prof['first_name']}))
        except: pass
        
        return f"✅ Turno confirmado el {apt_datetime.strftime('%d/%m %H:%M')} con Dr/a. {target_prof['first_name']}."

    except Exception as e:
        logger.error(f"Booking error: {e}")
        return "Error al agendar."

def register_dental_tools():
    tool_registry.register(check_availability)
    tool_registry.register(book_appointment)
