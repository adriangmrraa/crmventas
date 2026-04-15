# SPEC F-03: User Profile Page — Perfil Completo

**Prioridad:** Media
**Complejidad:** Baja
**Estado:** Parcialmente implementado — requiere extensión significativa
**Archivo de referencia:** `frontend_react/src/views/ProfileView.tsx`

---

## Intent

`ProfileView` existe y tiene funcionalidad básica: editar nombre/apellido y Google Calendar ID (solo para rol `professional`). Necesita extenderse para soportar: avatar upload, cambio de contraseña, preferencias de notificaciones, idioma, y timezone — y hacer que estas funciones también estén disponibles para roles CRM (setter, closer, CEO), no solo professional.

---

## Estado Actual (Discovery)

### Lo que existe en el frontend (`ProfileView.tsx`):
- `GET /auth/profile` — carga `{ id, email, role, first_name, last_name, google_calendar_id }`
- `PATCH /auth/profile` — guarda `{ first_name, last_name, google_calendar_id }` (solo si rol=professional)
- Formulario de nombre/apellido: funcional
- Google Calendar ID: solo visible si `role === 'professional'` — incorrecto para CRM
- Avatar: muestra inicial del nombre como placeholder — NO hay upload real
- Sin sección de cambio de contraseña
- Sin preferencias de notificaciones
- Sin selector de idioma en el perfil (existe en ConfigView pero solo para CEO)
- Sin selector de timezone

### Lo que existe en el backend (`auth_routes.py`):

**`GET /auth/profile`** (implementado):
- Retorna `{ id, email, role, first_name, last_name }` desde tabla `users`
- Si `role='professional'`: agrega `google_calendar_id`, `is_active` desde tabla `professionals`
- NO retorna avatar_url, timezone, ni preferencias de notificaciones

**`PATCH /auth/profile`** (implementado, incompleto):
- Acepta `{ first_name, last_name, google_calendar_id }`
- `google_calendar_id` solo se guarda si `role='professional'` (hardcoded en backend)
- NO acepta avatar_url, timezone, language, ni password change

### Lo que NO existe aún:
- Endpoint de cambio de contraseña (`POST /auth/change-password`)
- Endpoint de upload de avatar — necesita un mecanismo de storage (Drive existente o storage directo)
- Campos `avatar_url`, `timezone`, `language`, `notification_preferences` en tabla `users` — probable que no existan aún, hay que verificar o migrar
- Preferencias de notificaciones — `NotificationSettings` model existe en `notification_routes.py` pero no hay endpoint PUT para el usuario autenticado

---

## Requirements

### MUST (crítico)

#### Edición de datos básicos (para TODOS los roles)
- M1. Editar `first_name` y `last_name` — ya funciona, mantener
- M2. El campo Google Calendar ID debe estar disponible para todos los roles (no solo professional) — el CEO también puede tener una agenda Google
- M3. `PATCH /auth/profile` debe aceptar `google_calendar_id` para todos los roles y guardarlo en la tabla `users` (o crear columna si no existe)

#### Avatar Upload
- M4. Mostrar avatar actual si `avatar_url` existe, sino iniciales (como ahora)
- M5. Click en el avatar abre file picker (accept: `image/*`, max 2MB)
- M6. Preview inmediato del avatar seleccionado antes de guardar
- M7. Upload a `POST /api/v1/drive/upload` (endpoint Drive existente) con `folder='avatars'` o similar, obtener URL pública
- M8. `PATCH /auth/profile` acepta `avatar_url` y lo guarda en `users.avatar_url`
- M9. Mostrar error si el archivo supera 2MB o no es imagen

#### Cambio de Contraseña
- M10. Sección "Cambiar contraseña" separada del formulario de datos básicos
- M11. Campos: contraseña actual, nueva contraseña, confirmar nueva contraseña
- M12. Validación client-side: nueva contraseña min 8 chars, nueva = confirmar
- M13. `POST /auth/change-password` con `{ current_password, new_password }` — NUEVO ENDPOINT a crear
- M14. Backend verifica `current_password` antes de cambiar
- M15. Error específico si contraseña actual es incorrecta (HTTP 400)

#### Preferencias de Idioma
- M16. Selector de idioma (es/en/fr) visible en el perfil — igual que en ConfigView pero a nivel personal
- M17. El idioma guardado en perfil afecta la UI del usuario actual vía `LanguageContext`
- M18. `PATCH /auth/profile` acepta `language` y lo guarda en `users` (o en una tabla de preferencias)

#### Timezone
- M19. Selector de timezone con lista de zonas comunes de LATAM + España + resto
- M20. `PATCH /auth/profile` acepta `timezone` y lo guarda
- M21. Timezone visible en pantalla de perfil (no necesita afectar la UI inmediatamente — es un campo informativo para sincronización de calendarios)

#### Preferencias de Notificaciones
- M22. Toggles para: `email_notifications`, `push_notifications`, `desktop_notifications`
- M23. `GET /admin/core/notifications/settings` — carga preferencias actuales (revisar si existe o crear)
- M24. `PUT /admin/core/notifications/settings` — guarda preferencias (revisar endpoint en `notification_routes.py`)

### SHOULD (deseable)
- S1. Indicador de "cuenta activa desde" (fecha de creación del usuario)
- S2. Mostrar el tenant/empresa al que pertenece el usuario
- S3. Sección "Sesiones activas" (fuera de scope de esta spec — marcar como TO-DO)
- S4. Si el avatar no se puede cargar, fallback graceful a iniciales

---

## API Endpoints

### Existentes (a extender)

| Método | Path | Cambio requerido |
|--------|------|-----------------|
| GET | `/auth/profile` | Agregar `avatar_url`, `timezone`, `language` en respuesta |
| PATCH | `/auth/profile` | Aceptar `avatar_url`, `timezone`, `language`, `google_calendar_id` (todos los roles) |

### Nuevos a crear

| Método | Path | Descripción |
|--------|------|-------------|
| POST | `/auth/change-password` | Cambia contraseña verificando la actual |
| GET | `/admin/core/notifications/settings` | Carga preferencias de notificación del user |
| PUT | `/admin/core/notifications/settings` | Guarda preferencias de notificación |

### Existente para avatar upload

| Método | Path | Descripción |
|--------|------|-------------|
| POST | `/api/v1/drive/upload` | Sube archivo — ya existe en `drive_routes.py` |

**Verificar:** si `drive_routes.py` acepta upload de imágenes sin `clientId` (para avatars sin asociación a cliente). Si no, se necesita un endpoint de upload genérico.

### Modelos Pydantic (cambios en backend)

```python
# Extender ProfileUpdate en auth_routes.py
class ProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    google_calendar_id: Optional[str] = None  # Ahora para todos los roles
    avatar_url: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None  # 'es' | 'en' | 'fr'

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
```

---

## DB Changes Requeridas

Verificar si las columnas existen en la tabla `users`. Si no:

```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS timezone TEXT DEFAULT 'America/Argentina/Buenos_Aires';
ALTER TABLE users ADD COLUMN IF NOT EXISTS language TEXT DEFAULT 'es';
```

Para notificaciones, la tabla `notification_settings` ya puede existir. Verificar schema antes de crear.

---

## React Components

### Modificaciones en `ProfileView.tsx`

Reestructurar el componente en secciones separadas:

```
ProfileView (existente — modificar)
├── AvatarUpload         — Avatar circular + file picker + preview
├── BasicInfoForm        — first_name, last_name, email (readonly), google_calendar_id
├── LanguageTimezoneForm — Selector idioma + timezone
├── ChangePasswordForm   — 3 campos de password + submit independiente
└── NotificationToggles  — 3 toggles + save
```

Cada sección tiene su propio botón "Guardar" y estado de loading/error independiente, para no mezclar validaciones entre secciones.

---

## Scenarios

### SC-01: Usuario actualiza su nombre y apellido
**Dado** que el usuario (cualquier rol) está en `/perfil`
**Cuando** cambia "Juan" por "Juan Pablo" y hace click en "Guardar datos básicos"
**Entonces** `PATCH /auth/profile` se llama con `{ first_name: "Juan Pablo" }`, el nombre se actualiza en el header/sidebar sin recargar la página, y aparece un toast de éxito.

### SC-02: CEO sube avatar
**Dado** que el CEO está en su perfil y no tiene avatar configurado
**Cuando** hace click en su inicial "J", selecciona un archivo `foto.png` de 500KB, ve el preview, y hace click en "Guardar avatar"
**Entonces** el archivo se sube a Drive, se obtiene la URL pública, `PATCH /auth/profile` se llama con `{ avatar_url: "https://..." }`, y el avatar circular muestra la foto en lugar de la inicial.

### SC-03: Archivo de avatar demasiado grande
**Dado** que el usuario intenta subir `foto_grande.jpg` de 5MB
**Cuando** selecciona el archivo
**Entonces** el error aparece inmediatamente (validación client-side, sin llamar al backend): "El archivo no puede superar 2MB". El picker se resetea.

### SC-04: Cambio de contraseña exitoso
**Dado** que el usuario está logueado y conoce su contraseña actual
**Cuando** completa: contraseña actual = "OldPass123", nueva = "NewPass456!", confirmar = "NewPass456!" y hace click en "Cambiar contraseña"
**Entonces** `POST /auth/change-password` se llama correctamente, aparece toast de éxito, y los 3 campos se resetean a vacío.

### SC-05: Contraseña actual incorrecta
**Dado** que el usuario ingresa contraseña actual incorrecta
**Cuando** hace click en "Cambiar contraseña"
**Entonces** el backend retorna 400, el frontend muestra "La contraseña actual es incorrecta" debajo del campo de contraseña actual, sin resetear ningún campo.

### SC-06: Usuario cambia idioma desde perfil
**Dado** que el usuario tiene idioma `en` configurado
**Cuando** selecciona `es` en el selector de idioma y guarda
**Entonces** `PATCH /auth/profile` guarda `language: 'es'`, `setLanguage('es')` del `LanguageContext` se llama, y la UI cambia a español inmediatamente.

### SC-07: Toggle de notificaciones email
**Dado** que el usuario tiene `email_notifications: true`
**Cuando** desactiva el toggle y guarda preferencias
**Entonces** `PUT /admin/core/notifications/settings` se llama con `{ email_notifications: false, ... }`, y el toggle queda en off.

---

## Testing Strategy

### Unit Tests (Vitest + Testing Library)
- `ProfileView.test.tsx`:
  - Render con datos de perfil cargados
  - Validación de contraseñas (nueva != confirmar → error)
  - Validación de tamaño de avatar (>2MB → error, sin llamar API)
  - Cada sección guarda independientemente (mock de axios verify calls)

### Integration Tests
- Mock `GET /auth/profile` → render de todos los campos
- Mock `PATCH /auth/profile` → verificar payload con solo los campos enviados
- Mock `POST /auth/change-password` 400 → mensaje de error en campo correcto
- Mock `POST /api/v1/drive/upload` → verificar que avatar_url se usa en PATCH siguiente

---

## Files to Modify

| Archivo | Tipo de cambio |
|---------|---------------|
| `frontend_react/src/views/ProfileView.tsx` | Modificar — reestructurar en secciones |
| `orchestrator_service/auth_routes.py` | Modificar — extender PATCH /auth/profile, agregar POST /auth/change-password |
| DB migration | Verificar/agregar columnas `avatar_url`, `timezone`, `language` en `users` |

---

## Acceptance Criteria

- [ ] Todos los roles (setter, closer, CEO, secretary) pueden editar su nombre y apellido
- [ ] Google Calendar ID editable para todos los roles (no solo professional)
- [ ] Avatar upload funciona con preview y validación de tamaño
- [ ] Cambio de contraseña requiere la contraseña actual
- [ ] Error claro si contraseña actual es incorrecta
- [ ] Selector de idioma en perfil cambia la UI inmediatamente
- [ ] Selector de timezone guarda el valor seleccionado
- [ ] Toggles de notificaciones guardan preferencias
- [ ] Cada sección tiene loading state y error state independientes
- [ ] No hay regresión en la funcionalidad básica actual (nombre/apellido)

---

## Notas Técnicas

- **Avatar y Drive:** `drive_routes.py` está en `/api/v1/drive`. Verificar si acepta uploads sin `clientId`. Si no, crear endpoint `POST /auth/avatar` que internamente llama al storage y retorna URL pública. Alternativa simple: aceptar `avatar_url` como string y que el frontend haga el upload directamente a un servicio externo (Cloudinary, S3) — pero esto agrega complejidad de credenciales.
- **Cambio de contraseña:** el backend usa `auth_service.verify_password(current, hash)` y `auth_service.get_password_hash(new)` — ya existen en `auth_service.py`. El endpoint nuevo es directo.
- **Language en LanguageContext:** `LanguageContext` tiene `setLanguage` — llamarlo después de PATCH exitoso. Persistencia: el context puede leer el idioma desde `localStorage` o desde `GET /auth/profile` en el login. Documentar cuál es la fuente de verdad.
- **Timezone options:** usar lista hardcodeada de ~30 zonas relevantes (LATAM + España) en lugar de la lista completa de IANA (500+ opciones). Ejemplo: `America/Argentina/Buenos_Aires`, `America/Bogota`, `America/Santiago`, `America/Lima`, `America/Mexico_City`, `Europe/Madrid`.
- **Notificaciones:** revisar si `GET /admin/core/notifications/settings` ya existe en `notification_routes.py` antes de crear. El modelo `NotificationSettings` ya está definido en ese archivo.
