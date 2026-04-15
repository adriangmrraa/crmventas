# Tasks F-03: User Profile Page

**Spec:** `03-user-profile.spec.md`
**Design:** `design/design-F03.md`
**Fecha:** 2026-04-14

---

## Fase 1: Backend — Modelo y endpoints

### T-03.01: DB Migration — agregar columnas a users
- [ ] Verificar si `avatar_url`, `timezone`, `language` existen en tabla `users`
- [ ] Si no existen, ejecutar ALTER TABLE con defaults (timezone: 'America/Argentina/Buenos_Aires', language: 'es')
- [ ] Verificar que `google_calendar_id` existe en tabla `users` (no solo en `professionals`)
- **Archivos:** migration SQL o script de inicializacion
- **Criterio:** columnas existen y tienen defaults correctos

### T-03.02: Extender GET /auth/profile
- [ ] Agregar `avatar_url`, `timezone`, `language` al SELECT query
- [ ] Retornar estos campos en la respuesta JSON
- [ ] Retornar `google_calendar_id` para TODOS los roles (no solo professional)
- **Archivos:** `orchestrator_service/auth_routes.py`
- **Criterio:** GET retorna los 3 campos nuevos + calendar_id sin filtro de rol

### T-03.03: Extender PATCH /auth/profile
- [ ] Agregar `avatar_url`, `timezone`, `language` al modelo `ProfileUpdate`
- [ ] Eliminar restriccion de `google_calendar_id` solo para professional
- [ ] UPDATE en tabla `users` con todos los campos opcionales enviados
- [ ] Solo actualizar campos que estan presentes en el body (no null-ear los ausentes)
- **Archivos:** `orchestrator_service/auth_routes.py`
- **Criterio:** PATCH acepta y guarda todos los campos para cualquier rol

### T-03.04: Crear POST /auth/change-password
- [ ] Crear endpoint `POST /auth/change-password`
- [ ] Modelo: `ChangePasswordRequest { current_password: str, new_password: str (min 8) }`
- [ ] Verificar `current_password` con `auth_service.verify_password()`
- [ ] Si incorrecta: HTTP 400 con mensaje "Contrasena actual incorrecta"
- [ ] Si correcta: hashear nueva con `auth_service.get_password_hash()`, UPDATE en DB
- [ ] Retornar 200 con mensaje de exito
- **Archivos:** `orchestrator_service/auth_routes.py`
- **Criterio:** cambio exitoso con contrasena correcta, 400 con incorrecta

### T-03.05: Verificar endpoint de notificaciones usuario
- [ ] Leer `notification_routes.py` y verificar si GET/PUT de settings por usuario existen
- [ ] Si no existen: crear `GET /auth/notifications/settings` y `PUT /auth/notifications/settings`
- [ ] Modelo: `{ email_notifications: bool, push_notifications: bool, desktop_notifications: bool }`
- [ ] Scope: por usuario autenticado (no por tenant)
- **Archivos:** `orchestrator_service/auth_routes.py` o `notification_routes.py`
- **Criterio:** GET carga, PUT guarda preferencias por usuario

---

## Fase 2: Frontend — Reestructuracion de ProfileView

### T-03.06: Refactor ProfileView — layout por secciones
- [ ] Mantener layout grid actual (sidebar izquierdo + contenido derecho)
- [ ] Sidebar: SummaryCard con avatar, nombre, rol, email, fecha registro
- [ ] Contenido derecho: stack de secciones, cada una con card independiente
- [ ] Extender interface `UserProfile` con `avatar_url`, `timezone`, `language`
- [ ] fetchProfile() ya carga los nuevos campos
- **Archivos:** `frontend_react/src/views/ProfileView.tsx`
- **Criterio:** layout renderiza con datos extendidos sin romper UI existente

### T-03.07: AvatarUpload en SummaryCard
- [ ] Click en avatar circular abre `<input type="file" accept="image/*" />`
- [ ] Validacion client-side: max 2MB, tipo imagen
- [ ] Preview inmediato con `URL.createObjectURL(file)`
- [ ] Boton "Guardar avatar" visible solo cuando hay preview pendiente
- [ ] Upload a `POST /api/v1/drive/upload` con FormData (folder: 'avatars')
- [ ] Al obtener URL, llamar PATCH /auth/profile con `{ avatar_url: url }`
- [ ] Fallback: si avatar_url falla (onError en img), mostrar iniciales
- [ ] Error visible si archivo > 2MB o no es imagen
- **Archivos:** `frontend_react/src/views/ProfileView.tsx`
- **Criterio:** upload funciona, preview visible, errores claros, fallback a iniciales

### T-03.08: BasicInfoSection
- [ ] Campos: first_name, last_name (ya existen), google_calendar_id (para TODOS los roles)
- [ ] Eliminar condicion `authUser?.role === 'professional'` para calendar_id
- [ ] Boton "Guardar datos basicos" independiente
- [ ] Estado de loading/success/error propio
- [ ] Llamar PATCH /auth/profile con solo estos campos
- **Archivos:** `frontend_react/src/views/ProfileView.tsx`
- **Criterio:** todos los roles ven calendar_id, guardan independientemente

### T-03.09: LanguageTimezoneSection
- [ ] Selector de idioma (es/en/fr) con las mismas opciones que ConfigView
- [ ] Selector de timezone con lista TIMEZONE_OPTIONS (10 zonas LATAM + Espana + UTC)
- [ ] Boton "Guardar preferencias" independiente
- [ ] Al guardar idioma exitosamente: llamar `setLanguage()` del LanguageContext
- [ ] PATCH /auth/profile con `{ language, timezone }`
- **Archivos:** `frontend_react/src/views/ProfileView.tsx`
- **Criterio:** idioma cambia UI inmediatamente, timezone se persiste

### T-03.10: ChangePasswordSection
- [ ] Card separada con titulo "Cambiar contrasena"
- [ ] 3 campos: contrasena actual, nueva contrasena, confirmar nueva
- [ ] Validacion client-side: nueva min 8 chars, nueva === confirmar
- [ ] Boton "Cambiar contrasena" independiente
- [ ] POST /auth/change-password con { current_password, new_password }
- [ ] Exito: toast + limpiar los 3 campos
- [ ] Error 400: mostrar "Contrasena actual incorrecta" bajo el campo correspondiente
- [ ] Los campos NO se limpian en caso de error
- **Archivos:** `frontend_react/src/views/ProfileView.tsx`
- **Criterio:** flujo completo funciona, errores claros, campos se limpian solo en exito

### T-03.11: NotificationPrefsSection
- [ ] 3 toggles: email_notifications, push_notifications, desktop_notifications
- [ ] Cargar estado inicial desde GET endpoint de notificaciones
- [ ] Boton "Guardar notificaciones" independiente
- [ ] PUT al endpoint de notificaciones con los 3 valores
- [ ] Descripcion debajo de cada toggle explicando que controla
- **Archivos:** `frontend_react/src/views/ProfileView.tsx`
- **Criterio:** toggles cargan estado real, guardan correctamente

---

## Fase 3: Tests

### T-03.12: Tests unitarios ProfileView
- [ ] Test: render con perfil cargado muestra todos los campos
- [ ] Test: avatar upload con archivo > 2MB muestra error (sin API call)
- [ ] Test: contrasena nueva != confirmar -> error de validacion
- [ ] Test: cada seccion guarda independientemente (verificar calls a API)
- [ ] Test: cambio de idioma llama a setLanguage del contexto
- **Archivos:** `frontend_react/src/__tests__/ProfileView.test.tsx`
- **Criterio:** todos los tests pasan

---

## Orden de ejecucion

```
T-03.01 (DB) -> T-03.02 + T-03.03 + T-03.04 + T-03.05 (backend, paralelo)
                    |
                    v
            T-03.06 (refactor layout)
                    |
                    v
    T-03.07 + T-03.08 + T-03.09 + T-03.10 + T-03.11 (secciones, paralelo)
                    |
                    v
               T-03.12 (tests)
```

**Estimacion total:** ~8-10 horas
