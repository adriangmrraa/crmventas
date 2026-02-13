import os
import json
import logging
import asyncio
import socketio
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, Request
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
import modules.dental.tools_provider  # Import to register dental tools
import modules.crm_sales.tools_provider  # Import to register CRM Sales tools
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
    "https://dentalogic-frontend.onrender.com",
    "https://dentalogic.co",
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

# Dynamic Niche Router Loading
SUPPORTED_NICHES = ["dental", "crm_sales"]
for niche in SUPPORTED_NICHES:
    NicheManager.load_niche_router(app, niche)

# Dental also under /admin/core so frontend dashboard (stats/summary, chat/urgencies) resolves
try:
    from modules.dental import routes as dental_routes
    app.include_router(dental_routes.router, prefix="/admin/core", tags=["Dental (Admin)"])
    logger.info("✅ Dental API also mounted at /admin/core")
except Exception as e:
    logger.warning(f"Could not mount Dental under /admin/core: {e}")

# CRM Sales also under /admin/core/crm so proxy/CORS work (same path as other admin routes)
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
    Creates an AgentExecutor with tools and prompt specific to the tenant's niche.
    This function should be called per request to ensure correct tool and prompt loading.
    """
    # Fetch niche type from database
    niche_type = await db.fetchval("SELECT niche_type FROM tenants WHERE id = $1", tenant_id)
    if not niche_type:
        niche_type = 'dental'  # Default fallback
    
    # Get tools from registry
    tools = tool_registry.get_tools(niche_type, tenant_id)
    
    # Load dynamic context and prompt
    if niche_type == 'dental':
        from modules.dental.context import get_dental_context
        context_data = await get_dental_context(tenant_id)
        system_prompt = prompt_loader.load_prompt('dental', 'base_assistant.txt', context_data)
    elif niche_type == 'crm_sales':
        # CRM: cuando agendan una reunión usá book_sales_meeting; la persona pasa a ser lead (no cliente).
        system_prompt = (
            "Sos un asistente de ventas inteligente. Cuando el usuario quiera agendar una reunión, "
            "una demo o una llamada, usá la herramienta book_sales_meeting con la fecha/hora, el motivo y el nombre si lo da. "
            "Al agendar, la persona se registra como lead (después el equipo puede pasarla a cliente activo desde el CRM)."
        )
    else:
        system_prompt = "You are a helpful assistant."
    
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