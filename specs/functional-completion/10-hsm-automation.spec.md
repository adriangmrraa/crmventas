# SPEC F-10: HSM Automation Rules

**Priority:** Media
**Complexity:** Media
**Estado:** Draft
**Fecha:** 2026-04-14

---

## Contexto actual

`MetaTemplatesView.tsx` muestra un log de automatización (tabla de eventos disparados) y un panel lateral con configuración de zona horaria y descripción de reglas de negocio. Actualmente:

- Solo consume `GET /crm/marketing/automation-logs` — logs de lo que ya se ejecutó.
- No tiene UI para CREAR, EDITAR ni DESACTIVAR reglas de automatización.
- El selector de timezone está deshabilitado (`disabled`, `cursor-not-allowed`).
- Los triggers mostrados son solo 3 (`appointment_reminder`, `appointment_feedback`, `lead_recovery`) — el spec pide 5.
- No hay preview de plantilla con sustitución de variables.
- No hay toggle enable/disable por regla.
- El campo `template` de cada log no se muestra (solo trigger + status + timestamp).

El backend en `routes/marketing.py` tiene:
- `GET /crm/marketing/automation-logs` — funcional, devuelve logs con `lead_name`, `trigger_type`, `status`, `created_at`, `error_details`.
- `GET /crm/marketing/automation/rules` — lista reglas actuales.
- `POST /crm/marketing/automation/rules` — actualiza reglas (batch update, no CRUD individual).

El backend en `routes/hsm_templates_routes.py` tiene CRUD completo de plantillas HSM en `/admin/core/crm/hsm-templates`.

`services/marketing/automation_service.py` implementa el motor de automatización con loop cada 15 minutos. Los triggers reales procesados en el servicio deben mapearse a los 5 que requiere este spec.

---

## Requisitos funcionales

### RF-10.1: Lista de reglas de automatización

- Mostrar todas las reglas configuradas para el tenant con: trigger, plantilla asociada, estado (activo/inactivo), última ejecución (`last_run`).
- Triggers soportados:
  1. `appointment_reminder` — Recordatorio de cita (X horas antes)
  2. `appointment_feedback` — Feedback post-cita (X horas después)
  3. `lead_recovery` — Recuperación de lead frío (sin respuesta en X días)
  4. `post_treatment_followup` — Seguimiento post-tratamiento/venta (X días después)
  5. `patient_reactivation` — Reactivación de cliente sin actividad (X días sin contacto)
- Cada regla muestra: nombre del trigger, template name, timing, estado (badge), fecha de último disparo.
- Lista vacía muestra estado empty con CTA para crear primera regla.

### RF-10.2: Crear / editar regla de automatización

- Formulario/drawer con:
  - **Trigger type**: select con los 5 opciones de RF-10.1
  - **Template**: select de plantillas disponibles del tenant (de `GET /admin/core/crm/hsm-templates`, status `APPROVED`)
  - **Timing**: campo numérico + unidad (horas / días) con label contextual según trigger:
    - `appointment_reminder`: "horas ANTES de la cita"
    - `appointment_feedback`: "horas DESPUÉS de la cita"
    - `lead_recovery`: "días sin respuesta"
    - `post_treatment_followup`: "días después del cierre"
    - `patient_reactivation`: "días de inactividad"
  - **Condiciones opcionales**: filtro por estado del lead (select multi), filtro por fuente (META_ADS, ORGANIC, etc.)
  - **Activo**: toggle on/off
- Validación: no pueden existir dos reglas con el mismo trigger activo simultáneamente.
- Al guardar: `POST /admin/core/automation-rules` (crear) o `PUT /admin/core/automation-rules/{id}` (editar).

### RF-10.3: Toggle enable/disable por regla

- Switch en la tarjeta de cada regla que cambia `is_active` via `PATCH /admin/core/automation-rules/{id}`.
- Feedback visual inmediato (optimistic update + confirmación del servidor).
- Regla desactivada muestra badge "Pausada" en gris.

### RF-10.4: Preview de plantilla con sustitución de variables

- Al seleccionar una template en el form de regla, mostrar preview inline con variables en color destacado.
- Variables `{{1}}`, `{{2}}`, etc. reemplazadas por placeholders descriptivos según posición (ej: `{{1}} → [Nombre del lead]`).
- Preview en burbuja estilo WhatsApp.

### RF-10.5: Logs de automatización — tabla completa

- Columnas: Lead/Paciente, Trigger, Plantilla enviada, Estado, Detalle de error, Timestamp.
- Estados con colores: `sent` → violeta, `failed` → rojo, `delivered` → verde, `read` → púrpura.
- Fila expandible al hacer click para ver `error_details` completo (si status = `failed`).
- Filtro por estado (select) y por trigger (select).
- Paginación: 50 por página, botón "Cargar más".

### RF-10.6: Selector de timezone funcional

- El select de timezone debe habilitarse y guardar via `PUT /admin/core/automation-rules/timezone` o equivalente en settings del tenant.
- Opciones mínimas: Buenos Aires (GMT-3), México (GMT-6), Madrid (GMT+1), Bogotá (GMT-5), Miami (GMT-5).
- El timezone seleccionado afecta a cuándo se disparan las automatizaciones (el backend usa `ZoneInfo` — ya importado en `automation_service.py`).

---

## Contratos de API

### GET `/crm/marketing/automation-logs`

**Query params:**
- `limit`: int (default 50, max 200)
- `offset`: int (default 0)
- `status`: `sent` | `failed` | `delivered` | `read` (opcional)
- `trigger_type`: string (opcional)

**Respuesta:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "lead_name": "Juan Pérez",
      "trigger_type": "appointment_reminder",
      "template_name": "recordatorio_llamada",
      "status": "delivered",
      "created_at": "2026-04-14T10:30:00Z",
      "error_details": null
    },
    {
      "id": 2,
      "lead_name": "María López",
      "trigger_type": "lead_recovery",
      "template_name": "apertura_reactivacion_frio",
      "status": "failed",
      "created_at": "2026-04-14T09:15:00Z",
      "error_details": "YCloud: number not in WhatsApp"
    }
  ],
  "total": 87,
  "timestamp": "2026-04-14T11:00:00Z"
}
```

**Nota:** el campo `template_name` no existe actualmente en `automation_logs` — debe agregarse como JOIN con `meta_templates` en la query del `AutomationService.get_automation_logs()`.

### GET `/crm/marketing/automation/rules`

**Respuesta:**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "trigger_type": "appointment_reminder",
      "template_id": "uuid",
      "template_name": "recordatorio_llamada",
      "timing_value": 24,
      "timing_unit": "hours",
      "conditions": { "lead_statuses": ["interested", "negotiation"] },
      "is_active": true,
      "last_run": "2026-04-13T22:00:00Z",
      "created_at": "2026-01-15T10:00:00Z"
    }
  ]
}
```

### POST `/admin/core/automation-rules`

**Body:**
```json
{
  "trigger_type": "lead_recovery",
  "template_id": "uuid-of-template",
  "timing_value": 3,
  "timing_unit": "days",
  "conditions": {
    "lead_statuses": ["contacted", "interested"],
    "lead_sources": ["META_ADS"]
  },
  "is_active": true
}
```

**Respuesta:** `201 Created` con la regla creada.

### PUT `/admin/core/automation-rules/{id}`

**Body:** mismos campos que POST, todos opcionales.

### DELETE `/admin/core/automation-rules/{id}`

**Respuesta:** `204 No Content`.

### PATCH `/admin/core/automation-rules/{id}` (toggle)

**Body:** `{ "is_active": false }`

**Respuesta:** `200 OK` con la regla actualizada.

---

## Endpoints faltantes en el backend

Los siguientes endpoints existen en la spec pero NO están implementados en el backend actual (solo existe `GET` y `POST` batch en `marketing.py`):

| Endpoint | Método | Estado |
|----------|--------|--------|
| `/admin/core/automation-rules` | GET | Existe en `marketing.py` como `/crm/marketing/automation/rules` — verificar prefijo |
| `/admin/core/automation-rules` | POST | Parcial — existe `POST /crm/marketing/automation/rules` pero es batch update |
| `/admin/core/automation-rules/{id}` | PUT | NO EXISTE — crear |
| `/admin/core/automation-rules/{id}` | DELETE | NO EXISTE — crear |
| `/admin/core/automation-rules/{id}` | PATCH | NO EXISTE — crear |

Los nuevos endpoints deben agregarse en un nuevo router o en `admin_routes.py`. Seguir el patrón de `verify_admin_token` + `get_resolved_tenant_id` + `audit_access`.

---

## Modelo de datos requerido

La tabla `automation_rules` debe existir con:

```sql
CREATE TABLE IF NOT EXISTS automation_rules (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   INTEGER NOT NULL REFERENCES tenants(id),
    trigger_type VARCHAR(50) NOT NULL,
    template_id  UUID REFERENCES meta_templates(id),
    timing_value INTEGER NOT NULL DEFAULT 24,
    timing_unit  VARCHAR(10) NOT NULL DEFAULT 'hours', -- 'hours' | 'days'
    conditions   JSONB DEFAULT '{}',
    is_active    BOOLEAN NOT NULL DEFAULT true,
    last_run     TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, trigger_type)
);
```

Verificar que esta tabla exista en el schema actual. Si usa otra estructura, adaptar.

---

## Escenarios de prueba

**Escenario 1 — Listar reglas vacías:**
- `GET /admin/core/automation-rules` → lista vacía
- Vista muestra empty state: "Sin reglas configuradas — Crear primera regla"

**Escenario 2 — Crear regla válida:**
- POST con `trigger_type: "appointment_reminder"`, `template_id` válido, `timing_value: 24`
- Respuesta 201 con regla creada
- La regla aparece en la lista con badge "Activa"

**Escenario 3 — Crear regla duplicada (mismo trigger):**
- POST con `trigger_type: "appointment_reminder"` cuando ya existe una activa
- Backend responde `409 Conflict`: "Ya existe una regla activa para este trigger"
- Frontend muestra error inline en el form

**Escenario 4 — Toggle desactivar regla:**
- PATCH `/{id}` con `{ "is_active": false }`
- La regla muestra badge "Pausada"
- El motor de automatización omite esta regla en su próximo ciclo

**Escenario 5 — Preview de template:**
- Seleccionar template `recordatorio_llamada` (3 variables)
- Preview muestra: "Hola [Nombre del lead], te recuerdo que tenemos una llamada agendada para [Fecha] a las [Hora]. ¿Confirmamos?"
- Variables destacadas en color violeta

**Escenario 6 — Logs con error:**
- Fila con `status: "failed"` → expandir fila
- Muestra `error_details` completo: "YCloud: number not in WhatsApp"
- Badge rojo visible sin expandir

**Escenario 7 — Filtrar logs:**
- Filtro por `status: "failed"` → solo muestra logs fallidos
- Filtro combinado `trigger_type: "lead_recovery"` + `status: "sent"` → resultados correctos

---

## Dependencias

- `GET /admin/core/crm/hsm-templates` debe devolver templates con status `APPROVED` para el select del form.
- `AutomationService` en `services/marketing/automation_service.py` debe leer de `automation_rules` en lugar de tener reglas hardcodeadas.
- El motor de automatización (loop cada 15 min) debe respetar `is_active = false`.
- Timezone configurado en la regla (o en settings del tenant) debe usarse en los cálculos de timing del `AutomationService`.
