# Spec: Desacople clínica/dental – CRM VENTAS single-niche

## Objetivos

- Desacoplar todo lo relacionado con **clínica/dental** y con **VentasLogic** del proyecto CRM VENTAS.
- Dejar CRM VENTAS como **único nicho**: solo CRM de ventas (leads, pipeline, vendedores, agenda, chats).
- El producto debe funcionar igual que si fuera “el proyecto de las clínicas” pero para un CRM de ventas: misma estructura (tenant/sede, auth, agente, frontend), sin multi-nicho ni referencias a dental o VentasLogic.

## Criterios de aceptación

1. **Backend**
   - No se importa ni se monta el módulo `modules.dental`. Solo se carga el nicho `crm_sales`.
   - `niche_type` por defecto en BD y en código es `crm_sales` (no `dental`).
   - En `/chat` (inbound) solo se usa flujo CRM: `ensure_lead_exists`; no existe rama dental ni `ensure_patient_exists`.
   - CORS y nombres de app sin “Dentalogic” ni “VentasLogic”; opcional usar “CRM Ventas” o nombre neutro.
   - Parches/DB: default `niche_type = 'crm_sales'` donde corresponda.

2. **Frontend**
   - No hay rutas ni vistas de dental (agenda dental, pacientes, tratamientos, analytics profesionales, aprobaciones dentales). Las rutas útiles para el CRM son: dashboard, `/crm/agenda`, `/crm/leads`, `/crm/clientes`, `/crm/vendedores`, `/chats`, `/sedes`, `/configuracion`, `/perfil`.
   - Redirecciones: `/agenda` → `/crm/agenda`, `/pacientes` → `/crm/clientes`.
   - Sidebar muestra solo ítems del CRM (un solo “modo”); no selector de nicho dental/CRM.
   - Configuración: sin selector de “Modo de la sede” (dental vs CRM); el producto es solo CRM.
   - i18n: sin “Dentalogic”, “Dental Clinic”, “niche_dental”; título/app unificado “CRM Ventas” (o equivalente). Textos “clínica” reemplazados por “sede” o “entidad” donde aplique.

3. **Identidad y documentación**
   - Documentación y .agent describen el producto como CRM de ventas, single-niche, sin referencias a dental ni VentasLogic.

## Alcance

- **Dentro de:** `CRM VENTAS/` (orchestrator_service, frontend_react, .agent, docs).
- **Fuera de alcance:** No eliminar tablas ni columnas de BD ya desplegadas (p. ej. `niche_type` puede quedar; se usa solo `crm_sales`). El archivo de schema `dentalogic_schema.sql` puede conservar el nombre para no romper despliegues existentes.

## Riesgos

- Tenants existentes con `niche_type = 'dental'` dejarían de tener flujo dental (ya no existe). Asumir que en este producto todos los tenants son CRM o se migran a `crm_sales`.
