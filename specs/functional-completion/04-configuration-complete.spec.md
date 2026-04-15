# SPEC F-04: Configuration Page — 8 Tabs Funcionales Completos

**Prioridad:** Media
**Complejidad:** Media
**Estado:** Parcialmente implementado — algunos tabs son placeholder o incompletos
**Archivo de referencia:** `frontend_react/src/views/ConfigView.tsx`

---

## Intent

`ConfigView` tiene 8 tabs estructurados y varios ya tienen lógica parcial. Esta spec define el estado funcional completo de cada tab: qué falta implementar, qué endpoint usar, y cuál es el comportamiento esperado. El objetivo es que ningún tab quede "En construcción" ni en placeholder.

---

## Estado Actual por Tab (Discovery)

### Tab 1 — General
**Estado:** Parcialmente funcional
- Carga `GET /admin/core/settings/clinic` → obtiene `{ name, ui_language }`
- Permite cambiar idioma via `PATCH /admin/core/settings/clinic`
- **FALTA:** no hay campo para editar el nombre de la empresa (`clinic_name`). El nombre se muestra pero no se puede editar desde aquí. El endpoint `PUT /admin/core/settings/company` existe en `company_settings_routes.py` y acepta `business_name`.

### Tab 2 — YCloud (WhatsApp)
**Estado:** Funcional (bien implementado)
- `GET /admin/core/settings/integration/ycloud/{tenantId}` — carga config
- `POST /admin/core/settings/integration/ycloud/{tenantId}` — guarda API key y webhook secret
- Tabla de credenciales activas, acciones editar/eliminar
- **FALTA menor:** al eliminar una credencial de la tabla, no hay confirmación modal — solo `confirm()` del browser. Mejorar con modal.

### Tab 3 — Meta Ads (Leadgen)
**Estado:** Básico — solo muestra webhook URL
- Muestra `GET /admin/core/config/deployment` para obtener URL de webhook Meta
- Permite copiar la URL por tenant
- **FALTA:** No hay flujo real de conexión/desconexión de Meta Business. El componente `MetaConnectionPanel.tsx` y `MetaConnectionWizard.tsx` existen pero no están integrados en este tab. Solo se muestra la URL del webhook. El estado de conexión (¿está conectado?) no se verifica.

### Tab 4 — Otras (Credenciales genéricas)
**Estado:** Funcional
- CRUD completo de credentials via `/admin/core/credentials`
- Modal de creación/edición funcional
- **FALTA:** no hay validación de nombre duplicado, y el campo `value` en edición siempre muestra `"••••••••"` — no permite ver ni editar el valor real (comportamiento correcto para seguridad, pero debe ser claro para el usuario).

### Tab 5 — Mantenimiento
**Estado:** Parcialmente funcional
- `POST /admin/core/maintenance/clean-media` — funcional con selector de días
- **FALTA:** No hay botón de "Sincronizar DB" ni de "Limpiar cache". El tab solo tiene la limpieza de media. La spec del usuario menciona "DB sync button, queue management, clear cache" — estos endpoints probablemente NO existen aún.

### Tab 6 — Notificaciones
**Estado:** Placeholder total
- Solo muestra "Próximamente" con ícono de Bell
- **FALTA:** Implementar toggles de preferencias de alerta: email, push, desktop. Los modelos existen en `notification_routes.py` (`NotificationSettings`). Verificar si hay endpoints GET/PUT para settings de notificaciones globales (por tenant, no por usuario).

### Tab 7 — Seguridad
**Estado:** Delegado a componente existente
- Renderiza `<BlacklistManager />` — este componente es funcional (gestiona IPs/números en lista negra)
- **FALTA:** No hay toggle de 2FA, ni configuración de política de contraseñas. El componente solo cubre blacklist.

### Tab 8 — Calendario
**Estado:** Delegado a componente existente
- Renderiza `<CalComSettings />` — componente existente
- **FALTA verificar:** si `CalComSettings` realmente guarda sus datos o también es placeholder.

---

## Requirements

### MUST (crítico)

#### Tab 1 — General

- M1. Agregar campo editable "Nombre de empresa" que lee y guarda `business_name` via `GET /admin/core/settings/company` + `PUT /admin/core/settings/company`
- M2. El campo nombre muestra el valor actual al cargar el tab
- M3. Botón "Guardar nombre" separado del cambio de idioma (no mezclar formularios)
- M4. Solo CEO puede editar el nombre (el endpoint ya requiere role=ceo)

#### Tab 3 — Meta Ads

- M5. Mostrar estado de conexión: "Conectado" / "No conectado" consultando `GET /admin/meta/status` (o endpoint equivalente en `meta_connect_routes.py`)
- M6. Si no conectado: botón "Conectar con Meta" que abre flujo OAuth (el componente `MetaConnectionWizard.tsx` existe — integrarlo aquí)
- M7. Si conectado: mostrar nombre de la cuenta Business conectada + botón "Desconectar"
- M8. URL del webhook Meta sigue visible y copiable (ya funciona)

#### Tab 5 — Mantenimiento

- M9. Limpiar media — ya funcional, mantener
- M10. Botón "Sincronizar base de datos" — llama a `POST /admin/core/maintenance/sync-db` si el endpoint existe; si no existe, mostrar botón deshabilitado con tooltip "Próximamente"
- M11. Botón "Limpiar caché de sesiones" — llama a `POST /admin/core/maintenance/clear-cache` si existe; misma lógica
- M12. Sección de información del sistema: versión del backend (`GET /admin/health` o `/health`), uptime, timestamp del último sync

#### Tab 6 — Notificaciones

- M13. Cargar preferencias globales de notificación via `GET /admin/core/notifications/settings` (o `GET /admin/core/settings/notifications` — verificar cuál existe)
- M14. Toggles: `email_notifications`, `push_notifications`, `desktop_notifications`
- M15. Botón "Guardar preferencias" que llama a `PUT` (o `PATCH`) en el endpoint correspondiente
- M16. Descripción clara debajo de cada toggle (qué activa cada uno)

#### Tab 7 — Seguridad

- M17. Mantener `<BlacklistManager />` — ya funcional
- M18. Agregar sección "Política de sesiones": timeout de inactividad (select: 1h/8h/24h/7d) con `PATCH /admin/core/settings/security` si el endpoint existe — si no, mostrar como "Próximamente"
- M19. Agregar info de auditoría: botón "Ver log de auditoría" que navega a la vista de audit logs (ya existe `GET /admin/core/audit/logs`)

#### Tab 8 — Calendario

- M20. Verificar que `<CalComSettings />` guarda datos reales. Si es placeholder: implementar selector de provider (`local` vs `google`) via `PUT /admin/core/tenants/{id}` con `calendar_provider`
- M21. Si provider = `google`: mostrar el flujo de conexión Google Calendar
- M22. Si provider = `local`: mostrar configuración de horarios de atención (business_hours_start, business_hours_end) via `PUT /admin/core/settings/company`

### SHOULD (deseable)
- S1. Tab 2 (YCloud): reemplazar `confirm()` nativo por modal de confirmación con el componente `<Modal />` existente
- S2. Tab 4 (Otras): mensaje informativo explicando que el valor de las credenciales no se puede ver por seguridad
- S3. Tab 6 (Notificaciones): opción "Silenciar hasta..." con selector de fecha/hora (`mute_until`)
- S4. Indicador de "último guardado" en cada tab que haya guardado exitosamente
- S5. Detectar cambios no guardados al cambiar de tab y mostrar advertencia

---

## API Endpoints por Tab

### Tab 1 — General

| Método | Path | Descripción | Estado |
|--------|------|-------------|--------|
| GET | `/admin/core/settings/clinic` | Carga settings actuales (name, ui_language) | Implementado |
| PATCH | `/admin/core/settings/clinic` | Guarda ui_language | Implementado |
| GET | `/admin/core/settings/company` | Carga business_name y más | Implementado |
| PUT | `/admin/core/settings/company` | Guarda business_name | Implementado (CEO only) |

### Tab 3 — Meta

| Método | Path | Descripción | Estado |
|--------|------|-------------|--------|
| GET | `/admin/meta/status` (o similar) | Estado de conexión Meta | Verificar en `meta_connect.py` |
| GET/POST | `/admin/meta/connect` | Flujo OAuth Meta | Verificar |
| DELETE | `/admin/meta/disconnect` | Desconectar cuenta | Verificar |
| GET | `/admin/core/config/deployment` | URL webhook Meta | Implementado |

### Tab 5 — Mantenimiento

| Método | Path | Descripción | Estado |
|--------|------|-------------|--------|
| POST | `/admin/core/maintenance/clean-media` | Limpia archivos viejos | Implementado |
| POST | `/admin/core/maintenance/sync-db` | Sincroniza DB | Verificar / No existe |
| POST | `/admin/core/maintenance/clear-cache` | Limpia caché | Verificar / No existe |
| GET | `/health` o `/admin/health` | Info del sistema | Verificar en `health_routes.py` |

### Tab 6 — Notificaciones

| Método | Path | Descripción | Estado |
|--------|------|-------------|--------|
| GET | `/admin/core/notifications/settings` | Carga preferencias | Verificar en `notification_routes.py` |
| PUT | `/admin/core/notifications/settings` | Guarda preferencias | Verificar |

### Tab 7 — Seguridad

| Método | Path | Descripción | Estado |
|--------|------|-------------|--------|
| GET | `/admin/core/blacklist` | Lista blacklist | Implementado (en BlacklistManager) |
| GET | `/admin/core/audit/logs` | Logs de auditoría | Implementado |
| PATCH | `/admin/core/settings/security` | Política de sesiones | Verificar / No existe |

### Tab 8 — Calendario

| Método | Path | Descripción | Estado |
|--------|------|-------------|--------|
| GET/PATCH | `/admin/core/settings/company` | business_hours, calendar_provider | Implementado |
| PUT | `/admin/core/tenants/{id}` | Actualizar calendar_provider | Implementado |

---

## Scenarios

### SC-01: CEO edita nombre de empresa
**Dado** que el CEO está en el tab General
**Cuando** cambia el nombre de "Empresa Demo" a "Nexus Corp" y hace click en "Guardar nombre"
**Entonces** `PUT /admin/core/settings/company` se llama con `{ business_name: "Nexus Corp" }`, aparece toast "Nombre actualizado", y el header/sidebar refleja el nuevo nombre si está enlazado al contexto.

### SC-02: Meta sin conectar — botón de conexión visible
**Dado** que el tenant no tiene Meta Business conectado
**Cuando** el CEO abre el tab Meta
**Entonces** se muestra estado "No conectado" con chip rojo, el botón "Conectar con Meta" visible, y la URL del webhook visible pero con advertencia "Configura el webhook en Meta Business Manager después de conectar".

### SC-03: Meta conectado — opción de desconexión
**Dado** que Meta Business está conectado con la cuenta "Nexus Corp - Meta"
**Cuando** el CEO abre el tab Meta
**Entonces** se muestra "Conectado" con chip verde, nombre de la cuenta, y botón "Desconectar" que abre confirmación antes de ejecutar.

### SC-04: Mantenimiento — botón de sync deshabilitado
**Dado** que `POST /admin/core/maintenance/sync-db` no existe en el backend
**Cuando** el CEO ve el tab Mantenimiento
**Entonces** el botón "Sincronizar DB" está visible pero deshabilitado (opacity reducida), con tooltip "Próximamente" — no oculto, sino claramente marcado como pendiente.

### SC-05: Notificaciones — guardar preferencias
**Dado** que el CEO tiene todas las notificaciones activadas
**Cuando** desactiva `email_notifications` y hace click en "Guardar preferencias"
**Entonces** `PUT /admin/core/notifications/settings` se llama con `{ email_notifications: false, push_notifications: true, desktop_notifications: true }` y aparece toast de éxito.

### SC-06: Seguridad — navegar a audit logs
**Dado** que el CEO está en el tab Seguridad
**Cuando** hace click en "Ver log de auditoría"
**Entonces** se navega a `/crm/auditoria` (o la ruta existente de AuditLogView) via `react-router-dom` `useNavigate`.

### SC-07: Calendario — cambiar provider a Google
**Dado** que el tenant usa `calendar_provider: 'local'`
**Cuando** el CEO selecciona "Google Calendar" en el selector de provider
**Entonces** aparece una sección de configuración de Google Calendar (o botón de autenticación Google) y al guardar se llama `PUT /admin/core/tenants/{id}` con `{ calendar_provider: 'google' }`.

### SC-08: YCloud — confirmación antes de eliminar credencial
**Dado** que existe una credencial YCloud activa para el tenant
**Cuando** el CEO hace click en el botón de eliminar (ícono Trash)
**Entonces** se abre el componente `<Modal />` con texto "¿Eliminar esta credencial? Esta acción desconectará WhatsApp." y botones "Cancelar" y "Eliminar". Solo si confirma se llama `DELETE /admin/core/credentials/{id}`.

---

## Testing Strategy

### Unit Tests (Vitest + Testing Library)
- `ConfigView.test.tsx`:
  - Tab 1: render con nombre de empresa, edición y submit
  - Tab 3: render estado "no conectado" (mock 404 en status endpoint)
  - Tab 3: render estado "conectado" (mock 200 con account name)
  - Tab 5: render botón sync deshabilitado (sin endpoint)
  - Tab 6: render toggles, cambio de toggle, submit
  - Tab 7: botón navigate a audit logs
  - Tab 8: selector de provider, render condicional

### Integration Tests
- Mock `GET /admin/core/settings/company` → render nombre en Tab 1
- Mock `PUT /admin/core/settings/company` → verificar payload
- Mock notificaciones settings GET/PUT

---

## Files to Modify

| Archivo | Tipo de cambio |
|---------|---------------|
| `frontend_react/src/views/ConfigView.tsx` | Modificar — implementar tabs incompletos |
| `frontend_react/src/components/config/CalComSettings.tsx` | Verificar/modificar si es placeholder |
| `frontend_react/src/components/config/BlacklistManager.tsx` | Verificar (probablemente funcional) |
| `orchestrator_service/routes/company_settings_routes.py` | Verificar/extender si faltan campos |
| `orchestrator_service/routes/notification_routes.py` | Verificar/agregar GET/PUT settings endpoints |

---

## Acceptance Criteria

- [ ] Tab General: nombre de empresa editable y guarda correctamente
- [ ] Tab General: cambio de idioma funciona (ya funciona — mantener)
- [ ] Tab YCloud: funcional completo (ya funciona — agregar modal de confirmación delete)
- [ ] Tab Meta: estado de conexión visible (conectado/no conectado)
- [ ] Tab Meta: botón de conexión o desconexión según estado
- [ ] Tab Otras: funcional completo (ya funciona — sin cambios funcionales requeridos)
- [ ] Tab Mantenimiento: limpieza de media funciona (ya funciona)
- [ ] Tab Mantenimiento: botones de sync/cache visibles aunque deshabilitados si no hay endpoint
- [ ] Tab Notificaciones: no muestra "Próximamente" — tiene toggles funcionales
- [ ] Tab Seguridad: BlacklistManager funcional + enlace a audit logs
- [ ] Tab Calendario: provider seleccionable y guarda correctamente
- [ ] Ningún tab muestra "En construcción" o "Próximamente" como estado final

---

## Notas Técnicas

- **Verificar meta_connect.py:** antes de implementar Tab Meta, leer `orchestrator_service/routes/meta_connect.py` para entender qué endpoints de status/connect/disconnect realmente existen. El componente `MetaConnectionWizard.tsx` ya existe en el frontend — puede que solo haya que conectarlo al tab.
- **Verificar CalComSettings:** leer `frontend_react/src/components/config/CalComSettings.tsx` completamente para saber si ya guarda datos o es placeholder.
- **Verificar health_routes.py:** leer el router para saber qué información retorna (versión, uptime) y si puede usarse en el tab Mantenimiento.
- **Notificaciones settings:** el modelo `NotificationSettings` en `notification_routes.py` existe pero los endpoints GET/PUT para configuración pueden no estar implementados. Verificar antes de crear nuevos endpoints.
- **Tab 6 vs Spec F-03:** el tab Notificaciones en ConfigView es para preferencias **globales del tenant** (CEO). Las preferencias de notificación del usuario individual están en el perfil (Spec F-03). Son ámbitos distintos — asegurarse de usar endpoints y payloads diferentes.
- **Importar Modal:** el componente `Modal` ya existe en `frontend_react/src/components/Modal.tsx` — usarlo para la confirmación de delete en Tab YCloud en lugar de `window.confirm()`.
