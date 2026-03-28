# SPEC: Comunicación — Menciones @usuario en Notas Internas con Notificación Inmediata

**Ticket:** DEV-43
**Fecha:** 2026-03-28
**Prioridad:** Media-Alta
**Esfuerzo:** Medio (3-4 dias)
**Confidence:** 90%

---

## 1. Contexto

Las notas internas de un lead (`lead_notes`) son el canal de comunicación setter-closer. Actualmente solo se emiten eventos Socket.IO genéricos. No hay forma de llamar la atención de un compañero específico sobre una nota urgente.

Las menciones `@usuario` permiten:
- Notificar inmediatamente al mencionado vía push + socket
- Resaltar visualmente las menciones en el texto
- Crear un flujo de comunicación directa dentro del contexto del lead

### Estado actual

| Componente | Estado |
|------------|--------|
| `lead_notes` tabla con content TEXT | Existente |
| `seller_notification_service` con push | Existente |
| Socket.IO `LEAD_NOTE_CREATED` event | Existente |
| `activity_events` (DEV-39) | Existente |
| Parser de @menciones en backend | **NO existe** |
| Autocomplete de usuarios en frontend | **NO existe** |
| Notificación por mención | **NO existe** |
| Resaltado visual de @menciones | **NO existe** |

---

## 2. Requerimientos Técnicos

### 2.1 Backend: Parser de menciones

Al crear una nota, el backend:
1. Parsea el contenido buscando `@nombre` o `@{nombre completo}`
2. Resuelve cada mención contra usuarios del tenant
3. Para cada mención resuelta: crea notificación y emite via WebSocket

**Tabla auxiliar:** `note_mentions` (opcional, para tracking)
```sql
CREATE TABLE IF NOT EXISTS note_mentions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    note_id UUID NOT NULL REFERENCES lead_notes(id) ON DELETE CASCADE,
    mentioned_user_id UUID NOT NULL REFERENCES users(id),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 2.2 Backend: Endpoint de búsqueda de usuarios

#### `GET /admin/core/users/search?q=tom`
Busca usuarios del tenant por nombre parcial (para autocomplete).
Devuelve: `[{id, name, role}]`

### 2.3 Backend: Modificar create_note

En `lead_notes_routes.py`, después de crear la nota:
1. Llamar a `parse_mentions(content, tenant_id)` → lista de user_ids
2. Para cada mentioned_user_id:
   - Insertar en `note_mentions`
   - Crear `Notification` tipo `mention` al mencionado
   - Emitir Socket.IO event `NOTE_MENTION` al mencionado

### 2.4 Frontend: Autocomplete @usuario

En el campo de texto de las notas:
1. Cuando el usuario escribe `@`, mostrar un dropdown con usuarios del tenant
2. Filtrar en tiempo real mientras sigue escribiendo
3. Al seleccionar, insertar `@{Nombre Completo}` en el texto
4. Resaltar visualmente las menciones con color diferente

### 2.5 Frontend: Renderizado de menciones

Al mostrar notas en el timeline del lead:
- Las menciones `@{Nombre}` se renderizan como badge/pill con color destacado
- Si el usuario actual es el mencionado, el badge tiene color diferente (azul vs gris)

---

## 3. Criterios de Aceptación

### Scenario 1: Escribir mención con autocomplete
```gherkin
Given el setter está escribiendo una nota en el lead #342
When escribe "@tom"
Then aparece un dropdown con usuarios que coinciden: "Tomás García (setter)"
When selecciona "Tomás García"
Then el texto muestra "@Tomás García" resaltado en el input
```

### Scenario 2: Notificación al mencionado
```gherkin
Given el setter crea la nota "Ojo @Tomás García, este lead pidió presupuesto urgente"
Then Tomás García recibe una notificación: "Te mencionaron en una nota del lead #342"
And la notificación tiene link directo al lead
```

### Scenario 3: Renderizado visual
```gherkin
Given el closer ve la nota "@Tomás García revisó el presupuesto"
Then "@Tomás García" se muestra como un badge azul destacado
And el resto del texto se muestra normal
```

### Scenario 4: Múltiples menciones
```gherkin
Given la nota contiene "@Tomás García y @Lucía Fernández revisar esto"
Then ambos usuarios reciben notificaciones individuales
And ambas menciones se renderizan como badges
```

### Scenario 5: Mención inválida
```gherkin
Given la nota contiene "@UsuarioInexistente"
Then no se envía notificación
And el texto se muestra como texto plano (sin badge)
```

---

## 4. Esquema de Datos

### Nueva tabla: `note_mentions`
```sql
CREATE TABLE IF NOT EXISTS note_mentions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    note_id UUID NOT NULL REFERENCES lead_notes(id) ON DELETE CASCADE,
    mentioned_user_id UUID NOT NULL REFERENCES users(id),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_note_mentions_user ON note_mentions (mentioned_user_id, created_at DESC);
CREATE INDEX idx_note_mentions_note ON note_mentions (note_id);
```

---

## 5. Riesgos y Mitigación

| Riesgo | Mitigación |
|--------|------------|
| Abuso de menciones (spam) | Rate limit: max 5 menciones por nota |
| Mención a usuario de otro tenant | Filtrar SIEMPRE por tenant_id |
| Performance del autocomplete | ILIKE con índice GIN en names, limit 10 |

---

## 6. Fuera de Alcance (v1)
- Menciones en chat (solo en notas de lead)
- Responder directamente a una mención
- Desactivar menciones por preferencia del usuario
- Menciones a roles completos (@setters, @closers)
