# SPEC: Admin — Sistema de Alertas Automáticas por Leads sin Actividad o SLA Vencido

**Ticket:** DEV-42
**Fecha:** 2026-03-28
**Prioridad:** Alta (impacto directo en revenue)
**Esfuerzo:** Medio (3-4 dias)
**Confidence:** 92%
**Depende de:** DEV-39 (activity_events + alerts)

---

## 1. Contexto

DEV-39 creó alertas visuales de leads sin actividad en el panel de actividad. DEV-42 lo extiende con:
- **SLA configurable** por tenant (ej: "primer contacto en <30min", "respuesta en <2h")
- **Notificaciones push automáticas** al vendedor y al CEO cuando un SLA se vence
- **Background job** que verifica SLAs periódicamente
- **Escalamiento automático**: si el vendedor no responde en X tiempo, notifica al CEO

### Estado actual

| Componente | Estado |
|------------|--------|
| `get_inactive_lead_alerts()` en DEV-39 | Existente (leads >2h sin actividad) |
| `seller_notification_service` | Existente |
| APScheduler background jobs | Existente |
| Configuración SLA por tenant | **NO existe** |
| Notificación push al vendedor por SLA | **NO existe** |
| Escalamiento automático al CEO | **NO existe** |
| Vista de configuración de SLAs | **NO existe** |

---

## 2. Requerimientos Técnicos

### 2.1 Backend: Tabla sla_rules

```sql
CREATE TABLE IF NOT EXISTS sla_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    trigger_type VARCHAR(50) NOT NULL, -- 'first_response', 'follow_up', 'status_change'
    threshold_minutes INTEGER NOT NULL, -- tiempo límite
    applies_to_statuses TEXT[], -- estados de lead donde aplica (null = todos)
    applies_to_roles TEXT[], -- roles donde aplica (null = todos)
    escalate_to_ceo BOOLEAN DEFAULT true,
    escalate_after_minutes INTEGER DEFAULT 30, -- tiempo extra antes de escalar
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 2.2 Backend: Endpoints

#### `GET /admin/core/sla-rules` (CEO only)
Lista las reglas SLA del tenant.

#### `POST /admin/core/sla-rules` (CEO only)
Crear regla SLA.

#### `PUT /admin/core/sla-rules/{id}` (CEO only)
Actualizar regla SLA.

#### `DELETE /admin/core/sla-rules/{id}` (CEO only)
Desactivar regla SLA.

#### `GET /admin/core/sla-rules/violations` (CEO only)
Lista violaciones activas de SLA con detalle.

### 2.3 Backend: Background Job

**`sla_checker_job`** — se ejecuta cada 5 minutos:
1. Obtiene todas las reglas SLA activas por tenant
2. Para cada regla, busca leads que la violan
3. Si hay violación nueva: crea `Notification` al vendedor asignado
4. Si la violación supera `escalate_after_minutes`: crea `Notification` al CEO
5. Emite evento WebSocket `team_activity:new_alert`

### 2.4 Frontend: Configuración SLA en ConfigView

Agregar sección "Reglas SLA" en `/configuracion`:
- Lista de reglas con toggle activo/inactivo
- Formulario para crear/editar regla
- Campos: nombre, tipo trigger, umbral minutos, estados aplicables, escalar a CEO

### 2.5 Frontend: Badge en sidebar

Mostrar badge con número de violaciones SLA activas junto al item "Actividad Equipo" en sidebar.

---

## 3. Criterios de Aceptación

### Scenario 1: Crear regla SLA
```gherkin
Given el CEO navega a /configuracion > Reglas SLA
When crea una regla "Primera respuesta < 30 min" con threshold 30
Then la regla aparece en la lista activa
```

### Scenario 2: Notificación automática al vendedor
```gherkin
Given existe la regla "Primera respuesta < 30 min"
And el lead "Juan Pérez" fue asignado a "Tomás" hace 35 minutos
And Tomás no ha realizado ninguna acción sobre ese lead
Then Tomás recibe una notificación push: "SLA vencido: Lead Juan Pérez sin respuesta hace 35 min"
```

### Scenario 3: Escalamiento al CEO
```gherkin
Given la regla tiene escalate_after_minutes = 30
And la violación SLA lleva 65 minutos sin resolverse
Then el CEO recibe notificación: "Escalamiento: Lead Juan Pérez — SLA vencido hace 65 min (vendedor: Tomás)"
```

### Scenario 4: Violaciones activas
```gherkin
Given el CEO navega a /admin/core/sla-rules/violations
Then ve una lista de leads que violan algún SLA
And cada item muestra: lead, vendedor, regla violada, minutos excedidos
```

---

## 4. Fuera de Alcance (v1)
- SLA por tipo de lead source (meta vs orgánico)
- Penalizaciones automáticas (reasignación de lead)
- Historial de violaciones pasadas
- Integración con email para alertas
