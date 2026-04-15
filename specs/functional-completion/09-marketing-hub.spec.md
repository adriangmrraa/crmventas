# SPEC F-09: Marketing Hub (Meta + Google Ads)

**Priority:** Media
**Complexity:** Alta
**Estado:** Draft
**Fecha:** 2026-04-14

---

## Contexto actual

`MarketingHubView.tsx` existe y tiene la estructura visual completa: tabs de plataforma (Meta / Google), selector de rango temporal, tabla de campañas/creatives, card de conexión con badge de estado, y wizards de conexión (`MetaConnectionWizard`, `GoogleConnectionWizard`).

El backend tiene los endpoints requeridos distribuidos en tres routers:
- `routes/marketing.py` → `/crm/marketing/stats`, `/crm/marketing/automation-logs`, `/crm/marketing/campaigns`
- `routes/google_ads_routes.py` → `/crm/marketing/combined-stats`, `/crm/marketing/google/campaigns`, `/crm/marketing/google/metrics`
- `routes/meta_auth.py` → `/crm/auth/meta/url`, `/crm/auth/meta/callback`
- `routes/google_auth.py` → `/crm/auth/google/ads/url`, `/crm/auth/google/ads/callback`

**Problemas identificados:**

1. El frontend llama `/crm/marketing/combined-stats` con param `range` pero el endpoint acepta `time_range`. Desajuste de parámetro.
2. El selector de rango en el frontend usa valores `last_30d`, `last_90d`, `this_year`, `all` pero los pasa como `range=${timeRange}` al combined-stats, que los ignora (usa `time_range`). Los rangos de Google van fijos a `LAST_30_DAYS` en la llamada.
3. `MetaTemplatesView.tsx` tiene `timezone` selector deshabilitado (hardcodeado `cursor-not-allowed disabled`) — incompleto.
4. La vista no tiene tab de "Vista Combinada" (merged Meta + Google) aunque el endpoint `/combined-stats` ya devuelve ambos.
5. Los errores OAuth se muestran con `alert()` nativo — debe ser toast/inline.
6. El flujo de reconexión por token expirado existe en URL params (`?reconnect=true`) pero no tiene banner visual persistente.

---

## Requisitos funcionales

### RF-09.1: Selector de rango temporal

- Valores: `last_30d` (30 días), `last_90d` (90 días), `this_year` (este año), `all` (histórico).
- Al cambiar el rango, se recargan las stats de ambas plataformas.
- El rango debe mapearse al equivalente de Google Ads: `last_30d → LAST_30_DAYS`, `last_90d → LAST_90_DAYS`, `this_year → THIS_YEAR`, `all → ALL_TIME`.
- El parámetro enviado al backend debe ser `time_range` (no `range`) — corregir llamada en `loadStats()`.

### RF-09.2: Tab Meta Ads

- Muestra badge de estado de conexión: "Conectado" (verde) / "Desconectado" (rojo).
- Si no conectado: botón "Conectar Meta" lanza OAuth via `GET /crm/auth/meta/url`.
- Si conectado: botón "Reconectar" visible pero secundario.
- Tabla de campañas: columnas nombre, inversión, leads, conversiones/oportunidades, ROI, estado.
- Tab secundario "Creatives" muestra breakdown a nivel de anuncio (ad-level).
- Métricas de campaña: `impressions`, `clicks`, `ctr`, `spend`, `leads`, `roi`, `status`.
- Datos provienen de `stats.meta.campaigns.campaigns` (tab Campañas) y `stats.meta.campaigns.creatives` (tab Creatives).

### RF-09.3: Tab Google Ads

- Mismas métricas de tabla que Meta: nombre, costo, conversiones, estado.
- Badge de estado de conexión Google: independiente del estado de Meta.
- Si no conectado: botón "Conectar Google Ads" lanza OAuth via `GET /crm/auth/google/ads/url`.
- Keyword performance: subtab o sección desplegable por campaña mostrando keywords con `clicks`, `impressions`, `ctr`, `average_cpc`.
- Datos provienen de `stats.google.campaigns` del endpoint `combined-stats`.

### RF-09.4: Vista Combinada

- Tercer tab "Combinado" muestra métricas aggregadas de Meta + Google.
- Totales: inversión total, leads totales, conversiones totales, ROI promedio ponderado.
- Tabla unificada con columna "Plataforma" (Meta / Google) para distinguir campañas.
- Usa los datos que ya retorna `combined-stats` en `data.combined`.

### RF-09.5: Manejo de errores OAuth

- Errores `missing_tenant`, `auth_failed`, `token_exchange_failed`, `google_auth_failed`, `invalid_state`, `invalid_oauth_type` se detectan via `searchParams.get('error')`.
- Reemplazar `alert()` por toast o banner inline con mensaje descriptivo y botón de dismiss.
- El banner persiste en pantalla 8 segundos o hasta dismiss manual.

### RF-09.6: Flujo de reconexión por token expirado

- Si `stats.meta.meta_connected === false` y el tenant tenía conexión previa (detectar via campo `token_expired_at` en respuesta), mostrar banner "Tu conexión con Meta expiró — reconectar".
- Banner incluye botón "Reconectar ahora" que ejecuta `handleConnectMeta()`.
- Mismo flujo para Google: si `stats.google.connected === false` con token previo.
- `?reconnect=true` en URL activa el banner automáticamente.

---

## Contratos de API

### GET `/crm/marketing/stats`

**Query params:**
- `time_range`: `last_30d` | `last_90d` | `this_year` | `all` (default: `last_30d`)

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "roi": {
      "meta_leads": 120,
      "converted_leads": 34,
      "total_revenue": 450000,
      "total_spend": 85000,
      "roi": 4.29,
      "currency": "ARS",
      "is_connected": true,
      "meta_connected": true
    },
    "campaigns": {
      "campaigns": [...],
      "creatives": [...]
    },
    "currency": "ARS",
    "meta_connected": true
  }
}
```

### GET `/crm/marketing/combined-stats`

**Query params (corrección requerida en frontend):**
- `time_range`: `last_30d` | `last_90d` | `this_year` | `all`
- `google_date_range`: `LAST_30_DAYS` | `LAST_90_DAYS` | `THIS_YEAR` | `ALL_TIME`

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "meta": {
      "roi": { "meta_leads": 120, "roi": 4.29, "is_connected": true },
      "campaigns": { "campaigns": [...], "creatives": [...] },
      "currency": "ARS",
      "meta_connected": true
    },
    "google": {
      "connected": true,
      "customer_ids": ["1234567890"],
      "current_customer": "1234567890",
      "campaigns": [
        {
          "id": "camp_001",
          "name": "Campaña Awareness Q1",
          "status": "ENABLED",
          "impressions": 84000,
          "clicks": 2100,
          "cost": 45000,
          "conversions": 23,
          "ctr": 0.025
        }
      ],
      "metrics": { "total_cost": 45000, "total_conversions": 23 }
    },
    "combined": {
      "total_spend": 130000,
      "total_leads": 143,
      "total_conversions": 57,
      "weighted_roi": 3.8
    }
  }
}
```

### POST `/crm/marketing/oauth/meta`

Alias interno para iniciar flujo OAuth Meta. El frontend actualmente usa `GET /crm/auth/meta/url` (correcto, no cambia).

### POST `/crm/marketing/oauth/google`

Alias interno para iniciar flujo OAuth Google. El frontend actualmente usa `GET /crm/auth/google/ads/url` (correcto, no cambia).

---

## Correcciones requeridas en el frontend

| Archivo | Problema | Corrección |
|---------|----------|------------|
| `MarketingHubView.tsx` L76 | Param `range=` | Cambiar a `time_range=` |
| `MarketingHubView.tsx` L76 | Google range fijo `LAST_30_DAYS` | Mapear desde `timeRange` state |
| `MarketingHubView.tsx` L34-41 | `alert()` nativo | Reemplazar por toast/banner inline |
| `MarketingHubView.tsx` L21 | No existe tab "combined" | Agregar tercer estado al `activePlatform` |

---

## Correcciones requeridas en el backend

| Archivo | Problema | Corrección |
|---------|----------|------------|
| `routes/google_ads_routes.py` | `combined-stats` registrado en router de google pero montado en `/crm/marketing/` — verificar prefijo en `main.py` | Confirmar que `GET /crm/marketing/combined-stats` funciona en producción |
| `routes/marketing.py` | Endpoint `/stats` no devuelve datos de `impressions`/`clicks`/`ctr` por campaña | Agregar campos desde Meta API si conectado |

---

## Escenarios de prueba

**Escenario 1 — Meta desconectado:**
- `GET /crm/marketing/combined-stats` → `meta.meta_connected: false`
- Vista muestra badge "Desconectado" en tab Meta
- Botón "Conectar Meta" visible
- Tabla de campañas vacía con empty state "Conecta tu cuenta de Meta Ads"

**Escenario 2 — Meta conectado, Google desconectado:**
- `meta.meta_connected: true`, `google.connected: false`
- Tab Meta muestra datos de campañas
- Tab Google muestra badge "Desconectado" con botón "Conectar Google Ads"
- Tab Combinado muestra solo datos Meta con aviso "Google no conectado"

**Escenario 3 — Ambas plataformas conectadas:**
- Todos los tabs con datos
- Tab Combinado muestra tabla unificada con columna "Plataforma"
- Totales combinados en header

**Escenario 4 — Error OAuth `token_exchange_failed`:**
- URL redirige con `?error=token_exchange_failed`
- Banner inline rojo con mensaje "Error al intercambiar token de autorización"
- Sin `alert()` nativo
- Banner desaparece en 8s o al hacer click en X

**Escenario 5 — Cambio de rango temporal:**
- Al seleccionar `last_90d`, se llama `combined-stats?time_range=last_90d&google_date_range=LAST_90_DAYS`
- Datos actualizados en todas las tabs
- Loading state visible durante fetch

---

## Dependencias

- `MetaConnectionWizard` y `GoogleConnectionWizard` ya implementados (no requieren cambios)
- `MarketingPerformanceCard` ya implementado
- Backend `AutomationService` independiente de este spec
- Credenciales `META_USER_LONG_TOKEN` y `GOOGLE_ADS_REFRESH_TOKEN` deben existir en `tenant_credentials` para que las plataformas aparezcan como conectadas
