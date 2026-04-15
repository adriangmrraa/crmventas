# Design F-01: Client 360° Tabs — Notes, Calls, WhatsApp

**Spec:** `01-client-360-tabs.spec.md`
**Fecha:** 2026-04-14

---

## Component Tree

```
ClientDetailView.tsx (existente)
├── DataTab (existente — formulario datos personales)
├── NotesTab.tsx (NUEVO)
│   ├── NoteItem.tsx (NUEVO) — nota individual con author badge, edit, delete
│   └── NoteForm (inline) — textarea + note_type + visibility + submit
├── CallsTab.tsx (NUEVO)
│   ├── NoteItem.tsx (reusado, filtrado note_type=post_call)
│   ├── CallResultBadge.tsx (NUEVO) — chip con color por resultado
│   └── CallLogForm (inline) — datetime + resultado + duracion + notas
├── WhatsAppTab.tsx (NUEVO)
│   ├── WhatsAppBubble.tsx (NUEVO) — burbuja inbound/outbound
│   └── MessageInput (inline) — textarea + boton enviar
└── DriveExplorer.tsx (existente)
```

### Ubicacion de archivos nuevos

```
frontend_react/src/modules/crm_sales/components/client360/
├── NotesTab.tsx
├── CallsTab.tsx
├── WhatsAppTab.tsx
├── NoteItem.tsx
├── CallResultBadge.tsx
└── WhatsAppBubble.tsx
```

---

## Data Flow: Lead ID desde Client

El `ClientDetailView` usa `client.id` de la URL. En el backend, los clientes CRM son leads promovidos — el mismo UUID funciona como `lead_id` para los endpoints de notas.

```
ClientDetailView
  |-- client.id -----------> GET /admin/core/crm/leads/{id}/notes     (Notes + Calls)
  |-- client.phone_number -> GET /admin/core/chat/messages/{phone}     (WhatsApp)
  |-- user.tenant_id ------> query param tenant_id para chat messages
```

**Importante:** No hay indirection. El `id` del cliente ES el `lead_id` que acepta el backend.

---

## API Endpoints por Tab

### Notes Tab

| Accion | Metodo | Endpoint | Body/Query |
|--------|--------|----------|------------|
| Listar notas | GET | `/admin/core/crm/leads/{id}/notes` | `?limit=50&offset=0` |
| Crear nota | POST | `/admin/core/crm/leads/{id}/notes` | `{ content, note_type, visibility }` |
| Editar nota | PUT | `/admin/core/crm/leads/{id}/notes/{note_id}` | `{ content }` |
| Eliminar nota | DELETE | `/admin/core/crm/leads/{id}/notes/{note_id}` | — |

### Calls Tab

| Accion | Metodo | Endpoint | Body/Query |
|--------|--------|----------|------------|
| Listar llamadas | GET | `/admin/core/crm/leads/{id}/notes` | `?note_type=post_call` |
| Registrar llamada | POST | `/admin/core/crm/leads/{id}/notes` | `{ content, note_type: 'post_call', structured_data: { call_result, duration_minutes, scheduled_at? } }` |

### WhatsApp Tab

| Accion | Metodo | Endpoint | Body/Query |
|--------|--------|----------|------------|
| Historial mensajes | GET | `/admin/core/chat/messages/{phone}` | `?tenant_id=N&limit=50&offset=0` |
| Enviar mensaje | POST | `/admin/core/chat/send` | `{ phone, message, channel: "whatsapp" }` |

---

## Socket.IO — Eventos Real-Time

### Notes (LEAD_NOTE_CREATED)

```typescript
// Al montar NotesTab:
socket.emit('join_lead', { lead_id: clientId });

// Listener:
socket.on('LEAD_NOTE_CREATED', (note: Note) => {
  if (note.lead_id === clientId) {
    setNotes(prev => {
      // Dedup por id para evitar duplicados con la respuesta del POST
      if (prev.some(n => n.id === note.id)) return prev;
      return [...prev, note];
    });
  }
});

// Cleanup al desmontar:
socket.emit('leave_lead', { lead_id: clientId });
socket.off('LEAD_NOTE_CREATED');
```

### WhatsApp (NEW_MESSAGE)

```typescript
socket.on('NEW_MESSAGE', (msg: ChatMessage) => {
  if (msg.from_number === clientPhone) {
    setMessages(prev => [...prev, msg]);
    scrollToBottom();
  }
});
```

---

## State Management

### En ClientDetailView (orquestador)

```typescript
// Estado por tab — independiente para fault tolerance
const [notesState, setNotesState] = useState<TabState>({ data: [], loading: true, error: null });
const [callsState, setCallsState] = useState<TabState>({ data: [], loading: true, error: null });
const [whatsappState, setWhatsappState] = useState<TabState>({ data: [], loading: true, error: null });

// Precarga paralela al montar
useEffect(() => {
  if (!client) return;
  Promise.allSettled([
    fetchNotes(client.id),
    fetchCalls(client.id),
    fetchMessages(client.phone_number),
  ]).then(([notes, calls, msgs]) => {
    // Cada resultado se procesa independientemente
    // fulfilled -> setData, rejected -> setError
  });
}, [client]);
```

### Dentro de cada Tab (local state)

Cada tab maneja su propio estado de formulario internamente:
- `NotesTab`: `newNoteContent`, `noteType`, `visibility`, `editingNoteId`
- `CallsTab`: `callResult`, `duration`, `scheduledAt`, `callNotes`
- `WhatsAppTab`: `messageText`, `sending`

### Tipo compartido

```typescript
interface TabState<T> {
  data: T[];
  loading: boolean;
  error: string | null;
}
```

---

## Error Handling — Fault Tolerant por Tab

Principio: **un tab que falla NO rompe a los demas.**

```
Promise.allSettled garantiza:
  - Notes falla (500) -> Notes muestra error + boton retry
  - Calls carga OK    -> Calls muestra datos normalmente
  - WhatsApp carga OK -> WhatsApp muestra datos normalmente
```

### Patron por tab

```typescript
// Dentro de cada tab component:
if (error) {
  return (
    <div className="error-state">
      <AlertCircle />
      <p>{error}</p>
      <button onClick={onRetry}>Reintentar</button>
    </div>
  );
}

if (loading) {
  return <TabSkeleton />;
}
```

### Retry on tab click (M20)

```typescript
// En ClientDetailView, al cambiar de tab:
const handleTabChange = (tab: TabKey) => {
  setActiveTab(tab);
  // Si el tab tenia error previo, re-fetch
  if (tab === 'notes' && notesState.error) fetchNotes(client.id);
  if (tab === 'calls' && callsState.error) fetchCalls(client.id);
  if (tab === 'whatsapp' && whatsappState.error) fetchMessages(client.phone_number);
};
```

---

## Decisiones de Diseno

1. **Componentes nuevos en `client360/`**, no reusar `LeadNotesThread` directamente — el componente existente tiene acoplamiento con `LeadDetailView` y mezcla tipos (`general`, `handoff`, `post_call`, `system`). Los nuevos componentes son mas enfocados.

2. **NoteItem reutilizado** entre NotesTab y CallsTab — la unica diferencia es el filtro `note_type` y el badge de resultado en Calls.

3. **Optimistic update en WhatsApp** — al enviar mensaje, agregar burbuja inmediatamente a la derecha. Si el POST falla, marcar la burbuja con error y dar opcion de retry.

4. **Socket context existente** — usar `useSocket()` de `SocketContext.tsx`, NO crear nueva conexion.

5. **Edit window 15 min** — el backend valida, pero el frontend muestra un countdown visual. Calcular `15min - (now - created_at)` y deshabilitar el boton cuando llega a 0.

6. **ROLE_COLORS** — reusar el mapa de colores de `LeadNotesThread` (setter=violet, closer=green, ceo=purple).
