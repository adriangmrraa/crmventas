# Tasks F-04: Configuration Page — 8 Tabs Funcionales

**Spec:** `04-configuration-complete.spec.md`
**Design:** `design/design-F04.md`
**Fecha:** 2026-04-14

---

## Fase 1: Verificacion de backend (prerequisito)

### T-04.01: Verificar endpoints existentes
- [ ] Leer `company_settings_routes.py` — confirmar GET/PUT de company settings con `business_name`
- [ ] Leer `meta_connect.py` o `meta_auth.py` — confirmar endpoint de status de conexion Meta
- [ ] Leer `notification_routes.py` — confirmar si GET/PUT de notification settings global existen
- [ ] Leer `health_routes.py` — confirmar que retorna version/uptime
- [ ] Verificar si `PATCH /admin/core/settings/security` existe
- [ ] Leer `CalComSettings.tsx` completamente — determinar si es funcional o placeholder
- **Archivos:** multiples en `orchestrator_service/routes/`
- **Criterio:** documento de gaps actualizado, se sabe exactamente que falta

### T-04.02: Crear endpoints faltantes de notificaciones (si necesario)
- [ ] Si no existen: crear `GET /admin/core/notifications/settings` (scope tenant)
- [ ] Si no existen: crear `PUT /admin/core/notifications/settings` (scope tenant)
- [ ] Modelo: `{ email_notifications: bool, push_notifications: bool, desktop_notifications: bool }`
- [ ] Proteger con `verify_admin_token` + `get_resolved_tenant_id`
- **Archivos:** `orchestrator_service/routes/notification_routes.py`
- **Criterio:** GET carga y PUT guarda preferencias a nivel tenant

---

## Fase 2: Tab General (Tab 1)

### T-04.03: Campo nombre de empresa
- [ ] Agregar input "Nombre de empresa" al Tab General
- [ ] Cargar valor inicial desde `GET /admin/core/settings/company` campo `business_name`
- [ ] Boton "Guardar nombre" llama a `PUT /admin/core/settings/company` con `{ business_name }`
- [ ] Solo visible si rol === 'ceo'
- [ ] Toast de exito al guardar
- [ ] Mantener selector de idioma existente sin cambios
- **Archivos:** `frontend_react/src/views/ConfigView.tsx`
- **Criterio:** CEO puede editar nombre de empresa, otros roles solo ven idioma

---

## Fase 3: Tab YCloud (Tab 2)

### T-04.04: Modal de confirmacion en delete
- [ ] Reemplazar `window.confirm()` por `<Modal />` al eliminar credencial YCloud
- [ ] Texto: "Eliminar esta credencial? Esta accion desconectara WhatsApp."
- [ ] Botones: "Cancelar" (cierra modal) y "Eliminar" (ejecuta DELETE)
- [ ] Estado: `deleteModalOpen` + `credentialToDelete`
- **Archivos:** `frontend_react/src/views/ConfigView.tsx`
- **Criterio:** modal se abre al click delete, elimina solo si confirma

---

## Fase 4: Tab Meta (Tab 3)

### T-04.05: Estado de conexion Meta
- [ ] Al montar tab: llamar a endpoint de status Meta (determinar en T-04.01)
- [ ] Si conectado: chip verde "Conectado" + nombre de cuenta
- [ ] Si no conectado: chip rojo "No conectado"
- [ ] Mantener URL de webhook visible y copiable (ya funciona)
- [ ] Boton "Ir a Integraciones" que navega a `/crm/integraciones` via `useNavigate()`
- [ ] NO duplicar logica de OAuth/wizard aqui — solo estado + navegacion
- **Archivos:** `frontend_react/src/views/ConfigView.tsx`
- **Criterio:** estado de conexion visible, boton navega correctamente

---

## Fase 5: Tab Mantenimiento (Tab 5)

### T-04.06: Botones de sync y cache
- [ ] Boton "Sincronizar base de datos": llama a `POST /admin/core/maintenance/sync-db`
- [ ] Si retorna 404: deshabiliatar boton y mostrar tooltip "Proximamente"
- [ ] Boton "Limpiar cache de sesiones": llama a `POST /admin/core/maintenance/clear-cache`
- [ ] Misma logica de 404
- [ ] Loading spinner durante ejecucion, toast al completar
- [ ] Mantener "Limpiar media" existente sin cambios
- **Archivos:** `frontend_react/src/views/ConfigView.tsx`
- **Criterio:** botones visibles, manejan 404 gracefully

### T-04.07: Informacion del sistema
- [ ] Seccion "Informacion del sistema" al final del tab Mantenimiento
- [ ] Llamar a `GET /health` al montar
- [ ] Mostrar: version del backend, uptime (si disponible), timestamp
- [ ] Si endpoint no responde: mostrar "No disponible"
- **Archivos:** `frontend_react/src/views/ConfigView.tsx`
- **Criterio:** info del sistema visible si endpoint responde

---

## Fase 6: Tab Notificaciones (Tab 6)

### T-04.08: Implementar toggles de notificaciones
- [ ] Reemplazar placeholder "Proximamente" por contenido real
- [ ] 3 toggles: email_notifications, push_notifications, desktop_notifications
- [ ] Cargar estado inicial desde GET endpoint (T-04.02)
- [ ] Descripcion debajo de cada toggle
- [ ] Boton "Guardar preferencias" con PUT al endpoint
- [ ] Loading state durante carga y guardado
- [ ] Toast de exito al guardar
- **Archivos:** `frontend_react/src/views/ConfigView.tsx`
- **Criterio:** tab funcional con toggles reales, no muestra "Proximamente"

---

## Fase 7: Tab Seguridad (Tab 7)

### T-04.09: Link a auditoria + politica de sesiones
- [ ] Mantener `<BlacklistManager />` sin cambios
- [ ] Agregar seccion "Auditoria" con boton "Ver log de auditoria"
- [ ] Click navega a `/crm/auditoria` via `useNavigate()`
- [ ] Agregar seccion "Politica de sesiones": select con opciones (1h/8h/24h/7d)
- [ ] Si endpoint de security settings no existe (verificado en T-04.01): mostrar select deshabilitado con tooltip "Proximamente"
- [ ] Si existe: guardar via PATCH
- **Archivos:** `frontend_react/src/views/ConfigView.tsx`
- **Criterio:** link funciona, policy section visible (funcional o marcada como pendiente)

---

## Fase 8: Tab Calendario (Tab 8)

### T-04.10: Verificar y completar CalComSettings
- [ ] Si CalComSettings es funcional: no tocar, tarea completada
- [ ] Si es placeholder: implementar selector de provider (local/google)
- [ ] Provider `local`: inputs business_hours_start/end, guardar via `PUT /admin/core/settings/company`
- [ ] Provider `google`: boton de conexion Google Calendar (flujo OAuth existente)
- [ ] Guardar provider seleccionado via `PUT /admin/core/tenants/{id}` con `{ calendar_provider }`
- **Archivos:** `frontend_react/src/components/config/CalComSettings.tsx`
- **Criterio:** tab funcional con provider seleccionable

---

## Fase 9: Tests

### T-04.11: Tests unitarios ConfigView
- [ ] Test Tab 1: render nombre empresa, edicion y submit
- [ ] Test Tab 2: modal de confirmacion en delete (no window.confirm)
- [ ] Test Tab 3: render estado "no conectado" (mock 404)
- [ ] Test Tab 3: render estado "conectado" (mock 200)
- [ ] Test Tab 5: boton sync deshabilitado si 404
- [ ] Test Tab 6: toggles renderizan, cambian, guardan
- [ ] Test Tab 7: click "Ver auditoria" navega correctamente
- **Archivos:** `frontend_react/src/__tests__/ConfigView.test.tsx`
- **Criterio:** todos los tests pasan

---

## Orden de ejecucion

```
T-04.01 (verificacion) -> T-04.02 (endpoints faltantes)
         |
         v
T-04.03 + T-04.04 + T-04.05 + T-04.06 + T-04.07 + T-04.08 + T-04.09 + T-04.10
         (tabs individuales — pueden ser paralelos o secuenciales)
         |
         v
     T-04.11 (tests)
```

**Estimacion total:** ~10-12 horas (depende de cuantos endpoints faltan en backend)
