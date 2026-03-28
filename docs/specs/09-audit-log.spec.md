# SPEC: Admin — Log de Auditoría Completo por Lead y por Vendedor

**Ticket:** DEV-40
**Fecha:** 2026-03-28
**Prioridad:** Alta
**Esfuerzo:** Medio (3-4 dias)
**Confidence:** 96%
**Depende de:** DEV-39 (activity_events table)

---

## 1. Contexto

DEV-39 creó la tabla `activity_events` y un feed de actividad en tiempo real. DEV-40 extiende esto con una vista de auditoría detallada que permite al admin:
- Ver TODO el historial de acciones sobre un lead específico (timeline)
- Ver TODO el historial de acciones de un vendedor específico
- Filtrar por rango de fechas, tipo de evento, vendedor, lead
- Exportar el log a CSV

### Estado actual

| Componente | Estado |
|------------|--------|
| Tabla `activity_events` (DEV-39) | Existente |
| `activity_service.get_feed()` con filtros | Existente |
| Vista por lead (timeline de un lead) | **NO existe** |
| Vista por vendedor (historial de un vendedor) | **NO existe** |
| Export CSV del log | **NO existe** |
| Registros de login/logout/settings | **NO se registran** |

---

## 2. Requerimientos Técnicos

### 2.1 Backend: Nuevos endpoints

#### `GET /admin/core/team-activity/audit/by-lead/{lead_id}`
Timeline completa de un lead: cambios de estado, notas, asignaciones, mensajes.

#### `GET /admin/core/team-activity/audit/by-seller/{user_id}`
Historial completo de acciones de un vendedor.

#### `GET /admin/core/team-activity/audit/export`
Export CSV con los mismos filtros del feed. Header: `Content-Type: text/csv`.

### 2.2 Backend: Registrar más tipos de evento

Agregar `record_event` en:
- Login exitoso → `user_login`
- Crear lead (módulo CRM) → `lead_created`
- Asignación manual de seller → `lead_assigned`
- Envío de mensaje chat → `chat_message_sent`

### 2.3 Frontend: Vista AuditLogView

- Ruta: `/crm/auditoria` (CEO only)
- Tabs: "General" | "Por Lead" | "Por Vendedor"
- Tab General: feed completo con filtros avanzados + botón exportar CSV
- Tab Por Lead: buscador de lead → muestra timeline vertical
- Tab Por Vendedor: selector de vendedor → muestra historial cronológico
- Componente reutilizable: `AuditTimeline.tsx`

---

## 3. Criterios de Aceptación

### Scenario 1: Timeline de un lead
```gherkin
Given el CEO navega a /crm/auditoria y selecciona tab "Por Lead"
When busca el lead "Juan Pérez" y lo selecciona
Then ve una timeline vertical con todas las acciones sobre ese lead
And cada item muestra: quién, qué, cuándo
And las acciones están ordenadas de más reciente a más antigua
```

### Scenario 2: Historial de un vendedor
```gherkin
Given el CEO selecciona tab "Por Vendedor" y elige "Tomás García"
Then ve todas las acciones que Tomás ha realizado
And puede filtrar por tipo de acción y rango de fechas
```

### Scenario 3: Export CSV
```gherkin
Given el CEO tiene filtros activos en el tab "General"
When hace click en "Exportar CSV"
Then se descarga un archivo CSV con las columnas: fecha, vendedor, tipo, lead, detalle
And solo contiene los eventos que coinciden con los filtros activos
```

### Scenario 4: Acceso restringido
```gherkin
Given un usuario con rol "setter"
When intenta acceder a /crm/auditoria
Then es redirigido al dashboard
```

---

## 4. Fuera de Alcance (v1)
- Registros de cambios en configuración del tenant
- Logs de acceso a la API (ya existe en system_events)
- Comparativa entre vendedores en vista audit
