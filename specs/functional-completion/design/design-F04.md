# Design F-04: Configuration Page — 8 Tabs Funcionales

**Spec:** `04-configuration-complete.spec.md`
**Fecha:** 2026-04-14

---

## Estado actual por tab

| Tab | Nombre | Estado actual | Trabajo requerido |
|-----|--------|---------------|-------------------|
| 1 | General | Parcial (idioma funciona, nombre empresa falta) | Agregar campo business_name |
| 2 | YCloud | Funcional | Modal de confirmacion en delete |
| 3 | Meta Ads | Solo webhook URL | Estado conexion + wizard |
| 4 | Otras | Funcional | Sin cambios funcionales |
| 5 | Mantenimiento | Solo clean-media | Botones sync/cache + info sistema |
| 6 | Notificaciones | Placeholder "Proximamente" | Implementar toggles completos |
| 7 | Seguridad | Solo BlacklistManager | Politica sesiones + link auditoria |
| 8 | Calendario | CalComSettings delegado | Verificar si es real o placeholder |

---

## Decisiones tecnicas

### D1: Tab General — campo nombre de empresa

- Usar `GET /admin/core/settings/company` para cargar `business_name`.
- Usar `PUT /admin/core/settings/company` para guardar.
- Boton "Guardar nombre" separado del selector de idioma (dos formularios distintos dentro del mismo tab).
- Solo visible/editable para CEO (el endpoint ya requiere role=ceo en backend).

### D2: Tab YCloud — modal de confirmacion

- Reemplazar `window.confirm()` por el componente `<Modal />` existente (`components/Modal.tsx`).
- Ya importado en ConfigView (linea 8 del archivo actual).
- Estado: `const [deleteModalOpen, setDeleteModalOpen] = useState(false)` + `credentialToDelete` para saber cual eliminar.

### D3: Tab Meta — integracion del wizard existente

- `MetaConnectionPanel.tsx` y `MetaConnectionWizard.tsx` ya existen en el frontend.
- El tab Meta en ConfigView NO debe duplicar la logica de IntegrationsView.
- Estrategia: renderizar un componente ligero que muestra estado + link a integraciones.
  - Si no conectado: chip rojo + boton "Ir a Integraciones" (navega a /crm/integraciones).
  - Si conectado: chip verde + nombre de cuenta + boton "Gestionar" -> navega a integraciones.
- Alternativa: importar `MetaConnectionPanel` directamente. Elegimos la navegacion para evitar duplicar estado y lógica de OAuth en dos lugares.
- La URL del webhook sigue visible y copiable en este tab (funcionalidad existente).

### D4: Tab Mantenimiento — botones condicionales

- Botones "Sincronizar DB" y "Limpiar cache": se renderizan siempre, pero con logica:
  - Si el endpoint existe (responde 200/4xx): boton habilitado, ejecuta accion.
  - Si el endpoint no existe (404 o no implementado): boton deshabilitado con tooltip "Proximamente".
- No hacer deteccion en runtime de si el endpoint existe. Simplemente: si el boton se clickea y retorna 404, mostrar toast "Funcion no disponible aun".
- Seccion info del sistema: `GET /health` (verificar en backend). Mostrar version, uptime si disponible.

### D5: Tab Notificaciones — preferencias globales del tenant

- Scope: configuracion GLOBAL del tenant (diferente a F-03 que es por usuario).
- Endpoint: `GET /admin/core/notifications/settings` y `PUT /admin/core/notifications/settings`.
- Si no existe: crear con modelo `{ email_notifications, push_notifications, desktop_notifications }`.
- 3 toggles con descripcion debajo de cada uno:
  - Email: "Enviar notificaciones por correo electronico a los miembros del equipo"
  - Push: "Notificaciones push en dispositivos moviles"
  - Desktop: "Notificaciones del navegador en escritorio"

### D6: Tab Seguridad — extension conservadora

- `<BlacklistManager />` se mantiene sin cambios (funcional).
- Agregar seccion "Auditoria" con boton "Ver log de auditoria" que navega a `/crm/auditoria` via `useNavigate()`.
- Seccion "Politica de sesiones": si `PATCH /admin/core/settings/security` existe, mostrar select de timeout. Si no, mostrar como "Proximamente" con texto informativo.
- No agregar 2FA en esta spec — fuera de scope.

### D7: Tab Calendario — verificar CalComSettings

- Leer `CalComSettings.tsx` para determinar si es funcional o placeholder.
- Si placeholder: implementar selector de provider (`local` | `google`) con `PUT /admin/core/tenants/{id}` campo `calendar_provider`.
- Si `local`: mostrar business_hours_start/end editables.
- Si `google`: mostrar flujo de conexion Google Calendar (boton OAuth).

---

## Estructura de componentes por tab

```
ConfigView.tsx (existente — modificar)
|-- Tab 1: GeneralTab
|   |-- BusinessNameForm (nuevo)
|   +-- LanguageSelector (existente, funcional)
|-- Tab 2: YCloudTab (existente, agregar modal)
|-- Tab 3: MetaTab
|   |-- MetaStatusBadge (nuevo — chip conectado/desconectado)
|   |-- WebhookUrlDisplay (existente)
|   +-- Link a /crm/integraciones
|-- Tab 4: OtrasTab (existente, sin cambios)
|-- Tab 5: MantenimientoTab
|   |-- CleanMediaSection (existente)
|   |-- SyncDbButton (nuevo, condicional)
|   |-- ClearCacheButton (nuevo, condicional)
|   +-- SystemInfoSection (nuevo)
|-- Tab 6: NotificacionesTab (nuevo, reemplaza placeholder)
|-- Tab 7: SeguridadTab
|   |-- BlacklistManager (existente)
|   |-- AuditLogLink (nuevo)
|   +-- SessionPolicySection (nuevo, condicional)
+-- Tab 8: CalendarioTab
    |-- CalComSettings (existente — verificar)
    +-- ProviderSelector (nuevo si CalCom es placeholder)
```

Los componentes nuevos se implementan inline dentro de ConfigView.tsx (siguiendo el patron actual del archivo). Si el archivo crece demasiado (>500 lineas), extraer tabs a `components/config/tabs/`.

---

## Riesgos y mitigaciones

| Riesgo | Mitigacion |
|--------|------------|
| MetaConnectionWizard duplicado entre tabs y IntegrationsView | Tab Meta solo muestra status + link a integraciones |
| Endpoints de mantenimiento no existen | Botones visibles pero manejan 404 gracefully |
| CalComSettings es placeholder | Verificar antes de implementar; crear ProviderSelector si necesario |
| ConfigView.tsx ya es grande (~400+ lineas) | Extraer tabs a componentes si supera 500 lineas |
| Tab Notificaciones: confusion scope user vs tenant | Documentar claramente que F-04 es tenant-level, F-03 es user-level |
