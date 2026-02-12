# Checklist de Validación: Transformación Agnóstica

Este documento lista las pruebas críticas para asegurar el éxito de la migración de Dentalogic a Nexus Core CRM.

## 1. Integridad del Core (Agnóstico)
*   [ ] **Login**: Usuario puede loguearse y recibir un JWT válido.
*   [ ] **Tenant Load**: El backend carga correctamente la configuración (`niche_config`) desde la DB.
*   [ ] **Chat WebSocket**: Los mensajes entran y salen vía Socket.IO sin errores, independientemente del nicho.
*   [ ] **Admin Token**: Rutas protegidas siguen rechazando requests sin `X-Admin-Token`.

## 2. Regresión del Nicho Dental (Legacy)
*   [ ] **Sidebar**: Muestra ítems "Agenda", "Pacientes", "Tratamientos".
*   [ ] **Prompt Carga**: El log del backend muestra "Loading prompt: modules/dental/prompts/base_assistant.txt".
*   [ ] **Tools**: El agente puede ejecutar `check_availability` y responde con horarios.
*   [ ] **Vistas**:
    *   La vista de Agenda carga bloques de Google Calendar.
    *   La vista de Pacientes muestra el Odontograma (si aplica).

## 3. Validación del Nicho CRM (Nuevo)
*   [ ] **Sidebar**: Muestra ítems "Leads", "Plantillas", "Campañas". NO muestra "Pacientes".
*   [ ] **Prompt Carga**: El log muestra "Loading prompt: modules/crm_sales/prompts/setter_v1.txt".
*   [ ] **Tools**: El agente puede ejecutar `list_templates`. Si se intenta `check_availability`, debe dar error o no estar disponible.
*   [ ] **Leads**:
    *   `POST /admin/niche/leads` crea un nuevo lead.
    *   El lead aparece en la lista del dashboard.

## 4. Seguridad y Aislamiento
*   [ ] **Cross-Niche**: Un usuario de un tenant dental NO puede acceder a `/admin/niche/leads` (debe recibir 403 o 404).
*   [ ] **Cross-Tenant**: Un usuario del Tenant A no ve los chats del Tenant B.

## 5. Documentación y Código
*   [ ] `README.md` actualizado mencionando la arquitectura modular.
*   [ ] No quedan imports hardcodeados a `modules/dental` dentro de `core/`.
