"""
DEV-36: AI Agent Script & Personality Configuration Routes

Endpoints:
  GET  /admin/core/settings/ai-agent           — Returns current AI agent config for tenant
  PUT  /admin/core/settings/ai-agent           — CEO only, updates AI agent config
  POST /admin/setup/seed-ai-agent              — Seed default Codexy-specific agent config (admin token only)
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from db import db
from core.security import verify_admin_token, get_resolved_tenant_id

logger = logging.getLogger("ai_agent_routes")

router = APIRouter()
setup_router = APIRouter()

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")


# ─── Pydantic Schemas ────────────────────────────────────────────────────────────

class QualificationQuestion(BaseModel):
    label: str = Field(..., description="Short label for the question, e.g. 'Necesidad'")
    example: str = Field("", description="Example phrasing the agent should use")


class ObjectionResponse(BaseModel):
    objection: str = Field(..., description="What the prospect might say")
    response: str = Field(..., description="How the agent should respond")


class AIAgentConfigResponse(BaseModel):
    ai_agent_name: Optional[str] = None
    ai_tone: Optional[str] = None
    ai_services_description: Optional[str] = None
    ai_company_description: Optional[str] = None
    ai_qualification_questions: Optional[List[Any]] = None
    ai_objection_responses: Optional[List[Any]] = None
    ai_system_prompt: Optional[str] = None
    business_hours: Optional[Dict[str, Any]] = None
    tenant_name: Optional[str] = None


class AIAgentConfigUpdate(BaseModel):
    ai_agent_name: Optional[str] = None
    ai_tone: Optional[str] = None
    ai_services_description: Optional[str] = None
    ai_company_description: Optional[str] = None
    ai_qualification_questions: Optional[List[Any]] = None
    ai_objection_responses: Optional[List[Any]] = None
    ai_system_prompt: Optional[str] = None
    business_hours: Optional[Dict[str, Any]] = None


# ─── Default Codexy Agent Config (Seed) ──────────────────────────────────────────

DEFAULT_AI_AGENT_CONFIG = {
    "ai_agent_name": "Mati",
    "ai_tone": "informal_argentino",
    "ai_services_description": (
        "- Desarrollo de software a medida (web, mobile, APIs)\n"
        "- CRM de ventas con IA integrada (este mismo producto)\n"
        "- Automatizacion de procesos con inteligencia artificial\n"
        "- Chatbots y asistentes virtuales para WhatsApp\n"
        "- Integraciones con APIs externas (Meta, Google, pasarelas de pago)\n"
        "- Consultoria tecnologica y arquitectura de sistemas"
    ),
    "ai_company_description": (
        "En Codexy creamos software que transforma negocios. Somos un equipo argentino "
        "especializado en desarrollo a medida con IA. Nuestro diferencial: no vendemos "
        "productos genericos, construimos soluciones que se adaptan exactamente a lo que "
        "tu empresa necesita. Desde CRMs inteligentes hasta automatizaciones complejas, "
        "hacemos que la tecnologia trabaje para vos."
    ),
    "ai_qualification_questions": [
        {
            "label": "Necesidad",
            "example": "Contame, que estas buscando? Que problema o necesidad tenes hoy?"
        },
        {
            "label": "Timeline",
            "example": "Para cuando necesitarias tenerlo funcionando?"
        },
        {
            "label": "Presupuesto",
            "example": "Tenes un rango de inversion en mente? Asi te doy una idea si estamos en la misma pagina."
        },
        {
            "label": "Tamano de empresa",
            "example": "Cuantas personas son en el equipo? Asi dimensiono mejor la solucion."
        },
        {
            "label": "Necesidades especificas",
            "example": "Hay alguna integracion o funcionalidad puntual que sea clave para vos?"
        }
    ],
    "ai_objection_responses": [
        {
            "objection": "Es muy caro / no tengo presupuesto",
            "response": "Entiendo, la inversion depende mucho del alcance. Podemos arrancar con un MVP mas acotado y escalar despues. Te cuento como funciona?"
        },
        {
            "objection": "Ya tengo un sistema / uso otra herramienta",
            "response": "Genial que ya tengas algo andando. Muchos clientes vienen porque quieren algo mas adaptado a su proceso. Que es lo que no te cierra del sistema actual?"
        },
        {
            "objection": "Necesito pensarlo / lo voy a evaluar",
            "response": "Dale, tomate tu tiempo. Si queres te agendo una llamada rapida con el equipo para que te saquen todas las dudas. Sin compromiso, eh."
        },
        {
            "objection": "No tengo tiempo ahora",
            "response": "Cero drama. Cuando te venga bien charlamos. Te dejo agendar una llamada para cuando puedas?"
        },
        {
            "objection": "Estoy viendo otras opciones / comparando",
            "response": "Me parece bien comparar. Lo que nos diferencia es que hacemos todo 100% a medida, no es un producto generico. Si queres te muestro un caso similar al tuyo."
        }
    ],
    "business_hours": {
        "lunes_a_viernes": "09:00 - 18:00",
        "sabado": "10:00 - 13:00",
        "domingo": "cerrado"
    }
}


# ─── GET /admin/core/settings/ai-agent ───────────────────────────────────────────

@router.get("/admin/core/settings/ai-agent", tags=["AI Agent Config"])
async def get_ai_agent_config(
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """Returns the current AI agent configuration for the tenant."""
    row = await db.fetchrow(
        """SELECT clinic_name, ai_agent_name, ai_tone, ai_services_description,
                  ai_company_description, ai_qualification_questions,
                  ai_objection_responses, ai_system_prompt, business_hours
           FROM tenants WHERE id = $1""",
        tenant_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return {
        "tenant_name": row["clinic_name"],
        "ai_agent_name": row.get("ai_agent_name"),
        "ai_tone": row.get("ai_tone"),
        "ai_services_description": row.get("ai_services_description"),
        "ai_company_description": row.get("ai_company_description"),
        "ai_qualification_questions": row.get("ai_qualification_questions") or [],
        "ai_objection_responses": row.get("ai_objection_responses") or [],
        "ai_system_prompt": row.get("ai_system_prompt"),
        "business_hours": row.get("business_hours") or {},
    }


# ─── PUT /admin/core/settings/ai-agent ───────────────────────────────────────────

@router.put("/admin/core/settings/ai-agent", tags=["AI Agent Config"])
async def update_ai_agent_config(
    payload: AIAgentConfigUpdate,
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """
    Updates the AI agent configuration. CEO only.
    Only non-null fields in the payload are updated (partial update).
    """
    if user_data.role != "ceo":
        raise HTTPException(status_code=403, detail="CEO only: AI agent config requires CEO role")

    # Build dynamic SET clause from non-None fields
    updates = {}
    if payload.ai_agent_name is not None:
        updates["ai_agent_name"] = payload.ai_agent_name
    if payload.ai_tone is not None:
        updates["ai_tone"] = payload.ai_tone
    if payload.ai_services_description is not None:
        updates["ai_services_description"] = payload.ai_services_description
    if payload.ai_company_description is not None:
        updates["ai_company_description"] = payload.ai_company_description
    if payload.ai_qualification_questions is not None:
        updates["ai_qualification_questions"] = json.dumps(payload.ai_qualification_questions)
    if payload.ai_objection_responses is not None:
        updates["ai_objection_responses"] = json.dumps(payload.ai_objection_responses)
    if payload.ai_system_prompt is not None:
        updates["ai_system_prompt"] = payload.ai_system_prompt
    if payload.business_hours is not None:
        updates["business_hours"] = json.dumps(payload.business_hours)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Build parameterized query
    set_parts = []
    params = []
    for i, (col, val) in enumerate(updates.items(), 1):
        if col in ("ai_qualification_questions", "ai_objection_responses", "business_hours"):
            set_parts.append(f"{col} = ${i}::jsonb")
        else:
            set_parts.append(f"{col} = ${i}")
        params.append(val)

    params.append(tenant_id)
    query = f"UPDATE tenants SET {', '.join(set_parts)}, updated_at = NOW() WHERE id = ${len(params)}"

    await db.execute(query, *params)

    logger.info(f"DEV-36: AI agent config updated for tenant {tenant_id} by user {user_data.user_id} (fields: {list(updates.keys())})")

    return {
        "status": "ok",
        "updated_fields": list(updates.keys()),
        "message": f"AI agent config updated successfully ({len(updates)} fields)"
    }


# ─── POST /admin/setup/seed-ai-agent ─────────────────────────────────────────────

@setup_router.post("/admin/setup/seed-ai-agent", tags=["Setup"])
async def seed_ai_agent_config(x_admin_token: str = Header(None)):
    """
    Seeds the default Codexy-specific AI agent config for all existing tenants.
    Protected by X-Admin-Token only (no JWT needed -- used during initial setup).
    Idempotent: only updates tenants that don't have ai_agent_name set yet.
    """
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=500, detail="ADMIN_TOKEN not configured on server.")
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid X-Admin-Token.")

    tenants = await db.pool.fetch("SELECT id, clinic_name, ai_agent_name FROM tenants")
    if not tenants:
        raise HTTPException(status_code=404, detail="No tenants found. Run seed-team first.")

    results = []
    for tenant in tenants:
        tid = tenant["id"]
        tname = tenant["clinic_name"]

        # Only seed if ai_agent_name is not already configured
        if tenant.get("ai_agent_name") and tenant["ai_agent_name"] != "Asistente":
            results.append({"tenant_id": tid, "tenant_name": tname, "action": "skipped", "reason": "already configured"})
            continue

        cfg = DEFAULT_AI_AGENT_CONFIG
        await db.execute(
            """UPDATE tenants SET
                ai_agent_name = $2,
                ai_tone = $3,
                ai_services_description = $4,
                ai_company_description = $5,
                ai_qualification_questions = $6::jsonb,
                ai_objection_responses = $7::jsonb,
                business_hours = $8::jsonb,
                updated_at = NOW()
            WHERE id = $1""",
            tid,
            cfg["ai_agent_name"],
            cfg["ai_tone"],
            cfg["ai_services_description"],
            cfg["ai_company_description"],
            json.dumps(cfg["ai_qualification_questions"]),
            json.dumps(cfg["ai_objection_responses"]),
            json.dumps(cfg["business_hours"]),
        )
        results.append({"tenant_id": tid, "tenant_name": tname, "action": "seeded", "agent_name": cfg["ai_agent_name"]})

    seeded_count = sum(1 for r in results if r["action"] == "seeded")
    skipped_count = sum(1 for r in results if r["action"] == "skipped")

    logger.info(f"DEV-36: AI agent config seeded for {seeded_count} tenants, {skipped_count} skipped")

    return {
        "status": "ok",
        "message": f"AI agent config seeded: {seeded_count} updated, {skipped_count} skipped",
        "results": results,
    }
