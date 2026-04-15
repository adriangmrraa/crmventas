# Design F-07: Vendedores (Standalone Page)

**Spec:** `07-vendedores-standalone.spec.md`
**Archivo principal:** `frontend_react/src/modules/crm_sales/views/SellersView.tsx`

---

## Decisiones de Arquitectura

### 1. Auto-load KPIs al abrir modal (VEND-03 + VEND-01)

**Problema:** KPIs se cargan on-demand con boton "Cargar KPIs" -- UX confusa.

**Solucion:** Mover la carga de KPIs al `useEffect` que ya observa `sellerRows`. Cuando `sellerRows` se popula (despues de abrir el modal y traer filas via `by-user/:userId`), disparar automaticamente `Promise.allSettled` contra `/sellers/:id/analytics` para cada fila.

```
selectedSeller cambia
  -> useEffect trae sellerRows via /sellers/by-user/:userId
    -> useEffect[sellerRows] dispara loadAllKpis()
      -> Promise.allSettled para cada row
      -> setKpisByRow con datos + conversion_rate calculado
```

**Eliminar:** El boton "Cargar KPIs" y cualquier estado `kpisLoaded` asociado.

### 2. Calculo de conversion_rate client-side (VEND-01)

**Problema:** El endpoint `/analytics` retorna `total_leads` y `by_status` pero no `conversion_rate`.

**Solucion:** Calcular client-side con lista de estados "convertidos".

```ts
const CONVERTED_STATUSES = ['vendido', 'cerrado_ganado', 'sold', 'closed_won', 'ganado'];

const getConversionRate = (byStatus: Record<string, number>, total: number): number => {
  if (total === 0) return 0;
  const converted = CONVERTED_STATUSES.reduce((acc, s) => acc + (byStatus[s] || 0), 0);
  return Math.round((converted / total) * 100);
};
```

**Tipo actualizado de KpisByRowRecord:**

```ts
type KpisByRowRecord = Record<string, {
  total_leads: number;
  by_status: Record<string, number>;
  conversion_rate: number;  // NUEVO
}>;
```

**Trade-off:** Hardcodear estados convertidos es fragil si el pipeline cambia. Alternativa seria traer la config de pipeline del backend, pero agrega complejidad innecesaria para el MVP. Si el backend agrega `conversion_rate` al endpoint, usarlo directamente.

### 3. Navegacion a SellerPerformanceView (VEND-02)

**Solucion:** Agregar `useNavigate` de react-router-dom. Boton "Ver Performance Detallada" dentro del modal de detalle, visible cuando `selectedSeller.user_id` existe.

```
navigate(`/crm/vendedores/${selectedSeller.user_id}/performance`)
```

La ruta ya existe en `App.tsx` (linea 141). No hay cambios de routing.

### 4. Indicador visual is_active en SellerCard (VEND-06)

**Solucion:** Dos cambios visuales cuando `seller.is_active === false`:
- Tarjeta con clase `opacity-60`
- Badge "Inactivo" en rojo (`bg-red-500/20 text-red-400`)

Implementar en el render de cada card en el tab "Vendedores".

### 5. Modal de confirmacion para desactivacion (VEND-05)

**Problema:** Toggle accidental de `is_active` en el form de edicion.

**Solucion:** Nuevo estado `showDeactivateConfirm: boolean`. Al hacer submit del form de edicion:
1. Comparar `editFormData.is_active` con `editingRow.is_active`
2. Si cambio de `true` a `false`, mostrar modal de confirmacion en lugar de submit directo
3. Modal con texto: "Confirmas que queres desactivar a este vendedor? Seguira en el sistema pero no podra operar."
4. Boton "Confirmar" ejecuta el PUT, boton "Cancelar" cierra el modal

**Flujo:**
```
Submit form -> is_active cambio a false?
  SI -> setShowDeactivateConfirm(true) -> Modal -> Confirmar -> PUT /sellers/:id
  NO -> PUT /sellers/:id directamente
```

### 6. Filtro por rol (VEND-07)

**Solucion:** Estado `roleFilter: 'all' | 'setter' | 'closer'`. Filtro client-side sobre `sellers` ya cargados.

```ts
const filteredSellers = roleFilter === 'all'
  ? sellers
  : sellers.filter(s => s.role === roleFilter);
```

Renderizar como chips/tabs sobre el listado de vendedores: "Todos", "Setter", "Closer".

### 7. Reemplazo de alert() (VEND-04)

**Estado actual:** Ya corregido en bug fixes previos con `setError()`. Verificar que no queden `alert()` residuales.

**Patron:** Estado `actionError: string | null` mostrado como banner rojo inline en la seccion correspondiente (solicitudes o modal).

---

## Estado Nuevo Requerido

```ts
// Existentes que se mantienen
const [kpisByRow, setKpisByRow] = useState<KpisByRowRecord>({});

// Nuevos
const [roleFilter, setRoleFilter] = useState<'all' | 'setter' | 'closer'>('all');
const [showDeactivateConfirm, setShowDeactivateConfirm] = useState(false);
const [actionError, setActionError] = useState<string | null>(null); // verificar si ya existe
```

---

## Componentes Afectados

Todo en `SellersView.tsx` -- no se crean componentes nuevos, se modifica inline:

| Seccion | Cambios |
|---------|---------|
| useEffect[sellerRows] | Auto-load KPIs con conversion_rate |
| Modal de detalle | Mostrar conversion_rate, boton "Ver Performance Detallada" |
| Form de edicion | Interceptar submit para confirmacion de desactivacion |
| Tab vendedores | Chips de filtro por rol, indicador is_active en cards |
| handleAction | Verificar que usa setError en lugar de alert() |

---

## Riesgos

| Riesgo | Mitigacion |
|--------|------------|
| Estados convertidos hardcodeados | Constante `CONVERTED_STATUSES` facil de actualizar; si backend agrega campo, usar directo |
| Promise.allSettled con muchas filas | En la practica un seller tiene 1-3 filas, no es problema de performance |
| Boton "Cargar KPIs" eliminado sin reemplazo manual | El auto-load cubre el caso, usuario puede cambiar fechas si se implementa en el futuro |
