"""
DEV-31: HSM WhatsApp Template Management Routes
Setup: crear y cargar plantillas HSM de WhatsApp aprobadas por Meta.

Endpoints:
  POST /admin/setup/seed-hsm-templates              — Seed 4 default CRM sales templates (admin token only)
  GET  /admin/core/crm/hsm-templates                 — List HSM templates for tenant
  POST /admin/core/crm/hsm-templates                 — Create a custom HSM template
  POST /admin/core/crm/hsm-templates/{id}/send       — Send a template message to a lead's phone
"""

import os
import uuid
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from db import db
from core.security import verify_admin_token, get_resolved_tenant_id, audit_access
from core.rate_limiter import limiter

logger = logging.getLogger("hsm_templates")
router = APIRouter()

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")


# ─── Pydantic Schemas ────────────────────────────────────────────────────────────

class CreateHSMTemplateRequest(BaseModel):
    name: str = Field(..., description="Template name (slug, e.g. 'saludo_inicial')")
    body_text: str = Field(..., description="Template body with {{1}}, {{2}} placeholders")
    category: str = Field("MARKETING", description="MARKETING | UTILITY | AUTHENTICATION")
    language: str = Field("es", description="Language code")
    variables_count: int = Field(0, description="Number of {{N}} variables in the body")


class SendHSMTemplateRequest(BaseModel):
    phone_number: str = Field(..., description="Recipient phone in E.164 format, e.g. +5491155551234")
    variables: List[str] = Field(default_factory=list, description="Ordered list of variable values for {{1}}, {{2}}, etc.")


# ─── Default CRM Sales Templates ─────────────────────────────────────────────────

DEFAULT_HSM_TEMPLATES = [
    {
        "name": "saludo_inicial",
        "category": "MARKETING",
        "language": "es",
        "body_text": (
            "Hola {{1}}, soy {{2}} de {{3}}. Vi que estás interesado en nuestros servicios. "
            "¿Te gustaría agendar una llamada para conocer cómo podemos ayudarte?"
        ),
        "variables_count": 3,
    },
    {
        "name": "recordatorio_llamada",
        "category": "MARKETING",
        "language": "es",
        "body_text": (
            "Hola {{1}}, te recuerdo que tenemos una llamada agendada para {{2}} a las {{3}}. "
            "¿Confirmamos?"
        ),
        "variables_count": 3,
    },
    {
        "name": "seguimiento_post_llamada",
        "category": "MARKETING",
        "language": "es",
        "body_text": (
            "Hola {{1}}, fue un gusto hablar contigo. Como acordamos, te envío información sobre {{2}}. "
            "¿Tenés alguna duda?"
        ),
        "variables_count": 2,
    },
    {
        "name": "reactivacion_frio",
        "category": "MARKETING",
        "language": "es",
        "body_text": (
            "Hola {{1}}, hace tiempo hablamos sobre {{2}}. Tenemos novedades que podrían interesarte. "
            "¿Te gustaría retomar la conversación?"
        ),
        "variables_count": 2,
    },
]


# ─── Full CRM Sales Templates (21 across 5 categories) ──────────────────────────

FULL_HSM_TEMPLATES = [
    # ── 1. Prospeccion (4) ──────────────────────────────────────────────────
    {
        "name": "prospeccion_primer_contacto",
        "category": "prospeccion",
        "language": "es",
        "body_text": (
            "Hola {{1}}, soy {{2}} de {{3}}. "
            "Noté tu interés en {{4}} y me encantaría mostrarte cómo podemos ayudarte. "
            "¿Tenés 5 minutos para una charla rápida?"
        ),
        "variables_count": 4,
    },
    {
        "name": "prospeccion_seguimiento_dia2",
        "category": "prospeccion",
        "language": "es",
        "body_text": (
            "Hola {{1}}, te escribí hace un par de días desde {{2}}. "
            "Quería saber si pudiste revisar la info sobre {{3}}. "
            "¿Te queda alguna duda que pueda resolverse?"
        ),
        "variables_count": 3,
    },
    {
        "name": "prospeccion_seguimiento_dia4",
        "category": "prospeccion",
        "language": "es",
        "body_text": (
            "Hola {{1}}, soy {{2}} de {{3}}. "
            "No quiero ser insistente, pero creo que {{4}} puede generarte resultados concretos. "
            "¿Hay algo que te frene para avanzar?"
        ),
        "variables_count": 4,
    },
    {
        "name": "prospeccion_ultimo_intento",
        "category": "prospeccion",
        "language": "es",
        "body_text": (
            "Hola {{1}}, entiendo que quizás no sea el momento ideal. "
            "Te dejo mi contacto por si más adelante necesitás ayuda con {{2}}. "
            "Soy {{3}} de {{4}}, siempre a disposición."
        ),
        "variables_count": 4,
    },
    # ── 2. Previo a llamada (4) ─────────────────────────────────────────────
    {
        "name": "previo_llamada_confirmacion",
        "category": "previo_llamada",
        "language": "es",
        "body_text": (
            "Hola {{1}}, te confirmo nuestra llamada para el {{2}} a las {{3}}. "
            "Si necesitás cambiar el horario, avisame sin problema. ¡Te espero!"
        ),
        "variables_count": 3,
    },
    {
        "name": "previo_llamada_recordatorio_1h",
        "category": "previo_llamada",
        "language": "es",
        "body_text": (
            "Hola {{1}}, te recuerdo que en 1 hora tenemos nuestra llamada agendada ({{2}} - {{3}}). "
            "Nos conectamos por este link: {{4}}"
        ),
        "variables_count": 4,
    },
    {
        "name": "previo_llamada_preparacion",
        "category": "previo_llamada",
        "language": "es",
        "body_text": (
            "Hola {{1}}, antes de nuestra llamada del {{2}}, te comparto un breve recurso "
            "para que aproveches al máximo la sesión: {{3}}. ¡Nos vemos!"
        ),
        "variables_count": 3,
    },
    {
        "name": "previo_llamada_reagendado",
        "category": "previo_llamada",
        "language": "es",
        "body_text": (
            "Hola {{1}}, como acordamos, reagendé nuestra llamada para el {{2}} a las {{3}}. "
            "Cualquier cambio, escribime. ¡Saludos!"
        ),
        "variables_count": 3,
    },
    # ── 3. Ventana 24hs (5) ─────────────────────────────────────────────────
    {
        "name": "ventana24_recurso",
        "category": "ventana_24hs",
        "language": "es",
        "body_text": (
            "Hola {{1}}, te comparto este recurso que creo que te va a interesar "
            "sobre {{2}}: {{3}}. Contame qué te parece."
        ),
        "variables_count": 3,
    },
    {
        "name": "ventana24_profundizacion",
        "category": "ventana_24hs",
        "language": "es",
        "body_text": (
            "Hola {{1}}, vi que te interesó {{2}}. Te cuento un poco más: "
            "{{3}} tiene resultados comprobados en empresas como la tuya. ¿Hablamos?"
        ),
        "variables_count": 3,
    },
    {
        "name": "ventana24_propuesta_valor",
        "category": "ventana_24hs",
        "language": "es",
        "body_text": (
            "Hola {{1}}, en {{2}} ayudamos a empresas a {{3}}. "
            "Nuestros clientes reportan mejoras de hasta un 40%%. ¿Te gustaría saber cómo?"
        ),
        "variables_count": 3,
    },
    {
        "name": "ventana24_invitacion_llamada",
        "category": "ventana_24hs",
        "language": "es",
        "body_text": (
            "Hola {{1}}, me encantaría contarte cómo {{2}} puede funcionar para tu caso. "
            "¿Te viene bien una llamada de 15 min el {{3}} a las {{4}}?"
        ),
        "variables_count": 4,
    },
    {
        "name": "ventana24_social_proof",
        "category": "ventana_24hs",
        "language": "es",
        "body_text": (
            "Hola {{1}}, quería contarte que {{2}} ya confía en {{3}} para {{4}}. "
            "Los resultados hablan por sí solos. ¿Te interesa ver un caso similar al tuyo?"
        ),
        "variables_count": 4,
    },
    # ── 4. Apertura de conversacion (4) ─────────────────────────────────────
    {
        "name": "apertura_reactivacion_frio",
        "category": "apertura_conversacion",
        "language": "es",
        "body_text": (
            "Hola {{1}}, soy {{2}} de {{3}}. Hace un tiempo hablamos y quería "
            "retomar el contacto. Tenemos novedades en {{4}} que podrían interesarte. ¿Hablamos?"
        ),
        "variables_count": 4,
    },
    {
        "name": "apertura_referido",
        "category": "apertura_conversacion",
        "language": "es",
        "body_text": (
            "Hola {{1}}, me recomendó contactarte {{2}}. Soy {{3}} de {{4}} y creo "
            "que podemos ayudarte con {{5}}. ¿Tenés un momento para charlar?"
        ),
        "variables_count": 5,
    },
    {
        "name": "apertura_problema_especifico",
        "category": "apertura_conversacion",
        "language": "es",
        "body_text": (
            "Hola {{1}}, sé que muchas empresas de tu rubro enfrentan el desafío de {{2}}. "
            "En {{3}} desarrollamos {{4}} justamente para resolver eso. ¿Te cuento más?"
        ),
        "variables_count": 4,
    },
    {
        "name": "apertura_post_evento",
        "category": "apertura_conversacion",
        "language": "es",
        "body_text": (
            "Hola {{1}}, fue un gusto coincidir en {{2}}. Soy {{3}} de {{4}}. "
            "Me encantaría continuar la conversación. ¿Te queda bien una llamada esta semana?"
        ),
        "variables_count": 4,
    },
    # ── 5. Marketing masivo (4) ─────────────────────────────────────────────
    {
        "name": "marketing_novedad",
        "category": "marketing_masivo",
        "language": "es",
        "body_text": (
            "Hola {{1}}, desde {{2}} queremos contarte que lanzamos {{3}}. "
            "Es ideal para {{4}}. Conocé más acá: {{5}}"
        ),
        "variables_count": 5,
    },
    {
        "name": "marketing_contenido_valor",
        "category": "marketing_masivo",
        "language": "es",
        "body_text": (
            "Hola {{1}}, preparamos una guía gratuita sobre {{2}} que creo que te va a servir. "
            "Descargala acá: {{3}}. ¡Esperamos que te sea útil!"
        ),
        "variables_count": 3,
    },
    {
        "name": "marketing_reactivacion_masiva",
        "category": "marketing_masivo",
        "language": "es",
        "body_text": (
            "Hola {{1}}, hace tiempo que no hablamos. En {{2}} seguimos trabajando "
            "para ayudarte con {{3}}. ¿Te interesa agendar una charla rápida? Respondé este mensaje."
        ),
        "variables_count": 3,
    },
    {
        "name": "marketing_campana_estacional",
        "category": "marketing_masivo",
        "language": "es",
        "body_text": (
            "Hola {{1}}, este {{2}} en {{3}} tenemos una promo especial en {{4}}. "
            "Válida hasta el {{5}}. ¡No te la pierdas! Info: {{6}}"
        ),
        "variables_count": 6,
    },
]


# ─── Helper: build components JSONB from body_text ───────────────────────────────

def _build_components(body_text: str, variables_count: int) -> list:
    """Build Meta-compatible components array from body text and variable count."""
    body_component = {"type": "BODY", "text": body_text}
    if variables_count > 0:
        body_component["example"] = {
            "body_text": [[f"{{{{var{i}}}}}" for i in range(1, variables_count + 1)]]
        }
    return [body_component]


# ─── 1. Seed HSM Templates (admin token only, no JWT) ────────────────────────────

@router.post("/admin/setup/seed-hsm-templates")
async def seed_hsm_templates(x_admin_token: str = Header(None)):
    """
    Seeds the 4 default CRM sales HSM templates for all existing tenants.
    Protected by X-Admin-Token only (no JWT needed — used during initial setup).
    Idempotent: skips templates that already exist (matched by tenant_id + name).
    """
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=500, detail="ADMIN_TOKEN not configured on server.")
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid X-Admin-Token.")

    # Get all tenants
    tenants = await db.pool.fetch("SELECT id, clinic_name FROM tenants")
    if not tenants:
        raise HTTPException(status_code=404, detail="No tenants found. Run seed-team first.")

    results = []
    for tenant in tenants:
        tenant_id = tenant["id"]
        tenant_name = tenant["clinic_name"]
        tenant_result = {"tenant_id": tenant_id, "tenant_name": tenant_name, "created": 0, "skipped": 0}

        for tmpl in DEFAULT_HSM_TEMPLATES:
            # Check if already exists (by name for this tenant)
            existing = await db.fetchrow(
                "SELECT id FROM meta_templates WHERE tenant_id = $1 AND name = $2",
                tenant_id, tmpl["name"],
            )
            if existing:
                tenant_result["skipped"] += 1
                continue

            # Generate a placeholder meta_template_id (will be replaced once submitted to Meta)
            meta_template_id = f"local_{tmpl['name']}_{uuid.uuid4().hex[:8]}"
            components = _build_components(tmpl["body_text"], tmpl["variables_count"])

            await db.execute(
                """
                INSERT INTO meta_templates (
                    id, tenant_id, meta_template_id, waba_id, name, category,
                    language, status, components, example, sync_status, created_at, updated_at
                ) VALUES (
                    gen_random_uuid(), $1, $2, 'pending', $3, $4,
                    $5, 'PENDING_APPROVAL', $6::jsonb, $7::jsonb, 'pending', NOW(), NOW()
                )
                """,
                tenant_id,
                meta_template_id,
                tmpl["name"],
                tmpl["category"],
                tmpl["language"],
                json.dumps(components),
                json.dumps({
                    "body_text": tmpl["body_text"],
                    "variables_count": tmpl["variables_count"],
                }),
            )
            tenant_result["created"] += 1

        results.append(tenant_result)

    total_created = sum(r["created"] for r in results)
    total_skipped = sum(r["skipped"] for r in results)

    return {
        "success": True,
        "summary": {
            "tenants_processed": len(results),
            "templates_created": total_created,
            "templates_skipped": total_skipped,
        },
        "details": results,
    }


# ─── 2. List HSM Templates ──────────────────────────────────────────────────────

@router.get("/admin/core/crm/hsm-templates")
@audit_access("list_hsm_templates")
@limiter.limit("30/minute")
async def list_hsm_templates(
    request: Request,
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """List all HSM templates for the tenant."""
    rows = await db.pool.fetch(
        """
        SELECT id, tenant_id, meta_template_id, waba_id, name, category,
               language, status, components, example,
               sent_count, delivered_count, read_count, replied_count,
               last_synced_at, sync_status, created_at, updated_at
        FROM meta_templates
        WHERE tenant_id = $1
        ORDER BY created_at DESC
        """,
        tenant_id,
    )
    templates = []
    for row in rows:
        t = dict(row)
        t["id"] = str(t["id"])
        # Extract body_text from components or example for convenience
        body_text = ""
        variables_count = 0
        if t.get("example") and isinstance(t["example"], dict):
            body_text = t["example"].get("body_text", "")
            variables_count = t["example"].get("variables_count", 0)
        elif t.get("components") and isinstance(t["components"], list):
            for comp in t["components"]:
                if comp.get("type") == "BODY":
                    body_text = comp.get("text", "")
        t["body_text"] = body_text
        t["variables_count"] = variables_count
        templates.append(t)

    return {
        "success": True,
        "data": templates,
        "total": len(templates),
        "timestamp": datetime.utcnow().isoformat(),
    }


# ─── 3. Create Custom HSM Template ──────────────────────────────────────────────

@router.post("/admin/core/crm/hsm-templates")
@audit_access("create_hsm_template")
@limiter.limit("10/minute")
async def create_hsm_template(
    payload: CreateHSMTemplateRequest,
    request: Request,
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """Create a custom HSM template (status = PENDING_APPROVAL until Meta approves)."""
    # Check for duplicate name
    existing = await db.fetchrow(
        "SELECT id FROM meta_templates WHERE tenant_id = $1 AND name = $2",
        tenant_id, payload.name,
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"Template with name '{payload.name}' already exists for this tenant.")

    meta_template_id = f"local_{payload.name}_{uuid.uuid4().hex[:8]}"
    components = _build_components(payload.body_text, payload.variables_count)

    new_id = await db.fetchval(
        """
        INSERT INTO meta_templates (
            id, tenant_id, meta_template_id, waba_id, name, category,
            language, status, components, example, sync_status, created_at, updated_at
        ) VALUES (
            gen_random_uuid(), $1, $2, 'pending', $3, $4,
            $5, 'PENDING_APPROVAL', $6::jsonb, $7::jsonb, 'pending', NOW(), NOW()
        )
        RETURNING id
        """,
        tenant_id,
        meta_template_id,
        payload.name,
        payload.category,
        payload.language,
        json.dumps(components),
        json.dumps({
            "body_text": payload.body_text,
            "variables_count": payload.variables_count,
        }),
    )

    return {
        "success": True,
        "data": {
            "id": str(new_id),
            "name": payload.name,
            "category": payload.category,
            "language": payload.language,
            "status": "PENDING_APPROVAL",
            "body_text": payload.body_text,
            "variables_count": payload.variables_count,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


# ─── 4. Send HSM Template to a Lead ─────────────────────────────────────────────

@router.post("/admin/core/crm/hsm-templates/{template_id}/send")
@audit_access("send_hsm_template")
@limiter.limit("20/minute")
async def send_hsm_template(
    template_id: str,
    payload: SendHSMTemplateRequest,
    request: Request,
    user_data: Dict = Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """
    Send a specific HSM template to a lead's phone number via YCloud.
    Validates variable count matches, then fires the message.
    """
    # Fetch template
    tmpl = await db.fetchrow(
        "SELECT * FROM meta_templates WHERE tenant_id = $1 AND id = $2::uuid",
        tenant_id, template_id,
    )
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found.")

    # Only allow sending APPROVED or PENDING_APPROVAL templates
    # (In production, only APPROVED would work on Meta side, but we allow PENDING for testing)
    if tmpl["status"] in ("REJECTED",):
        raise HTTPException(status_code=400, detail=f"Cannot send template with status '{tmpl['status']}'.")

    # Extract expected variables count from example
    expected_vars = 0
    if tmpl["example"] and isinstance(tmpl["example"], dict):
        expected_vars = tmpl["example"].get("variables_count", 0)

    if len(payload.variables) != expected_vars:
        raise HTTPException(
            status_code=400,
            detail=f"Template expects {expected_vars} variables but {len(payload.variables)} were provided.",
        )

    # Build components for YCloud send_template
    body_params = [{"type": "text", "text": v} for v in payload.variables]
    components = []
    if body_params:
        components.append({"type": "body", "parameters": body_params})

    # Get YCloud credentials
    from core.credentials import get_tenant_credential, YCLOUD_API_KEY

    api_key = await get_tenant_credential(tenant_id, YCLOUD_API_KEY)
    from_number = await get_tenant_credential(tenant_id, "YCLOUD_WHATSAPP_NUMBER")

    if not api_key:
        raise HTTPException(status_code=503, detail="YCloud API key not configured for this tenant.")

    # Send via YCloud
    from ycloud_client import YCloudClient

    client = YCloudClient(api_key)
    if from_number:
        client.business_number = from_number

    correlation_id = f"hsm_manual_{template_id}_{uuid.uuid4().hex[:8]}"

    try:
        response = await client.send_template(
            to=payload.phone_number,
            template_name=tmpl["name"],
            language_code=tmpl["language"],
            components=components,
            correlation_id=correlation_id,
        )
    except Exception as e:
        logger.error(f"YCloud send_template failed: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"Failed to send template via YCloud: {str(e)}")

    # Increment sent_count
    await db.execute(
        "UPDATE meta_templates SET sent_count = sent_count + 1, updated_at = NOW() WHERE id = $1::uuid",
        template_id,
    )

    # Log in automation_logs for traceability
    # Find lead by phone if possible
    lead_row = await db.fetchrow(
        "SELECT id FROM leads WHERE tenant_id = $1 AND phone_number = $2 LIMIT 1",
        tenant_id, payload.phone_number,
    )
    lead_id = lead_row["id"] if lead_row else None

    await db.execute(
        """
        INSERT INTO automation_logs (tenant_id, patient_id, trigger_type, target_id, status, meta)
        VALUES ($1, $2, 'hsm_manual_send', $3, 'sent', $4)
        """,
        tenant_id,
        lead_id,
        template_id,
        json.dumps({"phone": payload.phone_number, "template": tmpl["name"], "ycloud_response": response}),
    )

    # Also record in chat_messages so it appears in the CRM conversation
    body_text = ""
    if tmpl["example"] and isinstance(tmpl["example"], dict):
        body_text = tmpl["example"].get("body_text", "")
    # Replace placeholders with actual values
    rendered_text = body_text
    for i, val in enumerate(payload.variables, start=1):
        rendered_text = rendered_text.replace(f"{{{{{i}}}}}", val)

    if rendered_text:
        await db.append_chat_message(
            from_number=payload.phone_number,
            role="assistant",
            content=f"[HSM: {tmpl['name']}] {rendered_text}",
            correlation_id=correlation_id,
            tenant_id=tenant_id,
        )

    return {
        "success": True,
        "data": {
            "template_id": template_id,
            "template_name": tmpl["name"],
            "phone_number": payload.phone_number,
            "status": "sent",
            "correlation_id": correlation_id,
            "ycloud_response": response,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


# ─── 5. Seed Full HSM Templates (21 templates, 5 categories) ──────────────────

@router.post("/admin/setup/seed-hsm-templates-full")
async def seed_hsm_templates_full(x_admin_token: str = Header(None)):
    """
    Seeds all 21 CRM sales HSM templates across 5 categories for every tenant.
    Protected by X-Admin-Token only (no JWT — used during initial setup).
    Idempotent: skips templates that already exist (matched by tenant_id + name).
    Status is set to APPROVED so they appear ready-to-use in the setter panel.
    """
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=500, detail="ADMIN_TOKEN not configured on server.")
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid X-Admin-Token.")

    tenants = await db.pool.fetch("SELECT id, clinic_name FROM tenants")
    if not tenants:
        raise HTTPException(status_code=404, detail="No tenants found. Run seed-team first.")

    results = []
    for tenant in tenants:
        tenant_id = tenant["id"]
        tenant_name = tenant["clinic_name"]
        tenant_result = {"tenant_id": tenant_id, "tenant_name": tenant_name, "created": 0, "skipped": 0}

        for tmpl in FULL_HSM_TEMPLATES:
            existing = await db.fetchrow(
                "SELECT id FROM meta_templates WHERE tenant_id = $1 AND name = $2",
                tenant_id, tmpl["name"],
            )
            if existing:
                tenant_result["skipped"] += 1
                continue

            meta_template_id = f"local_{tmpl['name']}_{uuid.uuid4().hex[:8]}"
            components = _build_components(tmpl["body_text"], tmpl["variables_count"])

            await db.execute(
                """
                INSERT INTO meta_templates (
                    id, tenant_id, meta_template_id, waba_id, name, category,
                    language, status, components, example, sync_status, created_at, updated_at
                ) VALUES (
                    gen_random_uuid(), $1, $2, 'pending', $3, $4,
                    $5, 'APPROVED', $6::jsonb, $7::jsonb, 'synced', NOW(), NOW()
                )
                """,
                tenant_id,
                meta_template_id,
                tmpl["name"],
                tmpl["category"],
                tmpl["language"],
                json.dumps(components),
                json.dumps({
                    "body_text": tmpl["body_text"],
                    "variables_count": tmpl["variables_count"],
                }),
            )
            tenant_result["created"] += 1

        results.append(tenant_result)

    total_created = sum(r["created"] for r in results)
    total_skipped = sum(r["skipped"] for r in results)

    return {
        "success": True,
        "summary": {
            "tenants_processed": len(results),
            "templates_created": total_created,
            "templates_skipped": total_skipped,
            "categories": ["prospeccion", "previo_llamada", "ventana_24hs", "apertura_conversacion", "marketing_masivo"],
            "templates_per_category": {
                "prospeccion": 4,
                "previo_llamada": 4,
                "ventana_24hs": 5,
                "apertura_conversacion": 4,
                "marketing_masivo": 4,
            },
        },
        "details": results,
    }
