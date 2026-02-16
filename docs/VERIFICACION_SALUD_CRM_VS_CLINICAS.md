# Verificación de salud: CRM VENTAS vs CLINICASV1.0

**Objetivo:** Garantizar que CRM VENTAS tenga la misma lógica y nivel de completitud que Clínicas B1.0 (CLINICASV1.0), adaptado al dominio CRM (entidades, vendedores, clientes, leads). Este documento registra el estado actual y **lo que falta** para que CRM funcione de forma óptima y paritaria.

**Fecha:** 2026-02-16  
**Alcance:** Backend (orchestrator_service), Frontend (frontend_react), Base de datos.

---

## 1. Mapeo de conceptos (Clínicas → CRM)

| Clínicas B1.0        | CRM VENTAS     | Notas                                      |
|----------------------|----------------|--------------------------------------------|
| Clínicas / Sedes      | Entidades      | Misma tabla `tenants`; naming en UI.       |
| Profesionales        | Vendedores     | Misma tabla `professionals`; roles setter/closer. |
| Pacientes            | Clientes       | Tabla `clients` en CRM; flujo lead→cliente.|
| (no existe)          | Leads          | Tabla `leads`; página dedicada en CRM.     |
| Turnos (appointments)| Eventos agenda | CRM: `agenda/events` (crm_sales).          |
| Urgencias (chat)     | Opcional       | CRM puede tener "leads calientes" o lista vacía. |

---

## 2. Backend – Endpoints y rutas

### 2.1 Comparativa de prefijos

- **CLINICASV1.0:** auth (`/auth`), admin (`/admin` con rutas directas: `/admin/users`, `/admin/chat/...`, `/admin/tenants`, `/admin/patients`, `/admin/professionals`, `/admin/appointments`, `/admin/stats/summary`, `/admin/chat/urgencies`, etc.).
- **CRM VENTAS:** auth (`/auth`), admin core (`/admin/core`), CRM bajo `/admin/core/crm` (módulo crm_sales) y `/niche/crm_sales` (NicheManager).

### 2.2 Endpoints que CRM VENTAS ya tiene (alineados con Clínicas)

| Funcionalidad        | Clínicas                      | CRM VENTAS                         | Estado   |
|----------------------|-------------------------------|------------------------------------|----------|
| Login/Register       | POST /auth/login, /auth/register | Igual                              | OK       |
| Listar sedes         | GET /auth/clinics             | GET /auth/clinics                  | OK       |
| Usuarios pendientes  | GET /admin/users/pending      | GET /admin/core/users/pending     | OK       |
| Listar usuarios      | GET /admin/users              | GET /admin/core/users             | OK       |
| Aprobar/rechazar     | POST /admin/users/{id}/status | POST /admin/core/users/{id}/status| OK       |
| Chat: tenants        | GET /admin/chat/tenants       | GET /admin/core/chat/tenants      | OK       |
| Chat: sesiones       | GET /admin/chat/sessions      | GET /admin/core/chat/sessions     | OK       |
| Chat: mensajes       | GET /admin/chat/messages/{phone} | GET /admin/core/chat/messages/{phone} | OK   |
| Chat: enviar         | POST /admin/chat/send        | POST /admin/core/chat/send        | OK       |
| Tenants CRUD         | GET/POST/PUT/DELETE /admin/tenants | GET/POST/PUT/DELETE /admin/core/tenants | OK |
| Settings clínica     | GET/PATCH /admin/settings/clinic | GET/PATCH /admin/core/settings/clinic | OK   |
| Config deployment    | GET /admin/config/deployment  | GET /admin/core/config/deployment | OK       |
| Credenciales internas| GET /admin/internal/credentials/{name} | GET /admin/core/internal/credentials/{name} | OK |
| Leads CRUD           | —                             | /admin/core/crm/leads             | OK (solo CRM) |
| Clientes CRUD        | (patients)                    | /admin/core/crm/clients           | OK       |
| Vendedores            | (professionals)               | /admin/core/crm/sellers           | OK       |
| Agenda eventos       | (appointments)                | /admin/core/crm/agenda/events     | OK       |

### 2.3 Endpoints que FALTABAN en CRM VENTAS (estado tras implementación)

| Endpoint que llama el frontend              | Uso                    | Estado |
|--------------------------------------------|------------------------|--------|
| **GET /admin/core/stats/summary**          | DashboardView (KPIs)   | Implementar en admin_routes o en crm_sales. Debe devolver métricas CRM: conversaciones IA, reuniones/eventos, “urgencias”/leads calientes (opcional), ingresos si aplica, growth_data. |
| **GET /admin/core/chat/urgencies**         | DashboardView (lista urgencias) | Implementar. En CRM puede ser lista vacía o “leads calientes” (por ejemplo por status o última interacción). |
| **PUT /admin/core/chat/sessions/{phone}/read** | ChatsView (marcar leído) | Implementar en admin_routes. Puede ser solo `{"status":"ok"}` si el estado “leído” es solo frontend. |
| **POST /admin/core/chat/human-intervention**  | ChatsView (activar humano 24h) | ✅ Implementado en admin_routes; actualiza **leads** (human_handoff_requested, human_override_until). |
| **POST /admin/core/chat/remove-silence**   | ChatsView (quitar silencio IA) | ✅ Implementado en admin_routes; actualiza **leads**. |
| **GET /admin/core/crm/leads/phone/{phone}/context** | ChatsView (panel contexto contacto) | ✅ Implementado en modules/crm_sales/routes.py; devuelve lead, upcoming_event, last_event, is_guest. ChatsView actualizado. |

---

## 3. Frontend – Rutas y llamadas API

### 3.1 Rutas de pantalla (CRM ya adaptado)

- Dashboard, Leads, Clientes, Agenda CRM, Chats, Vendedores, Sedes/Entidades, Configuración, Perfil, Aprobaciones (staff) están cubiertas en App y Sidebar para CRM.

### 3.2 Llamadas API (estado tras implementación)

| Archivo           | Llamada actual                               | Estado |
|-------------------|----------------------------------------------|--------|
| DashboardView.tsx | GET /admin/core/stats/summary                | ✅ Endpoint implementado. |
| DashboardView.tsx | GET /admin/core/chat/urgencies               | ✅ Endpoint implementado. |
| ChatsView.tsx     | GET /admin/core/crm/leads/phone/${phone}/context | ✅ Endpoint implementado; ChatsView usa LeadContext (lead, upcoming_event, last_event). |
| ChatsView.tsx     | PUT /admin/core/chat/sessions/${phone}/read | ✅ Endpoint implementado. |
| ChatsView.tsx     | POST /admin/core/chat/human-intervention     | ✅ Endpoint implementado. |
| ChatsView.tsx     | POST /admin/core/chat/remove-silence        | ✅ Endpoint implementado. |

El resto de vistas CRM (Leads, LeadDetail, Clients, ClientDetail, Sellers, CrmAgendaView, Config, Clinics, Login, UserApproval, Profile) usan rutas que existen en el backend.

---

## 4. Base de datos – Columnas necesarias para Chat (human override)

En Clínicas, el human override y “remove silence” se persisten en la tabla **patients**:

- `human_handoff_requested BOOLEAN`
- `human_override_until TIMESTAMPTZ`

En CRM VENTAS las sesiones de chat se resuelven por **leads** (ChatService._get_crm_sessions). Para que human-intervention y remove-silence funcionen igual:

- La tabla **leads** debe tener las mismas columnas (o equivalentes):
  - `human_handoff_requested BOOLEAN DEFAULT FALSE`
  - `human_override_until TIMESTAMPTZ DEFAULT NULL`
- Añadir un **parche de migración** en `db.py` (o migración SQL) que agregue estas columnas a `leads` si no existen.
- Los nuevos endpoints **POST /admin/core/chat/human-intervention** y **POST /admin/core/chat/remove-silence** deben actualizar la tabla **leads** (por `tenant_id` + `phone_number`) en lugar de `patients`.

Además, para que el frontend pueda mostrar estado “humano activo” / “silenciado” en la lista de sesiones, **ChatService.get_chat_sessions** (o _get_crm_sessions) debería devolver algo como `status`, `human_override_until` por sesión, leyendo de `leads`.

---

## 5. ChatService y single-niche

- En CRM VENTAS, `core/services/chat_service.py` sigue usando `niche_type` y `_get_dental_sessions` / `_get_crm_sessions`. Con proyecto solo CRM:
  - Se puede simplificar a **solo _get_crm_sessions** y eliminar la rama dental, o dejar el if y asegurar que `niche_type` sea siempre `crm_sales`.
  - Si se añaden `human_handoff_requested` y `human_override_until` a `leads`, las consultas de sesiones deben incluir estos campos para que el frontend muestre correctamente el estado de “humano activo” / “silenciado”.

---

## 6. Resumen de tareas (estado tras implementación)

### Backend (orchestrator_service)

1. **GET /admin/core/stats/summary**  
   Implementar con métricas CRM (conversaciones, eventos/reuniones, opcional “leads calientes”, growth_data, ingresos si aplica).

2. **GET /admin/core/chat/urgencies**  
   Implementar; en CRM puede devolver array vacío o lista de “leads calientes” según criterio de negocio.

3. **PUT /admin/core/chat/sessions/{phone}/read**  
   Implementar (aunque sea solo respuesta `{"status":"ok"}` si el “leído” es solo en frontend).

4. **POST /admin/core/chat/human-intervention** — ✅ Implementado; actualiza **leads**.

5. **POST /admin/core/chat/remove-silence** — ✅ Implementado; actualiza **leads**.

6. **GET /admin/core/crm/leads/phone/{phone}/context** — ✅ Implementado en modules/crm_sales/routes.py.

### Frontend (frontend_react)

7. **ChatsView.tsx**  
   - Cambiar la llamada de contexto de `/admin/patients/phone/${phone}/context` al nuevo endpoint de contexto de **lead** (p. ej. `/admin/core/crm/leads/phone/${phone}/context`).
   - Ajustar el tipo/estructura de la respuesta si el contrato es distinto al de “patient context” (nombres de campos, estructura).

### Base de datos

8. **Tabla leads** — ✅ Parche 25 en db.py: human_handoff_requested, human_override_until.

9. **ChatService (_get_crm_sessions)** — ✅ Incluye status, human_override_until por sesión.

---

## 7. Checklist de paridad funcional (Clínicas vs CRM)

| Área              | Clínicas B1.0     | CRM VENTAS        | Estado      |
|-------------------|-------------------|--------------------|-------------|
| Auth (login, register, me, profile) | Sí        | Sí                 | OK          |
| Sedes/Tenants CRUD                  | Sí        | Sí (entidades)     | OK          |
| Configuración (idioma, sede)        | Sí        | Sí                 | OK          |
| Usuarios y aprobaciones            | Sí        | Sí (vendedores/staff) | OK       |
| Chat: listar sesiones              | Sí        | Sí (por leads)     | OK          |
| Chat: mensajes y enviar            | Sí        | Sí                 | OK          |
| Chat: marcar leído                 | Sí        | Sí (admin_routes)   | OK          |
| Chat: human intervention           | Sí        | Sí (leads + admin_routes) | OK   |
| Chat: remove silence               | Sí        | Sí (leads + admin_routes) | OK   |
| Chat: contexto contacto (panel)    | Paciente  | Lead (leads/phone/context + ChatsView) | OK |
| Dashboard (stats + urgencias)      | Sí        | Sí (stats/summary + chat/urgencies) | OK |
| CRUD “persona de contacto”         | Pacientes | Leads + Clientes   | OK          |
| CRUD “staff”                       | Profesionales | Vendedores      | OK          |
| Agenda / turnos                    | Appointments | Agenda eventos  | OK          |
| Específico CRM                     | —         | Leads, pipeline    | OK          |

---

## 8. Conclusión

Tras la implementación del plan de paridad:

1. Los **6 endpoints** están implementados (stats/summary, chat/urgencies, chat/sessions/read, human-intervention, remove-silence, GET /admin/core/crm/leads/phone/{phone}/context).
2. La tabla **leads** tiene las columnas de human override (Parche 25) y **ChatService** expone status y human_override_until en las sesiones.
3. **ChatsView** usa el endpoint de contexto de lead y el tipo LeadContext (lead, upcoming_event, last_event).

CRM VENTAS queda alineado en lógica y capacidades con Clínicas B1.0 en los flujos equivalentes, adaptado al dominio CRM (entidades, vendedores, clientes, leads).

---

## Plan de implementación

Para abordar paso a paso las tareas anteriores, ver: **[docs/plans/plan-paridad-crm-vs-clinicas.md](plans/plan-paridad-crm-vs-clinicas.md)**.

---

*Documento generado en el marco de la verificación de salud CRM vs Clínicas. Proyecto: CRM VENTAS.*
