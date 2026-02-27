# 🦷 CRM Ventas – Nexus Core CRM

**Sovereign Multi-Tenant CRM Platform with AI-Driven Sales Automation.** Transform your sales pipeline with intelligent lead management, WhatsApp-first communication, and real-time analytics.

`Python` `React` `TypeScript` `FastAPI` `LangChain`

---

## 📋 Table of Contents

- [Vision & Value Proposition](#-vision--value-proposition)
- [Technology Stack & Architecture](#-technology-stack--architecture)
- [AI Models & Capabilities](#-ai-models--capabilities)
- [Key Features](#-key-features)
- [Project Structure](#-project-structure)
- [Module Architecture (Nexus Core)](#-module-architecture-nexus-core)
- [Deployment Guide (Quick Start)](#-deployment-guide-quick-start)
- [Documentation Hub](#-documentation-hub)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🌟 Vision & Value Proposition

**CRM Ventas** is a sovereign, multi-tenant CRM platform for sales organizations. Single product focus: leads, pipeline, vendedores, agenda, and WhatsApp-powered conversations. Enterprise-grade architecture with strict tenant isolation.

### 🎯 For Whom

| Audience | Value |
|----------|--------|
| **Sales teams** | Centralize leads, deals, WhatsApp conversations, and revenue analytics in one tool; no more spreadsheets and missed opportunities. |
| **Agencies & franchises** | Each location (tenant) has its own data, pipeline, and calendar; the CEO sees all locations, team approvals, and analytics from one panel. |
| **Multilingual teams** | UI in **Spanish**, **English**, and **French**. Language is set in Configuration and applies to the entire platform. The WhatsApp assistant detects the lead's language and replies in the same language. |

### 🛡️ Sovereign Data (Tenant-First)

Your data, your company, your keys. Every query is filtered by `tenant_id`. Identity is resolved from JWT and database (never from client-supplied tenant). Admin routes require **JWT + X-Admin-Token** so that a stolen token alone cannot access the API.

### 📱 True Omnichannel (WhatsApp-First)

The AI lives where your prospects are:

- **WhatsApp** (YCloud integration): Lead qualification, appointment scheduling, deal closing, and human handoff.
- **Operations Center** (React SPA): Dashboard, pipeline, leads, chats, analytics, staff approval, and configuration—all in one place, with real-time updates via Socket.IO.

### 🚀 Sprint 2 - Tracking Avanzado (Completed Feb 27, 2026)

#### **🎯 Key Achievements:**
1. **Real-time CEO Control System** - Complete oversight of sales team with advanced metrics
2. **Intelligent Notification System** - 4 types of smart notifications with Socket.IO
3. **Background Jobs Automation** - Scheduled tasks with auto-start and health monitoring
4. **Enhanced CEO Dashboard** - Advanced analytics, leaderboards, and real-time updates
5. **Seller Performance Tracking** - Comprehensive metrics for individual and team performance

#### **🛠️ New Technologies Added:**
- **Redis**: Real-time metrics caching and performance optimization
- **Socket.IO**: WebSocket-based real-time communication for notifications
- **APScheduler**: Background jobs and scheduled tasks with auto-start
- **Health Checks**: Comprehensive system monitoring and alerting
- **Real-time Analytics**: Instant updates for CEO decision-making

#### **📈 Business Value Delivered:**
- **CEO**: Complete control with real-time metrics, alerts, and automated reporting
- **Sellers**: Intelligent notifications, performance tracking, and automated follow-ups
- **Business**: Automated processes, measurable ROI, and data-driven decisions

---

## 🛠️ Technology Stack & Architecture

Nexus Core CRM uses a **Sovereign Microservices Architecture**, designed to scale while keeping strict isolation per tenant.

### 🎨 Frontend (Operations Center)

| Layer | Technology |
|-------|------------|
| **Framework** | React 18 + TypeScript |
| **Build** | Vite (fast HMR & build) |
| **Styling** | Tailwind CSS |
| **Icons** | Lucide React |
| **Routing** | React Router DOM v6 (`path="/*"` for nested routes) |
| **State** | Context API (Auth, Language) + Axios (API with JWT + X-Admin-Token) |
| **i18n** | LanguageProvider + `useTranslation()` + `es.json` / `en.json` / `fr.json` |
| **Deployment** | Docker + Nginx (SPA mode) |

### ⚙️ Backend (The Core)

| Component | Technology |
|-----------|-------------|
| **Orchestrator** | FastAPI (Python 3.11+) – central brain, LangChain agent, Socket.IO server |
| **Add-ons** | Pydantic, Uvicorn (ASGI) |
| **Microservices** | `orchestrator_service`: main API, agent, calendar, tenants, auth; `whatsapp_service`: YCloud relay, Whisper transcription |

### 🗄️ Infrastructure & Persistence

| Layer | Technology |
|-------|------------|
| **Database** | PostgreSQL (leads, deals, appointments, tenants, users, notifications, seller metrics) |
| **Cache / Real-time** | Redis (metrics caching, notification queuing, real-time updates) |
| **Background Jobs** | APScheduler (scheduled tasks, automated notifications, metrics refresh) |
| **Real-time Communication** | Socket.IO (WebSocket-based notifications, live updates) |
| **Containers** | Docker & Docker Compose |
| **Deployment** | EasyPanel, Render, AWS ECS compatible |

### 🤖 Artificial Intelligence Layer

| Layer | Technology |
|-------|------------|
| **Orchestration** | LangChain + custom tools |
| **Primary model** | OpenAI **gpt-4o-mini** (default for agent and lead scoring) |
| **Audio** | Whisper (voice message transcription) |
| **Tools** | `check_availability`, `book_appointment`, `list_services`, `list_professionals`, `list_my_appointments`, `cancel_appointment`, `reschedule_appointment`, `triage_urgency`, `derivhumano` |
| **Hybrid calendar** | Per-tenant: local (BD) or Google Calendar; JIT sync and collision checks |

### 🔐 Security & Authentication

| Mechanism | Description |
|-----------|-------------|
| **Auth** | JWT (login) + **X-Admin-Token** header for all `/admin/*` routes |
| **Multi-tenancy** | Strict `tenant_id` filter on every query; tenant resolved from JWT/DB, not from request params |
| **Credentials** | Google Calendar tokens stored encrypted (Fernet) when using connect-sovereign |
| **Passwords** | Bcrypt hashing; no plaintext in repo or UI |
| **Real-time Security** | Socket.IO authentication with JWT validation |
| **Background Jobs Security** | Environment variable controlled task execution |

### ⚡ Real-time & Background Processing

| Technology | Purpose |
|------------|---------|
| **Redis** | Real-time metrics cache, notification queuing, performance optimization |
| **Socket.IO** | WebSocket-based real-time notifications and live updates |
| **APScheduler** | Background jobs and scheduled tasks with auto-start |
| **Health Checks** | Comprehensive system monitoring and alerting endpoints |
| **Notification System** | Intelligent notifications with 4 types and user preferences |

### 🆕 New Services (Sprint 2)

| Service | Description |
|---------|-------------|
| **SellerNotificationService** | Intelligent notification system (unanswered conversations, hot leads, follow-ups, performance alerts) |
| **ScheduledTasksService** | Background jobs with auto-start, configurable intervals, health monitoring |
| **SocketNotificationService** | Real-time WebSocket communication for instant updates |
| **HealthCheckService** | Comprehensive system monitoring with readiness/liveness probes |
| **SellerMetricsService** | Real-time performance tracking with Redis caching |

---

## 🧠 AI Models & Capabilities

| Model | Provider | Use case |
|-------|----------|----------|
| **gpt-4o-mini** | OpenAI | Default: agent conversation, lead scoring, availability, booking |
| **Whisper** | OpenAI | Voice message transcription |

### Agent capabilities

- **Conversation:** Greeting, company identity, service selection, availability check, slot offering, booking with lead data (name, phone, source).
- **Lead Scoring:** Urgency/interest classification from symptoms or requirements.
- **Human handoff:** `derivhumano` + 24h silence window per tenant/phone.
- **Multilingual:** Detects message language (es/en/fr) and responds in the same language; company name injected from `tenants.company_name`.

---

## 🚀 Key Features

### 🎯 AI Sales Agent & Pipeline Orchestration

- **Single AI brain** per tenant: qualifies leads, lists services and agents, checks real availability (local or Google Calendar), books appointments/deals.
- **Canonical tool format** and retry on booking errors ("never give up a reservation").
- **Tools:** `check_availability`, `book_appointment`, `list_services`, `list_professionals`, `list_my_appointments`, `cancel_appointment`, `reschedule_appointment`, `triage_urgency`, `derivhumano`.

### 📅 Smart Calendar (Hybrid by Tenant)

- **Per-tenant:** Local (DB only) or **Google Calendar**; `tenants.config.calendar_provider` + `google_calendar_id` per user.
- **JIT sync:** External blocks mirrored to `google_calendar_blocks`; collision checks before create/update.
- **Real-time UI:** Socket.IO events (`NEW_APPOINTMENT`, `APPOINTMENT_UPDATED`, `APPOINTMENT_DELETED`).

### 👥 Leads & Pipeline Management

- List, search, create, edit leads with full pipeline tracking.
- Stages: new → contacted → interested → negotiation → closed_won → closed_lost.
- Source tracking (meta_ads, website, referral) and lead attribution.

### 💬 Conversations (Chats)

- **Per tenant:** Sessions and messages filtered by `tenant_id`; CEO can switch tenant.
- **Context:** Last/upcoming appointment, deal stage, human override and 24h window.
- **Actions:** Human intervention, remove silence, send message; click on derivation notification opens the right conversation.

### 📊 Advanced Analytics & CEO Control (Sprint 2)

#### **Real-time CEO Dashboard:**
- **Comprehensive Metrics**: 15+ metrics per seller including response time, conversion rate, lead quality
- **Leaderboard System**: Real-time ranking of sellers by performance
- **Team Overview**: Aggregate metrics for entire sales team
- **Date Range Filters**: Customizable time periods for analysis
- **Export Capabilities**: CSV export for external reporting

#### **Intelligent Notifications:**
- **4 Notification Types**: Unanswered conversations, hot leads, follow-up reminders, performance alerts
- **Real-time Updates**: Socket.IO powered instant notifications
- **User Preferences**: Configurable notification settings per user
- **Notification Center**: Centralized interface for managing all notifications

#### **Background Automation:**
- **Scheduled Tasks**: Automated notification checks (5 min), metrics refresh (15 min), data cleanup (hourly)
- **Auto-start**: Tasks start automatically with backend, configurable via environment variables
- **Health Monitoring**: Comprehensive health checks and status endpoints
- **Daily Reports**: Automated CEO reports at 8:00 AM daily

### 👔 Staff & Approvals (CEO)

- Registration with **tenant** (GET `/auth/clinics`), role, phone; POST `/auth/register` creates pending user.
- **Active Staff** as single source of truth: detail modal, "Link to tenant", gear → Edit profile.
- Scroll-isolated Staff view (Aprobaciones) for long lists on desktop and mobile.

### 🏢 Multi-Tenant Architecture

- **Isolation:** Leads, appointments, chats, users, and configuration are separated by `tenant_id`. One company never sees another's data.
- **CEO:** Can switch tenant in Chats and other views; manages approvals, tenants, and configuration.
- **Staff:** Access only to their assigned tenant(s).

### 🌐 Internationalization (i18n)

- **UI:** Spanish, English, French. Set in **Configuration** (CEO); stored in `tenants.config.ui_language`; applies to login, menus, calendar, analytics, chats, and all main views.
- **WhatsApp agent:** Responds in the **language of the lead's message** (auto-detect es/en/fr); independent of UI language.

---

## 📁 Project Structure

```
CRM Ventas/
├── 📂 .agent/                    # Agent configuration & skills
│   ├── workflows/                # Autonomy, specify, plan, audit, update-docs, etc.
│   └── skills/                   # Backend, Frontend, DB, Prompt, Doc_Keeper, etc.
├── 📂 frontend_react/            # React 18 + Vite SPA (Operations Center)
│   ├── src/
│   │   ├── components/           # Layout, Sidebar, AppointmentForm, Modal, etc.
│   │   │   ├── SellerBadge.tsx           # Seller badge with assignment (Sprint 2)
│   │   │   ├── SellerSelector.tsx        # Seller assignment modal (Sprint 2)
│   │   │   ├── AssignmentHistory.tsx     # Assignment history timeline (Sprint 2)
│   │   │   ├── SellerMetricsDashboard.tsx # CEO dashboard with metrics (Sprint 2)
│   │   │   ├── NotificationBell.tsx      # Real-time notification bell (Sprint 2)
│   │   │   └── NotificationCenter.tsx    # Notification management center (Sprint 2)
│   │   ├── views/               # Dashboard, Pipeline, Leads, Chats, Landing, etc.
│   │   │   ├── MetaLeadsView.tsx         # Meta Ads leads view (Sprint 2)
│   │   │   └── ChatsView.tsx             # Updated with seller assignment (Sprint 2)
│   │   ├── context/              # AuthContext, LanguageContext, SocketContext
│   │   │   └── SocketContext.tsx         # Socket.IO real-time context (Sprint 2)
│   │   ├── locales/             # es.json, en.json, fr.json (updated with Sprint 2 terms)
│   │   └── modules/              # Pluggable modules (crm_sales only – single-niche CRM)
│   ├── package.json
│   └── vite.config.ts
├── 📂 orchestrator_service/      # FastAPI Core (Orchestrator)
│   ├── main.py                   # App, /chat, /health, Socket.IO, LangChain agent & tools, auto-start tasks
│   ├── admin_routes.py           # /admin/* (leads, appointments, users, chat, tenants, etc.)
│   ├── auth_routes.py            # /auth/* (tenants, register, login, me, profile)
│   ├── db.py                     # Pool + Maintenance Robot (idempotent patches)
│   ├── gcal_service.py           # Google Calendar (hybrid calendar)
│   ├── analytics_service.py      # Agent metrics
│   ├── services/                 # Business services (Sprint 2)
│   │   ├── seller_metrics_service.py      # Real-time seller metrics with Redis cache
│   │   ├── seller_notification_service.py  # Intelligent notification system (4 types)
│   │   ├── scheduled_tasks.py              # Background jobs with auto-start
│   │   └── seller_assignment_service.py    # Seller assignment logic
│   ├── routes/                   # API routes (Sprint 2)
│   │   ├── seller_routes.py               # Seller metrics and assignment endpoints
│   │   ├── notification_routes.py         # Notification management endpoints
│   │   ├── scheduled_tasks_routes.py      # Background jobs management
│   │   └── health_routes.py               # Health checks and monitoring
│   ├── core/                     # Agnostic core (auth, chat, security, real-time)
│   │   ├── socket_manager.py              # Socket.IO server setup
│   │   └── socket_notifications.py        # Real-time notification handlers
│   ├── modules/                  # Pluggable business modules
│   │   └── crm_sales/            # Sales CRM module (leads, clients, sellers, agenda, routes under /admin/core/crm)
│   └── requirements.txt
├── 📂 whatsapp_service/          # YCloud relay & Whisper
│   ├── main.py
│   └── ycloud_client.py
├── 📂 docs/                      # Documentation
│   ├── 01_architecture.md
│   ├── 02_environment_variables.md
│   ├── 03_deployment_guide.md
│   ├── 04_agent_logic_and_persona.md
│   ├── API_REFERENCE.md
│   ├── transformacion/           # Transformation to Nexus Core
│   │   ├── 02_nucleo_agnostico_propuesta.md
│   │   ├── 08_modelo_crm_ventas.md
│   │   └── ...
│   └── ...
├── 📂 db/init/                   # Schema migrations
├── docker-compose.yml            # Local stack
└── README.md                     # This file
```

---

## 🏗️ Module Architecture (Nexus Core)

Nexus Core CRM follows a **pluggable module architecture** that separates the agnostic core from business-specific logic.

### Core (Agnostic)

The core manages base infrastructure, security, and communication—totally independent of the vertical business.

- **Auth & Security**: JWT, X-Admin-Token, password hashing
- **Tenant Management**: Multi-tenant isolation, configuration per tenant
- **Users & Roles**: Base user management (agents, secretaries, CEOs)
- **Chat Engine**: WhatsApp/YCloud connection, message storage, Socket.IO events
- **Calendar Base**: Hybrid calendar infrastructure (local/Google)

### Modules (Pluggable)

Business logic is encapsulated in modules that can be activated per tenant:

| Module | Description |
|--------|-------------|
| **dental** | Dental clinic module: patients, clinical records, treatments, dental appointments |
| **crm_sales** | Sales CRM module: leads, deals, pipeline, campaigns, Meta ads integration |

### Data Model: CRM Ventas

```sql
-- Leads (replaces patients)
CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    phone_number TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    status TEXT DEFAULT 'new', -- new, contacted, interested, negotiation, closed_won, closed_lost
    assigned_seller_id INTEGER REFERENCES users(id),
    source TEXT,
    tags JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_leads_tenant_phone ON leads(tenant_id, phone_number);
```

---

## 🚀 Deployment Guide (Quick Start)

Nexus Core CRM follows a **clone and run** approach. With Docker you don't need to install Python or Node locally.

### Prerequisites

- **Docker Desktop** (Windows/Mac) or **Docker Engine** (Linux)
- **Git**
- **OpenAI API Key** (required for the agent)
- **PostgreSQL** and **Redis** (or use `docker-compose`)

### Standard deployment (recommended)

**1. Clone the repository**

```bash
git clone https://github.com/adriangmrraa/crmventas.git
cd crmventas
```

**2. Environment configuration**

```bash
cp .env.example .env
# Edit .env (see docs/02_environment_variables.md):
# - OPENAI_API_KEY
# - YCLOUD_API_KEY / YCLOUD_WEBHOOK_SECRET (WhatsApp)
# - POSTGRES_DSN / REDIS_URL
# - COMPANY_NAME, BOT_PHONE_NUMBER
# - GOOGLE_CREDENTIALS or connect-sovereign (optional)
# - ADMIN_TOKEN (for X-Admin-Token), JWT_SECRET_KEY

# Sprint 2 - Advanced Tracking Configuration:
# - ENABLE_SCHEDULED_TASKS=true                    # Enable background jobs
# - NOTIFICATION_CHECK_INTERVAL_MINUTES=5          # Notification check interval
# - METRICS_REFRESH_INTERVAL_MINUTES=15            # Metrics refresh interval
# - CLEANUP_INTERVAL_HOURS=1                       # Data cleanup interval
# - REDIS_HOST=localhost                           # Redis for real-time metrics
# - REDIS_PORT=6379                                # Redis port
# - REDIS_PASSWORD=                                # Redis password (if any)
```

**3. Start services**

```bash
docker-compose up -d --build
```

**4. Access**

| Service | URL | Purpose |
|---------|-----|---------|
| **Orchestrator** | `http://localhost:8000` | Core API & agent |
| **Swagger UI** | `http://localhost:8000/docs` | OpenAPI contract; test with JWT + X-Admin-Token |
| **ReDoc / OpenAPI** | `http://localhost:8000/redoc`, `/openapi.json` | Read-only docs and JSON schema |
| **WhatsApp Service** | `http://localhost:8002` | YCloud relay & Whisper |
| **Operations Center** | `http://localhost:5173` | React UI (ES/EN/FR) |

---

## 📚 Documentation Hub

| Document | Description |
|----------|-------------|
| [**00. Documentation index**](docs/00_INDICE_DOCUMENTACION.md) | Master index of all docs in `docs/` with short descriptions. |
| [**01. Architecture**](docs/01_architecture.md) | Microservices, Orchestrator, WhatsApp Service, hybrid calendar, Socket.IO, background jobs. |
| [**02. Environment variables**](docs/02_environment_variables.md) | OPENAI, YCloud, PostgreSQL, Redis, Google, CREDENTIALS_FERNET_KEY, scheduled tasks. |
| [**03. Deployment guide**](docs/03_deployment_guide.md) | EasyPanel, production configuration, background jobs setup. |
| [**04. Agent logic & persona**](docs/04_agent_logic_and_persona.md) | Assistant persona, tools, conversation flow. |
| [**API Reference**](docs/API_REFERENCE.md) | All admin and auth endpoints; Swagger at `/docs`, ReDoc at `/redoc`. |
| [**08. Background Jobs Guide**](docs/08_background_jobs_guide.md) | Complete guide to scheduled tasks, configuration, monitoring. |
| [**09. Real-time Notifications Guide**](docs/09_real_time_notifications.md) | Socket.IO setup, notification system, real-time updates. |
| [**10. CEO Dashboard Guide**](docs/10_ceo_dashboard_guide.md) | Advanced analytics, seller metrics, leaderboards, reporting. |
| [**Transformation Docs**](docs/transformacion/) | Nexus Core transformation documentation. |
| [**SPECS index**](docs/SPECS_IMPLEMENTADOS_INDICE.md) | Consolidated specs and where each feature is documented. |
| [**Context for AI agents**](docs/CONTEXTO_AGENTE_IA.md) | Entry point for another IA: stack, rules, API, DB, i18n. |
| [**Prompt for IA**](docs/PROMPT_CONTEXTO_IA_COMPLETO.md) | Copy-paste block for full project context in a new chat. |
| [**Verificación CRM vs Clínicas**](docs/VERIFICACION_SALUD_CRM_VS_CLINICAS.md) | Paridad funcional, endpoints admin core, checklist. |
| [**Plan paridad**](docs/plans/plan-paridad-crm-vs-clinicas.md) | Plan de implementación por fases (DB, chat, stats, contexto lead, ChatsView). |
| [**Sprint 2 Documentation**](docs/sprint2/) | Complete documentation for Sprint 2 - Tracking Avanzado features. |

---

## 🚀 Sprint 2 - Tracking Avanzado (Completed Feb 27, 2026)

### **🎯 Complete Feature Set:**

#### **1. Real-time CEO Control System:**
- **Seller Assignment**: Manual and automatic assignment of conversations to sellers
- **Seller Metrics**: 15+ real-time metrics per seller with Redis caching
- **CEO Dashboard**: Advanced analytics, leaderboards, and team overview
- **Performance Tracking**: Individual and team performance monitoring

#### **2. Intelligent Notification System:**
- **4 Notification Types**: Unanswered conversations, hot leads, follow-up reminders, performance alerts
- **Real-time Delivery**: Socket.IO powered instant notifications
- **User Preferences**: Configurable notification settings
- **Notification Center**: Centralized management interface

#### **3. Background Jobs Automation:**
- **Scheduled Tasks**: Automated system with configurable intervals
- **Auto-start**: Tasks start automatically with backend startup
- **Health Monitoring**: Comprehensive health checks and status endpoints
- **Daily Reports**: Automated CEO reports at 8:00 AM daily

#### **4. Technical Implementation:**
- **Redis Integration**: Real-time metrics caching and performance optimization
- **Socket.IO**: WebSocket-based real-time communication
- **APScheduler**: Robust background job scheduling
- **Health Checks**: Readiness and liveness probes for production monitoring

### **📊 Business Impact:**
- **CEO**: Complete control with real-time insights and automated reporting
- **Sellers**: Intelligent notifications and performance feedback
- **Business**: Automated processes, measurable ROI, data-driven decisions
- **Scalability**: Enterprise-ready architecture for growth

### **🔧 Deployment Notes:**
- New environment variables for scheduled tasks configuration
- Redis required for optimal performance
- Socket.IO enabled for real-time notifications
- Comprehensive health check endpoints available

---

## 🤝 Contributing

Development follows the project's SDD workflows (specify → plan → implement) and **AGENTS.md** (sovereignty rules, scroll isolation, auth). For documentation changes, use the **Non-Destructive Fusion** protocol (see [update-docs](.agent/workflows/update-docs.md)). Do not run SQL directly; propose commands for the maintainer to run.

---

## 📜 License

Nexus Core CRM – CRM Ventas © 2026.
