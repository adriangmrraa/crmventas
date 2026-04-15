# Design F-09: Marketing Hub (Meta + Google Ads)

**Spec:** 09-marketing-hub.spec.md
**Fecha:** 2026-04-14

---

## 1. Arquitectura de cambios

### 1.1 Frontend — MarketingHubView.tsx

**Estado actual del componente:**
- `activePlatform` solo acepta `'meta' | 'google'` — falta `'combined'`
- `loadStats()` ya llama a `/crm/marketing/combined-stats` con `time_range` correcto en L76
- Fallback a `/crm/marketing/stats` usa `range=` (param incorrecto) en L92
- OAuth errors usan `alert()` nativo en L38
- No existe banner de reconexion por token expirado
- No existe tab "Combinado"

### 1.2 Correcciones de parametros

**Problema principal:** El frontend pasa `google_date_range=${timeRange}` al combined-stats, pero `timeRange` tiene valores como `last_30d` mientras que Google espera `LAST_30_DAYS`.

**Solucion — mapping function:**

```typescript
const GOOGLE_RANGE_MAP: Record<string, string> = {
  'last_30d': 'LAST_30_DAYS',
  'last_90d': 'LAST_90_DAYS',
  'this_year': 'THIS_YEAR',
  'all': 'ALL_TIME',
};

function toGoogleRange(timeRange: string): string {
  return GOOGLE_RANGE_MAP[timeRange] ?? 'LAST_30_DAYS';
}
```

**Aplicacion en loadStats():**
```typescript
// Linea principal (combined-stats) — ya usa time_range, solo corregir google_date_range
const { data } = await api.get(
  `/crm/marketing/combined-stats?time_range=${timeRange}&google_date_range=${toGoogleRange(timeRange)}`
);

// Fallback (/stats) — corregir range → time_range
const { data } = await api.get(`/crm/marketing/stats?time_range=${timeRange}`);
```

### 1.3 Tab Combinado

**Cambio en tipo:**
```typescript
const [activePlatform, setActivePlatform] = useState<'meta' | 'google' | 'combined'>('meta');
```

**Datos del tab:**
- Usa `stats.combined` del response de `combined-stats`
- Tabla unificada: merge `stats.meta.campaigns.campaigns` + `stats.google.campaigns` con columna extra `platform: 'Meta' | 'Google'`
- KPIs header: `combined.total_spend`, `combined.total_leads`, `combined.total_conversions`, `combined.weighted_roi`

**Componente nuevo:** `CombinedCampaignsTable` — tabla que recibe ambos arrays normalizados y agrega columna "Plataforma".

### 1.4 Manejo de errores OAuth

**Reemplazar alert() por componente toast/banner inline:**

```typescript
const [errorBanner, setErrorBanner] = useState<{ message: string; visible: boolean }>({ message: '', visible: false });

// En el useEffect de OAuth errors:
if (error) {
  setErrorBanner({ message: errorMessages[error] || `Error: ${error}`, visible: true });
  setTimeout(() => setErrorBanner(prev => ({ ...prev, visible: false })), 8000);
  // limpiar searchParams...
}
```

**Componente:** Banner inline rojo con icono de error, mensaje, y boton X para dismiss manual. Se renderiza arriba del contenido principal. Auto-dismiss a los 8 segundos.

### 1.5 Banner de reconexion por token expirado

**Deteccion:**
- Meta: `stats.meta.meta_connected === false` (si antes estaba conectado, el backend puede indicar `token_expired_at`)
- Google: `stats.google.connected === false`
- URL `?reconnect=true`

**Componente:** `ReconnectionBanner` — strip amarillo/warning con texto "Tu conexion con {plataforma} expiro" + boton "Reconectar ahora".

**Logica:** Si `?reconnect=true` en URL, mostrar banner automaticamente sin esperar respuesta de stats.

---

## 2. Backend — Verificaciones

### 2.1 Endpoint combined-stats

**Estado actual:** Funciona correctamente. El endpoint en `google_ads_routes.py:206` ya acepta `time_range` y `google_date_range` como query params separados. NO hay bug en el backend para este param.

### 2.2 Endpoint /stats (fallback)

**Correccion:** El frontend fallback debe usar `time_range=` en lugar de `range=`. El endpoint `marketing.py:29` ya acepta `time_range`.

### 2.3 Campos faltantes en /stats

El spec menciona que `/stats` no devuelve `impressions`/`clicks`/`ctr` por campana. Esto depende de que `MarketingService.get_campaign_stats()` los incluya desde la Meta API. **Verificar** si el servicio los extrae o no; si no, agregar al SELECT del service.

---

## 3. Componentes nuevos / modificados

| Componente | Tipo | Descripcion |
|------------|------|-------------|
| `MarketingHubView.tsx` | Modificado | Fix params, agregar tab combined, reemplazar alert, agregar banners |
| `OAuthErrorBanner.tsx` | Nuevo | Banner inline de error OAuth con auto-dismiss 8s |
| `ReconnectionBanner.tsx` | Nuevo | Strip de reconexion con CTA |
| `CombinedCampaignsTable.tsx` | Nuevo | Tabla merge Meta+Google con col "Plataforma" |

---

## 4. Decisiones de diseno

1. **Toast vs Banner inline:** Banner inline dentro de la vista (no toast flotante global). Razon: el error OAuth es contextual al Marketing Hub, no es una notificacion global.
2. **Mapping de rangos en frontend:** No en backend. El backend acepta formatos distintos para Meta (`last_30d`) y Google (`LAST_30_DAYS`) intencionalmente. El frontend hace el mapping.
3. **Tab Combinado como tercer tab:** No como vista por defecto. El usuario elige explicitamente verlo.
4. **CombinedCampaignsTable separado:** No inline en MarketingHubView. Mantiene el componente principal manejable.

---

## 5. Riesgos

| Riesgo | Mitigacion |
|--------|-----------|
| `combined-stats` falla y fallback no tiene datos Google | El fallback ya maneja esto: setIsGoogleConnected(false) |
| Token expirado sin `token_expired_at` en response | Usar heuristica: si `meta_connected=false` y no hay error explicito, asumir expiracion |
| Tab Combinado con solo una plataforma conectada | Mostrar aviso "Google/Meta no conectado" y datos parciales |
