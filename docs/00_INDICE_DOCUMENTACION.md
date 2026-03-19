# Índice de documentación – CRM Ventas

Este documento lista **todos** los archivos activos de la carpeta `docs/` con una breve descripción. Sirve como mapa para encontrar rápidamente qué documento consultar.
**Proyecto:** CRM Ventas (Nexus Core) – single-niche CRM de ventas (leads, pipeline, vendedores, agenda, chats, marketing).
**Protocolo:** Non-Destructive Fusion. Última revisión: 2026-03.

---

## Documento principal

| Archivo | Contenido |
|---------|-----------|
| **[ESTADO_ACTUAL_PROYECTO.md](ESTADO_ACTUAL_PROYECTO.md)** | **Foto completa del proyecto**: arquitectura, stack, auth, seguridad, base de datos (todas las tablas), inventario completo de endpoints API, frontend (rutas, vistas, API calls), Socket.IO, background jobs, integraciones, despliegue, variables de entorno. **Leer primero.** |

---

## Documentos numerados (por orden)

| # | Archivo | Contenido |
|---|---------|-----------|
| 01 | [01_architecture.md](01_architecture.md) | Arquitectura del sistema: diagrama, microservicios (Orchestrator, WhatsApp), Socket.IO, multi-tenant, analytics, background jobs. |
| 02 | [02_environment_variables.md](02_environment_variables.md) | Variables de entorno por servicio: Orchestrator, WhatsApp, PostgreSQL, Redis, OpenAI, YCloud, Google, Meta, JWT, ADMIN_TOKEN. |
| 03 | [03_deployment_guide.md](03_deployment_guide.md) | Guía de despliegue: EasyPanel, Docker Compose, configuración de producción. |
| 05 | [05_developer_notes.md](05_developer_notes.md) | Notas para desarrolladores: añadir tools, paginación, debugging, Maintenance Robot, i18n, agenda móvil, analytics, prospecting, landing. |
| 07 | [07_workflow_guide.md](07_workflow_guide.md) | Guía de flujo de trabajo: ciclo de tareas, Git, documentación, troubleshooting, comunicación entre servicios. |
| 08a | [08_troubleshooting_history.md](08_troubleshooting_history.md) | Histórico de problemas y soluciones. |
| 08b | [08_background_jobs_guide.md](08_background_jobs_guide.md) | Guía de background jobs: APScheduler, 4 tareas programadas, health checks, configuración por entorno. |
| 09 | [09_real_time_notifications.md](09_real_time_notifications.md) | Sistema de notificaciones en tiempo real: Socket.IO, 4 tipos de notificación, seller-specific y CEO broadcast. |
| 10 | [10_ceo_dashboard_guide.md](10_ceo_dashboard_guide.md) | Dashboard CEO: KPIs, métricas de vendedores, analytics en tiempo real. |
| 29 | [29_seguridad_owasp_auditoria.md](29_seguridad_owasp_auditoria.md) | Auditoría de seguridad OWASP Top 10:2025; JWT + X-Admin-Token; gestión de credenciales. |
| 30 | [30_audit_api_contrato_2026-02-09.md](30_audit_api_contrato_2026-02-09.md) | Auditoría del contrato API: verificación endpoints reales vs documentación. |
| 31 | [31_audit_documentacion_2026-02-09.md](31_audit_documentacion_2026-02-09.md) | Auditoría de documentación: alineación con la plataforma SaaS. |

---

## Documentos por nombre (alfabético)

| Archivo | Contenido |
|---------|-----------|
| [API_REFERENCE.md](API_REFERENCE.md) | Referencia completa de la API: autenticación, prefijos `/admin/core` y `/admin/core/crm`, leads, clientes, vendedores, agenda, chat, métricas, notificaciones, marketing, health. Swagger en `/docs`, ReDoc en `/redoc`. |
| [CONTEXTO_AGENTE_IA.md](CONTEXTO_AGENTE_IA.md) | Punto de entrada para agentes IA: qué es el proyecto, stack, carpetas, reglas, API, rutas frontend, BD, i18n, tareas frecuentes. |
| [ESTADOS_LEADS_SYSTEM.spec.md](ESTADOS_LEADS_SYSTEM.spec.md) | Especificación del sistema de estados de leads: workflows configurables, transiciones, automatización. |
| [MARKETING_INTEGRATION_DEEP_DIVE.md](MARKETING_INTEGRATION_DEEP_DIVE.md) | Análisis técnico profundo integración Meta Ads Marketing Hub: arquitectura, componentes, flujos, seguridad, debugging. |
| [MATRIZ_DECISION_SKILLS.md](MATRIZ_DECISION_SKILLS.md) | Matriz de decisión para elegir skills según tipo de tarea. |
| [PROMPT_CONTEXTO_IA_COMPLETO.md](PROMPT_CONTEXTO_IA_COMPLETO.md) | Bloque de texto listo para copiar/pegar al inicio de una conversación con una IA: contexto global, reglas, workflows, skills. |
| [PROTOCOLO_AUTONOMIA_SDD.md](PROTOCOLO_AUTONOMIA_SDD.md) | Protocolo de autonomía SDD v2.0: ciclo de retroalimentación, criterios de detención, soberanía de datos. |
| [SPECS_IMPLEMENTADOS_INDICE.md](SPECS_IMPLEMENTADOS_INDICE.md) | Índice de especificaciones implementadas: consolidación de .spec.md retirados; dónde está documentada cada funcionalidad. |

---

## Planes (docs/plans/)

| Archivo | Contenido |
|---------|-----------|
| [plan-paridad-crm-vs-clinicas.md](plans/plan-paridad-crm-vs-clinicas.md) | Plan de implementación para cerrar brechas CRM vs Clínicas: DB, ChatService, backend, frontend, verificación. |

---

## Documentos en la raíz del proyecto

| Archivo | Contenido |
|---------|-----------|
| **AGENTS.md** (raíz) | Guía suprema del proyecto: arquitectura, soberanía de datos, aislamiento de scroll, tools, Maintenance Robot, i18n, connect-sovereign. **Leer antes de modificar.** |
| **README.md** (raíz) | Visión, tecnología, características, estructura del proyecto, despliegue, documentación hub. |

---

## Archivo histórico (docs/archive/)

Documentación que ya no refleja el estado actual del proyecto pero se conserva como referencia histórica. Incluye:
- Reportes de sprints completados (Sprint 1, 2, 3)
- Planes de implementación ya ejecutados (Meta Ads, Google Ads, Estados Leads)
- Auditorías completadas y reportes de verificación
- Documentación específica del módulo dental (Dentalogic)
- Scripts de diagnóstico, auditoría y testing one-off
- Resúmenes de implementación ya consolidados

---

## Total

- **En `docs/` (activos):** 20 archivos Markdown (numerados + por nombre + planes).
- **En `docs/archive/`:** ~60 archivos históricos preservados.
- **En raíz:** AGENTS.md, README.md.

Para endpoints y contratos API, usar [API_REFERENCE.md](API_REFERENCE.md) y Swagger en `http://localhost:8000/docs`. Rutas admin bajo **`/admin/core/*`** y módulo CRM bajo **`/admin/core/crm/*`**.
