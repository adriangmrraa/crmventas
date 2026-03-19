---
name: "DB Schema Surgeon"
description: "v8.0: Database & Persistence Master. Evolución segura del esquema CRM, parches idempotentes y JSONB para configuración de ventas."
trigger: "v8.0, sql, idempotent, schema, migration, database, leads, sellers, opportunities"
scope: "DATABASE"
auto-invoke: true
---

# DB Schema Surgeon - CRM Ventas (Nexus Core) v8.0

## 1. Evolución Segura e Idempotente (Maintenance Robot)
**REGLA DE ORO**: Se prohíbe la ejecución de SQL directo fuera del Evolution Pipeline.
- **Protocolo de Parches**: Todo cambio estructural debe realizarse mediante un parche asíncrono en `orchestrator_service/db.py`.
- **CRM Persistence**: La tabla `leads` se gestiona vía el pipeline de evolución (Patch 16+). No buscarla en el schema base inicial.
- **Bloques DO $$**: Uso mandatorio de bloques `DO $$` con lógica de verificación (`IF NOT EXISTS`, `IF EXISTS`) para garantizar la estabilidad tras múltiples reinicios.
- **Auditoría & Normalización**: Parche 35 (Auditoría con `tenant_id`) y Parche 36 (Normalización de `source` a `whatsapp_inbound`) son críticos para la integridad v7.7.
- **Parches 37-40 (Marketing & Sales)**: Implementan `page_id` en tokens, tablas de campañas, insights, templates, automatización y el pipeline de ventas (opportunities/transactions).
- **Sincronización de Base**: Tras evolucionar el pipeline, se debe actualizar el archivo de cimiento `db/init/` para nuevas instalaciones.

## 2. Esquema CRM de Ventas (Tablas Core)
### Tablas Principales
- **`tenants`**: Registro de organizaciones/empresas. Cada tenant es un negocio independiente.
- **`users`**: Usuarios del sistema con roles (`ceo`, `professional`, `secretary`, `setter`, `closer`). Estado `pending`/`active`.
- **`leads`**: Prospectos de venta. Campos clave: `name`, `phone_number`, `email`, `source`, `status`, `assigned_seller_id`, `score`, `temperature` (hot/warm/cold), `tenant_id`. Gestionada vía parches en db.py.
- **`sellers`**: Vendedores activos. Campos: `user_id`, `working_hours` (JSONB), `specialties`, `max_leads`, `is_active`, `tenant_id`.
- **`clients`**: Leads convertidos en clientes efectivos tras cerrar una venta.
- **`opportunities`**: Pipeline de ventas. Campos: `lead_id`, `seller_id`, `stage`, `value`, `expected_close_date`, `extra_data` (JSONB), `tenant_id`.
- **`sales_transactions`**: Registro de ventas cerradas. Vinculada a `opportunities` y `clients`.

### Tablas de Soporte
- **`seller_agenda_events`**: Eventos de agenda de vendedores (reuniones, llamadas, demos).
- **`chat_messages`**: Historial de conversaciones WhatsApp vinculado a `lead_id` para contexto comercial.
- **`notifications`**: 4 tipos de notificaciones para sellers y managers. Campos: `type`, `title`, `message`, `read`, `tenant_id`.
- **`seller_metrics`**: Métricas de rendimiento por vendedor (tasa de conversión, tiempo de respuesta, leads activos).
- **`assignment_rules`**: Reglas de asignación automática de leads a sellers (round-robin, por carga, por especialidad).

### Tablas de Marketing & Integraciones
- **`meta_tokens`**: Tokens de integración con Meta (Facebook/Instagram). Incluye `page_id`.
- **`meta_ads_campaigns`**: Campañas publicitarias de Meta Ads con métricas de rendimiento.
- **`google_calendar_blocks`**: Bloques de calendario sincronizados desde Google Calendar.
- **`credentials`**: Almacén encriptado (Fernet/AES-256) de claves API por tenant (YCloud, Meta, Google).

## 3. Multi-tenancy & Aislamiento Legal
- **Filtro tenant_id**: Todas las tablas core **DEBEN** incluir y filtrar por `tenant_id` en cada consulta de lectura o escritura.
- **Aislamiento Técnico**: Este campo es el único garante de la privacidad de datos comerciales entre diferentes organizaciones.
- **Tipo de Dato**: `tenant_id` siempre como `INTEGER`, nunca como string, para consistencia en joins y filtros.

## 4. Uso Estratégico de JSONB (Flexibilidad Comercial)
Preferir JSONB para datos semi-estructurados o con alta variabilidad:
- **`sellers.working_hours`**: Configuración de disponibilidad semanal (slots y habilitación por día, 0=Domingo a 6=Sábado).
- **`leads.metadata`**: Datos adicionales del lead capturados desde formularios, Meta Ads o WhatsApp (UTM params, campaign_id, ad_id).
- **`opportunities.extra_data`**: Información variable del deal (productos cotizados, notas de negociación, archivos adjuntos).
- **`assignment_rules.config`**: Configuración flexible de reglas de asignación (criterios, pesos, exclusiones).

## 5. Persistencia & Optimización
- **Búsqueda Ultrarrápida**: Garantizar índices operativos en `phone_number` y `email` dentro de la tabla `leads`. Índice en `assigned_seller_id` para queries de carga de trabajo.
- **Persistencia de Memoria**: Vincular `chat_messages` con `lead_id` para mantener el contexto comercial a largo plazo en el Orchestrator.
- **Deduplicación con Redis**: Utilizar Redis para locks efímeros y deduplicación de webhooks (2 min) antes de confirmar escrituras en PostgreSQL.
- **Índices Compuestos**: `(tenant_id, status)` en leads, `(tenant_id, seller_id)` en opportunities para queries frecuentes del dashboard.

## 6. Lógica de Negocio en Datos
- **Conversión Lead-Cliente**: El `status` del lead dispara los protocolos de avance en el pipeline. Un lead pasa a `client` solo tras cerrar una `opportunity` exitosa.
- **Seller Metrics**: Las métricas se recalculan periódicamente via APScheduler y se almacenan en `seller_metrics` para consulta rápida en dashboards.
- **Protocolo Omega Prime**: El sistema de DB debe asegurar la auto-activación del primer usuario CEO registrado para evitar bloqueos iniciales de acceso.
- **Soft Delete**: Preferir campos `is_active`/`deleted_at` sobre DELETE físico para leads, sellers y clients, preservando historial comercial.

---
*Nexus v8.0 - Senior Database & Persistence Architect Protocol - CRM Ventas*
