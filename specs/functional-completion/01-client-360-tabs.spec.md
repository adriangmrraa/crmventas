# SPEC F-01: Client 360° Tabs — Notes, Calls, WhatsApp

**Prioridad:** Alta
**Complejidad:** Media
**Estado:** Pendiente de implementación
**Archivo de referencia:** `frontend_react/src/modules/crm_sales/views/ClientDetailView.tsx`

---

## Intent

`ClientDetailView` ya tiene estructura de 5 tabs y los tabs Data y Drive son completamente funcionales. Los tabs **Notes**, **Calls** y **WhatsApp** muestran solo el placeholder i18n (`t('client360.notes_placeholder')`, etc.) sin lógica real. Esta spec define la implementación completa de esos tres tabs conectados al backend real.

---

## Estado Actual (Discovery)

### Lo que existe en el frontend:
- `ClientDetailView.tsx` — estructura de tabs completa, state `activeTab`, `clientNotes`, `clientCalls` ya declarados pero sin uso real
- `LeadNotesThread.tsx` — componente de notas ya implementado para `LeadDetailView` (re-usable)
- `DriveExplorer.tsx` — ejemplo de componente de tab funcional (patrón a seguir)
- `api/axios.ts` — instancia axios con baseURL y auth headers

### Lo que existe en el backend:

**Notes (completamente implementado — DEV-21 + DEV-23):**
- `GET /admin/core/crm/leads/{lead_id}/notes` — lista notas con author info, visibility, paginación
- `POST /admin/core/crm/leads/{lead_id}/notes` — crea nota, emite `LEAD_NOTE_CREATED` via Socket.IO
- `PUT /admin/core/crm/leads/{lead_id}/notes/{note_id}` — edita nota (solo autor, ventana 15 min)
- `DELETE /admin/core/crm/leads/{lead_id}/notes/{note_id}` — soft-delete (autor o CEO)

**WhatsApp:**
- `GET /admin/core/chat/messages/{phone}` — historial de mensajes del lead (query param `tenant_id`, `limit`, `offset`)
- `POST /admin/core/chat/send` — envía mensaje libre (body: `{ phone, message, channel }`)
- Socket.IO event `NEW_MESSAGE` — mensaje nuevo en tiempo real

**Calls:**
- NO existe endpoint dedicado en el backend para historial de llamadas. Los datos de llamadas pueden estar en `lead_notes` con `note_type = 'post_call'` o en actividad del team.
- Alternativa: usar `GET /admin/core/team-activity` filtrando por `lead_id` y tipo `call_logged`

### Lo que NO existe aún:
- Endpoint dedicado `/admin/core/crm/leads/{id}/calls` — DEBE CREARSE o usar notas `post_call` como proxy
- Widget de registro de llamada con resultado/reagenda

---

## Requirements

### MUST (crítico)

#### Notes Tab
- M1. Cargar notas via `GET /admin/core/crm/leads/{id}/notes` al activar el tab
- M2. Mostrar timeline cronológico (ASC) con author badge (nombre + rol + color por rol: setter=blue, closer=green, ceo=purple)
- M3. Formulario de creación: textarea + selector `note_type` (internal/post_call/follow_up/handoff) + selector `visibility` (setter_closer/all/private) + botón submit
- M4. Actualización en tiempo real via Socket.IO evento `LEAD_NOTE_CREATED` (join room `lead:{id}`)
- M5. Soft-delete de nota propia (con confirmación) — ocultar botón delete si no es autor o CEO
- M6. Edit inline de nota propia dentro de ventana de 15 minutos (contador regresivo visible)
- M7. Loading state y error boundary por tab (error en Notes no rompe Calls ni WhatsApp)

#### WhatsApp Tab
- M8. Cargar mensajes via `GET /admin/core/chat/messages/{phone}?tenant_id=N&limit=50`
- M9. Mostrar burbujas: mensajes `role=user` a la izquierda (inbound), `role=assistant` a la derecha (outbound)
- M10. Timestamps visibles bajo cada burbuja (formato local)
- M11. Formulario de envío: textarea + botón enviar — usa `POST /admin/core/chat/send`
- M12. Scroll to bottom automático al cargar y al recibir mensaje nuevo
- M13. Socket.IO `NEW_MESSAGE` — agregar burbuja en tiempo real si `phone === lead.phone_number`

#### Calls Tab
- M14. Mostrar historial de llamadas como notas `note_type='post_call'` filtradas desde `/notes`
- M15. Formulario "Registrar llamada": fecha/hora (datetime-local), resultado (select: connected/no_answer/voicemail/rescheduled), duración (minutos), notas libres
- M16. Al guardar: crea una nota `note_type='post_call'` con `structured_data: { call_result, duration_minutes, scheduled_at }`
- M17. Si resultado es `rescheduled`: mostrar campo de reagenda con datetime-local

#### Cross-cutting
- M18. Patrón `Promise.allSettled` — precargar los 3 tabs en paralelo al montar el componente, sin bloquear entre sí
- M19. Cada tab muestra su propio skeleton/spinner mientras carga
- M20. Re-fetch al activar un tab si hay error previo (retry on tab click)

### SHOULD (deseable)
- S1. Paginación en Notes tab: botón "cargar más" (offset-based, 50 notas por página)
- S2. Filtro por `note_type` en Notes tab (chip filters)
- S3. Indicador de mensajes no leídos en tab header de WhatsApp
- S4. Preview del structured_data de llamadas (chips de resultado con colores)
- S5. Menciones (@usuario) en textarea de notas con autocompletado (si `parse_and_notify_mentions` ya existe en backend)

---

## API Endpoints

| Método | Path | Descripción | Estado Backend |
|--------|------|-------------|----------------|
| GET | `/admin/core/crm/leads/{id}/notes` | Lista notas del lead | Implementado |
| POST | `/admin/core/crm/leads/{id}/notes` | Crea nota | Implementado |
| PUT | `/admin/core/crm/leads/{id}/notes/{note_id}` | Edita nota | Implementado |
| DELETE | `/admin/core/crm/leads/{id}/notes/{note_id}` | Soft-delete nota | Implementado |
| GET | `/admin/core/chat/messages/{phone}` | Historial WhatsApp | Implementado |
| POST | `/admin/core/chat/send` | Envía mensaje | Implementado |

**Nota sobre Calls:** No existe endpoint de calls dedicado. La solución es usar `/notes` con `note_type=post_call`. El tab Calls hace GET a las mismas notas filtrando `?note_type=post_call` y POST con `note_type: 'post_call'` al crear.

### Tipos de respuesta relevantes

**NoteResponse** (del backend):
```typescript
interface Note {
  id: string;
  lead_id: string;
  author_id: string | null;
  author_name: string | null;
  author_role: string | null;
  note_type: 'handoff' | 'post_call' | 'internal' | 'follow_up';
  content: string;
  structured_data: Record<string, unknown>;
  visibility: 'setter_closer' | 'all' | 'private';
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
}
```

**ChatMessage** (de admin_routes):
```typescript
interface ChatMessage {
  id: string;
  from_number: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  tenant_id: number;
}
```

---

## React Components

### Nuevos componentes a crear

```
frontend_react/src/modules/crm_sales/components/client360/
├── NotesTab.tsx          — Timeline + formulario de notas
├── CallsTab.tsx          — Historial + registro de llamada
├── WhatsAppTab.tsx       — Burbujas + formulario de envío
├── NoteItem.tsx          — Item de nota con author badge, edit, delete
├── CallResultBadge.tsx   — Chip colorido por resultado de llamada
└── WhatsAppBubble.tsx    — Burbuja de mensaje (inbound/outbound)
```

### Modificación requerida

**`ClientDetailView.tsx`:**
1. Reemplazar los 3 bloques placeholder por los nuevos componentes
2. Implementar `Promise.allSettled` en `useEffect` al montar
3. Pasar `client.id` (como `leadId`) y `client.phone_number` como props

```typescript
// Patrón Promise.allSettled a implementar
useEffect(() => {
  if (!client) return;
  Promise.allSettled([
    fetchNotes(client.id),
    fetchCalls(client.id),
    fetchMessages(client.phone_number),
  ]).then(([notesResult, callsResult, msgsResult]) => {
    // cada resultado independiente
  });
}, [client]);
```

---

## Scenarios

### SC-01: Usuario abre Notes tab — carga exitosa
**Dado** que existe un lead con 3 notas en el backend
**Cuando** el usuario hace click en el tab "Notas"
**Entonces** se muestran las 3 notas en orden cronológico ascendente, cada una con author badge de color según rol, y el formulario de nueva nota está habilitado.

### SC-02: Usuario crea nota — actualización en tiempo real
**Dado** que dos usuarios (setter y closer) ven el mismo lead simultáneamente
**Cuando** el setter crea una nota
**Entonces** el closer recibe la nota via Socket.IO `LEAD_NOTE_CREATED` sin recargar la página, y el setter ve la nota agregada al final del timeline.

### SC-03: Usuario intenta editar nota fuera de ventana de 15 min
**Dado** que una nota fue creada hace 20 minutos
**Cuando** el autor hace click en el botón editar
**Entonces** el backend retorna 403 con mensaje "Edit window expired" y el frontend muestra un toast de error, sin ocultar el botón (visually disabled with tooltip).

### SC-04: Notes tab falla pero WhatsApp tab carga
**Dado** que el endpoint de notas retorna 500 (error de DB)
**Cuando** se precarga con `Promise.allSettled`
**Entonces** el tab Notes muestra un estado de error con botón "Reintentar", pero el tab WhatsApp carga normalmente con el historial de mensajes.

### SC-05: Usuario envía mensaje WhatsApp
**Dado** que el lead tiene número de teléfono `+5491112345678`
**Cuando** el usuario escribe "Hola, ¿cómo estás?" y hace click en Enviar
**Entonces** la burbuja se agrega optimísticamente a la derecha, `POST /admin/core/chat/send` se llama con `{ phone: "+5491112345678", message: "Hola, ¿cómo estás?", channel: "whatsapp" }`, y el botón vuelve a estar habilitado.

### SC-06: Registro de llamada con reagenda
**Dado** que el usuario está en el tab Calls
**Cuando** completa el formulario: resultado = "rescheduled", fecha = "2026-04-20 10:00", notas = "Le interesa pero quiere pensar"
**Entonces** se crea una nota `note_type='post_call'` con `structured_data: { call_result: "rescheduled", scheduled_at: "2026-04-20T10:00:00", duration_minutes: null }` y la llamada aparece en el historial del tab Calls.

### SC-07: WhatsApp sin número de teléfono
**Dado** que un cliente fue creado sin número de teléfono
**Cuando** el usuario abre el tab WhatsApp
**Entonces** el tab muestra un estado vacío: "Este cliente no tiene número de WhatsApp registrado" sin intentar el fetch y sin mostrar el formulario de envío.

---

## Testing Strategy

### Unit Tests (Vitest + Testing Library)
- `NotesTab.test.tsx`: render con notas, render sin notas, crear nota, delete nota, error state
- `WhatsAppTab.test.tsx`: render burbujas inbound/outbound, envío de mensaje, estado sin teléfono
- `CallsTab.test.tsx`: filtrado `note_type=post_call`, formulario registro llamada, campo reagenda condicional

### Integration Tests
- Mock axios: verificar que `Promise.allSettled` hace 3 requests simultáneos
- Mock Socket.IO: verificar que `LEAD_NOTE_CREATED` agrega nota al state sin duplicados
- Verificar que error en un tab no afecta los otros

### E2E (si aplica)
- Flujo completo: abrir ClientDetail → abrir Notes → crear nota → verificar aparece en timeline

---

## Files to Modify

| Archivo | Tipo de cambio |
|---------|----------------|
| `frontend_react/src/modules/crm_sales/views/ClientDetailView.tsx` | Modificar — reemplazar placeholders, agregar Promise.allSettled |
| `frontend_react/src/modules/crm_sales/components/client360/NotesTab.tsx` | Crear |
| `frontend_react/src/modules/crm_sales/components/client360/CallsTab.tsx` | Crear |
| `frontend_react/src/modules/crm_sales/components/client360/WhatsAppTab.tsx` | Crear |
| `frontend_react/src/modules/crm_sales/components/client360/NoteItem.tsx` | Crear |
| `frontend_react/src/modules/crm_sales/components/client360/CallResultBadge.tsx` | Crear |
| `frontend_react/src/modules/crm_sales/components/client360/WhatsAppBubble.tsx` | Crear |

---

## Acceptance Criteria

- [ ] Notes tab carga y muestra notas reales desde el backend
- [ ] Se puede crear una nota desde el formulario y aparece en el timeline
- [ ] Las notas se actualizan en tiempo real via Socket.IO sin recargar
- [ ] Notes tab muestra error state si el backend falla, sin romper los otros tabs
- [ ] WhatsApp tab muestra historial de mensajes con burbujas inbound/outbound
- [ ] Envío de mensaje WhatsApp funciona y agrega burbuja optimísticamente
- [ ] Calls tab filtra y muestra notas `post_call` como historial de llamadas
- [ ] Registro de llamada crea nota `post_call` con `structured_data` correcto
- [ ] Campo reagenda aparece condicionalmente cuando resultado = `rescheduled`
- [ ] Todos los tabs muestran skeleton mientras cargan
- [ ] No hay regresiones en tabs Data y Drive

---

## Notas Técnicas

- El `ClientDetailView` usa el `id` de la URL como `clientId`. En el backend, los clientes CRM son leads con `status='ganado'` o similar, por lo que el endpoint de notas acepta el mismo UUID.
- El endpoint `GET /admin/core/chat/messages/{phone}` requiere `tenant_id` como query param — obtenerlo del contexto `AuthContext` (`user.tenant_id`).
- Para Socket.IO: usar el `SocketContext` existente en `frontend_react/src/context/SocketContext.tsx` — hacer `socket.emit('join_lead', { lead_id: id })` y escuchar `LEAD_NOTE_CREATED`.
- El `LeadNotesThread.tsx` existente puede servir de referencia de implementación pero tiene acoplamiento con `LeadDetailView`; se recomienda crear componentes nuevos en `client360/` para evitar regresión.
