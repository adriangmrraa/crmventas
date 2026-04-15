# SPEC F-07: Vendedores (Standalone Page)

**Priority:** Alta
**Complexity:** Media
**Status:** Sustancialmente implementada. Gaps en KPIs de conversión, navegación a performance, y deactivation flow.

---

## Intent

`SellersView.tsx` ya maneja el flujo completo de dos tabs: "Solicitudes" (usuarios pendientes) y "Vendedores" (sellers activos con modal de detalle). El objetivo es cerrar los gaps pendientes: KPIs de conversión real (conversion_rate, avg_response_time), navegación funcional a `/crm/vendedores/:userId/performance`, y soft-delete correcto vía `is_active` toggle.

---

## Current State

### Lo que ya funciona

**Tab "Solicitudes":**
- `GET /admin/core/users` → lista usuarios `status: 'pending'` con `role: 'setter' | 'closer'`.
- Aprobar: `POST /admin/core/users/:id/status` con `{ status: 'active' }`. (línea 107)
- Rechazar: `POST /admin/core/users/:id/status` con `{ status: 'suspended' }`. (línea 107)
- Badge de conteo de solicitudes pendientes en el tab. (línea 244)

**Tab "Vendedores":**
- `GET /admin/core/crm/sellers` → lista de sellers activos. (línea 98)
- Click en tarjeta → modal detalle con:
  - `GET /admin/core/crm/sellers/by-user/:userId` → filas de seller por usuario.
  - Asignación a entidad: `POST /admin/core/crm/sellers` (link to tenant). (línea 160)
  - KPIs por fila: `GET /admin/core/crm/sellers/:id/analytics` con rango de fechas. (línea 129)
    - Retorna `total_leads` y `by_status` (breakdown por estado del lead).
  - "Remove Access": `POST /admin/core/users/:userId/status` con `{ status: 'suspended' }`. (línea 141)
- Edición de seller: `PUT /admin/core/crm/sellers/:id` con campos nombre, email, phone, `is_active`. (línea 200)

### Gaps identificados

1. **KPIs de conversión no calculados**: `analytics` endpoint retorna `total_leads` y `by_status` pero el frontend no calcula `conversion_rate` ni `avg_response_time`. Solo muestra el breakdown crudo.
2. **Sin navegación a `/crm/vendedores/:userId/performance`**: `SellerPerformanceView.tsx` existe y está ruteada (App.tsx línea 141), pero ningún botón en `SellersView` navega a ella. El userId existe en `selectedSeller.user_id`.
3. **`is_active` toggle en edit form**: el checkbox existe y se envía al backend (línea 200), pero no hay confirmación de deactivation — el usuario puede toggle accidentalmente.
4. **KPIs se cargan on-demand** (botón "Cargar KPIs") en lugar de cargarse automáticamente al abrir el modal — genera UX confusa.
5. **Sin indicador visual de `is_active` en las tarjetas de seller**: si `is_active = false`, la tarjeta se ve igual que una activa.
6. **Sin filtro por rol** (setter/closer) en el tab de vendedores.
7. **Error handling**: `handleAction` y `handleLinkToEntitySubmit` usan `alert()` — inconsistente con el resto del sistema que usa toasts/inline errors.

---

## Requirements

### MUST

- **VEND-01**: En el modal de detalle de seller, calcular y mostrar `conversion_rate` automáticamente al abrir el modal. Formula: `(leads en status 'sold' o 'closed_won') / total_leads * 100`. Si `by_status` incluye esos estados, derivarlo client-side. Si no, agregar el campo al endpoint backend (ver nota).
- **VEND-02**: Botón "Ver Performance Detallada" en el modal de detalle que navega a `/crm/vendedores/:userId/performance` usando `useNavigate`. Debe estar visible cuando `selectedSeller.user_id` existe.
- **VEND-03**: KPIs del mes actual deben cargarse automáticamente al abrir el modal de detalle, sin requerir click en "Cargar KPIs". Eliminar el botón lazy-load.
- **VEND-04**: Reemplazar los `alert()` en `handleAction` y `handleLinkToEntitySubmit` con inline error state (variable `actionError: string | null`) mostrada dentro del modal o tarjeta correspondiente.

### SHOULD

- **VEND-05**: Modal de confirmación al desactivar (`is_active = false`) con texto "¿Confirmas que querés desactivar a este vendedor? Seguirá en el sistema pero no podrá operar." Solo mostrar si el valor cambia de `true` a `false`.
- **VEND-06**: Indicador visual en las `SellerCard` cuando `seller.is_active === false`: badge "Inactivo" en rojo y tarjeta con `opacity-60`.
- **VEND-07**: Filtro por rol en el tab vendedores: todos / setter / closer (client-side, sin API call adicional).
- **VEND-08**: Mostrar `avg_response_time` en el modal de detalle. El endpoint `/admin/core/crm/sellers/:id/analytics` puede no retornarlo; si no existe, usar `GET /admin/core/team-activity/seller/:userId/performance` (mismo que usa `SellerPerformanceView`) para obtener `avg_first_response_seconds`.

### COULD

- **VEND-09**: En el tab "Solicitudes", al aprobar un usuario, pre-abrir automáticamente el form de asignación a entidad para ese usuario recién aprobado (mejorar el flujo de onboarding).
- **VEND-10**: Export CSV del listado de sellers con sus KPIs del mes.

---

## API Endpoints

| Endpoint | Método | Estado | Uso |
|----------|--------|--------|-----|
| `GET /admin/core/users` | GET | Existe | Lista usuarios (tab Solicitudes) |
| `POST /admin/core/users/:id/status` | POST | Existe | Aprobar / rechazar / suspender |
| `GET /admin/core/crm/sellers` | GET | Existe | Lista sellers activos |
| `GET /admin/core/crm/sellers/by-user/:userId` | GET | Existe | Filas de seller por usuario |
| `POST /admin/core/crm/sellers` | POST | Existe | Vincular seller a tenant |
| `PUT /admin/core/crm/sellers/:id` | PUT | Existe | Editar datos del seller |
| `GET /admin/core/crm/sellers/:id/analytics` | GET | Existe | KPIs por seller (total_leads, by_status) |
| `GET /admin/core/team-activity/seller/:userId/performance` | GET | Existe | KPIs extendidos (avg_first_response_seconds, etc.) |
| `GET /admin/core/chat/tenants` | GET | Existe | Lista de tenants para selector |

### Nota sobre conversion_rate

El endpoint `analytics` retorna `by_status: { "nuevo": 3, "contactado": 2, "vendido": 1 }`. Los estados que cuentan como "convertido" dependen de la configuración del pipeline. Estrategia pragmática:

```tsx
const CONVERTED_STATUSES = ['vendido', 'cerrado_ganado', 'sold', 'closed_won', 'ganado'];

const getConversionRate = (byStatus: Record<string, number>, total: number): number => {
  if (total === 0) return 0;
  const converted = CONVERTED_STATUSES.reduce(
    (acc, s) => acc + (byStatus[s] || 0),
    0
  );
  return Math.round((converted / total) * 100);
};
```

Si el backend ya retorna `conversion_rate` en algún endpoint futuro, usarlo directamente.

---

## Files to Modify

| File | Action | Motivo |
|------|--------|--------|
| `frontend_react/src/modules/crm_sales/views/SellersView.tsx` | Modify | VEND-01 al VEND-08 |

No se requieren cambios de backend para los MUST (todos los datos necesarios ya están disponibles).

---

## Solution

### VEND-01 y VEND-03: KPIs automáticos con conversion_rate

Reemplazar el `useEffect` de `loadKpis` lazy por carga automática en el `useEffect` de `selectedSeller`:

```tsx
useEffect(() => {
  if (!selectedSeller || sellerRows.length === 0) return;

  const loadAllKpis = async () => {
    const now = new Date();
    const start = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10);
    const end = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().slice(0, 10);

    const results = await Promise.allSettled(
      sellerRows.map((row) =>
        api.get(`${CRM_PREFIX}/sellers/${row.id}/analytics`, {
          params: { tenant_id: row.tenant_id, start_date: start, end_date: end },
        })
      )
    );

    const newKpis: KpisByRowRecord = {};
    results.forEach((result, i) => {
      const key = `${sellerRows[i].id}-${sellerRows[i].tenant_id}`;
      if (result.status === 'fulfilled') {
        const { total_leads, by_status } = result.value.data;
        newKpis[key] = {
          total_leads: total_leads || 0,
          by_status: by_status || {},
          conversion_rate: getConversionRate(by_status || {}, total_leads || 0),
        };
      } else {
        newKpis[key] = { total_leads: 0, by_status: {}, conversion_rate: 0 };
      }
    });
    setKpisByRow(newKpis);
  };

  loadAllKpis();
}, [sellerRows]);
```

### VEND-02: Botón de navegación a performance

```tsx
import { useNavigate } from 'react-router-dom';
const navigate = useNavigate();

// Dentro del modal de detalle, después del header:
<button
  type="button"
  onClick={() => navigate(`/crm/vendedores/${selectedSeller.user_id}/performance`)}
  className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-white/[0.06] text-white/70 hover:bg-white/[0.03] text-sm"
>
  <BarChart3 size={16} />
  Ver Performance Detallada
</button>
```

### VEND-04: Reemplazar alert() con inline error

```tsx
const [actionError, setActionError] = useState<string | null>(null);

const handleAction = async (userId: string, action: 'active' | 'suspended') => {
  try {
    setActionError(null);
    await api.post(`/admin/core/users/${userId}/status`, { status: action });
    setUsers((prev) => prev.map((u) => (u.id === userId ? { ...u, status: action } : u)));
    if (action === 'active') fetchSellers();
  } catch (err: any) {
    setActionError(err?.response?.data?.detail || t('alerts.error_process'));
  }
};
```

Mostrar `actionError` sobre el listado de solicitudes o vendedores como un banner rojo inline.

### VEND-06: Indicador de inactividad en SellerCard

```tsx
// En SellerCard render:
<div className={`glass p-5 ... ${!seller.is_active ? 'opacity-60' : ''}`}>
  {!seller.is_active && (
    <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 uppercase font-bold">
      Inactivo
    </span>
  )}
  ...
</div>
```

---

## Acceptance Criteria

- [ ] Al abrir el modal de un seller con filas vinculadas, los KPIs se cargan automáticamente (sin botón "Cargar KPIs").
- [ ] `conversion_rate` se muestra como porcentaje junto a `total_leads` para cada tenant vinculado.
- [ ] Botón "Ver Performance Detallada" navega a `/crm/vendedores/:userId/performance` con el userId correcto.
- [ ] Aprobar un usuario pendiente muestra mensaje de éxito inline (no `alert()`).
- [ ] Error en aprobación muestra banner rojo con el mensaje del backend.
- [ ] Sellers con `is_active = false` muestran badge "Inactivo" y tarjeta con opacidad reducida.
- [ ] Filtro por rol (setter/closer) en el tab de vendedores funciona sin llamadas adicionales a la API.
- [ ] Modal de confirmación aparece antes de guardar `is_active = false` en el form de edición.
- [ ] KPIs se cargan con `Promise.allSettled` — si uno falla, los demás se muestran igual.

---

## Testing Strategy

- **Unit**: Renderizar `SellerCard` con `seller.is_active = false` → badge "Inactivo" visible, opacidad reducida.
- **Unit**: `getConversionRate({ vendido: 2, nuevo: 8 }, 10)` → retorna `20`.
- **Unit**: `getConversionRate({}, 0)` → retorna `0` (no divide por cero).
- **Unit**: Abrir modal de seller con 2 filas vinculadas → mock `api.get` analytics → verificar que `kpisByRow` se setea para ambas filas sin click del usuario.
- **Unit**: Click en "Ver Performance Detallada" → `navigate` fue llamado con `/crm/vendedores/user-123/performance`.
- **Integration**: Rechazar un usuario con backend retornando error 500 → banner rojo visible en tab Solicitudes.
- **Edge case**: Seller sin filas vinculadas → KPIs no se cargan, modal muestra "not_linked_hint" sin crash.
