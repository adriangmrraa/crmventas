# Plan de implementación: Backend listo + UI CRM funcional

**Objetivo:** Dejar el backend listo y construir la UI mínima del CRM de ventas para verla funcional.

**SSOT:** `docs/AUDIT_TRANSFORMACION_NEXUS_2025-02-12.md` + `docs/transformacion/03_config_nicho_diseno.md`

---

## Backend

1. **Registrar tools CRM en el registry**
   - Crear `orchestrator_service/modules/crm_sales/tools_provider.py` que importe las tools de `niches/crm_sales/sales_tools.py` y llame a `tool_registry.register_provider("crm_sales", crm_sales_tools_provider)`.
   - En `main.py`, importar el módulo al arranque (ej. `import modules.crm_sales.tools_provider`) para que se ejecute el registro.

2. **Corregir prefijo de rutas CRM**
   - En `modules/crm_sales/routes.py`, cambiar el router de `prefix="/crm_sales"` a `prefix=""` para que las rutas queden como `/niche/crm_sales/leads`, etc.

3. **Compatibilidad esquema leads con stage_id**
   - Añadir en `db.py` un parche que agregue la columna `stage_id` a `leads` si no existe (las rutas CRM la usan en SELECT/RETURNING).

---

## Frontend

4. **Rutas y vistas CRM**
   - En `App.tsx`, añadir rutas: `/crm/leads`, `/crm/leads/:id` (y opcional `/crm` redirect a `/crm/leads`).
   - Crear `frontend_react/src/modules/crm_sales/views/LeadsView.tsx` (listado de leads con tabla/cards, filtro por status, llamada a GET `/niche/crm_sales/leads`).
   - Crear `frontend_react/src/modules/crm_sales/views/LeadDetailView.tsx` (detalle de un lead por id, GET/PUT `/niche/crm_sales/leads/:id`).

5. **Sidebar y menú CRM**
   - En `Sidebar.tsx`, añadir ítems de menú para nicho `crm_sales`: "Leads" (path `/crm/leads`), visible solo cuando `user.niche_type === 'crm_sales'`.

6. **API client**
   - Usar el `api` (axios) existente con baseURL ya configurada; las llamadas serán `api.get('/niche/crm_sales/leads')`, etc. Asegurar que en login se guarde `niche_type` y `tenant_id` en el perfil y que se establezca `X-Tenant-ID` en storage si hace falta para el backend.

7. **Scroll Isolation**
   - Aplicar en las nuevas vistas CRM el patrón: contenedor principal `h-screen overflow-hidden`, área de contenido `flex-1 min-h-0 overflow-y-auto`.

---

## Verificación

- Backend: arrancar orchestrator y comprobar que GET `/niche/crm_sales/leads` (con JWT + X-Admin-Token) responde 200.
- Frontend: `npm run build` sin errores; en navegador con usuario de nicho crm_sales, ver menú Leads y listado de leads.
