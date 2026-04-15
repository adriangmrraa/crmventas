# MASTER PROPOSAL: Migración crmcodexy → CRM VENTAS

**Estado**: DRAFT
**Fecha**: 2026-04-14
**Autor**: Equipo Fusa Labs
**Topic Key**: `sdd/codexy-migration/proposal`

---

## 1. Resumen Ejecutivo

Este documento es el plan maestro para migrar las funcionalidades únicas y valiosas de **crmcodexy** (prototipo Next.js + Supabase) hacia **CRM VENTAS** (sistema principal FastAPI + React 18 + PostgreSQL multi-tenant). El objetivo no es fusionar sistemas sino extraer el valor real del prototipo e integrarlo de forma nativa en la arquitectura de producción.

Se identificaron **9 features** en crmcodexy que no existen en CRM VENTAS. Se migran como microfeatures nativas, respetando multi-tenancy, roles, y la arquitectura de microservicios existente. No se migra código fuente de Next.js/Supabase directamente — se reimplementa contra la stack de producción.

**Alcance total**: 9 specs, 4 fases, estimado 14–20 semanas.

---

## 2. Background

### 2.1 crmcodexy (origen)

| Atributo | Valor |
|---|---|
| Framework | Next.js 16 (App Router) |
| Backend | Supabase (PostgreSQL + Auth + Storage + Realtime) |
| Tenancy | Single-tenant |
| Roles | 2: `admin`, `vendedor` |
| Estado | Borrador funcional, no producción |
| Valor | Ideas y UX bien ejecutadas para equipo pequeño |

### 2.2 CRM VENTAS (destino)

| Atributo | Valor |
|---|---|
| Backend | FastAPI + PostgreSQL |
| Frontend | React 18 |
| Tenancy | Multi-tenant (tenant_id en todas las tablas) |
| Roles | 5: `superadmin`, `admin`, `gerente`, `vendedor`, `soporte` |
| Arquitectura | Microservicios + Socket.IO + JWT + X-Admin-Token |
| Estado | Producción activa |

### 2.3 Problema

crmcodexy desarrolló soluciones funcionales para problemas reales (almacenamiento de archivos, comunicación interna, seguimiento diario) que CRM VENTAS no tiene. Descartar ese trabajo sería un error — la oportunidad es extraer el valor e integrarlo correctamente.

### 2.4 Decisión

Migración **feature-by-feature** como reimplementación nativa. No se porta código fuente. Se toma la lógica de negocio, la UX, y las reglas del dominio; se implementan contra FastAPI + React 18 + PostgreSQL multi-tenant.

---

## 3. Features Matrix

| # | Spec | Feature | Prioridad | Complejidad | Fase |
|---|------|---------|-----------|-------------|------|
| 01 | [SPEC-01](./01-drive-storage.md) | Drive/Storage — carpetas, upload, vinculación a cliente | Alta | Alta | 1 |
| 07 | [SPEC-07](./07-telegram-notifications.md) | Telegram Bot — notificaciones a canal CEO | Baja | Baja | 1 |
| 04 | [SPEC-04](./04-internal-chat.md) | Chat Interno — canales + DMs + notificaciones | Alta | Alta | 2 |
| 02 | [SPEC-02](./02-message-templates.md) | Plantillas de Mensajes — variables + categorías + contador | Media | Media | 2 |
| 05 | [SPEC-05](./05-daily-checkin.md) | Check-in Diario — metas vendedor + panel CEO tiempo real | Media | Media | 3 |
| 06 | [SPEC-06](./06-admin-vendor-tasks.md) | Tareas Admin→Vendedor — asignación + deadlines + notas | Media | Media | 3 |
| 03 | [SPEC-03](./03-knowledge-base.md) | Base de Conocimiento — docs markdown + categorías + búsqueda | Media | Media | 3 |
| 08 | [SPEC-08](./08-client-360-profile.md) | Perfil 360° Cliente — tabs unificados (notas, llamadas, WhatsApp, archivos) | Media | Media | 4 |
| 09 | [SPEC-09](./09-pipeline-ui-enhancements.md) | Pipeline & UI — indicador stale, CSV preview, resolver dialog | Baja | Baja-Media | 4 |

---

## 4. Fases de Implementación

### Fase 1 — Foundation (Semanas 1–4)

**Objetivo**: Infraestructura base que desbloquea el resto.

#### SPEC-01: Drive/Storage
- Almacenamiento de archivos con carpetas jerárquicas
- Upload directo a MinIO (S3-compatible, Docker)
- Vinculación de archivos a clientes específicos
- **Bloqueante para**: SPEC-08 (Perfil 360° necesita tab de archivos)

#### SPEC-07: Telegram Notifications
- Integración con Bot API de Telegram
- Notificaciones a canal CEO configurado por tenant
- Standalone, sin dependencias internas
- **Valor**: Quick win, alto impacto para dirección

**Criterio de salida Fase 1**: MinIO operativo, archivos persistidos con tenant_id, bot Telegram enviando notificaciones reales.

---

### Fase 2 — Communication (Semanas 5–9)

**Objetivo**: Canales de comunicación interna del equipo.

#### SPEC-04: Chat Interno
- Canales de equipo (general, ventas, soporte, etc.)
- DMs entre usuarios del mismo tenant
- Notificaciones de tareas y llamadas dentro del chat
- Usa Socket.IO rooms por canal/DM (infraestructura ya existente)
- **Alto valor**: Reemplaza WhatsApp/Slack para comunicación interna

#### SPEC-02: Plantillas de Mensajes
- Plantillas reutilizables con `{{variables}}` interpoladas
- Categorías configurables por tenant
- Contador de uso por plantilla
- Almacenadas en PostgreSQL con JSONB para array de variables
- **Depende de**: Nada. Puede usarse desde Chat y WhatsApp.

**Criterio de salida Fase 2**: Chat funcional con rooms por tenant, plantillas creadas y aplicables desde múltiples contextos.

---

### Fase 3 — Operations (Semanas 10–15)

**Objetivo**: Herramientas operativas del equipo de ventas.

#### SPEC-05: Daily Check-in
- Registro diario de metas por vendedor (llamadas planificadas, cierres, demos)
- Panel CEO con vista en tiempo real de todos los vendedores
- Socket.IO para actualizaciones en vivo
- **Valor**: Visibilidad de dirección sin micromanagement

#### SPEC-06: Admin→Vendor Tasks
- Admin asigna tareas/notas a vendedores con deadline
- Vendedor recibe notificación (chat + Telegram si configurado)
- Tracking de estado: pendiente → en progreso → completada
- **Depende de**: SPEC-04 (notificaciones por chat), SPEC-07 (notificaciones Telegram, opcional)

#### SPEC-03: Knowledge Base
- Documentos de entrenamiento en formato Markdown
- Categorías configurables por tenant
- Búsqueda full-text (PostgreSQL FTS)
- **Valor**: Onboarding y referencia para equipo de ventas

**Criterio de salida Fase 3**: Check-ins registrándose, panel CEO operativo, tareas asignables y rastreables, base de conocimiento con búsqueda.

---

### Fase 4 — Polish (Semanas 16–20)

**Objetivo**: UX final que aprovecha toda la infraestructura construida.

#### SPEC-08: Perfil 360° Cliente
- Vista unificada por cliente con tabs: Notas, Llamadas, WhatsApp, Archivos
- Tab de Archivos usa SPEC-01 (Drive)
- Consolidación de datos dispersos en una sola pantalla
- **Depende de**: SPEC-01 (archivos), datos existentes de notas/llamadas

#### SPEC-09: Pipeline & UI Enhancements
- Indicador visual de deals estancados (stale indicator con umbral configurable)
- Preview de CSV antes de importación masiva
- Resolver dialog para conflictos en importaciones
- **Valor**: Calidad UX del pipeline existente

**Criterio de salida Fase 4**: Perfil 360° operativo, pipeline con indicadores, importación CSV mejorada.

---

## 5. Decisiones Arquitectónicas

### 5.1 Multi-Tenancy (NO NEGOCIABLE)

```sql
-- TODAS las tablas nuevas deben incluir:
tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE
```

- Nunca retornar datos sin filtrar por `tenant_id`
- Row-Level Security en PostgreSQL para capas críticas
- Sin excepciones. Un error acá compromete datos de todos los tenants.

### 5.2 Autenticación

- Usar JWT + `X-Admin-Token` existentes en CRM VENTAS
- No introducir Supabase Auth ni ningún proveedor nuevo
- Roles: los 5 existentes (`superadmin`, `admin`, `gerente`, `vendedor`, `soporte`)
- Mapeo de roles crmcodexy → CRM VENTAS: `admin` → `admin`, `vendedor` → `vendedor`

### 5.3 File Storage

- **MinIO** (S3-compatible) corriendo en Docker como nuevo servicio
- NO usar Supabase Storage
- SDK: `boto3` en FastAPI para operaciones S3
- Paths: `/{tenant_id}/{entity_type}/{entity_id}/{filename}`
- URLs firmadas con TTL configurable (default: 1 hora)

### 5.4 Real-Time

- Usar Socket.IO existente en CRM VENTAS
- Rooms por tenant: `tenant:{tenant_id}:channel:{channel_id}`
- Rooms para DMs: `tenant:{tenant_id}:dm:{user_a_id}:{user_b_id}` (IDs ordenados)
- NO usar polling, NO usar Supabase Realtime
- Eventos nuevos deben seguir convención de naming existente

### 5.5 Plantillas y Variables

```json
{
  "name": "Seguimiento post-demo",
  "category": "ventas",
  "content": "Hola {{nombre_cliente}}, te escribo para dar seguimiento a la demo del {{fecha}}...",
  "variables": ["nombre_cliente", "fecha"],
  "usage_count": 0
}
```

- Almacenadas en PostgreSQL, campo `variables` como `JSONB`
- Interpolación en frontend con regex `/{{\w+}}/g`
- Sin ejecución de código del lado servidor

### 5.6 Testing (TDD Obligatorio)

- **Backend**: pytest con fixtures por tenant, mocks de MinIO con `moto`
- **Frontend**: vitest (a implementar) — no bloquea desarrollo pero es obligatorio antes de merge
- Cobertura mínima: 80% en rutas nuevas
- Tests de integración para flujos multi-tenant críticos

---

## 6. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| Leak de datos entre tenants | Media | Crítico | RLS en PostgreSQL + tests de aislamiento obligatorios |
| Capacidad de MinIO en producción | Baja | Alto | Definir quotas por tenant desde Fase 1 |
| Complejidad de Socket.IO rooms en Chat | Media | Alto | Proof of concept antes de SPEC-04 completo |
| Acumulación de deuda técnica en Fase 4 | Alta | Medio | Code review obligatorio entre fases |
| Scope creep — agregar features de crmcodexy no listadas | Media | Medio | Este doc es el scope freeze. Cambios requieren nueva propuesta. |
| Migración de datos existentes de crmcodexy | Baja | Bajo | No hay migración de datos, solo de features |

---

## 7. Plan de Rollback

Dado que se trata de features nuevas (no modificación de features existentes), el rollback es simple:

1. **Feature flags por tenant**: Cada feature nueva se activa via flag en tabla `tenant_features`. Rollback = desactivar flag.
2. **Tablas aditivas**: No se modifica esquema existente. Las tablas nuevas son independientes. Rollback = `DROP TABLE` sin afectar producción.
3. **MinIO**: Servicio independiente en Docker. Rollback = detener contenedor. Frontend cae a "sin archivos" gracefully.
4. **Socket.IO events nuevos**: Los clientes que no conocen el evento lo ignoran. Rollback = eliminar handlers en server.
5. **Telegram Bot**: Variable de entorno `TELEGRAM_BOT_TOKEN` vacía deshabilita el feature completamente.

**Criterio de rollback**: Si un feature falla en producción y no se puede hotfix en 2 horas, se desactiva via feature flag sin downtime.

---

## 8. Timeline Estimado

```
Semana 01-02: SPEC-01 (Drive — backend + MinIO setup)
Semana 03-04: SPEC-01 (Drive — frontend) + SPEC-07 (Telegram)
Semana 05-07: SPEC-04 (Chat Interno — backend + Socket.IO rooms)
Semana 08-09: SPEC-04 (Chat — frontend) + SPEC-02 (Plantillas)
Semana 10-11: SPEC-05 (Check-in)
Semana 12-13: SPEC-06 (Admin Tasks)
Semana 14-15: SPEC-03 (Knowledge Base)
Semana 16-17: SPEC-08 (Perfil 360°)
Semana 18-19: SPEC-09 (Pipeline & UI)
Semana 20:    Buffer + QA final + hardening multi-tenant
```

**Velocidad asumida**: 1 desarrollador full-stack. Con 2 desarrolladores, Fase 1 y 2 pueden correr en paralelo reduciendo a ~14 semanas totales.

---

## 9. Grafo de Dependencias

```
SPEC-07 (Telegram)
  └── [standalone — sin dependencias]

SPEC-01 (Drive/Storage)
  └── [standalone — desbloquea SPEC-08]

SPEC-02 (Plantillas)
  └── [standalone — usable desde Chat y WhatsApp]

SPEC-04 (Chat Interno)
  ├── usa Socket.IO existente
  └── desbloquea notificaciones en SPEC-06

SPEC-05 (Check-in)
  ├── usa Socket.IO existente
  └── [standalone operativamente]

SPEC-06 (Admin Tasks)
  ├── depende de SPEC-04 (notificaciones por chat)
  └── opcionalmente SPEC-07 (notificaciones Telegram)

SPEC-03 (Knowledge Base)
  └── [standalone]

SPEC-08 (Perfil 360°)
  └── depende de SPEC-01 (tab de archivos)

SPEC-09 (Pipeline & UI)
  └── [standalone — mejoras sobre features existentes]
```

**Diagrama de dependencias (DAG)**:

```
SPEC-07 ──────────────────────────────────────────────► (done)
SPEC-01 ──────────────────────────────────► SPEC-08
SPEC-02 ──────────────────────────────────► (done)
SPEC-04 ──────────────────────────────────► SPEC-06
SPEC-05 ──────────────────────────────────► (done)
SPEC-07 (opcional) ───────────────────────► SPEC-06
SPEC-03 ──────────────────────────────────► (done)
SPEC-09 ──────────────────────────────────► (done)
```

---

## 10. Specs Individuales

Cada spec vive en este mismo directorio y sigue la convención `{NN}-{slug}.md`:

| Archivo | Spec | Estado |
|---------|------|--------|
| `01-drive-storage.md` | SPEC-01: Drive/Storage | PENDIENTE |
| `02-message-templates.md` | SPEC-02: Plantillas de Mensajes | PENDIENTE |
| `03-knowledge-base.md` | SPEC-03: Base de Conocimiento | PENDIENTE |
| `04-internal-chat.md` | SPEC-04: Chat Interno | PENDIENTE |
| `05-daily-checkin.md` | SPEC-05: Check-in Diario | PENDIENTE |
| `06-admin-vendor-tasks.md` | SPEC-06: Tareas Admin→Vendedor | PENDIENTE |
| `07-telegram-notifications.md` | SPEC-07: Telegram Notifications | PENDIENTE |
| `08-client-360-profile.md` | SPEC-08: Perfil 360° Cliente | PENDIENTE |
| `09-pipeline-ui-enhancements.md` | SPEC-09: Pipeline & UI Enhancements | PENDIENTE |

---

## 11. Criterios de Éxito Globales

- [ ] Todas las tablas nuevas tienen `tenant_id NOT NULL`
- [ ] Tests de aislamiento multi-tenant pasan para cada feature
- [ ] Cobertura pytest >= 80% en endpoints nuevos
- [ ] MinIO operativo con quotas por tenant
- [ ] Socket.IO rooms correctamente namespaced por tenant
- [ ] Feature flags implementados desde Fase 1
- [ ] Ningún feature modifica tablas existentes de producción
- [ ] Rollback documentado y probado por feature

---

*Este documento es el scope freeze. Cualquier feature no listado acá requiere una nueva propuesta antes de ser considerado para implementación.*
