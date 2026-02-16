# API Reference - CRM Ventas

Referencia de los endpoints del **Orchestrator** (FastAPI) para **CRM Ventas** (Nexus Core). Base URL típica: `http://localhost:8000` en desarrollo o la URL del servicio en producción.

## Prefijos en CRM Ventas

| Prefijo | Contenido |
|---------|-----------|
| **`/auth`** | Login, registro, clínicas, me, profile (público o con JWT). |
| **`/admin/core`** | Rutas administrativas: usuarios, tenants, settings, **chat** (tenants, sessions, messages, read, human-intervention, remove-silence), **stats/summary**, **chat/urgencies**, config/deployment, internal/credentials. Requieren **JWT + X-Admin-Token**. |
| **`/admin/core/crm`** | Módulo CRM: **leads** (CRUD, phone/context), **clients**, **sellers**, **whatsapp/connections**, **templates**, **campaigns**, **agenda/events**. Requieren JWT + X-Admin-Token. |
| **`/chat`** | POST: envío de mensaje al agente IA (usado por WhatsApp Service). |
| **`/health`** | Health check (público). |

## Documentación interactiva (OpenAPI / Swagger)

En la misma base del Orchestrator están disponibles:

| URL | Descripción |
|-----|-------------|
| **[/docs](http://localhost:8000/docs)** | **Swagger UI**: contrato completo, agrupado por tags (Auth, CRM Sales, etc.). Configurar **Bearer** (JWT) y **X-Admin-Token** en *Authorize*. |
| **[/redoc](http://localhost:8000/redoc)** | **ReDoc**: documentación en formato lectura. |
| **[/openapi.json](http://localhost:8000/openapi.json)** | Esquema OpenAPI 3.x en JSON para Postman, Insomnia o generación de clientes. |

Sustituye `localhost:8000` por la URL del Orchestrator en tu entorno.

---

## Índice

1. [Autenticación y headers](#autenticación-y-headers)
2. [Auth (login, registro, perfil)](#auth-público-y-registro)
3. [Configuración de clínica](#configuración-de-clínica-idioma-ui)
4. [Usuarios y aprobaciones](#usuarios-y-aprobaciones)
5. [Sedes (Tenants)](#sedes-tenants)
6. [Chat (admin core)](#chat-admin-core)
7. [Estadísticas y urgencias (admin core)](#estadísticas-y-urgencias-admin-core)
8. [CRM: Leads, clientes, vendedores, agenda](#crm-leads-clientes-vendedores-agenda)
9. [Contexto de lead por teléfono](#contexto-de-lead-por-teléfono)
10. [Pacientes (referencia legacy)](#pacientes)
11. [Turnos (Appointments)](#turnos-appointments)
12. [Profesionales / Vendedores](#profesionales)
13. [Calendario y bloques](#calendario-y-bloques)
14. [Tratamientos](#tratamientos-services)
15. [Otros (health, chat IA)](#otros)

---

## Autenticación y headers

Todas las rutas bajo **`/admin/core/*`** (y **`/admin/core/crm/*`**) exigen:

| Header | Obligatorio | Descripción |
|--------|-------------|-------------|
| **`Authorization`** | Sí | `Bearer <JWT>`. El JWT se obtiene con `POST /auth/login`. |
| **`X-Admin-Token`** | Sí (si está configurado en servidor) | Token estático de infraestructura. El frontend lo inyecta desde `VITE_ADMIN_TOKEN`. Sin este header, el backend responde **401** aunque el JWT sea válido. |

Rutas **públicas** (sin JWT/X-Admin-Token): `GET /auth/clinics`, `POST /auth/register`, `POST /auth/login`, `GET /health`.

---

## Auth (público y registro)

### Listar clínicas (público)
`GET /auth/clinics`

**Sin autenticación.** Devuelve el listado de clínicas para el selector de registro.

**Response:**
```json
[
  { "id": 1, "clinic_name": "Clínica Centro" },
  { "id": 2, "clinic_name": "Sede Norte" }
]
```

### Registro
`POST /auth/register`

Crea usuario con `status = 'pending'`. Para roles `professional` y `secretary` es **obligatorio** enviar `tenant_id`; se crea una fila en `professionals` con `is_active = FALSE` y los datos indicados.

**Payload (campos ampliados):**
- `email`, `password`, `role` (`professional` | `secretary` | `ceo`)
- `first_name`, `last_name`
- **`tenant_id`** (obligatorio si role es professional o secretary)
- `specialty` (opcional; recomendado para professional)
- `phone_number` (opcional)
- `registration_id` / matrícula (opcional)

El backend aplica fallbacks si la tabla `professionals` no tiene columnas `phone_number`, `specialty` o `updated_at` (parches 12d/12e en db.py).

### Login
`POST /auth/login`

**Payload:** `email`, `password` (form/x-www-form-urlencoded o JSON).

**Response (200):**
```json
{
  "access_token": "<JWT>",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@clinica.com",
    "role": "ceo",
    "tenant_id": 1,
    "allowed_tenant_ids": [1, 2]
  }
}
```
El frontend guarda `access_token` y lo envía en `Authorization: Bearer <JWT>` junto con `X-Admin-Token` en rutas `/admin/*`.

### Usuario actual
`GET /auth/me`

Requiere `Authorization: Bearer <JWT>`. Devuelve el usuario autenticado (id, email, role, tenant_id, allowed_tenant_ids).

### Perfil
`GET /auth/profile` — Datos de perfil del usuario (incl. profesional si aplica).  
`PATCH /auth/profile` — Actualizar perfil (campos permitidos según rol).

---

## Configuración de clínica (idioma UI)

### Obtener configuración
`GET /admin/core/settings/clinic`

Devuelve la configuración de la clínica/entidad del tenant resuelto del usuario (nombre, horarios, **idioma de la UI**). Requiere autenticación admin.

**Response:**
- `name`: nombre de la clínica (`tenants.clinic_name`)
- `ui_language`: `"es"` | `"en"` | `"fr"` (por defecto `"en"`). Persistido en `tenants.config.ui_language`.
- `hours_start`, `hours_end`, `time_zone`, etc.

### Actualizar idioma de la plataforma
`PATCH /admin/core/settings/clinic`

Actualiza la configuración de la clínica. Solo se envían los campos a modificar.

### Configuración de despliegue
`GET /admin/core/config/deployment`

Devuelve datos de configuración del despliegue (feature flags, URLs, etc.) para el frontend. Requiere autenticación admin.

**Payload:**
```json
{ "ui_language": "en" }
```
Valores permitidos: `"es"`, `"en"`, `"fr"`. Se persiste en `tenants.config.ui_language` del tenant resuelto.

---

## Usuarios y aprobaciones

Todas las rutas requieren autenticación admin. Solo **CEO** puede aprobar/rechazar usuarios.

### Usuarios pendientes
`GET /admin/core/users/pending`

Lista usuarios con `status = 'pending'` (registrados pero no aprobados). Útil para la vista de Aprobaciones.

### Listar usuarios
`GET /admin/core/users`

Lista usuarios del sistema. Filtrado por tenant según rol (CEO ve todos los suyos; secretaria/profesional solo su tenant).

### Cambiar estado de usuario
`POST /admin/core/users/{user_id}/status`

Aprueba o rechaza un usuario pendiente.

**Payload:** `{ "status": "approved" }` o `{ "status": "rejected" }`.

---

## Sedes (Tenants)

Solo **CEO** puede gestionar sedes. Requieren autenticación admin.

### Listar sedes
`GET /admin/core/tenants`

Devuelve todas las clínicas/sedes del CEO.

### Crear sede
`POST /admin/core/tenants`

**Payload:** Incluye `clinic_name`, `config` (JSON, ej. `calendar_provider`, `ui_language`), etc.

### Actualizar sede
`PUT /admin/core/tenants/{tenant_id}`

Actualiza nombre y/o configuración de la sede.

### Eliminar sede
`DELETE /admin/core/tenants/{tenant_id}`

Elimina la sede (restricciones de integridad según esquema).

---

## Tratamientos (Services)

### Listar Tratamientos
`GET /admin/treatment-types`

Retorna todos los tipos de tratamiento configurados para el tenant. Aislado por `tenant_id`.

**Response:** Lista de objetos con `code`, `name`, `description`, `default_duration_minutes`, `category`, `is_active`, etc.

### Obtener por código
`GET /admin/treatment-types/{code}`

Devuelve un tipo de tratamiento por su `code`.

### Duración por código
`GET /admin/treatment-types/{code}/duration`

Devuelve la duración en minutos del tratamiento (para agendar). Response: `{ "duration_minutes": 30 }`.

### Crear Tratamiento
`POST /admin/treatment-types`

Registra un nuevo servicio clínico.

**Payload:**
```json
{
  "code": "blanqueamiento",
  "name": "Blanqueamiento Dental",
  "description": "Tratamiento estético con láser",
  "default_duration_minutes": 45,
  "min_duration_minutes": 30,
  "max_duration_minutes": 60,
  "complexity_level": "medium",
  "category": "estetica",
  "requires_multiple_sessions": false,
  "session_gap_days": 0
}
```

### Actualizar Tratamiento
`PUT /admin/treatment-types/{code}`

Modifica las propiedades de un tratamiento existente.

**Payload:** (Mismo que POST, todos los campos opcionales)

### Eliminar Tratamiento
`DELETE /admin/treatment-types/{code}`

- Si no tiene citas asociadas: **Eliminación física**.
- Si tiene citas asociadas: **Soft Delete** (`is_active = false`).

## Profesionales

### Listar Profesionales
`GET /admin/professionals`

- **CEO:** devuelve profesionales de **todas** las sedes permitidas (`allowed_ids`).
- **Secretary/Professional:** solo los de su clínica.

**Response:** Lista de profesionales con `id`, `tenant_id`, `name`, `specialty`, `is_active`, `working_hours`, etc. (incluye `phone_number`, `registration_id` cuando existen en BD).

### Profesionales por usuario
`GET /admin/professionals/by-user/{user_id}`

Devuelve las filas de `professionals` asociadas a ese `user_id`. Usado por el modal de detalle y Editar Perfil en Aprobaciones (Personal Activo). Incluye `phone_number`, `registration_id`, `working_hours`, `tenant_id`, etc.

### Crear/Actualizar Profesional
`POST /admin/professionals` | `PUT /admin/professionals/{id}`

Crea o actualiza profesional (tenant_id, nombre, contacto, especialidad, matrícula, working_hours). El backend aplica fallbacks si faltan columnas `phone_number`, `specialty`, `updated_at` en la tabla `professionals`.

### Analíticas por profesional
`GET /admin/professionals/{id}/analytics`

Devuelve métricas del profesional (turnos, ingresos, etc.) para el dashboard. Requiere autenticación admin; filtrado por tenant.

### Bóveda de Credenciales (Internal)
`GET /admin/internal/credentials/{name}`

Obtiene credenciales internas. Requiere header **`X-Internal-Token`** (no JWT). Uso interno entre servicios.

---

## Calendario y bloques

### Connect Sovereign (Auth0 / Google Calendar)
`POST /admin/calendar/connect-sovereign`

Guarda el token de Auth0 cifrado (Fernet) en la tabla `credentials` (category `google_calendar`, por `tenant_id`) y actualiza `tenants.config.calendar_provider` a `'google'` para esa clínica. Requiere `CREDENTIALS_FERNET_KEY` en el entorno.

**Payload:**
```json
{
  "access_token": "<token Auth0>",
  "tenant_id": 1
}
```
- `tenant_id` opcional; si no se envía se usa la clínica resuelta del usuario (CEO puede indicar clínica).

**Response:** `{ "status": "connected", "tenant_id": 1, "calendar_provider": "google" }`

### Bloques de calendario
`GET /admin/calendar/blocks` — Lista bloques (no disponibilidad) del tenant. Params: `professional_id`, fechas si aplica.  
`POST /admin/calendar/blocks` — Crea bloque. Body: `google_event_id`, `title`, `description`, `start_datetime`, `end_datetime`, `all_day`, `professional_id`.  
`DELETE /admin/calendar/blocks/{block_id}` — Elimina un bloque.

### Sincronización (JIT)
`POST /admin/calendar/sync` o `POST /admin/sync/calendar`

Fuerza el mirroring entre Google Calendar y la BD local (bloqueos externos → `google_calendar_blocks`). Suele invocarse al cargar la Agenda.

---

## Chat (admin core)

Todas las rutas de chat están bajo **`/admin/core/chat/*`**. Filtran por `tenant_id`; Human Override y ventana 24h se persisten en la tabla **leads** (columnas `human_handoff_requested`, `human_override_until`).

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/admin/core/chat/tenants` | Clínicas/entidades disponibles para Chats (CEO: todas; otros: una). Response: `[{ "id", "clinic_name" }]`. |
| GET | `/admin/core/chat/sessions?tenant_id=<id>` | Sesiones de chat del tenant (leads con mensajes recientes; incluye `status`, `human_override_until`, `unread_count`). |
| GET | `/admin/core/chat/messages/{phone}?tenant_id=<id>` | Historial de mensajes por teléfono y tenant. |
| PUT | `/admin/core/chat/sessions/{phone}/read` | Marcar conversación como leída. Query: `tenant_id`. Response: `{ "status": "ok" }`. |
| POST | `/admin/core/chat/human-intervention` | Activar/desactivar intervención humana (24h de silencio IA). Body: `phone`, `tenant_id`, `activate` (bool), `duration` (minutos opcional). Actualiza `leads.human_handoff_requested` y `leads.human_override_until`. |
| POST | `/admin/core/chat/remove-silence` | Quitar silencio: vuelve a habilitar respuestas de la IA. Body: `phone`, `tenant_id`. Pone `human_handoff_requested = false`, `human_override_until = null` en el lead. |
| POST | `/admin/core/chat/send` | Enviar mensaje manual desde el panel. Body: `phone`, `tenant_id`, `message`. |

---

## Estadísticas y urgencias (admin core)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/admin/core/stats/summary` | Resumen de métricas CRM para el Dashboard. Query: `range` (opcional, `weekly` \| `monthly`). Response: `ia_conversations`, `ia_appointments`, `active_urgencies`, `total_revenue`, `growth_data` (array por día). |
| GET | `/admin/core/chat/urgencies` | Lista de urgencias/leads recientes para el panel. Response: array de `{ lead_name, phone, urgency_level, reason, timestamp }`. |

---

## CRM: Leads, clientes, vendedores, agenda

Todas las rutas CRM están bajo **`/admin/core/crm/*`**. Requieren autenticación admin; filtrado por `tenant_id`.

- **Leads:** `GET/POST /admin/core/crm/leads`, `GET/PUT/DELETE /admin/core/crm/leads/{lead_id}`, `POST /admin/core/crm/leads/{id}/assign`, `PUT /admin/core/crm/leads/{id}/stage`, `POST /admin/core/crm/leads/{id}/convert-to-client`.
- **Clientes:** `GET/POST /admin/core/crm/clients`, `GET/PUT/DELETE /admin/core/crm/clients/{client_id}`.
- **Vendedores:** `GET /admin/core/crm/sellers`, `GET /admin/core/crm/sellers/by-user/{user_id}`, `PUT /admin/core/crm/sellers/{id}`, `POST /admin/core/crm/sellers`, `GET /admin/core/crm/sellers/{id}/analytics`.
- **Agenda:** `GET/POST /admin/core/crm/agenda/events`, `PUT/DELETE /admin/core/crm/agenda/events/{event_id}`.
- **WhatsApp/Templates/Campaigns:** `GET/POST /admin/core/crm/whatsapp/connections`, `GET /admin/core/crm/templates`, `POST /admin/core/crm/templates/sync`, `GET/POST /admin/core/crm/campaigns`, `POST /admin/core/crm/campaigns/{id}/launch`.

---

## Contexto de lead por teléfono

`GET /admin/core/crm/leads/phone/{phone}/context`

Devuelve el contexto del lead para el panel de Chats (nombre, próximo evento, último evento). Query opcional: `tenant_id_override` (si el usuario puede ver varios tenants).

**Response (200):**
```json
{
  "lead": {
    "id": "uuid",
    "first_name": "Juan",
    "last_name": "Pérez",
    "phone_number": "+54911...",
    "status": "contacted",
    "email": "juan@mail.com"
  },
  "upcoming_event": {
    "id": "uuid",
    "title": "Llamada de seguimiento",
    "date": "2026-02-20T10:00:00",
    "end_datetime": "2026-02-20T10:30:00",
    "status": "scheduled"
  },
  "last_event": {
    "id": "uuid",
    "title": "Reunión inicial",
    "date": "2026-02-10T14:00:00",
    "status": "completed"
  },
  "is_guest": false
}
```

Si no hay lead para ese teléfono en el tenant: `lead: null`, `upcoming_event: null`, `last_event: null`, `is_guest: true`.

## Pacientes

> [!NOTE]
> **CRM Ventas:** En este proyecto el contacto principal es el **lead** (tabla `leads`). El contexto para Chats se obtiene con `GET /admin/core/crm/leads/phone/{phone}/context`. Las rutas siguientes (pacientes, turnos con patient_id) se conservan como referencia para integraciones o specs legacy; el frontend actual usa leads, clients y agenda/events bajo `/admin/core/crm`.

Todas las rutas de pacientes están aisladas por `tenant_id`.

### Listar pacientes
`GET /admin/patients`

**Query params:** `limit`, `offset`, `search` (texto libre). Devuelve lista paginada de pacientes del tenant.

### Alta de Paciente
`POST /admin/patients`

Crea una ficha médica administrativamente. Incluye triaje inicial. Aislado por `tenant_id`.

**Payload (PatientCreate):**
```json
{
  "first_name": "Juan",
  "last_name": "Pérez",
  "phone_number": "+5491112345678",
  "email": "juan@mail.com",
  "dni": "12345678",
  "insurance": "OSDE"
}
```
Campos requeridos: `first_name`, `phone_number`. Opcionales: `last_name`, `email`, `dni`, `insurance`.

### Obtener paciente por ID
`GET /admin/patients/{id}`

Devuelve la ficha del paciente (datos personales, contacto, obra social, etc.).

### Actualizar paciente
`PUT /admin/patients/{id}`

Actualiza datos del paciente. Body: mismos campos que creación (parcial o completo según implementación).

### Eliminar paciente
`DELETE /admin/patients/{id}`

Elimina el paciente del tenant (o soft-delete según esquema).

### Historial clínico (records)
`GET /admin/patients/{id}/records` — Lista notas/registros clínicos del paciente.  
`POST /admin/patients/{id}/records` — Crea una nota clínica. Body: `content`, opcionalmente `odontogram_data`.

### Búsqueda semántica
`GET /admin/patients/search-semantic?q=<texto>`

Búsqueda por texto sobre pacientes del tenant (nombre, teléfono, email, etc.).

### Estado de obra social
`GET /admin/patients/{patient_id}/insurance-status`

Devuelve información de cobertura/obra social del paciente.

### Contexto Clínico del Paciente (legacy)
`GET /admin/patients/phone/{phone}/context` — En CRM Ventas no se usa; en su lugar usar **`GET /admin/core/crm/leads/phone/{phone}/context`** (ver [Contexto de lead por teléfono](#contexto-de-lead-por-teléfono)).

---

## Turnos (Appointments)

Todas las rutas de turnos están aisladas por `tenant_id`. La disponibilidad y reserva usan **calendario híbrido**: si `tenants.config.calendar_provider == 'google'` se usa Google Calendar; si `'local'`, solo BD local (`appointments` + bloques).

### Listar turnos
`GET /admin/appointments`

**Query params:** `start_date`, `end_date` (ISO), `professional_id` (opcional). Devuelve turnos del tenant en el rango.

### Verificar colisiones
`GET /admin/appointments/check-collisions`

Comprueba solapamientos antes de crear/editar. Params: `professional_id`, `start`, `end`, opcional `exclude_appointment_id`.

### Crear turno
`POST /admin/appointments`

**Payload (AppointmentCreate):**
```json
{
  "patient_id": 1,
  "patient_phone": null,
  "professional_id": 2,
  "appointment_datetime": "2026-02-15T10:00:00",
  "appointment_type": "checkup",
  "notes": "Primera visita",
  "check_collisions": true
}
```
`patient_id` o `patient_phone` (para paciente rápido); `professional_id` y `appointment_datetime` obligatorios. `check_collisions` por defecto `true`.

### Actualizar turno
`PUT /admin/appointments/{id}`

Actualiza fecha, profesional, tipo, notas, etc. Respeta calendario (Google o local) según tenant.

### Cambiar estado
`PATCH /admin/appointments/{id}/status` o `PUT /admin/appointments/{id}/status`

Body: `{ "status": "confirmed" }` (o `cancelled`, `completed`, etc., según modelo).

### Eliminar turno
`DELETE /admin/appointments/{id}`

Borra el turno; si hay evento en Google Calendar, se sincroniza la cancelación.

### Próximos slots
`GET /admin/appointments/next-slots`

**Query params:** `professional_id`, `date` (opcional), `limit`. Devuelve los siguientes huecos disponibles para agendar (según calendario híbrido).

---

## Analítica y Estadísticas

### Resumen de Estadísticas (admin core)
`GET /admin/core/stats/summary`

Retorna métricas clave del sistema CRM (conversaciones IA, eventos/reuniones, urgencias, ingresos). Usado por el Dashboard.

**Query Params:** `range` (opcional): `weekly` | `monthly`. Default: `weekly`.

**Response:** `ia_conversations`, `ia_appointments`, `active_urgencies`, `total_revenue`, `growth_data` (array por día).

### Urgencias Recientes (admin core)
`GET /admin/core/chat/urgencies`

Lista de urgencias/leads recientes para el panel del Dashboard. Response: array de objetos con `lead_name`, `phone`, `urgency_level`, `reason`, `timestamp`.

### Resumen de profesionales (analytics)
`GET /admin/core/crm/sellers/{id}/analytics` — Métricas por vendedor (agenda, conversiones). Para listado de vendedores: `GET /admin/core/crm/sellers`.

---

## Otros

### Health
`GET /health`

**Público.** Respuesta: `{ "status": "ok", "service": "orchestrator" }` (o similar). Usado por orquestadores y monitoreo.

### Chat (IA / WhatsApp)
`POST /chat`

Endpoint usado por el **WhatsApp Service** (y pruebas) para enviar mensajes al agente LangChain. Persiste historial en BD. No usa JWT ni X-Admin-Token; la seguridad se gestiona en el servicio que llama (webhook con secret, IP, etc.).

**Payload:** Incluye identificador de conversación (ej. `phone`), `message`, y contexto de tenant/clínica según integración.

---

## Parámetros globales (paginación y filtros)

En rutas de listado administrativas suelen soportarse:
- **`limit`**: Cantidad de registros (default típico: 50).
- **`offset`**: Desplazamiento para paginación.
- **`search`**: Filtro por texto libre cuando aplique.

---

## Códigos de error habituales

| Código | Significado |
|--------|-------------|
| **401** | No autenticado o token inválido. En `/admin/*` suele indicar JWT faltante/inválido o **falta de header `X-Admin-Token`**. |
| **403** | Sin permiso para el recurso (ej. tenant no permitido para el usuario). |
| **404** | Recurso no encontrado (paciente, turno, sede, etc.). |
| **422** | Error de validación (body o query params incorrectos). |
| **500** | Error interno del servidor. |
