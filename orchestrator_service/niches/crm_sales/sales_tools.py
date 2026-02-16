"""
CRM Sales Tools - Reuniones y leads.
Cuando un usuario agenda una reunión por WhatsApp, se convierte en lead (no en cliente).
El cliente se pasa manualmente después desde el CRM.
"""
import re
import uuid
import logging
from datetime import datetime, timedelta, date
from typing import Optional

from langchain.tools import tool
from dateutil.parser import parse as dateutil_parse

from db import db
from core.context import current_tenant_id, current_customer_phone
from core.utils import normalize_phone, ARG_TZ

logger = logging.getLogger(__name__)


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

        seller_name = f"{target_seller['first_name'] or ''} {target_seller['last_name'] or ''}".strip()
        return (
            f"✅ Reunión confirmada el {start_dt.strftime('%d/%m a las %H:%M')} con {seller_name}. "
            "Te registré como lead; en el CRM podés ver y gestionar la reunión."
        )
    except Exception as e:
        logger.exception("book_sales_meeting error")
        return f"❌ Error al agendar la reunión. Intentá de nuevo o contactá por otro canal."


CRM_SALES_TOOLS = [lead_scoring, list_templates, book_sales_meeting]
