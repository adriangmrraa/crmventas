# Plan de Implementacion: DEV-39 — Panel de Actividad del Equipo

**Spec:** `docs/specs/08-team-activity-panel.spec.md`
**Fecha:** 2026-03-28
**Confidence:** 94%

---

## Goal Description

Crear un panel de actividad en tiempo real para el CEO/admin que muestre un feed de acciones de los vendedores, estado de cada vendedor (activo/inactivo), metricas de respuesta, y alertas de leads sin atencion.

## User Review Required

- [ ] Confirmar que la ruta sera `/crm/actividad-equipo`
- [ ] Confirmar que solo el rol `ceo` tendra acceso (no setter/closer)
- [ ] Validar que el evento se registra **despues** de la accion exitosa (no antes)

---

## Proposed Changes

### Grupo 1: Backend — Modelo y Migracion

**Archivo:** `orchestrator_service/models.py`
- [ ] Agregar clase `ActivityEvent` (SQLAlchemy model)
- [ ] Campos: id (UUID), tenant_id (INT FK), actor_id (UUID FK), event_type (VARCHAR 50), entity_type (VARCHAR 30), entity_id (VARCHAR 100), metadata (JSONB), created_at (TIMESTAMP)
- [ ] Filtro `WHERE tenant_id = $tenant_id` en todas las queries

**Archivo:** `orchestrator_service/migrations/` (script SQL)
- [ ] CREATE TABLE IF NOT EXISTS activity_events con indices

### Grupo 2: Backend — Servicio de Actividad

**Archivo nuevo:** `orchestrator_service/services/activity_service.py`
- [ ] `async def record_event(tenant_id, actor_id, event_type, entity_type, entity_id, metadata)` — inserta en activity_events + emite via WebSocket
- [ ] `async def get_feed(tenant_id, limit, offset, filters)` — query paginada con JOINs a users para actor info
- [ ] `async def get_seller_statuses(tenant_id)` — estado de cada vendedor con metricas
- [ ] `async def get_inactive_lead_alerts(tenant_id)` — leads sin actividad >2h

### Grupo 3: Backend — Rutas

**Archivo nuevo:** `orchestrator_service/routes/team_activity_routes.py`
- [ ] `GET /admin/core/team-activity/feed` — feed paginado con filtros
- [ ] `GET /admin/core/team-activity/seller-status` — estado de vendedores
- [ ] `GET /admin/core/team-activity/alerts` — alertas de leads inactivos
- [ ] Validacion de rol `ceo` en todos los endpoints
- [ ] Registrar router en `main.py`

### Grupo 4: Backend — WebSocket Canal

**Archivo:** `orchestrator_service/core/socket_notifications.py`
- [ ] Agregar handler `subscribe_team_activity` — valida rol ceo, une a room `team_activity:{tenant_id}`
- [ ] Agregar handler `unsubscribe_team_activity`
- [ ] Funcion `emit_team_activity_event(tenant_id, event_data)` — broadcast a room

### Grupo 5: Backend — Integracion en Servicios Existentes

**Puntos de integracion (agregar llamada a `record_event`):**
- [ ] `routes/lead_status_routes.py` — al cambiar estado → `lead_status_changed`
- [ ] `services/seller_assignment_service.py` — al asignar → `lead_assigned`
- [ ] `routes/lead_notes_routes.py` — al crear nota → `note_added`
- [ ] Handoff setter→closer → `lead_handoff`
- [ ] Crear lead → `lead_created`
- [ ] Completar task → `task_completed`

### Grupo 6: Frontend — Vista y Componentes

**Archivo nuevo:** `frontend_react/src/modules/crm_sales/views/TeamActivityView.tsx`
- [ ] Layout con Scroll Isolation (`h-screen overflow-hidden` + `flex-1 min-h-0`)
- [ ] Panel izquierdo: SellerStatusPanel
- [ ] Panel derecho: ActivityFeed
- [ ] Barra de filtros superior

**Archivos nuevos en** `frontend_react/src/modules/crm_sales/components/team-activity/`
- [ ] `ActivityFeed.tsx` — lista scrolleable, recibe eventos WebSocket en tiempo real
- [ ] `ActivityFeedItem.tsx` — item individual, clickeable → navega a lead
- [ ] `SellerStatusPanel.tsx` — lista de vendedores con indicadores
- [ ] `SellerStatusCard.tsx` — card de vendedor (estado, leads, response time)
- [ ] `InactiveLeadsAlert.tsx` — seccion de alertas con badge de conteo
- [ ] `ActivityFilters.tsx` — filtros por fecha, vendedor, tipo de accion

### Grupo 7: Frontend — Routing y Navegacion

**Archivo:** `frontend_react/src/App.tsx`
- [ ] Agregar ruta `/crm/actividad-equipo` con `ProtectedRoute allowedRoles={['ceo']}`
- [ ] Import lazy de TeamActivityView

**Archivo:** Sidebar/Navegacion (donde esten los links del menu)
- [ ] Agregar item "Actividad del Equipo" visible solo para rol `ceo`

### Grupo 8: Frontend — Hook WebSocket

**Archivo nuevo:** `frontend_react/src/modules/crm_sales/hooks/useTeamActivity.ts`
- [ ] Hook que se suscribe a room `team_activity:{tenant_id}`
- [ ] Escucha eventos `team_activity:new_event`, `team_activity:seller_status_changed`, `team_activity:new_alert`
- [ ] Mantiene estado local del feed y lo prepende con nuevos eventos

---

## Orden de Ejecucion

1. Modelo + Migracion (Grupo 1)
2. Servicio de actividad (Grupo 2)
3. WebSocket canal (Grupo 4)
4. Rutas API (Grupo 3)
5. Integracion en servicios existentes (Grupo 5)
6. Frontend componentes (Grupo 6)
7. Routing + navegacion (Grupo 7)
8. Hook WebSocket (Grupo 8)

---

## Verification Plan

### Tests automatizados
- [ ] Test unitario: `activity_service.record_event` inserta correctamente
- [ ] Test unitario: `get_feed` respeta filtros y paginacion
- [ ] Test unitario: `get_seller_statuses` calcula estados correctamente
- [ ] Test integracion: endpoint feed devuelve 403 para rol setter
- [ ] Test integracion: WebSocket emite evento al registrar actividad

### Verificacion manual
- [ ] Abrir panel como CEO, dejar nota en otro tab → aparece en feed
- [ ] Verificar que setter no puede acceder a la ruta
- [ ] Click en item del feed → navega al lead correcto
- [ ] Filtrar por vendedor → solo muestra sus eventos
- [ ] Verificar alertas de leads sin actividad >2h
- [ ] Mobile: layout responsive sin scroll roto
