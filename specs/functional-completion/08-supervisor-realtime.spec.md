# SPEC F-08: Supervisor Dashboard (Real-Time)

**Priority:** Alta
**Complexity:** Alta
**Status:** Base funcional. Socket.IO conectado y live feed operativo. Gaps en: stats reales, alertas dinámicas, tenant selector, filtros por canal, transcripciones de voz, e intervención manual.

---

## Intent

`SupervisorDashboard.tsx` ya establece conexión Socket.IO y recibe eventos `SUPERVISOR_CHAT_EVENT` en tiempo real. El live feed muestra mensajes con phone, content, role, channel y timestamp. Los gaps son todos en la capa de inteligencia: stats reales calculadas desde el live feed y APIs, alertas de clientes frustrados o con espera larga, selector de tenant para supervisores CEO, filtro por canal, display de transcripciones de voz (Whisper), y el botón de intervención que llama al backend para tomar control de una conversación.

---

## Current State

### Lo que funciona

- **Socket.IO**: conectado a `BACKEND_URL` con `io()`, join a room `supervisors:{tenant_id}` al conectar. (líneas 30-38)
- **Live feed**: `SUPERVISOR_CHAT_EVENT` agrega mensajes al estado, cappado en 50. (líneas 42-44)
- **Conexión status**: badge LIVE/DISCONNECTED con `isConnected` state. (líneas 58-64)
- **Indicador silenced**: mensajes con `is_silenced = true` se muestran con fondo rojo diferenciado. (líneas 113-117)
- **Estructura de layout**: columna de stats (1/4) + live feed (3/4). (línea 67)

### Lo que está hardcodeado / incompleto

- **Card "Actividad Total"** (línea 73): solo muestra `messages.length` de la sesión actual. No refleja actividad histórica real.
- **Card "Alertas Críticas"** (líneas 78-89): hardcodeado con "0 Intervenciones req." y "Buscando patrones..." — no conectado a datos reales.
- **Sin tenant selector**: `user.tenant_id` se usa directamente (línea 27). CEO con acceso multi-tenant no puede cambiar de empresa.
- **Sin filtros de canal**: todos los mensajes se muestran juntos sin filtro WhatsApp/Instagram/Facebook.
- **Sin `role` visual diferenciado**: el ícono de usuario es igual para todos los roles (user/assistant/system). (líneas 119-122)
- **Sin transcripciones de voz**: `LiveMessage` interface no incluye `audio_transcription`.
- **Sin botón de intervención**: no hay mecanismo en la UI para llamar a `POST /admin/core/chat/human-intervention`.
- **Sin stats de sesiones activas**: no hay llamada a `GET /admin/core/chat/sessions`.
- **Sin alertas por tiempo de espera**: ningún cálculo de tiempo desde el último mensaje de un usuario.

---

## Requirements

### MUST

- **SUP-01**: Stats reales en columna lateral:
  - "Mensajes en sesión": `messages.length` (ya existe).
  - "Conversaciones activas": calculado desde `GET /admin/core/chat/sessions` al montar y refreshado cada 60 segundos.
  - "Ratio IA vs Humano": calculado en tiempo real desde `messages` state — contar `role === 'assistant'` vs resto.
- **SUP-02**: Alertas reales — calcular desde `GET /admin/core/chat/urgencies` al montar:
  - "Intervenciones activas": count de urgencies con `urgency_level === 'URGENT'`.
  - "Largo tiempo de espera": desde `messages` state, detectar conversaciones donde el último mensaje es de `role: 'user'` y tiene más de 5 minutos de antigüedad.
- **SUP-03**: Botón de intervención en cada mensaje card. Al clickear "Tomar control":
  1. Llamar a `POST /admin/core/chat/human-intervention` con `{ phone, tenant_id, activate: true }`.
  2. Marcar la card con badge "INTERVENIDO" en amarillo.
  3. Mostrar botón "Liberar" que llama con `{ activate: false }`.
- **SUP-04**: Filtro por canal (WhatsApp/Instagram/Facebook/Todos) como tabs o chips sobre el live feed.
- **SUP-05**: Diferenciación visual por `role` en cada mensaje card:
  - `user`: ícono azul (cliente).
  - `assistant`: ícono violeta con indicador "IA" (bot).
  - `system`: ícono gris con indicador "Sistema".

### SHOULD

- **SUP-06**: Selector de tenant para usuarios con rol `ceo` que tienen acceso multi-tenant. Al cambiar el tenant, desconectar del room actual, conectar al nuevo (`supervisors:{newTenantId}`), limpiar `messages`, y re-fetchear stats.
- **SUP-07**: Transcripciones de voz — extender `LiveMessage` para incluir `audio_transcription?: string`. Si existe, mostrar un bloque colapsable con la transcripción debajo del mensaje, con ícono de micrófono.
- **SUP-08**: Límite de mensajes configurable (50/100/200) con selector en el header del live feed.
- **SUP-09**: Auto-scroll al mensaje más reciente cuando llega un nuevo evento, con override manual — si el usuario scrolleó hacia arriba, no forzar scroll.

### COULD

- **SUP-10**: Exportar el live feed de la sesión actual como JSON o CSV.
- **SUP-11**: Resaltar visualmente conversaciones con cliente frustrado (detectado por palabras clave en `content`: "enojado", "molesto", "disgusted", "frustrated" — configurable).
- **SUP-12**: Panel colapsable de detalle de sesión cuando se clickea en una card de mensaje: mostrar historial completo via `GET /admin/core/chat/messages/:phone`.

---

## API Endpoints

| Endpoint | Tipo | Estado | Uso |
|----------|------|--------|-----|
| Socket.IO `SUPERVISOR_CHAT_EVENT` | Evento | Existe | Live feed de mensajes |
| Socket.IO `join` room `supervisors:{tenant_id}` | Emit | Existe | Autenticación de room |
| `GET /admin/core/chat/sessions` | REST | Existe | Conversaciones activas |
| `GET /admin/core/chat/urgencies` | REST | Existe | Alertas de intervención activa |
| `POST /admin/core/chat/human-intervention` | REST | Existe | Tomar/liberar control de conversación |
| `GET /admin/core/chat/tenants` | REST | Existe | Lista de tenants (para CEO) |
| `GET /admin/core/chat/messages/:phone` | REST | Existe | Historial de conversación |

### Payloads existentes confirmados

`POST /admin/core/chat/human-intervention`:
```json
{ "phone": "5491112345678", "tenant_id": 1, "activate": true, "duration": 86400000 }
```
Retorna: `{ "status": "activated", "phone": "...", "tenant_id": 1, "until": "..." }`

`GET /admin/core/chat/urgencies` retorna:
```json
[{ "id": "...", "lead_name": "...", "phone": "...", "urgency_level": "URGENT", "reason": "...", "timestamp": "DD/MM HH:mm" }]
```

---

## Files to Modify

| File | Action | Motivo |
|------|--------|--------|
| `frontend_react/src/modules/crm_sales/views/SupervisorDashboard.tsx` | Modify | SUP-01 al SUP-09 |

No se requieren cambios de backend para los MUST — todos los endpoints existen.

---

## Solution

### Extender LiveMessage interface

```tsx
interface LiveMessage {
  tenant_id: number;
  lead_id: string | null;
  phone_number: string;
  content: string;
  role: 'user' | 'assistant' | 'system';
  channel_source: string;
  is_silenced: boolean;
  timestamp: string;
  audio_transcription?: string;    // SUP-07
}
```

### Estado adicional requerido

```tsx
const [sessions, setSessions] = useState<any[]>([]);
const [urgencies, setUrgencies] = useState<any[]>([]);
const [channelFilter, setChannelFilter] = useState<string>('all');
const [interventions, setInterventions] = useState<Set<string>>(new Set());
const [selectedTenantId, setSelectedTenantId] = useState<number>(user?.tenant_id || 0);
const [tenants, setTenants] = useState<{ id: number; clinic_name: string }[]>([]);
```

### SUP-01: Stats calculadas

```tsx
// Al montar y cada 60 segundos:
const fetchStats = async () => {
  const [sessionsRes, urgenciesRes] = await Promise.allSettled([
    api.get('/admin/core/chat/sessions', { params: { tenant_id: selectedTenantId } }),
    api.get('/admin/core/chat/urgencies', { params: { limit: 50 } }),
  ]);
  if (sessionsRes.status === 'fulfilled') setSessions(sessionsRes.value.data || []);
  if (urgenciesRes.status === 'fulfilled') setUrgencies(urgenciesRes.value.data || []);
};

useEffect(() => {
  fetchStats();
  const interval = setInterval(fetchStats, 60000);
  return () => clearInterval(interval);
}, [selectedTenantId]);

// Ratio IA vs Humano (calculado desde messages state):
const aiMessages = messages.filter(m => m.role === 'assistant').length;
const humanMessages = messages.filter(m => m.role === 'user').length;
const aiRatio = messages.length > 0 ? Math.round((aiMessages / messages.length) * 100) : 0;
```

### SUP-02: Alerta de tiempo de espera

```tsx
const longWaitConversations = useMemo(() => {
  const byPhone = new Map<string, LiveMessage>();
  // Tomar el mensaje más reciente de cada phone
  messages.forEach(m => {
    if (!byPhone.has(m.phone_number) || m.timestamp > byPhone.get(m.phone_number)!.timestamp) {
      byPhone.set(m.phone_number, m);
    }
  });
  const fiveMinutesAgo = Date.now() - 5 * 60 * 1000;
  return Array.from(byPhone.values()).filter(
    m => m.role === 'user' && new Date(m.timestamp).getTime() < fiveMinutesAgo
  );
}, [messages]);
```

### SUP-03: Botón de intervención

```tsx
const handleIntervention = async (msg: LiveMessage) => {
  const isActive = interventions.has(msg.phone_number);
  await api.post('/admin/core/chat/human-intervention', {
    phone: msg.phone_number,
    tenant_id: msg.tenant_id,
    activate: !isActive,
  });
  setInterventions(prev => {
    const next = new Set(prev);
    isActive ? next.delete(msg.phone_number) : next.add(msg.phone_number);
    return next;
  });
};
```

Mostrar en la card:
```tsx
<button onClick={() => handleIntervention(msg)} className={interventions.has(msg.phone_number) ? 'btn-danger' : 'btn-warning'}>
  {interventions.has(msg.phone_number) ? 'Liberar' : 'Tomar control'}
</button>
```

### SUP-04: Filtro por canal

```tsx
const CHANNELS = ['all', 'whatsapp', 'instagram', 'facebook'];

const filteredMessages = channelFilter === 'all'
  ? messages
  : messages.filter(m => m.channel_source === channelFilter);
```

Renderizar chips sobre el live feed:
```tsx
{CHANNELS.map(ch => (
  <button
    key={ch}
    onClick={() => setChannelFilter(ch)}
    className={`px-3 py-1 rounded-full text-xs font-bold transition-all ${
      channelFilter === ch ? 'bg-violet-500 text-white' : 'bg-white/5 text-white/40 hover:bg-white/10'
    }`}
  >
    {ch === 'all' ? 'Todos' : ch.charAt(0).toUpperCase() + ch.slice(1)}
  </button>
))}
```

### SUP-05: Diferenciación visual por role

```tsx
const roleConfig = {
  user:      { bg: 'bg-blue-500/20',   text: 'text-blue-400',   label: 'Cliente' },
  assistant: { bg: 'bg-violet-500/20', text: 'text-violet-400', label: 'IA' },
  system:    { bg: 'bg-white/10',      text: 'text-white/40',   label: 'Sistema' },
};

const config = roleConfig[msg.role] ?? roleConfig.system;
// Usar config.bg y config.text en el avatar, mostrar config.label como badge
```

### SUP-06: Tenant selector (CEO)

```tsx
// Al montar, si role === 'ceo':
useEffect(() => {
  if (user?.role === 'ceo') {
    api.get('/admin/core/chat/tenants').then(r => setTenants(r.data || []));
  }
}, []);

// Cuando selectedTenantId cambia:
useEffect(() => {
  if (!user || !selectedTenantId) return;
  const socket = io(BACKEND_URL);
  socketRef.current = socket;
  socket.on('connect', () => {
    setIsConnected(true);
    socket.emit('join', { room: `supervisors:${selectedTenantId}` });
  });
  // ... resto del setup
  return () => socket.disconnect();
}, [selectedTenantId]);
```

---

## Layout Final de la Columna de Stats

```
[Card: Mensajes en sesión]         messages.length
[Card: Conversaciones activas]     sessions.length (REST, refresh 60s)
[Card: Ratio IA]                   aiRatio% calculado live
[Card: Intervenciones activas]     urgencies.length (URGENT)
[Card: Esperas largas]             longWaitConversations.length (> 5 min)
[Selector: Tenant]                 solo visible si role === 'ceo'
```

---

## Acceptance Criteria

- [ ] Card "Conversaciones activas" muestra datos reales de `GET /admin/core/chat/sessions`, refrescados cada 60 segundos.
- [ ] Card "Ratio IA" muestra el porcentaje calculado desde los mensajes del live feed de la sesión actual.
- [ ] Card "Intervenciones activas" muestra el count de urgencies desde `/admin/core/chat/urgencies`.
- [ ] Card "Esperas largas" muestra cuántas conversaciones tienen el último mensaje de `role: 'user'` con más de 5 minutos de antigüedad.
- [ ] Filtro por canal (WhatsApp/Instagram/Facebook/Todos) filtra el live feed client-side sin API call.
- [ ] Cada mensaje card muestra el role con color y label diferenciado (Cliente/IA/Sistema).
- [ ] Botón "Tomar control" en una card llama a `POST /admin/core/chat/human-intervention` con `activate: true`.
- [ ] Tras tomar control, el botón cambia a "Liberar" (color rojo/danger).
- [ ] Botón "Liberar" llama al mismo endpoint con `activate: false`.
- [ ] Selector de tenant aparece solo cuando `user.role === 'ceo'`.
- [ ] Cambiar tenant en selector reconecta el socket al nuevo room `supervisors:{newTenantId}` y limpia el live feed.
- [ ] Si existe `audio_transcription` en el evento, se muestra un bloque colapsable con la transcripción.
- [ ] Live feed muestra badge "SILENCED" en rojo cuando `is_silenced = true` (ya existe, verificar sin regresión).
- [ ] Conexión status badge LIVE/DISCONNECTED sigue funcionando (sin regresión).

---

## Testing Strategy

- **Unit**: Renderizar con `messages` que incluyen 3 `role: 'assistant'` y 1 `role: 'user'` → Card "Ratio IA" muestra 75%.
- **Unit**: `longWaitConversations` con mensaje de `role: 'user'` con timestamp de hace 10 minutos → incluido en resultado.
- **Unit**: `longWaitConversations` con mensaje de `role: 'assistant'` de hace 10 minutos → NO incluido.
- **Unit**: Click en "Tomar control" → `api.post` fue llamado con `activate: true` y el phone correcto.
- **Unit**: Click en "Liberar" (intervention activo) → `api.post` fue llamado con `activate: false`.
- **Unit**: `channelFilter === 'whatsapp'` → solo mensajes con `channel_source === 'whatsapp'` en `filteredMessages`.
- **Unit**: Renderizar con `user.role = 'seller'` → selector de tenant NO visible.
- **Unit**: Renderizar con `user.role = 'ceo'` → selector de tenant visible y carga `/admin/core/chat/tenants`.
- **Integration**: Simular `SUPERVISOR_CHAT_EVENT` con `role: 'assistant'` → card renderizada con avatar violeta y label "IA".
- **Edge case**: Socket desconectado → badge DISCONNECTED, live feed mantiene mensajes previos (no se limpia).
- **Edge case**: `GET /admin/core/chat/sessions` retorna error → Card "Conversaciones activas" muestra "--" sin crash.
- **Edge case**: Cambiar tenant en selector → `messages` se limpia, nuevo socket se conecta al room correcto.
