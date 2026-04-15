# Tasks F-09: Marketing Hub (Meta + Google Ads)

**Spec:** 09-marketing-hub.spec.md
**Design:** design-F09.md
**Fecha:** 2026-04-14

---

## Tareas

### T-09.1: Fix parametro google_date_range en loadStats()
**Archivo:** `frontend_react/src/views/marketing/MarketingHubView.tsx`
**Lineas:** ~76, ~92

- [ ] Crear constante `GOOGLE_RANGE_MAP` que mapea `last_30d → LAST_30_DAYS`, `last_90d → LAST_90_DAYS`, `this_year → THIS_YEAR`, `all → ALL_TIME`
- [ ] Crear funcion helper `toGoogleRange(timeRange: string): string`
- [ ] En `loadStats()` linea principal: cambiar `google_date_range=${timeRange}` a `google_date_range=${toGoogleRange(timeRange)}`
- [ ] En fallback (L92): cambiar `range=${timeRange}` a `time_range=${timeRange}`

**Criterio:** Al seleccionar `last_90d`, la request a combined-stats envia `google_date_range=LAST_90_DAYS`

---

### T-09.2: Reemplazar alert() por banner inline de error OAuth
**Archivos:** `MarketingHubView.tsx`, nuevo `OAuthErrorBanner.tsx`

- [ ] Crear componente `OAuthErrorBanner` en `frontend_react/src/components/marketing/OAuthErrorBanner.tsx`
  - Props: `message: string`, `visible: boolean`, `onDismiss: () => void`
  - Estilo: fondo rojo/error, icono AlertTriangle, texto blanco, boton X
  - Auto-dismiss con `setTimeout` de 8000ms (el padre controla via state)
- [ ] En `MarketingHubView.tsx`: agregar state `errorBanner` con `{ message, visible }`
- [ ] Reemplazar `alert(errorMessages[error]...)` por `setErrorBanner({ message: ..., visible: true })`
- [ ] Agregar `setTimeout(() => setErrorBanner(prev => ({ ...prev, visible: false })), 8000)` despues de setear el error
- [ ] Renderizar `<OAuthErrorBanner>` arriba del contenido principal
- [ ] Eliminar la linea `alert(...)` completamente

**Criterio:** URL con `?error=token_exchange_failed` muestra banner rojo inline, no alert nativo. Desaparece en 8s o al click en X.

---

### T-09.3: Agregar tab "Combinado" al selector de plataforma
**Archivo:** `MarketingHubView.tsx`

- [ ] Cambiar tipo de `activePlatform` a `'meta' | 'google' | 'combined'`
- [ ] Agregar tercer boton/tab "Combinado" en el selector de plataforma (junto a Meta y Google)
- [ ] Cuando `activePlatform === 'combined'`: renderizar seccion de KPIs combinados + tabla combinada

**Criterio:** Tres tabs visibles: Meta, Google, Combinado. Click en Combinado cambia la vista.

---

### T-09.4: Crear componente CombinedCampaignsTable
**Archivo nuevo:** `frontend_react/src/components/marketing/CombinedCampaignsTable.tsx`

- [ ] Crear componente que recibe `metaCampaigns: any[]` y `googleCampaigns: any[]`
- [ ] Normalizar ambos arrays a columnas comunes: nombre, inversion/costo, leads/conversiones, estado, plataforma
- [ ] Columna "Plataforma" con badge (Meta = azul, Google = verde)
- [ ] Fila de totales: `combined.total_spend`, `combined.total_leads`, `combined.total_conversions`, `combined.weighted_roi`
- [ ] Si una plataforma no esta conectada: mostrar aviso inline "Meta/Google no conectado"

**Criterio:** Tabla muestra campanas de ambas plataformas con columna "Plataforma" diferenciada.

---

### T-09.5: Renderizar tab Combinado en MarketingHubView
**Archivo:** `MarketingHubView.tsx`

- [ ] Cuando `activePlatform === 'combined'`: renderizar KPI cards con datos de `stats.combined`
  - Inversion total, Leads totales, Conversiones totales, ROI ponderado
- [ ] Renderizar `<CombinedCampaignsTable>` pasando `stats.meta.campaigns.campaigns` y `stats.google.campaigns`
- [ ] Si solo una plataforma conectada: mostrar datos parciales con aviso

**Criterio:** Tab Combinado muestra metricas agregadas y tabla unificada.

---

### T-09.6: Banner de reconexion por token expirado
**Archivo nuevo:** `frontend_react/src/components/marketing/ReconnectionBanner.tsx`
**Archivo modificado:** `MarketingHubView.tsx`

- [ ] Crear componente `ReconnectionBanner` con props: `platform: 'Meta' | 'Google'`, `onReconnect: () => void`, `visible: boolean`
  - Estilo: strip amarillo/warning, texto "Tu conexion con {platform} expiro", boton "Reconectar ahora"
- [ ] En `MarketingHubView.tsx`: detectar estado de token expirado
  - Meta: `stats.meta.meta_connected === false` cuando previamente estaba conectado
  - Google: `stats.google.connected === false` cuando previamente estaba conectado
  - URL param `?reconnect=true`
- [ ] Renderizar `<ReconnectionBanner>` debajo de `<OAuthErrorBanner>` si aplica
- [ ] Boton "Reconectar ahora" ejecuta `handleConnectMeta()` o `handleConnectGoogle()` segun plataforma

**Criterio:** Si Meta esta desconectado con token previo, aparece banner amarillo. Click en "Reconectar" inicia OAuth.

---

### T-09.7: Verificar backend — campos impressions/clicks/ctr en /stats
**Archivo:** `orchestrator_service/services/marketing/marketing_service.py`

- [ ] Verificar que `get_campaign_stats()` retorna `impressions`, `clicks`, `ctr` por campana
- [ ] Si no estan presentes: agregar al SELECT/response del servicio (datos de Meta API)
- [ ] Verificar que el endpoint `combined-stats` en `google_ads_routes.py` esta montado correctamente en `/crm/marketing/` prefix

**Criterio:** GET `/crm/marketing/stats` retorna campanas con campos `impressions`, `clicks`, `ctr`.

---

## Orden de ejecucion

1. T-09.1 (fix params) — independiente, critico
2. T-09.2 (error banner) — independiente, critico
3. T-09.7 (verificar backend) — independiente
4. T-09.3 (tab combined type) — prerequisito de T-09.4/T-09.5
5. T-09.4 (CombinedCampaignsTable) — prerequisito de T-09.5
6. T-09.5 (renderizar tab combined) — depende de T-09.3 + T-09.4
7. T-09.6 (reconnection banner) — independiente

## Dependencias externas

- `MetaConnectionWizard` y `GoogleConnectionWizard` ya implementados — no requieren cambios
- Backend endpoints ya funcionales — solo verificacion en T-09.7
