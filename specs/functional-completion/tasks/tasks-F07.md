# Tasks F-07: Vendedores (Standalone Page)

**Spec:** `07-vendedores-standalone.spec.md`
**Design:** `design/design-F07.md`
**Archivo:** `frontend_react/src/modules/crm_sales/views/SellersView.tsx`

---

## Tareas

### T-07-01: Actualizar tipo KpisByRowRecord con conversion_rate
**Req:** VEND-01
**Esfuerzo:** XS

- [ ] Agregar campo `conversion_rate: number` al tipo `KpisByRowRecord`
- [ ] Crear funcion pura `getConversionRate(byStatus, total): number` con constante `CONVERTED_STATUSES`
- [ ] Test unitario: `getConversionRate({ vendido: 2, nuevo: 8 }, 10)` retorna `20`
- [ ] Test unitario: `getConversionRate({}, 0)` retorna `0` (no divide por cero)
- [ ] Test unitario: `getConversionRate({ closed_won: 1, sold: 2 }, 10)` retorna `30`

### T-07-02: Auto-load KPIs al abrir modal
**Req:** VEND-03, VEND-01
**Depende de:** T-07-01

- [ ] Agregar `useEffect` que observe `sellerRows` y dispare `loadAllKpis()` automaticamente
- [ ] `loadAllKpis` usa `Promise.allSettled` contra `/sellers/:id/analytics` por cada fila
- [ ] Calcular `conversion_rate` con `getConversionRate` para cada resultado
- [ ] Almacenar en `kpisByRow` con key `${row.id}-${row.tenant_id}`
- [ ] Eliminar boton "Cargar KPIs" del modal
- [ ] Test: abrir modal con 2 filas vinculadas -> mock api.get analytics -> verificar kpisByRow seteado para ambas sin click
- [ ] Test edge case: seller sin filas vinculadas -> KPIs no se cargan, sin crash

### T-07-03: Mostrar conversion_rate en modal de detalle
**Req:** VEND-01
**Depende de:** T-07-02

- [ ] En la seccion de KPIs del modal, mostrar `conversion_rate` como porcentaje junto a `total_leads`
- [ ] Formato: "Conversion: XX%" con icono o color indicativo
- [ ] Si KPIs aun cargando, mostrar skeleton/spinner

### T-07-04: Boton navegacion a SellerPerformanceView
**Req:** VEND-02
**Esfuerzo:** XS

- [ ] Agregar `import { useNavigate } from 'react-router-dom'` y `const navigate = useNavigate()`
- [ ] Boton "Ver Performance Detallada" en modal de detalle con icono `BarChart3`
- [ ] `onClick={() => navigate(/crm/vendedores/${selectedSeller.user_id}/performance)`
- [ ] Visible solo cuando `selectedSeller?.user_id` existe
- [ ] Test: click en boton -> navigate llamado con ruta correcta

### T-07-05: Indicador visual is_active en cards
**Req:** VEND-06
**Esfuerzo:** S

- [ ] En render de SellerCard: agregar `opacity-60` cuando `seller.is_active === false`
- [ ] Badge "Inactivo" rojo (`bg-red-500/20 text-red-400`) visible cuando inactivo
- [ ] Test: renderizar card con `is_active = false` -> badge visible, opacidad reducida
- [ ] Test: renderizar card con `is_active = true` -> sin badge, opacidad normal

### T-07-06: Modal de confirmacion para desactivacion
**Req:** VEND-05
**Esfuerzo:** S

- [ ] Nuevo estado `showDeactivateConfirm: boolean`
- [ ] Interceptar submit del form de edicion: si `is_active` cambio de `true` a `false`, mostrar modal
- [ ] Modal con texto de confirmacion y botones Confirmar/Cancelar
- [ ] Confirmar ejecuta el PUT, Cancelar cierra el modal sin cambios
- [ ] Test: cambiar is_active de true a false y submit -> modal aparece
- [ ] Test: confirmar en modal -> PUT ejecutado
- [ ] Test: cancelar en modal -> PUT NO ejecutado

### T-07-07: Filtro por rol en tab vendedores
**Req:** VEND-07
**Esfuerzo:** S

- [ ] Nuevo estado `roleFilter: 'all' | 'setter' | 'closer'`
- [ ] Renderizar chips "Todos" / "Setter" / "Closer" sobre el listado de vendedores
- [ ] Filtro client-side: `sellers.filter(s => s.role === roleFilter)` o todos si `'all'`
- [ ] Test: filtro 'setter' -> solo sellers con role 'setter' visibles
- [ ] Test: filtro 'all' -> todos visibles

### T-07-08: Verificar reemplazo de alert() (VEND-04)
**Req:** VEND-04
**Esfuerzo:** XS

- [ ] Buscar `alert(` en SellersView.tsx -- verificar que no queden instancias
- [ ] Si quedan, reemplazar con `setActionError()` / `setError()`
- [ ] Verificar que errores de `handleAction` y `handleLinkToEntitySubmit` se muestran inline
- [ ] Test: error en aprobacion -> banner rojo visible, no alert

### T-07-09 (SHOULD): avg_response_time en modal
**Req:** VEND-08
**Esfuerzo:** M

- [ ] Verificar si `/sellers/:id/analytics` retorna `avg_response_time`
- [ ] Si no, llamar a `/team-activity/seller/:userId/performance` para obtener `avg_first_response_seconds`
- [ ] Mostrar en modal como "Tiempo de respuesta promedio: Xm Xs"
- [ ] Manejar caso donde el endpoint no retorna datos

---

## Orden de Ejecucion

```
T-07-01 (tipo + funcion pura)
  -> T-07-02 (auto-load)
    -> T-07-03 (mostrar conversion_rate)
T-07-04 (navegacion)          -- independiente
T-07-05 (indicador is_active) -- independiente
T-07-06 (modal confirmacion)  -- independiente
T-07-07 (filtro rol)          -- independiente
T-07-08 (verificar alerts)    -- independiente
T-07-09 (avg_response_time)   -- SHOULD, despues de MUST
```

Tareas T-07-04 a T-07-08 son independientes entre si y pueden ejecutarse en paralelo.
