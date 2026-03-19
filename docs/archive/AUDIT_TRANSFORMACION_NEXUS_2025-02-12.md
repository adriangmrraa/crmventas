# Informe de Auditoría: Transformación Dentalogic → Nexus Core

**Fecha:** 2025-02-12  
**Workflow:** Audit (detección de drift)  
**SSOT:** `docs/transformacion.md` + `docs/transformacion/01_inventario_dominio_dental.md`, `02_nucleo_agnostico_propuesta.md`, `03_config_nicho_diseno.md`

---

## 1. Resumen ejecutivo

- **Backend:** En gran parte implementado según los tres primeros prompts y los diseños 01–03. Hay **drift** en puntos concretos (tools CRM no registrados, prefijo de rutas CRM duplicado, dental con menos tools de las especificadas).
- **Frontend:** **No está construido** para el nicho CRM. Solo existe el shell preparado (Sidebar con filtro por `niche_type`, AuthContext con `niche_type`). Faltan todas las vistas y rutas CRM (leads, templates, agents, analytics).

**Respuesta directa:**

- **¿El backend ya está todo implementado?**  
  **No del todo.** La base está: `niche_type`, módulos dental/crm_sales, registry de tools, prompt por nicho, tabla `leads` y rutas CRM. Pero faltan: registrar las tools de CRM en el registry, corregir prefijo de rutas CRM y (opcional) completar tools dentales en el provider.

- **¿Queda construir todo el frontend?**  
  **Sí.** Para el nicho CRM queda construir todo el frontend: rutas `/crm/*`, vistas de Leads, Chats (reutilizar o adaptar), Templates, Agentes/Vendedores y Analíticas de ventas.

---

## 2. Comparativa Backend vs Spec

### 2.1 Núcleo agnóstico (Doc 02)

| Criterio | Estado | Notas |
|----------|--------|--------|
| Carpeta `core/` con lógica agnóstica | ✅ Match | `core/` existe: agent (executor_factory, prompt_loader), context, niche_manager, security, services/chat_service, tools (ToolRegistry). |
| Auth, tenants, usuarios, chat (tablas/infra) | ✅ Match | `auth_routes`, `admin_routes` (core), `db.py`, ChatService resuelve sessions por niche (patients vs leads). |
| main.py como entrypoint | ✅ Match | `main.py` en raíz de orchestrator_service; carga NicheManager y `get_agent_executor(tenant_id)`. |
| Módulos pluggables por nicho | ✅ Match | `modules/dental/` y `modules/crm_sales/` con routes; NicheManager carga router por `modules.<niche>.routes`. |

### 2.2 Configuración de nicho (Doc 03)

| Criterio | Estado | Notas |
|----------|--------|--------|
| Nicho por tenant en BD | ✅ Match | Parche 17: columna `tenants.niche_type` (default `'dental'`). |
| Agente con tools según nicho | ⚠️ Drift | Solo el nicho `dental` está registrado en `tool_registry` (`modules/dental/tools_provider.py`). Para `crm_sales`, `tool_registry.get_tools('crm_sales', tenant_id)` no tiene provider → solo devuelve herramientas globales. Las tools en `niches/crm_sales/sales_tools.py` no se registran en ningún `modules/crm_sales/tools_provider.py`. |
| System prompt por nicho | ✅ Match (parcial) | `prompt_loader.load_prompt` para dental con contexto; crm_sales usa string fijo en `main.py` ("Sos un asistente de ventas inteligente."). No hay plantilla en `modules/crm_sales/prompts/`. |
| API resources CRM (leads, etc.) | ✅ Match | Tablas `leads`, `whatsapp_connections`, `templates`, `campaigns` (Parche 16). `modules/crm_sales/routes.py`: CRUD leads, assign, stage. |
| Rutas de API por nicho | ⚠️ Drift | Router CRM tiene `prefix="/crm_sales"` y NicheManager monta con `prefix=f"/niche/{niche_type}"` → rutas quedan `/niche/crm_sales/crm_sales/leads`. Prefijo duplicado; lo esperable sería `/niche/crm_sales/leads`. |

### 2.3 Inventario y herramientas (Docs 01 y 03)

| Criterio | Estado | Notas |
|----------|--------|--------|
| Tabla `leads` y índices | ✅ Match | Parche 16: `leads` con `tenant_id`, `phone_number`, status, etc.; `idx_leads_tenant_phone`, `idx_leads_seller`. |
| Chat sessions por nicho | ✅ Match | `ChatService.get_chat_sessions(tenant_id)` usa `niche_type` y devuelve pacientes (dental) o leads (crm_sales). |
| Auth devuelve niche_type | ✅ Match | `auth_routes` incluye `niche_type` en la respuesta de login/registro (desde `tenants`). |
| Tools dentales en provider | ⚠️ Drift | `dental_tools_provider` solo devuelve `check_availability` y `book_appointment`. El diseño 03 lista también: list_professionals, list_services, list_my_appointments, cancel_appointment, reschedule_appointment, triage_urgency, derivhumano. Esas tools pueden existir en `modules/dental/tools.py` pero no están incluidas en el provider. |

---

## 3. Comparativa Frontend vs Spec

| Criterio (Doc 03 – frontend_routes crm_sales) | Estado | Notas |
|-----------------------------------------------|--------|--------|
| `/`, `/crm/leads`, `/crm/leads/:id`, `/crm/chats`, `/crm/templates`, `/crm/agents`, `/crm/analytics` | ❌ No implementado | En `App.tsx` solo hay rutas dentales/genéricas (agenda, pacientes, chats, tratamientos, aprobaciones, sedes, configuracion). No existe ninguna ruta bajo `/crm/*` ni vistas para Leads, Templates, Agentes ni Analíticas CRM. |
| Shell / menú según nicho | ✅ Parcial | `Sidebar.tsx` filtra ítems por `user.niche_type` y `item.niche`; `AuthContext` tiene `niche_type`. No hay ítems de menú específicos para CRM (ej. "Leads", "Templates") ni rutas que apunten a ellos. |

Conclusión: **el frontend del nicho CRM está por construir** (vistas + rutas + llamadas a la API CRM).

---

## 4. Lógica no pedida / ruido

- No se detecta lógica relevante que contradiga la especificación. La coexistencia de `niches/crm_sales/sales_tools.py` con `modules/crm_sales/` es una duplicidad de ubicación de tools CRM (deberían estar expuestas vía `modules/crm_sales/tools_provider.py` y, si se quiere, reutilizar las definiciones de `niches/`).

---

## 5. Veredicto

- **Backend:** **Drift moderado.** Funciona el flujo por nicho (dental con tools y prompt; crm_sales con prompt fijo pero sin tools de CRM registradas). API CRM de leads existe y está montada bajo `/niche/crm_sales/...` con prefijo duplicado.
- **Frontend:** **Drift total** para el nicho CRM: no hay implementación de las vistas/rutas CRM descritas en el diseño.

---

## 6. Acciones correctivas sugeridas

**Estado post-implementación (Autonomy 2025-02-12):**  
✅ (1) y (2) aplicados. ✅ (3) Parche 18 añadido en db.py para `stage_id`. ✅ (4) Frontend CRM: rutas `/crm/leads`, `/crm/leads/:id`, vistas LeadsView y LeadDetailView, ítem Sidebar "Leads" para nicho `crm_sales`, login con `setTenantId`.

1. **Registrar tools CRM en el registry** ✅
   - Crear `modules/crm_sales/tools_provider.py` que devuelva las tools de `niches/crm_sales/sales_tools.py` (o moverlas a `modules/crm_sales/tools.py`) y llamar a `tool_registry.register_provider("crm_sales", crm_sales_tools_provider)`.
   - Asegurar que ese módulo se importe al arranque (igual que `modules.dental.tools_provider` en `main.py`).

2. **Corregir prefijo de rutas CRM**
   - En `modules/crm_sales/routes.py`, cambiar el router a `prefix=""` (o a `/`) para que las rutas queden como `/niche/crm_sales/leads`, `/niche/crm_sales/leads/{id}`, etc.

3. **Opcional – Completar tools dentales en el provider**
   - Incluir en `dental_tools_provider` todas las tools listadas en el spec (list_professionals, list_services, list_my_appointments, cancel_appointment, reschedule_appointment, triage_urgency, derivhumano) si ya existen en el código dental.

4. **Construir frontend CRM**
   - Añadir rutas en `App.tsx`: p.ej. `/crm/leads`, `/crm/leads/:id`, `/crm/templates`, `/crm/agents`, `/crm/analytics` (y reutilizar o adaptar `/chats` para CRM).
   - Crear vistas (LeadsView, LeadDetailView, TemplatesView, etc.) y ítems de menú en Sidebar para el nicho `crm_sales` que apunten a esas rutas.
   - Consumir la API bajo `/niche/crm_sales/...` (o la URL definitiva tras corregir el prefijo) con el mismo patrón de auth (tenant_id, tokens) que el resto del frontend.

---

*Auditoría generada según `.agent/workflows/audit.md`. SSOT: documentación en `docs/transformacion*.md`.*
