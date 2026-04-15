import os
import json
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging
import asyncio
import socketio
from datetime import datetime, timezone
from typing import Optional, List, Any

from fastapi import FastAPI, Request, Header, HTTPException, Depends, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor
from langchain_community.agent_toolkits.load_tools import load_tools
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from services.calcom_service import calcom_service

# --- APP SETUP ---
from core.rate_limiter import limiter

from db import db
from admin_routes import router as admin_router
from auth_routes import router as auth_router
from modules.crm_sales.tools_provider import tool_registry  # Registered via import
from core.socket_manager import sio
from core.socket_notifications import register_notification_socket_handlers
from core.context import current_customer_phone, current_patient_id, current_tenant_id
from core.tools import tool_registry
from core.niche_manager import NicheManager
from core.agent.prompt_loader import prompt_loader

# --- CONFIGURACIÓN ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger("orchestrator")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
POSTGRES_DSN = os.getenv("POSTGRES_DSN", "")

# --- DATABASE SETUP ---
engine = create_async_engine(POSTGRES_DSN, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# --- APP CONFIG ---
app = FastAPI(title="Nexus Orchestrator", version="7.7.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS: merge defaults with CORS_ALLOWED_ORIGINS (comma-separated) for EasyPanel/custom deployments
_default_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://crmventas-frontend.ugwrjq.easypanel.host",  # EasyPanel CRM Ventas frontend
    "https://crmfusa-frontend.a6pys6.easypanel.host",  # Current Fusa Labs deployment
]
_env_origins = os.getenv("CORS_ALLOWED_ORIGINS", "")
if _env_origins:
    _default_origins.extend(o.strip() for o in _env_origins.split(",") if o.strip())
origins = list(dict.fromkeys(_default_origins))  # dedupe, keep order
logger.info(f"CORS allow_origins: {origins}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Nexus Security Middleware: CSP, HSTS, X-Frame-Options (se aplica DESPUÉS de CORS)
from core.security_middleware import SecurityHeadersMiddleware

app.add_middleware(SecurityHeadersMiddleware)


# --- SOCKET.IO ---
sio_app = socketio.ASGIApp(sio, app)

# --- ROUTERS ---
app.include_router(auth_router)
app.include_router(admin_router)

# Seller Assignment Routes
try:
    from routes.seller_routes import router as seller_router

    app.include_router(seller_router, tags=["Seller Management"])
    logger.info("✅ Seller Management API mounted at /admin/core/sellers")
except Exception as e:
    logger.error(f"❌ Could not mount Seller Management routes: {e}")
    import traceback

    traceback.print_exc()

# Notification Routes
try:
    from routes.notification_routes import router as notification_router

    app.include_router(notification_router, tags=["Notifications"])
    logger.info("✅ Notification API mounted")
except Exception as e:
    logger.error(f"❌ Could not mount Notification routes: {e}", exc_info=True)

    # Fallback: minimal notifications/count endpoint so frontend doesn't break
    @app.get("/admin/core/notifications/count")
    async def _fallback_notifications_count(x_admin_token: str = Header(None)):
        try:
            count = await db.fetchval(
                "SELECT COUNT(*) FROM notifications WHERE is_read = false"
            )
            return {"count": count or 0}
        except Exception:
            return {"count": 0}

    logger.info("✅ Fallback /admin/core/notifications/count endpoint registered")

# Scheduled Tasks Routes
try:
    from routes.scheduled_tasks_routes import router as scheduled_tasks_router

    app.include_router(scheduled_tasks_router, tags=["Scheduled Tasks"])
    logger.info("✅ Scheduled Tasks API mounted")
except Exception as e:
    logger.error(f"❌ Could not mount Scheduled Tasks routes: {e}", exc_info=True)

# Health Check Routes
try:
    from routes.health_routes import router as health_router

    app.include_router(health_router, tags=["Health"])
    logger.info("✅ Health Check API mounted")
except Exception as e:
    logger.error(f"❌ Could not mount Health Check routes: {e}", exc_info=True)

# Single-niche: CRM Sales only (no sales)
SUPPORTED_NICHES = ["crm_sales"]
for niche in SUPPORTED_NICHES:
    NicheManager.load_niche_router(app, niche)

# CRM Sales under /admin/core/crm so proxy/CORS work (same path as other admin routes)
try:
    from modules.crm_sales import routes as crm_routes

    app.include_router(
        crm_routes.router, prefix="/admin/core/crm", tags=["CRM Sales (Admin)"]
    )
    logger.info("✅ CRM API also mounted at /admin/core/crm")
except Exception as e:
    logger.warning(f"Could not mount CRM under /admin/core/crm: {e}")

# Lead Status Routes (DEV-27: pipeline de estados)
try:
    from routes.lead_status_routes import router as lead_status_router

    app.include_router(lead_status_router, tags=["Lead Status"])
    logger.info("✅ Lead Status API mounted at /admin/core/crm/lead-statuses")
except Exception as e:
    logger.error(f"❌ Could not mount Lead Status routes: {e}", exc_info=True)

# Lead Tags Routes
try:
    from routes.lead_tags_routes import router as lead_tags_router

    app.include_router(lead_tags_router, tags=["Lead Tags"])
    logger.info("✅ Lead Tags API mounted")
except Exception as e:
    logger.error(f"❌ Could not mount Lead Tags routes: {e}", exc_info=True)

# Lead Notes & Derivation Routes (DEV-21)
try:
    from routes.lead_notes_routes import router as lead_notes_router

    app.include_router(lead_notes_router, tags=["Lead Notes & Derivation"])
    logger.info("✅ Lead Notes & Derivation API mounted")
except Exception as e:
    logger.error(f"❌ Could not mount Lead Notes routes: {e}", exc_info=True)

# User Management Routes (DEV-29)
try:
    from routes.user_management_routes import router as user_mgmt_router

    app.include_router(user_mgmt_router, tags=["User Management"])
    logger.info("✅ User Management API mounted (seed-team, users CRUD)")
except Exception as e:
    logger.error(f"❌ Could not mount User Management routes: {e}", exc_info=True)

# HSM Templates Routes (DEV-31)
try:
    from routes.hsm_templates_routes import router as hsm_templates_router

    app.include_router(hsm_templates_router, tags=["HSM Templates"])
    logger.info("✅ HSM Templates API mounted (seed + CRUD + send)")
except Exception as e:
    logger.error(f"❌ Could not mount HSM Templates routes: {e}", exc_info=True)

# Free-text Chat Send Routes
try:
    from routes.chat_routes import router as chat_routes_router

    app.include_router(chat_routes_router, tags=["Chat Send"])
    logger.info("✅ Chat Send API mounted (POST /admin/core/chat/send)")
except Exception as e:
    logger.error(f"❌ Could not mount Chat Send routes: {e}", exc_info=True)

# Meta Ads Marketing Routes
try:
    from routes.marketing import router as marketing_router
    from routes.meta_auth import router as meta_auth_router
    from routes.meta_webhooks import router as meta_webhooks_router

    app.include_router(marketing_router, prefix="/crm/marketing", tags=["Marketing"])
    app.include_router(meta_auth_router, prefix="/crm/auth/meta", tags=["Meta OAuth"])
    app.include_router(meta_webhooks_router, prefix="/webhooks", tags=["Webhooks"])
    logger.info("✅ Meta Ads Marketing API and Webhooks mounted")
except Exception as e:
    logger.error(f"❌ Could not mount Meta Ads Marketing routes: {e}", exc_info=True)

# Meta Embedded Signup — WhatsApp, Instagram, Facebook Pages connection
try:
    from routes.meta_connect import router as meta_connect_router

    app.include_router(
        meta_connect_router, prefix="/admin/meta", tags=["Meta Embedded Signup"]
    )
    logger.info("✅ Meta Embedded Signup routes mounted at /admin/meta")
except Exception as e:
    logger.error(f"❌ Could not mount Meta Embedded Signup routes: {e}", exc_info=True)

# Google Ads Marketing Routes
try:
    from routes.google_auth import router as google_auth_router
    from routes.google_ads_routes import router as google_ads_routes_router

    app.include_router(
        google_auth_router, prefix="/crm/auth/google", tags=["Google OAuth"]
    )
    app.include_router(
        google_ads_routes_router, prefix="/crm/marketing", tags=["Google Ads"]
    )
    logger.info("✅ Google Ads Marketing API mounted")
except Exception as e:
    logger.error(f"❌ Could not mount Google Ads Marketing routes: {e}", exc_info=True)

# Email Lead Monitor Routes (DEV-34 Part 2)
try:
    from routes.email_monitor_routes import router as email_monitor_router

    app.include_router(email_monitor_router, tags=["Email Lead Monitor"])
    logger.info("✅ Email Lead Monitor API mounted at /admin/core/email-monitor")
except Exception as e:
    logger.error(f"❌ Could not mount Email Lead Monitor routes: {e}", exc_info=True)

# Company Settings Routes (DEV-35)
try:
    from routes.company_settings_routes import router as company_settings_router
    from routes.company_settings_routes import setup_router as setup_router

    app.include_router(company_settings_router, tags=["Company Settings"])
    app.include_router(setup_router, tags=["Setup"])
    logger.info(
        "✅ Company Settings API mounted (GET/PUT /admin/core/settings/company + POST /admin/setup/configure-tenant)"
    )
except Exception as e:
    logger.error(f"❌ Could not mount Company Settings routes: {e}", exc_info=True)

# AI Agent Config Routes (DEV-36)
try:
    from routes.ai_agent_routes import router as ai_agent_router
    from routes.ai_agent_routes import setup_router as ai_agent_setup_router

    app.include_router(ai_agent_router, tags=["AI Agent Config"])
    app.include_router(ai_agent_setup_router, tags=["Setup"])
    logger.info(
        "✅ AI Agent Config API mounted (GET/PUT /admin/core/settings/ai-agent + POST /admin/setup/seed-ai-agent)"
    )
except Exception as e:
    logger.error(f"❌ Could not mount AI Agent Config routes: {e}", exc_info=True)

# Channel Bindings & Multi-Channel Routing (Patch 27)
try:
    from routes.channel_routes import internal_router as channel_internal_router
    from routes.channel_routes import admin_router as channel_admin_router

    app.include_router(channel_internal_router, tags=["Internal Routing"])
    app.include_router(channel_admin_router, tags=["Channel Management"])
    logger.info(
        "✅ Channel Routing API mounted (GET /internal/routing/resolve + /admin/core/channels CRUD)"
    )
except Exception as e:
    logger.error(f"❌ Could not mount Channel Routing routes: {e}", exc_info=True)

# Team Activity Routes (DEV-39 + DEV-40 + DEV-41)
try:
    from routes.team_activity_routes import router as team_activity_router

    app.include_router(team_activity_router, tags=["Team Activity"])
    logger.info("✅ Team Activity API mounted at /admin/core/team-activity")
except Exception as e:
    logger.error(f"❌ Could not mount Team Activity routes: {e}", exc_info=True)

# SLA Rules Routes (DEV-42)
try:
    from routes.sla_routes import router as sla_router

    app.include_router(sla_router, tags=["SLA Rules"])
    logger.info("✅ SLA Rules API mounted at /admin/core/sla-rules")
except Exception as e:
    logger.error(f"❌ Could not mount SLA Rules routes: {e}", exc_info=True)

# Reactivation Routes (DEV-47)
try:
    from routes.reactivation_routes import router as reactivation_router

    app.include_router(reactivation_router, tags=["Reactivation DEV-47"])
    logger.info("✅ Reactivation API mounted at /admin/core/crm/reactivation")
except Exception as e:
    logger.error(f"❌ Could not mount Reactivation routes: {e}", exc_info=True)

# Deduplication Routes (DEV-50)
try:
    from routes.deduplication_routes import router as deduplication_router

    app.include_router(deduplication_router, tags=["Deduplication DEV-50"])
    logger.info("✅ Deduplication API mounted at /admin/core/crm/duplicates")
except Exception as e:
    logger.error(f"❌ Could not mount Deduplication routes: {e}", exc_info=True)

# Analytics Dashboard Routes (Integrated from Dashboard_Analytics_Sovereign)
try:
    from routes.analytics_routes import router as analytics_router

    app.include_router(analytics_router)
    logger.info(
        "✅ Analytics Dashboard API mounted at /admin/analytics/ceo, /admin/analytics/secretary"
    )
except Exception as e:
    logger.warning(f"⚠️ Could not mount Analytics routes: {e}")

# Drive Storage Routes (SPEC-01)
try:
    from routes.drive_routes import router as drive_router

    app.include_router(drive_router, tags=["Drive Storage"])
    logger.info("✅ Drive Storage API mounted at /api/v1/drive")
except Exception as e:
    logger.warning(f"⚠️ Could not mount Drive routes: {e}")

# Lead Forms Routes (F-02)
try:
    from routes.lead_forms_routes import router as lead_forms_router, public_router as lead_forms_public_router
    app.include_router(lead_forms_router, tags=["Lead Forms"])
    app.include_router(lead_forms_public_router, tags=["Lead Forms Public"])
    logger.info("✅ Lead Forms API mounted at /admin/core/crm/forms + /f/{slug}")
except Exception as e:
    logger.warning(f"⚠️ Could not mount Lead Forms routes: {e}")

# Daily Check-in Routes (SPEC-05)
try:
    from routes.checkin_routes import router as checkin_router
    app.include_router(checkin_router, tags=["Daily Check-in"])
    logger.info("✅ Daily Check-in API mounted at /admin/core/checkin")
except Exception as e:
    logger.warning(f"⚠️ Could not mount Check-in routes: {e}")

# Vendor Tasks Routes (SPEC-06)
try:
    from routes.vendor_tasks_routes import router as vendor_tasks_router
    app.include_router(vendor_tasks_router, tags=["Vendor Tasks"])
    logger.info("✅ Vendor Tasks API mounted at /admin/core/crm/vendor-tasks")
except Exception as e:
    logger.warning(f"⚠️ Could not mount Vendor Tasks routes: {e}")

# Knowledge Base Routes (SPEC-03)
try:
    from routes.manuales_routes import router as manuales_router
    app.include_router(manuales_router, tags=["Knowledge Base"])
    logger.info("✅ Knowledge Base API mounted at /admin/core/manuales")
except Exception as e:
    logger.warning(f"⚠️ Could not mount Manuales routes: {e}")

# Internal Chat Routes (SPEC-04)
try:
    from routes.internal_chat_routes import router as internal_chat_router

    app.include_router(internal_chat_router, tags=["Internal Chat"])
    logger.info("✅ Internal Chat API mounted at /admin/core/internal-chat")
except Exception as e:
    logger.warning(f"⚠️ Could not mount Internal Chat routes: {e}")

# Plantillas Routes (SPEC-02)
try:
    from routes.plantillas_routes import router as plantillas_router

    app.include_router(plantillas_router, tags=["Plantillas"])
    logger.info("✅ Plantillas API mounted at /api/v1/plantillas")
except Exception as e:
    logger.warning(f"⚠️ Could not mount Plantillas routes: {e}")

# Telegram Notification Routes (SPEC-07)
try:
    from routes.telegram_routes import router as telegram_router

    app.include_router(telegram_router, tags=["Telegram Notifications"])
    logger.info("✅ Telegram Notification API mounted at /internal/telegram/notify")
except Exception as e:
    logger.warning(f"⚠️ Could not mount Telegram routes: {e}")

# --- LANGCHAIN AGENT FACTORY ---
llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=OPENAI_API_KEY)


async def get_agent_executor(tenant_id: int):
    """
    Creates an AgentExecutor with CRM Sales tools and prompt.
    DEV-36: Fetches tenant AI config to build dynamic or custom system prompt.
    """
    row = await db.fetchrow(
        """SELECT COALESCE(niche_type, 'crm_sales') AS niche_type, clinic_name,
                  ai_system_prompt, ai_agent_name, ai_tone, ai_services_description,
                  ai_qualification_questions, ai_objection_responses,
                  ai_company_description, business_hours,
                  business_hours_start, business_hours_end
           FROM tenants WHERE id = $1""",
        tenant_id,
    )
    niche_type = (row["niche_type"] if row else "crm_sales") or "crm_sales"
    tenant_name = (
        row["clinic_name"] if row else "nuestra empresa"
    ) or "nuestra empresa"
    tools = tool_registry.get_tools(niche_type, tenant_id)

    # --- DEV-36: Build system prompt from tenant AI config ---
    system_prompt = _build_system_prompt(row, tenant_name)

    # Create dynamic prompt template
    prompt_template = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    # Create agent with niche-specific tools and prompt
    from langchain.agents import create_openai_tools_agent

    agent = create_openai_tools_agent(llm, tools, prompt_template)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)


def _build_system_prompt(tenant_row, tenant_name: str) -> str:
    """
    DEV-36: Builds the AI agent system prompt from tenant config.
    If ai_system_prompt is set, uses it as full override.
    Otherwise builds dynamically from ai_agent_name, ai_tone, etc.
    """
    if not tenant_row:
        return _default_system_prompt(tenant_name, "Asistente")

    # Full override: if tenant has a custom system prompt, use it directly
    custom_prompt = tenant_row.get("ai_system_prompt")
    if custom_prompt and custom_prompt.strip():
        return custom_prompt

    # Dynamic build from config fields
    agent_name = tenant_row.get("ai_agent_name") or "Asistente"
    ai_tone = tenant_row.get("ai_tone") or "profesional_argentino"
    services_desc = tenant_row.get("ai_services_description") or ""
    company_desc = tenant_row.get("ai_company_description") or ""
    qualification_qs = tenant_row.get("ai_qualification_questions") or []
    objection_resps = tenant_row.get("ai_objection_responses") or []
    business_hours = tenant_row.get("business_hours") or {}
    bh_start = tenant_row.get("business_hours_start") or "09:00"
    bh_end = tenant_row.get("business_hours_end") or "18:00"

    # Parse tone into prompt instructions
    tone_instructions = _get_tone_instructions(ai_tone, agent_name)

    # Build qualification section
    qualification_section = _build_qualification_section(qualification_qs)

    # Build objection handling section
    objection_section = _build_objection_section(objection_resps)

    # Build services section
    services_section = ""
    if services_desc:
        services_section = f"""
SERVICIOS QUE OFRECEMOS
{services_desc}
"""

    # Build company description section
    company_section = ""
    if company_desc:
        company_section = f"""
PROPUESTA DE VALOR DE {tenant_name.upper()}
{company_desc}
"""

    # Build business hours section
    hours_section = _build_hours_section(business_hours, bh_start, bh_end)

    return f"""Sos {agent_name} de {tenant_name}. Tu mision es atender a cada prospecto que escriba por WhatsApp o formulario web de forma profesional, calida y consultiva, operando 24/7 sin intervencion humana hasta que un vendedor tome el control.

{tone_instructions}

IDENTIDAD
- Nunca reveles que sos una inteligencia artificial a menos que te lo pregunten directamente.
- Si te preguntan, responde con honestidad: "Soy {agent_name}, asistente virtual de {tenant_name}".
- Presentate brevemente al inicio de cada nueva conversacion: "Hola! Soy {agent_name} de {tenant_name}. En que puedo ayudarte hoy?"
{company_section}{services_section}
{qualification_section}

PREGUNTAS FRECUENTES (FAQ)
- **Precios**: "Los planes dependen del alcance del proyecto. Contame que necesitas y te paso un estimado, o puedo agendarte una llamada con el equipo."
- **Servicios**: Describi brevemente lo que ofrece {tenant_name} basandote en la seccion de SERVICIOS. Si no tenes el detalle exacto, ofrece agendar una demo.
- **Proceso**: "El proceso es simple: primero entendemos tu necesidad, armamos una propuesta y arrancamos."
- **Disponibilidad**: "Estamos disponibles para charlar cuando quieras. Te agendo una reunion?"
- Si el prospecto hace una pregunta que no podes responder con certeza, no inventes. Deci: "Esa consulta la maneja mejor nuestro equipo. Te conecto con un especialista?"
{objection_section}
HERRAMIENTAS
- Cuando el prospecto quiera agendar una reunion, demo o llamada, usa **book_sales_meeting** con fecha/hora, motivo y nombre.
- Cuando tengas datos de calificacion, usa **qualify_lead** para registrar interes, presupuesto, timeline y resumen.
- Cuando necesites escalar a un humano, usa **request_human_handoff** indicando el motivo y la urgencia.
- Usa **assign_lead_tags** proactivamente para etiquetar al lead segun el contexto de la conversacion.
- Usa **get_lead_tags** para consultar las etiquetas actuales antes de agregar nuevas.
- Usa **derive_to_setter** cuando termines la interaccion con un lead y debas pasarlo a un setter humano: si agendaste una llamada, si detectas potencial de cierre, o si el lead perdio interes. Inclui un resumen completo de los puntos clave del prospecto (necesidades, presupuesto, timeline, objeciones).

DERIVACION A SETTER (derive_to_setter)
Despues de completar la calificacion o agendar una reunion, deriva al lead al setter con un resumen detallado.
Escenarios de derivacion:
- **Llamada agendada**: Usaste book_sales_meeting -> deriva con resumen para que el setter se prepare.
- **Potencial de cierre**: El lead muestra senales claras de compra (pregunta "como arrancamos?", pide propuesta formal).
- **Lead perdio interes**: Despues de varios intercambios el prospecto se enfria -> deriva para seguimiento humano.
- **Consulta compleja**: El prospecto tiene necesidades que requieren atencion personalizada.
Siempre inclui en el summary: necesidad principal, presupuesto si lo menciono, timeline, objeciones, y cualquier dato relevante.

ETIQUETADO AUTOMATICO DE LEADS (assign_lead_tags)
Despues de CADA intercambio, evalua si corresponde asignar una o mas etiquetas al lead. Usa assign_lead_tags con la lista de tags y un motivo breve. Las etiquetas se mergean (no reemplazan).

Mapa de etiquetas:
- **caliente**: El prospecto muestra interes concreto en implementacion, compra o contratacion. Pide detalles operativos, pregunta "como arrancamos?" o similar.
- **tibio**: Pregunta por precio o servicios pero no agenda ni se compromete. Interes exploratorio.
- **precio_sensible**: Menciona presupuesto limitado, pide descuentos o compara precios explicitamente.
- **llamada_pactada**: Se agendo una reunion o llamada (asigna este tag siempre que uses book_sales_meeting).
- **handoff_solicitado**: El prospecto pide hablar con un humano o vendedor directamente.
- **comparando_opciones**: Menciona competidores, alternativas o dice que esta evaluando otras opciones.
- **urgente**: El prospecto expresa urgencia explicita ("lo necesito ya", "es para esta semana", etc.).

Reglas:
- Siempre inclui un "reason" claro y breve explicando por que asignas cada tag.
- No repitas tags que el lead ya tiene (consulta con get_lead_tags si no estas seguro).
- Podes asignar multiples tags en una sola llamada si aplican varios.
- Prioriza la calidad: solo asigna tags cuando haya evidencia clara en la conversacion.

REGLAS DE ESCALADO (request_human_handoff)
- **Urgencia high**: El prospecto pide explicitamente hablar con una persona, muestra intencion de compra inminente (lead caliente), o hay un reclamo.
- **Urgencia medium**: Pregunta tecnica compleja que no podes responder, o la conversacion se estanca despues de 3+ intercambios sin avance.
- **Urgencia low**: El prospecto menciona que volvera despues, o la consulta es informativa sin intencion clara.
{hours_section}
OBJETIVO FINAL
- Siempre intenta obtener datos de contacto (nombre, email) o agendar una reunion antes de cerrar la conversacion.
- Si el prospecto se despide sin agendar, ofrece: "Te puedo mandar mas info por este medio? O preferis que te contacte un asesor?"
- Se conciso: mensajes de 1-3 oraciones. Evita parrafos largos por WhatsApp.
- Nunca presiones. Se servicial, no insistente."""


def _get_tone_instructions(ai_tone: str, agent_name: str) -> str:
    """Returns tone/language instructions based on the ai_tone config."""
    tone_map = {
        "profesional_argentino": """IDIOMA Y TONO
- Responde en espanol por defecto. Si el prospecto escribe en ingles, cambia a ingles automaticamente.
- Usa "vos" (espanol rioplatense) a menos que el prospecto use "tu", en cuyo caso adaptate.
- Tono profesional pero cercano. Se calido sin ser demasiado formal.""",
        "informal_argentino": f"""IDIOMA Y TONO
- Responde en espanol por defecto. Si el prospecto escribe en ingles, cambia a ingles automaticamente.
- Usa "vos" siempre (espanol rioplatense con voseo). Escribi como hablarias con un amigo que te pide consejo profesional.
- Tono informal, natural y copado. {agent_name} es como un conocido que sabe mucho del tema y te ayuda con onda.
- Podes usar expresiones argentinas naturales: "dale", "genial", "barbaro", "de una", "joya".
- Evita sonar como un robot o como un vendedor de telemarketing. Se genuino.""",
        "formal_neutro": """IDIOMA Y TONO
- Responde en espanol neutro por defecto. Si el prospecto escribe en ingles, cambia a ingles.
- Usa "usted" por defecto. Si el prospecto usa "tu" o "vos", adaptate a su registro.
- Tono formal y profesional. Mantene la cortesia y claridad en cada mensaje.""",
        "friendly_english": """LANGUAGE & TONE
- Respond in English by default. If the prospect writes in Spanish, switch to Spanish.
- Use a friendly, approachable tone. Be warm but professional.
- Keep messages concise and conversational.""",
    }
    return tone_map.get(ai_tone, tone_map["profesional_argentino"])


def _build_qualification_section(questions: list) -> str:
    """Builds the qualification flow section from config questions."""
    if not questions or not isinstance(questions, list) or len(questions) == 0:
        return """FLUJO DE CALIFICACION (segui este orden natural, sin parecer un formulario):
1. **Necesidad**: Pregunta en que servicio o solucion esta interesado/a.
2. **Urgencia/timeline**: "Para cuando necesitarias esto?" o similar.
3. **Presupuesto**: Abordalo con tacto, ej. "Tenes un rango de inversion en mente?".
4. **Tamano de empresa / contexto**: "Me contas un poco sobre tu empresa/proyecto?".
Cuando tengas suficiente informacion (al menos necesidad + timeline), usa la herramienta qualify_lead para registrar la calificacion."""

    lines = [
        "FLUJO DE CALIFICACION (segui este orden natural, sin parecer un formulario):"
    ]
    for i, q in enumerate(questions, 1):
        if isinstance(q, dict):
            label = q.get("label", f"Pregunta {i}")
            example = q.get("example", "")
            lines.append(
                f'{i}. **{label}**: "{example}"' if example else f"{i}. **{label}**"
            )
        else:
            lines.append(f"{i}. {q}")
    lines.append(
        "Cuando tengas suficiente informacion (al menos necesidad + timeline), usa la herramienta qualify_lead para registrar la calificacion."
    )
    return "\n".join(lines)


def _build_objection_section(objections: list) -> str:
    """Builds the objection handling section from config."""
    if not objections or not isinstance(objections, list) or len(objections) == 0:
        return ""

    lines = ["\nMANEJO DE OBJECIONES"]
    for obj in objections:
        if isinstance(obj, dict):
            objection = obj.get("objection", "")
            response = obj.get("response", "")
            if objection and response:
                lines.append(f'- Si dice "{objection}": {response}')
        elif isinstance(obj, str):
            lines.append(f"- {obj}")
    lines.append("")
    return "\n".join(lines)


def _build_hours_section(business_hours: dict, bh_start: str, bh_end: str) -> str:
    """Builds business hours info for the prompt."""
    if business_hours and isinstance(business_hours, dict) and len(business_hours) > 0:
        lines = ["\nHORARIO DE ATENCION"]
        for day, hours in business_hours.items():
            lines.append(f"- {day}: {hours}")
        lines.append(
            f"Fuera de horario, informa que el equipo respondera en el proximo dia habil, pero que vos podes seguir ayudando.\n"
        )
        return "\n".join(lines)
    else:
        return f"""
HORARIO DE ATENCION
- Lunes a Viernes: {bh_start} - {bh_end}
Fuera de horario, informa que el equipo respondera en el proximo dia habil, pero que vos podes seguir ayudando.
"""


def _default_system_prompt(tenant_name: str, agent_name: str) -> str:
    """Fallback system prompt when no tenant row is found."""
    return f"""Sos {agent_name} de {tenant_name}. Tu mision es atender a cada prospecto que escriba por WhatsApp de forma profesional, calida y consultiva.
Responde en espanol rioplatense con voseo. Se conciso (1-3 oraciones por mensaje). Nunca reveles que sos IA salvo que te pregunten directamente.
Califica leads preguntando: necesidad, timeline, presupuesto, tamano de empresa.
Usa las herramientas qualify_lead, book_sales_meeting, request_human_handoff, assign_lead_tags, derive_to_setter segun corresponda."""


# --- PUBLIC WEBHOOK PROXIES ---
import httpx
from fastapi.responses import Response


@app.post("/webhook/ycloud/{tenant_id}", tags=["Webhooks"])
async def proxy_ycloud_webhook(tenant_id: int, request: Request):
    """
    Proxies inbound YCloud webhooks from the public orchestrator domain to the internal whatsapp_service.
    """
    WHATSAPP_SERVICE_URL = os.getenv(
        "WHATSAPP_SERVICE_URL", "http://whatsapp_service:8002"
    )

    body = await request.body()
    headers = dict(request.headers)
    headers.pop("host", None)  # Remove host to avoid conflicts

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{WHATSAPP_SERVICE_URL}/webhook/ycloud/{tenant_id}",
                content=body,
                headers=headers,
                timeout=15.0,
            )
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                media_type=resp.headers.get("content-type"),
            )
        except httpx.RequestError as e:
            logger.error(f"Error proxying webhook to whatsapp_service: {e}")
            raise HTTPException(status_code=502, detail="Bad Gateway")


# --- INTERNAL CHAT (Multi-Channel inbound: WhatsApp / Instagram / Facebook) ---
INTERNAL_API_TOKEN = os.getenv("INTERNAL_API_TOKEN", "internal-secret-token")

# Valid channel sources for multi-channel routing
_VALID_CHANNELS = {"whatsapp", "instagram", "facebook"}


def _verify_internal_token(x_internal_token: Optional[str] = Header(None)):
    if not x_internal_token or x_internal_token != INTERNAL_API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing internal token")
    return x_internal_token


@app.post("/chat", tags=["Internal"])
async def chat_inbound(
    request: Request,
    _token: str = Depends(_verify_internal_token),
):
    """
    Receives inbound messages from any channel (WhatsApp, Instagram, Facebook).
    Deduplicates by provider+provider_message_id, ensures lead exists (CRM),
    appends user message, runs agent, appends assistant reply, returns response for sending.

    Multi-channel fields (all optional, backward-compat with WhatsApp-only callers):
      - channel_source / platform: "whatsapp" | "instagram" | "facebook"  (default: "whatsapp")
      - external_user_id: phone number (whatsapp) or PSID (instagram/facebook)
      - platform_message_id: provider-level message ID for dedup
      - media: list of media attachments from Meta messaging
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    provider = body.get("provider") or "ycloud"
    event_id = body.get("event_id") or ""
    provider_message_id = body.get("provider_message_id") or event_id
    from_number = body.get("from_number") or ""
    text = body.get("text") or ""
    customer_name = body.get("customer_name")
    to_number = body.get("to_number")
    correlation_id = body.get("correlation_id") or ""
    media = body.get("media")  # List of media attachments from Meta messaging

    # --- Multi-channel identity ---
    # channel_source / platform are interchangeable; prefer channel_source
    channel_source = body.get("channel_source") or body.get("platform") or "whatsapp"
    if channel_source not in _VALID_CHANNELS:
        channel_source = "whatsapp"  # safe fallback

    # external_user_id: PSID for IG/FB, phone for WhatsApp
    external_user_id = body.get("external_user_id") or ""
    if not external_user_id:
        # Derive from sender_id (IG/FB webhook field) or from_number (WhatsApp)
        external_user_id = body.get("sender_id") or from_number
    platform_msg_id = body.get("platform_message_id") or provider_message_id

    # Validation: need at least one identifier
    if channel_source == "whatsapp" and not from_number:
        raise HTTPException(
            status_code=400, detail="from_number required for whatsapp channel"
        )
    if channel_source in ("instagram", "facebook") and not external_user_id:
        raise HTTPException(
            status_code=400,
            detail="external_user_id or sender_id required for instagram/facebook channel",
        )
    if text is None:
        raise HTTPException(status_code=400, detail="text is required")

    # For IG/FB: if from_number wasn't provided, use external_user_id as conversation key
    if not from_number:
        from_number = external_user_id

    # Conversation key: prefixed for IG/FB to avoid PSID-phone collisions
    conversation_key = from_number
    if channel_source in ("instagram", "facebook"):
        conversation_key = f"{channel_source}:{from_number}"

    # Resolve tenant (prioritize explicit tenant_id from payload)
    tenant_id = body.get("tenant_id")
    if not tenant_id and to_number:
        row = await db.fetchrow(
            "SELECT id FROM tenants WHERE bot_phone_number = $1 LIMIT 1",
            to_number,
        )
        if row:
            tenant_id = row["id"]

    if not tenant_id:
        tenant_id = 1  # Extreme fallback

    # Critical: Ensure tenant_id is int for asyncpg (Spec Database Evolution)
    tenant_id = int(tenant_id)

    logger.info(
        f"chat_inbound: channel={channel_source} ext_id={external_user_id} from={from_number} tenant={tenant_id}"
    )

    is_new = await db.try_insert_inbound(
        provider, provider_message_id, event_id, conversation_key, body, correlation_id
    )
    if not is_new:
        return {"status": "duplicate", "send": False}

    await db.mark_inbound_processing(provider, provider_message_id)
    try:
        # Pass referral + channel info to ensure_lead_exists (Spec Meta Attribution + Multi-Channel)
        referral = body.get("referral")

        # Determine source label based on channel
        source_label = {
            "whatsapp": "whatsapp_inbound",
            "instagram": "instagram_dm",
            "facebook": "facebook_messenger",
        }.get(channel_source, "whatsapp_inbound")

        # For WhatsApp: phone_number is from_number; for IG/FB: phone may be empty, lead identified by PSID
        _phone_for_lead = (
            from_number
            if channel_source == "whatsapp"
            else (body.get("from_number") or "")
        )

        lead = await db.ensure_lead_exists(
            tenant_id,
            _phone_for_lead,
            customer_name=customer_name,
            source=source_label,
            referral=referral,
            channel_source=channel_source,
            external_user_id=external_user_id,
        )

        # --- DEV-49: Check for Human Override / Silence ---
        if lead and lead.get("human_override_until"):
            until = lead["human_override_until"]
            # Ensure TZ awareness
            if until.tzinfo is None:
                from core.utils import ARG_TZ

                until = until.replace(tzinfo=ARG_TZ)

            if until > datetime.now(until.tzinfo):
                logger.info(
                    f"Chat inbound: Lead {from_number} is silenciated (Human Override) until {until}"
                )
                # Append user message so it shows in history, but don't respond
                await db.append_chat_message(
                    conversation_key,
                    "user",
                    text,
                    correlation_id,
                    tenant_id,
                    platform=channel_source,
                    platform_message_id=platform_msg_id,
                    channel_source=channel_source,
                    external_user_id=external_user_id,
                )
                await db.mark_inbound_done(provider, provider_message_id)

                # Emit to supervisor even if silenced (monitoring)
                try:
                    await sio.emit(
                        "SUPERVISOR_CHAT_EVENT",
                        {
                            "tenant_id": tenant_id,
                            "lead_id": str(lead.get("id")) if lead else None,
                            "phone_number": from_number,
                            "content": text,
                            "role": "user",
                            "channel_source": channel_source,
                            "external_user_id": external_user_id,
                            "is_silenced": True,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                        room=f"supervisors:{tenant_id}",
                    )
                except Exception as e:
                    logger.error(f"Error emitting supervisor event (silenced): {e}")

                return {
                    "status": "silenced",
                    "send": False,
                    "text": "Human override active",
                    "channel_source": channel_source,
                    "external_user_id": external_user_id,
                }

        # Notify via Socket.IO if attributed (Spec Mission 4)
        if referral and lead and lead.get("lead_source") == "META_ADS":
            try:
                await sio.emit(
                    "META_LEAD_RECEIVED",
                    {
                        "tenant_id": tenant_id,
                        "lead_id": str(lead.get("id")),
                        "phone_number": conversation_key,
                        "channel_source": channel_source,
                        "name": f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip(),
                        "ad_id": referral.get("ad_id"),
                        "headline": referral.get("headline"),
                        "timestamp": datetime.now().isoformat(),
                    },
                )
                logger.info(f"Socket META_LEAD_RECEIVED emitted for {conversation_key}")
            except Exception as sio_err:
                logger.error(f"Error emitting Meta lead notification: {sio_err}")

        # --- DEV-52: Broadcast to Supervisor Mode ---
        try:
            await sio.emit(
                "SUPERVISOR_CHAT_EVENT",
                {
                    "tenant_id": tenant_id,
                    "lead_id": str(lead.get("id")) if lead else None,
                    "phone_number": from_number,
                    "content": text,
                    "role": "user",
                    "channel_source": channel_source,
                    "external_user_id": external_user_id,
                    "is_silenced": False,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                room=f"supervisors:{tenant_id}",
            )
            logger.info(
                f"Supervisor event emitted for {from_number} in tenant {tenant_id}"
            )
        except Exception as e:
            logger.error(f"Error emitting supervisor event: {e}")

        # --- DEV-19: Auto-detect "sin_respuesta" tag ---
        # If the last assistant message was sent >24h ago and no user message since,
        # the lead was unresponsive. Auto-tag before processing current message.
        try:
            # Use channel-aware query for IG/FB, from_number for WhatsApp
            if channel_source != "whatsapp" and external_user_id:
                last_msg_row = await db.fetchrow(
                    """
                    SELECT role, created_at FROM chat_messages
                    WHERE tenant_id = $1 AND channel_source = $2 AND external_user_id = $3
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    tenant_id,
                    channel_source,
                    external_user_id,
                )
            else:
                last_msg_row = await db.fetchrow(
                    """
                    SELECT role, created_at FROM chat_messages
                    WHERE from_number = $1 AND tenant_id = $2
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    from_number,
                    tenant_id,
                )
            if last_msg_row and last_msg_row["role"] == "assistant":
                from datetime import timedelta as _td

                gap = (
                    datetime.now(
                        last_msg_row["created_at"].tzinfo
                        if last_msg_row["created_at"].tzinfo
                        else None
                    )
                    - last_msg_row["created_at"]
                )
                if gap > _td(hours=24):
                    # Lead was silent for >24h after our last message -- auto-tag
                    # Find lead by channel-appropriate lookup
                    _lead_row = None
                    if channel_source == "instagram":
                        _lead_row = await db.fetchrow(
                            "SELECT id, tags FROM leads WHERE tenant_id = $1 AND instagram_psid = $2",
                            tenant_id,
                            external_user_id,
                        )
                    elif channel_source == "facebook":
                        _lead_row = await db.fetchrow(
                            "SELECT id, tags FROM leads WHERE tenant_id = $1 AND facebook_psid = $2",
                            tenant_id,
                            external_user_id,
                        )
                    if not _lead_row:
                        # Fallback to phone lookup (works for WhatsApp or cross-channel leads)
                        from core.utils import normalize_phone as _norm

                        _phone = _norm(from_number)
                        if _phone:
                            _lead_row = await db.fetchrow(
                                "SELECT id, tags FROM leads WHERE tenant_id = $1 AND phone_number = $2",
                                tenant_id,
                                _phone,
                            )
                    if _lead_row:
                        _existing = _lead_row["tags"] if _lead_row["tags"] else []
                        if isinstance(_existing, str):
                            _existing = json.loads(_existing)
                        if "sin_respuesta" not in _existing:
                            _merged = list(dict.fromkeys(_existing + ["sin_respuesta"]))
                            await db.execute(
                                "UPDATE leads SET tags = $1, updated_at = NOW() WHERE id = $2",
                                json.dumps(_merged),
                                _lead_row["id"],
                            )
                            await db.execute(
                                "INSERT INTO lead_tag_log (tenant_id, lead_id, tags_added, reason, source) VALUES ($1, $2, $3, $4, 'system_auto')",
                                tenant_id,
                                _lead_row["id"],
                                ["sin_respuesta"],
                                f"Lead no respondio por {gap.days}d {gap.seconds // 3600}h desde ultimo mensaje del asistente",
                            )
                            logger.info(
                                f"Auto-tagged lead {channel_source}:{external_user_id} as sin_respuesta (gap: {gap})"
                            )
        except Exception as tag_err:
            logger.warning(f"sin_respuesta auto-tag check failed: {tag_err}")

        await db.append_chat_message(
            conversation_key,
            "user",
            text,
            correlation_id,
            tenant_id,
            platform=channel_source,
            platform_message_id=platform_msg_id,
            channel_source=channel_source,
            external_user_id=external_user_id,
        )

        # --- DEV-49: Frustration Detection ---
        try:
            from services.frustration_detection_service import (
                detect_frustration,
                handle_escalation,
            )

            frustration_result = await detect_frustration(
                tenant_id, str(lead["id"]), text
            )
            if frustration_result["score"] >= 70:
                logger.warning(
                    f"DEV-49: High frustration detected for lead {lead['id']}: {frustration_result['score']}"
                )
                # Escalar: pausa 24h, notificar, etc.
                escalation = await handle_escalation(
                    tenant_id, str(lead["id"]), frustration_result, db.pool
                )
                # No respondemos con IA
                await db.mark_inbound_done(provider, provider_message_id)
                return {
                    "status": "escalated",
                    "send": False,
                    "text": "Frustration detected. Escalated to human.",
                    "score": frustration_result["score"],
                    "channel_source": channel_source,
                    "external_user_id": external_user_id,
                }
        except Exception as frustrate_err:
            logger.error(f"Error in frustration detection: {frustrate_err}")

        # Build history (previous messages only; current turn is "input")
        history_raw = await db.get_chat_history(
            conversation_key,
            limit=15,
            tenant_id=tenant_id,
            channel_source=channel_source,
            external_user_id=external_user_id,
        )
        # Exclude the message we just added (last one is current user)
        if (
            history_raw
            and history_raw[-1].get("content") == text
            and history_raw[-1].get("role") == "user"
        ):
            history_raw = history_raw[:-1]
        from langchain_core.messages import HumanMessage, AIMessage

        lc_history = []
        for m in history_raw:
            if m.get("role") == "user":
                lc_history.append(HumanMessage(content=m.get("content", "")))
            elif m.get("role") == "assistant":
                lc_history.append(AIMessage(content=m.get("content", "")))

        current_customer_phone.set(conversation_key)
        current_tenant_id.set(tenant_id)
        agent = await get_agent_executor(tenant_id)
        result = await agent.ainvoke({"history": lc_history, "input": text})
        output = (result.get("output") or "").strip()

        await db.append_chat_message(
            conversation_key,
            "assistant",
            output,
            correlation_id,
            tenant_id,
            platform=channel_source,
            platform_message_id=None,
            channel_source=channel_source,
            external_user_id=external_user_id,
        )
        await db.mark_inbound_done(provider, provider_message_id)
        return {
            "status": "ok",
            "send": True,
            "text": output,
            "messages": [{"text": output}],
            "channel_source": channel_source,
            "external_user_id": external_user_id,
            "from_number": from_number,
            "conversation_key": conversation_key,
        }
    except Exception as e:
        logger.exception("chat_inbound_error")
        await db.mark_inbound_failed(provider, provider_message_id, str(e))
        return {"status": "error", "send": False, "text": None, "error": str(e)}


# --- EVENTOS ---
@app.on_event("startup")
async def startup_event():
    await db.connect()
    logger.info("🚀 Nexus Orchestrator v7.6 Started")

    # Initialize notification socket handlers
    try:
        from core.socket_notifications import register_notification_socket_handlers

        register_notification_socket_handlers()
        logger.info("✅ Notification socket handlers registered")
    except Exception as e:
        logger.error(f"❌ Error registering notification socket handlers: {e}")

    # Start scheduled tasks if enabled
    try:
        from services.scheduled_tasks import scheduled_tasks_service

        # Check if scheduled tasks should be enabled
        enable_tasks = os.getenv("ENABLE_SCHEDULED_TASKS", "true").lower() == "true"

        if enable_tasks:
            # Configurar intervalos personalizados si están definidos
            notification_interval = int(
                os.getenv("NOTIFICATION_CHECK_INTERVAL_MINUTES", "5")
            )
            metrics_interval = int(os.getenv("METRICS_REFRESH_INTERVAL_MINUTES", "15"))
            cleanup_interval = int(os.getenv("CLEANUP_INTERVAL_HOURS", "1"))

            logger.info(f"📅 Scheduled tasks configuration:")
            logger.info(
                f"   • Notification checks: every {notification_interval} minutes"
            )
            logger.info(f"   • Metrics refresh: every {metrics_interval} minutes")
            logger.info(f"   • Data cleanup: every {cleanup_interval} hours")

            # Iniciar tareas
            scheduled_tasks_service.start_all_tasks()

            # Verificar que se iniciaron correctamente
            task_status = scheduled_tasks_service.get_task_status()
            if task_status.get("scheduler_running", False):
                logger.info(
                    f"✅ Scheduled tasks started ({task_status.get('total_tasks', 0)} tasks)"
                )

                # Log de tareas programadas
                for task in task_status.get("tasks", []):
                    logger.info(f"   • {task.get('name')}: {task.get('trigger')}")
            else:
                logger.warning("⚠️  Scheduler started but not running")
        else:
            logger.info(
                "⚠️  Scheduled tasks disabled by environment variable (ENABLE_SCHEDULED_TASKS=false)"
            )

    except ImportError as e:
        logger.error(f"❌ Could not import scheduled tasks service: {e}")
        logger.info("💡 Install apscheduler: pip install apscheduler")
    except Exception as e:
        logger.error(f"❌ Error starting scheduled tasks: {e}")
        import traceback

        traceback.print_exc()

    # DEV-34 Part 2: Start Email Lead Monitor polling if IMAP is configured
    try:
        imap_host = os.getenv("IMAP_HOST", "")
        if imap_host:
            from services.email_lead_monitor import email_lead_monitor

            poll_interval = int(os.getenv("EMAIL_MONITOR_INTERVAL_SECONDS", "120"))
            await email_lead_monitor.start_polling(interval_seconds=poll_interval)
            logger.info(
                f"✅ Email Lead Monitor started (IMAP: {imap_host}, every {poll_interval}s)"
            )
        else:
            logger.info("⚠️  Email Lead Monitor disabled (IMAP_HOST not set)")
    except Exception as e:
        logger.error(f"❌ Error starting Email Lead Monitor: {e}", exc_info=True)


@app.on_event("shutdown")
async def shutdown_event():
    # Stop email lead monitor
    try:
        from services.email_lead_monitor import email_lead_monitor

        email_lead_monitor.stop_polling()
    except Exception:
        pass

    # Stop scheduled tasks
    try:
        from services.scheduled_tasks import scheduled_tasks_service

        scheduled_tasks_service.stop_all_tasks()
        logger.info("✅ Scheduled tasks stopped")
    except Exception as e:
        logger.error(f"❌ Error stopping scheduled tasks: {e}")

    await db.disconnect()
    await engine.dispose()


async def emit_event_shim(event: str, data: dict):
    await sio.emit(event, data)


app.state.emit_appointment_event = emit_event_shim

# =============================================================================
# NOVA VOICE — WebSocket Handler (CRM Sales)
# =============================================================================


@app.websocket("/public/nova/voice")
async def nova_voice_crm(websocket: WebSocket):
    """Nova Voice Assistant for CRM Sales — WebSocket bridge to OpenAI Realtime API."""
    import json as json_mod

    # Parse query params
    query_params = dict(websocket.query_params)
    token = query_params.get("token", "")
    tenant_id_str = query_params.get("tenant_id", "1")
    page = query_params.get("page", "dashboard")

    # Validate JWT
    try:
        from auth import decode_token

        payload = decode_token(token)
        user_id = payload.get("user_id", "")
        user_role = payload.get("role", "ceo")
        tenant_id = int(payload.get("tenant_id", tenant_id_str))
    except Exception:
        await websocket.close(code=4001, reason="Invalid token")
        return

    await websocket.accept()
    logger.info(
        f"🎙️ NOVA CRM: Connected tenant={tenant_id} role={user_role} page={page}"
    )

    # Get model from DB config
    model = "gpt-4o-realtime-preview"
    try:
        from dashboard.config_manager import get_config

        model = await get_config(
            db.pool, tenant_id, "MODEL_NOVA_VOICE", "gpt-4o-realtime-preview"
        )
    except Exception:
        pass

    # Build system prompt
    system_prompt = f"""IDIOMA: Espanol argentino con voseo. NUNCA cambies de idioma.

Sos Nova, la inteligencia artificial de ventas del CRM. Sos como Jarvis pero para un equipo de ventas.
Pagina: {page}. Rol: {user_role}. Tenant: {tenant_id}.

PRINCIPIO: Ejecutar primero, hablar despues. Tu PRIMER instinto ante cualquier pedido es ejecutar una tool.

TOOLS (20):
LEADS: buscar_lead, ver_lead, registrar_lead, actualizar_lead, cambiar_estado_lead
PIPELINE: ver_pipeline, mover_lead_etapa, resumen_pipeline, leads_por_etapa
AGENDA: ver_agenda_hoy, agendar_llamada, proxima_llamada
ANALYTICS: resumen_ventas, rendimiento_vendedor, conversion_rate
NAVEGACION: ir_a_pagina, ir_a_lead
COMUNICACION: ver_chats_recientes, enviar_whatsapp, ver_sellers

REGLAS:
- Ejecutar tools SIN confirmacion intermedia
- Sin dato → inferilo o preguntá UNA vez
- NUNCA inventes datos. SIEMPRE tools.
- Formato: 2-3 oraciones breves. Montos: $15.000.
"""

    # Import tools
    from services.nova_tools_crm import NOVA_CRM_TOOLS_SCHEMA, execute_nova_crm_tool

    # Connect to OpenAI Realtime
    import websockets

    openai_key = os.getenv("OPENAI_API_KEY", "")
    openai_url = f"wss://api.openai.com/v1/realtime?model={model}"

    try:
        async with websockets.connect(
            openai_url,
            extra_headers={
                "Authorization": f"Bearer {openai_key}",
                "OpenAI-Beta": "realtime=v1",
            },
        ) as openai_ws:
            # Send session config
            session_config = {
                "type": "session.update",
                "session": {
                    "modalities": ["audio", "text"],
                    "instructions": system_prompt,
                    "voice": "alloy",
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "tools": NOVA_CRM_TOOLS_SCHEMA,
                    "tool_choice": "auto",
                    "temperature": 0.7,
                },
            }
            await openai_ws.send(json_mod.dumps(session_config))
            logger.info(
                f"🎙️ NOVA CRM: session.update sent with {len(NOVA_CRM_TOOLS_SCHEMA)} tools"
            )

            async def relay_browser_to_openai():
                """Forward browser audio/text to OpenAI."""
                try:
                    async for message in websocket.iter_bytes():
                        try:
                            data = json_mod.loads(message)
                            await openai_ws.send(json_mod.dumps(data))
                        except (json_mod.JSONDecodeError, ValueError):
                            # Raw audio bytes
                            import base64

                            audio_b64 = base64.b64encode(message).decode()
                            await openai_ws.send(
                                json_mod.dumps(
                                    {
                                        "type": "input_audio_buffer.append",
                                        "audio": audio_b64,
                                    }
                                )
                            )
                except Exception as e:
                    logger.info(f"🎙️ NOVA CRM: Browser disconnected: {e}")

            async def relay_openai_to_browser():
                """Forward OpenAI responses to browser, handle tool calls."""
                try:
                    async for message in openai_ws:
                        data = json_mod.loads(message)
                        event_type = data.get("type", "")

                        # Handle tool calls
                        if event_type == "response.function_call_arguments.done":
                            tool_name = data.get("name", "")
                            tool_args_str = data.get("arguments", "{}")
                            call_id = data.get("call_id", "")

                            try:
                                tool_args = json_mod.loads(tool_args_str)
                            except:
                                tool_args = {}

                            logger.info(f"🎙️ NOVA CRM TOOL: {tool_name}({tool_args})")

                            # Execute tool
                            result = await execute_nova_crm_tool(
                                tool_name, tool_args, tenant_id, user_role, user_id
                            )

                            logger.info(
                                f"🎙️ NOVA CRM RESULT: {tool_name} → {result[:100]}"
                            )

                            # Send result back to OpenAI
                            await openai_ws.send(
                                json_mod.dumps(
                                    {
                                        "type": "conversation.item.create",
                                        "item": {
                                            "type": "function_call_output",
                                            "call_id": call_id,
                                            "output": result,
                                        },
                                    }
                                )
                            )
                            await openai_ws.send(
                                json_mod.dumps(
                                    {
                                        "type": "response.create",
                                    }
                                )
                            )

                        # Forward everything to browser
                        await websocket.send_text(json_mod.dumps(data))

                except Exception as e:
                    logger.info(f"🎙️ NOVA CRM: OpenAI disconnected: {e}")

            # Run both relays concurrently
            await asyncio.gather(
                relay_browser_to_openai(),
                relay_openai_to_browser(),
            )

    except Exception as e:
        logger.error(f"🎙️ NOVA CRM ERROR: {e}")
        try:
            await websocket.close()
        except:
            pass


# --- MAIN ENTRYPOINT (For Uvicorn) ---
final_app = socketio.ASGIApp(sio, app)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(final_app, host="0.0.0.0", port=8000)
