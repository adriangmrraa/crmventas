# Design F-03: User Profile Page — Perfil Completo

**Spec:** `03-user-profile.spec.md`
**Fecha:** 2026-04-14

---

## Arquitectura de la solucion

### Principio de diseno

ProfileView se reestructura en secciones independientes. Cada seccion tiene su propio estado de loading/error/success y su propio boton de guardar. Esto evita mezclar validaciones y permite guardar parcialmente sin afectar otras secciones.

### Estructura de componentes

```
ProfileView.tsx (refactor)
|-- SummaryCard              (avatar + nombre + role + email — sidebar izquierdo)
|   +-- AvatarUpload         (click en avatar -> file picker -> preview -> upload)
|-- BasicInfoSection         (first_name, last_name, google_calendar_id)
|-- LanguageTimezoneSection   (selector idioma + selector timezone)
|-- ChangePasswordSection     (current_password, new_password, confirm_password)
+-- NotificationPrefsSection  (3 toggles: email, push, desktop)
```

Cada seccion es un componente interno de ProfileView (no archivos separados) ya que solo se usan aqui. Si crecen demasiado, se extraen a `components/profile/`.

### Estado del componente

```typescript
// Estado global del perfil (carga una vez)
interface ExtendedUserProfile {
  id: string;
  email: string;
  role: string;
  first_name: string;
  last_name: string;
  google_calendar_id?: string;
  avatar_url?: string;
  timezone?: string;
  language?: string;
  created_at?: string;
}

// Cada seccion mantiene su propio estado de formulario via useState
// No se usa un form library (react-hook-form) para mantener consistencia con el resto del CRM
```

---

## Decisiones tecnicas

### D1: Avatar Upload — ruta de archivo

**Opcion elegida:** Upload via `POST /api/v1/drive/upload` con folder `avatars`.

- El endpoint de Drive ya existe en `drive_routes.py`.
- Verificar si acepta uploads sin `clientId`. Si no, crear wrapper `POST /auth/avatar` que llame internamente al storage.
- Flujo: file picker -> validacion client-side (2MB, image/*) -> preview con `URL.createObjectURL()` -> upload a Drive -> obtener URL -> PATCH /auth/profile con `avatar_url`.
- Fallback: si upload falla, mantener iniciales. Si `avatar_url` existe pero la imagen no carga (onError), fallback a iniciales.

### D2: Cambio de contrasena — endpoint separado

**Razon:** El cambio de contrasena es una operacion sensible que requiere verificar la contrasena actual. No debe mezclarse con PATCH /auth/profile.

- Nuevo endpoint: `POST /auth/change-password`
- Backend ya tiene `auth_service.verify_password()` y `auth_service.get_password_hash()`.
- Respuestas: 200 OK (exito), 400 Bad Request (contrasena actual incorrecta), 422 (validacion).
- Los 3 campos se limpian despues de exito. En caso de error, no se limpian.

### D3: Google Calendar ID — todos los roles

**Cambio:** Eliminar el check `role === 'professional'` en frontend y backend.

- Frontend: mostrar seccion de Calendar ID para TODOS los roles.
- Backend: PATCH /auth/profile ya acepta `google_calendar_id`, pero solo lo guarda si `role='professional'`. Cambiar para guardarlo en la tabla `users` directamente (o agregar columna si no existe).

### D4: Idioma — fuente de verdad

- El idioma se guarda en `users.language` via PATCH /auth/profile.
- Al hacer login, `GET /auth/profile` retorna `language` -> se setea en `LanguageContext`.
- Al cambiar idioma en perfil: PATCH exitoso -> `setLanguage(newLang)` -> UI cambia inmediatamente.
- `localStorage` actua como cache entre sesiones (el context ya lo usa).

### D5: Timezone — lista acotada

Lista hardcodeada de ~15 zonas relevantes para el mercado target (LATAM + Espana):

```typescript
const TIMEZONE_OPTIONS = [
  { value: 'America/Argentina/Buenos_Aires', label: 'Buenos Aires (GMT-3)' },
  { value: 'America/Bogota', label: 'Bogota (GMT-5)' },
  { value: 'America/Lima', label: 'Lima (GMT-5)' },
  { value: 'America/Santiago', label: 'Santiago (GMT-4/-3)' },
  { value: 'America/Mexico_City', label: 'Ciudad de Mexico (GMT-6)' },
  { value: 'America/Sao_Paulo', label: 'Sao Paulo (GMT-3)' },
  { value: 'America/New_York', label: 'New York / Miami (GMT-5)' },
  { value: 'America/Los_Angeles', label: 'Los Angeles (GMT-8)' },
  { value: 'Europe/Madrid', label: 'Madrid (GMT+1)' },
  { value: 'UTC', label: 'UTC' },
];
```

### D6: Notificaciones — endpoint personal vs global

- Perfil (F-03): preferencias del USUARIO individual -> `GET/PUT /admin/core/notifications/settings` con scope user.
- ConfigView (F-04): preferencias GLOBALES del tenant -> endpoints diferentes.
- Verificar si `notification_routes.py` soporta ambos scopes. Si no, el endpoint de usuario se crea en `auth_routes.py`.

---

## Cambios de backend requeridos

### auth_routes.py

1. **Extender `GET /auth/profile`**: agregar `avatar_url`, `timezone`, `language` en la respuesta.
2. **Extender `PATCH /auth/profile`**: aceptar `avatar_url`, `timezone`, `language`, `google_calendar_id` para TODOS los roles.
3. **Nuevo `POST /auth/change-password`**:
   ```python
   class ChangePasswordRequest(BaseModel):
       current_password: str
       new_password: str = Field(..., min_length=8)

   @router.post("/change-password")
   async def change_password(req: ChangePasswordRequest, user=Depends(get_current_user)):
       if not auth_service.verify_password(req.current_password, user.hashed_password):
           raise HTTPException(400, "Contrasena actual incorrecta")
       hashed = auth_service.get_password_hash(req.new_password)
       # UPDATE users SET hashed_password = ... WHERE id = user.id
       return {"message": "Contrasena actualizada"}
   ```

### DB Migration

```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS timezone TEXT DEFAULT 'America/Argentina/Buenos_Aires';
ALTER TABLE users ADD COLUMN IF NOT EXISTS language TEXT DEFAULT 'es';
```

Verificar si las columnas ya existen antes de ejecutar.

---

## Riesgos y mitigaciones

| Riesgo | Mitigacion |
|--------|------------|
| Drive upload no acepta sin clientId | Crear endpoint wrapper POST /auth/avatar |
| Columnas no existen en tabla users | Migration SQL con IF NOT EXISTS |
| LanguageContext no persiste al recargar | localStorage ya se usa como fallback |
| Notificaciones endpoint no existe | Crear minimal GET/PUT en auth_routes |
