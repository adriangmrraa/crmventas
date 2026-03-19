# 03 – Diseño de configuración de nicho (dental vs CRM ventas)

Este documento responde al **Prompt 3** de `docs/transformacion.md`:

> Diseña (en documento .md o spec) un módulo o esquema de ‘configuración de nicho’ que permita definir por tenant o por producto: (a) nombre del nicho (dental, crm_sales, etc.), (b) lista de tools del agente (nombre y descripción), (c) system prompt base del agente, (d) conjunto de rutas de API (o nombres de recursos) que ese nicho expone. No escribas código; solo el diseño.

---

## 1. Objetivo de la configuración de nicho

Queremos que **cada tenant** (clínica actual o empresa de ventas futura) tenga asociado un **nicho funcional** que determine:

- Cómo se comporta el agente (persona, tono, flujo de conversación).
- Qué herramientas (tools LangChain) están disponibles para ese tenant.
- Qué recursos de API administra (pacientes/turnos/profesionales vs leads/deals/agents).
- Qué vistas del frontend se muestran tras el login (Agenda/Pacientes vs Leads/CRM).

Todo esto sin duplicar infraestructura (auth, chat, sockets, migraciones).

---

## 2. Modelo conceptual de “NicheConfig”

### 2.1 Entidad conceptual

Propuesta de estructura abstracta (no SQL, solo diseño):

```json
{
  "id": "dental",
  "label": "Dentalogic (Clínicas dentales)",
  "agent_tools": [
    "list_professionals",
    "list_services",
    "check_availability",
    "book_appointment",
    "list_my_appointments",
    "cancel_appointment",
    "reschedule_appointment",
    "triage_urgency",
    "derivhumano"
  ],
  "system_prompt_key": "dental_assistant_v1",
  "api_resources": [
    "patients",
    "professionals",
    "appointments",
    "treatment_types",
    "calendar",
    "analytics_professionals"
  ],
  "frontend_routes": [
    "/",
    "/agenda",
    "/pacientes",
    "/pacientes/:id",
    "/chats",
    "/tratamientos",
    "/analytics/professionals"
  ]
}
```

Para CRM ventas (`crm_sales`):

```json
{
  "id": "crm_sales",
  "label": "Nexus Core CRM (Vendedores/Setters)",
  "agent_tools": [
    "lead_scoring",
    "list_templates",
    "book_sales_meeting",
    "derivhumano"
  ],
  "system_prompt_key": "sales_setter_v1",
  "api_resources": [
    "leads",
    "sales_agents",
    "deals_meetings",
    "templates",
    "connections",
    "analytics_sales"
  ],
  "frontend_routes": [
    "/",
    "/crm/leads",
    "/crm/leads/:id",
    "/crm/chats",
    "/crm/templates",
    "/crm/agents",
    "/crm/analytics"
  ]
}
```

---

## 3. Dónde se almacena la configuración de nicho

### 3.1 Por tenant (recomendado)

Aprovechando `tenants.config` (JSONB ya existente), se puede añadir:

```json
{
  "ui_language": "es",
  "calendar_provider": "local",
  "niche": "dental"
}
```

o bien:

```json
{
  "ui_language": "en",
  "calendar_provider": "local",
  "niche": "crm_sales"
}
```

Esto permite:

- Que distintas clínicas/empresas en el mismo despliegue usen nichos distintos.
- Cambiar el nicho de un tenant (migración controlada) sin tocar código.

### 3.2 Catálogo global de nichos

Además del campo por tenant, se puede definir un **catálogo global** en código o en un JSON de configuración, por ejemplo:

- Archivo `orchestrator_service/core/config/niches.json` **o**
- Un diccionario en `core/config_core.py`.

Ejemplo:

```json
{
  "dental": {
    "system_prompt_key": "dental_assistant_v1",
    "tools_module": "orchestrator_service.niches.dental.agent_tools_dental",
    "api_router_module": "orchestrator_service.niches.dental.api_dental",
    "frontend_namespace": "dental"
  },
  "crm_sales": {
    "system_prompt_key": "sales_setter_v1",
    "tools_module": "orchestrator_service.niches.crm_sales.sales_tools",
    "api_router_module": "orchestrator_service.niches.crm_sales.api_crm",
    "frontend_namespace": "crm"
  }
}
```

---

## 4. Selección dinámica de tools del agente por nicho

### 4.1 Resolución en el backend (orchestrator_service)

En `POST /chat`:

1. Resolver `tenant_id` a partir de `to_number` (ya implementado).
2. Leer `tenants.config.niche` (por defecto `"dental"` si no está definido).
3. Según el niche:
   - Cargar la lista de tools correspondiente (p.ej. `DENTAL_TOOLS` o `CRM_SALES_TOOLS`).
   - Cargar el system prompt apropiado (p.ej. `build_system_prompt_dental` vs `build_system_prompt_sales`).
4. Invocar `create_agent_executor(...)` con `tools` y `system_prompt` adecuados.

### 4.2 Ejemplo de mapeo conceptual

- `niche == "dental"` → tools:  
  `list_professionals`, `list_services`, `check_availability`, `book_appointment`, `list_my_appointments`, `cancel_appointment`, `reschedule_appointment`, `triage_urgency`, `derivhumano`.

- `niche == "crm_sales"` → tools:  
  `lead_scoring`, `list_templates`, `book_sales_meeting`, `derivhumano`.

---

## 5. System prompt base por nicho

### 5.1 Claves de system prompt

En lugar de hardcodear el prompt en `main.py`, se define un catálogo:

- `dental_assistant_v1`: persona actual (asistente clínico dental) ya documentada en `06_ai_prompt_template.md` y `build_system_prompt`.
- `sales_setter_v1`: nueva persona para nicho CRM (Senior Sales Setter), tal como describe el Prompt Maestro 3:
  - Persuasivo, orientado a conversión, voseo argentino.
  - Usa `lead_scoring`, `book_sales_meeting`, `list_templates`.
  - “Service-First”: define oferta y califica al lead antes de ofrecer agenda.

### 5.2 Ubicación de los prompts

Opciones:

- Archivos Markdown en `orchestrator_service/niches/<niche>/prompts/*.md` cargados por un `prompt_loader`.
- Constantes de texto en módulos Python, referenciadas por clave (`system_prompt_key`).

En cualquier caso, el agente siempre recibe el prompt correcto según `tenant.niche`.

---

## 6. Recursos de API por nicho

### 6.1 Dental

- Recursos: `patients`, `professionals`, `appointments`, `treatment_types`, `calendar`, `analytics_professionals`.  
- Endpoints bajo `/admin/...` ya existentes (ver `API_REFERENCE.md`).

### 6.2 CRM ventas

- Recursos nuevos: `leads`, `sales_agents`, `deals_meetings`, `templates`, `connections`, `analytics_sales`.  
- Se expondrían típicamente como:
  - `/admin/leads`, `/admin/leads/{id}`.
  - `/admin/sales-agents`, `/admin/sales-agents/{id}`.
  - `/admin/deals`, `/admin/deals/{id}`.
  - `/admin/templates`, `/admin/connections`.
  - `/admin/analytics/sales/summary`.

La elección final de rutas (prefijo `/admin/dental/...` vs `/admin/crm/...` o uso de `niche` implícito por tenant) se detalla en el Prompt 4 (Contrato de API agnóstico vs por nicho).

---

## 7. Rutas de frontend por nicho

### 7.1 Dental (actual)

- `/`, `/agenda`, `/pacientes`, `/pacientes/:id`, `/chats`, `/tratamientos`, `/analytics/professionals`, `/aprobaciones`, `/sedes`, `/configuracion`.

### 7.2 CRM ventas (propuesta)

- `/` – Dashboard de ventas.
- `/crm/leads`, `/crm/leads/:id` – Lista/detalle de leads.
- `/crm/chats` – Conversaciones por vendedor/tenant.
- `/crm/templates` – Gestión de plantillas aprobadas.
- `/crm/agents` – Vendedores/Setters.
- `/crm/analytics` – KPIs de ventas.

El shell (Layout, Sidebar, AuthContext, LanguageContext) se mantiene; solo varía el **subárbol de rutas** montado según `tenant.niche`.

---

## 8. Resumen

- La **configuración de nicho** se basa en:
  - Un campo por tenant: `tenants.config.niche` (ej. `"dental"`, `"crm_sales"`).
  - Un catálogo global de definiciones de nicho (`id`, `system_prompt_key`, módulos de tools y routers, rutas frontend).
- El backend elige herramientas y prompt del agente por nicho antes de cada `/chat`.
- El frontend monta vistas distintas (dental vs CRM) dentro del mismo App Shell.

Este diseño completa el Prompt 3 y sirve como base para los prompts siguientes (4: contrato de API agnóstico vs por nicho; 5: tools parametrizables; 6: system prompt por nicho; 7: frontend shell/vistas por nicho).+
