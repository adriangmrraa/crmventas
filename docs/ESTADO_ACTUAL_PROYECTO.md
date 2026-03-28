# Estado Actual del Proyecto - CRM Ventas (Nexus Core)

**Fecha:** 2026-03-28
**Versión:** Nexus v9.0 — Dark Theme Premium
**Despliegue:** VPS en EasyPanel
**Repositorio:** github.com/adriangmrraa/crmventas

---

## 1. Visión General

CRM Ventas es una plataforma **multi-tenant SaaS** de gestión de ventas con asistente IA por WhatsApp. Permite gestionar leads, pipeline de ventas, vendedores, agenda, chats en tiempo real y marketing (Meta Ads + Google Ads).

**Stack tecnológico:**

| Capa | Tecnología | Puerto |
|------|-----------|--------|
| Backend (Orchestrator) | FastAPI + LangChain + OpenAI gpt-4o-mini | 8000 |
| WhatsApp Service | FastAPI + YCloud + Whisper | 8002 |
| BFF Service | Node.js/Express + TypeScript | 3000 |
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS | 5173/4173 |
| Base de datos | PostgreSQL 13 | 5432 |
| Cache/Real-time | Redis (Alpine) | 6379 |
| Real-time | Socket.IO (integrado en Orchestrator) | - |
| Background Jobs | APScheduler (integrado en Orchestrator) | - |

---

## 2. Arquitectura de Microservicios

```
[Usuario WhatsApp] → [YCloud API] → [WhatsApp Service :8002]
                                          ├─ Validación HMAC
                                          ├─ Deduplicación (Redis)
                                          ├─ Transcripción (Whisper)
                                          └─ POST /chat → [Orchestrator :8000]
                                                              ├─ LangChain Agent
                                                              ├─ Tools CRM
                                                              ├─ PostgreSQL
                                                              ├─ Redis (cache)
                                                              └─ Socket.IO → [Frontend React :5173]
                                                                                ├─ Dashboard CEO
                                                                                ├─ Leads / Pipeline
                                                                                ├─ Chats / Notificaciones
                                                                                └─ Marketing Hub
```

### Estructura de directorios principal

```
CRM VENTAS/
├── orchestrator_service/          # Backend principal (FastAPI)
│   ├── main.py                    # App, /chat endpoint, LangChain agent
│   ├── admin_routes.py            # Rutas /admin/core/*
│   ├── auth_routes.py             # /auth/* (login, register, me, logout)
│   ├── db.py                      # Pool PostgreSQL + Maintenance Robot (migrations)
│   ├── gcal_service.py            # Google Calendar integration
│   ├── analytics_service.py       # Métricas y analytics
│   ├── core/
│   │   ├── security.py            # verify_admin_token, RBAC, audit
│   │   ├── credentials.py         # Fernet encryption vault
│   │   ├── socket_manager.py      # Socket.IO server config
│   │   ├── socket_notifications.py # Notification events
│   │   ├── rate_limiter.py        # slowapi rate limiting
│   │   └── security_middleware.py # CSP, HSTS, X-Frame headers
│   ├── modules/crm_sales/
│   │   ├── routes.py              # /admin/core/crm/* (leads, clients, sellers, agenda)
│   │   ├── models.py              # Pydantic models
│   │   ├── status_models.py       # Lead status workflow models
│   │   └── tools_provider.py      # LangChain tools for CRM
│   ├── routes/
│   │   ├── seller_routes.py       # /admin/core/sellers/*
│   │   ├── lead_status_routes.py  # Lead status transitions
│   │   ├── notification_routes.py # /admin/core/notifications/*
│   │   ├── metrics_routes.py      # /admin/core/metrics/*
│   │   ├── health_routes.py       # /health/*
│   │   ├── scheduled_tasks_routes.py
│   │   ├── marketing.py           # /crm/marketing/*
│   │   ├── meta_auth.py           # /crm/auth/meta/*
│   │   ├── meta_webhooks.py       # /webhooks/meta
│   │   ├── google_auth.py         # /crm/auth/google/*
│   │   └── google_ads_routes.py   # /crm/marketing/google/*
│   ├── services/
│   │   ├── seller_notification_service.py
│   │   ├── seller_assignment_service.py
│   │   ├── seller_metrics_service.py
│   │   ├── lead_status_service.py
│   │   ├── lead_history_service.py
│   │   ├── lead_automation_service.py
│   │   └── marketing/ (meta_ads, google_ads, automation)
│   └── migrations/                # SQL patches externos (008-018)
├── whatsapp_service/              # Servicio WhatsApp (FastAPI)
│   ├── main.py                    # Webhooks YCloud, envío de mensajes
│   └── ycloud_client.py           # Cliente API YCloud
├── bff_service/                   # Backend for Frontend (Express)
│   └── src/index.ts
├── frontend_react/                # SPA React
│   └── src/
│       ├── App.tsx                # Rutas y providers
│       ├── api/axios.ts           # Cliente HTTP configurado
│       ├── api/marketing.ts       # API calls Meta Ads
│       ├── api/google_ads.ts      # API calls Google Ads
│       ├── api/leadStatus.ts      # API calls estados de leads
│       ├── context/
│       │   ├── AuthContext.tsx     # JWT + sesión
│       │   ├── SocketContext.tsx   # Socket.IO + notificaciones
│       │   └── LanguageContext.tsx # i18n (es/en/fr)
│       ├── views/                 # Vistas principales
│       ├── modules/crm_sales/     # Módulo CRM (leads, clients, agenda, etc.)
│       ├── components/            # Componentes compartidos
│       └── locales/ (es.json, en.json, fr.json)
├── db/init/dentalogic_schema.sql  # Schema base PostgreSQL
├── docker-compose.yml             # Orquestación Docker
└── docs/                          # Documentación actualizada
```

---

## 3. Autenticación y Seguridad

### 3.1 Capas de autenticación

```
Capa 1 (Infraestructura): X-Admin-Token header
  └─ Token estático desde env ADMIN_TOKEN
  └─ Requerido en TODAS las rutas admin

Capa 2 (Identidad): JWT Bearer + HttpOnly Cookie
  └─ Algoritmo: HS256
  └─ Expiración: 7 días
  └─ Secret: JWT_SECRET_KEY (64+ caracteres)
  └─ Payload: { user_id, email, role, tenant_id, exp }

Capa 3 (Multi-tenancy): tenant_id enforcement
  └─ Resuelto desde BD (sellers → professionals → default)
  └─ CEO: acceso a todos los tenants
  └─ Otros roles: solo su tenant asignado
  └─ TODAS las queries filtran por tenant_id
```

### 3.2 Roles y permisos (RBAC)

| Rol | Acceso |
|-----|--------|
| `ceo` | Acceso total. Gestión de tenants, usuarios, vendedores, config, métricas de equipo |
| `setter` | Leads asignados, chats, prospecting, agenda propia |
| `closer` | Leads asignados, chats, agenda propia, pipeline |
| `secretary` | Usuarios pendientes, chats, agenda |
| `professional` | Legacy (dental). Agenda y chats |

### 3.3 Flujo de login

1. `POST /auth/login` (rate limit: 5/min)
2. Verificación bcrypt del password
3. Verificación `status = 'active'` (usuarios `pending` no pueden entrar)
4. Generación JWT + Set-Cookie HttpOnly
5. Frontend almacena token en localStorage + recibe cookie

### 3.4 Flujo de registro

1. `POST /auth/register` (rate limit: 3/min)
2. Usuario creado con `status = 'pending'`
3. Si rol es CRM (setter/closer), se crea fila en `sellers` con `is_active = FALSE`
4. CEO aprueba → `status = 'active'`
5. **Protocolo Omega**: primer CEO registrado se auto-activa

### 3.5 Security headers (middleware)

- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Strict-Transport-Security: max-age=15768000; includeSubDomains`
- `Content-Security-Policy` con whitelist de dominios trusted
- CORS configurado con `allow_credentials: true`

### 3.6 Rate limiting

| Endpoint | Límite |
|----------|--------|
| `/auth/login` | 5/min |
| `/auth/register` | 3/min |

### 3.7 Vault de credenciales

- Tabla `credentials` con encriptación Fernet (AES-256)
- Aislamiento por `tenant_id`
- Almacena: YCLOUD_API_KEY, META tokens, GOOGLE tokens, WEBHOOK secrets
- Ruta interna: `GET /admin/core/internal/credentials/{name}` (X-Internal-Token)

---

## 4. Base de Datos

### 4.1 Sistema de migraciones (Maintenance Robot)

El archivo `orchestrator_service/db.py` implementa un sistema de migraciones idempotentes:

1. Al iniciar, crea el pool asyncpg
2. Verifica existencia de tablas core (`tenants`, `users`, `leads`)
3. Si no existen, ejecuta `dentalogic_schema.sql` (foundation)
4. Aplica patches 1-14 secuencialmente con bloques `DO $$` idempotentes
5. Aplica patches externos 008-018 desde `migrations/`

**Regla de oro**: Todo cambio de esquema debe ser un patch idempotente (`IF NOT EXISTS`, `DO $$`).

### 4.2 Tablas principales

#### Core CRM

| Tabla | Descripción | Columnas clave |
|-------|------------|----------------|
| `tenants` | Sedes/empresas | id, clinic_name, bot_phone_number, config (JSONB), niche_type |
| `users` | Usuarios del sistema | id (UUID), email, password_hash, role, status, tenant_id |
| `leads` | Leads de ventas | id (UUID), tenant_id, phone_number, first_name, last_name, email, status, source, assigned_seller_id, stage_id, tags (JSONB) |
| `sellers` | Vendedores | id, user_id, tenant_id, first_name, last_name, email, phone_number, is_active |
| `clients` | Clientes convertidos | id, tenant_id, phone_number, first_name, last_name, status |
| `opportunities` | Oportunidades de venta | id (UUID), tenant_id, lead_id, seller_id, name, value, stage, probability |
| `sales_transactions` | Transacciones | id (UUID), tenant_id, opportunity_id, lead_id, amount, transaction_date, payment_method |

#### Comunicación

| Tabla | Descripción | Columnas clave |
|-------|------------|----------------|
| `chat_messages` | Mensajes WhatsApp | id, tenant_id, from_number, role (user/assistant/system), content, assigned_seller_id |
| `inbound_messages` | Webhooks entrantes | id, provider, provider_message_id, from_number, payload (JSONB), status |

#### Agenda y Calendario

| Tabla | Descripción | Columnas clave |
|-------|------------|----------------|
| `seller_agenda_events` | Eventos de agenda | id (UUID), tenant_id, seller_id, title, start_datetime, end_datetime, lead_id, status |
| `google_calendar_blocks` | Bloqueos de GCal | id (UUID), tenant_id, google_event_id, title, start_datetime, end_datetime, professional_id |

#### Notificaciones y Métricas

| Tabla | Descripción | Columnas clave |
|-------|------------|----------------|
| `notifications` | Notificaciones | id, tenant_id, type, title, message, priority, recipient_id, read, expires_at |
| `seller_metrics` | Métricas de vendedores | id, seller_id, tenant_id, total_conversations, leads_assigned, leads_converted, conversion_rate, avg_response_time_seconds |
| `assignment_rules` | Reglas de asignación | id, tenant_id, rule_name, rule_type (round_robin/performance/specialty/load_balance), config (JSONB) |

#### Marketing (Meta Ads + Google Ads)

| Tabla | Descripción | Columnas clave |
|-------|------------|----------------|
| `meta_tokens` | Tokens OAuth Meta | id, tenant_id, access_token, token_type, page_id |
| `meta_ads_campaigns` | Campañas Meta Ads | id, tenant_id, meta_campaign_id, name, status, spend, impressions, clicks, leads, roi_percentage |
| `meta_ads_insights` | Insights por día | id, tenant_id, meta_campaign_id, date, spend, impressions, clicks, ctr, cost_per_lead |
| `meta_templates` | Templates HSM WhatsApp | id, tenant_id, meta_template_id, name, category, components (JSONB), status |
| `automation_rules` | Reglas de automatización | id, tenant_id, trigger_type, trigger_conditions (JSONB), action_type, action_config (JSONB) |

#### Lead Status System

| Tabla | Descripción | Columnas clave |
|-------|------------|----------------|
| `lead_statuses` | Estados configurables | id, tenant_id, name, code, category, color, icon, is_initial, is_final, sort_order |
| `lead_status_transitions` | Transiciones permitidas | id, tenant_id, from_status_code, to_status_code, is_allowed, requires_approval |
| `lead_status_history` | Historial de cambios | id, lead_id, tenant_id, from_status_code, to_status_code, changed_by_user_id, comment |
| `lead_status_triggers` | Triggers automáticos | id, tenant_id, trigger_name, action_type (email/whatsapp/notification), action_config |

#### Auditoría

| Tabla | Descripción | Columnas clave |
|-------|------------|----------------|
| `system_events` | Eventos de seguridad | id, tenant_id, user_id, event_type, severity, message, payload (JSONB) |
| `credentials` | Bóveda de credenciales | id, tenant_id, name, value (encrypted), category |

### 4.3 Campos extendidos de leads (Prospecting + Meta Ads)

```sql
-- Prospecting (Apify)
apify_title, apify_category_name, apify_address, apify_city,
apify_state, apify_country_code, apify_website, apify_place_id,
apify_reviews_count, apify_rating, apify_scraped_at,
prospecting_niche, prospecting_location_query

-- Outreach
outreach_message_sent, outreach_message_content, outreach_last_sent_at

-- Meta Ads Attribution
meta_lead_id, meta_campaign_id, meta_ad_id, meta_adset_id,
meta_campaign_name, meta_adset_name, meta_ad_name,
meta_ad_headline, meta_ad_body, lead_source, external_ids (JSONB)

-- Status tracking
status_changed_at, status_changed_by, status_metadata (JSONB)
```

---

## 5. API - Inventario Completo de Endpoints

### 5.1 Autenticación (`/auth/*`)

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/auth/companies` | Public | Lista de tenants disponibles |
| POST | `/auth/register` | Public (3/min) | Registro de usuario |
| POST | `/auth/login` | Public (5/min) | Login → JWT + Cookie |
| GET | `/auth/me` | Bearer/Cookie | Verificar sesión actual |
| POST | `/auth/logout` | Any | Cerrar sesión (limpia cookie) |
| GET | `/auth/profile` | Authenticated | Obtener perfil |
| PATCH | `/auth/profile` | Authenticated | Actualizar perfil |

### 5.2 Core Admin (`/admin/core/*`)

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/admin/core/users/pending` | Admin (CEO/Secretary) | Usuarios pendientes de aprobación |
| GET | `/admin/core/users` | Admin (CEO/Secretary) | Lista de usuarios |
| POST | `/admin/core/users/{id}/status` | Admin (CEO) | Activar/suspender usuario |
| GET | `/admin/core/chat/sessions` | Admin | Sesiones de chat (por tenant) |
| GET | `/admin/core/chat/messages/{phone}` | Admin | Mensajes de un número (limit/offset) |
| POST | `/admin/core/chat/send` | Admin | Enviar mensaje manual vía WhatsApp |
| PUT | `/admin/core/chat/sessions/{phone}/read` | Admin | Marcar chat como leído |
| POST | `/admin/core/chat/human-intervention` | Admin | Activar/desactivar override humano |
| POST | `/admin/core/chat/remove-silence` | Admin | Reactivar respuesta IA |
| GET | `/admin/core/stats/summary` | Admin | KPIs del dashboard (weekly/30d) |
| GET | `/admin/core/chat/urgencies` | Admin | Chats urgentes |
| GET | `/admin/core/tenants` | CEO | Lista de tenants |
| PUT | `/admin/core/tenants/{id}` | CEO | Actualizar tenant |
| POST | `/admin/core/tenants` | CEO | Crear tenant |
| DELETE | `/admin/core/tenants/{id}` | CEO | Eliminar tenant |
| GET | `/admin/core/settings/clinic` | Admin | Config del tenant (idioma, niche) |
| PATCH | `/admin/core/settings/clinic` | Admin | Actualizar config |
| GET | `/admin/core/credentials` | Admin | Lista de credenciales del vault |
| POST | `/admin/core/credentials` | CEO | Guardar credencial |
| DELETE | `/admin/core/credentials/{id}` | CEO | Eliminar credencial |
| GET | `/admin/core/config/deployment` | Admin | URLs de deployment |
| GET | `/admin/core/audit/logs` | CEO | Logs de auditoría |

### 5.3 CRM Sales (`/admin/core/crm/*`)

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/admin/core/crm/leads` | User Context | Lista de leads (filtros: status, seller, search) |
| POST | `/admin/core/crm/leads` | User Context | Crear lead |
| GET | `/admin/core/crm/leads/{id}` | User Context | Detalle de lead |
| PUT | `/admin/core/crm/leads/{id}` | User Context | Actualizar lead |
| POST | `/admin/core/crm/leads/{id}/assign` | User Context | Asignar lead a vendedor |
| PUT | `/admin/core/crm/leads/{id}/stage` | User Context | Cambiar etapa del pipeline |
| GET | `/admin/core/crm/leads/phone/{phone}/context` | User Context | Contexto de lead por teléfono (para chats) |
| GET | `/admin/core/crm/lead-statuses` | Admin | Estados de lead configurados |
| GET | `/admin/core/crm/leads/{id}/available-transitions` | Admin | Transiciones disponibles |
| PUT | `/admin/core/crm/{id}/status` | Admin | Cambiar estado de lead |
| POST | `/admin/core/crm/leads/bulk-status` | Admin | Cambio masivo de estado |
| GET | `/admin/core/crm/leads/{id}/status-history` | Admin | Timeline de estados |
| GET | `/admin/core/crm/clients` | User Context | Lista de clientes |
| POST | `/admin/core/crm/clients` | User Context | Crear cliente |
| PUT | `/admin/core/crm/clients/{id}` | User Context | Actualizar cliente |
| DELETE | `/admin/core/crm/clients/{id}` | User Context | Eliminar cliente |
| GET | `/admin/core/crm/sellers` | User Context | Lista de vendedores |
| POST | `/admin/core/crm/sellers` | User Context | Crear vendedor |
| PUT | `/admin/core/crm/sellers/{id}` | User Context | Actualizar vendedor |
| GET | `/admin/core/crm/agenda/events` | User Context | Eventos de agenda (start_date, end_date, seller_id) |
| POST | `/admin/core/crm/agenda/events` | User Context | Crear evento |
| PUT | `/admin/core/crm/agenda/events/{id}` | User Context | Actualizar evento |
| DELETE | `/admin/core/crm/agenda/events/{id}` | User Context | Eliminar evento |
| POST | `/admin/core/crm/prospecting/scrape` | User Context | Scraping Apify (Google Places) |
| GET | `/admin/core/crm/prospecting/leads` | User Context | Leads de prospecting |
| POST | `/admin/core/crm/prospecting/send-message` | User Context | Envío masivo WhatsApp |

### 5.4 Seller Management (`/admin/core/sellers/*`)

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| POST | `/admin/core/sellers/conversations/assign` | Admin | Asignar conversación a vendedor |
| GET | `/admin/core/sellers/conversations/{phone}/assignment` | Admin | Ver asignación actual |
| POST | `/admin/core/sellers/conversations/{phone}/reassign` | CEO | Reasignar conversación |
| POST | `/admin/core/sellers/conversations/{phone}/auto-assign` | Admin | Auto-asignar por reglas |
| GET | `/admin/core/sellers/available` | Admin | Vendedores disponibles (por rol) |
| GET | `/admin/core/sellers/{id}/conversations` | Admin | Conversaciones de un vendedor |
| GET | `/admin/core/sellers/{id}/metrics` | Admin | Métricas individuales |
| GET | `/admin/core/sellers/team/metrics` | CEO | Métricas del equipo completo |
| GET | `/admin/core/sellers/leaderboard` | Admin | Ranking de vendedores |
| GET/POST/PUT/DELETE | `/admin/core/sellers/rules` | Admin/CEO | CRUD reglas de asignación |
| GET | `/admin/core/sellers/dashboard/overview` | Admin | Overview del dashboard de vendedores |

### 5.5 Notificaciones (`/admin/core/notifications/*`)

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/admin/core/notifications/` | User | Lista de notificaciones (limit, offset, unread_only) |
| GET | `/admin/core/notifications/count` | User | Conteo por prioridad (total, critical, high, medium, low) |
| POST | `/admin/core/notifications/read` | User | Marcar como leída |
| POST | `/admin/core/notifications/read-all` | User | Marcar todas como leídas |
| GET/PUT | `/admin/core/notifications/settings` | User | Config de notificaciones |
| POST | `/admin/core/notifications/run-checks` | CEO | Ejecutar verificación manual |
| DELETE | `/admin/core/notifications/expired` | CEO | Limpiar notificaciones expiradas |

### 5.6 Métricas (`/admin/core/metrics/*`)

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/admin/core/metrics/realtime/conversations/{seller_id}` | Admin | Métricas en tiempo real de un vendedor |
| GET | `/admin/core/metrics/realtime/team` | CEO | Métricas en tiempo real del equipo |
| GET | `/admin/core/metrics/trends/{seller_id}` | Admin | Tendencias por período |
| GET | `/admin/core/metrics/daily/summary` | CEO | Resumen diario |
| GET | `/admin/core/metrics/insights/{seller_id}` | Admin | Insights de rendimiento |
| GET | `/admin/core/metrics/system/health` | CEO | Salud del sistema |
| GET | `/admin/core/metrics/comparative/team` | CEO | Comparativa de equipo |
| POST | `/admin/core/metrics/cache/invalidate/{seller_id}` | CEO | Invalidar cache |

### 5.7 Marketing (`/crm/marketing/*`)

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/crm/marketing/stats` | Admin | Estadísticas Meta Ads (ROI, campaigns) |
| GET | `/crm/marketing/stats/roi` | Admin | Desglose de ROI |
| GET | `/crm/marketing/token-status` | Admin | Estado del token Meta |
| GET | `/crm/marketing/campaigns` | Admin | Lista de campañas |
| GET | `/crm/marketing/campaigns/{id}` | Admin | Detalle de campaña |
| GET | `/crm/marketing/hsm/templates` | Admin | Templates HSM WhatsApp |
| GET/POST | `/crm/marketing/automation/rules` | Admin | Reglas de automatización |
| GET | `/crm/marketing/google/campaigns` | Admin | Campañas Google Ads |
| GET | `/crm/marketing/google/metrics` | Admin | Métricas Google Ads |
| GET | `/crm/marketing/google/customers` | Admin | Cuentas Google Ads |
| GET | `/crm/marketing/combined-stats` | Admin | Stats combinadas Meta + Google |

### 5.8 OAuth (`/crm/auth/*`)

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/crm/auth/meta/url` | Admin | URL de autorización Meta OAuth |
| GET | `/crm/auth/meta/callback` | Public | Callback OAuth Meta |
| POST | `/crm/auth/meta/disconnect` | Admin | Desconectar Meta |
| GET | `/crm/auth/google/ads/url` | Admin | URL de autorización Google OAuth |
| GET | `/crm/auth/google/ads/callback` | Public | Callback OAuth Google |
| POST | `/crm/auth/google/ads/disconnect` | Admin | Desconectar Google Ads |

### 5.9 Webhooks (públicos)

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| POST | `/chat` | X-Internal-Token | Recepción de mensajes (WhatsApp → Orchestrator) |
| POST | `/webhook/ycloud/{tenant_id}` | Public | Proxy webhook YCloud |
| GET/POST | `/webhooks/meta` | Public | Webhooks Meta (verificación + eventos) |
| GET/POST | `/webhooks/meta/{tenant_id}` | Public | Webhooks Meta por tenant |

### 5.10 Health & Tasks (`/health/*`, `/scheduled-tasks/*`)

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/health/` | Public | Health check general |
| GET | `/health/readiness` | Public | Readiness probe (Kubernetes) |
| GET | `/health/liveness` | Public | Liveness probe |
| GET | `/health/tasks` | Public | Estado de tareas programadas |
| POST | `/health/tasks/start` | Public | Iniciar scheduler |
| POST | `/health/tasks/stop` | Public | Detener scheduler |
| GET | `/scheduled-tasks/status` | CEO | Estado de tareas (autenticado) |
| POST | `/scheduled-tasks/run/notification-checks` | CEO | Ejecutar check de notificaciones |
| POST | `/scheduled-tasks/run/metrics-refresh` | CEO | Refrescar métricas |
| POST | `/scheduled-tasks/run/data-cleanup` | CEO | Limpieza de datos |

---

## 6. Frontend - Mapa de Rutas y Vistas

### 6.1 Rutas públicas

| Ruta | Componente | Descripción |
|------|-----------|-------------|
| `/login` | LoginView | Login con JWT |
| `/demo` | LandingView | Landing page pública |
| `/legal`, `/privacy`, `/terms` | PrivacyTermsView | Páginas legales (requeridas por Meta OAuth) |

### 6.2 Rutas protegidas

| Ruta | Componente | Roles permitidos |
|------|-----------|-----------------|
| `/` | CrmDashboardView | Todos |
| `/chats` | ChatsView | Todos |
| `/crm/leads` | LeadsView | Todos |
| `/crm/leads/:id` | LeadDetailView | Todos |
| `/crm/clientes` | ClientsView | Todos |
| `/crm/clientes/:id` | ClientDetailView | Todos |
| `/crm/agenda` | CrmAgendaView | Todos |
| `/crm/prospeccion` | ProspectingView | CEO, Setter, Closer |
| `/crm/vendedores` | SellersView | CEO |
| `/crm/marketing` | MarketingHubView | CEO, Admin |
| `/crm/meta-leads` | MetaLeadsView | CEO, Setter, Closer, Secretary |
| `/crm/hsm` | MetaTemplatesView | CEO, Setter, Closer |
| `/notificaciones` | NotificationsView | Todos |
| `/aprobaciones` | UserApprovalView | CEO |
| `/empresas` | CompaniesView | CEO |
| `/configuracion` | ConfigView | CEO |
| `/perfil` | ProfileView | Todos |

### 6.3 Cliente HTTP (axios.ts)

```
Base URL: VITE_API_URL || 'http://localhost:8000'

Headers automáticos:
├─ Content-Type: application/json
├─ Authorization: Bearer ${JWT_TOKEN}
├─ X-Admin-Token: ${VITE_ADMIN_TOKEN}
├─ X-Tenant-ID: ${getCurrentTenantId()}
└─ withCredentials: true

Interceptors:
├─ 401 → Clear token, redirect to /login
├─ 403 → Emit tenant:error
├─ 5xx → Auto-retry (3 intentos, exponential backoff)
└─ Cache GET: 60s en localStorage
```

### 6.4 Contextos globales (React Context)

**AuthContext**: Sesión de usuario, login/logout, verificación automática al montar
**SocketContext**: Socket.IO, notificaciones en tiempo real, hook `useSocketNotifications()`
**LanguageContext**: i18n con `t('key')`, soporta es/en/fr, persiste en tenant config

### 6.5 UI Design System — ClinicForge Premium Dark Theme (v9.0)

**Implementado:** 2026-03-28 | **Archivos convertidos:** 51 componentes + index.css

El frontend usa un **dark theme premium** basado en el sistema de diseño ClinicForge. No existe light mode.

#### Paleta de colores

| Elemento | Valor | Tailwind |
|----------|-------|----------|
| Root background | `#06060e` | `bg-[#06060e]` |
| Surface Level 1 | `#0a0e1a` | `bg-[#0a0e1a]` |
| Surface Level 2 | `#0d1117` | `bg-[#0d1117]` |
| Glass surfaces | `rgba(255,255,255, 0.02-0.08)` | `bg-white/[0.03]` |
| Cards | `bg-white/[0.03]` + `border-white/[0.06]` | — |
| Inputs | `bg-white/[0.04]` + `border-white/[0.08]` | — |
| Modals | `bg-[#0d1117]` + `border-white/[0.08]` | — |
| Text primary | `rgba(255,255,255, 0.9)` | `text-white` |
| Text secondary | `rgba(255,255,255, 0.5)` | `text-white/50` |
| Text muted | `rgba(255,255,255, 0.30)` | `text-white/30` |

#### Componentes globales (index.css)

| Clase | Estilo dark |
|-------|-------------|
| `.card` | `bg-white/[0.03] rounded-xl border border-white/[0.06]` |
| `.btn-primary` | `bg-medical-600 text-white` |
| `.btn-secondary` | `bg-white/[0.06] text-white/70 border border-white/[0.08]` |
| `.input` | `bg-white/[0.04] border-white/[0.08] text-white placeholder-white/30` |
| `.modal-content` | `bg-[#0d1117] rounded-2xl border border-white/[0.08]` |
| `.badge-*` | `bg-{color}-500/10 text-{color}-400` |
| `.toast-*` | `bg-{color}-500/10 border-{color}-500 text-{color}-400` |
| `.skeleton` | `bg-white/[0.06] animate-pulse` |
| `.table th` | `bg-white/[0.03] text-white/50 border-white/[0.06]` |

#### Scrollbar dark
```css
::-webkit-scrollbar-track { background: #0a0e1a; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); }
```

#### Convenciones para nuevos componentes

1. **Fondos**: Siempre `bg-white/[0.02-0.08]`, nunca `bg-white` ni `bg-gray-*`
2. **Texto**: Escala `text-white` → `text-white/70` → `text-white/50` → `text-white/40` → `text-white/30`
3. **Bordes**: `border-white/[0.04-0.08]`, nunca `border-gray-*`
4. **Semánticos**: `bg-{color}-500/10 text-{color}-400` (no `bg-{color}-50 text-{color}-800`)
5. **Hover**: `hover:bg-white/[0.04-0.08]`, nunca `hover:bg-gray-*`
6. **Shadows**: Evitar `shadow-sm`. Usar `shadow-lg shadow-black/20` para elevation
7. **Touch**: Agregar `active:scale-95 transition-all touch-manipulation` a todo botón

---

## 7. Real-Time (Socket.IO)

### Eventos escuchados por el frontend

| Evento | Datos | Uso |
|--------|-------|-----|
| `NEW_MESSAGE` | phone_number, message, role | Nuevo mensaje en chat |
| `HUMAN_HANDOFF` | phone_number, reason | Derivación a humano |
| `HUMAN_OVERRIDE_CHANGED` | phone_number, enabled, until | Toggle IA on/off |
| `SELLER_ASSIGNMENT_UPDATED` | phone_number, seller_id, seller_name | Reasignación de vendedor |
| `CHAT_UPDATED` | phone_number, session data | Actualización de sesión |
| `NEW_APPOINTMENT` | phone_number | Nueva cita agendada |
| `new_notification` | Notification object | Notificación en tiempo real |
| `notification_count_update` | total, critical, high, medium, low | Conteo de no leídas |

### Eventos emitidos por el frontend

| Evento | Datos | Uso |
|--------|-------|-----|
| `subscribe_notifications` | user_id | Suscribirse a notificaciones |
| `mark_notification_read` | notification_id | Marcar como leída |
| `get_notification_count` | user_id | Solicitar conteo |
| `MANUAL_MESSAGE` | phone, tenant_id, message | Enviar mensaje manual |

---

## 8. Background Jobs (APScheduler)

| Tarea | Intervalo | Descripción |
|-------|----------|-------------|
| Notification checks | Cada 5 min | Verifica leads sin respuesta, leads calientes, follow-ups, alertas de rendimiento |
| Metrics refresh | Cada 15 min | Recalcula métricas de vendedores con cache Redis |
| Data cleanup | Cada 1 hora | Limpieza de notificaciones expiradas y datos temporales |
| Daily reports | 8:00 AM | Reportes diarios de rendimiento |

Control: `ENABLE_SCHEDULED_TASKS=true` en env. Endpoints en `/health/tasks/*` y `/scheduled-tasks/*`.

---

## 9. Integraciones Externas

### 9.1 WhatsApp (YCloud)
- Webhooks entrantes con validación HMAC-SHA256
- Transcripción de audios con OpenAI Whisper
- Deduplicación de mensajes con Redis (2 min TTL)
- Templates HSM para mensajes masivos
- Credenciales por tenant desde el Vault

### 9.2 Meta Ads (Facebook/Instagram)
- OAuth 2.0 flow completo
- Sincronización de campañas, insights, ROI
- Webhooks de leads desde formularios
- Templates HSM integrados
- Reglas de automatización (trigger → action)

### 9.3 Google Ads
- OAuth 2.0 flow
- Sincronización de campañas y métricas
- Stats combinadas con Meta Ads

### 9.4 Google Calendar
- Service Account authentication
- Sincronización bidireccional de eventos
- Detección de colisiones de horarios
- Timezone: America/Argentina/Buenos_Aires

### 9.5 Apify (Prospecting)
- Scraping de Google Places por nicho y ubicación
- Enriquecimiento de leads con datos de negocio
- Envío masivo de mensajes WhatsApp a prospectos

---

## 10. Despliegue (Docker + EasyPanel)

### docker-compose.yml

```yaml
services:
  orchestrator_service:   # Puerto 8000
  whatsapp_service:       # Puerto 8002
  bff_service:            # Puerto 3000
  frontend_react:         # Puerto 4173
  redis:                  # Puerto 6379
  postgres:               # Puerto 5432
```

### Variables de entorno críticas

| Variable | Requerida | Servicio |
|----------|-----------|---------|
| `JWT_SECRET_KEY` | SI | orchestrator |
| `ADMIN_TOKEN` | SI | orchestrator |
| `INTERNAL_API_TOKEN` | SI | orchestrator + whatsapp |
| `POSTGRES_DSN` | SI | orchestrator |
| `REDIS_URL` | SI | orchestrator + whatsapp |
| `OPENAI_API_KEY` | NO | orchestrator + whatsapp |
| `YCLOUD_API_KEY` | SI (WhatsApp) | whatsapp |
| `YCLOUD_WEBHOOK_SECRET` | SI (WhatsApp) | whatsapp |
| `GOOGLE_CREDENTIALS` | NO | orchestrator (GCal) |
| `CREDENTIALS_FERNET_KEY` | NO | orchestrator (vault) |
| `CORS_ALLOWED_ORIGINS` | NO | orchestrator |
| `VITE_API_URL` | SI | frontend (build time) |
| `VITE_ADMIN_TOKEN` | SI | frontend (build time) |

### Health checks

- `GET /health/` → Estado general del orchestrator
- `GET /health/readiness` → Readiness probe (PostgreSQL + Redis)
- `GET /health/liveness` → Liveness probe
- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 11. Internacionalización (i18n)

- 3 idiomas: Español (es), English (en), Français (fr)
- Archivos: `frontend_react/src/locales/{es,en,fr}.json`
- Hook: `useTranslation()` → `t('namespace.key')`
- Persistencia: campo `tenants.config.ui_language`
- **Regla**: Todo texto visible debe usar `t()`. Nunca strings hardcodeados.

---

## 12. Cómo ejecutar el proyecto

### Desarrollo local (Docker)
```bash
docker-compose up --build
```
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- WhatsApp Service: http://localhost:8002

### Solo frontend (dev)
```bash
cd frontend_react && npm install && npm run dev
```
Requiere `VITE_API_URL` apuntando al backend.

### Variables mínimas
Ver sección 10 de este documento. Imprescindibles: `POSTGRES_DSN`, `REDIS_URL`, `JWT_SECRET_KEY`, `ADMIN_TOKEN`, `INTERNAL_API_TOKEN`.

---

*Documento generado: 2026-03-19. Fuente de verdad: código fuente del repositorio.*
