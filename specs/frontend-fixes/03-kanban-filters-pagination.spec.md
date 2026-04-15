# FIX-03: Kanban Pipeline — Filtros + Paginacion

## Intent

Agregar filtros y paginacion al Kanban pipeline para mejorar el rendimiento con datasets grandes. Actualmente carga 500 leads de una sola vez sin filtrado, causando problemas de performance.

## Requirements

### MUST

- Reducir el limite default de carga de 500 a 100 leads.
- Agregar toolbar con filtros:
  - **Filtro vendedor**: dropdown con lista de sellers disponibles.
  - **Busqueda**: input de texto que filtre por nombre, telefono o empresa del lead.
  - **Filtro rango de valor**: inputs min/max para `estimated_value`.
  - **Toggle "Solo estancados"**: mostrar solo leads con mas de N dias sin actividad.
- Agregar boton "Cargar mas" al final de cada columna cuando hay mas leads disponibles.
- Usar `StaleDealIndicator` (ya existe en `StaleDealIndicator.tsx`) en las tarjetas de deal del Kanban.
- Los filtros DEBEN usar los query params que ya existen en el endpoint backend.

### SHOULD

- Mantener la funcionalidad de drag-and-drop existente sin afectarla.
- Persistir filtros en URL search params para que sean compartibles.
- Mostrar contador de leads filtrados vs total en el header.
- Debounce en el input de busqueda (300ms).

## Current State (lo que esta roto)

En `KanbanPipelineView.tsx`:

- **Linea 58**: Carga 500 leads de una vez:
  ```tsx
  api.get('/admin/core/crm/leads', { params: { limit: 500 } }),
  ```
- **Sin filtros**: No hay toolbar, no hay inputs de busqueda, no hay filtros de vendedor/valor.
- **Sin paginacion**: No hay "cargar mas" ni infinite scroll por columna.
- **Sin indicador de stale**: Existe `getDaysInStage` (linea 127-131) pero no usa `StaleDealIndicator`.
- Performance: con muchos leads, la vista se torna lenta por renderizar todas las tarjetas en el DOM.

## Solution

### 1. Toolbar de filtros

Agregar debajo del `PageHeader` (linea 279), antes del board Kanban:

```
Toolbar layout:
[Search input] [Seller dropdown] [Value min-max] [Toggle stale] [Clear filters]
```

State de filtros:
```tsx
const [filters, setFilters] = useState({
  search: '',
  seller_id: '',
  value_min: undefined as number | undefined,
  value_max: undefined as number | undefined,
  stale_only: false,
});
```

### 2. Reducir limite y agregar paginacion por columna

- Cambiar `limit: 500` a `limit: 100` en la llamada inicial.
- Pasar filtros como query params al endpoint: `?limit=100&seller_id=X&search=Y`.
- Agregar estado `hasMore` para saber si hay mas leads por cargar.
- Boton "Cargar mas" al final de cada columna que haga `offset += limit` y concatene resultados.

### 3. Integrar StaleDealIndicator

En cada tarjeta de lead (linea 343-422), agregar `StaleDealIndicator` junto al indicador de dias:

```tsx
import StaleDealIndicator from '../components/StaleDealIndicator';

// Dentro de la tarjeta, despues del nombre:
<StaleDealIndicator days={days} />
```

### 4. Filtrado

Los filtros se aplican de dos formas:
- **Server-side**: `seller_id`, `search`, `value_min`, `value_max` se pasan como query params al API.
- **Client-side**: `stale_only` filtra los leads ya cargados por `getDaysInStage() > threshold`.

Al cambiar filtros, resetear offset a 0 y recargar.

## Files to Modify

| File | Action |
|------|--------|
| `frontend_react/src/modules/crm_sales/views/KanbanPipelineView.tsx` | Modify |

## API Endpoints (ya existentes)

| Endpoint | Params disponibles |
|----------|--------------------|
| `GET /admin/core/crm/leads` | `limit`, `offset`, `seller_id`, `search`, `status` |
| `GET /admin/core/crm/lead-statuses` | (sin params adicionales) |

## Acceptance Criteria

- [ ] El limite default de carga es 100 (no 500).
- [ ] Toolbar de filtros visible debajo del header.
- [ ] Filtro de vendedor funciona: dropdown con sellers, filtra leads al seleccionar.
- [ ] Busqueda funciona: filtra por nombre/telefono/empresa con debounce 300ms.
- [ ] Filtro de rango de valor funciona: muestra solo leads con estimated_value en rango.
- [ ] Toggle "Solo estancados" funciona: muestra solo leads con mas de X dias sin actividad.
- [ ] Boton "Cargar mas" aparece al final de cada columna cuando hay mas leads.
- [ ] Cargar mas concatena resultados sin perder los existentes.
- [ ] `StaleDealIndicator` se muestra en cada tarjeta del Kanban.
- [ ] Drag-and-drop sigue funcionando correctamente con filtros activos.
- [ ] Boton "Limpiar filtros" resetea todos los filtros.
- [ ] La vista es notablemente mas rapida con el limite reducido.

## Testing Strategy

- **Unit tests**:
  - Renderizar con filtros vacios: verificar que carga con `limit=100`.
  - Aplicar filtro de vendedor: verificar que el API se llama con `seller_id` param.
  - Aplicar busqueda: verificar debounce y que el API se llama con `search` param.
  - Toggle stale: verificar filtrado client-side por dias.
  - Click "Cargar mas": verificar que offset incrementa y leads se concatenan.
- **Integration test**: Drag-and-drop funciona con filtros activos.
- **Performance test**: Comparar render time con 500 vs 100 leads (deberia ser ~5x mas rapido).
