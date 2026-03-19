# German - Leelo antes de tocar algo

Esto es un resumen ejecutivo de cómo está el proyecto hoy. Te lo dejo masticado para que puedas arrancar a laburar sin perder tiempo leyendo 50 archivos.

---

## Qué es esto

CRM de ventas multi-tenant con un agente IA que atiende WhatsApp. Los leads entran por WhatsApp (o Meta Ads, o prospecting), la IA los califica y los deriva a vendedores. El CEO ve todo desde un dashboard en tiempo real.

**En criollo**: un sistema donde entran contactos por WhatsApp, la IA los atiende, los clasifica, y los reparte entre los vendedores. El CEO ve métricas, el vendedor ve sus leads y chats.

---

## Stack (no te asustes, es estándar)

| Qué | Con qué | Puerto |
|-----|---------|--------|
| Backend | Python / FastAPI | 8000 |
| WhatsApp | Python / FastAPI + YCloud | 8002 |
| Frontend | React 18 + TypeScript + Tailwind | 5173 |
| BFF | Node.js / Express (proxy mínimo) | 3000 |
| DB | PostgreSQL 13 | 5432 |
| Cache | Redis | 6379 |
| Real-time | Socket.IO (dentro del backend) | - |
| Jobs | APScheduler (dentro del backend) | - |
| IA | LangChain + OpenAI gpt-4o-mini | - |

---

## Cómo levantar

```bash
# Todo junto (la forma fácil)
docker-compose up --build

# Solo frontend para desarrollar
cd frontend_react && npm install && npm run dev
```

Variables mínimas que necesitás en el `.env`:
- `POSTGRES_DSN` - conexión a la base
- `REDIS_URL` - conexión a Redis
- `JWT_SECRET_KEY` - para firmar tokens (64+ caracteres)
- `ADMIN_TOKEN` - token de infraestructura
- `INTERNAL_API_TOKEN` - comunicación entre servicios

Swagger está en `http://localhost:8000/docs` - ahí ves todos los endpoints.

---

## Estructura del repo (lo que importa)

```
CRM VENTAS/
│
├── orchestrator_service/        ← ACÁ ESTÁ TODO EL BACKEND
│   ├── main.py                  ← App FastAPI, endpoint /chat, agente IA con LangChain
│   ├── admin_routes.py          ← Rutas /admin/core/* (usuarios, chats, tenants, config)
│   ├── auth_routes.py           ← Login, register, /me, logout
│   ├── db.py                    ← Pool PostgreSQL + MIGRACIONES AUTOMÁTICAS (importante)
│   ├── gcal_service.py          ← Google Calendar
│   ├── analytics_service.py     ← Métricas
│   ├── core/
│   │   ├── security.py          ← verify_admin_token, roles, audit
│   │   ├── credentials.py       ← Vault encriptado (Fernet/AES-256)
│   │   ├── socket_manager.py    ← Socket.IO config
│   │   └── rate_limiter.py      ← Rate limiting (slowapi)
│   ├── modules/crm_sales/
│   │   ├── routes.py            ← /admin/core/crm/* (leads, clients, sellers, agenda)
│   │   ├── models.py            ← Pydantic models
│   │   └── status_models.py     ← Sistema de estados de leads
│   ├── routes/                  ← Sellers, notifications, metrics, marketing, OAuth
│   ├── services/                ← Lógica de negocio
│   └── migrations/              ← Patches SQL externos (008-018)
│
├── whatsapp_service/            ← Recibe webhooks de YCloud, envía mensajes
│   ├── main.py
│   └── ycloud_client.py
│
├── frontend_react/src/          ← FRONTEND REACT
│   ├── App.tsx                  ← Rutas y providers
│   ├── api/axios.ts             ← Cliente HTTP (ya tiene auth headers configurados)
│   ├── context/
│   │   ├── AuthContext.tsx       ← Sesión JWT
│   │   ├── SocketContext.tsx     ← Socket.IO + notificaciones real-time
│   │   └── LanguageContext.tsx   ← i18n (español, inglés, francés)
│   ├── views/                   ← Vistas principales (Dashboard, Chats, Login, etc.)
│   ├── modules/crm_sales/       ← Leads, Clients, Agenda, Prospecting, Sellers
│   └── locales/                 ← es.json, en.json, fr.json
│
├── docs/                        ← Documentación organizada
│   ├── ESTADO_ACTUAL_PROYECTO.md ← LA BIBLIA (todo el detalle técnico)
│   └── 00_INDICE_DOCUMENTACION.md ← Índice de docs
│
├── .agent/                      ← Skills y workflows para IAs
│   ├── skills/                  ← 26 skills (backend, frontend, DB, security, etc.)
│   └── workflows/               ← 20 workflows (specify, plan, implement, verify, etc.)
│
├── AGENTS.md                    ← Guía suprema. Leelo antes de modificar.
└── docker-compose.yml
```

---

## Seguridad (3 capas, no te las saltees)

```
Capa 1: X-Admin-Token (header fijo)
  → Token de infraestructura. Si no lo mandás, 401.
  → Viene de la variable ADMIN_TOKEN

Capa 2: JWT Bearer (token de usuario)
  → Se genera en login, dura 7 días
  → Va en header Authorization: Bearer <token>
  → También se setea como cookie HttpOnly

Capa 3: tenant_id (aislamiento de datos)
  → CADA query a la DB filtra por tenant_id
  → Un tenant NUNCA ve datos de otro
  → El CEO puede ver todos, los demás solo el suyo
```

**Roles**:
- `ceo` → ve y hace todo
- `setter` → califica leads, solo ve los suyos
- `closer` → cierra ventas, solo ve los suyos
- `secretary` → gestiona usuarios y chats
- `professional` → rol legacy (viene del módulo dental, se usa poco)

---

## Base de datos (lo más importante)

### Cómo funcionan las migraciones

**No hay Alembic ni nada raro.** Las migraciones están en `orchestrator_service/db.py` como bloques `DO $$` idempotentes. Cuando el backend arranca:

1. Crea el pool de conexiones
2. Verifica si existen las tablas core
3. Si no existen, corre el schema base (`db/init/dentalogic_schema.sql`)
4. Aplica los patches 1-14 secuencialmente (cada uno tiene `IF NOT EXISTS`)
5. Aplica patches externos 008-018 desde `migrations/`

**Para agregar un cambio de schema**: agregás un patch nuevo en `db.py` con `DO $$ BEGIN IF NOT EXISTS... END $$`. Así es idempotente y no rompe si se ejecuta 100 veces.

### Tablas que vas a tocar seguido

| Tabla | Para qué |
|-------|----------|
| `leads` | Los contactos de venta. Tiene 30+ columnas (datos básicos + prospecting Apify + atribución Meta Ads + estados) |
| `sellers` | Vendedores. Vinculados a `users` por `user_id` |
| `clients` | Leads que se convirtieron en clientes |
| `opportunities` | Oportunidades de venta (valor, etapa, probabilidad) |
| `sales_transactions` | Ventas cerradas |
| `chat_messages` | Historial de WhatsApp. Tiene `assigned_seller_id` para saber quién atiende |
| `seller_agenda_events` | Calendario de vendedores |
| `notifications` | Notificaciones con prioridad (critical/high/medium/low) |
| `seller_metrics` | Métricas: conversaciones, leads asignados, conversion rate, response time |
| `assignment_rules` | Reglas de auto-asignación (round_robin, performance, etc.) |
| `lead_statuses` | Estados configurables de leads (nombre, color, ícono) |
| `lead_status_transitions` | Qué transiciones están permitidas entre estados |
| `credentials` | Vault encriptado con API keys por tenant |
| `meta_ads_campaigns` | Campañas de Meta Ads sincronizadas |
| `system_events` | Logs de auditoría |

---

## API - Las rutas que necesitás conocer

### Autenticación
- `POST /auth/login` → devuelve JWT (rate limit: 5/min)
- `POST /auth/register` → crea usuario pending (rate limit: 3/min)
- `GET /auth/me` → verifica sesión
- `POST /auth/logout` → limpia cookie

### CRM (el módulo principal)
- `GET/POST /admin/core/crm/leads` → CRUD leads
- `GET/PUT /admin/core/crm/leads/{id}` → detalle/editar lead
- `POST /admin/core/crm/leads/{id}/assign` → asignar a vendedor
- `GET/POST /admin/core/crm/clients` → CRUD clientes
- `GET/POST /admin/core/crm/sellers` → CRUD vendedores
- `GET/POST/PUT/DELETE /admin/core/crm/agenda/events` → calendario
- `POST /admin/core/crm/prospecting/scrape` → scraping Apify
- `GET /admin/core/crm/lead-statuses` → estados configurados
- `PUT /admin/core/crm/{id}/status` → cambiar estado de lead

### Chats
- `GET /admin/core/chat/sessions` → sesiones de WhatsApp
- `GET /admin/core/chat/messages/{phone}` → historial de un número
- `POST /admin/core/chat/send` → enviar mensaje manual
- `POST /admin/core/chat/human-intervention` → activar/desactivar IA

### Sellers
- `POST /admin/core/sellers/conversations/assign` → asignar conversación
- `POST /admin/core/sellers/conversations/{phone}/auto-assign` → auto-asignar
- `GET /admin/core/sellers/{id}/metrics` → métricas de un vendedor
- `GET /admin/core/sellers/team/metrics` → métricas del equipo (CEO)
- `GET/POST/PUT/DELETE /admin/core/sellers/rules` → reglas de asignación

### Marketing
- `GET /crm/marketing/stats` → stats Meta Ads
- `GET /crm/marketing/combined-stats` → Meta + Google combinados
- `GET /crm/auth/meta/url` → iniciar OAuth Meta
- `GET /crm/auth/google/ads/url` → iniciar OAuth Google

### Health
- `GET /health/` → health check
- `GET /health/readiness` → readiness probe
- Swagger completo: `http://localhost:8000/docs`

---

## Frontend - Las pantallas

| Pantalla | Ruta | Quién la ve |
|----------|------|-------------|
| Dashboard (KPIs) | `/` | Todos |
| Chats WhatsApp | `/chats` | Todos |
| Leads | `/crm/leads` | Todos (filtrado por rol) |
| Detalle Lead | `/crm/leads/:id` | Todos |
| Clientes | `/crm/clientes` | Todos |
| Agenda | `/crm/agenda` | Todos |
| Prospecting | `/crm/prospeccion` | CEO, Setter, Closer |
| Vendedores | `/crm/vendedores` | Solo CEO |
| Marketing Hub | `/crm/marketing` | CEO |
| Meta Leads | `/crm/meta-leads` | CEO, Setter, Closer |
| Templates HSM | `/crm/hsm` | CEO, Setter, Closer |
| Aprobaciones | `/aprobaciones` | Solo CEO |
| Config | `/configuracion` | Solo CEO |

### Cómo funciona el frontend

- **Auth**: JWT en localStorage + cookie HttpOnly. El `AuthContext` verifica sesión al montar con `GET /auth/me`
- **HTTP**: `api/axios.ts` ya tiene configurados los headers (Bearer, X-Admin-Token, X-Tenant-ID, withCredentials)
- **Real-time**: `SocketContext` maneja Socket.IO. Hook `useSocketNotifications()` para notificaciones
- **i18n**: `LanguageContext` con `t('key')`. Archivos en `locales/{es,en,fr}.json`. Todo texto visible debe usar `t()`
- **Retry**: El axios interceptor reintenta 5xx automáticamente (3 intentos, exponential backoff)

### Eventos Socket.IO que escucha el frontend
- `NEW_MESSAGE` → nuevo mensaje en chat
- `SELLER_ASSIGNMENT_UPDATED` → reasignación de vendedor
- `new_notification` → notificación nueva
- `notification_count_update` → conteo de no leídas por prioridad
- `HUMAN_OVERRIDE_CHANGED` → toggle IA on/off en un chat
- `NEW_APPOINTMENT` → nueva cita agendada

---

## Las 5 reglas que NO podés romper

### 1. SIEMPRE filtrar por tenant_id
Toda query SQL tiene que tener `WHERE tenant_id = $x`. Sin excepciones. Es la base del multi-tenancy. Si te lo olvidás, un tenant ve datos de otro.

### 2. NUNCA ejecutar SQL directo
Los cambios de schema van como patches idempotentes en `db.py`. Usás bloques `DO $$ BEGIN IF NOT EXISTS... END $$`. Así el sistema se auto-migra al arrancar sin romper nada.

### 3. SIEMPRE usar t('key') para textos
El frontend soporta español, inglés y francés. Cualquier string visible al usuario tiene que usar `useTranslation()` y `t('namespace.key')`. Agregás la clave en los 3 archivos JSON.

### 4. Scroll isolation en frontend
El layout usa `h-screen overflow-hidden` en el root. Las vistas usan `flex-1 min-h-0 overflow-y-auto`. Si no respetás esto, el scroll se rompe en mobile.

### 5. No commitear secretos
Nada de `.env`, API keys, tokens ni credenciales en el repo. Las credenciales van en el Vault (tabla `credentials`, encriptadas con Fernet).

---

## Cómo usar una IA para trabajar en este repo

El repo tiene un sistema completo de skills y workflows pensado para que cualquier IA de código (Claude, Cursor, etc.) pueda trabajar sin romper nada.

### Opción 1: Contexto rápido (1 línea)

Pegá esto como primer mensaje en tu chat con la IA:

```
Trabajo en el proyecto CRM Ventas (CRM de ventas multi-tenant + agente WhatsApp).
Lee AGENTS.md y docs/CONTEXTO_AGENTE_IA.md antes de tocar código.
Reglas: filtrar siempre por tenant_id, i18n con t(), no ejecutar SQL directo.
Para flujos completos usá .agent/workflows/ (specify, plan, implement, verify).
```

### Opción 2: Contexto completo

Pegá el contenido de `docs/PROMPT_CONTEXTO_IA_COMPLETO.md` como primer mensaje. Le da a la IA todas las reglas, estructura y workflows de una.

### Workflows disponibles (comandos para la IA)

| Comando | Qué hace |
|---------|----------|
| `/specify` | Genera una especificación técnica (.spec.md) a partir de un requerimiento |
| `/plan` | Convierte la spec en un plan de tareas paso a paso |
| `/implement` | Ejecuta el plan: backend, frontend, migraciones |
| `/verify` | Corre tests, valida build, chequea seguridad |
| `/bug_fix` | Diagnóstico → reproducción → fix → verificación |
| `/new_feature` | Análisis → backend → frontend → verificación |
| `/audit` | Compara spec vs implementación real |
| `/update-docs` | Actualiza documentación sin borrar nada |
| `/push` | Commit + push al repo |

### Skills (la IA las lee automáticamente)

Hay 26 skills en `.agent/skills/`. Las más importantes:

- **Backend_Sovereign** → cómo trabajar el backend (rutas, modelos, migraciones, multi-tenancy)
- **Frontend_Nexus** → cómo trabajar el frontend (vistas, componentes, axios, i18n, Socket.IO)
- **DB_Evolution** → cómo hacer migraciones seguras
- **CRM_Sales_Module** → lógica del módulo CRM (leads, pipeline, vendedores)
- **Sovereign_Auditor** → checklist de seguridad antes de commitear
- **Omnichannel_Chat_Operator** → WhatsApp, YCloud, handoff humano

### Ejemplo práctico

Si querés agregar un campo nuevo a leads:

1. Decile a la IA: "Agregá el campo `company_name` a leads"
2. La IA (si leyó las skills) va a:
   - Agregar un patch idempotente en `db.py`
   - Actualizar el modelo Pydantic en `modules/crm_sales/models.py`
   - Actualizar la ruta en `modules/crm_sales/routes.py`
   - Agregar el campo en el frontend (LeadDetailView, LeadsView)
   - Agregar las traducciones en los 3 archivos JSON
   - Filtrar por `tenant_id` en la query

Sin las skills, la IA probablemente haría SQL directo y rompería todo.

---

## Dónde está el detalle técnico completo

Si necesitás más detalle (cada endpoint con sus params, cada tabla con sus columnas, cada evento Socket.IO):

- **`docs/ESTADO_ACTUAL_PROYECTO.md`** → la foto completa del proyecto
- **`docs/API_REFERENCE.md`** → referencia de API
- **`docs/00_INDICE_DOCUMENTACION.md`** → índice de toda la documentación
- **`AGENTS.md`** → la guía suprema (léela antes de tocar código)

---

*Cualquier duda, preguntale a la IA con el contexto cargado. Para eso están las skills.*
