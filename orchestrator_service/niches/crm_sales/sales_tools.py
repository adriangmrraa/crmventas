"""
CRM Sales Tools - Reuniones, calificación de leads y escalado humano.
Cuando un usuario agenda una reunión por WhatsApp, se convierte en lead (no en cliente).
El cliente se pasa manualmente después desde el CRM.
"""
import re
import json
import uuid
import logging
from datetime import datetime, timedelta, date, time as dt_time
from typing import Optional, Literal

from langchain.tools import tool
from dateutil.parser import parse as dateutil_parse

from db import db
from core.context import current_tenant_id, current_customer_phone
from core.utils import normalize_phone, ARG_TZ

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper: resolve lead_id from current context (phone + tenant)
# ---------------------------------------------------------------------------
async def _resolve_lead_id() -> Optional[int]:
    """Return the lead ID for the current phone+tenant, or None."""
    phone = current_customer_phone.get()
    tenant_id = current_tenant_id.get()
    if not phone:
        return None
    phone = normalize_phone(phone)
    if not phone:
        return None
    row = await db.pool.fetchrow(
        "SELECT id FROM leads WHERE tenant_id = $1 AND phone_number = $2",
        tenant_id, phone,
    )
    return row["id"] if row else None

# Business hours constants
BUSINESS_HOUR_START = 9
BUSINESS_HOUR_END = 18
SLOT_DURATION_MINUTES = 30

DAY_NAMES_ES = {
    0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves",
    4: "Viernes", 5: "Sábado", 6: "Domingo",
}


def _get_now():
    return datetime.now(ARG_TZ)


def _parse_date(date_query: str) -> date:
    query = date_query.lower().strip()
    today = _get_now().date()
    day_map = {
        "mañana": 1, "tomorrow": 1, "pasado mañana": 2, "day after tomorrow": 2,
        "hoy": 0, "today": 0,
        "lunes": 0, "monday": 0, "martes": 1, "tuesday": 1,
        "miércoles": 2, "miercoles": 2, "wednesday": 2, "jueves": 3, "thursday": 3,
        "viernes": 4, "friday": 4, "sábado": 5, "sabado": 5, "saturday": 5,
        "domingo": 6, "sunday": 6,
    }
    for key, days_ahead in day_map.items():
        if key in query:
            if days_ahead == 0:
                return today
            return (today + timedelta(days=days_ahead))
    try:
        return dateutil_parse(query, dayfirst=True).date()
    except Exception:
        return today + timedelta(days=1)


def _parse_datetime_crm(datetime_query: str) -> datetime:
    """Parsea fecha/hora tipo 'miércoles 17:00' o 'tomorrow 15:30'."""
    query = datetime_query.lower().strip()
    target_time = (10, 0)
    time_match = re.search(r"(\d{1,2})[:h](\d{2})", query)
    if time_match:
        target_time = (int(time_match.group(1)), int(time_match.group(2)))
    else:
        hour_only = re.search(r"(?:las?\s+)?(\d{1,2})\s*(?:hs?|horas?)?\b", query)
        if hour_only:
            h = int(hour_only.group(1))
            if 0 <= h <= 23:
                target_time = (h, 0)
        pm_am = re.search(r"(\d{1,2})\s*(am|pm|a\.m\.|p\.m\.)", query, re.IGNORECASE)
        if pm_am:
            h = int(pm_am.group(1))
            is_pm = "p" in pm_am.group(2).lower()
            if h == 12:
                target_time = (0, 0) if not is_pm else (12, 0)
            elif is_pm:
                target_time = (h + 12, 0)
            else:
                target_time = (h, 0)
    target_date = None
    for word in query.split():
        try:
            d = _parse_date(word)
            if "hoy" in query or "today" in query or d != _get_now().date():
                target_date = d
                break
        except Exception:
            continue
    if not target_date:
        try:
            dt = dateutil_parse(query, dayfirst=True)
            if dt.year > 2000:
                target_date = dt.date()
                if not time_match:
                    target_time = (dt.hour, dt.minute)
        except Exception:
            target_date = (_get_now() + timedelta(days=1)).date()
    return datetime.combine(
        target_date,
        datetime.min.time(),
        tzinfo=ARG_TZ,
    ).replace(hour=target_time[0], minute=target_time[1], second=0, microsecond=0)


# ---------------------------------------------------------------------------
# Helper: parse date range for available slots
# ---------------------------------------------------------------------------
def _parse_date_range(date_range: str) -> tuple[date, date]:
    """Parse natural language date range into (start_date, end_date)."""
    query = date_range.lower().strip()
    today = _get_now().date()

    if "esta semana" in query or "this week" in query:
        days_until_sunday = 6 - today.weekday()
        return today, today + timedelta(days=max(days_until_sunday, 1))

    if "próxima semana" in query or "proxima semana" in query or "next week" in query:
        days_until_monday = 7 - today.weekday()
        start = today + timedelta(days=days_until_monday)
        return start, start + timedelta(days=6)

    if "próximos" in query or "proximos" in query:
        num_match = re.search(r"(\d+)", query)
        days = int(num_match.group(1)) if num_match else 7
        return today, today + timedelta(days=days)

    # Single day reference
    target = _parse_date(query)
    return target, target


# ---------------------------------------------------------------------------
# Helper: send notification to seller about meeting changes
# ---------------------------------------------------------------------------
async def _notify_seller_meeting(
    tenant_id: int,
    seller_id: int,
    title: str,
    message: str,
    lead_phone: str,
    priority: str = "medium",
    notif_type: str = "assignment",
):
    """Create and broadcast a notification to the seller about a meeting event."""
    try:
        from services.seller_notification_service import seller_notification_service, Notification

        user_row = await db.pool.fetchrow(
            "SELECT user_id FROM professionals WHERE id = $1 AND tenant_id = $2",
            seller_id, tenant_id,
        )
        if not user_row or not user_row["user_id"]:
            logger.warning(f"No user_id found for seller professional {seller_id}")
            return

        notif = Notification(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            type=notif_type,
            title=title,
            message=message,
            priority=priority,
            recipient_id=str(user_row["user_id"]),
            related_entity_type="lead",
            related_entity_id=lead_phone,
            metadata={"phone": lead_phone, "seller_id": str(seller_id)},
        )
        await seller_notification_service.save_notifications([notif])
        await seller_notification_service.broadcast_notifications([notif])
    except Exception as e:
        logger.error(f"Error sending seller meeting notification: {e}")


# ---------------------------------------------------------------------------
# Helper: update lead status and tags after booking
# ---------------------------------------------------------------------------
async def _update_lead_after_booking(lead_id, tenant_id: int):
    """Set lead status to 'llamada_agendada' and add 'llamada_pactada' tag."""
    try:
        async with db.pool.acquire() as conn:
            await conn.execute(
                "UPDATE leads SET status = 'llamada_agendada', updated_at = NOW() WHERE id = $1 AND tenant_id = $2",
                lead_id, tenant_id,
            )
            lead = await conn.fetchrow(
                "SELECT tags FROM leads WHERE id = $1 AND tenant_id = $2",
                lead_id, tenant_id,
            )
            existing_tags = lead["tags"] if lead and lead["tags"] else []
            if isinstance(existing_tags, str):
                existing_tags = json.loads(existing_tags)
            if "llamada_pactada" not in existing_tags:
                existing_tags.append("llamada_pactada")
            await conn.execute(
                "UPDATE leads SET tags = $1, updated_at = NOW() WHERE id = $2",
                existing_tags, lead_id,
            )
            await conn.execute(
                "INSERT INTO lead_tag_log (tenant_id, lead_id, tags_added, reason, source) VALUES ($1, $2, $3, $4, 'ai_agent')",
                tenant_id, lead_id, ["llamada_pactada"], "Reunión agendada automáticamente por IA",
            )
    except Exception as e:
        logger.error(f"Error updating lead after booking: {e}")


@tool
async def list_available_slots(date_range: str) -> str:
    """
    Lista los horarios disponibles para agendar una reunión de ventas.
    Consulta la agenda del equipo de ventas y devuelve slots de 30 minutos
    en horario comercial (9:00 a 18:00).

    Parámetros:
    - date_range: rango de fechas en lenguaje natural, ej. 'esta semana', 'mañana',
      'próximo lunes', 'próximos 3 días'

    Retorna una lista de horarios disponibles formateados.
    """
    tenant_id = current_tenant_id.get()
    if not tenant_id:
        return "❌ No se pudo identificar el tenant."

    try:
        start_date, end_date = _parse_date_range(date_range)
        now = _get_now()

        if start_date < now.date():
            start_date = now.date()
        if end_date < start_date:
            end_date = start_date

        # Get all active sellers
        sellers = await db.pool.fetch(
            """
            SELECT p.id, p.first_name, p.last_name
            FROM professionals p
            JOIN users u ON p.user_id = u.id AND u.role IN ('setter', 'closer')
            WHERE p.tenant_id = $1 AND p.is_active = true
            ORDER BY p.first_name
            """,
            tenant_id,
        )
        if not sellers:
            return "❌ No hay vendedores activos disponibles."

        # Fetch busy events in date range
        range_start = datetime.combine(start_date, dt_time(BUSINESS_HOUR_START, 0), tzinfo=ARG_TZ)
        range_end = datetime.combine(end_date, dt_time(BUSINESS_HOUR_END, 0), tzinfo=ARG_TZ)

        busy_events = await db.pool.fetch(
            """
            SELECT seller_id, start_datetime, end_datetime
            FROM seller_agenda_events
            WHERE tenant_id = $1 AND status != 'cancelled'
              AND start_datetime < $3 AND end_datetime > $2
            """,
            tenant_id, range_start, range_end,
        )

        # Build set of busy (seller_id, slot_start) pairs
        busy_slots: set[tuple[int, datetime]] = set()
        for evt in busy_events:
            slot = evt["start_datetime"].astimezone(ARG_TZ).replace(
                minute=(evt["start_datetime"].minute // SLOT_DURATION_MINUTES) * SLOT_DURATION_MINUTES,
                second=0, microsecond=0,
            )
            evt_end = evt["end_datetime"].astimezone(ARG_TZ)
            while slot < evt_end:
                busy_slots.add((evt["seller_id"], slot))
                slot += timedelta(minutes=SLOT_DURATION_MINUTES)

        # Generate available slots (at least one seller free)
        available: list[str] = []
        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() == 6:  # Skip Sundays
                current_date += timedelta(days=1)
                continue

            day_name = DAY_NAMES_ES.get(current_date.weekday(), "")
            date_str = current_date.strftime("%d/%m")

            for hour in range(BUSINESS_HOUR_START, BUSINESS_HOUR_END):
                for minute in range(0, 60, SLOT_DURATION_MINUTES):
                    slot_dt = datetime.combine(
                        current_date, dt_time(hour, minute), tzinfo=ARG_TZ,
                    )
                    if slot_dt <= now:
                        continue

                    has_free_seller = any(
                        (s["id"], slot_dt) not in busy_slots for s in sellers
                    )
                    if has_free_seller:
                        available.append(f"{day_name} {date_str} {hour:02d}:{minute:02d}")

            current_date += timedelta(days=1)

        if not available:
            return "❌ No hay horarios disponibles en ese rango. Probá con otras fechas."

        MAX_DISPLAY = 15
        display = available[:MAX_DISPLAY]
        remaining = len(available) - MAX_DISPLAY

        result = "📅 Horarios disponibles:\n"
        for slot_str in display:
            result += f"  • {slot_str}\n"
        if remaining > 0:
            result += f"  ...y {remaining} horarios más.\n"
        result += "\n¿Cuál preferís? Decime el día y horario y lo agendo."
        return result

    except Exception as e:
        logger.exception("list_available_slots error")
        return "❌ Error al consultar horarios disponibles. Intentá de nuevo."


@tool
async def lead_scoring(message: str) -> str:
    """
    Analiza un mensaje de un prospecto y devuelve una clasificación cualitativa del lead
    (por ejemplo: cold, warm, hot) junto con una breve explicación.
    """
    return (
        "Esqueleto lead_scoring activo. Aún no se ha implementado la lógica de scoring "
        "para CRM; este tool debe ser conectado cuando el nicho crm_sales esté habilitado."
    )


@tool
async def list_templates() -> str:
    """
    Devuelve (en el futuro) la lista de plantillas de mensaje aprobadas por Meta
    disponibles para el tenant actual.
    """
    return (
        "Esqueleto list_templates activo. En la versión CRM, este tool listará las "
        "plantillas de WhatsApp aprobadas para el tenant, pero todavía no está implementado."
    )


@tool
async def book_sales_meeting(
    date_time: str,
    lead_reason: str,
    lead_name: str | None = None,
    preferred_agent_name: str | None = None,
) -> str:
    """
    Reserva una reunión de ventas (demo o llamada) para un lead.
    Si la persona aún no es lead, se la crea como lead al agendar (por teléfono de WhatsApp).
    Los leads se convierten en clientes después, de forma manual en el CRM.

    Parámetros:
    - date_time: fecha y hora, ej. 'miércoles 17:00', 'mañana 15:30', 'tomorrow 10:00'
    - lead_reason: motivo de la reunión (ej. producto o servicio de interés)
    - lead_name: nombre del lead si lo conocés (opcional)
    - preferred_agent_name: nombre del vendedor preferido (opcional)
    """
    phone = current_customer_phone.get()
    tenant_id = current_tenant_id.get()
    if not phone:
        return "❌ No pude identificar tu número de teléfono. Escribí desde WhatsApp para poder agendar."

    phone = normalize_phone(phone)
    if not phone:
        return "❌ Número de teléfono inválido."

    try:
        start_dt = _parse_datetime_crm(date_time)
        if start_dt < _get_now():
            return "❌ No se pueden agendar reuniones en el pasado. Elegí una fecha y hora futura."
        duration_minutes = 60
        end_dt = start_dt + timedelta(minutes=duration_minutes)

        # Verificar que el tenant sea CRM
        niche = await db.pool.fetchval(
            "SELECT COALESCE(niche_type, 'crm_sales') FROM tenants WHERE id = $1",
            tenant_id,
        )
        if niche != "crm_sales":
            return "❌ Esta entidad no está configurada para agenda de ventas."

        # Obtener o crear LEAD (no cliente). Al agendar se convierte en lead.
        existing = await db.pool.fetchrow(
            "SELECT id FROM leads WHERE tenant_id = $1 AND phone_number = $2",
            tenant_id,
            phone,
        )
        if existing:
            lead_id = existing["id"]
            if lead_name and lead_name.strip():
                parts = lead_name.strip().split(None, 1)
                first_name = parts[0] if parts else None
                last_name = parts[1] if len(parts) > 1 else None
                await db.pool.execute(
                    "UPDATE leads SET first_name = COALESCE($1, first_name), last_name = COALESCE($2, last_name), updated_at = NOW() WHERE id = $3",
                    first_name,
                    last_name,
                    lead_id,
                )
        else:
            parts = (lead_name or "").strip().split(None, 1)
            first_name = parts[0] if parts else None
            last_name = parts[1] if len(parts) > 1 else None
            row = await db.pool.fetchrow(
                """
                INSERT INTO leads (tenant_id, phone_number, first_name, last_name, status, source, created_at, updated_at)
                VALUES ($1, $2, $3, $4, 'new', 'whatsapp', NOW(), NOW())
                RETURNING id
                """,
                tenant_id,
                phone,
                first_name or "Lead",
                last_name or "",
            )
            lead_id = row["id"]

        # Buscar vendedor (setter/closer) disponible
        clean_agent = (
            re.sub(r"^(sr|sra|vendedor|seller)\.\s*", "", (preferred_agent_name or ""), flags=re.IGNORECASE).strip()
            if preferred_agent_name
            else ""
        )
        sellers_query = """
            SELECT p.id, p.first_name, p.last_name
            FROM professionals p
            JOIN users u ON p.user_id = u.id AND u.role IN ('setter', 'closer')
            JOIN tenants t ON t.id = p.tenant_id AND COALESCE(t.niche_type, 'crm_sales') = 'crm_sales'
            WHERE p.tenant_id = $1 AND p.is_active = true
        """
        sellers_params: list = [tenant_id]
        if clean_agent:
            sellers_query += " AND (p.first_name ILIKE $2 OR p.last_name ILIKE $2 OR (p.first_name || ' ' || COALESCE(p.last_name, '')) ILIKE $2)"
            sellers_params.append(f"%{clean_agent}%")
        sellers_query += " ORDER BY p.first_name"
        candidates = await db.pool.fetch(sellers_query, *sellers_params)
        if not candidates:
            return "❌ No hay vendedores disponibles en esta entidad."

        target_seller = None
        for seller in candidates:
            conflict = await db.pool.fetchval(
                """
                SELECT EXISTS(
                    SELECT 1 FROM seller_agenda_events
                    WHERE tenant_id = $1 AND seller_id = $2 AND status != 'cancelled'
                      AND start_datetime < $4 AND end_datetime > $3
                )
                """,
                tenant_id,
                seller["id"],
                start_dt,
                end_dt,
            )
            if not conflict:
                target_seller = seller
                break
        if not target_seller:
            return "❌ No hay horario disponible en esa fecha. Probá otro día u horario."

        title = f"Reunión: {lead_reason[:80]}" if lead_reason else "Reunión de ventas"
        event_id = uuid.uuid4()
        await db.pool.execute(
            """
            INSERT INTO seller_agenda_events (id, tenant_id, seller_id, title, start_datetime, end_datetime, lead_id, source, status, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, 'ai', 'scheduled', NOW(), NOW())
            """,
            event_id,
            tenant_id,
            target_seller["id"],
            title,
            start_dt,
            end_dt,
            lead_id,
        )

        # Update lead status to 'llamada_agendada' and add 'llamada_pactada' tag
        await _update_lead_after_booking(lead_id, tenant_id)

        # Notify assigned seller
        seller_name = f"{target_seller['first_name'] or ''} {target_seller['last_name'] or ''}".strip()
        lead_display = lead_name or phone
        await _notify_seller_meeting(
            tenant_id=tenant_id,
            seller_id=target_seller["id"],
            title=f"Nueva reunión agendada — {lead_display}",
            message=(
                f"Reunión el {start_dt.strftime('%d/%m a las %H:%M')}. "
                f"Motivo: {lead_reason}. Lead: {lead_display} ({phone})."
            ),
            lead_phone=phone,
            priority="high",
            notif_type="assignment",
        )

        logger.info(
            f"Meeting booked: {lead_display} with {seller_name} at {start_dt.isoformat()}, event_id={event_id}"
        )
        return (
            f"✅ Reunión confirmada el {start_dt.strftime('%d/%m a las %H:%M')} con {seller_name}. "
            f"Motivo: {lead_reason}. "
            "Te registré como lead y notifiqué al vendedor. En el CRM podés ver y gestionar la reunión."
        )
    except Exception as e:
        logger.exception("book_sales_meeting error")
        return f"❌ Error al agendar la reunión. Intentá de nuevo o contactá por otro canal."


@tool
async def assign_lead_tags(tags: list[str], reason: str) -> str:
    """
    Asigna etiquetas (tags) a un lead basándose en el contexto de la conversación.
    Las etiquetas se MERGEAN con las existentes (no se reemplazan).
    El setter verá estas etiquetas al tomar el lead.

    Etiquetas válidas:
    - caliente: muestra interés en implementación/compra
    - tibio: pregunta por precio pero no se compromete
    - precio_sensible: pregunta por precio y muestra interés
    - llamada_pactada: agendó una reunión/llamada
    - handoff_solicitado: pide hablar con un humano
    - comparando_opciones: menciona competidores
    - urgente: tiene urgencia explícita
    - sin_respuesta: no responde hace más de 24h

    Parámetros:
    - tags: lista de etiquetas a asignar, ej. ["caliente", "urgente"]
    - reason: motivo breve de por qué se asigna cada tag
    """
    phone = current_customer_phone.get()
    tenant_id = current_tenant_id.get()
    if not phone:
        return "No se pudo identificar el lead (sin teléfono en contexto)."

    phone = normalize_phone(phone)
    if not phone:
        return "Número de teléfono inválido."

    VALID_TAGS = {
        "caliente", "tibio", "precio_sensible", "llamada_pactada",
        "handoff_solicitado", "comparando_opciones", "urgente", "sin_respuesta",
    }
    # Filter to valid tags only
    clean_tags = [t.strip().lower() for t in tags if t.strip().lower() in VALID_TAGS]
    if not clean_tags:
        return "Ninguna etiqueta válida proporcionada."

    try:
        async with db.pool.acquire() as conn:
            # Get lead
            lead = await conn.fetchrow(
                "SELECT id, tags FROM leads WHERE tenant_id = $1 AND phone_number = $2",
                tenant_id, phone,
            )
            if not lead:
                return "Lead no encontrado para este número."

            lead_id = lead["id"]
            existing_tags = lead["tags"] if lead["tags"] else []
            if isinstance(existing_tags, str):
                import json as _json
                existing_tags = _json.loads(existing_tags)

            # Merge: add new tags without duplicates
            merged = list(dict.fromkeys(existing_tags + clean_tags))

            await conn.execute(
                "UPDATE leads SET tags = $1, updated_at = NOW() WHERE id = $2",
                merged, lead_id,
            )

            # Audit log
            await conn.execute(
                "INSERT INTO lead_tag_log (tenant_id, lead_id, tags_added, reason, source) VALUES ($1, $2, $3, $4, 'ai_agent')",
                tenant_id, lead_id, clean_tags, reason,
            )

        new_tags_str = ", ".join(clean_tags)
        logger.info(f"Tags assigned to lead {phone}: [{new_tags_str}] — {reason}")
        return f"Etiquetas asignadas: [{new_tags_str}]. Motivo: {reason}. Tags actuales del lead: {merged}"
    except Exception as e:
        logger.exception("assign_lead_tags error")
        return f"Error al asignar etiquetas: {e}"


@tool
async def get_lead_tags() -> str:
    """
    Obtiene las etiquetas (tags) actuales de un lead.
    Útil para saber qué etiquetas ya tiene asignadas antes de agregar nuevas.
    """
    phone = current_customer_phone.get()
    tenant_id = current_tenant_id.get()
    if not phone:
        return "No se pudo identificar el lead (sin teléfono en contexto)."

    phone = normalize_phone(phone)
    if not phone:
        return "Número de teléfono inválido."

    try:
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT tags, first_name, last_name FROM leads WHERE tenant_id = $1 AND phone_number = $2",
                tenant_id, phone,
            )
            if not row:
                return "Lead no encontrado."

            tags = row["tags"] if row["tags"] else []
            if isinstance(tags, str):
                import json as _json
                tags = _json.loads(tags)
            name = f"{row['first_name'] or ''} {row['last_name'] or ''}".strip() or phone
            if not tags:
                return f"El lead {name} no tiene etiquetas asignadas."
            return f"Etiquetas del lead {name}: {tags}"
    except Exception as e:
        logger.exception("get_lead_tags error")
        return f"Error al obtener etiquetas: {e}"


@tool
async def qualify_lead(
    interest_level: str,
    budget_range: str,
    timeline: str,
    needs_summary: str,
) -> str:
    """
    Registra la calificación de un lead basándose en la conversación.
    Actualiza el score numérico, el desglose (score_breakdown) y el estado del lead.

    Parámetros:
    - interest_level: nivel de interés detectado ('high', 'medium', 'low')
    - budget_range: rango de presupuesto mencionado, ej. '$1000-$5000', 'no definido'
    - timeline: urgencia temporal, ej. 'esta semana', '1 mes', 'sin definir'
    - needs_summary: resumen breve de lo que necesita el prospecto
    """
    phone = current_customer_phone.get()
    tenant_id = current_tenant_id.get()
    if not phone:
        return "No se pudo identificar el lead (sin teléfono en contexto)."

    phone = normalize_phone(phone)
    if not phone:
        return "Número de teléfono inválido."

    # --- Score calculation ---
    INTEREST_SCORES = {"high": 40, "medium": 25, "low": 10}
    TIMELINE_SCORES = {
        "esta semana": 30, "this week": 30,
        "este mes": 20, "this month": 20,
        "1 mes": 20, "2 semanas": 25,
        "sin definir": 5, "no definido": 5,
    }
    BUDGET_SCORES_DEFAULT = 15  # has a budget at all

    interest_score = INTEREST_SCORES.get(interest_level.lower().strip(), 15)

    timeline_score = 10  # default
    timeline_lower = timeline.lower().strip()
    for key, val in TIMELINE_SCORES.items():
        if key in timeline_lower:
            timeline_score = val
            break

    budget_score = 0 if budget_range.lower().strip() in ("no definido", "sin definir", "n/a", "") else BUDGET_SCORES_DEFAULT
    needs_score = 15 if len(needs_summary.strip()) > 10 else 5

    total_score = interest_score + timeline_score + budget_score + needs_score

    breakdown = {
        "interest": {"level": interest_level, "score": interest_score},
        "timeline": {"value": timeline, "score": timeline_score},
        "budget": {"range": budget_range, "score": budget_score},
        "needs": {"summary": needs_summary[:200], "score": needs_score},
        "total": total_score,
        "qualified_at": datetime.now(ARG_TZ).isoformat(),
    }

    # Determine status from score
    if total_score >= 70:
        new_status = "hot"
    elif total_score >= 45:
        new_status = "warm"
    else:
        new_status = "cold"

    try:
        async with db.pool.acquire() as conn:
            lead = await conn.fetchrow(
                "SELECT id, status, first_name, last_name FROM leads WHERE tenant_id = $1 AND phone_number = $2",
                tenant_id, phone,
            )
            if not lead:
                return "Lead no encontrado para este número."

            lead_id = lead["id"]
            # Do not downgrade status if already qualified higher manually
            current_status = (lead["status"] or "").lower()
            manual_statuses = {"contacted", "negotiation", "won", "lost"}
            if current_status in manual_statuses:
                new_status = current_status  # preserve manual status

            await conn.execute(
                """
                UPDATE leads
                SET score = $1,
                    score_breakdown = $2,
                    score_updated_at = NOW(),
                    status = $3,
                    lead_score = $4,
                    updated_at = NOW()
                WHERE id = $5
                """,
                total_score,
                json.dumps(breakdown),
                new_status,
                new_status,
                lead_id,
            )

        name = f"{lead['first_name'] or ''} {lead['last_name'] or ''}".strip() or phone
        logger.info(f"Lead qualified: {name} — score={total_score}, status={new_status}")
        return (
            f"Lead {name} calificado: score={total_score}/100, estado={new_status}. "
            f"Interés={interest_level}, presupuesto={budget_range}, timeline={timeline}."
        )
    except Exception as e:
        logger.exception("qualify_lead error")
        return f"Error al calificar el lead: {e}"


@tool
async def request_human_handoff(
    reason: str,
    urgency: str = "medium",
) -> str:
    """
    Marca la conversación actual para que un vendedor humano la tome.
    Envía una notificación al vendedor asignado y al CEO.

    Parámetros:
    - reason: motivo del escalado (ej. 'El prospecto quiere hablar con una persona', 'pregunta técnica compleja')
    - urgency: nivel de urgencia — 'low', 'medium' o 'high'
    """
    phone = current_customer_phone.get()
    tenant_id = current_tenant_id.get()
    if not phone:
        return "No se pudo identificar el lead (sin teléfono en contexto)."

    phone = normalize_phone(phone)
    if not phone:
        return "Número de teléfono inválido."

    if urgency.lower().strip() not in ("low", "medium", "high"):
        urgency = "medium"
    else:
        urgency = urgency.lower().strip()

    URGENCY_TO_PRIORITY = {"high": "critical", "medium": "high", "low": "medium"}
    priority = URGENCY_TO_PRIORITY[urgency]

    try:
        async with db.pool.acquire() as conn:
            lead = await conn.fetchrow(
                "SELECT id, first_name, last_name, assigned_seller_id FROM leads WHERE tenant_id = $1 AND phone_number = $2",
                tenant_id, phone,
            )
            if not lead:
                return "Lead no encontrado para este número."

            lead_id = lead["id"]
            name = f"{lead['first_name'] or ''} {lead['last_name'] or ''}".strip() or phone
            assigned_seller_id = lead["assigned_seller_id"]

            # Mark lead with handoff tag
            existing_tags = await conn.fetchval(
                "SELECT tags FROM leads WHERE id = $1", lead_id,
            )
            if existing_tags is None:
                existing_tags = []
            if isinstance(existing_tags, str):
                existing_tags = json.loads(existing_tags)
            if "handoff_solicitado" not in existing_tags:
                existing_tags.append("handoff_solicitado")
            if urgency == "high" and "urgente" not in existing_tags:
                existing_tags.append("urgente")

            await conn.execute(
                "UPDATE leads SET tags = $1, updated_at = NOW() WHERE id = $2",
                existing_tags, lead_id,
            )

            # Build notifications
            from services.seller_notification_service import Notification, seller_notification_service
            notifications = []

            # Notify assigned seller (if any)
            if assigned_seller_id:
                # Resolve the user_id for the seller (professionals.user_id)
                seller_user_id = await conn.fetchval(
                    "SELECT user_id FROM professionals WHERE id = $1", assigned_seller_id,
                )
                if seller_user_id:
                    notifications.append(Notification(
                        id=str(uuid.uuid4()),
                        tenant_id=tenant_id,
                        type="handoff",
                        title=f"Handoff solicitado — {name}",
                        message=f"Urgencia: {urgency}. Motivo: {reason}",
                        priority=priority,
                        recipient_id=str(seller_user_id),
                        related_entity_type="lead",
                        related_entity_id=str(lead_id),
                        metadata={"phone": phone, "reason": reason, "urgency": urgency},
                    ))

            # Always notify CEO
            ceo = await conn.fetchrow(
                "SELECT id FROM users WHERE tenant_id = $1 AND role = 'ceo' AND status = 'active' LIMIT 1",
                tenant_id,
            )
            if ceo:
                ceo_id = str(ceo["id"])
                # Avoid duplicate if seller IS the CEO
                already_notified = any(n.recipient_id == ceo_id for n in notifications)
                if not already_notified:
                    notifications.append(Notification(
                        id=str(uuid.uuid4()),
                        tenant_id=tenant_id,
                        type="handoff",
                        title=f"Handoff solicitado — {name}",
                        message=f"Urgencia: {urgency}. Motivo: {reason}",
                        priority=priority,
                        recipient_id=ceo_id,
                        related_entity_type="lead",
                        related_entity_id=str(lead_id),
                        metadata={"phone": phone, "reason": reason, "urgency": urgency},
                    ))

            if notifications:
                await seller_notification_service.save_notifications(notifications)
                await seller_notification_service.broadcast_notifications(notifications)

            # Emit Socket.IO event for real-time frontend update
            try:
                from core.socket_manager import sio
                await sio.emit("HANDOFF_REQUESTED", {
                    "tenant_id": tenant_id,
                    "lead_id": str(lead_id),
                    "phone": phone,
                    "name": name,
                    "reason": reason,
                    "urgency": urgency,
                    "timestamp": datetime.now(ARG_TZ).isoformat(),
                })
            except Exception as sio_err:
                logger.warning(f"Could not emit HANDOFF_REQUESTED socket event: {sio_err}")

        notified_count = len(notifications)
        logger.info(f"Human handoff requested for lead {name} ({phone}) — urgency={urgency}, reason={reason}, notified={notified_count}")
        return (
            f"Handoff registrado. Urgencia: {urgency}. Se notificó a {notified_count} persona(s) del equipo. "
            f"Un vendedor se pondrá en contacto lo antes posible."
        )
    except Exception as e:
        logger.exception("request_human_handoff error")
        return f"Error al solicitar el handoff: {e}"


@tool
async def cancel_or_reschedule_meeting(
    action: str,
    new_date_time: str | None = None,
    reason: str | None = None,
) -> str:
    """
    Cancela o reprograma una reunión de ventas existente para el lead actual.

    Parámetros:
    - action: 'cancel' para cancelar, 'reschedule' para reprogramar
    - new_date_time: nueva fecha y hora si se reprograma, ej. 'jueves 16:00' (requerido si action='reschedule')
    - reason: motivo de la cancelación o reprogramación (opcional)
    """
    phone = current_customer_phone.get()
    tenant_id = current_tenant_id.get()
    if not phone:
        return "❌ No pude identificar tu número de teléfono."

    phone = normalize_phone(phone)
    if not phone:
        return "❌ Número de teléfono inválido."

    action = action.lower().strip()
    if action not in ("cancel", "reschedule"):
        return "❌ Acción inválida. Usá 'cancel' o 'reschedule'."

    if action == "reschedule" and not new_date_time:
        return "❌ Para reprogramar necesito la nueva fecha y hora. Ej: 'jueves 16:00'."

    try:
        # Find the lead
        lead = await db.pool.fetchrow(
            "SELECT id, first_name, last_name FROM leads WHERE tenant_id = $1 AND phone_number = $2",
            tenant_id, phone,
        )
        if not lead:
            return "❌ No encontré un lead asociado a tu número."

        lead_id = lead["id"]
        lead_display = f"{lead['first_name'] or ''} {lead['last_name'] or ''}".strip() or phone

        # Find the upcoming scheduled meeting for this lead
        meeting = await db.pool.fetchrow(
            """
            SELECT sae.id, sae.seller_id, sae.title, sae.start_datetime, sae.end_datetime,
                   p.first_name AS seller_first, p.last_name AS seller_last
            FROM seller_agenda_events sae
            JOIN professionals p ON p.id = sae.seller_id
            WHERE sae.tenant_id = $1 AND sae.lead_id = $2 AND sae.status = 'scheduled'
              AND sae.start_datetime > $3
            ORDER BY sae.start_datetime ASC
            LIMIT 1
            """,
            tenant_id, lead_id, _get_now(),
        )
        if not meeting:
            return "❌ No encontré una reunión programada para cancelar o reprogramar."

        seller_name = f"{meeting['seller_first'] or ''} {meeting['seller_last'] or ''}".strip()
        old_dt = meeting["start_datetime"].astimezone(ARG_TZ)
        reason_text = reason or "Sin motivo especificado"

        if action == "cancel":
            # Cancel the meeting
            await db.pool.execute(
                "UPDATE seller_agenda_events SET status = 'cancelled', notes = COALESCE(notes, '') || $2, updated_at = NOW() WHERE id = $1",
                meeting["id"],
                f"\n[Cancelado por IA] {reason_text} — {_get_now().isoformat()}",
            )

            # Remove 'llamada_pactada' tag and update status
            async with db.pool.acquire() as conn:
                lead_row = await conn.fetchrow(
                    "SELECT tags FROM leads WHERE id = $1 AND tenant_id = $2",
                    lead_id, tenant_id,
                )
                existing_tags = lead_row["tags"] if lead_row and lead_row["tags"] else []
                if isinstance(existing_tags, str):
                    existing_tags = json.loads(existing_tags)
                if "llamada_pactada" in existing_tags:
                    existing_tags.remove("llamada_pactada")
                if "llamada_cancelada" not in existing_tags:
                    existing_tags.append("llamada_cancelada")
                await conn.execute(
                    "UPDATE leads SET tags = $1, status = 'contacted', updated_at = NOW() WHERE id = $2",
                    existing_tags, lead_id,
                )

            # Notify seller
            await _notify_seller_meeting(
                tenant_id=tenant_id,
                seller_id=meeting["seller_id"],
                title=f"Reunión cancelada — {lead_display}",
                message=(
                    f"La reunión del {old_dt.strftime('%d/%m a las %H:%M')} fue cancelada. "
                    f"Motivo: {reason_text}. Lead: {lead_display} ({phone})."
                ),
                lead_phone=phone,
                priority="high",
                notif_type="assignment",
            )

            logger.info(f"Meeting cancelled: {lead_display}, was {old_dt.isoformat()}, reason={reason_text}")
            return (
                f"✅ Reunión del {old_dt.strftime('%d/%m a las %H:%M')} con {seller_name} cancelada. "
                f"Motivo: {reason_text}. Se notificó al vendedor."
            )

        else:  # reschedule
            new_start = _parse_datetime_crm(new_date_time)
            if new_start < _get_now():
                return "❌ La nueva fecha no puede ser en el pasado."

            duration = meeting["end_datetime"] - meeting["start_datetime"]
            new_end = new_start + duration

            # Check seller availability at new time
            conflict = await db.pool.fetchval(
                """
                SELECT EXISTS(
                    SELECT 1 FROM seller_agenda_events
                    WHERE tenant_id = $1 AND seller_id = $2 AND status != 'cancelled'
                      AND id != $5
                      AND start_datetime < $4 AND end_datetime > $3
                )
                """,
                tenant_id, meeting["seller_id"], new_start, new_end, meeting["id"],
            )
            if conflict:
                return (
                    f"❌ {seller_name} no está disponible en ese horario. "
                    "Probá otro día u horario, o usá list_available_slots para ver opciones."
                )

            # Update the meeting
            await db.pool.execute(
                """
                UPDATE seller_agenda_events
                SET start_datetime = $2, end_datetime = $3,
                    notes = COALESCE(notes, '') || $4,
                    updated_at = NOW()
                WHERE id = $1
                """,
                meeting["id"],
                new_start,
                new_end,
                f"\n[Reprogramado por IA] de {old_dt.strftime('%d/%m %H:%M')} a {new_start.strftime('%d/%m %H:%M')}. Motivo: {reason_text} — {_get_now().isoformat()}",
            )

            # Notify seller
            await _notify_seller_meeting(
                tenant_id=tenant_id,
                seller_id=meeting["seller_id"],
                title=f"Reunión reprogramada — {lead_display}",
                message=(
                    f"La reunión fue movida del {old_dt.strftime('%d/%m %H:%M')} "
                    f"al {new_start.strftime('%d/%m a las %H:%M')}. "
                    f"Motivo: {reason_text}. Lead: {lead_display} ({phone})."
                ),
                lead_phone=phone,
                priority="high",
                notif_type="assignment",
            )

            logger.info(
                f"Meeting rescheduled: {lead_display}, from {old_dt.isoformat()} to {new_start.isoformat()}"
            )
            return (
                f"✅ Reunión reprogramada: del {old_dt.strftime('%d/%m %H:%M')} "
                f"al {new_start.strftime('%d/%m a las %H:%M')} con {seller_name}. "
                f"Se notificó al vendedor."
            )

    except Exception as e:
        logger.exception("cancel_or_reschedule_meeting error")
        return "❌ Error al procesar la solicitud. Intentá de nuevo."


@tool
async def derive_to_setter(
    summary: str,
    reason: str,
) -> str:
    """
    Deriva el lead actual a la cola de un setter humano con un resumen generado por IA.
    Usá esta herramienta cuando:
    - Se agendó una llamada y el setter debe prepararse
    - El lead perdió interés y necesita seguimiento humano
    - Detectás potencial de cierre y un humano debería tomar el control

    Parámetros:
    - summary: resumen generado por IA de los puntos clave del prospecto (necesidades, presupuesto, timeline, objeciones, etc.)
    - reason: motivo de la derivación (ej. 'llamada agendada', 'potencial de cierre detectado', 'lead perdió interés')
    """
    phone = current_customer_phone.get()
    tenant_id = current_tenant_id.get()
    if not phone:
        return "No se pudo identificar el lead (sin teléfono en contexto)."

    phone = normalize_phone(phone)
    if not phone:
        return "Número de teléfono inválido."

    try:
        async with db.pool.acquire() as conn:
            # 1. Get lead
            lead = await conn.fetchrow(
                "SELECT id, first_name, last_name, assigned_seller_id, tags, score_breakdown FROM leads WHERE tenant_id = $1 AND phone_number = $2",
                tenant_id, phone,
            )
            if not lead:
                return "Lead no encontrado para este número."

            lead_id = lead["id"]
            name = f"{lead['first_name'] or ''} {lead['last_name'] or ''}".strip() or phone

            # 2. Find next available setter (round-robin: setter with fewest active derivado leads)
            setter = await conn.fetchrow(
                """
                SELECT u.id
                FROM users u
                LEFT JOIN (
                    SELECT assigned_seller_id, COUNT(*) as active_leads
                    FROM leads
                    WHERE tenant_id = $1 AND status = 'derivado'
                    GROUP BY assigned_seller_id
                ) lc ON lc.assigned_seller_id = u.id
                WHERE u.tenant_id = $1
                AND u.role = 'setter'
                AND u.status = 'active'
                ORDER BY COALESCE(lc.active_leads, 0) ASC, u.created_at ASC
                LIMIT 1
                """,
                tenant_id,
            )
            if not setter:
                # Fallback: any active seller
                setter = await conn.fetchrow(
                    """
                    SELECT u.id FROM users u
                    WHERE u.tenant_id = $1 AND u.status = 'active'
                    AND u.role IN ('setter', 'closer', 'ceo')
                    ORDER BY u.created_at ASC LIMIT 1
                    """,
                    tenant_id,
                )
            if not setter:
                return "No hay setters disponibles para recibir la derivación."

            setter_id = setter["id"]

            # 3. Update lead: assign to setter, status = derivado
            # Store AI summary in score_breakdown under "ai_derivation" key
            existing_breakdown = lead["score_breakdown"] if lead["score_breakdown"] else {}
            if isinstance(existing_breakdown, str):
                existing_breakdown = json.loads(existing_breakdown)
            existing_breakdown["ai_derivation"] = {
                "summary": summary,
                "reason": reason,
                "derived_at": datetime.now(ARG_TZ).isoformat(),
            }

            await conn.execute(
                """
                UPDATE leads
                SET assigned_seller_id = $1,
                    status = 'derivado',
                    score_breakdown = $2,
                    status_changed_at = NOW(),
                    updated_at = NOW()
                WHERE id = $3 AND tenant_id = $4
                """,
                setter_id,
                json.dumps(existing_breakdown),
                lead_id,
                tenant_id,
            )

            # 4. Add assignment history entry
            await conn.execute(
                """
                UPDATE leads
                SET assignment_history = COALESCE(assignment_history, '[]'::jsonb) || jsonb_build_array(
                    jsonb_build_object(
                        'seller_id', $1::text,
                        'assigned_at', NOW()::text,
                        'assigned_by', 'ai_agent',
                        'source', 'derive_to_setter',
                        'reason', $2
                    )
                )
                WHERE id = $3 AND tenant_id = $4
                """,
                str(setter_id), reason, lead_id, tenant_id,
            )

            # 5. Add tag "derivado_por_ia"
            existing_tags = lead["tags"] if lead["tags"] else []
            if isinstance(existing_tags, str):
                existing_tags = json.loads(existing_tags)
            if "derivado_por_ia" not in existing_tags:
                existing_tags.append("derivado_por_ia")

            await conn.execute(
                "UPDATE leads SET tags = $1, updated_at = NOW() WHERE id = $2",
                existing_tags, lead_id,
            )
            await conn.execute(
                "INSERT INTO lead_tag_log (tenant_id, lead_id, tags_added, reason, source) VALUES ($1, $2, $3, $4, 'ai_agent')",
                tenant_id, lead_id, ["derivado_por_ia"], f"Derivado por IA: {reason}",
            )

            # 6. Log system event
            await conn.execute(
                """
                INSERT INTO system_events
                (tenant_id, event_type, severity, message, payload)
                VALUES ($1, 'lead_derived_to_setter', 'info',
                        'Lead derivado a setter por IA',
                        jsonb_build_object(
                            'lead_id', $2::text,
                            'phone', $3,
                            'setter_id', $4::text,
                            'reason', $5,
                            'summary', $6
                        ))
                """,
                tenant_id, str(lead_id), phone, str(setter_id), reason, summary[:500],
            )

            # 7. Create notification for the setter
            from services.seller_notification_service import Notification, seller_notification_service
            notif = Notification(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                type="derivation",
                title=f"Nuevo lead derivado — {name}",
                message=f"Motivo: {reason}. Resumen IA: {summary[:200]}",
                priority="high",
                recipient_id=str(setter_id),
                related_entity_type="lead",
                related_entity_id=str(lead_id),
                metadata={
                    "phone": phone,
                    "reason": reason,
                    "summary": summary,
                    "lead_name": name,
                },
            )
            await seller_notification_service.save_notifications([notif])
            await seller_notification_service.broadcast_notifications([notif])

            # 8. Emit Socket.IO event LEAD_DERIVED
            try:
                from core.socket_manager import sio
                await sio.emit("LEAD_DERIVED", {
                    "tenant_id": tenant_id,
                    "lead_id": str(lead_id),
                    "phone": phone,
                    "name": name,
                    "setter_id": str(setter_id),
                    "reason": reason,
                    "summary": summary[:300],
                    "timestamp": datetime.now(ARG_TZ).isoformat(),
                })
            except Exception as sio_err:
                logger.warning(f"Could not emit LEAD_DERIVED socket event: {sio_err}")

        logger.info(f"Lead {name} ({phone}) derived to setter {setter_id} — reason={reason}")
        return (
            f"Lead {name} derivado exitosamente al setter. "
            f"Motivo: {reason}. Se envió notificación con el resumen. "
            f"El setter puede tomar el lead desde su panel."
        )
    except Exception as e:
        logger.exception("derive_to_setter error")
        return f"Error al derivar el lead: {e}"


CRM_SALES_TOOLS = [
    lead_scoring,
    list_templates,
    list_available_slots,
    book_sales_meeting,
    cancel_or_reschedule_meeting,
    assign_lead_tags,
    get_lead_tags,
    qualify_lead,
    request_human_handoff,
    derive_to_setter,
]
