# FIX-02: Dashboard CRM — Chart Funcional + Botones Rotos

## Intent

Reemplazar el placeholder "Chart coming soon" del dashboard CRM con un grafico Recharts real, conectar los botones sin onClick handler, y calcular trends reales en vez de usar valores hardcodeados.

## Requirements

### MUST

- Reemplazar el placeholder (lineas 343-349) con un `AreaChart` de Recharts que muestre datos de `revenue_leads_trend` del API.
- Agregar `onClick={() => navigate('/crm/leads'))` al boton "See All Leads" (linea 385) que actualmente no tiene handler.
- Agregar `onClick={() => navigate(`/crm/leads/${lead.id}`))` al boton de vista de lead individual (linea 436) que actualmente no tiene handler.
- Calcular trends reales comparando periodo actual vs anterior (los datos del API tienen timestamps).

### SHOULD

- Mostrar leyenda del chart con colores consistentes al tema.
- Mostrar tooltip con datos formateados en el chart.
- Si no hay datos de trend, mostrar "Sin datos suficientes" en vez de +0%.

## Current State (lo que esta roto)

En `DashboardView.tsx`:

- **Lineas 343-349**: Bloque CRM renderiza placeholder estatico:
  ```tsx
  <div className="h-full flex flex-col items-center justify-center text-white/30">
    <TrendingUpIcon className="w-16 h-16 mb-4 opacity-50" />
    <p className="text-lg font-medium">Leads Analytics</p>
    <p className="text-sm mt-2">Chart coming soon with lead conversion data</p>
  </div>
  ```
- **Linea 385**: Boton "See All Leads" sin onClick:
  ```tsx
  <button className="text-violet-400 text-sm font-semibold hover:underline px-3 py-2">
    {isCrmSales ? 'See All Leads' : t('dashboard.see_all')}
  </button>
  ```
- **Linea 436**: Boton para ver lead individual sin onClick:
  ```tsx
  <button className="p-2 hover:bg-white/[0.06] ...">
    <ArrowUpRight size={20} />
  </button>
  ```
- **Lineas 271, 279, 291**: Trends hardcodeados: `trend="+12%"`, `trend="+5%"`, `trend="+8%"` — no reflejan datos reales.

## Solution

### 1. Chart real con Recharts

Reemplazar el placeholder con un `AreaChart` que use datos de la API. El endpoint `GET /admin/core/crm/stats/summary?range={range}` ya retorna `revenue_leads_trend` (array con timestamps y valores).

```
Estructura esperada del chart:
- X axis: fechas (date)
- Area 1: nuevos leads por periodo (color violet)
- Area 2: revenue acumulado por periodo (color emerald)
- Gradientes consistentes con el tema dark
```

Si `revenue_leads_trend` esta vacio o no existe, mostrar mensaje "Sin datos de tendencia disponibles" en lugar del placeholder actual.

### 2. Botones con navegacion

```tsx
// Linea 385 — "See All Leads"
<button onClick={() => navigate('/crm/leads')} className="...">

// Linea 436 — Ver lead individual
<button onClick={() => navigate(`/crm/leads/${lead.id}`)} className="...">
```

### 3. Trends calculados

Agregar funcion `calculateTrend(current, previous)` que:
1. Compare valor del periodo actual vs anterior.
2. Retorne string formateado: "+12%", "-5%", o `null` si no hay datos previos.
3. Pasar resultado a cada `KPICard` en vez de strings hardcodeados.

La data ya tiene timestamps, asi que se puede dividir el array a la mitad (primera mitad = periodo anterior, segunda mitad = periodo actual) para calcular el delta.

## Files to Modify

| File | Action |
|------|--------|
| `frontend_react/src/views/DashboardView.tsx` | Modify |

## API Endpoints (ya existentes)

| Endpoint | Dato relevante |
|----------|---------------|
| `GET /admin/core/crm/stats/summary?range={range}` | `revenue_leads_trend`, `total_leads`, `active_leads`, `conversion_rate`, `total_revenue` |

## Acceptance Criteria

- [ ] El placeholder "Chart coming soon" fue reemplazado con un AreaChart funcional de Recharts.
- [ ] El chart muestra datos reales de `revenue_leads_trend` del API.
- [ ] El chart tiene tooltips y leyenda con colores consistentes al tema dark.
- [ ] Si no hay datos de trend, se muestra mensaje "Sin datos de tendencia" (no un chart vacio).
- [ ] Boton "See All Leads" navega a `/crm/leads` al hacer click.
- [ ] Boton de vista de lead individual navega a `/crm/leads/{id}` al hacer click.
- [ ] Los porcentajes de trend (+12%, +8%, +5%) se calculan con datos reales.
- [ ] Si no hay datos para calcular trend, no se muestra porcentaje (en vez de hardcodear).
- [ ] No se rompio nada del dashboard Dental (modo no-CRM sigue funcionando igual).

## Testing Strategy

- **Unit tests**:
  - Renderizar DashboardView en modo CRM (`niche_type: 'crm_sales'`): verificar que el chart se renderiza (no el placeholder).
  - Verificar que "See All Leads" tiene onClick que llama navigate.
  - Verificar que boton de lead individual tiene onClick con el ID correcto.
  - Verificar calculo de trends con datos mock (positivo, negativo, sin datos previos).
- **Regression test**: Renderizar en modo Dental y verificar que nada cambio.
- **Visual test**: Chart se ve correctamente con datos vacios, pocos datos, y muchos datos.
