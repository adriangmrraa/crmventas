"""
Nova CRM Sales Assistant -- Tool definitions & async dispatcher for OpenAI Realtime function calling.

20 tools organized by category:
  A. Leads (5)
  B. Pipeline (4)
  C. Agenda (3)
  D. Analytics (3)
  E. Navegacion (2)
  F. Comunicacion (3)

Each tool returns a plain string that OpenAI Realtime will speak back to the user.
Navigation tools return JSON strings with type="navigation" for frontend handling.
"""

import json
import logging
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from db import db

logger = logging.getLogger(__name__)


# =============================================================================
# Helper: emit Socket.IO events from Nova tools (for real-time UI sync)
# =============================================================================
async def _nova_emit(event: str, data: Dict[str, Any]):
    """Emit a Socket.IO event so the frontend updates in real-time."""
    try:
        from main import sio, to_json_safe
        await sio.emit(event, to_json_safe(data))
        logger.info(f"NOVA Socket: {event}")
    except Exception as e:
        logger.warning(f"NOVA Socket emit failed ({event}): {e}")


# =============================================================================
# Helpers
# =============================================================================

def _today() -> date:
    return date.today()


def _now() -> datetime:
    return datetime.utcnow()


def _fmt_date(d) -> str:
    if isinstance(d, str):
        d = datetime.fromisoformat(d)
    if isinstance(d, datetime):
        return d.strftime("%d/%m/%Y %H:%M")
    if isinstance(d, date):
        return d.strftime("%d/%m/%Y")
    return str(d)


def _fmt_money(amount) -> str:
    if amount is None:
        return "$0"
    if isinstance(amount, Decimal):
        amount = float(amount)
    return f"${amount:,.2f}"


def _parse_date_str(s: str) -> date:
    """Parse YYYY-MM-DD string to date (args from OpenAI come as strings)."""
    if isinstance(s, date):
        return s
    return datetime.strptime(s, "%Y-%m-%d").date()


def _parse_datetime_str(s: str) -> datetime:
    """Parse datetime string from OpenAI args."""
    if isinstance(s, datetime):
        return s
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse datetime: {s}")


# =============================================================================
# NOVA_CRM_TOOLS_SCHEMA -- OpenAI Realtime function calling format (flat)
# =============================================================================

NOVA_CRM_TOOLS_SCHEMA: List[Dict[str, Any]] = [
    # -------------------------------------------------------------------------
    # A. Leads (5)
    # -------------------------------------------------------------------------
    {
        "type": "function",
        "name": "buscar_lead",
        "description": "Busca lead por nombre, telefono o empresa. Retorna hasta 5 resultados.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Nombre, telefono o empresa del lead",
                }
            },
            "required": ["query"],
        },
    },
    {
        "type": "function",
        "name": "ver_lead",
        "description": "Ver ficha completa de un lead: datos, empresa, estado, vendedor asignado, historial.",
        "parameters": {
            "type": "object",
            "properties": {
                "lead_id": {
                    "type": "string",
                    "description": "UUID del lead",
                }
            },
            "required": ["lead_id"],
        },
    },
    {
        "type": "function",
        "name": "registrar_lead",
        "description": "Registrar un nuevo lead en el CRM.",
        "parameters": {
            "type": "object",
            "properties": {
                "first_name": {"type": "string", "description": "Nombre del lead"},
                "last_name": {"type": "string", "description": "Apellido del lead"},
                "phone_number": {"type": "string", "description": "Telefono del lead"},
                "company": {"type": "string", "description": "Empresa del lead"},
                "source": {"type": "string", "description": "Origen: meta_ads, website, referral, whatsapp_inbound"},
            },
            "required": ["first_name", "phone_number"],
        },
    },
    {
        "type": "function",
        "name": "actualizar_lead",
        "description": "Actualizar un campo especifico de un lead existente.",
        "parameters": {
            "type": "object",
            "properties": {
                "lead_id": {"type": "string", "description": "UUID del lead"},
                "field": {
                    "type": "string",
                    "enum": ["first_name", "last_name", "email", "company", "phone_number", "notes"],
                    "description": "Campo a actualizar",
                },
                "value": {"type": "string", "description": "Nuevo valor del campo"},
            },
            "required": ["lead_id", "field", "value"],
        },
    },
    {
        "type": "function",
        "name": "cambiar_estado_lead",
        "description": "Cambiar estado/etapa de un lead en el pipeline (new, contacted, interested, negotiation, closed_won, closed_lost).",
        "parameters": {
            "type": "object",
            "properties": {
                "lead_id": {"type": "string", "description": "UUID del lead"},
                "new_status": {"type": "string", "description": "Nuevo estado del lead"},
            },
            "required": ["lead_id", "new_status"],
        },
    },

    # -------------------------------------------------------------------------
    # B. Pipeline (4)
    # -------------------------------------------------------------------------
    {
        "type": "function",
        "name": "ver_pipeline",
        "description": "Ver resumen del pipeline completo con cantidad de leads por etapa y valor total.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "type": "function",
        "name": "mover_lead_etapa",
        "description": "Mover un lead a otra etapa del pipeline.",
        "parameters": {
            "type": "object",
            "properties": {
                "lead_id": {"type": "string", "description": "UUID del lead"},
                "new_stage": {"type": "string", "description": "Nuevo codigo de etapa"},
            },
            "required": ["lead_id", "new_stage"],
        },
    },
    {
        "type": "function",
        "name": "resumen_pipeline",
        "description": "Resumen ejecutivo del pipeline: leads por etapa, valor estimado total, tasa de conversion.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "type": "function",
        "name": "leads_por_etapa",
        "description": "Listar los leads de una etapa especifica del pipeline.",
        "parameters": {
            "type": "object",
            "properties": {
                "stage": {
                    "type": "string",
                    "description": "Codigo de etapa (new, contacted, interested, negotiation, closed_won, closed_lost)",
                }
            },
            "required": ["stage"],
        },
    },

    # -------------------------------------------------------------------------
    # C. Agenda (3)
    # -------------------------------------------------------------------------
    {
        "type": "function",
        "name": "ver_agenda_hoy",
        "description": "Ver eventos de agenda de hoy: llamadas, reuniones, seguimientos.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "type": "function",
        "name": "agendar_llamada",
        "description": "Agendar una llamada o reunion con un lead.",
        "parameters": {
            "type": "object",
            "properties": {
                "lead_id": {"type": "string", "description": "UUID del lead (opcional)"},
                "date": {"type": "string", "description": "Fecha en formato YYYY-MM-DD"},
                "time": {"type": "string", "description": "Hora en formato HH:MM (24h)"},
                "title": {"type": "string", "description": "Titulo del evento"},
            },
            "required": ["date", "time", "title"],
        },
    },
    {
        "type": "function",
        "name": "proxima_llamada",
        "description": "Ver la proxima llamada o evento agendado.",
        "parameters": {"type": "object", "properties": {}},
    },

    # -------------------------------------------------------------------------
    # D. Analytics (3)
    # -------------------------------------------------------------------------
    {
        "type": "function",
        "name": "resumen_ventas",
        "description": "Resumen de ventas: total leads, conversiones, revenue del periodo.",
        "parameters": {
            "type": "object",
            "properties": {
                "periodo": {
                    "type": "string",
                    "enum": ["hoy", "semana", "mes"],
                    "description": "Periodo del resumen",
                }
            },
            "required": ["periodo"],
        },
    },
    {
        "type": "function",
        "name": "rendimiento_vendedor",
        "description": "Metricas de rendimiento de un vendedor: leads asignados, conversiones, tiempo de respuesta.",
        "parameters": {
            "type": "object",
            "properties": {
                "seller_name": {
                    "type": "string",
                    "description": "Nombre del vendedor",
                }
            },
            "required": ["seller_name"],
        },
    },
    {
        "type": "function",
        "name": "conversion_rate",
        "description": "Tasa de conversion general del pipeline: leads totales vs cerrados ganados.",
        "parameters": {"type": "object", "properties": {}},
    },

    # -------------------------------------------------------------------------
    # E. Navegacion (2)
    # -------------------------------------------------------------------------
    {
        "type": "function",
        "name": "ir_a_pagina",
        "description": "Navegar a una pagina del CRM.",
        "parameters": {
            "type": "object",
            "properties": {
                "page": {
                    "type": "string",
                    "enum": [
                        "dashboard", "leads", "pipeline", "clientes", "agenda",
                        "chats", "analytics", "marketing", "vendedores", "configuracion",
                    ],
                    "description": "Pagina destino",
                }
            },
            "required": ["page"],
        },
    },
    {
        "type": "function",
        "name": "ir_a_lead",
        "description": "Abrir la ficha de un lead especifico.",
        "parameters": {
            "type": "object",
            "properties": {
                "lead_id": {
                    "type": "string",
                    "description": "UUID del lead",
                }
            },
            "required": ["lead_id"],
        },
    },

    # -------------------------------------------------------------------------
    # F. Comunicacion (3)
    # -------------------------------------------------------------------------
    {
        "type": "function",
        "name": "ver_chats_recientes",
        "description": "Ver las ultimas conversaciones de WhatsApp con leads.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Cantidad de chats a mostrar (default 5)",
                }
            },
        },
    },
    {
        "type": "function",
        "name": "enviar_whatsapp",
        "description": "Enviar un mensaje de WhatsApp a un lead por su telefono.",
        "parameters": {
            "type": "object",
            "properties": {
                "phone": {"type": "string", "description": "Telefono del destinatario"},
                "message": {"type": "string", "description": "Contenido del mensaje"},
            },
            "required": ["phone", "message"],
        },
    },
    {
        "type": "function",
        "name": "ver_sellers",
        "description": "Listar vendedores activos con sus metricas basicas.",
        "parameters": {"type": "object", "properties": {}},
    },
]


# =============================================================================
# TOOL IMPLEMENTATIONS
# =============================================================================

# --- A. Leads ---

async def _buscar_lead(args: Dict, tenant_id: int) -> str:
    q = args.get("query", "").strip()
    if not q:
        return "Necesito un nombre, telefono o empresa para buscar."

    like_q = f"%{q}%"
    rows = await db.pool.fetch(
        """
        SELECT id, first_name, last_name, phone_number, company, status, source,
               email, estimated_value
        FROM leads
        WHERE tenant_id = $1
          AND (
            (first_name || ' ' || COALESCE(last_name, '')) ILIKE $2
            OR first_name ILIKE $2 OR last_name ILIKE $2
            OR phone_number ILIKE $2
            OR company ILIKE $2
            OR email ILIKE $2
            OR REGEXP_REPLACE(phone_number, '[^0-9]', '', 'g') LIKE REGEXP_REPLACE($2, '[^0-9]', '', 'g')
          )
        ORDER BY
          CASE WHEN LOWER(first_name) = LOWER($3) THEN 0
               WHEN company ILIKE $2 THEN 1
               ELSE 2 END,
          updated_at DESC
        LIMIT 5
        """,
        tenant_id, like_q, q,
    )

    if not rows:
        return f"No encontre leads con '{q}'."

    lines = [f"Encontre {len(rows)} lead(s):"]
    for r in rows:
        name = f"{r['first_name'] or ''} {r['last_name'] or ''}".strip() or "Sin nombre"
        company = f" | {r['company']}" if r['company'] else ""
        value = f" | {_fmt_money(r['estimated_value'])}" if r['estimated_value'] else ""
        lines.append(f"  - {name} ({r['phone_number']}){company} | {r['status']}{value} [ID: {r['id']}]")
    return "\n".join(lines)


async def _ver_lead(args: Dict, tenant_id: int) -> str:
    lead_id = args.get("lead_id", "").strip()
    if not lead_id:
        return "Necesito el ID del lead."

    row = await db.pool.fetchrow(
        """
        SELECT l.*, s.first_name AS seller_first, s.last_name AS seller_last
        FROM leads l
        LEFT JOIN sellers s ON s.user_id = l.assigned_seller_id
        WHERE l.id = $1 AND l.tenant_id = $2
        """,
        uuid.UUID(lead_id), tenant_id,
    )
    if not row:
        return "No encontre ese lead."

    name = f"{row['first_name'] or ''} {row['last_name'] or ''}".strip() or "Sin nombre"
    seller = f"{row['seller_first'] or ''} {row['seller_last'] or ''}".strip() if row['seller_first'] else "Sin asignar"
    company = row['company'] or "Sin empresa"
    value = _fmt_money(row['estimated_value']) if row.get('estimated_value') else "Sin valor"

    # Recent activity count
    msg_count = await db.pool.fetchval(
        "SELECT COUNT(*) FROM chat_messages WHERE from_number = $1 AND tenant_id = $2",
        row['phone_number'], tenant_id,
    ) or 0

    return (
        f"Lead: {name}\n"
        f"  Telefono: {row['phone_number']}\n"
        f"  Email: {row.get('email') or 'No registrado'}\n"
        f"  Empresa: {company}\n"
        f"  Estado: {row['status']}\n"
        f"  Origen: {row.get('source') or 'Desconocido'}\n"
        f"  Valor estimado: {value}\n"
        f"  Vendedor: {seller}\n"
        f"  Mensajes: {msg_count}\n"
        f"  Score: {row.get('score', 0) or 0}\n"
        f"  Creado: {_fmt_date(row['created_at'])}\n"
        f"  Actualizado: {_fmt_date(row['updated_at'])}"
    )


async def _registrar_lead(args: Dict, tenant_id: int) -> str:
    first_name = args.get("first_name", "").strip()
    phone = args.get("phone_number", "").strip()
    if not first_name or not phone:
        return "Necesito al menos nombre y telefono para registrar un lead."

    last_name = args.get("last_name", "").strip() or None
    company = args.get("company", "").strip() or None
    source = args.get("source", "manual").strip()

    # Check duplicate
    existing = await db.pool.fetchval(
        "SELECT id FROM leads WHERE tenant_id = $1 AND phone_number = $2",
        tenant_id, phone,
    )
    if existing:
        return f"Ya existe un lead con ese telefono (ID: {existing})."

    lead_id = await db.pool.fetchval(
        """
        INSERT INTO leads (tenant_id, phone_number, first_name, last_name, company, source, status)
        VALUES ($1, $2, $3, $4, $5, $6, 'new')
        RETURNING id
        """,
        tenant_id, phone, first_name, last_name, company, source,
    )

    await _nova_emit("LEAD_CREATED", {"tenant_id": tenant_id, "lead_id": str(lead_id)})
    return f"Lead registrado: {first_name} {last_name or ''} ({phone}). ID: {lead_id}"


async def _actualizar_lead(args: Dict, tenant_id: int) -> str:
    lead_id = args.get("lead_id", "").strip()
    field = args.get("field", "").strip()
    value = args.get("value", "").strip()

    if not lead_id or not field or not value:
        return "Necesito lead_id, campo y valor."

    allowed = {"first_name", "last_name", "email", "company", "phone_number", "notes"}
    if field not in allowed:
        return f"Campo '{field}' no permitido. Campos validos: {', '.join(sorted(allowed))}."

    # notes is not a standard column, map to a safe update
    if field == "notes":
        # notes stored in score_breakdown or we skip -- use company as fallback
        return "El campo 'notes' no esta disponible como columna directa. Usa otro campo."

    result = await db.pool.execute(
        f"UPDATE leads SET {field} = $1, updated_at = NOW() WHERE id = $2 AND tenant_id = $3",
        value, uuid.UUID(lead_id), tenant_id,
    )

    if "UPDATE 0" in result:
        return "No encontre ese lead."

    await _nova_emit("LEAD_UPDATED", {"tenant_id": tenant_id, "lead_id": lead_id})
    return f"Lead actualizado: {field} = '{value}'."


async def _cambiar_estado_lead(args: Dict, tenant_id: int) -> str:
    lead_id = args.get("lead_id", "").strip()
    new_status = args.get("new_status", "").strip()

    if not lead_id or not new_status:
        return "Necesito lead_id y nuevo estado."

    # Validate status exists in lead_statuses for this tenant
    valid = await db.pool.fetchval(
        "SELECT code FROM lead_statuses WHERE tenant_id = $1 AND code = $2 AND is_active = true",
        tenant_id, new_status,
    )
    if not valid:
        # Fallback: list available statuses
        statuses = await db.pool.fetch(
            "SELECT code, name FROM lead_statuses WHERE tenant_id = $1 AND is_active = true ORDER BY sort_order",
            tenant_id,
        )
        if statuses:
            options = ", ".join(f"{s['code']} ({s['name']})" for s in statuses)
            return f"Estado '{new_status}' no valido. Opciones: {options}"
        # If no lead_statuses table or no rows, allow raw status
        pass

    old_status = await db.pool.fetchval(
        "SELECT status FROM leads WHERE id = $1 AND tenant_id = $2",
        uuid.UUID(lead_id), tenant_id,
    )
    if old_status is None:
        return "No encontre ese lead."

    await db.pool.execute(
        "UPDATE leads SET status = $1, updated_at = NOW() WHERE id = $2 AND tenant_id = $3",
        new_status, uuid.UUID(lead_id), tenant_id,
    )

    await _nova_emit("LEAD_UPDATED", {"tenant_id": tenant_id, "lead_id": lead_id})
    return f"Lead movido de '{old_status}' a '{new_status}'."


# --- B. Pipeline ---

async def _ver_pipeline(args: Dict, tenant_id: int) -> str:
    rows = await db.pool.fetch(
        """
        SELECT ls.code, ls.name, ls.color,
               COUNT(l.id) AS cnt,
               COALESCE(SUM(l.estimated_value), 0) AS total_value
        FROM lead_statuses ls
        LEFT JOIN leads l ON l.tenant_id = ls.tenant_id AND l.status = ls.code
        WHERE ls.tenant_id = $1 AND ls.is_active = true
        GROUP BY ls.code, ls.name, ls.color, ls.sort_order
        ORDER BY ls.sort_order
        """,
        tenant_id,
    )

    if not rows:
        # Fallback: group by raw status
        rows = await db.pool.fetch(
            """
            SELECT status AS code, status AS name, '' AS color,
                   COUNT(*) AS cnt,
                   COALESCE(SUM(estimated_value), 0) AS total_value
            FROM leads
            WHERE tenant_id = $1
            GROUP BY status
            ORDER BY MIN(created_at)
            """,
            tenant_id,
        )

    if not rows:
        return "Pipeline vacio. No hay leads registrados."

    total_leads = sum(r['cnt'] for r in rows)
    total_val = sum(r['total_value'] for r in rows)

    lines = [f"Pipeline ({total_leads} leads | Valor total: {_fmt_money(total_val)}):"]
    for r in rows:
        lines.append(f"  {r['name']}: {r['cnt']} leads | {_fmt_money(r['total_value'])}")
    return "\n".join(lines)


async def _mover_lead_etapa(args: Dict, tenant_id: int) -> str:
    # Same logic as cambiar_estado_lead
    return await _cambiar_estado_lead(
        {"lead_id": args.get("lead_id", ""), "new_status": args.get("new_stage", "")},
        tenant_id,
    )


async def _resumen_pipeline(args: Dict, tenant_id: int) -> str:
    stats = await db.pool.fetchrow(
        """
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE status = 'closed_won') AS won,
            COUNT(*) FILTER (WHERE status = 'closed_lost') AS lost,
            COUNT(*) FILTER (WHERE status NOT IN ('closed_won', 'closed_lost')) AS active,
            COALESCE(SUM(estimated_value), 0) AS total_value,
            COALESCE(SUM(estimated_value) FILTER (WHERE status = 'closed_won'), 0) AS won_value,
            COALESCE(SUM(estimated_value) FILTER (WHERE status NOT IN ('closed_won', 'closed_lost')), 0) AS pipeline_value
        FROM leads
        WHERE tenant_id = $1
        """,
        tenant_id,
    )

    total = stats['total'] or 0
    won = stats['won'] or 0
    lost = stats['lost'] or 0
    active = stats['active'] or 0
    conv_rate = f"{(won / total * 100):.1f}%" if total > 0 else "0%"

    return (
        f"Resumen del Pipeline:\n"
        f"  Total leads: {total}\n"
        f"  Activos: {active}\n"
        f"  Ganados: {won} | Perdidos: {lost}\n"
        f"  Tasa de conversion: {conv_rate}\n"
        f"  Valor en pipeline: {_fmt_money(stats['pipeline_value'])}\n"
        f"  Valor ganado: {_fmt_money(stats['won_value'])}"
    )


async def _leads_por_etapa(args: Dict, tenant_id: int) -> str:
    stage = args.get("stage", "").strip()
    if not stage:
        return "Necesito el codigo de etapa."

    rows = await db.pool.fetch(
        """
        SELECT id, first_name, last_name, phone_number, company, estimated_value, updated_at
        FROM leads
        WHERE tenant_id = $1 AND status = $2
        ORDER BY updated_at DESC
        LIMIT 10
        """,
        tenant_id, stage,
    )

    if not rows:
        return f"No hay leads en la etapa '{stage}'."

    lines = [f"Leads en '{stage}' ({len(rows)}):"]
    for r in rows:
        name = f"{r['first_name'] or ''} {r['last_name'] or ''}".strip() or "Sin nombre"
        company = f" | {r['company']}" if r['company'] else ""
        value = f" | {_fmt_money(r['estimated_value'])}" if r['estimated_value'] else ""
        lines.append(f"  - {name}{company}{value} | {_fmt_date(r['updated_at'])}")
    return "\n".join(lines)


# --- C. Agenda ---

async def _ver_agenda_hoy(args: Dict, tenant_id: int, user_id: str) -> str:
    today = _today()
    tomorrow = today + timedelta(days=1)

    rows = await db.pool.fetch(
        """
        SELECT sae.id, sae.title, sae.start_datetime, sae.end_datetime, sae.status,
               l.first_name AS lead_first, l.last_name AS lead_last, l.company
        FROM seller_agenda_events sae
        LEFT JOIN leads l ON l.id = sae.lead_id
        WHERE sae.tenant_id = $1
          AND sae.start_datetime >= $2 AND sae.start_datetime < $3
          AND sae.status != 'cancelled'
        ORDER BY sae.start_datetime
        """,
        tenant_id, today, tomorrow,
    )

    if not rows:
        return "No hay eventos en la agenda de hoy."

    lines = [f"Agenda de hoy ({_fmt_date(today)}): {len(rows)} evento(s)"]
    for r in rows:
        lead_name = f"{r['lead_first'] or ''} {r['lead_last'] or ''}".strip()
        lead_info = f" con {lead_name}" if lead_name else ""
        company = f" ({r['company']})" if r.get('company') else ""
        start = r['start_datetime'].strftime("%H:%M") if r['start_datetime'] else "?"
        end = r['end_datetime'].strftime("%H:%M") if r['end_datetime'] else "?"
        lines.append(f"  - {start}-{end}: {r['title']}{lead_info}{company} [{r['status']}]")
    return "\n".join(lines)


async def _agendar_llamada(args: Dict, tenant_id: int, user_id: str) -> str:
    date_str = args.get("date", "").strip()
    time_str = args.get("time", "").strip()
    title = args.get("title", "").strip()

    if not date_str or not time_str or not title:
        return "Necesito fecha, hora y titulo para agendar."

    d = _parse_date_str(date_str)
    start_dt = _parse_datetime_str(f"{date_str} {time_str}")
    end_dt = start_dt + timedelta(minutes=30)

    lead_id = args.get("lead_id")
    lead_uuid = uuid.UUID(lead_id) if lead_id else None

    # Resolve seller_id from user_id
    seller_id = await db.pool.fetchval(
        "SELECT id FROM sellers WHERE user_id = $1 AND tenant_id = $2",
        uuid.UUID(user_id), tenant_id,
    )
    if not seller_id:
        # Fallback: use first active seller or professional
        seller_id = await db.pool.fetchval(
            "SELECT id FROM professionals WHERE tenant_id = $1 AND is_active = true LIMIT 1",
            tenant_id,
        )
    if not seller_id:
        return "No se encontro un vendedor asociado a tu usuario."

    event_id = await db.pool.fetchval(
        """
        INSERT INTO seller_agenda_events (tenant_id, seller_id, title, start_datetime, end_datetime, lead_id, status)
        VALUES ($1, $2, $3, $4, $5, $6, 'scheduled')
        RETURNING id
        """,
        tenant_id, seller_id, title, start_dt, end_dt, lead_uuid,
    )

    await _nova_emit("AGENDA_UPDATED", {"tenant_id": tenant_id})

    lead_info = ""
    if lead_uuid:
        lead_row = await db.pool.fetchrow(
            "SELECT first_name, last_name FROM leads WHERE id = $1 AND tenant_id = $2",
            lead_uuid, tenant_id,
        )
        if lead_row:
            lead_info = f" con {lead_row['first_name'] or ''} {lead_row['last_name'] or ''}".strip()

    return f"Evento agendado: '{title}'{lead_info} el {_fmt_date(d)} a las {time_str}."


async def _proxima_llamada(args: Dict, tenant_id: int, user_id: str) -> str:
    now = _now()

    row = await db.pool.fetchrow(
        """
        SELECT sae.title, sae.start_datetime, sae.end_datetime,
               l.first_name AS lead_first, l.last_name AS lead_last, l.phone_number AS lead_phone, l.company
        FROM seller_agenda_events sae
        LEFT JOIN leads l ON l.id = sae.lead_id
        WHERE sae.tenant_id = $1
          AND sae.start_datetime >= $2
          AND sae.status = 'scheduled'
        ORDER BY sae.start_datetime
        LIMIT 1
        """,
        tenant_id, now,
    )

    if not row:
        return "No tenes llamadas o eventos proximos."

    lead_name = f"{row['lead_first'] or ''} {row['lead_last'] or ''}".strip()
    lead_info = f" con {lead_name}" if lead_name else ""
    company = f" ({row['company']})" if row.get('company') else ""
    phone = f" | Tel: {row['lead_phone']}" if row.get('lead_phone') else ""

    return (
        f"Proximo evento: {row['title']}{lead_info}{company}\n"
        f"  Horario: {_fmt_date(row['start_datetime'])}{phone}"
    )


# --- D. Analytics ---

async def _resumen_ventas(args: Dict, tenant_id: int) -> str:
    periodo = args.get("periodo", "semana")
    days_map = {"hoy": 0, "semana": 7, "mes": 30}
    days = days_map.get(periodo, 7)

    if days == 0:
        since = _today()
    else:
        since = _today() - timedelta(days=days)

    stats = await db.pool.fetchrow(
        """
        SELECT
            COUNT(*) AS total_leads,
            COUNT(*) FILTER (WHERE status = 'closed_won') AS won,
            COUNT(*) FILTER (WHERE status = 'closed_lost') AS lost,
            COALESCE(SUM(estimated_value) FILTER (WHERE status = 'closed_won'), 0) AS revenue
        FROM leads
        WHERE tenant_id = $1 AND created_at::date >= $2
        """,
        tenant_id, since,
    )

    # Also count new leads vs total active
    total = stats['total_leads'] or 0
    won = stats['won'] or 0
    lost = stats['lost'] or 0
    revenue = stats['revenue'] or 0
    conv_rate = f"{(won / total * 100):.1f}%" if total > 0 else "0%"

    period_label = {"hoy": "hoy", "semana": "esta semana", "mes": "este mes"}.get(periodo, periodo)

    return (
        f"Resumen de ventas ({period_label}):\n"
        f"  Leads nuevos: {total}\n"
        f"  Cerrados ganados: {won}\n"
        f"  Cerrados perdidos: {lost}\n"
        f"  Tasa de conversion: {conv_rate}\n"
        f"  Revenue: {_fmt_money(revenue)}"
    )


async def _rendimiento_vendedor(args: Dict, tenant_id: int) -> str:
    seller_name = args.get("seller_name", "").strip()
    if not seller_name:
        return "Necesito el nombre del vendedor."

    like_name = f"%{seller_name}%"
    seller = await db.pool.fetchrow(
        """
        SELECT s.id, s.user_id, s.first_name, s.last_name
        FROM sellers s
        WHERE s.tenant_id = $1
          AND (s.first_name ILIKE $2 OR s.last_name ILIKE $2
               OR (s.first_name || ' ' || COALESCE(s.last_name, '')) ILIKE $2)
        LIMIT 1
        """,
        tenant_id, like_name,
    )
    if not seller:
        return f"No encontre un vendedor con nombre '{seller_name}'."

    since = _today() - timedelta(days=30)
    seller_user_id = seller['user_id']

    lead_stats = await db.pool.fetchrow(
        """
        SELECT
            COUNT(*) AS total_assigned,
            COUNT(*) FILTER (WHERE status = 'closed_won') AS won,
            COUNT(*) FILTER (WHERE status = 'closed_lost') AS lost,
            COALESCE(SUM(estimated_value) FILTER (WHERE status = 'closed_won'), 0) AS revenue
        FROM leads
        WHERE tenant_id = $1 AND assigned_seller_id = $2
        """,
        tenant_id, seller_user_id,
    )

    # Metrics from seller_metrics if available
    metrics = await db.pool.fetchrow(
        """
        SELECT total_conversations, total_messages_sent, avg_response_time_seconds,
               leads_assigned, leads_converted
        FROM seller_metrics
        WHERE seller_id = $1 AND tenant_id = $2
        ORDER BY metrics_period_start DESC
        LIMIT 1
        """,
        seller_user_id, tenant_id,
    )

    name = f"{seller['first_name'] or ''} {seller['last_name'] or ''}".strip()
    total = lead_stats['total_assigned'] or 0
    won = lead_stats['won'] or 0
    conv = f"{(won / total * 100):.1f}%" if total > 0 else "0%"

    result = (
        f"Rendimiento de {name}:\n"
        f"  Leads asignados: {total}\n"
        f"  Cerrados ganados: {won}\n"
        f"  Cerrados perdidos: {lead_stats['lost'] or 0}\n"
        f"  Conversion: {conv}\n"
        f"  Revenue: {_fmt_money(lead_stats['revenue'])}"
    )

    if metrics:
        resp_time = metrics.get('avg_response_time_seconds')
        resp_str = f"{resp_time // 60}min {resp_time % 60}s" if resp_time else "N/A"
        result += (
            f"\n  Conversaciones: {metrics.get('total_conversations', 0)}"
            f"\n  Mensajes enviados: {metrics.get('total_messages_sent', 0)}"
            f"\n  Tiempo de respuesta promedio: {resp_str}"
        )

    return result


async def _conversion_rate(args: Dict, tenant_id: int) -> str:
    stats = await db.pool.fetchrow(
        """
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE status = 'closed_won') AS won,
            COUNT(*) FILTER (WHERE status = 'closed_lost') AS lost,
            COUNT(*) FILTER (WHERE status NOT IN ('closed_won', 'closed_lost')) AS active
        FROM leads
        WHERE tenant_id = $1
        """,
        tenant_id,
    )

    total = stats['total'] or 0
    won = stats['won'] or 0
    lost = stats['lost'] or 0
    active = stats['active'] or 0
    decided = won + lost

    overall = f"{(won / total * 100):.1f}%" if total > 0 else "0%"
    decided_rate = f"{(won / decided * 100):.1f}%" if decided > 0 else "0%"

    return (
        f"Tasas de conversion:\n"
        f"  General (ganados / total): {overall} ({won}/{total})\n"
        f"  Sobre decididos (ganados / ganados+perdidos): {decided_rate} ({won}/{decided})\n"
        f"  Leads activos en pipeline: {active}"
    )


# --- E. Navegacion ---

PAGE_ROUTES = {
    "dashboard": "/dashboard",
    "leads": "/leads",
    "pipeline": "/pipeline",
    "clientes": "/clientes",
    "agenda": "/agenda",
    "chats": "/chats",
    "analytics": "/analytics",
    "marketing": "/marketing",
    "vendedores": "/vendedores",
    "configuracion": "/configuracion",
}


async def _ir_a_pagina(args: Dict) -> str:
    page = args.get("page", "").strip()
    route = PAGE_ROUTES.get(page)
    if not route:
        return f"Pagina '{page}' no reconocida. Opciones: {', '.join(PAGE_ROUTES.keys())}"
    return json.dumps({"type": "navigation", "route": route})


async def _ir_a_lead(args: Dict) -> str:
    lead_id = args.get("lead_id", "").strip()
    if not lead_id:
        return "Necesito el ID del lead."
    return json.dumps({"type": "navigation", "route": f"/leads/{lead_id}"})


# --- F. Comunicacion ---

async def _ver_chats_recientes(args: Dict, tenant_id: int) -> str:
    limit = args.get("limit", 5)
    if not isinstance(limit, int):
        try:
            limit = int(limit)
        except (ValueError, TypeError):
            limit = 5
    limit = min(max(limit, 1), 15)

    rows = await db.pool.fetch(
        """
        SELECT DISTINCT ON (cm.from_number)
            cm.from_number,
            cm.content,
            cm.role,
            cm.created_at,
            l.first_name AS lead_first,
            l.last_name AS lead_last,
            l.company
        FROM chat_messages cm
        LEFT JOIN leads l ON l.phone_number = cm.from_number AND l.tenant_id = cm.tenant_id
        WHERE cm.tenant_id = $1
        ORDER BY cm.from_number, cm.created_at DESC
        LIMIT $2
        """,
        tenant_id, limit,
    )

    if not rows:
        return "No hay conversaciones recientes."

    lines = [f"Ultimos {len(rows)} chats:"]
    for r in rows:
        name = f"{r['lead_first'] or ''} {r['lead_last'] or ''}".strip() or r['from_number']
        company = f" ({r['company']})" if r.get('company') else ""
        preview = (r['content'] or "")[:60]
        if len(r['content'] or "") > 60:
            preview += "..."
        ago = _fmt_date(r['created_at'])
        lines.append(f"  - {name}{company}: \"{preview}\" ({ago})")
    return "\n".join(lines)


async def _enviar_whatsapp(args: Dict, tenant_id: int) -> str:
    phone = args.get("phone", "").strip()
    message = args.get("message", "").strip()

    if not phone or not message:
        return "Necesito telefono y mensaje."

    try:
        from ycloud_client import send_whatsapp_message
        await send_whatsapp_message(phone, message, tenant_id)

        # Save to chat_messages
        await db.pool.execute(
            """
            INSERT INTO chat_messages (from_number, role, content, tenant_id)
            VALUES ($1, 'assistant', $2, $3)
            """,
            phone, message, tenant_id,
        )

        await _nova_emit("CHAT_MESSAGE_SENT", {"tenant_id": tenant_id, "phone": phone})
        return f"Mensaje enviado a {phone}."
    except ImportError:
        return "Servicio de WhatsApp no disponible en este entorno."
    except Exception as e:
        logger.error(f"Error sending WhatsApp via Nova: {e}")
        return f"Error al enviar mensaje: {str(e)[:100]}"


async def _ver_sellers(args: Dict, tenant_id: int) -> str:
    rows = await db.pool.fetch(
        """
        SELECT s.id, s.first_name, s.last_name, s.email, s.phone_number, s.is_active,
               (SELECT COUNT(*) FROM leads l WHERE l.assigned_seller_id = s.user_id AND l.tenant_id = $1) AS leads_count,
               (SELECT COUNT(*) FROM leads l WHERE l.assigned_seller_id = s.user_id AND l.tenant_id = $1 AND l.status = 'closed_won') AS won_count
        FROM sellers s
        WHERE s.tenant_id = $1
        ORDER BY s.is_active DESC, s.first_name
        """,
        tenant_id,
    )

    if not rows:
        return "No hay vendedores registrados."

    lines = [f"Vendedores ({len(rows)}):"]
    for r in rows:
        name = f"{r['first_name'] or ''} {r['last_name'] or ''}".strip()
        status = "Activo" if r['is_active'] else "Inactivo"
        leads = r['leads_count'] or 0
        won = r['won_count'] or 0
        conv = f"{(won / leads * 100):.0f}%" if leads > 0 else "0%"
        lines.append(f"  - {name} | {status} | {leads} leads | {won} ganados ({conv}) | {r['email'] or ''}")
    return "\n".join(lines)


# =============================================================================
# DISPATCHER
# =============================================================================

async def execute_nova_crm_tool(
    name: str,
    args: Dict[str, Any],
    tenant_id: int,
    user_role: str,
    user_id: str,
) -> str:
    """
    Execute a Nova CRM tool by name and return the response string.

    Args:
        name: Tool name (must match one of NOVA_CRM_TOOLS_SCHEMA entries)
        args: Tool arguments as parsed from OpenAI function calling
        tenant_id: Current tenant context (resolved from session)
        user_role: User role ('ceo', 'seller', 'setter', 'closer')
        user_id: User UUID string

    Returns:
        String response for OpenAI Realtime to speak
    """
    try:
        # A. Leads
        if name == "buscar_lead":
            return await _buscar_lead(args, tenant_id)
        elif name == "ver_lead":
            return await _ver_lead(args, tenant_id)
        elif name == "registrar_lead":
            return await _registrar_lead(args, tenant_id)
        elif name == "actualizar_lead":
            return await _actualizar_lead(args, tenant_id)
        elif name == "cambiar_estado_lead":
            return await _cambiar_estado_lead(args, tenant_id)

        # B. Pipeline
        elif name == "ver_pipeline":
            return await _ver_pipeline(args, tenant_id)
        elif name == "mover_lead_etapa":
            return await _mover_lead_etapa(args, tenant_id)
        elif name == "resumen_pipeline":
            return await _resumen_pipeline(args, tenant_id)
        elif name == "leads_por_etapa":
            return await _leads_por_etapa(args, tenant_id)

        # C. Agenda
        elif name == "ver_agenda_hoy":
            return await _ver_agenda_hoy(args, tenant_id, user_id)
        elif name == "agendar_llamada":
            return await _agendar_llamada(args, tenant_id, user_id)
        elif name == "proxima_llamada":
            return await _proxima_llamada(args, tenant_id, user_id)

        # D. Analytics
        elif name == "resumen_ventas":
            return await _resumen_ventas(args, tenant_id)
        elif name == "rendimiento_vendedor":
            return await _rendimiento_vendedor(args, tenant_id)
        elif name == "conversion_rate":
            return await _conversion_rate(args, tenant_id)

        # E. Navegacion
        elif name == "ir_a_pagina":
            return await _ir_a_pagina(args)
        elif name == "ir_a_lead":
            return await _ir_a_lead(args)

        # F. Comunicacion
        elif name == "ver_chats_recientes":
            return await _ver_chats_recientes(args, tenant_id)
        elif name == "enviar_whatsapp":
            return await _enviar_whatsapp(args, tenant_id)
        elif name == "ver_sellers":
            return await _ver_sellers(args, tenant_id)

        else:
            return f"Tool '{name}' no reconocida."

    except Exception as e:
        logger.error(f"Nova CRM tool error ({name}): {e}", exc_info=True)
        return f"Error ejecutando {name}: {str(e)[:150]}"
