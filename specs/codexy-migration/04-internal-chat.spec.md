# SPEC-04: Internal Team Chat

**Proyecto:** CRM VENTAS
**Origen:** crmcodexy → CRM VENTAS
**Prioridad:** Alta
**Complejidad:** Alta
**Fecha:** 2026-04-14
**Estado:** Draft

---

## 1. Contexto y Motivación

crmcodexy implementó un sistema de chat interno tipo Slack con canales fijos, DMs y notificaciones de eventos de negocio (llamadas y tareas). El objetivo es migrar esta funcionalidad a CRM VENTAS, adaptándola al modelo multi-tenant y aprovechando la infraestructura Socket.IO ya existente (actualmente usada en el dashboard de supervisión CEO y en el sistema de notificaciones de vendedores).

La migración no es un port literal: el modelo de tiempo real cambia de **Supabase postgres_changes** a **Socket.IO rooms por tenant**, lo que elimina la dependencia de Supabase y unifica toda la comunicación en tiempo real bajo un único servidor.

---

## 2. Alcance

### Incluido

- 3 canales fijos por tenant: `#general`, `#ventas`, `#operaciones`
- Mensajes Directos (DMs) entre miembros del tenant
- 3 tipos de mensaje: `mensaje`, `notificacion_tarea`, `notificacion_llamada`
- Tiempo real vía Socket.IO rooms (no polling)
- Sidebar: lista de canales + DMs con badge de no leídos
- Dialog de supervisión CEO/admin: ver todas las conversaciones DM del tenant
- Tarjetas visuales de notificación: amber para llamadas, violet para tareas
- Límite de 2000 caracteres por mensaje
- Enter para enviar, Shift+Enter para salto de línea
- Integración: el módulo de llamadas publica en `#general` cuando se agenda una llamada
- Marcar DM como leído al abrir la conversación
- Scoping multi-tenant: todo dato filtrado por `tenant_id`

### Excluido

- Canales personalizados creados por usuarios (post-MVP)
- Adjuntos / archivos (post-MVP)
- Reacciones a mensajes (post-MVP)
- Threads / hilos (post-MVP)
- Push notifications mobile (post-MVP)

---

## 3. Modelo de Datos

### 3.1 Tabla: `chat_mensajes`

```sql
CREATE TABLE IF NOT EXISTS chat_mensajes (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    canal_id    TEXT NOT NULL,
    -- 'general' | 'ventas' | 'operaciones' | 'dm_<uuid>_<uuid>' (UUIDs sorted asc)
    autor_id    VARCHAR(255) NOT NULL REFERENCES users(id),
    autor_nombre TEXT NOT NULL,
    autor_rol   TEXT NOT NULL CHECK (autor_rol IN ('ceo', 'admin', 'vendedor')),
    contenido   TEXT NOT NULL CHECK (char_length(contenido) <= 2000),
    tipo        TEXT NOT NULL DEFAULT 'mensaje'
                    CHECK (tipo IN ('mensaje', 'notificacion_tarea', 'notificacion_llamada')),
    metadata    JSONB,
    -- Para notificaciones: { cliente_nombre, descripcion, url }
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_chat_mensajes_tenant_canal
    ON chat_mensajes(tenant_id, canal_id, created_at DESC);

CREATE INDEX idx_chat_mensajes_autor_canal
    ON chat_mensajes(tenant_id, autor_id, canal_id, created_at DESC);
```

### 3.2 Tabla: `chat_conversaciones`

```sql
CREATE TABLE IF NOT EXISTS chat_conversaciones (
    canal_id         TEXT NOT NULL,
    tenant_id        INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    tipo             TEXT NOT NULL CHECK (tipo IN ('canal', 'dm')),
    participantes    VARCHAR(255)[] NOT NULL DEFAULT '{}',
    ultima_actividad TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (canal_id, tenant_id)
);

CREATE INDEX idx_chat_conv_tenant_tipo
    ON chat_conversaciones(tenant_id, tipo, ultima_actividad DESC);

-- GIN para queries sobre array de participantes
CREATE INDEX idx_chat_conv_participantes
    ON chat_conversaciones USING GIN (participantes);
```

**Diferencia clave vs. crmcodexy:** La PK es `(canal_id, tenant_id)` en lugar de solo `canal_id`. Esto garantiza aislamiento multi-tenant.

### 3.3 Trigger: `touch_chat_conversacion`

Al insertar un mensaje, actualiza `ultima_actividad` y hace upsert de la conversación:

```sql
CREATE OR REPLACE FUNCTION touch_chat_conversacion() RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO chat_conversaciones (canal_id, tenant_id, tipo, ultima_actividad)
    VALUES (
        NEW.canal_id,
        NEW.tenant_id,
        CASE WHEN NEW.canal_id LIKE 'dm_%' THEN 'dm' ELSE 'canal' END,
        NEW.created_at
    )
    ON CONFLICT (canal_id, tenant_id)
    DO UPDATE SET ultima_actividad = EXCLUDED.ultima_actividad;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_touch_chat_conv
    AFTER INSERT ON chat_mensajes
    FOR EACH ROW EXECUTE FUNCTION touch_chat_conversacion();
```

### 3.4 Seed de Canales Fijos

Los canales se crean al provisionar un nuevo tenant:

```sql
INSERT INTO chat_conversaciones (canal_id, tenant_id, tipo, participantes)
VALUES
    ('general',     :tenant_id, 'canal', '{}'),
    ('ventas',      :tenant_id, 'canal', '{}'),
    ('operaciones', :tenant_id, 'canal', '{}')
ON CONFLICT (canal_id, tenant_id) DO NOTHING;
```

### 3.5 DM Canonical ID

La ID de un DM es `dm_<uuid_menor>_<uuid_mayor>`, donde los UUIDs son los `user.id` de los dos participantes, ordenados lexicográficamente. Esto garantiza idempotencia: dos usuarios siempre convergen al mismo `canal_id` sin importar quién inicia la conversación.

```python
def dm_canal_id(user_a: str, user_b: str) -> str:
    return "dm_" + "_".join(sorted([user_a, user_b]))
```

### 3.6 Tabla de No Leídos (`chat_dm_no_leidos`)

Para evitar queries costosas al calcular badges de DMs no leídos:

```sql
CREATE TABLE IF NOT EXISTS chat_dm_no_leidos (
    tenant_id   INTEGER NOT NULL,
    user_id     VARCHAR(255) NOT NULL,
    canal_id    TEXT NOT NULL,
    count       INTEGER NOT NULL DEFAULT 0,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, user_id, canal_id),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);
```

Se incrementa en el trigger `touch_chat_conversacion` y se resetea al llamar `marcarDMLeido`.

---

## 4. API Endpoints (FastAPI)

Prefijo: `/admin/core/internal-chat`
Auth: `verify_admin_token` (JWT con `tenant_id`)
Rate limit: 60/minuto para send, 120/minuto para reads

### 4.1 `GET /canales`

Retorna los 3 canales fijos del tenant + lista de DMs del usuario autenticado, con `ultima_actividad` y `no_leidos`.

**Response:**
```json
{
  "canales": [
    { "canal_id": "general", "label": "general", "tipo": "canal" },
    { "canal_id": "ventas", "label": "ventas", "tipo": "canal" },
    { "canal_id": "operaciones", "label": "operaciones", "tipo": "canal" }
  ],
  "dms": [
    {
      "canal_id": "dm_<uuid>_<uuid>",
      "tipo": "dm",
      "otro_participante": { "id": "...", "nombre": "...", "rol": "vendedor" },
      "ultima_actividad": "2026-04-14T20:00:00Z",
      "no_leidos": 3
    }
  ]
}
```

### 4.2 `GET /mensajes/{canal_id}`

Retorna los últimos N mensajes de un canal/DM del tenant.

**Query params:** `limit` (default 50, max 200), `before` (cursor ISO timestamp)

**Auth check:** Si el canal es un DM, verificar que el usuario autenticado sea uno de los `participantes`. Si el rol es `ceo` o `admin`, permite acceso a cualquier DM del tenant.

### 4.3 `POST /mensajes`

Envía un mensaje al canal/DM.

**Request:**
```json
{
  "canal_id": "general",
  "contenido": "Texto del mensaje",
  "tipo": "mensaje"
}
```

**Flujo:**
1. Validar `char_length(contenido) <= 2000`
2. Insertar en `chat_mensajes` con `tenant_id` del JWT
3. El trigger actualiza `chat_conversaciones`
4. Emitir evento Socket.IO `chat:nuevo_mensaje` al room `chat:{tenant_id}:{canal_id}`
5. Si es DM, emitir `chat:dm_badge_update` al room personal del destinatario

### 4.4 `POST /dms/iniciar`

Crea o recupera un DM entre el usuario autenticado y otro miembro del tenant.

**Request:** `{ "destinatario_id": "<uuid>" }`
**Response:** `{ "canal_id": "dm_<uuid>_<uuid>" }`

**Flujo:**
1. Calcular `canal_id` = `dm_canal_id(user_id, destinatario_id)`
2. Upsert en `chat_conversaciones` con ambos participantes
3. Retornar `canal_id`

### 4.5 `POST /dms/{canal_id}/leer`

Marca el DM como leído para el usuario autenticado. Resetea el contador en `chat_dm_no_leidos` y emite `chat:badge_clear` por Socket.IO.

### 4.6 `GET /dms/todos` (solo CEO/admin)

Retorna todas las conversaciones DM activas del tenant para la vista de supervisión. Incluye los últimos mensajes y perfiles de participantes.

**Auth check:** Rechazar con 403 si el rol no es `ceo` ni `admin`.

### 4.7 `GET /perfiles`

Lista todos los usuarios del tenant (para el dialog "Nuevo DM"). Retorna `id`, `nombre`, `email`, `rol`.

---

## 5. Socket.IO: Rooms y Eventos

### 5.1 Rooms

| Room | Descripción |
|------|-------------|
| `chat:{tenant_id}:{canal_id}` | Room de un canal/DM específico |
| `notifications:{user_id}` | Room personal (ya existe, se reutiliza) |

El join al room del canal ocurre cuando el cliente abre la vista de chat para ese canal. Se hace `leave` al cambiar de canal.

### 5.2 Eventos Cliente → Servidor

| Evento | Payload | Descripción |
|--------|---------|-------------|
| `chat:join_canal` | `{ tenant_id, canal_id, user_id }` | Unirse al room del canal activo |
| `chat:leave_canal` | `{ tenant_id, canal_id }` | Salir del room al cambiar de canal |
| `chat:dm_leido` | `{ tenant_id, canal_id, user_id }` | Marcar DM como leído |

### 5.3 Eventos Servidor → Cliente

| Evento | Room destino | Payload | Descripción |
|--------|-------------|---------|-------------|
| `chat:nuevo_mensaje` | `chat:{tenant_id}:{canal_id}` | `ChatMensaje` completo | Nuevo mensaje en tiempo real |
| `chat:dm_badge_update` | `notifications:{user_id}` | `{ canal_id, no_leidos }` | Actualizar badge de DM no leído |
| `chat:badge_clear` | `notifications:{user_id}` | `{ canal_id }` | Limpiar badge al leer DM |
| `chat:sidebar_refresh` | `notifications:{user_id}` | `{ ultima_actividad }` | Actualizar `ultima_actividad` en sidebar |

### 5.4 Handlers en `socket_notifications.py`

Se agregan handlers al archivo existente `core/socket_notifications.py` bajo la función `register_notification_socket_handlers()`:

```python
@sio.on('chat:join_canal')
async def handle_chat_join_canal(sid, data):
    tenant_id = data.get('tenant_id')
    canal_id = data.get('canal_id')
    # Validar que el usuario tiene acceso al canal (DM: verificar participantes)
    await sio.enter_room(sid, f"chat:{tenant_id}:{canal_id}")

@sio.on('chat:leave_canal')
async def handle_chat_leave_canal(sid, data):
    tenant_id = data.get('tenant_id')
    canal_id = data.get('canal_id')
    await sio.leave_room(sid, f"chat:{tenant_id}:{canal_id}")

@sio.on('chat:dm_leido')
async def handle_chat_dm_leido(sid, data):
    # Delegar a ChatService.marcar_dm_leido()
    # Emitir chat:badge_clear al room personal del usuario
    pass
```

La emisión de `chat:nuevo_mensaje` ocurre en la route `POST /mensajes`, no en el handler, para mantener consistencia transaccional (mensaje persistido antes de emitir).

---

## 6. Integración con Módulo de Llamadas

Cuando se agenda una llamada en el módulo de llamadas de CRM VENTAS, ese módulo llama a una función utilitaria:

```python
async def notificar_llamada_en_chat(
    tenant_id: int,
    autor_id: str,
    autor_nombre: str,
    cliente_nombre: str,
    descripcion: str,
    url: str,
) -> None:
    """Publica una notificacion_llamada en #general del tenant."""
    await ChatService.enviar_mensaje(
        tenant_id=tenant_id,
        canal_id="general",
        autor_id=autor_id,
        autor_nombre=autor_nombre,
        autor_rol="vendedor",  # o el rol real del usuario
        contenido=f"Se agendó una llamada con {cliente_nombre}",
        tipo="notificacion_llamada",
        metadata={
            "cliente_nombre": cliente_nombre,
            "descripcion": descripcion,
            "url": url,
        },
    )
```

Esta función no es un endpoint; es una llamada directa de servicio a servicio dentro del mismo proceso FastAPI.

---

## 7. Frontend React (CRM VENTAS)

### 7.1 Estructura de Componentes

```
src/
  components/
    internal-chat/
      ChatLayout.tsx          # Contenedor: sidebar + panel principal
      ChatSidebar.tsx         # Lista canales + DMs + sección CEO
      MensajesList.tsx        # Scroll container con separadores de fecha
      MensajeBubble.tsx       # Bubble estándar (propio / ajeno)
      NotificacionCard.tsx    # Tarjeta amber/violet para llamadas/tareas
      NuevoDMDialog.tsx       # Dialog para iniciar DM con búsqueda de perfiles
      CeoSupervisionDialog.tsx # Dialog CEO: todas las convs DM del tenant
  hooks/
    useChatSocket.ts          # Suscripción Socket.IO a chat:nuevo_mensaje
    useChatUnread.ts          # Gestión de badges no leídos
```

### 7.2 Hook `useChatSocket`

```typescript
// Al montar: socket.emit('chat:join_canal', { tenant_id, canal_id, user_id })
// Al desmontar: socket.emit('chat:leave_canal', { tenant_id, canal_id })
// Handler: socket.on('chat:nuevo_mensaje', (msg) => setMensajes(prev => [...prev, msg]))
// Dedup: ignorar si msg.id ya existe en el array (idempotencia)
```

### 7.3 Comportamiento UI

- Enter envía, Shift+Enter inserta `\n`
- `maxLength={2000}` en el input, con contador visual al superar 1800 chars
- Auto-scroll al último mensaje al recibir nuevo mensaje o al cambiar de canal
- Separador de fecha entre mensajes de días distintos
- Badge rojo con conteo de no leídos en sidebar de DMs
- Al abrir un DM: llamar `POST /dms/{canal_id}/leer` + emitir `chat:dm_leido`
- Vista CEO: dialog con lista de todas las convs DM; clic navega al DM

### 7.4 Tarjetas de Notificación

| Tipo | Borde / Fondo | Ícono | Color |
|------|--------------|-------|-------|
| `notificacion_llamada` | amber-500/30, amber-500/10 | Phone | amber-400 |
| `notificacion_tarea` | violet-500/30, violet-500/10 | Bell | violet-400 |

Las tarjetas muestran: título (label del tipo), `contenido`, `cliente_nombre`, `descripcion`, link "Ver detalle" si hay `url`.

---

## 8. Scoping Multi-Tenant

| Capa | Implementación |
|------|----------------|
| DB | `tenant_id` en todas las queries, nunca cross-tenant |
| API | `tenant_id` extraído del JWT via `get_resolved_tenant_id()` |
| Socket.IO rooms | Prefijo `chat:{tenant_id}:` en todos los rooms de chat |
| CEO supervision | Filtra por `tenant_id` del CEO; un CEO no ve DMs de otros tenants |

---

## 9. Escenarios de Prueba (TDD)

### Backend

**ESCENARIO 01 — Enviar mensaje a canal fijo**
- DADO un usuario autenticado del tenant 1
- CUANDO `POST /admin/core/internal-chat/mensajes` con `canal_id=general`, `contenido="Hola"`, `tipo=mensaje`
- ENTONCES el mensaje se persiste en `chat_mensajes` con `tenant_id=1`
- Y se emite `chat:nuevo_mensaje` al room `chat:1:general`
- Y `chat_conversaciones` tiene `ultima_actividad` actualizada

**ESCENARIO 02 — DM canonical ID es idempotente**
- DADO users A y B (UUIDs)
- CUANDO A inicia DM con B y B inicia DM con A
- ENTONCES ambos producen el mismo `canal_id` = `dm_<min>_<max>`

**ESCENARIO 03 — Vendedor no puede ver DM de terceros**
- DADO un usuario con rol `vendedor`
- CUANDO `GET /mensajes/dm_<uuid_X>_<uuid_Y>` donde no es participante
- ENTONCES responde 403

**ESCENARIO 04 — CEO puede ver cualquier DM del tenant**
- DADO un usuario con rol `ceo` del tenant 1
- CUANDO `GET /mensajes/dm_<uuid_X>_<uuid_Y>` (DM entre dos vendedores del tenant 1)
- ENTONCES responde 200 con los mensajes

**ESCENARIO 05 — Aislamiento multi-tenant**
- DADO tenant 1 y tenant 2 con canal_id `general` en ambos
- CUANDO un usuario del tenant 2 emite a `chat:2:general`
- ENTONCES el room `chat:1:general` NO recibe el evento

**ESCENARIO 06 — Mensaje supera 2000 caracteres**
- DADO un mensaje de 2001 chars
- CUANDO `POST /mensajes`
- ENTONCES responde 422 con error de validación

**ESCENARIO 07 — Marcar DM como leído limpia badge**
- DADO un DM con 3 mensajes no leídos para user A
- CUANDO `POST /dms/{canal_id}/leer` con user A
- ENTONCES `chat_dm_no_leidos.count = 0` para `(tenant_id, user_A, canal_id)`
- Y se emite `chat:badge_clear` al room `notifications:{user_A}`

**ESCENARIO 08 — Integración llamadas: notificación en #general**
- DADO que se agenda una llamada en el módulo de llamadas
- CUANDO `notificar_llamada_en_chat()` es invocada
- ENTONCES se persiste un mensaje con `tipo=notificacion_llamada` en `canal_id=general`
- Y se emite `chat:nuevo_mensaje` al room `chat:{tenant_id}:general`

**ESCENARIO 09 — CEO supervision endpoint requiere rol adecuado**
- DADO un usuario con rol `vendedor`
- CUANDO `GET /dms/todos`
- ENTONCES responde 403

**ESCENARIO 10 — Notificacion_tarea persiste metadata completa**
- DADO un mensaje de tipo `notificacion_tarea` con `metadata={cliente_nombre, descripcion, url}`
- CUANDO se inserta
- ENTONCES `metadata` se almacena en el campo JSONB sin pérdida de campos

### Frontend

**ESCENARIO 11 — Socket join/leave al cambiar canal**
- DADO que el usuario está en el canal `general`
- CUANDO navega al canal `ventas`
- ENTONCES se emite `chat:leave_canal` para `general` y `chat:join_canal` para `ventas`

**ESCENARIO 12 — Dedup de mensajes en tiempo real**
- DADO que el mensaje M ya está en el array de mensajes local
- CUANDO llega `chat:nuevo_mensaje` con el mismo `id`
- ENTONCES el array no duplica el mensaje

**ESCENARIO 13 — Badge se limpia al abrir DM**
- DADO un DM con badge no_leidos=3 en sidebar
- CUANDO el usuario abre el DM
- ENTONCES el badge desaparece y se llama `POST /dms/{canal_id}/leer`

---

## 10. Migración de Base de Datos

Crear `patch_019_internal_chat.py`:

1. Crear tabla `chat_mensajes` con tenant_id
2. Crear tabla `chat_conversaciones` con PK compuesta `(canal_id, tenant_id)`
3. Crear tabla `chat_dm_no_leidos`
4. Crear función y trigger `touch_chat_conversacion`
5. Seed de canales fijos para tenants existentes
6. Registrar en `migrations` con `patch_number=19`

**No migrar datos históricos de crmcodexy.** Los datos de crmcodexy viven en Supabase (stack diferente). El chat de CRM VENTAS arranca vacío.

---

## 11. Riesgos y Decisiones de Diseño

| Riesgo | Decisión |
|--------|---------|
| Rooms Socket.IO acumulan sids si el cliente no hace `leave` (ej. cierre brusco) | Usar `disconnect` handler para limpiar todos los rooms del `sid` |
| DM visible para CEO: riesgo de privacidad | Documentar en UI con label "Supervisión CEO" explícito; es comportamiento intencional |
| Conteo no_leidos puede desincronizarse si el mensaje llega fuera del trigger | Endpoint de reconciliación: `GET /dms/{canal_id}/conteo` calcula desde tabla |
| Multi-tab del mismo usuario recibe doble badge update | Emitir `chat:badge_clear` al room personal (todos los tabs del usuario se actualizan) |
| canal_id `general` colisiona entre tenants en el room Socket.IO si no se prefixa | Room siempre con formato `chat:{tenant_id}:{canal_id}` — NO hay colisión |

---

## 12. Archivos Afectados

**Nuevos:**
- `orchestrator_service/migrations/patch_019_internal_chat.py`
- `orchestrator_service/routes/internal_chat_routes.py`
- `orchestrator_service/services/internal_chat_service.py`
- `frontend_react/src/components/internal-chat/ChatLayout.tsx`
- `frontend_react/src/components/internal-chat/ChatSidebar.tsx`
- `frontend_react/src/components/internal-chat/MensajesList.tsx`
- `frontend_react/src/components/internal-chat/MensajeBubble.tsx`
- `frontend_react/src/components/internal-chat/NotificacionCard.tsx`
- `frontend_react/src/components/internal-chat/NuevoDMDialog.tsx`
- `frontend_react/src/components/internal-chat/CeoSupervisionDialog.tsx`
- `frontend_react/src/hooks/useChatSocket.ts`
- `frontend_react/src/hooks/useChatUnread.ts`

**Modificados:**
- `orchestrator_service/core/socket_notifications.py` — agregar handlers `chat:join_canal`, `chat:leave_canal`, `chat:dm_leido`
- `orchestrator_service/main.py` — registrar `internal_chat_routes.router`
- `<modulo_llamadas>/service.py` — invocar `notificar_llamada_en_chat()` al agendar llamada

---

## 13. Criterios de Aceptación

- [ ] Los 3 canales fijos existen para cada tenant desde el primer login
- [ ] Mensajes aparecen en tiempo real en todos los clientes del mismo tenant y canal (sin reload)
- [ ] DMs son privados entre los dos participantes (vendedor no puede ver DMs ajenos)
- [ ] CEO/admin puede ver todas las convs DM del tenant desde el dialog de supervisión
- [ ] Badges de no leídos aparecen en sidebar y se limpian al abrir el DM
- [ ] Tarjetas de notificación de llamadas se visualizan correctamente en #general
- [ ] Enter envía, Shift+Enter inserta salto de línea
- [ ] Mensajes de más de 2000 caracteres son rechazados en frontend y backend
- [ ] Un usuario del tenant A no puede leer mensajes del tenant B bajo ninguna circunstancia
- [ ] Al agendar una llamada, aparece la notificación en #general automáticamente
- [ ] Todos los escenarios de prueba (01-13) pasan en CI
