---
name: "Sovereign Backend Engineer"
description: "v8.0: Senior Backend Architect & Python Expert. Multi-tenancy CRM, pipelines de ventas, WhatsApp y evolución idempotente."
trigger: "v8.0, backend, tenancy, idempotencia, tools, pipeline, sellers, leads"
scope: "BACKEND"
auto-invoke: true
---

# Sovereign Backend Engineer - CRM Ventas (Nexus Core) v8.0

## 1. Evolución de Datos & Idempotencia (Maintenance Robot)
**REGLA DE ORO**: Nunca proporciones o ejecutes SQL directo fuera del pipeline de migración.
- **Evolution Pipeline**: Todo cambio estructural debe implementarse como un parche en `orchestrator_service/db.py`.
- **Bloques DO $$**: Usar siempre bloques `DO $$` para garantizar que la migración sea idempotente (ej: `IF NOT EXISTS (SELECT 1 FROM information_schema.columns...)`).
- **Foundation**: Si el parche es crítico para nuevos tenants, debe replicarse en `db/init/00x_schema.sql`.

## 2. Multi-tenancy & Modelo de Datos CRM
Es obligatorio el aislamiento estricto de datos:
- **Tenant Isolation**: Todas las queries SQL **DEBEN** incluir el filtro `tenant_id`. No asumas nunca contexto global. El `tenant_id` debe ser manejado siempre como **entero (`int`)** para evitar fallos de firma en integraciones.
- **The Vault (Sovereign Credentials)**: Las claves de integración (YCloud, Meta, Google) deben leerse de la tabla `credentials` filtrando por `tenant_id`. El uso de variables de entorno para esto es considerado **legacy/fallback**.
- **Tablas Core**: `tenants`, `users`, `leads`, `sellers`, `clients`, `opportunities`, `sales_transactions`, `seller_agenda_events`, `chat_messages`, `notifications`, `seller_metrics`, `assignment_rules`, `meta_tokens`, `meta_ads_campaigns`, `google_calendar_blocks`, `credentials`.
- **Tipado JSONB**: Dominio de la estructura de `config`/`metadata` en leads, `working_hours` en sellers (0-6 days), y `extra_data` en oportunidades dentro de PostgreSQL.

## 3. Sincronización JIT v2 (Google Calendar)
La lógica de sincronización híbrida debe ser robusta:
- **Mirroring en Vivo**: Consultar Google Calendar en tiempo real durante el `check_availability` vía `gcal_service`.
- **Normalización**: Limpiar nombres de vendedores para matching exacto con calendarios externos.
- **Deduping**: Filtrar eventos de GCal que ya existen localmente como `seller_agenda_events` mediante el `google_calendar_event_id`.

## 4. Lógica de Ventas & Herramientas del Agente (Tools)
Las herramientas del agente (definidas en `modules/crm_sales/tools_provider.py`) deben actuar como gatekeepers:
1. **check_availability**: Valida primero los `working_hours` del seller (BD) y luego GCal.
2. **Lead Qualification**: Antes de agendar, el lead debe tener como mínimo: **Nombre Completo, Teléfono, y Producto/Servicio de interés**.
3. **Seller Assignment**: Asignación automática de leads a sellers basada en `assignment_rules`, carga de trabajo actual (`seller_metrics`) y disponibilidad.
4. **Pipeline Management**: Gestión de `opportunities` con estados definidos en `modules/crm_sales/status_models.py`. Las transiciones de estado deben validarse contra el flujo permitido.
5. **Lead Scoring**: Clasificación de leads por temperatura (hot/warm/cold) basada en interacción y datos recopilados.

## 5. Seguridad & Infraestructura (Nexus v7.6)
- **Security Layer**: Implementación obligatoria de `SecurityHeadersMiddleware` (CSP, HSTS, X-Frame-Options) en `main.py`.
- **Auth Layer**: Manejo de JWT (HS256) con **Cookies HttpOnly**. Login emite `Set-Cookie` y logout limpia la sesión. Soporte adicional de `X-Admin-Token` para acceso administrativo.
- **Prompt Security**: Validación de mensajes entrantes mediante `core/prompt_security.py` para detectar inyecciones de prompts antes de procesar con LLM.
- **Fernet Encryption**: Uso de `core/credentials.py` para encriptación AES-256 de claves API en la tabla `credentials`.
- **RBAC**: Diferenciación estricta de roles: `ceo`, `professional`, `secretary`, `setter`, `closer`.
- **Gatekeeper Flow**: Usuarios nuevos nacen `pending`. La activación (`active`) es responsabilidad única del rol `ceo`.
- **Protocolo de Resiliencia**: Los queries a tablas de módulos (como `sellers`, `opportunities`) deben estar protegidos con `try/except` para manejar estados de migración incompletos.

## 6. Sincronización Real-Time (WebSockets / Socket.IO)
Garantizar que el Frontend esté siempre al día:
- **Emitir Eventos**: Emitir `NEW_LEAD`, `LEAD_UPDATED`, `NEW_APPOINTMENT`, `APPOINTMENT_UPDATED`, `NOTIFICATION_CREATED` vía Socket.IO tras cualquier mutación exitosa.
- **Seller Notifications**: Usar `seller_notification_service` para crear notificaciones (4 tipos) y emitir el evento correspondiente.
- **Rooms por Tenant**: Las rooms de Socket.IO deben segmentarse por `tenant_id` para respetar el aislamiento multi-tenant.

## 7. WhatsApp Service (Pipeline) v7.8
- **Transcripción**: Integración Whisper para audios.
- **Deduplicación**: Cache de 2 minutos en Redis para evitar procesar webhooks duplicados.
- **Buffering**: Agrupar mensajes en ráfaga para mejorar el contexto del LLM.
- **Protocolo HSM (v7.8)**:
    - **Consistencia de Firma**: Todo cliente de mensajería (YCloudClient) debe mantener firmas idénticas (`tenant_id` opcional) entre servicios para evitar fallos de tipo en disparadores asíncronos.
    - **Registro Espejo**: Todo mensaje automático/saliente (HSM) debe registrarse en `chat_messages` mediante `db.append_chat_message` para garantizar visibilidad en el CRM y prevenir bucles de reintentos por falta de estado conversacional.

## 8. Background Jobs (APScheduler)
- **Métricas de Sellers**: Jobs periódicos para recalcular `seller_metrics` (conversión, tiempo de respuesta, leads activos).
- **Seguimiento de Leads**: Tareas automáticas de re-contacto según reglas de negocio configuradas.
- **Limpieza**: Purga periódica de tokens expirados y sesiones inactivas.

## 9. Hardening v7.7.1 (Rate Limiting & Auditoría Multi-tenant)
- **Rate Limiting (slowapi)**:
    - `/auth/login`: 5/min.
    - `/auth/register`: 3/min.
    - Endpoints de listado (`leads`, `clients`, `sellers`): 100/min.
- **Auditoría Multi-tenant (Parche 35)**: La tabla `system_events` DEBE incluir `tenant_id` para garantizar el aislamiento de logs.
- **Decorador `@audit_access`**: Uso obligatorio en rutas administrativas y de acceso a datos sensibles (PII) para trazabilidad en `system_events`.
- **Security Logging**: Todo fallo crítico o acceso a PII debe registrarse mediante `log_security_event` (asegurando pasar el `tenant_id`). Los logs se consultan en `/admin/core/audit/logs`.

## 10. Rutas y Módulos
- **Rutas Base**: `/admin/core/*` para operaciones generales del sistema.
- **Rutas CRM**: `/admin/core/crm/*` para leads, clients, sellers, agenda/events.
- **Módulo CRM Sales**: `modules/crm_sales/` contiene `routes.py`, `models.py`, `tools_provider.py`, `status_models.py`.
- **Servicios Clave**: `seller_metrics_service`, `seller_notification_service`, `gcal_service`, `analytics_service`.

---
*Nexus v8.0 - Senior Backend Architect & Python Expert Protocol - CRM Ventas*
