# SPEC F-11: Migration Pages Backend Verification

**Priority:** Alta
**Complexity:** Media
**Estado:** Draft
**Fecha:** 2026-04-14

---

## Contexto

Las siguientes páginas fueron migradas desde el proyecto `crmcodexy` (Next.js) al frontend React 18 del CRM Ventas:

1. Chat Interno (`/admin/core/internal-chat/*`)
2. Daily Check-in (`/admin/core/checkin/*`)
3. Mis Notas / Vendor Tasks (`/admin/core/crm/vendor-tasks/*`)
4. Manuales (`/admin/core/manuales/*`)
5. Plantillas (`/api/v1/plantillas/*`)
6. Drive (`/api/v1/drive/*`)

Los routers FastAPI existen en `orchestrator_service/routes/`. Este spec verifica que CADA endpoint:
- Consulta la base de datos real (no retorna datos mock)
- Aplica `tenant_id` como filtro mandatorio en todas las queries
- Maneja errores correctamente (HTTP status codes apropiados)
- Funciona con el servicio de capa de datos correspondiente

---

## 1. Chat Interno

**Router:** `routes/internal_chat_routes.py`
**Prefijo:** `/admin/core/internal-chat`
**Servicio:** `services/internal_chat_service.py` (instancia `chat_service`)

### Endpoints a verificar

| Método | Path | Descripción |
|--------|------|-------------|
| GET | `/canales` | Lista canales + DMs del usuario |
| GET | `/mensajes/{canal_id}` | Mensajes de un canal/DM (paginados) |
| POST | `/mensajes` | Enviar mensaje (body: `canal_id`, `contenido`, `tipo`) |
| POST | `/dm` | Iniciar DM con otro usuario |
| GET | `/unread` | Conteo de no leídos por canal |

### Verificaciones requeridas

**`GET /canales`:**
- Llama `chat_service.ensure_channels_exist(tenant_id)` antes de listar → verifica que crea canales fijos si no existen en DB.
- Query sobre tabla `internal_chat_channels` filtrando por `tenant_id`.
- Incluye DMs del usuario autenticado (`user_id` del JWT).
- Respuesta incluye `unread_count` por canal (debe ser un COUNT real, no 0 hardcodeado).

**`GET /mensajes/{canal_id}`:**
- Verifica que el usuario tiene acceso al canal (`chat_service.get_mensajes` hace este check — devuelve `None` si sin acceso → 403).
- Query sobre `internal_chat_messages` con `canal_id = $1 AND tenant_id = $2`.
- Paginación real: params `limit` y `before` (cursor por timestamp) funcionan.
- Marca mensajes como leídos al consultar (upsert en `message_reads` o similar).

**`POST /mensajes`:**
- Inserta en `internal_chat_messages` con `tenant_id`, `canal_id`, `autor_id`, `contenido`, `tipo`, `created_at`.
- Emite evento Socket.IO `nuevo_mensaje` al room del canal. Verificar que `request.app.state.socketio` existe y el emit no falla silenciosamente.
- Valida `tipo` en `["mensaje", "notificacion_tarea", "notificacion_llamada"]` → 422 si inválido.
- Devuelve el mensaje creado con su `id` generado.

**Socket.IO:**
- El servidor Socket.IO debe estar montado en `main.py` o en el app startup.
- Los rooms de canales deben tener el formato `canal_{canal_id}` o similar consistente.
- El evento debe emitir a todos los sockets en el room excepto el emisor.

### Criterios de aceptación

- `GET /canales` con `tenant_id` válido devuelve lista (puede ser vacía).
- `GET /mensajes/{canal_id}` con canal inexistente devuelve 404 o 403.
- `POST /mensajes` con `contenido` vacío devuelve 422.
- `POST /mensajes` con `tipo` inválido devuelve 422.
- El mensaje persiste en DB después del POST (verificar con GET subsiguiente).

---

## 2. Daily Check-in

**Router:** `routes/checkin_routes.py`
**Prefijo:** `/admin/core/checkin`
**Servicio:** `services/daily_checkin_service.py` (instancia `checkin_service`)

### Endpoints a verificar

| Método | Path | Descripción |
|--------|------|-------------|
| POST | `/` | Abrir jornada (check-in) |
| POST | `/{checkin_id}/checkout` | Cerrar jornada |
| GET | `/today` | Check-in del día actual del usuario |
| GET | `/ceo/today` | Panel CEO: check-ins del día de todo el equipo |
| GET | `/ceo/weekly` | Panel CEO: datos semanales agregados |
| GET | `/history` | Historial del usuario (últimos N días) |

### Verificaciones requeridas

**`POST /` (check-in):**
- Inserta en tabla `daily_checkins` con `user_id`, `tenant_id`, `llamadas_planeadas`, `fecha` (solo fecha, sin hora), `status: 'open'`.
- Lanza `CheckinAlreadyExistsError` → 409 si ya existe un check-in con `fecha = today` y `user_id = $1 AND tenant_id = $2`.
- La constraint de unicidad debe ser por `(user_id, tenant_id, fecha)`.

**`POST /{checkin_id}/checkout`:**
- Actualiza el registro: `status = 'closed'`, `llamadas_logradas`, `contactos_logrados`, `notas`, `checkout_at = NOW()`.
- Valida que el checkin pertenece al `user_id` autenticado (no puede cerrar el checkin de otro).
- Lanza `CheckinAlreadyClosedError` → 409 si `status` ya es `'closed'`.
- Calcula automáticamente `tasa_contacto = contactos_logrados / llamadas_logradas` si llamadas > 0.

**`GET /today`:**
- Devuelve el check-in del día para el `user_id` autenticado.
- Si no existe, devuelve `{}` (no 404).
- Incluye campos: `id`, `llamadas_planeadas`, `llamadas_logradas`, `status`, `checkin_at`, `checkout_at`.

**`GET /ceo/today` (role: ceo, admin):**
- Devuelve lista de todos los check-ins del día para el tenant.
- Incluye `user_name` (JOIN con tabla `users` o `team_members`).
- Incluye métricas agregadas: total_planeadas, total_logradas, tasa_promedio, count_sin_checkin (usuarios del tenant que no hicieron check-in hoy).

**`GET /ceo/weekly` (role: ceo, admin):**
- Parámetro `weeks` (1 a 4).
- Devuelve datos agrupados por semana y por usuario.
- Agrega: llamadas_planeadas_total, llamadas_logradas_total, tasa_promedio_semana.

**APScheduler auto-close:**
- Debe existir un job programado (APScheduler o similar en `main.py`) que cierra automáticamente check-ins `status = 'open'` al final del día (ej: 23:59 en la timezone del tenant).
- El job marca el checkout con `llamadas_logradas = 0` si no se hizo checkout manual.
- Verificar que el scheduler se inicializa en startup y el job está registrado.

### Criterios de aceptación

- Check-in duplicado en el mismo día devuelve 409.
- Checkout de checkin ya cerrado devuelve 409.
- CEO puede ver check-ins de todos pero vendor solo el suyo.
- `GET /today` devuelve `{}` si no hay check-in (no error).

---

## 3. Mis Notas / Vendor Tasks

**Router:** `routes/vendor_tasks_routes.py`
**Prefijo:** `/admin/core/crm/vendor-tasks`
**Servicio:** `services/vendor_tasks_service.py` (instancia `vendor_tasks_service`)

### Endpoints a verificar

| Método | Path | Descripción |
|--------|------|-------------|
| POST | `` | Crear tarea asignada a vendor (role: ceo, admin) |
| GET | `` | Listar todas las tareas (role: ceo, admin), con filtros |
| GET | `/mine` | Tareas propias del vendor autenticado |
| POST | `/personal` | Crear nota personal del usuario |
| PATCH | `/{task_id}/completar` | Toggle completada |
| GET | `/pending-count` | Count de pendientes del usuario |

### Verificaciones requeridas

**`GET /mine`:**
- Query filtra por `vendor_id = user_id` (el usuario autenticado) y `tenant_id`.
- Incluye tanto tareas asignadas por CEO como notas personales (`es_personal = true`).
- Ordena por: primero las no completadas (`completada = false`), luego por `fecha_limite ASC NULLS LAST`.

**`PATCH /{task_id}/completar`:**
- Actualiza `completada = $1` y `completada_at = NOW()` en la tarea.
- Verifica que la tarea pertenece al `tenant_id` del usuario autenticado.
- Si la tarea fue asignada por CEO, el vendor puede marcarla como completada (es su tarea).
- Responde 404 si la tarea no existe para ese tenant.

**`GET /pending-count`:**
- Devuelve `{ "count": N }` con el número de tareas pendientes (`completada = false`) del usuario.
- Usado para el badge de notificaciones en el nav.
- Si el endpoint no existe, CREAR en el router.

**Asignación a vendor:**
- `POST /` requiere `vendor_id` (int) que debe existir como usuario del tenant. Si no existe → 404.
- El campo `es_tarea = true` distingue tareas formales de notas.

### Criterios de aceptación

- `GET /mine` devuelve solo tareas del usuario autenticado, no de otros vendors.
- `PATCH /{task_id}/completar` con task de otro tenant devuelve 404.
- `GET /pending-count` devuelve number correcto después de crear y completar tareas.

---

## 4. Manuales

**Router:** `routes/manuales_routes.py`
**Prefijo:** `/admin/core/manuales`
**Servicio:** `services/manuales_service.py` (instancia `manuales_service`, lista `VALID_CATEGORIAS`)

### Endpoints a verificar

| Método | Path | Descripción |
|--------|------|-------------|
| GET | `` | Listar manuales con filtros |
| GET | `/{manual_id}` | Obtener un manual |
| POST | `` | Crear manual (role: ceo, secretary) |
| PUT | `/{manual_id}` | Actualizar manual (role: ceo, secretary) |
| DELETE | `/{manual_id}` | Eliminar manual (role: ceo, secretary) |

### Verificaciones requeridas

**Todas las queries:**
- Filtran por `tenant_id`. Un tenant no puede ver ni modificar manuales de otro.
- `manual_id` es UUID — la query usa cast correcto (`$1::uuid` o equivalente).

**`GET `` (list):**
- Parámetros `categoria`, `q` (texto libre), `limit`, `offset` funcionan correctamente.
- `q` hace búsqueda en `titulo` y `contenido` (usando `ILIKE` o `tsvector`).
- Devuelve `{ "items": [...], "total": N }` con conteo total para paginación.

**`POST `` (create):**
- Valida `categoria` contra `VALID_CATEGORIAS`. Si inválida → 400.
- Inserta con `tenant_id`, `titulo`, `contenido`, `categoria`, `autor`, `created_at`, `updated_at`.
- Devuelve el manual creado con su `id`.

**`PUT /{manual_id}`:**
- Update parcial: solo actualiza los campos que vienen en el body (no reemplaza todo).
- Si `categoria` en body no está en `VALID_CATEGORIAS` → 400.
- Si manual no existe para el tenant → 404.

**`DELETE /{manual_id}`:**
- 204 si eliminado correctamente.
- 404 si no existe para el tenant (no debe poder eliminar manuales de otros tenants).

### Criterios de aceptación

- `GET` con `q="ventas"` devuelve manuales que contengan "ventas" en título o contenido.
- `POST` con `categoria` inválida devuelve 400 con mensaje claro.
- `DELETE` de manual de otro tenant devuelve 404 (no 403 — no revelamos existencia).

---

## 5. Plantillas de Mensajes

**Router:** `routes/plantillas_routes.py`
**Prefijo:** `/api/v1/plantillas`
**Servicio:** `services/plantillas_service.py` (instancia `plantillas_service`, `VALID_CATEGORIES`, `DuplicateTemplateNameError`)

### Endpoints a verificar

| Método | Path | Descripción |
|--------|------|-------------|
| GET | `` | Listar plantillas con filtros |
| GET | `/{plantilla_id}` | Obtener plantilla |
| POST | `` | Crear plantilla |
| PUT | `/{plantilla_id}` | Actualizar plantilla |
| DELETE | `/{plantilla_id}` | Eliminar plantilla |

### Verificaciones requeridas

**`POST `` (create):**
- Si ya existe una plantilla con el mismo `nombre` para el `tenant_id` → lanza `DuplicateTemplateNameError` → responde 409.
- Extrae variables del `contenido`: detecta patrones `{{variable}}` o `{variable}` y guarda `variables_detectadas` como array en DB.
- Este campo permite al frontend hacer preview con sustitución de variables.

**Incremento atómico de `uso_count`:**
- Debe existir endpoint `POST /{plantilla_id}/usar` que incrementa `uso_count` de forma atómica:
  ```sql
  UPDATE plantillas SET uso_count = uso_count + 1, updated_at = NOW()
  WHERE id = $1 AND tenant_id = $2
  RETURNING uso_count
  ```
- Si el endpoint no existe → CREAR. Se invoca cuando el usuario usa una plantilla para enviar un mensaje.
- El incremento debe ser atómico (UPDATE con RETURNING, no SELECT + UPDATE).

**Variable extraction:**
- La extracción de variables del `contenido` debe ocurrir en `POST` y `PUT`.
- Regex: `\{\{(\w+)\}\}` para extraer variables tipo `{{nombre}}`.
- El array extraído se guarda en columna `variables` (JSONB o TEXT[]) en la tabla.

### Criterios de aceptación

- `POST` con `nombre` duplicado devuelve 409.
- `GET` con `q="bienvenida"` devuelve plantillas que contengan ese texto.
- `POST /{id}/usar` incrementa `uso_count` de 0 a 1 la primera vez.
- Dos requests concurrentes a `POST /{id}/usar` resultan en `uso_count = 2` (atomicidad).

---

## 6. Drive / Almacenamiento de Archivos

**Router:** `routes/drive_routes.py`
**Prefijo:** `/api/v1/drive`
**Servicio:** `services/drive_service.py` (instancia `drive_service`)

### Endpoints a verificar

| Método | Path | Descripción |
|--------|------|-------------|
| GET | `/folders` | Listar carpetas raíz o subcarpetas |
| GET | `/folders/{folder_id}` | Obtener carpeta |
| POST | `/folders` | Crear carpeta |
| PUT | `/folders/{folder_id}` | Renombrar carpeta |
| DELETE | `/folders/{folder_id}` | Eliminar carpeta |
| POST | `/folders/{folder_id}/files` | Subir archivo a carpeta |
| GET | `/folders/{folder_id}/files` | Listar archivos en carpeta |
| DELETE | `/files/{file_id}` | Eliminar archivo |
| GET | `/files/{file_id}/download` | URL firmada de descarga |
| GET | `/folders/{folder_id}/breadcrumb` | Breadcrumb de navegación |

### Verificaciones requeridas

**Aislamiento por tenant:**
- Todas las queries sobre `drive_folders` y `drive_files` incluyen `tenant_id = $N`.
- Un tenant no puede listar ni acceder a carpetas de otro tenant.

**`POST /folders/{folder_id}/files` (upload):**
- Acepta `multipart/form-data` con el archivo.
- Valida MIME type contra `ALLOWED_MIME_TYPES`.
- Valida tamaño máximo contra `MAX_FILE_SIZE`.
- Guarda el archivo en storage (local disk bajo path aislado por tenant, o S3/compatible).
- Inserta en `drive_files` con: `id`, `nombre`, `mime_type`, `size_bytes`, `folder_id`, `tenant_id`, `storage_path`, `created_at`.
- Devuelve el archivo creado con su `id`.

**`GET /files/{file_id}/download` (URL firmada):**
- Si el storage es local: sirve el archivo directamente con `FileResponse` y header `Content-Disposition`.
- Si el storage es S3: genera URL prefirmada con expiración de 15 minutos.
- Verifica que el `file_id` pertenece al `tenant_id` del usuario autenticado.
- 404 si no existe o no pertenece al tenant.

**`GET /folders/{folder_id}/breadcrumb`:**
- Devuelve array de `[{ id, nombre }]` desde la raíz hasta la carpeta actual.
- Implementado con query recursiva CTE en PostgreSQL:
  ```sql
  WITH RECURSIVE breadcrumb AS (
    SELECT id, nombre, parent_id FROM drive_folders WHERE id = $1 AND tenant_id = $2
    UNION ALL
    SELECT f.id, f.nombre, f.parent_id FROM drive_folders f
    JOIN breadcrumb b ON f.id = b.parent_id
  )
  SELECT id, nombre FROM breadcrumb ORDER BY ...
  ```
- El orden debe ser de raíz a hoja (no invertido).

**`DELETE /folders/{folder_id}`:**
- Si la carpeta tiene subcarpetas o archivos → 409 "La carpeta no está vacía".
- O bien, implementar eliminación recursiva (cascada) con confirmación explícita via query param `?force=true`.
- Elimina el registro de `drive_folders` y todos los archivos del storage asociados.

### Criterios de aceptación

- Upload de archivo con MIME no permitido devuelve 415.
- Upload de archivo mayor a `MAX_FILE_SIZE` devuelve 413.
- `GET /folders/{id}/breadcrumb` para carpeta en nivel 3 devuelve 3 elementos.
- Download de archivo de otro tenant devuelve 404.
- Eliminar carpeta con archivos sin `?force=true` devuelve 409.

---

## Matriz de cobertura por página

| Página | Router | Servicio | DB Real | Tenant Isolation | Error Handling | Socket.IO |
|--------|--------|----------|---------|-----------------|----------------|-----------|
| Chat Interno | `internal_chat_routes.py` | `internal_chat_service.py` | Verificar | Verificar | Verificar | Verificar |
| Daily Check-in | `checkin_routes.py` | `daily_checkin_service.py` | Verificar | Verificar | Verificar | N/A |
| Mis Notas | `vendor_tasks_routes.py` | `vendor_tasks_service.py` | Verificar | Verificar | Verificar | N/A |
| Manuales | `manuales_routes.py` | `manuales_service.py` | Verificar | Verificar | Verificar | N/A |
| Plantillas | `plantillas_routes.py` | `plantillas_service.py` | Verificar | Verificar | Verificar | N/A |
| Drive | `drive_routes.py` | `drive_service.py` | Verificar | Verificar | Verificar | N/A |

---

## Notas de verificación

- "DB Real" significa: la query en el servicio hace un `db.pool.fetch*` o `db.execute` real, no retorna datos hardcodeados.
- "Tenant Isolation" significa: todas las queries incluyen `WHERE tenant_id = $N` como condición mandatoria.
- "Error Handling" significa: errores de DB (registro no encontrado, constraint violation) se capturan y devuelven el HTTP status code apropiado (no 500 genérico).
- Los tests de integración deben correr con la BD real (PostgreSQL) — no mocks. Ver `pytest.ini` y tests existentes en `tests/`.
