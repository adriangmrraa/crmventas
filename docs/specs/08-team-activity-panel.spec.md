# SPEC: Admin — Panel de Actividad del Equipo en Tiempo Real

**Ticket:** DEV-39
**Fecha:** 2026-03-28
**Prioridad:** Alta (Visibilidad operativa para CEO/Director)
**Esfuerzo:** Medio-Alto (4-6 dias)
**Confidence:** 94%

---

## 1. Contexto

### Por que el admin necesita un panel de actividad en tiempo real

El CRM VENTAS tiene vendedores (setters, closers) trabajando leads simultaneamente: dejando notas, cambiando estados, asignando, chateando por WhatsApp. **El administrador/CEO no tiene forma de ver que esta pasando ahora mismo.** Solo puede revisar metricas agregadas en el dashboard o entrar lead por lead.

Sin un panel de actividad en tiempo real:
- No detecta vendedores inactivos hasta que es tarde
- No sabe si hay leads sin atencion hace horas
- No puede identificar cuellos de botella operativos en el momento
- Depende de reportes manuales o preguntar por chat

### Estado actual del proyecto

| Componente | Estado |
|------------|--------|
| Socket.IO server (`core/socket_notifications.py`) | Existente |
| Socket.IO client (`SocketContext.tsx`) | Existente |
| Modelo `SellerMetrics` (KPIs por vendedor) | Existente |
| Modelo `LeadStatusHistory` (audit trail de cambios) | Existente |
| Modelo `LeadNote` (notas con author_id y timestamps) | Existente |
| Modelo `ChatMessage` (mensajes con assigned_seller_id) | Existente |
| `GET /admin/core/sellers/team/metrics` (metricas equipo) | Existente |
| `GET /admin/core/sellers/leaderboard` (ranking) | Existente |
| Modelo `ActivityEvent` (feed unificado de acciones) | **NO existe** |
| Endpoint de feed de actividad en vivo | **NO existe** |
| Canal WebSocket `team_activity` | **NO existe** |
| Vista `TeamActivityView` en frontend | **NO existe** |

**Conclusion**: La infraestructura de WebSocket y metricas ya existe. Hay que crear el modelo de eventos de actividad, un endpoint de feed, un canal WebSocket dedicado, y la vista frontend.

---

## 2. Requerimientos Tecnicos

### 2.1 Backend: Modelo ActivityEvent

#### Tabla `activity_events`

| Columna | Tipo | Nullable | Default | Descripcion |
|---------|------|----------|---------|-------------|
| `id` | UUID | NO | `uuid4` | PK |
| `tenant_id` | INTEGER | NO | — | FK a `tenants.id` |
| `actor_id` | UUID | NO | — | FK a `users.id` (quien hizo la accion) |
| `event_type` | VARCHAR(50) | NO | — | Tipo de evento (ver enum abajo) |
| `entity_type` | VARCHAR(30) | NO | — | `lead`, `chat`, `note`, `task` |
| `entity_id` | VARCHAR(100) | NO | — | ID de la entidad afectada |
| `metadata` | JSONB | SI | `{}` | Datos extra del evento |
| `created_at` | TIMESTAMP | NO | `now()` | Cuando ocurrio |

#### Enum `event_type`

| Tipo | Descripcion | Metadata esperada |
|------|-------------|-------------------|
| `lead_created` | Vendedor creo un lead | `{lead_name, phone}` |
| `lead_status_changed` | Cambio de estado del lead | `{from_status, to_status, lead_name}` |
| `lead_assigned` | Lead asignado/reasignado | `{lead_name, from_seller, to_seller}` |
| `note_added` | Nota agregada a un lead | `{lead_name, note_type}` |
| `call_logged` | Llamada registrada | `{lead_name, duration_seconds}` |
| `chat_message_sent` | Mensaje enviado en chat | `{lead_name, channel}` |
| `task_completed` | Tarea completada | `{lead_name, task_title}` |
| `lead_qualified` | Lead calificado por setter | `{lead_name, score}` |
| `lead_handoff` | Handoff de setter a closer | `{lead_name, from_seller, to_seller}` |

#### Indices

```sql
CREATE INDEX idx_activity_events_tenant_created ON activity_events (tenant_id, created_at DESC);
CREATE INDEX idx_activity_events_actor ON activity_events (actor_id, created_at DESC);
CREATE INDEX idx_activity_events_entity ON activity_events (entity_type, entity_id);
```

#### Checkpoint de Soberania
> `tenant_id` se extrae del JWT del usuario autenticado. TODAS las queries filtran por `WHERE tenant_id = $tenant_id`.

### 2.2 Backend: Endpoints

#### `GET /admin/core/team-activity/feed`
**Acceso:** Roles `ceo` unicamente.

**Query params:**
| Param | Tipo | Default | Descripcion |
|-------|------|---------|-------------|
| `limit` | int | 50 | Max eventos (max 200) |
| `offset` | int | 0 | Paginacion |
| `seller_id` | UUID? | null | Filtrar por vendedor |
| `event_type` | string? | null | Filtrar por tipo |
| `date_from` | datetime? | null | Desde fecha |
| `date_to` | datetime? | null | Hasta fecha |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "actor": {"id": "uuid", "name": "Tomas Garcia", "role": "setter"},
      "event_type": "note_added",
      "entity_type": "lead",
      "entity_id": "uuid-del-lead",
      "entity_name": "Lead #342 — Juan Perez",
      "metadata": {"note_type": "post_call"},
      "created_at": "2026-03-28T14:32:00Z",
      "time_ago": "hace 3 min"
    }
  ],
  "total": 245,
  "has_more": true
}
```

#### `GET /admin/core/team-activity/seller-status`
**Acceso:** Roles `ceo` unicamente.

**Response:**
```json
{
  "sellers": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "name": "Tomas Garcia",
      "role": "setter",
      "status": "active",
      "active_leads_count": 12,
      "last_activity_at": "2026-03-28T14:32:00Z",
      "last_activity_type": "note_added",
      "avg_first_response_today_seconds": 180,
      "avg_first_response_week_seconds": 220,
      "leads_without_activity_2h": 3
    }
  ]
}
```

#### `GET /admin/core/team-activity/alerts`
**Acceso:** Roles `ceo` unicamente.

**Response:**
```json
{
  "alerts": [
    {
      "type": "lead_inactive",
      "severity": "warning",
      "lead_id": "uuid",
      "lead_name": "Maria Lopez",
      "assigned_seller": "Lucia Fernandez",
      "hours_inactive": 3.5,
      "last_activity_at": "2026-03-28T11:00:00Z"
    }
  ]
}
```

### 2.3 Backend: WebSocket Canal `team_activity`

#### Eventos emitidos

| Evento | Payload | Cuando |
|--------|---------|--------|
| `team_activity:new_event` | ActivityEvent completo | Cada vez que se registra un evento |
| `team_activity:seller_status_changed` | `{seller_id, status, last_activity_at}` | Cuando cambia el estado de un vendedor |
| `team_activity:new_alert` | Alert object | Cuando un lead supera 2h sin actividad |

#### Subscripcion
- Room: `team_activity:{tenant_id}`
- Solo usuarios con rol `ceo` pueden suscribirse (validar en server)

### 2.4 Backend: Servicio de Registro de Actividad

**`activity_service.py`** — se integra en los servicios existentes para registrar eventos:

| Punto de integracion | Evento |
|----------------------|--------|
| `lead_status_service.py` al cambiar estado | `lead_status_changed` |
| `seller_assignment_service.py` al asignar | `lead_assigned` |
| `lead_notes_routes.py` al crear nota | `note_added` |
| Handoff setter→closer | `lead_handoff` |
| Crear lead | `lead_created` |
| Completar task | `task_completed` |
| Enviar mensaje chat | `chat_message_sent` |

### 2.5 Frontend: Vista TeamActivityView

#### Ruta
- `/crm/actividad-equipo`
- Acceso: `ProtectedRoute allowedRoles={['ceo']}`

#### Layout (Scroll Isolation)
```
┌─────────────────────────────────────────────────────┐
│ Header: "Actividad del Equipo"  [Filtros]           │
├────────────────────┬────────────────────────────────┤
│                    │                                │
│  Panel Vendedores  │  Feed de Actividad en Vivo     │
│  (sidebar left)    │  (scroll independiente)        │
│                    │                                │
│  ┌──────────────┐  │  ┌──────────────────────────┐  │
│  │ Tomas Garcia │  │  │ 🟢 Tomas dejo nota en   │  │
│  │ 🟢 activo    │  │  │    lead #342 — hace 3min │  │
│  │ 12 leads     │  │  ├──────────────────────────┤  │
│  │ resp: 3min   │  │  │ 🔄 Lucia derivo lead    │  │
│  ├──────────────┤  │  │    #289 al closer — 5min │  │
│  │ Lucia Fdez   │  │  ├──────────────────────────┤  │
│  │ 🟡 inactiva  │  │  │ ⚠️ Lead Maria Lopez sin │  │
│  │ 8 leads      │  │  │    actividad 3.5h        │  │
│  │ resp: 5min   │  │  └──────────────────────────┘  │
│  └──────────────┘  │                                │
│                    │                                │
│  ───────────────   │                                │
│  ALERTAS (3)       │                                │
│  ⚠️ 3 leads >2h   │                                │
│  sin actividad     │                                │
│                    │                                │
└────────────────────┴────────────────────────────────┘
```

#### Checkpoint de UI
> Contenedor padre: `h-screen overflow-hidden flex flex-col`. Area de contenido: `flex-1 min-h-0 overflow-y-auto`. Feed y panel de vendedores con scroll independiente.

#### Componentes

| Componente | Descripcion |
|------------|-------------|
| `TeamActivityView.tsx` | Vista principal con layout |
| `ActivityFeed.tsx` | Feed scrolleable con items en tiempo real |
| `ActivityFeedItem.tsx` | Item individual del feed (clickeable → navega al lead) |
| `SellerStatusPanel.tsx` | Panel lateral con estado de cada vendedor |
| `SellerStatusCard.tsx` | Card de un vendedor con indicadores |
| `InactiveLeadsAlert.tsx` | Alerta visual de leads sin actividad |
| `ActivityFilters.tsx` | Barra de filtros (fecha, vendedor, tipo) |

#### Indicadores de estado por vendedor

| Estado | Condicion | Color |
|--------|-----------|-------|
| `active` | Ultima actividad < 15 min | 🟢 Verde |
| `idle` | Ultima actividad entre 15-60 min | 🟡 Amarillo |
| `inactive` | Ultima actividad > 60 min | 🔴 Rojo |

#### Tiempo de primera respuesta

Mostrar dos metricas por vendedor:
- **Hoy**: promedio de tiempo entre asignacion y primera accion del vendedor (hoy)
- **Semana**: mismo calculo, ultimos 7 dias

---

## 3. Criterios de Aceptacion (Gherkin)

### Scenario 1: Feed de actividad en vivo
```gherkin
Given el usuario con rol "ceo" esta en /crm/actividad-equipo
When un vendedor deja una nota en el lead #342
Then aparece un nuevo item en el feed sin recargar la pagina
And el item muestra "Tomas dejo una nota en lead #342 — hace 1 min"
And el item es clickeable y navega a /crm/leads/{id}
```

### Scenario 2: Indicador de estado por vendedor
```gherkin
Given el panel de vendedores muestra a "Tomas Garcia"
When Tomas no ha realizado ninguna accion en los ultimos 20 minutos
Then su indicador cambia de 🟢 (activo) a 🟡 (inactivo)
And muestra "ultima actividad: hace 20 min"
```

### Scenario 3: Alerta de leads sin actividad
```gherkin
Given el lead "Maria Lopez" fue asignado a "Lucia Fernandez"
And no ha habido ninguna actividad sobre ese lead en 2 horas
Then aparece una alerta visual en el panel
And la alerta muestra el nombre del lead, vendedor asignado y horas sin actividad
```

### Scenario 4: Filtros de actividad
```gherkin
Given el feed muestra actividad de todos los vendedores
When el CEO filtra por vendedor "Tomas Garcia" y tipo "note_added"
Then el feed muestra solo las notas agregadas por Tomas
And los demas items desaparecen
```

### Scenario 5: Restriccion de acceso por rol
```gherkin
Given un usuario con rol "setter" intenta acceder a /crm/actividad-equipo
Then es redirigido al dashboard principal
And no tiene acceso al endpoint /admin/core/team-activity/feed
```

### Scenario 6: Contador de leads activos
```gherkin
Given el vendedor "Tomas Garcia" tiene 12 leads en estados no-finales
Then su card muestra "12 leads activos"
And el contador se actualiza en tiempo real cuando se asigna o cierra un lead
```

### Scenario 7: Click en item del feed navega al lead
```gherkin
Given el feed muestra "Lucia derivo lead #289 al closer"
When el CEO hace click en ese item
Then navega a /crm/leads/{id-del-lead-289}
And ve el detalle completo del lead
```

---

## 4. Esquema de Datos

### Nueva tabla: `activity_events`
```sql
CREATE TABLE IF NOT EXISTS activity_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    actor_id UUID NOT NULL REFERENCES users(id),
    event_type VARCHAR(50) NOT NULL,
    entity_type VARCHAR(30) NOT NULL,
    entity_id VARCHAR(100) NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_activity_events_tenant_created
    ON activity_events (tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_activity_events_actor
    ON activity_events (actor_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_activity_events_entity
    ON activity_events (entity_type, entity_id);
```

### Tablas existentes usadas (sin modificar)
- `users` — actor info (name, role)
- `sellers` — seller_id ↔ user_id mapping
- `seller_metrics` — last_activity_at, response times
- `leads` — entity info, assigned_seller_id
- `lead_status_history` — cambios de estado (backfill opcional)
- `lead_notes` — notas existentes

---

## 5. Riesgos y Mitigacion

| Riesgo | Impacto | Mitigacion |
|--------|---------|------------|
| Volumen alto de eventos satura la tabla | Lentitud en queries | Indice en `(tenant_id, created_at DESC)` + retention policy (borrar >90 dias) |
| WebSocket broadcast a muchos admins | Carga en server | Room por `tenant_id`, solo CEOs suscritos |
| Eventos duplicados si el servicio falla y reintenta | Feed confuso | Deduplicacion por `(actor_id, event_type, entity_id, created_at)` con ventana de 5s |
| Vendedor inactivo por almuerzo genera alerta falsa | Ruido | Solo alertar en horario laboral del tenant (`business_hours` en config) |
| Race condition en conteo de leads activos | Dato incorrecto | Query en tiempo real, no cache |

---

## 6. Fuera de Alcance (v1)

- Notificaciones push/email al CEO por alertas criticas (futuro)
- Grabaciones de llamadas en el feed
- Comparativa historica vendedor vs vendedor (ya existe en leaderboard)
- Export del feed a CSV/PDF
