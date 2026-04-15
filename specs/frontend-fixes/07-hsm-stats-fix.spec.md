# FIX-07: HSM Templates — Fix Hardcoded Stats

## Intent

Reemplazar las stats hardcodeadas en las hero cards de MetaTemplatesView (estado del motor y tasa de conversion) con datos calculados a partir de los logs reales, y resolver el selector de timezone deshabilitado.

## Requirements

### MUST

- M1: Card 1 (Motor status): calcular estado real basado en actividad reciente de logs
  - Logs en las ultimas 24h → "Operacional" (verde)
  - Sin logs en 24h → "Sin actividad" (amber)
  - Error de API al cargar logs → "Error" (rojo)
- M2: Card 3 (Conversion rate): calcular tasa real = `(logs con status 'delivered' o 'read') / (total logs) * 100`. Si no hay logs, mostrar "—"
- M3: Resolver el timezone selector: remover el atributo `disabled` y la clase `cursor-not-allowed opacity-70` del `<select>`, o remover el selector completamente si no hay backend para persistir la preferencia

### SHOULD

- S1: Formatear el porcentaje de conversion con un decimal (ej: "72.3%")
- S2: Agregar tooltip o texto explicativo en Card 1 indicando que el estado se basa en actividad de las ultimas 24h

## Current State (lo que esta roto)

### Problema 1: Motor status hardcodeado
`MetaTemplatesView.tsx` lineas 100-108: La Card 1 siempre muestra "Operacional" con estilo verde, independientemente de si el motor de automatizacion esta funcionando o no:
```tsx
<span className="... bg-green-500/10 text-green-400 ...">
  {t('hsm.motor_operational')}
</span>
```
No hay ninguna verificacion real del estado del motor.

### Problema 2: Conversion rate hardcodeada
Lineas 120-129: La Card 3 muestra un `85%` literal:
```tsx
<p className="text-2xl font-black text-white">85%</p>
```
Este valor no tiene relacion con los datos reales. La variable `logs` esta disponible en el componente y contiene los status reales (`sent`, `failed`, `delivered`, `read`), pero no se usa para calcular la conversion.

### Problema 3: Timezone selector deshabilitado
Lineas 209-218: El `<select>` de timezone tiene `disabled` como atributo y clases `cursor-not-allowed opacity-70`, haciendolo visible pero inusable. Tiene 3 opciones (Buenos Aires, Mexico City, Madrid) pero el usuario no puede cambiar la seleccion.

### Dato positivo
La Card 2 (Sent count, lineas 110-118) SI calcula un valor real: `logs.filter(l => l.status === 'sent').length`. Esta es la referencia de como deberian funcionar las otras cards.

## Solution

### Card 1: Motor status dinamico

Reemplazar el `<span>` hardcodeado con logica condicional basada en el estado de los logs:

```tsx
// Derivar estado del motor
const hasRecentLogs = logs.some(l => {
  const logDate = new Date(l.created_at);
  const now = new Date();
  return (now.getTime() - logDate.getTime()) < 24 * 60 * 60 * 1000;
});
const hasApiError = /* nuevo estado para capturar error de fetch */;

// En el JSX:
{hasApiError ? (
  <span className="... bg-red-500/10 text-red-400 ...">Error</span>
) : hasRecentLogs ? (
  <span className="... bg-green-500/10 text-green-400 ...">{t('hsm.motor_operational')}</span>
) : (
  <span className="... bg-amber-500/10 text-amber-400 ...">Sin actividad</span>
)}
```

Agregar estado `fetchError` al componente para capturar errores de la API:
```tsx
const [fetchError, setFetchError] = useState(false);
```
En `fetchLogs()`, setear `setFetchError(true)` en el catch y `setFetchError(false)` al inicio del try.

### Card 3: Conversion rate calculada

Reemplazar el `85%` con calculo real:

```tsx
const deliveredOrRead = logs.filter(l => l.status === 'delivered' || l.status === 'read').length;
const conversionRate = logs.length > 0
  ? ((deliveredOrRead / logs.length) * 100).toFixed(1)
  : '—';
```

En el JSX, reemplazar `85%` con `{conversionRate}{conversionRate !== '—' ? '%' : ''}`.

### Timezone selector: remover UI no funcional

Dado que no existe endpoint backend para persistir la preferencia de timezone del tenant, remover el bloque completo del timezone selector (lineas 200-221 — el `<div>` "Regional Config") para evitar confundir al usuario con un control que no hace nada.

Tambien remover el badge de timezone en el header (lineas 80-83) ya que sin selector no tiene sentido mostrarlo.

Remover el estado `timezone` (linea 34) y la importacion de `Globe` si no se usa en otro lugar.

## Files to Modify

| Archivo | Cambio |
|---------|--------|
| `frontend_react/src/views/marketing/MetaTemplatesView.tsx` | Agregar estado `fetchError`, calcular `hasRecentLogs` y `conversionRate` desde logs, reemplazar Card 1 y Card 3 con valores dinamicos, remover timezone selector y badge |

## Acceptance Criteria

- [ ] AC1: Card 1 muestra "Operacional" (verde) cuando hay logs en las ultimas 24h
- [ ] AC2: Card 1 muestra "Sin actividad" (amber) cuando no hay logs recientes
- [ ] AC3: Card 1 muestra "Error" (rojo) cuando la API falla al cargar logs
- [ ] AC4: Card 3 muestra porcentaje real calculado como (delivered + read) / total * 100
- [ ] AC5: Card 3 muestra "—" cuando no hay logs
- [ ] AC6: No existe ningun valor `85%` hardcodeado en el codigo
- [ ] AC7: El timezone selector deshabilitado ya no aparece en la UI
- [ ] AC8: Card 2 (Sent count) sigue funcionando igual que antes

## Testing Strategy

### Unit Tests
- Renderizar con logs que incluyen items de las ultimas 24h → Card 1 muestra "Operacional" con clase `text-green-400`
- Renderizar con logs todos mayores a 24h → Card 1 muestra "Sin actividad" con clase `text-amber-400`
- Renderizar con API mock que falla → Card 1 muestra "Error" con clase `text-red-400`
- Renderizar con logs: 2 sent, 1 delivered, 1 read → Card 3 muestra "50.0%"
- Renderizar con 0 logs → Card 3 muestra "—"
- Verificar que no existe el string "85%" en el output renderizado
- Verificar que no existe un `<select disabled>` para timezone en el output

### Integration Tests
- Cargar MetaTemplatesView con backend real → verificar que Card 1 y Card 3 reflejan datos reales
- Forzar error de red → verificar que Card 1 cambia a "Error"

### Manual Tests
- Con tenant activo (logs recientes): verificar verde + porcentaje real
- Con tenant inactivo (sin logs): verificar amber + "—"
- Verificar que el area de timezone ya no existe en el sidebar
