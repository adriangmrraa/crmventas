# SPEC-06: Admin-to-Vendor Notes & Tasks (Mis Notas)

**Proyecto:** CRM VENTAS (Nexus Core CRM)
**Origen:** crmcodexy — feature `vendor_notes` / `Mis Notas`
**Prioridad:** Media
**Complejidad:** Media
**Fecha:** 2026-04-14
**Estado:** Borrador

---

## 1. Contexto y Motivación

crmcodexy implementa un canal directo de comunicación Admin → Vendedor a través de una tabla `vendor_notes`. Los admins pueden escribir notas informativas o asignar tareas con deadline a vendedores específicos. El vendedor las ve en su página `/mis-notas`, separadas en tres secciones: tareas asignadas, notas del admin, y tareas personales propias.

CRM VENTAS ya tiene un sistema de notificaciones en tiempo real (4 tipos, Socket.IO), gestión de sellers (`SellersView`), y notas internas por lead (`lead_notes_routes.py`). Lo que NO tiene es un canal de tareas/notas directas Admin → Vendedor desacoplado de un lead concreto.

Esta spec define cómo migrar esa funcionalidad al stack de CRM VENTAS (FastAPI + React 18 + PostgreSQL multi-tenant) sin romper la arquitectura existente.

---

## 2. Alcance

### In scope

- Tabla `vendor_tasks` (equivalente a `vendor_notes` de codexy) con soporte multi-tenant
- Endpoints FastAPI para que admin CRUD tareas/notas sobre un seller
- Endpoint para que el seller marque una tarea como completada (con protección de autorización)
- Vista React `/mis-notas` con tres secciones: tareas asignadas, notas del admin, mis tareas personales
- Badge en sidebar con contador de tareas pendientes
- Integración con el sistema de notificaciones Socket.IO existente (notificar al seller cuando se crea una tarea)
- Soporte i18n (es.json / en.json / fr.json)

### Out of scope

- Adjuntos o archivos en notas
- Notificaciones push externas (email, WhatsApp) por tarea asignada — queda para Sprint posterior
- Edición de tareas ya creadas por el admin (fase 1: solo crear y completar)
- Comentarios o replies del vendedor sobre una tarea

---

## 3. Modelo de Datos

### 3.1 Tabla nueva: `vendor_tasks`

```sql
CREATE TABLE vendor_tasks (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    vendor_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_by   INTEGER NOT NULL REFERENCES users(id),
    contenido    TEXT NOT NULL CHECK (char_length(contenido) BETWEEN 1 AND 2000),
    es_tarea     BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_limite TIMESTAMP WITH TIME ZONE,
    completada   BOOLEAN NOT NULL DEFAULT FALSE,
    completada_at TIMESTAMP WITH TIME ZONE,
    created_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para queries frecuentes
CREATE INDEX idx_vendor_tasks_tenant_vendor
    ON vendor_tasks(tenant_id, vendor_id);

CREATE INDEX idx_vendor_tasks_pending
    ON vendor_tasks(tenant_id, vendor_id, completada)
    WHERE completada = FALSE;
```

**Decisiones de diseño vs codexy:**

| Aspecto | codexy | CRM VENTAS |
|---------|--------|------------|
| Nombre tabla | `vendor_notes` | `vendor_tasks` — más claro para el dominio |
| RLS (Row-Level Security) | Sí (Supabase) | No — la autorización se maneja en FastAPI con `tenant_id` + `vendor_id` == `current_user.id` |
| `vendor_id` tipo | UUID (Auth0) | INTEGER — consistente con `users.id` en CRM VENTAS |
| `created_by` tipo | UUID (Auth0) | INTEGER — idem |
| Multi-tenant | No (single-tenant) | Sí — `tenant_id` obligatorio en todas las queries |

### 3.2 Sección "Mis Tareas Personales" (auto-creadas por el seller)

Misma tabla `vendor_tasks`, con `created_by == vendor_id` y `es_tarea = TRUE`. La diferenciación en el frontend se hace por `created_by`:

- `created_by != current_user.id` → tarea/nota asignada por admin
- `created_by == current_user.id` → tarea personal

---

## 4. API — Endpoints FastAPI

Módulo: `orchestrator_service/routes/vendor_tasks_routes.py`
Prefijo: `/admin/core/crm/vendor-tasks`
Auth: `verify_admin_token` (admin) + `get_current_user` (seller — solo para sus propias rutas)

### 4.1 Admin — Crear nota/tarea para un vendedor

```
POST /admin/core/crm/vendor-tasks
Headers: Authorization: Bearer {jwt}, X-Admin-Token: {token}

Body:
{
  "vendor_id": 42,
  "contenido": "Texto de la nota o tarea",
  "es_tarea": true,
  "fecha_limite": "2026-05-01T18:00:00Z"  // opcional
}

Response 201:
{
  "id": "uuid",
  "vendor_id": 42,
  "created_by": 7,
  "contenido": "...",
  "es_tarea": true,
  "fecha_limite": "2026-05-01T18:00:00Z",
  "completada": false,
  "completada_at": null,
  "created_at": "2026-04-14T10:00:00Z"
}
```

Post-creación: emitir evento Socket.IO `VENDOR_TASK_ASSIGNED` al seller (ver sección 7).

### 4.2 Admin — Listar tareas/notas de un vendedor

```
GET /admin/core/crm/vendor-tasks?vendor_id=42&es_tarea=true&completada=false
Headers: Authorization: Bearer {jwt}, X-Admin-Token: {token}

Response 200: array de VendorTaskResponse
```

### 4.3 Admin — Eliminar una nota/tarea

```
DELETE /admin/core/crm/vendor-tasks/{task_id}
Headers: Authorization: Bearer {jwt}, X-Admin-Token: {token}

Response 204
```

Solo si `tenant_id` coincide. No se puede eliminar si ya está completada (retornar 409 con mensaje descriptivo).

### 4.4 Seller — Obtener sus tareas/notas

```
GET /admin/core/crm/vendor-tasks/mine
Headers: Authorization: Bearer {jwt}

Query params:
  - tipo: "asignadas" | "notas" | "personales" | "todas" (default: "todas")
  - completada: boolean (opcional)
  - q: string (búsqueda en contenido — para notas)

Response 200: {
  "asignadas": [...],   // es_tarea=true, created_by != me
  "notas": [...],       // es_tarea=false, created_by != me
  "personales": [...]   // created_by == me
}
```

### 4.5 Seller — Crear tarea personal

```
POST /admin/core/crm/vendor-tasks/personal
Headers: Authorization: Bearer {jwt}

Body:
{
  "contenido": "Mi tarea personal",
  "fecha_limite": "2026-04-20T12:00:00Z"  // opcional
}

Response 201: VendorTaskResponse
// vendor_id y created_by se setean al current_user.id
// es_tarea = TRUE siempre
```

### 4.6 Seller — Marcar completada / desmarcar

```
PATCH /admin/core/crm/vendor-tasks/{task_id}/completar
Headers: Authorization: Bearer {jwt}

Body: { "completada": true }

Response 200: VendorTaskResponse actualizado
```

**Regla de autorización:**
- `vendor_id == current_user.id` — el seller solo puede modificar SUS propias tareas
- `tenant_id` debe coincidir — nunca cruzar tenants
- Si `completada` pasa de `false` a `true`: setear `completada_at = NOW()`
- Si vuelve a `false`: limpiar `completada_at = NULL`

### 4.7 Seller — Badge count (pendientes)

```
GET /admin/core/crm/vendor-tasks/pending-count
Headers: Authorization: Bearer {jwt}

Response 200: { "count": 3 }
```

Solo tareas asignadas por admin (`created_by != current_user.id`, `es_tarea = TRUE`, `completada = FALSE`).

---

## 5. Pydantic Models

```python
# orchestrator_service/routes/vendor_tasks_routes.py

class CreateVendorTaskRequest(BaseModel):
    vendor_id: int
    contenido: str = Field(..., min_length=1, max_length=2000)
    es_tarea: bool = False
    fecha_limite: Optional[datetime] = None

class CreatePersonalTaskRequest(BaseModel):
    contenido: str = Field(..., min_length=1, max_length=2000)
    fecha_limite: Optional[datetime] = None

class ToggleCompletadaRequest(BaseModel):
    completada: bool

class VendorTaskResponse(BaseModel):
    id: str
    tenant_id: int
    vendor_id: int
    created_by: int
    created_by_name: Optional[str] = None   # JOIN con users para mostrar "Asignada por {nombre}"
    contenido: str
    es_tarea: bool
    fecha_limite: Optional[datetime] = None
    completada: bool
    completada_at: Optional[datetime] = None
    created_at: datetime

class VendorTasksGroupedResponse(BaseModel):
    asignadas: List[VendorTaskResponse]
    notas: List[VendorTaskResponse]
    personales: List[VendorTaskResponse]

class PendingCountResponse(BaseModel):
    count: int
```

---

## 6. Frontend — Componentes React

### 6.1 Ruta

```
/mis-notas  →  MisNotasView.tsx
```

Registrar en el router principal de `frontend_react/src/App.tsx` (o router equivalente).

### 6.2 Componentes nuevos

```
frontend_react/src/views/
  MisNotasView.tsx              # Vista principal con 3 secciones

frontend_react/src/components/vendor-tasks/
  TareasAsignadasSection.tsx    # Sección 1: tareas del admin
  NotasAdminSection.tsx         # Sección 2: notas del admin (read-only)
  MisTareasSection.tsx          # Sección 3: tareas personales
  TaskCard.tsx                  # Card reutilizable (checkbox, deadline coloring, etc.)
  NewPersonalTaskForm.tsx        # Form para crear tarea personal
  VendorNotesDialog.tsx         # Dialog del admin (admin-only) para crear nota/tarea a un seller
```

### 6.3 Comportamiento por sección

#### Sección 1 — Tareas Asignadas (admin tasks)

- Checkbox para marcar completada (PATCH `/completar`)
- Label "Asignada por {created_by_name}"
- Coloring de deadline:
  - Sin deadline → gris neutro
  - Pendiente con fecha futura → amber (`text-amber-600`)
  - Vencida (fecha pasada + no completada) → rojo (`text-red-600`)
  - Completada → verde con tachado (`text-green-600 line-through`)
- Tareas completadas colapsables con `<details>` (nativo HTML, sin dependencia)
- Ordenadas: primero vencidas, luego por fecha_limite ASC, luego sin fecha

#### Sección 2 — Notas del Admin

- Read-only — sin checkbox
- Searchable: input de búsqueda filtra `contenido` en el cliente (no server-side para la primera versión)
- Ordenadas por `created_at DESC`

#### Sección 3 — Mis Tareas Personales

- Mismo checkbox de completada que sección 1
- Botón "Nueva tarea" → `NewPersonalTaskForm` (inline o modal)
- Sin "Asignada por" — son propias
- Mismo coloring de deadline

### 6.4 VendorNotesDialog (admin-only)

Mostrar desde `SellersView` o desde el panel de detalle de un seller.

```
- Campo: textarea "Contenido" (requerido, max 2000 chars)
- Checkbox: "Es una tarea"
- Date picker: "Fecha límite" (visible solo si "Es una tarea" = true)
- Botón: "Guardar"
```

### 6.5 Badge en Sidebar

```
Sidebar item "Mis Notas" → mostrar badge rojo con número si count > 0
```

- Poll al montar la app: `GET /vendor-tasks/pending-count`
- Actualizar en tiempo real via Socket.IO evento `VENDOR_TASK_ASSIGNED`
- Limpiar badge al marcar todas las tareas como completadas

---

## 7. Integración Socket.IO

Usar el sistema existente en `orchestrator_service/core/socket_notifications.py`.

### Evento nuevo: `VENDOR_TASK_ASSIGNED`

Emitir cuando admin crea una tarea (`es_tarea = TRUE`) para un seller:

```python
await socket_manager.emit_to_user(
    user_id=vendor_id,
    event="VENDOR_TASK_ASSIGNED",
    data={
        "task_id": str(task.id),
        "contenido": task.contenido[:100],  # preview
        "fecha_limite": task.fecha_limite.isoformat() if task.fecha_limite else None,
        "created_by_name": admin_name,
    }
)
```

El frontend escucha este evento en `SocketContext` y:
1. Incrementa el badge counter
2. Muestra un toast: "Nueva tarea asignada por {admin_name}"

### Evento nuevo: `VENDOR_NOTE_CREATED`

Emitir cuando admin crea una nota (`es_tarea = FALSE`) — sin badge, solo toast informativo.

---

## 8. Integración con Sistema de Notificaciones Existente

El sistema de notificaciones de CRM VENTAS (`notification_routes.py`, `seller_notification_service.py`) maneja 4 tipos: conversaciones sin respuesta, leads calientes, follow-ups, y alertas de performance.

Para vendor tasks se agrega un quinto tipo lógico **`vendor_task`** pero NO se almacena en la tabla `notifications` (para mantener separación de concerns). Las vendor tasks tienen su propia tabla y sus propios endpoints. El sistema de badge es independiente.

Si en el futuro se quiere unificar, la extensión natural es agregar `type = 'vendor_task'` a la tabla `notifications` existente.

---

## 9. Escenarios de Aceptación

### SC-01: Admin crea tarea para seller

```
DADO que soy admin autenticado con X-Admin-Token válido
CUANDO POST /vendor-tasks con vendor_id=42, contenido="Llamar al cliente X", es_tarea=true, fecha_limite=mañana
ENTONCES respuesta 201 con la tarea creada
  Y el seller 42 recibe evento Socket.IO VENDOR_TASK_ASSIGNED
  Y el badge del seller se incrementa en 1
```

### SC-02: Admin crea nota (no tarea)

```
DADO que soy admin autenticado
CUANDO POST /vendor-tasks con es_tarea=false
ENTONCES se crea sin fecha_limite (ignorar si se envía)
  Y el seller recibe evento VENDOR_NOTE_CREATED (sin badge)
```

### SC-03: Seller marca tarea como completada

```
DADO que soy seller con vendor_id=42
CUANDO PATCH /vendor-tasks/{task_id}/completar con completada=true
  Y task.vendor_id == 42 Y task.tenant_id == mi tenant
ENTONCES completada=true, completada_at=NOW()
  Y el badge del sidebar se decrementa
  Y la tarea se mueve al bloque colapsado de "Completadas"
```

### SC-04: Seller intenta completar tarea de otro seller

```
DADO que soy seller con vendor_id=42
CUANDO PATCH /vendor-tasks/{task_id}/completar donde task.vendor_id=99
ENTONCES respuesta 403 Forbidden
```

### SC-05: Seller crea tarea personal

```
DADO que soy seller autenticado
CUANDO POST /vendor-tasks/personal con contenido="Preparar presentación"
ENTONCES tarea creada con vendor_id=created_by=mi id, es_tarea=TRUE
  Y aparece en sección "Mis Tareas Personales"
  Y NO genera notificación ni badge (es propia)
```

### SC-06: Seller busca en notas del admin

```
DADO que tengo notas del admin visible en /mis-notas
CUANDO escribo "descuento" en el input de búsqueda
ENTONCES se filtran en cliente las notas que contengan "descuento" (case-insensitive)
  Y las tareas asignadas NO se filtran (son sección separada)
```

### SC-07: Deadline vencida

```
DADO que tengo una tarea asignada con fecha_limite en el pasado y completada=false
CUANDO abro /mis-notas
ENTONCES la tarea aparece con borde rojo y texto rojo en el deadline
  Y aparece primero en el listado de tareas pendientes
```

### SC-08: Badge count multi-tenant

```
DADO que soy seller del tenant_id=5
CUANDO GET /vendor-tasks/pending-count
ENTONCES count refleja SOLO mis tareas pendientes del tenant_id=5
  Y no incluye tareas de otros tenants ni tareas personales
```

---

## 10. Estrategia de Migración desde codexy

codexy es Supabase (PostgreSQL) con RLS. CRM VENTAS es PostgreSQL multi-tenant. La migración de datos existentes (si se decide) requiere:

1. Export de `vendor_notes` de codexy con sus relaciones de usuario
2. Mapeo de UUIDs de Auth0 (codexy) a INTEGER ids de `users` en CRM VENTAS
3. Insertar con `tenant_id` correcto
4. Verificar que `completada_at` se preserve

Para la implementación inicial en CRM VENTAS se parte de tabla vacía — la migración de datos históricos es un paso posterior y opcional.

---

## 11. Archivos a Crear / Modificar

### Backend

| Archivo | Acción |
|---------|--------|
| `orchestrator_service/routes/vendor_tasks_routes.py` | Crear — todos los endpoints |
| `orchestrator_service/main.py` | Modificar — registrar el nuevo router |
| `orchestrator_service/db/migrations/` | Crear — migration SQL para `vendor_tasks` |
| `orchestrator_service/core/socket_notifications.py` | Modificar — agregar `emit_vendor_task_assigned` y `emit_vendor_note_created` |

### Frontend

| Archivo | Acción |
|---------|--------|
| `frontend_react/src/views/MisNotasView.tsx` | Crear |
| `frontend_react/src/components/vendor-tasks/TaskCard.tsx` | Crear |
| `frontend_react/src/components/vendor-tasks/TareasAsignadasSection.tsx` | Crear |
| `frontend_react/src/components/vendor-tasks/NotasAdminSection.tsx` | Crear |
| `frontend_react/src/components/vendor-tasks/MisTareasSection.tsx` | Crear |
| `frontend_react/src/components/vendor-tasks/NewPersonalTaskForm.tsx` | Crear |
| `frontend_react/src/components/vendor-tasks/VendorNotesDialog.tsx` | Crear |
| `frontend_react/src/components/Sidebar.tsx` (o equiv.) | Modificar — agregar item "Mis Notas" con badge |
| `frontend_react/src/App.tsx` (o router) | Modificar — registrar ruta `/mis-notas` |
| `frontend_react/src/context/SocketContext.tsx` | Modificar — escuchar `VENDOR_TASK_ASSIGNED` y `VENDOR_NOTE_CREATED` |
| `frontend_react/src/locales/es.json` | Modificar — strings de i18n |
| `frontend_react/src/locales/en.json` | Modificar — strings de i18n |
| `frontend_react/src/locales/fr.json` | Modificar — strings de i18n |

### Base de Datos

| Archivo | Acción |
|---------|--------|
| `db/init/` o `orchestrator_service/migrations/` | Crear migration `006_vendor_tasks.sql` |

---

## 12. Riesgos y Consideraciones

| Riesgo | Mitigación |
|--------|------------|
| Un seller podría intentar completar tareas de otro seller pasando un `task_id` ajeno | Siempre verificar `vendor_id == current_user.id` en el backend antes del UPDATE |
| Badge desincronizado si el seller tiene múltiples pestañas | Usar Socket.IO para sincronizar; el badge siempre refetch al re-focus de ventana |
| Tareas personales aparecen en vista de admin | La vista admin (`VendorNotesDialog`) filtra `created_by != vendor_id` — solo muestra lo que el admin creó |
| Escalabilidad: seller con cientos de notas | El índice `idx_vendor_tasks_pending` cubre el caso más frecuente; agregar paginación en fase 2 |
| i18n: fechas y labels de deadline | Usar `Intl.DateTimeFormat` con locale del LanguageContext existente |

---

## 13. Dependencias

- Sistema de notificaciones Socket.IO (ya implementado — Sprint 2)
- `users` table con sellers registrados (ya existe)
- `tenants` table (ya existe)
- `SocketContext.tsx` (ya existe — solo agregar event listeners)
- Auth: `get_current_user` y `verify_admin_token` (ya existen en `core/security.py`)

---

## 14. Criterios de Done

- [ ] Migration SQL aplicada y tabla `vendor_tasks` creada en dev y prod
- [ ] Todos los endpoints del spec implementados con tests unitarios
- [ ] Admin puede crear nota y tarea desde `VendorNotesDialog` en `SellersView`
- [ ] Seller ve `/mis-notas` con las 3 secciones correctamente separadas
- [ ] Checkbox de completar funciona y persiste en DB
- [ ] Coloring de deadline correcto (amber / red / green)
- [ ] Badge en sidebar muestra tareas pendientes asignadas
- [ ] Badge se actualiza en tiempo real via Socket.IO
- [ ] Búsqueda en notas filtra correctamente en cliente
- [ ] Tareas completadas colapsables con `<details>`
- [ ] Autorización: seller no puede completar tareas de otro seller (test explícito)
- [ ] Multi-tenant: queries siempre filtradas por `tenant_id`
- [ ] i18n: strings en es.json / en.json / fr.json
- [ ] No hay regresiones en notificaciones existentes (4 tipos previos intactos)
