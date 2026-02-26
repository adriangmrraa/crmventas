# 📄 Especificación Técnica (SSOT): Sistema Avanzado de Estados para Leads

## 1. Contexto y Objetivos
Migrar el sistema actual de CRM Ventas de estados rígidos de texto libre a una arquitectura madura: estados configurables por tenant, audit trail completo, transiciones reguladas (workflow) y ejecución de automatizaciones (triggers). Esta especificación se basa en los 5 documentos de arquitectura y la nueva guía de recomendaciones provistos.

## 2. Requerimientos Técnicas (Soberanía y UI)
- **Backend (Sovereign Backend):** Python, FastAPI, `asyncpg`.
  - **REGLA MANDATORIA:** Tenant isolation en TODAS las consultas SQL (`WHERE tenant_id = $1`).
  - **Idempotencia:** Las migraciones SQL deben ser seguras (`IF NOT EXISTS`, scripts de rollback).
- **Frontend (Nexus UI):** React, TailwindCSS.
  - **Aislamiento de Scroll:** Patrón de Scroll Isolation requerido.
  - **Optimistic UI:** Actualizaciones de estado en tiempo real con rollback automático de UI si falla la API.
- **Database:** PostgreSQL.

## 3. Criterios de Aceptación (Gherkin)

**Scenario 1: Migración segura de leads existentes**
- **Given** existing leads with hardcoded text statuses (e.g., 'new', 'contacted')
- **When** the database patch `patch_018_lead_status_system.sql` and python migration script run
- **Then** `lead_statuses` and `lead_status_transitions` are populated with default tenant settings
- **And** all existing leads are updated to reference the normalized `code` via Foreign Key without data loss.

**Scenario 2: Cambio de estado validado**
- **Given** a lead in 'new' status
- **When** the seller tries to change the status to 'contacted'
- **Then** the backend must validate if the transition from 'new' to 'contacted' is allowed for that tenant
- **And** it writes to `lead_status_history` saving the user_id, timestamp and optional comment.

**Scenario 3: Bulk Update seguro (Race Conditions)**
- **Given** a selection of 50 leads to change status
- **When** the bulk update is triggered
- **Then** the backend uses Advisory Locks per tenant and DB Transactions to process the batch without deadlocks or race conditions.

## 4. Esquema de Datos Requerido
- `lead_statuses` (tenant_id, code, name, color, icon, etc.)
- `lead_status_transitions` (tenant_id, from_status_code, to_status_code, is_allowed, etc.)
- `lead_status_history` (tenant_id, lead_id, from_status_code, to_status_code, changed_by, etc.)
- `lead_status_triggers` & `lead_status_trigger_logs` (Para la capa de automatización)
- Tabla `leads` alterada (Agregar constraint FK `status` hacia `lead_statuses(code)` y tracking timestamps).

## 5. Riesgos y Mitigación
1. **Pérdida de Operatividad en Producción:** Mitigado implementando Feature Flags (`REACT_APP_ENABLE_ADVANCED_LEAD_STATUS`) en el frontend para no interrumpir el workflow si hay fallos.
2. **Race Conditions en Bulk Update:** Mitigado con locks transaccionales de DB (`pg_advisory_xact_lock`).
3. **Errores de N+1 Queries en Listados:** Mitigado ejecutando sentencias de JOIN optimizadas con la tabla `lead_statuses` al pedir iterablemente los leads.
## 6. Clarificaciones (Acordadas con el Usuario)
1. **Feature Flag Frontend:** Se mantiene el interruptor (`REACT_APP_ENABLE_ADVANCED_LEAD_STATUS`) activo hasta validar estabilidad total.
2. **Circuit Breaker:** Implementar una estrategia profesional de "Safe-Retry". Tras 5 fallos consecutivos en envíos HSM para un tenant, se suspenderá la cola automáticamente por 1 hora para proteger la cuenta.
3. **Flujo de Estados:** Los estados "finales" (ej. Won/Lost) NO bloquean nuevas transiciones. El usuario retiene libertad de movimiento total.
4. **Migración de Datos:** Fallback predeterminado para estados no reconocidos será el código `new`.
5. **Locks Masivos:** Se valida el uso de Advisory Locks por Tenant para garantizar integridad en Bulk Updates.
