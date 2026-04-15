# Design F-11: Migration Pages Backend Verification

**Spec:** 11-migration-pages-backend.spec.md
**Fecha:** 2026-04-14

---

## 1. Alcance

Verificacion sistematica de 6 modulos migrados desde crmcodexy (Next.js) al stack actual (FastAPI + PostgreSQL). No es implementacion nueva — es auditoria de codigo existente y correccion de defectos encontrados.

---

## 2. Estrategia de verificacion por modulo

### 2.1 Chat Interno

**Archivos a auditar:**
- `orchestrator_service/routes/internal_chat_routes.py`
- `orchestrator_service/services/internal_chat_service.py`

**Checklist de auditoria:**
1. **DB Real:** Todas las queries usan `db.pool.fetch*` / `db.execute`, no datos hardcodeados
2. **Tenant isolation:** WHERE `tenant_id = $N` en TODAS las queries (canales, mensajes, reads)
3. **Access control:** `GET /mensajes/{canal_id}` verifica que el usuario pertenece al canal
4. **Paginacion:** `limit` + `before` (cursor timestamp) implementados correctamente
5. **Mark as read:** Al consultar mensajes, se hace upsert en tabla de lecturas
6. **Socket.IO:** `POST /mensajes` emite `nuevo_mensaje` al room `canal_{canal_id}`
7. **Validacion tipo:** `tipo` se valida contra `["mensaje", "notificacion_tarea", "notificacion_llamada"]`
8. **Error codes:** 403 para acceso denegado, 422 para validacion, 404 para canal inexistente

**Socket.IO especifico:**
- Verificar que `request.app.state.socketio` existe en el app startup
- Verificar que el emit no falla silenciosamente si socketio no esta montado
- Verificar formato de room: `canal_{canal_id}`

### 2.2 Daily Check-in

**Archivos a auditar:**
- `orchestrator_service/routes/checkin_routes.py`
- `orchestrator_service/services/daily_checkin_service.py`

**Checklist de auditoria:**
1. **Unicidad:** Constraint `(user_id, tenant_id, fecha)` — check-in duplicado retorna 409
2. **Checkout ownership:** Solo el usuario dueno puede cerrar su checkin
3. **Checkout idempotencia:** Checkout de checkin ya cerrado retorna 409
4. **Tasa de contacto:** Calculo automatico `contactos_logrados / llamadas_logradas`
5. **GET /today:** Retorna `{}` si no existe (no 404)
6. **CEO endpoints:** `/ceo/today` y `/ceo/weekly` filtran por tenant, incluyen user_name via JOIN
7. **APScheduler:** Verificar que existe job de auto-close de check-ins abiertos al final del dia
8. **Role guard:** Endpoints CEO requieren role `ceo` o `admin`

### 2.3 Mis Notas / Vendor Tasks

**Archivos a auditar:**
- `orchestrator_service/routes/vendor_tasks_routes.py`
- `orchestrator_service/services/vendor_tasks_service.py`

**Checklist de auditoria:**
1. **GET /mine:** Filtra por `vendor_id = user_id` + `tenant_id`
2. **Ordenamiento:** No completadas primero, luego por `fecha_limite ASC NULLS LAST`
3. **PATCH completar:** Verifica tenant ownership (404, no 403)
4. **GET /pending-count:** Existe y retorna `{ "count": N }` — si no existe, CREAR
5. **POST / (crear tarea):** Valida que `vendor_id` existe como usuario del tenant
6. **Notas personales:** `POST /personal` setea `es_personal = true`, visible solo para el autor

### 2.4 Manuales

**Archivos a auditar:**
- `orchestrator_service/routes/manuales_routes.py`
- `orchestrator_service/services/manuales_service.py`

**Checklist de auditoria:**
1. **Tenant isolation:** TODAS las queries filtran por `tenant_id`
2. **UUID handling:** `manual_id` cast correcto (`$1::uuid`)
3. **Busqueda texto:** `q` param busca en `titulo` y `contenido` (ILIKE o tsvector)
4. **Paginacion:** `limit` + `offset` con conteo `total` para paginacion
5. **Validacion categoria:** `categoria` validada contra `VALID_CATEGORIAS`, 400 si invalida
6. **Update parcial:** PUT actualiza solo campos presentes en body
7. **Delete cross-tenant:** 404 (no 403) si manual de otro tenant

### 2.5 Plantillas de Mensajes

**Archivos a auditar:**
- `orchestrator_service/routes/plantillas_routes.py`
- `orchestrator_service/services/plantillas_service.py`

**Checklist de auditoria:**
1. **Nombre duplicado:** `DuplicateTemplateNameError` retorna 409
2. **Variable extraction:** Regex `\{\{(\w+)\}\}` extrae variables del `contenido`
3. **Variables en PUT:** La extraccion ocurre tambien al actualizar, no solo al crear
4. **Endpoint POST /{id}/usar:** Existe e incrementa `uso_count` de forma atomica (UPDATE ... RETURNING)
5. **Busqueda:** `q` param funciona sobre `nombre` y/o `contenido`
6. **Concurrencia:** Dos `POST /usar` concurrentes resultan en `uso_count = 2` (no race condition)

### 2.6 Drive / Almacenamiento

**Archivos a auditar:**
- `orchestrator_service/routes/drive_routes.py`
- `orchestrator_service/services/drive_service.py`

**Checklist de auditoria:**
1. **Tenant isolation:** Queries sobre `drive_folders` y `drive_files` incluyen `tenant_id`
2. **Upload validacion:** MIME type contra `ALLOWED_MIME_TYPES`, tamanio contra `MAX_FILE_SIZE`
3. **Upload HTTP codes:** MIME invalido = 415, tamanio excedido = 413
4. **Download:** URL firmada o FileResponse con Content-Disposition, verificando tenant ownership
5. **Breadcrumb:** CTE recursivo ordena de raiz a hoja (no invertido)
6. **Delete folder:** 409 si no esta vacia sin `?force=true`
7. **Storage path:** Aislado por tenant (no collision entre tenants)

---

## 3. Estrategia de tests

### 3.1 Tipo de tests

**Tests de integracion contra PostgreSQL real** — no mocks de DB. Usar el `pytest` existente con fixtures de DB.

### 3.2 Estructura de test files

```
tests/
  integration/
    test_internal_chat.py
    test_daily_checkin.py
    test_vendor_tasks.py
    test_manuales.py
    test_plantillas.py
    test_drive.py
```

### 3.3 Patron de cada test file

```python
# Fixtures: tenant_id, user_id, auth_headers (JWT valido)
# Setup: crear datos de prueba en DB
# Test: llamar endpoint via TestClient
# Assert: verificar response + verificar estado en DB
# Teardown: limpiar datos de prueba
```

### 3.4 Tests criticos por modulo

| Modulo | Test critico | Por que |
|--------|-------------|---------|
| Chat | Mensaje persiste + Socket.IO emit | Core del modulo |
| Check-in | Duplicado retorna 409 | Integrity constraint |
| Vendor Tasks | pending-count correcto despues de CRUD | Badge de notificaciones depende de esto |
| Manuales | Cross-tenant 404 | Seguridad |
| Plantillas | uso_count atomico | Concurrencia |
| Drive | Upload MIME validation | Seguridad de archivos |

---

## 4. Clasificacion de hallazgos

| Severidad | Definicion | Accion |
|-----------|-----------|--------|
| CRITICAL | Datos de otro tenant accesibles, datos mock en produccion | Fix inmediato, bloqueante |
| HIGH | Endpoint retorna 500 en vez de status code apropiado | Fix antes de release |
| MEDIUM | Endpoint faltante (ej: pending-count) | Crear endpoint |
| LOW | Campo faltante en response, orden incorrecto | Fix en siguiente iteracion |

---

## 5. Decisiones de diseno

1. **Tests contra DB real, no mocks:** Los mocks no verifican queries SQL reales. El spec es explicito en esto.
2. **404 vs 403 para cross-tenant:** Siempre 404. No revelar existencia de recursos de otros tenants.
3. **pending-count endpoint:** Si no existe, se crea como parte de esta verificacion (no es solo auditoria).
4. **Socket.IO graceful degradation:** Si socketio no esta montado, el POST /mensajes NO debe fallar — log warning y continuar.
