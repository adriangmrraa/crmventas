import os
import json
import logging
import asyncio
import socketio
from datetime import datetime
from typing import Optional, List, Any

from fastapi import FastAPI, Request, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor
from langchain_community.agent_toolkits.load_tools import load_tools
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from db import db
from admin_routes import router as admin_router
from auth_routes import router as auth_router
import modules.crm_sales.tools_provider  # Import to register CRM Sales tools (single-niche: CRM only)
from core.socket_manager import sio
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

# --- APP SETUP ---
app = FastAPI(title="Nexus Orchestrator", version="7.6.0")

# CORS: merge defaults with CORS_ALLOWED_ORIGINS (comma-separated) for EasyPanel/custom deployments
_default_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://crmventas-frontend.ugwrjq.easypanel.host",  # EasyPanel CRM Ventas frontend
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

# --- SOCKET.IO ---
sio_app = socketio.ASGIApp(sio, app)

# --- ROUTERS ---
app.include_router(auth_router)
app.include_router(admin_router)

# Single-niche: CRM Sales only (no dental)
SUPPORTED_NICHES = ["crm_sales"]
for niche in SUPPORTED_NICHES:
    NicheManager.load_niche_router(app, niche)

# CRM Sales under /admin/core/crm so proxy/CORS work (same path as other admin routes)
try:
    from modules.crm_sales import routes as crm_routes
    app.include_router(crm_routes.router, prefix="/admin/core/crm", tags=["CRM Sales (Admin)"])
    logger.info("✅ CRM API also mounted at /admin/core/crm")
except Exception as e:
    logger.warning(f"Could not mount CRM under /admin/core/crm: {e}")

# --- LANGCHAIN AGENT FACTORY ---
llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=OPENAI_API_KEY)

async def get_agent_executor(tenant_id: int):
    """
    Creates an AgentExecutor with CRM Sales tools and prompt (single-niche: no dental).
    """
    niche_type = await db.fetchval("SELECT COALESCE(niche_type, 'crm_sales') FROM tenants WHERE id = $1", tenant_id) or "crm_sales"
    tools = tool_registry.get_tools(niche_type, tenant_id)
    # CRM: cuando agendan una reunión usá book_sales_meeting; la persona pasa a ser lead (no cliente).
    system_prompt = (
        "Sos un asistente de ventas inteligente. Cuando el usuario quiera agendar una reunión, "
        "una demo o una llamada, usá la herramienta book_sales_meeting con la fecha/hora, el motivo y el nombre si lo da. "
        "Al agendar, la persona se registra como lead (después el equipo puede pasarla a cliente activo desde el CRM)."
    )
    
    # Create dynamic prompt template
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    # Create agent with niche-specific tools and prompt
    from langchain.agents import create_openai_tools_agent
    agent = create_openai_tools_agent(llm, tools, prompt_template)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)


# --- INTERNAL CHAT (WhatsApp inbound) ---
INTERNAL_API_TOKEN = os.getenv("INTERNAL_API_TOKEN", "internal-secret-token")


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
    Receives inbound WhatsApp (or other) events from whatsapp_service.
    Deduplicates by provider+provider_message_id, ensures lead exists (CRM),
    appends user message, runs agent, appends assistant reply, returns response for sending.
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

    if not from_number or text is None:
        raise HTTPException(status_code=400, detail="from_number and text required")

    # Resolve tenant (by bot phone number or default 1)
    tenant_id = 1
    if to_number:
        row = await db.fetchrow(
            "SELECT id FROM tenants WHERE bot_phone_number = $1 LIMIT 1",
            to_number,
        )
        if row:
            tenant_id = row["id"]

    is_new = await db.try_insert_inbound(
        provider, provider_message_id, event_id, from_number, body, correlation_id
    )
    if not is_new:
        return {"status": "duplicate", "send": False}

    await db.mark_inbound_processing(provider, provider_message_id)
    try:
        await db.ensure_lead_exists(
            tenant_id, from_number, customer_name=customer_name, source="whatsapp"
        )

        await db.append_chat_message(
            from_number, "user", text, correlation_id, tenant_id
        )

        # Build history (previous messages only; current turn is "input")
        history_raw = await db.get_chat_history(from_number, limit=15, tenant_id=tenant_id)
        # Exclude the message we just added (last one is current user)
        if history_raw and history_raw[-1].get("content") == text and history_raw[-1].get("role") == "user":
            history_raw = history_raw[:-1]
        from langchain_core.messages import HumanMessage, AIMessage
        lc_history = []
        for m in history_raw:
            if m.get("role") == "user":
                lc_history.append(HumanMessage(content=m.get("content", "")))
            elif m.get("role") == "assistant":
                lc_history.append(AIMessage(content=m.get("content", "")))

        current_customer_phone.set(from_number)
        current_tenant_id.set(tenant_id)
        agent = await get_agent_executor(tenant_id)
        result = await agent.ainvoke({"history": lc_history, "input": text})
        output = (result.get("output") or "").strip()

        await db.append_chat_message(
            from_number, "assistant", output, correlation_id, tenant_id
        )
        await db.mark_inbound_done(provider, provider_message_id)
        return {"status": "ok", "send": True, "text": output, "messages": [{"text": output}]}
    except Exception as e:
        logger.exception("chat_inbound_error")
        await db.mark_inbound_failed(provider, provider_message_id, str(e))
        return {"status": "error", "send": False, "text": None, "error": str(e)}


# --- EVENTOS ---
@app.on_event("startup")
async def startup_event():
    await db.connect()
    logger.info("🚀 Nexus Orchestrator v7.6 Started")

@app.on_event("shutdown")
async def shutdown_event():
    await db.disconnect()
    await engine.dispose()

async def emit_event_shim(event: str, data: dict):
    await sio.emit(event, data)
app.state.emit_appointment_event = emit_event_shim

# --- MAIN ENTRYPOINT (For Uvicorn) ---
final_app = socketio.ASGIApp(sio, app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(final_app, host="0.0.0.0", port=8000)