# Spec 04 — Database Evolution + Nova Voice for CRM Ventas

**Status**: Draft
**Date**: 2026-03-27
**Author**: Engineering
**Priority**: High
**Depends on**: Spec 01 (baseline Alembic), Spec 03 (existing schema)

---

## Table of Contents

1. [Context](#1-context)
2. [Feature A: Database Evolution](#2-feature-a-database-evolution)
3. [Feature B: Nova Voice for CRM Sales](#3-feature-b-nova-voice-for-crm-sales)
4. [Implementation Phases](#4-implementation-phases)
5. [Risks & Mitigations](#5-risks--mitigations)

---

## 1. Context

### Current State — CRM Ventas

**Database layer**:
- 16 idempotent patches in `orchestrator_service/db.py` (`_run_evolution_pipeline`) that run on every startup
- Foundation schema in `orchestrator_service/db/init/dentalogic_schema.sql` (30+ tables)
- Additional migration files in `orchestrator_service/migrations/` (patch_016_notifications.py, patch_018_lead_status_system.sql)
- Alembic initialized with a single empty baseline revision (`9572635983a1_baseline_crm_ventas`)
- **No `models.py`** — all database access is raw asyncpg queries
- No autogenerate capability for migrations (requires ORM models)

**Tables in production** (from schema.sql + db.py patches + migration files):

| Table | Source |
|-------|--------|
| `inbound_messages` | schema.sql |
| `chat_messages` | schema.sql |
| `tenants` | schema.sql |
| `credentials` | schema.sql + db.py patch 3 |
| `system_events` | schema.sql + db.py patch 6 |
| `users` | schema.sql + db.py patch 10 |
| `professionals` | schema.sql + db.py patch 1 |
| `sellers` | schema.sql + db.py patches 12-14 |
| `leads` | schema.sql + db.py patches 2,5,7,11,15,16 |
| `clients` | schema.sql + db.py patch 9 |
| `opportunities` | schema.sql + db.py patch 9 |
| `sales_transactions` | schema.sql + db.py patch 9 |
| `seller_agenda_events` | db.py patch 9 |
| `meta_tokens` | schema.sql + db.py patch 4 |
| `meta_ads_campaigns` | schema.sql + db.py patch 7 |
| `meta_ads_insights` | schema.sql |
| `meta_templates` | schema.sql |
| `automation_rules` | schema.sql + db.py patch 7 |
| `automation_logs` | schema.sql |
| `notifications` | db.py patch 8 + patch_016 |
| `notification_settings` | patch_016 |
| `seller_metrics` | db.py patch 11 |
| `assignment_rules` | db.py patch 11 |
| `lead_tasks` | db.py patch 16 |
| `lead_statuses` | patch_018 |
| `lead_status_transitions` | patch_018 |
| `lead_status_history` | patch_018 |
| `lead_status_triggers` | patch_018 |
| `lead_status_trigger_logs` | patch_018 |
| `patients` | schema.sql (dental legacy) |
| `clinical_records` | schema.sql (dental legacy) |
| `appointments` | schema.sql (dental legacy) |
| `treatment_types` | schema.sql (dental legacy) |

**Nova Voice**: Does not exist in CRM Ventas. ClinicForge has a working implementation with 47 tools, WebSocket handler, and NovaWidget.tsx.

### Reference — ClinicForge

- `orchestrator_service/models.py`: 31 SQLAlchemy 2.0 ORM classes
- Alembic with 6 versioned migrations (001-006)
- Nova Voice: `NovaWidget.tsx` + `nova_tools.py` (47 tools) + WebSocket handler in `main.py`
- OpenAI Realtime API for bidirectional audio + function calling

---

## 2. Feature A: Database Evolution

### 2.1 Objective

Create a proper SQLAlchemy 2.0 ORM layer for ALL existing tables and establish Alembic as the sole migration mechanism going forward. This replaces the fragile startup-patch system with a deterministic, version-controlled migration chain.

### 2.2 What to Create

#### 2.2.1 `orchestrator_service/models.py` — SQLAlchemy 2.0 ORM Classes

Create ORM model classes for every table currently in production. Use SQLAlchemy 2.0 `DeclarativeBase` style with type annotations.

**CRM Core Models (19 classes)**:

```python
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Date,
    Numeric, Float, ForeignKey, UniqueConstraint, CheckConstraint,
    Index, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET, ARRAY
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime
import uuid

class Base(DeclarativeBase):
    pass

class Tenant(Base):
    __tablename__ = "tenants"
    # id SERIAL PK, clinic_name, bot_phone_number (UNIQUE), owner_email,
    # clinic_location, clinic_website, system_prompt_template,
    # config JSONB, niche_type, total_tokens_used, total_tool_calls,
    # created_at, updated_at

class User(Base):
    __tablename__ = "users"
    # id UUID PK, email (UNIQUE), password_hash, role (CHECK), status (CHECK),
    # first_name, last_name, professional_id, tenant_id FK, created_at, updated_at

class Professional(Base):
    __tablename__ = "professionals"
    # id SERIAL PK, tenant_id FK, user_id UUID FK, first_name, last_name,
    # email, phone_number, specialty, registration_id, is_active,
    # google_calendar_id, working_hours JSONB, created_at, updated_at

class Seller(Base):
    __tablename__ = "sellers"
    # id SERIAL PK, user_id UUID FK (UNIQUE), tenant_id FK, first_name,
    # last_name, email, phone_number, is_active, created_at, updated_at

class Lead(Base):
    __tablename__ = "leads"
    # id UUID PK, tenant_id FK, phone_number, first_name, last_name, email,
    # dni, social_links JSONB, status, lead_score, stage_id UUID,
    # source, lead_source, meta_campaign_id, meta_ad_id, meta_ad_headline,
    # meta_ad_body, meta_lead_id, external_ids JSONB, assigned_seller_id UUID FK,
    # apify_* fields (title, category_name, address, city, state, country_code,
    # website, place_id, total_score, reviews_count, scraped_at, raw JSONB, rating, reviews),
    # prospecting_niche, prospecting_location_query,
    # outreach_* fields, human_handoff_requested, human_override_until,
    # tags JSONB, initial_assignment_source, assignment_history JSONB,
    # score INTEGER, score_breakdown JSONB, score_updated_at,
    # company, estimated_value DECIMAL,
    # status_changed_at, status_changed_by UUID FK, status_metadata JSONB,
    # created_at, updated_at
    # UNIQUE(tenant_id, phone_number)

class Client(Base):
    __tablename__ = "clients"
    # id SERIAL PK, tenant_id FK, phone_number, first_name, last_name,
    # email, status, notes, created_at, updated_at
    # UNIQUE(tenant_id, phone_number)

class Opportunity(Base):
    __tablename__ = "opportunities"
    # id UUID PK, tenant_id FK, lead_id UUID FK, seller_id UUID FK,
    # name, description, value DECIMAL, currency, stage, probability DECIMAL,
    # expected_close_date DATE, closed_at, close_reason,
    # tags JSONB, custom_fields JSONB, created_at, updated_at

class SalesTransaction(Base):
    __tablename__ = "sales_transactions"
    # id UUID PK, tenant_id FK, opportunity_id UUID FK, lead_id UUID FK,
    # amount DECIMAL, currency, transaction_date DATE, description,
    # payment_method, payment_status, attribution_source,
    # meta_campaign_id, meta_ad_id, created_at, updated_at

class SellerAgendaEvent(Base):
    __tablename__ = "seller_agenda_events"
    # id UUID PK, tenant_id FK, seller_id INTEGER FK(professionals),
    # title, start_datetime TIMESTAMPTZ, end_datetime TIMESTAMPTZ,
    # lead_id UUID FK, status, source, created_at, updated_at

class LeadTask(Base):
    __tablename__ = "lead_tasks"
    # id SERIAL PK, tenant_id FK, lead_id UUID FK, seller_id INTEGER FK(sellers),
    # title, description, due_date TIMESTAMPTZ, status CHECK, priority CHECK,
    # completed_at, created_at, updated_at

class LeadStatus(Base):
    __tablename__ = "lead_statuses"
    # id UUID PK, tenant_id FK, name, code, description, category,
    # color, icon, badge_style, is_active, is_initial, is_final,
    # requires_comment, sort_order, metadata JSONB, created_at, updated_at
    # UNIQUE(tenant_id, code), CHECK constraints on color and code format

class LeadStatusTransition(Base):
    __tablename__ = "lead_status_transitions"
    # id UUID PK, tenant_id FK, from_status_code FK, to_status_code FK,
    # is_allowed, requires_approval, approval_role, max_daily_transitions,
    # label, description, icon, button_style, validation_rules JSONB,
    # pre_conditions JSONB, created_at, updated_at
    # UNIQUE(tenant_id, from_status_code, to_status_code)

class LeadStatusHistory(Base):
    __tablename__ = "lead_status_history"
    # id UUID PK, lead_id UUID FK, tenant_id FK, from_status_code, to_status_code,
    # changed_by_user_id UUID FK, changed_by_name, changed_by_role,
    # changed_by_ip INET, changed_by_user_agent, comment, reason_code,
    # source, metadata JSONB, session_id UUID, request_id, created_at

class LeadStatusTrigger(Base):
    __tablename__ = "lead_status_triggers"
    # id UUID PK, tenant_id FK, trigger_name, from/to_status_code FK,
    # action_type CHECK, action_config JSONB, execution_mode CHECK,
    # delay_minutes, scheduled_time TIME, timezone, conditions JSONB,
    # filters JSONB, is_active, max_executions, error_handling, retry_count,
    # retry_delay_minutes, description, tags TEXT[], created_at, updated_at,
    # last_executed_at, execution_count

class LeadStatusTriggerLog(Base):
    __tablename__ = "lead_status_trigger_logs"
    # id UUID PK, trigger_id UUID FK, tenant_id FK, lead_id UUID FK,
    # from/to_status_code, execution_status, started_at, completed_at,
    # execution_duration_ms, result_data JSONB, error_message, error_stack,
    # retry_count, worker_id, attempt_number, created_at
```

**Infrastructure Models (7 classes)**:

```python
class InboundMessage(Base):
    __tablename__ = "inbound_messages"
    # id BIGSERIAL PK, provider, provider_message_id, event_id, from_number,
    # payload JSONB, status CHECK, received_at, processed_at, error, correlation_id
    # UNIQUE(provider, provider_message_id)

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    # id BIGSERIAL PK, tenant_id, from_number, role CHECK, content,
    # created_at, correlation_id,
    # assigned_seller_id UUID FK, assigned_at, assigned_by UUID FK, assignment_source

class Credential(Base):
    __tablename__ = "credentials"
    # id BIGSERIAL PK, tenant_id FK, name, value, category, scope,
    # description, created_at, updated_at
    # UNIQUE(tenant_id, name)

class SystemEvent(Base):
    __tablename__ = "system_events"
    # id BIGSERIAL PK, tenant_id FK, user_id UUID, event_type, severity CHECK,
    # message, payload JSONB, description, created_at

class Notification(Base):
    __tablename__ = "notifications"
    # id VARCHAR PK, tenant_id FK, type, title, message, priority CHECK,
    # recipient_id UUID FK, sender_id UUID FK, related_entity_type,
    # related_entity_id, metadata JSONB, read BOOLEAN, created_at, expires_at

class NotificationSetting(Base):
    __tablename__ = "notification_settings"
    # user_id VARCHAR PK, email_notifications, push_notifications,
    # desktop_notifications, mute_until, muted_types JSONB,
    # created_at, updated_at

class SellerMetrics(Base):
    __tablename__ = "seller_metrics"
    # id UUID PK, seller_id UUID FK, tenant_id FK,
    # total_conversations, active_conversations, conversations_assigned_today,
    # total_messages_sent/received, avg_response_time_seconds,
    # leads_assigned, leads_converted, conversion_rate DECIMAL,
    # prospects_generated/converted, total_chat_minutes, avg_session_duration_minutes,
    # last_activity_at, metrics_calculated_at, metrics_period_start/end
    # UNIQUE(seller_id, tenant_id, metrics_period_start)

class AssignmentRule(Base):
    __tablename__ = "assignment_rules"
    # id UUID PK, tenant_id FK, rule_name, rule_type CHECK, is_active,
    # priority, config JSONB, apply_to_lead_source TEXT[],
    # apply_to_lead_status TEXT[], apply_to_seller_roles TEXT[],
    # max_conversations_per_seller, min_response_time_seconds,
    # description, created_at, updated_at
    # UNIQUE(tenant_id, rule_name)
```

**Marketing Models (4 classes)**:

```python
class MetaToken(Base):
    __tablename__ = "meta_tokens"
    # id SERIAL PK, tenant_id FK, access_token, token_type, expires_at,
    # meta_user_id, business_manager_id, page_id, scopes JSONB,
    # business_managers JSONB, last_used_by UUID, created_at, updated_at
    # UNIQUE(tenant_id, token_type)

class MetaAdsCampaign(Base):
    __tablename__ = "meta_ads_campaigns"
    # id UUID PK, tenant_id FK, meta_campaign_id, meta_account_id, name,
    # objective, status, daily_budget, lifetime_budget, start_time, end_time,
    # spend, impressions, clicks, leads_count, roi_percentage, last_synced_at,
    # created_at, updated_at
    # UNIQUE(tenant_id, meta_campaign_id)

class MetaAdsInsight(Base):
    __tablename__ = "meta_ads_insights"
    # id UUID PK, tenant_id FK, meta_campaign_id, date DATE,
    # spend, impressions, clicks, leads, created_at
    # UNIQUE(tenant_id, meta_campaign_id, date)

class MetaTemplate(Base):
    __tablename__ = "meta_templates"
    # id UUID PK, tenant_id FK, meta_template_id, name, category,
    # language, status, components JSONB, created_at, updated_at
    # UNIQUE(tenant_id, meta_template_id)

class AutomationRule(Base):
    __tablename__ = "automation_rules"
    # id UUID PK, tenant_id FK, name, trigger_type, trigger_conditions JSONB,
    # action_type, action_config JSONB, is_active, created_at, updated_at

class AutomationLog(Base):
    __tablename__ = "automation_logs"
    # id UUID PK, tenant_id FK, rule_id UUID FK, trigger_type,
    # status, error_message, created_at
```

**Dental Legacy Models (4 classes)** — kept for backward compatibility:

```python
class Patient(Base):
    __tablename__ = "patients"

class ClinicalRecord(Base):
    __tablename__ = "clinical_records"

class Appointment(Base):
    __tablename__ = "appointments"

class TreatmentType(Base):
    __tablename__ = "treatment_types"
```

**Total: ~34 model classes**.

#### 2.2.2 Alembic Migration — `002_scoring_indexes`

Create the second Alembic migration for columns that exist in db.py patches 15-16 but need formal Alembic tracking, plus new performance indexes.

```python
# alembic/versions/xxx_002_scoring_indexes.py

def upgrade():
    # Columns (idempotent — IF NOT EXISTS already in db.py)
    op.execute("""
        ALTER TABLE leads ADD COLUMN IF NOT EXISTS score INTEGER DEFAULT 0;
        ALTER TABLE leads ADD COLUMN IF NOT EXISTS score_breakdown JSONB DEFAULT '{}';
        ALTER TABLE leads ADD COLUMN IF NOT EXISTS score_updated_at TIMESTAMPTZ;
        ALTER TABLE leads ADD COLUMN IF NOT EXISTS company TEXT;
        ALTER TABLE leads ADD COLUMN IF NOT EXISTS estimated_value DECIMAL(12,2) DEFAULT 0;
    """)

    # Performance indexes
    op.create_index('idx_leads_tenant_status', 'leads', ['tenant_id', 'status'],
                     if_not_exists=True)
    op.create_index('idx_leads_tenant_score_desc', 'leads',
                     ['tenant_id', sa.text('score DESC')], if_not_exists=True)
    op.create_index('idx_lead_tasks_tenant_status', 'lead_tasks',
                     ['tenant_id', 'status'], if_not_exists=True)
    op.create_index('idx_leads_assigned_seller', 'leads',
                     ['tenant_id', 'assigned_seller_id'], if_not_exists=True)
    op.create_index('idx_opportunities_tenant_stage', 'opportunities',
                     ['tenant_id', 'stage'], if_not_exists=True)

def downgrade():
    op.drop_index('idx_opportunities_tenant_stage')
    op.drop_index('idx_leads_assigned_seller')
    op.drop_index('idx_lead_tasks_tenant_status')
    op.drop_index('idx_leads_tenant_score_desc')
    op.drop_index('idx_leads_tenant_status')
    op.execute("""
        ALTER TABLE leads DROP COLUMN IF EXISTS estimated_value;
        ALTER TABLE leads DROP COLUMN IF EXISTS company;
        ALTER TABLE leads DROP COLUMN IF EXISTS score_updated_at;
        ALTER TABLE leads DROP COLUMN IF EXISTS score_breakdown;
        ALTER TABLE leads DROP COLUMN IF EXISTS score;
    """)
```

#### 2.2.3 Alembic Config Update

Update `alembic/env.py` to import `models.Base.metadata` for autogenerate support:

```python
from models import Base
target_metadata = Base.metadata
```

### 2.3 Acceptance Criteria

**AC-A1**: `orchestrator_service/models.py` exists with a SQLAlchemy 2.0 `DeclarativeBase` subclass for every table listed in section 2.2.1. Each model class includes all columns, constraints, indexes, and foreign keys that match the current production schema. Running `alembic check` produces no autogenerate diff (schema and models are in sync).

**AC-A2**: Alembic migration `002_scoring_indexes` runs successfully on both a fresh database and an existing production database without errors. The migration is idempotent (safe to re-run after db.py patches have already applied the columns). The `downgrade()` function cleanly reverses all changes.

**AC-A3**: After `models.py` is in place, running `alembic revision --autogenerate -m "test"` produces an empty migration (no detected differences between models and database), confirming the ORM is fully synchronized with the schema.

### 2.4 Files to Create/Modify

| Action | File | Description |
|--------|------|-------------|
| **CREATE** | `orchestrator_service/models.py` | ~34 SQLAlchemy 2.0 ORM model classes |
| **CREATE** | `orchestrator_service/alembic/versions/xxx_002_scoring_indexes.py` | Formal migration for score/company/estimated_value columns + indexes |
| **MODIFY** | `orchestrator_service/alembic/env.py` | Import `Base.metadata` as `target_metadata` |
| **MODIFY** | `orchestrator_service/requirements.txt` | Ensure `sqlalchemy>=2.0` is listed |

---

## 3. Feature B: Nova Voice for CRM Sales

### 3.1 Objective

Port the Nova Voice assistant from ClinicForge to CRM Ventas, adapting the 47 dental tools down to 20 sales-focused tools. Nova becomes a "Jarvis for Sales" — a floating voice widget that lets sellers and CEOs interact with the CRM by speaking naturally in Spanish.

### 3.2 Architecture

```
NovaWidget.tsx (React)
    |
    | WebSocket (wss://)
    v
Nova WebSocket Handler (main.py)
    |
    | WebSocket (wss://)
    v
OpenAI Realtime API (gpt-4o-realtime-preview)
    |
    | function_call events
    v
nova_tools_crm.py (20 tools)
    |
    | asyncpg queries
    v
PostgreSQL
```

**Data flow**:
1. User clicks the floating violet button, grants microphone access
2. Browser captures audio via `MediaRecorder` / `AudioWorklet`
3. Audio frames sent to backend via WebSocket as base64
4. Backend bridges audio to OpenAI Realtime API WebSocket
5. OpenAI processes speech, may invoke function calls
6. Backend executes tool, sends result back to OpenAI
7. OpenAI generates audio response
8. Backend streams audio back to frontend for playback
9. Navigation tools emit JSON that the widget intercepts to route the user

### 3.3 Tool Definitions (20 tools)

#### A. LEADS (5 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `buscar_lead` | Search leads by name, phone, email, or company | `query: string` |
| `ver_lead` | Full lead detail: contact, status, score, history, tasks, conversations | `lead_id: string (UUID)` |
| `registrar_lead` | Create a new lead | `phone_number, first_name, last_name?, email?, source?, company?` |
| `actualizar_lead` | Update lead fields | `lead_id: string, campos: object` |
| `cambiar_estado` | Change lead status with transition validation | `lead_id: string, nuevo_estado: string, comentario?: string` |

#### B. PIPELINE (4 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `ver_pipeline` | Overview of all pipeline stages with counts and total value | (none) |
| `mover_etapa` | Move an opportunity to a new stage | `opportunity_id: string, nueva_etapa: string` |
| `resumen_pipeline` | Weighted pipeline summary: total value, expected close this month, conversion rates | (none) |
| `leads_por_etapa` | List leads in a specific pipeline stage | `etapa: string, limite?: integer` |

#### C. AGENDA (3 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `ver_agenda_hoy` | Today's scheduled calls/events for the current seller | `seller_id?: integer` |
| `agendar_llamada` | Schedule a call or follow-up event | `lead_id: string, fecha: string, hora: string, titulo?: string, duracion_minutos?: integer` |
| `proxima_llamada` | Get the next upcoming call/event | (none) |

#### D. ANALYTICS (3 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `resumen_ventas` | Sales summary: closed deals this week/month, revenue, average ticket | `periodo?: string ("semana" / "mes")` |
| `rendimiento_vendedor` | Individual seller performance: leads assigned, conversion rate, response time | `seller_id?: integer` |
| `conversion_rate` | Overall and per-stage conversion rates | `periodo?: string` |

#### E. NAVEGACION (2 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `ir_a_pagina` | Navigate the UI to a specific page | `pagina: string ("leads" / "pipeline" / "agenda" / "analytics" / "settings" / "chats")` |
| `ir_a_lead` | Navigate directly to a lead's detail page | `lead_id: string` |

#### F. COMUNICACION (3 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `ver_chats_recientes` | List recent WhatsApp conversations | `limite?: integer` |
| `enviar_whatsapp` | Send a WhatsApp message to a lead | `lead_id: string, mensaje: string` |
| `ver_sellers` | List all active sellers with their current stats | (none) |

### 3.4 Tool Schema Format

All tool schemas MUST use the **flat** OpenAI Realtime API format:

```json
{
  "type": "function",
  "name": "buscar_lead",
  "description": "Busca un lead por nombre, telefono, email o empresa. Retorna hasta 5 resultados.",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Nombre, telefono, email o empresa del lead"
      }
    },
    "required": ["query"]
  }
}
```

**NOT** the nested `{"type": "function", "function": {...}}` format used by Chat Completions. This is a critical compatibility requirement with the Realtime API.

### 3.5 System Prompt

```
Sos Nova, la asistente de voz del CRM de ventas. Tu rol es ser el Jarvis del equipo comercial.

REGLAS DE EJECUCION:
1. Ejecuta herramientas PRIMERO, habla DESPUES. Nunca digas "voy a buscar" — simplemente busca.
2. Si te piden algo que una herramienta puede resolver, usala sin pedir confirmacion.
3. Encadena 2-3 herramientas si es necesario (ej: buscar lead + ver detalle + agendar llamada).
4. Si te falta un dato, pregunta UNA sola vez. Si podes inferirlo, inferilo.
5. NUNCA digas "no puedo" si existe una herramienta que resuelve el pedido.

ESTILO:
- Espanol rioplatense con voseo natural ("vos tenes", "mirá")
- Respuestas concisas y accionables
- Cuando listes datos, usa formato hablado natural (no markdown)
- Siempre incluí numeros y porcentajes cuando esten disponibles

CONTEXTO:
- tenant_id: {tenant_id}
- user: {user_name} ({user_role})
- Pagina actual: {current_page}
- Fecha/hora: {now}
```

### 3.6 Frontend — NovaWidget.tsx

Port from ClinicForge's `NovaWidget.tsx` with the following adaptations:

**Visual changes**:
- Primary color: violet (`bg-violet-600`) instead of blue — sales identity
- Floating button position: bottom-right (same as ClinicForge)
- Dark mode compatible (mandatory per CLAUDE.md design system)
- Panel opens with context checks adapted for CRM: "Leads sin seguimiento", "Llamadas pendientes", "Pipeline summary"

**Functional changes**:
- WebSocket URL: `ws://{BACKEND_URL}/ws/nova`
- Navigation handler: map tool responses to CRM routes (`/leads`, `/pipeline`, `/agenda`, `/analytics`, `/chats`, `/settings`)
- Context endpoint: `GET /nova/context` returns CRM-specific stats (total leads, hot leads, pipeline value, calls today)
- Remove dental-specific: onboarding score, patient checks, appointment stats

**Audio pipeline** (identical to ClinicForge):
- `MediaRecorder` for microphone capture
- Base64 encoding for WebSocket transport
- `AudioContext` + `AudioWorklet` for playback
- Visual waveform animation while speaking/listening

### 3.7 Backend — WebSocket Handler

Add to `orchestrator_service/main.py` (or a separate `routes/nova_routes.py`):

```python
@app.websocket("/ws/nova")
async def nova_websocket(websocket: WebSocket):
    await websocket.accept()
    tenant_id = extract_tenant_from_ws(websocket)
    user = extract_user_from_ws(websocket)

    # Connect to OpenAI Realtime API
    openai_ws = await connect_openai_realtime(
        model=get_nova_model(tenant_id),  # from system_config table
        tools=NOVA_CRM_TOOLS_SCHEMA,
        system_prompt=build_nova_prompt(tenant_id, user)
    )

    # Bridge: browser <-> backend <-> OpenAI
    async def browser_to_openai():
        async for msg in websocket.iter_text():
            data = json.loads(msg)
            if data["type"] == "audio":
                await openai_ws.send(json.dumps({
                    "type": "input_audio_buffer.append",
                    "audio": data["audio"]
                }))

    async def openai_to_browser():
        async for msg in openai_ws:
            event = json.loads(msg)
            if event["type"] == "response.audio.delta":
                await websocket.send_json({
                    "type": "audio",
                    "audio": event["delta"]
                })
            elif event["type"] == "response.function_call_arguments.done":
                result = await execute_nova_tool(
                    event["name"], json.loads(event["arguments"]),
                    tenant_id, user
                )
                await openai_ws.send(json.dumps({
                    "type": "conversation.item.create",
                    "item": {
                        "type": "function_call_output",
                        "call_id": event["call_id"],
                        "output": result
                    }
                }))
                await openai_ws.send(json.dumps({
                    "type": "response.create"
                }))

    await asyncio.gather(browser_to_openai(), openai_to_browser())
```

### 3.8 Backend — nova_tools_crm.py

Structure follows ClinicForge's `nova_tools.py`:

```python
# orchestrator_service/services/nova_tools_crm.py

NOVA_CRM_TOOLS_SCHEMA: List[Dict[str, Any]] = [
    # 20 tool definitions in flat OpenAI Realtime format
]

async def execute_nova_tool(
    tool_name: str,
    args: Dict[str, Any],
    tenant_id: int,
    user: dict
) -> str:
    """Dispatch tool call to the correct handler. Returns plain string for speech."""
    handlers = {
        "buscar_lead": _buscar_lead,
        "ver_lead": _ver_lead,
        # ... 18 more
    }
    handler = handlers.get(tool_name)
    if not handler:
        return f"Herramienta {tool_name} no encontrada."
    return await handler(tenant_id=tenant_id, user=user, **args)
```

**Date handling**: All tool arguments arrive as strings from OpenAI. Use helper functions to parse:

```python
def _parse_date_str(s: str) -> date:
    """Parse 'YYYY-MM-DD' or 'hoy'/'manana' to date object."""

def _parse_datetime_str(s: str) -> datetime:
    """Parse 'YYYY-MM-DD HH:MM' to datetime object for asyncpg."""
```

**Tenant isolation**: Every query MUST include `WHERE tenant_id = $N` using the `tenant_id` from the authenticated WebSocket session. Never trust tool arguments for tenant scoping.

### 3.9 Nova Model Configuration

Uses the existing `system_config` table (already in CRM Ventas if it exists, otherwise create):

| key | value | description |
|-----|-------|-------------|
| `MODEL_NOVA_VOICE` | `gpt-4o-mini-realtime-preview` | Economic model (default) |

Options: `gpt-4o-mini-realtime-preview` (economic, ~$0.06/min) or `gpt-4o-realtime-preview` (premium, ~$0.24/min). Selectable from the admin settings page.

### 3.10 Acceptance Criteria

**AC-B1**: The NovaWidget renders as a floating violet button on every authenticated page. Clicking it opens a voice panel. Granting microphone access establishes a WebSocket connection to `/ws/nova`. Speaking a command like "busca el lead Juan Perez" triggers the `buscar_lead` tool and Nova speaks back the results within 3 seconds of tool completion.

**AC-B2**: All 20 tools execute correctly with tenant isolation. Specifically: `buscar_lead` returns up to 5 results; `ver_pipeline` returns stage counts and total value; `cambiar_estado` validates transitions via the `lead_status_transitions` table before updating; `ir_a_pagina("leads")` causes the frontend to navigate to `/leads`; `agendar_llamada` creates a row in `seller_agenda_events`.

**AC-B3**: The Nova model can be switched between `gpt-4o-mini-realtime-preview` and `gpt-4o-realtime-preview` from the admin settings page. The change takes effect on the next WebSocket connection without requiring a server restart.

### 3.11 Files to Create/Modify

| Action | File | Description |
|--------|------|-------------|
| **CREATE** | `frontend_react/src/components/NovaWidget.tsx` | Voice widget UI, WebSocket client, audio pipeline |
| **CREATE** | `orchestrator_service/services/nova_tools_crm.py` | 20 tool schemas + handler implementations |
| **CREATE** | `orchestrator_service/routes/nova_routes.py` | REST endpoints: `GET /nova/context`, `GET /nova/health` |
| **MODIFY** | `orchestrator_service/main.py` | Add WebSocket handler `/ws/nova`, import nova_tools_crm |
| **MODIFY** | `frontend_react/src/App.tsx` | Import and render `<NovaWidget />` inside authenticated layout |
| **MODIFY** | `orchestrator_service/requirements.txt` | Add `websockets>=12.0` |

### 3.12 Dependencies

| Dependency | Purpose | Required |
|------------|---------|----------|
| `OPENAI_API_KEY` | OpenAI Realtime API access (must support realtime models) | Yes |
| `websockets>=12.0` | Python WebSocket client for OpenAI Realtime connection | Yes |
| Browser `MediaRecorder` API | Audio capture (Chrome 49+, Firefox 25+, Safari 14.1+) | Yes |
| Browser `AudioContext` API | Audio playback | Yes |

---

## 4. Implementation Phases

### Phase 1: Database Foundation (3-4 days)

1. Create `orchestrator_service/models.py` with all 34 model classes
2. Update `alembic/env.py` to use `Base.metadata`
3. Create migration `002_scoring_indexes`
4. Verify: `alembic check` reports no diff
5. Test: run migration on fresh DB and existing DB

### Phase 2: Nova Backend (4-5 days)

1. Create `orchestrator_service/services/nova_tools_crm.py` with 20 tool schemas
2. Implement all 20 tool handler functions with asyncpg queries
3. Add WebSocket handler to `main.py`
4. Create `routes/nova_routes.py` (context + health endpoints)
5. Test: each tool returns correct data with tenant isolation

### Phase 3: Nova Frontend (3-4 days)

1. Port `NovaWidget.tsx` from ClinicForge with CRM adaptations
2. Implement audio pipeline (MediaRecorder + AudioContext)
3. Wire navigation handler to CRM routes
4. Add context panel with CRM-specific checks
5. Mount in `App.tsx` inside authenticated layout

### Phase 4: Integration & Polish (2-3 days)

1. End-to-end voice test: speak command -> tool execution -> spoken response
2. Model switching from admin settings
3. Error handling: WebSocket reconnection, OpenAI timeout, microphone denied
4. Performance: audio latency optimization, tool execution timing

**Total estimated effort: 12-16 days**

---

## 5. Risks & Mitigations

### R1: ORM Model Drift from Production Schema

**Risk**: The models.py classes may not perfectly match the actual production schema, especially for tables created by the migration files outside db.py (patch_016, patch_018) that may or may not have been applied.

**Mitigation**: Before deploying, run `alembic check` against a production database dump. If drift is detected, create a reconciliation migration. Document which migration files have been applied by checking the database directly (`SELECT * FROM alembic_version`).

### R2: db.py Patches Conflict with Alembic

**Risk**: The 16 patches in `db.py._run_evolution_pipeline()` run on every startup. After Alembic takes over, these patches might conflict with Alembic-managed state or attempt to re-apply changes that Alembic already tracks.

**Mitigation**: In Phase 1, add a guard to `_run_evolution_pipeline` that checks if the `alembic_version` table exists and has revision >= `002`. If so, skip the legacy patches entirely. This provides a clean cutover point.

### R3: OpenAI Realtime API Cost

**Risk**: The Realtime API is significantly more expensive than Chat Completions ($0.06-$0.24/minute). A team of 10 sellers using Nova throughout the day could generate substantial costs.

**Mitigation**: Default to `gpt-4o-mini-realtime-preview` (economic model). Implement a session timeout (5 minutes of inactivity auto-disconnects). Add token/minute tracking in the `system_config` or a dedicated `nova_sessions` table. Show daily cost estimate in the admin dashboard.

### R4: WebSocket Stability

**Risk**: The double-WebSocket bridge (browser -> backend -> OpenAI) creates two failure points. Either connection dropping causes the session to hang.

**Mitigation**: Implement heartbeat pings on both connections (every 30s). If either WebSocket closes, gracefully close the other and notify the user. Add automatic reconnection in the frontend (max 3 retries with exponential backoff). Log all WebSocket events for debugging.

### R5: Browser Audio Compatibility

**Risk**: `MediaRecorder` and `AudioContext` APIs have varying support across browsers. Safari in particular has historically been problematic with audio worklets.

**Mitigation**: Feature-detect on widget mount. If APIs are unavailable, show the Nova button in a disabled state with a tooltip: "Tu navegador no soporta audio. Usa Chrome o Firefox." Test on Chrome, Firefox, Edge, and Safari before release.

### R6: Tenant Isolation in Nova Tools

**Risk**: A bug in any of the 20 tool handlers could leak data across tenants if `tenant_id` is accidentally omitted from a query.

**Mitigation**: Every tool handler receives `tenant_id` as a mandatory parameter injected from the WebSocket session, never from the tool arguments. Add a pre-execution wrapper that logs `(tool_name, tenant_id, user_id)` for every call. Include `WHERE tenant_id = $N` in every SQL query. Code review checklist item: verify tenant_id in all queries before merge.
