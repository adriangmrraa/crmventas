# FIX-04: Supervisor Dashboard — Alertas Reales

## Intent

Reemplazar las 3 tarjetas de alerta hardcodeadas en el dashboard de supervisor con datos reales calculados desde las APIs existentes, y agregar actualizaciones en tiempo real via Socket.IO.

## Requirements

### MUST

- **Card 1 "Intervenciones"**: Contar conversaciones donde `human_override` esta activo hoy. API: `GET /admin/core/chat/sessions` y filtrar por `human_override === true`.
- **Card 2 "Patrones"**: Contar conversaciones con alta urgencia o sentimiento negativo. Derivar desde datos existentes de lead scoring o chat sessions.
- **Card 3 "Tiempo de Respuesta"**: Calcular tiempo promedio de respuesta desde chat sessions.
- Actualizar las cards en tiempo real via `SUPERVISOR_CHAT_EVENT` (ya existe y esta conectado en linea 42).
- Agregar filtro por periodo de tiempo: Hoy / Esta semana.

### SHOULD

- Mostrar indicador de tendencia (flecha arriba/abajo) comparando con periodo anterior.
- Mostrar mini-sparkline o numero destacado cuando el valor cambia en tiempo real (animacion).
- Las cards deben ser clickeables para navegar a vista filtrada del detalle.

## Current State (lo que esta roto)

En `SupervisorDashboard.tsx`:

- **Lineas 78-90**: Dos cards dentro de `GlassCard` con datos hardcodeados:
  ```tsx
  // Card "Alertas Criticas"
  <div className="flex items-center gap-2 text-yellow-500">
    <ShieldAlert size={14} />
    <span className="text-xs font-medium">0 Intervenciones req.</span>  // HARDCODED
  </div>
  <div className="flex items-center gap-2 text-violet-400">
    <Zap size={14} />
    <span className="text-xs font-medium">Buscando patrones...</span>  // HARDCODED
  </div>
  ```
- No hay Card 3 (Tiempo de Respuesta) — solo existen 2 cards en la columna de stats.
- No hay calculo real de ninguna metrica — todo es estatico.
- El socket `SUPERVISOR_CHAT_EVENT` (linea 42) solo alimenta el live feed, no las cards de metricas.

## Solution

### 1. Agregar estado para metricas del supervisor

```tsx
interface SupervisorMetrics {
  interventions_today: number;
  high_urgency_count: number;
  avg_response_time_seconds: number;
}

const [metrics, setMetrics] = useState<SupervisorMetrics>({
  interventions_today: 0,
  high_urgency_count: 0,
  avg_response_time_seconds: 0,
});
const [timePeriod, setTimePeriod] = useState<'today' | 'week'>('today');
```

### 2. Cargar metricas reales al montar

```
Al montar el componente:
1. GET /admin/core/chat/sessions → filtrar por tenant_id y periodo
2. Contar sessions con human_override === true → interventions_today
3. Contar sessions con urgency === 'high' o sentiment === 'negative' → high_urgency_count
4. Calcular promedio de (first_response_at - created_at) → avg_response_time_seconds
```

Si el backend no expone un endpoint agregado, hacer el calculo client-side con los datos de sessions. Alternativamente, crear un endpoint nuevo `GET /admin/core/chat/supervisor-metrics?period=today` que retorne las metricas pre-calculadas (mejor performance).

### 3. Actualizar metricas en tiempo real

Cuando llega un `SUPERVISOR_CHAT_EVENT`:
- Si `msg.is_silenced === true` o tiene flag de override → incrementar `interventions_today`.
- Recalcular `avg_response_time_seconds` con el nuevo mensaje.
- Actualizar el state para que las cards reflejen el cambio.

### 4. Redisenar la columna de stats

```
Layout de la columna (lg:col-span-1):

[Card: Actividad Total]        ← ya existe (messages.length)
[Card: Intervenciones]         ← NUEVO: interventions_today con icono ShieldAlert
[Card: Patrones/Urgencias]     ← NUEVO: high_urgency_count con icono Zap
[Card: Tiempo de Respuesta]    ← NUEVO: avg_response_time formateado (ej: "2m 34s")
[Filter: Hoy / Esta semana]    ← NUEVO: toggle de periodo
```

### 5. Filtro por periodo

Toggle entre "Hoy" y "Esta semana" que:
1. Cambia `timePeriod` state.
2. Re-fetcha las metricas con el nuevo rango.
3. Filtra el live feed si aplica.

## Files to Modify

| File | Action |
|------|--------|
| `frontend_react/src/modules/crm_sales/views/SupervisorDashboard.tsx` | Modify |
| Backend: posible nuevo endpoint `GET /admin/core/chat/supervisor-metrics` | Create (opcional) |

## API Endpoints

| Endpoint | Estado | Uso |
|----------|--------|-----|
| `GET /admin/core/chat/sessions` | Ya existe | Obtener sessions para calculo de metricas |
| `SUPERVISOR_CHAT_EVENT` (Socket.IO) | Ya existe (linea 42) | Actualizaciones en tiempo real |
| `GET /admin/core/chat/supervisor-metrics` | Por crear (opcional) | Metricas agregadas server-side |

## Acceptance Criteria

- [ ] Card "Intervenciones" muestra conteo real de conversaciones con `human_override` activo en el periodo seleccionado.
- [ ] Card "Patrones" muestra conteo real de conversaciones con alta urgencia o sentimiento negativo.
- [ ] Card "Tiempo de Respuesta" muestra tiempo promedio de respuesta formateado (ej: "2m 34s").
- [ ] Las metricas se actualizan en tiempo real cuando llega un `SUPERVISOR_CHAT_EVENT`.
- [ ] Filtro "Hoy / Esta semana" cambia el periodo de calculo de las metricas.
- [ ] Los valores "0 Intervenciones req." y "Buscando patrones..." hardcodeados fueron eliminados.
- [ ] Card de Tiempo de Respuesta fue agregada (no existia antes).
- [ ] Las cards muestran animacion sutil cuando un valor cambia en tiempo real.
- [ ] El live feed existente sigue funcionando sin regresiones.

## Testing Strategy

- **Unit tests**:
  - Renderizar SupervisorDashboard con metricas mock: verificar que los valores se muestran correctamente.
  - Simular `SUPERVISOR_CHAT_EVENT` con `is_silenced: true`: verificar que incrementa interventions.
  - Cambiar periodo "Hoy" → "Esta semana": verificar que re-fetcha metricas.
  - Metricas vacias (0 sessions): verificar que muestra "0" y "0s" (no errores).
- **Integration test**: Verificar que socket se conecta y las metricas se actualizan con eventos reales.
- **Edge cases**: Sin conexion socket (mostrar ultimo valor conocido), API retorna error (mostrar "--" o fallback).
