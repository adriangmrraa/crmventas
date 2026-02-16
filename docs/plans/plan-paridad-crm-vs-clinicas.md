# Plan de implementación: Paridad CRM VENTAS vs CLINICASV1.0

**Origen:** [VERIFICACION_SALUD_CRM_VS_CLINICAS.md](../VERIFICACION_SALUD_CRM_VS_CLINICAS.md)  
**Objetivo:** Implementar paso a paso todo lo documentado como faltante para que CRM VENTAS funcione con la misma completitud que Clínicas B1.0.  
**Alcance:** Base de datos → Backend (admin_routes, crm_sales, ChatService) → Frontend (ChatsView, DashboardView).

---

## Criterios de aceptación (resumen)

- Dashboard carga KPIs y lista de urgencias/leads calientes sin 404.
- Chats: marcar leído, activar humano 24h y quitar silencio funcionan (endpoints + persistencia en `leads`).
- Panel de contexto en Chats muestra datos del lead (y próxima reunión si aplica) vía endpoint CRM.
- Tabla `leads` tiene columnas `human_handoff_requested` y `human_override_until`.
- ChatService devuelve estado human override en las sesiones para el frontend.

---

## Fase 0 – Base de datos (parche en leads)

| Paso | Acción | Archivo | Verificación |
|------|--------|---------|--------------|
| 0.1 | Añadir **Parche 25** en `_run_evolution_pipeline`: columnas en `leads` → `human_handoff_requested BOOLEAN DEFAULT FALSE`, `human_override_until TIMESTAMPTZ DEFAULT NULL`. Usar bloque `DO $$ ... IF NOT EXISTS (information_schema.columns) ... ALTER TABLE leads ADD COLUMN ...` para cada columna. | `orchestrator_service/db.py` | Reiniciar backend y comprobar que no hay error al conectar; opcional: `SELECT column_name FROM information_schema.columns WHERE table_name='leads' AND column_name IN ('human_handoff_requested','human_override_until');` (debe devolver 2 filas). |
| 0.2 | (Opcional) Si se usa `core.utils.normalize_phone`, asegurar que las búsquedas por teléfono en leads usen la misma normalización. | — | Revisar llamadas a `normalize_phone` en los nuevos endpoints. |

**Comando de verificación sugerido (tras levantar backend):**  
`curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health` → 200.

---

## Fase 1 – ChatService: estado human override en sesiones

| Paso | Acción | Archivo | Verificación |
|------|--------|---------|--------------|
| 1.1 | En `_get_crm_sessions`, añadir al SELECT: `l.human_handoff_requested`, `l.human_override_until`. Incluir en el dict de cada sesión: `status`: `'silenced'` si `human_override_until` es no nulo y > now, sino `'active'`; `human_override_until`: ISO string o null. Mantener `tenant_id` en cada ítem si el frontend lo usa. | `orchestrator_service/core/services/chat_service.py` | GET `/admin/core/chat/sessions?tenant_id=1` con token; respuesta debe incluir por sesión `status` y `human_override_until`. |
| 1.2 | (Opcional) Simplificar `get_chat_sessions` a solo CRM: usar `COALESCE(niche_type,'crm_sales')` y llamar solo a `_get_crm_sessions`, eliminando rama dental si se desea. | `orchestrator_service/core/services/chat_service.py` | Misma verificación que 1.1. |

---

## Fase 2 – Backend: endpoints de Chat en admin_routes

| Paso | Acción | Archivo | Verificación |
|------|--------|---------|--------------|
| 2.1 | Implementar **PUT /admin/core/chat/sessions/{phone}/read**: query param `tenant_id`, depender de `get_allowed_tenant_ids`. Si `tenant_id` no permitido → 403. Respuesta `{"status":"ok","phone":"...","tenant_id":...}`. | `orchestrator_service/admin_routes.py` | `curl -X PUT "http://localhost:8000/admin/core/chat/sessions/+123456/read?tenant_id=1" -H "Authorization: Bearer <JWT>" -H "X-Admin-Token: <ADMIN>"` → 200 y JSON. |
| 2.2 | Implementar **POST /admin/core/chat/human-intervention**: body `HumanInterventionToggle` (phone, tenant_id, activate, duration opcional). Si `activate`: UPDATE leads SET human_handoff_requested=TRUE, human_override_until=NOW()+duration WHERE tenant_id=X AND phone_number=normalize(phone). Si no activate: SET human_handoff_requested=FALSE, human_override_until=NULL. Usar `emit_appointment_event("HUMAN_OVERRIDE_CHANGED", ...)` si existe en app.state. Respuesta con status activated/deactivated y until si aplica. | `orchestrator_service/admin_routes.py` | Llamar con activate true y false; comprobar en BD que leads queda actualizado. |
| 2.3 | Implementar **POST /admin/core/chat/remove-silence**: body `{ "phone", "tenant_id" }`. UPDATE leads SET human_handoff_requested=FALSE, human_override_until=NULL WHERE tenant_id=X AND phone_number=normalize(phone). Emitir evento HUMAN_OVERRIDE_CHANGED si aplica. Respuesta `{"status":"removed",...}`. | `orchestrator_service/admin_routes.py` | Misma verificación que 2.2. |

**Referencia:** En CLINICASV1.0 los endpoints equivalentes están en `admin_routes.py` (put read ~653, human-intervention ~666, remove-silence ~713). En CRM se actualiza la tabla `leads` en lugar de `patients`.

---

## Fase 3 – Backend: Dashboard (stats/summary y chat/urgencies)

| Paso | Acción | Archivo | Verificación |
|------|--------|---------|--------------|
| 3.1 | Implementar **GET /admin/core/stats/summary**: query param `range` (weekly|monthly), depender de `verify_admin_token` y `get_resolved_tenant_id`. Métricas CRM sugeridas: (1) conversaciones IA = COUNT(DISTINCT from_number) en chat_messages en el rango; (2) reuniones/eventos = COUNT(*) en seller_agenda_events en el rango; (3) active_urgencies = 0 o COUNT leads con criterio “caliente”; (4) total_revenue = 0 o lógica si hay tabla de ingresos; (5) growth_data = por día, ia_referrals y completed_events. Respuesta JSON con ia_conversations, ia_appointments (o ia_events), active_urgencies, total_revenue, growth_data. | `orchestrator_service/admin_routes.py` | DashboardView carga sin 404; datos coherentes en UI. |
| 3.2 | Implementar **GET /admin/core/chat/urgencies**: query param `limit` opcional (default 10), depender de `verify_admin_token` y `get_resolved_tenant_id`. En CRM puede devolver array vacío `[]` o lista de “leads calientes” (ej. leads con status 'interested' o última interacción reciente). Formato de ítem: id, lead_name (o patient_name por compatibilidad), phone, urgency_level, reason, timestamp. | `orchestrator_service/admin_routes.py` | GET con token → 200 y array; DashboardView no rompe. |

**Referencia:** CLINICASV1.0 stats/summary ~820, chat/urgencies ~975 en admin_routes.py.

---

## Fase 4 – Backend: contexto de lead por teléfono

| Paso | Acción | Archivo | Verificación |
|------|--------|---------|--------------|
| 4.1 | Implementar **GET /admin/core/crm/leads/phone/{phone}/context**: query param `tenant_id` (o tenant del usuario resuelto). Buscar lead por tenant_id + normalize(phone). Si no hay lead, devolver `{ "lead": null, "upcoming_event": null, "is_guest": true }`. Si hay lead: lead (id, first_name, last_name, phone_number, status, ...), próxima reunión/evento desde seller_agenda_events (donde lead_id = lead.id o por teléfono si se guarda) con start_datetime >= NOW() ORDER BY start_datetime LIMIT 1. Respuesta: lead, last_event (opcional), upcoming_event, is_guest. | `orchestrator_service/modules/crm_sales/routes.py` o `admin_routes.py` | GET con phone y tenant_id → 200; ChatsView podrá consumir este endpoint. |
| 4.2 | Asegurar que la ruta esté montada bajo el prefijo que usa el frontend: si el frontend llama a `/admin/core/crm/leads/phone/:phone/context`, el router de crm_sales debe exponer `GET /leads/phone/{phone}/context` con prefix `/admin/core/crm`. | `orchestrator_service/main.py` + `modules/crm_sales/routes.py` | La URL completa sea exactamente la que usará ChatsView. |

---

## Fase 5 – Frontend: ChatsView contexto lead

| Paso | Acción | Archivo | Verificación |
|------|--------|---------|--------------|
| 5.1 | En `fetchPatientContext`, cambiar URL de `GET /admin/patients/phone/${phone}/context` a `GET /admin/core/crm/leads/phone/${phone}/context`. Pasar `tenant_id_override` o `tenant_id` según lo que espere el backend. | `frontend_react/src/views/ChatsView.tsx` | Abrir Chats, seleccionar conversación; panel de contexto carga sin 404. |
| 5.2 | Ajustar el tipo/estructura de la respuesta si el contrato difiere del patient context: p. ej. renombrar `patient` a `lead`, `upcoming_appointment` a `upcoming_event`. Actualizar el componente que muestra el contexto para usar lead (nombre, estado, próxima reunión). | `frontend_react/src/views/ChatsView.tsx` | Panel muestra nombre del lead, estado y próxima cita/reunión si existe. |

---

## Fase 6 – Verificación integral y documentación

| Paso | Acción | Archivo | Verificación |
|------|--------|---------|--------------|
| 6.1 | Recorrer flujos: Login → Dashboard (stats + urgencias) → Chats → seleccionar sesión → ver contexto → marcar leído → activar humano → quitar silencio. Comprobar que no hay 404 ni errores en consola. | — | Prueba manual o checklist. |
| 6.2 | Actualizar VERIFICACION_SALUD_CRM_VS_CLINICAS.md: marcar como implementado los ítems de la sección 6 y actualizar el checklist de la sección 7 (Chat: marcar leído, human intervention, remove silence, contexto contacto, Dashboard). | `docs/VERIFICACION_SALUD_CRM_VS_CLINICAS.md` | Documento refleja estado “OK” en los puntos cerrados. |
| 6.3 | (Opcional) Añadir a API_REFERENCE.md los nuevos endpoints con método, ruta, params y cuerpo. | `docs/API_REFERENCE.md` | Documentación al día. |

---

## Orden de ejecución recomendado

1. **Fase 0** (DB)  
2. **Fase 1** (ChatService)  
3. **Fase 2** (endpoints chat: read, human-intervention, remove-silence)  
4. **Fase 3** (stats/summary, chat/urgencies)  
5. **Fase 4** (leads/phone/{phone}/context)  
6. **Fase 5** (ChatsView)  
7. **Fase 6** (verificación y docs)

---

## Referencias de archivos (CRM VENTAS)

| Qué | Ruta |
|-----|------|
| Parches DB | `orchestrator_service/db.py` (lista `patches` en `_run_evolution_pipeline`) |
| ChatService | `orchestrator_service/core/services/chat_service.py` |
| Admin routes | `orchestrator_service/admin_routes.py` |
| CRM routes | `orchestrator_service/modules/crm_sales/routes.py` |
| Main (mount routers) | `orchestrator_service/main.py` |
| ChatsView | `frontend_react/src/views/ChatsView.tsx` |
| DashboardView | `frontend_react/src/views/DashboardView.tsx` |
| Verificación | `docs/VERIFICACION_SALUD_CRM_VS_CLINICAS.md` |

---

## Comandos de verificación rápidos

```bash
# Backend health
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health

# Stats (requiere JWT + X-Admin-Token)
curl -s "http://localhost:8000/admin/core/stats/summary?range=weekly" -H "Authorization: Bearer <JWT>" -H "X-Admin-Token: <ADMIN>"

# Urgencies
curl -s "http://localhost:8000/admin/core/chat/urgencies" -H "Authorization: Bearer <JWT>" -H "X-Admin-Token: <ADMIN>"

# Contexto lead (requiere tenant_id en query)
curl -s "http://localhost:8000/admin/core/crm/leads/phone/+351123456789/context?tenant_id=1" -H "Authorization: Bearer <JWT>" -H "X-Admin-Token: <ADMIN>"
```

---

*Plan generado a partir de VERIFICACION_SALUD_CRM_VS_CLINICAS.md. Proyecto: CRM VENTAS.*
