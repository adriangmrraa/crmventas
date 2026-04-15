# Design F-08: Supervisor Dashboard (Real-Time)

**Spec:** `08-supervisor-realtime.spec.md`
**Archivo principal:** `frontend_react/src/modules/crm_sales/views/SupervisorDashboard.tsx`

---

## Decisiones de Arquitectura

### 1. Stats reales con polling (SUP-01)

**Problema:** Card "Actividad Total" solo muestra `messages.length`. No hay stats de sesiones activas ni ratio IA.

**Solucion:** Tres stats en columna lateral:

| Stat | Fuente | Actualizacion |
|------|--------|---------------|
| Mensajes en sesion | `messages.length` | Real-time (ya existe) |
| Conversaciones activas | `GET /admin/core/chat/sessions` | Polling 60s |
| Ratio IA vs Humano | Calculado de `messages` state | Real-time |

**Implementacion del polling:**

```ts
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
```

**Ratio IA:** Calculado en render, no en estado separado:

```ts
const aiMessages = messages.filter(m => m.role === 'assistant').length;
const aiRatio = messages.length > 0 ? Math.round((aiMessages / messages.length) * 100) : 0;
```

### 2. Alertas reales (SUP-02)

**Problema:** Card "Alertas Criticas" hardcodeada con "0 Intervenciones req." y "Buscando patrones...".

**Solucion:** Dos fuentes de alertas:

1. **Intervenciones activas:** `urgencies.filter(u => u.urgency_level === 'URGENT').length` desde el endpoint `/chat/urgencies`
2. **Esperas largas:** Calculado con `useMemo` desde `messages` state

**Calculo de esperas largas:**

```ts
const longWaitConversations = useMemo(() => {
  const byPhone = new Map<string, LiveMessage>();
  messages.forEach(m => {
    const existing = byPhone.get(m.phone_number);
    if (!existing || m.timestamp > existing.timestamp) {
      byPhone.set(m.phone_number, m);
    }
  });
  const fiveMinutesAgo = Date.now() - 5 * 60 * 1000;
  return Array.from(byPhone.values()).filter(
    m => m.role === 'user' && new Date(m.timestamp).getTime() < fiveMinutesAgo
  );
}, [messages]);
```

**Trade-off:** El calculo de esperas largas solo considera mensajes en la sesion actual del supervisor (ultimos 50). No es un indicador perfecto de TODAS las conversaciones sin respuesta, pero es suficiente para alertas live.

### 3. Boton de intervencion (SUP-03)

**Flujo:**

```
Card de mensaje -> Boton "Tomar control"
  -> POST /admin/core/chat/human-intervention { phone, tenant_id, activate: true }
  -> Agregar phone a Set<string> interventions
  -> Badge "INTERVENIDO" amarillo en la card
  -> Boton cambia a "Liberar"
    -> POST con activate: false
    -> Remover phone del Set
```

**Estado:** `interventions: Set<string>` para tracking local de phones intervenidos.

**Error handling:** try/catch con estado de error inline en la card. Si falla, mostrar toast/banner sin cambiar el Set.

### 4. Filtro por canal (SUP-04)

**Solucion:** Estado `channelFilter` con valores `'all' | 'whatsapp' | 'instagram' | 'facebook'`.

Chips renderizados sobre el live feed header:

```ts
const CHANNELS = ['all', 'whatsapp', 'instagram', 'facebook'] as const;

const filteredMessages = channelFilter === 'all'
  ? messages
  : messages.filter(m => m.channel_source === channelFilter);
```

Renderizar `filteredMessages` en lugar de `messages` en el live feed.

### 5. Diferenciacion visual por role (SUP-05)

**Problema:** Todos los mensajes usan el mismo icono violeta independientemente del role.

**Solucion:** Mapa de configuracion por role:

```ts
const roleConfig: Record<string, { bg: string; text: string; label: string; Icon: LucideIcon }> = {
  user:      { bg: 'bg-blue-500/20',    text: 'text-blue-400',    label: 'Cliente',  Icon: User },
  assistant: { bg: 'bg-violet-500/20',  text: 'text-violet-400',  label: 'IA',       Icon: Zap },
  system:    { bg: 'bg-white/10',       text: 'text-white/40',    label: 'Sistema',  Icon: ShieldAlert },
};
```

Aplicar en el avatar y agregar badge con `label` junto al channel_source badge.

### 6. Tenant selector para CEO (SUP-06)

**Problema:** `user.tenant_id` hardcodeado. CEO multi-tenant no puede cambiar.

**Solucion:**

1. Estado `selectedTenantId` inicializado con `user.tenant_id`
2. Si `user.role === 'ceo'`, fetch de tenants via `GET /admin/core/chat/tenants`
3. Selector visible solo para CEO en la columna lateral
4. Al cambiar tenant:
   - Disconnect socket actual
   - Limpiar `messages`
   - Reconectar a room `supervisors:{newTenantId}`
   - Re-fetch stats

**Impacto en socket useEffect:** Cambiar dependency de `[user]` a `[user, selectedTenantId]`. Socket se reconecta automaticamente al cambiar tenant.

### 7. Transcripciones de voz (SUP-07)

**Solucion:** Extender `LiveMessage` con `audio_transcription?: string`. Si presente, mostrar bloque colapsable debajo del contenido del mensaje:

```tsx
{msg.audio_transcription && (
  <details className="mt-2">
    <summary className="text-xs text-white/40 cursor-pointer flex items-center gap-1">
      <Mic size={12} /> Transcripcion de voz
    </summary>
    <p className="text-xs text-white/50 mt-1 pl-4 border-l border-white/10">
      {msg.audio_transcription}
    </p>
  </details>
)}
```

---

## Estado Nuevo Requerido

```ts
// REST data
const [sessions, setSessions] = useState<any[]>([]);
const [urgencies, setUrgencies] = useState<any[]>([]);
const [tenants, setTenants] = useState<{ id: number; clinic_name: string }[]>([]);

// UI state
const [channelFilter, setChannelFilter] = useState<string>('all');
const [interventions, setInterventions] = useState<Set<string>>(new Set());
const [selectedTenantId, setSelectedTenantId] = useState<number>(user?.tenant_id || 0);
const [interventionError, setInterventionError] = useState<string | null>(null);
```

---

## Interface Actualizada

```ts
interface LiveMessage {
  tenant_id: number;
  lead_id: string | null;
  phone_number: string;
  content: string;
  role: 'user' | 'assistant' | 'system';  // tipado estricto
  channel_source: string;
  is_silenced: boolean;
  timestamp: string;
  audio_transcription?: string;  // NUEVO - SUP-07
}
```

---

## Layout Final de Stats

```
[Card: Mensajes en sesion]         messages.length (real-time)
[Card: Conversaciones activas]     sessions.length (REST 60s)
[Card: Ratio IA]                   aiRatio% (calculado live)
[Card: Intervenciones activas]     urgencies URGENT count (REST 60s)
[Card: Esperas largas]             longWaitConversations.length (calculado live)
[Selector: Tenant]                 solo visible si role === 'ceo'
```

---

## Estructura del Live Feed (actualizada)

```
[Header: "Live Feed" + channel filter chips]
[Message cards con:]
  - Avatar con color/icono segun role
  - Badge de role (Cliente/IA/Sistema)
  - Badge de channel
  - Badge SILENCED (si aplica)
  - Badge INTERVENIDO (si phone en interventions Set)
  - Contenido del mensaje
  - Bloque colapsable de transcripcion (si audio_transcription)
  - Boton "Tomar control" / "Liberar"
  - Timestamp
```

---

## Riesgos

| Riesgo | Mitigacion |
|--------|------------|
| Polling cada 60s puede ser lento para alertas criticas | Socket ya provee real-time; REST complementa con datos historicos |
| Set de interventions se pierde al refrescar pagina | Aceptable -- las intervenciones persisten en backend, solo el badge visual se pierde |
| longWaitConversations solo ve ultimos 50 msgs | Documentado como limitacion; mejorable con endpoint dedicado en futuro |
| Socket reconnect al cambiar tenant puede perder mensajes | Limpiar messages es intencional -- nuevo tenant, nuevo contexto |
