# FIX-06: Meta Leads — Remove Confusing Demo Data

## Intent

Eliminar los 3 leads demo hardcodeados de MetaLeadsView que confunden a los usuarios al no poder distinguirlos de datos reales, y reemplazarlos con un empty state informativo con CTA.

## Requirements

### MUST

- M1: Eliminar el array `DEMO_LEADS` completo (lineas 35-75 de MetaLeadsView.tsx)
- M2: Eliminar la logica de fallback a demo data cuando no hay leads reales (lineas 150-157)
- M3: Eliminar el fallback a demo data en el catch de error (lineas 160-164)
- M4: Mostrar un empty state limpio cuando no hay leads: ilustracion/icono + titulo "No hay leads de Meta Ads" + descripcion + boton CTA "Conectar Meta Ads" que navegue a `/crm/integraciones`
- M5: Mantener intacta toda la logica de filtros, busqueda y API existente

### SHOULD

- S1: El empty state debe respetar el dark theme actual del CRM
- S2: El CTA "Conectar Meta Ads" debe usar el icono de Facebook/Meta para consistencia visual

## Current State (lo que esta roto)

### Problema: Demo data indistinguible de datos reales

`MetaLeadsView.tsx` define en lineas 35-75 un array `DEMO_LEADS` con 3 leads falsos:
- "Juan Perez" — Campania Dental Invierno
- "Maria Garcia" — Ortodoncia Invisible
- "Carlos Lopez" — Implantes Demo

Estos se muestran en dos situaciones:

1. **Lineas 150-153**: Cuando no hay leads reales Y no hay filtros activos (`searchQuery === '' && statusFilter === 'all' && dateFilter === 'all'`), se hace `setLeads(DEMO_LEADS)` y `calculateStats(DEMO_LEADS)`, mostrando los demo como si fueran reales.

2. **Lineas 160-164**: En el `catch` de error de la API, si `leads.length === 0`, tambien se cae a `DEMO_LEADS` como fallback silencioso, enmascarando errores de conexion.

El campo `is_demo: true` existe en la interfaz `MetaLead` (linea 32) pero no se usa en ningun lado para distinguir visualmente los leads demo. Los usuarios ven leads que parecen reales y no tienen forma de saber que son fabricados.

## Solution

### Eliminar demo data (~45 lineas a borrar)

1. Borrar el array `DEMO_LEADS` completo (lineas 35-75)
2. Borrar el campo `is_demo` de la interfaz `MetaLead` (linea 32)
3. Modificar el fetch en `fetchLeads()`:
   - Lineas 150-157: reemplazar el if/else con asignacion directa `setLeads(metaLeads); calculateStats(metaLeads);`
   - Lineas 160-164: en el catch, siempre mostrar el error: `setError(err.response?.data?.detail || 'Error de conexion')` sin fallback a demo

### Agregar empty state (~15 lineas nuevas)

Donde actualmente se renderiza la tabla de leads con el estado vacio, reemplazar con:

```tsx
<div className="flex flex-col items-center justify-center py-16 text-center">
  <Facebook size={48} className="text-white/10 mb-4" />
  <h3 className="text-lg font-semibold text-white/70 mb-2">
    No hay leads de Meta Ads
  </h3>
  <p className="text-sm text-white/40 max-w-md mb-6">
    Conecta tu cuenta de Meta Ads para comenzar a recibir leads
    automaticamente en el CRM.
  </p>
  <button
    onClick={() => navigate('/crm/integraciones')}
    className="px-4 py-2 bg-violet-600 hover:bg-violet-700 text-white rounded-lg text-sm font-medium flex items-center gap-2 transition-colors"
  >
    <Facebook size={16} />
    Conectar Meta Ads
  </button>
</div>
```

## Files to Modify

| Archivo | Cambio |
|---------|--------|
| `frontend_react/src/views/MetaLeadsView.tsx` | Borrar DEMO_LEADS, borrar is_demo de interfaz, borrar fallback logic, agregar empty state con CTA |

## Acceptance Criteria

- [ ] AC1: No existen leads demo hardcodeados en el codigo fuente
- [ ] AC2: Cuando la API devuelve 0 leads de Meta, se muestra el empty state con icono, titulo, descripcion y CTA
- [ ] AC3: El boton "Conectar Meta Ads" navega a `/crm/integraciones`
- [ ] AC4: Cuando la API devuelve un error, se muestra el mensaje de error (no demo data)
- [ ] AC5: Los filtros, busqueda y paginacion siguen funcionando identico
- [ ] AC6: Las stats se calculan correctamente con 0 leads (no con datos demo)

## Testing Strategy

### Unit Tests
- Renderizar MetaLeadsView con API mock que devuelve array vacio → verificar que aparece el texto "No hay leads de Meta Ads" y el boton CTA
- Renderizar MetaLeadsView con API mock que devuelve error → verificar que se muestra mensaje de error, no demo data
- Renderizar MetaLeadsView con API mock que devuelve leads reales → verificar que se muestran normalmente
- Verificar que `DEMO_LEADS` no existe como export ni como variable

### Integration Tests
- Navegar a MetaLeadsView sin leads → click en "Conectar Meta Ads" → verificar navegacion a `/crm/integraciones`

### Manual Tests
- Con tenant sin Meta configurado: verificar empty state limpio
- Con tenant con Meta configurado pero sin leads: verificar empty state
- Con tenant con leads reales: verificar que se muestran correctamente
