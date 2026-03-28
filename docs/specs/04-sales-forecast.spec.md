# SPEC: Sales Forecasting & Advanced Analytics

**Fecha:** 2026-03-27
**Prioridad:** Alta (core CRM intelligence)
**Esfuerzo:** Medio (3-5 days backend + frontend)
**Confidence:** 90%

---

## 1. Context & Motivation

Sales managers currently see basic KPI cards on the CRM dashboard (`CrmDashboardView.tsx`): total leads, total clients, conversion rate, revenue, and a status distribution chart. There is **no funnel visualization**, **no revenue forecasting**, **no sales velocity tracking**, and **no win/loss analysis**.

The CRM already has the data foundation for all of this:

- **`leads` table**: tracks `status` (new, contacted, interested, negotiation, closed_won, closed_lost), `source`, `assigned_seller_id`, `created_at`
- **`opportunities` table**: tracks `stage`, `value`, `probability`, `expected_close_date`, `closed_at`, `lost_reason`, `seller_id`, `lead_id`
- **`sales_transactions` table**: tracks `amount`, `transaction_date`, `payment_status`, `opportunity_id`
- **`lead_status_history` table**: tracks every status transition with timestamps

The analytics gap means managers cannot:
1. Predict monthly/quarterly revenue with any confidence
2. Identify bottleneck stages in their pipeline
3. Set data-driven quotas per seller
4. Understand why deals are lost and where to intervene
5. Measure how acquisition cohorts convert over time

This spec adds four analytics modules that compute everything from existing tables -- no schema changes required.

---

## 2. Features

### 2.A Conversion Funnel

**Goal:** Visualize leads flowing through pipeline stages with conversion rates between each stage.

**Data source:** `leads.status` + `lead_status_history` (for historical transitions)

**Stages (in order):**
1. `new` -- Lead created
2. `contacted` -- First outreach made
3. `interested` -- Lead expressed interest
4. `negotiation` -- Active deal discussion
5. `closed_won` -- Deal won (converted to client)
6. `closed_lost` -- Deal lost

**Metrics per stage:**
- Count of leads currently in that stage
- Count of leads that have ever passed through that stage (historical)
- Conversion rate to next stage: `(leads_entering_next_stage / leads_entering_this_stage) * 100`
- Drop-off rate: `100 - conversion_rate`
- Average time spent in stage (days)

**Visualization:**
- Horizontal funnel chart (Recharts `BarChart` with decreasing bar widths or a custom SVG funnel)
- Each bar shows count + percentage
- Hover tooltip: conversion rate, avg time in stage, drop-off count
- Color gradient: from blue (`#3b82f6`) at top to green (`#22c55e`) at closed_won, red (`#ef4444`) for closed_lost branch

**Filters:**
- Period selector (7d, 30d, 90d, YTD, Custom date range)
- Seller filter (all / specific seller)
- Source filter (all / meta_ads / referral / apify / organic)

### 2.B Revenue Forecast

**Goal:** Predict future revenue using weighted pipeline methodology.

**Weighted Pipeline Formula:**
```
forecast_value = SUM(opportunity.value * (opportunity.probability / 100))
```
for all open opportunities (stage NOT IN ('closed_won', 'closed_lost')).

**Breakdown views:**

1. **By stage** -- Aggregate weighted value per pipeline stage:
   - Prospecting (10% default probability)
   - Qualification (25%)
   - Proposal (50%)
   - Negotiation (75%)
   - Total weighted pipeline

2. **By month** -- Group open opportunities by `expected_close_date` month:
   - Show weighted vs unweighted (best case) values
   - Rolling 3-month and 6-month projections

3. **By seller** -- Weighted pipeline per seller for quota comparison

**Historical accuracy:**
- Compare past forecasts vs actual closed revenue (using `opportunities` where `stage = 'closed_won'` and `closed_at` within period)
- Forecast accuracy % = `(actual_revenue / forecasted_revenue) * 100`

**Visualization:**
- `AreaChart` (Recharts): X-axis = months, Y-axis = revenue
- Two areas: "Weighted Forecast" (primary blue fill, 20% opacity) and "Actual Closed" (solid green line)
- Stacked bar overlay showing per-stage contribution to forecast
- Summary cards: Total Pipeline, Weighted Forecast, Closed This Period, Forecast Accuracy %

### 2.C Sales Velocity

**Goal:** Measure how fast the team converts leads to revenue.

**Sales Velocity Formula:**
```
velocity = (num_opportunities * avg_deal_value * win_rate) / avg_sales_cycle_days
```

**Individual metrics:**

1. **Average Days to Close:**
   - `AVG(closed_at - created_at)` for opportunities where `stage = 'closed_won'`
   - Breakdown by seller, by source, by deal size bracket

2. **Deals per Month:**
   - Count of `closed_won` opportunities grouped by `DATE_TRUNC('month', closed_at)`
   - Trend line over time

3. **Average Deal Size:**
   - `AVG(value)` for `closed_won` opportunities
   - Distribution histogram (buckets: <$1K, $1K-5K, $5K-15K, $15K-50K, $50K+)

4. **Win Rate:**
   - `closed_won / (closed_won + closed_lost) * 100`
   - Trend over time

**Visualization:**
- Four KPI cards at top (velocity score, avg cycle, deals/month, avg deal size)
- `LineChart`: velocity trend over last 6-12 months
- `BarChart`: deals per month with color-coded won/lost
- Seller comparison table with sparklines

### 2.D Win/Loss Analysis

**Goal:** Understand why deals are won or lost to improve strategy.

**Data source:** `opportunities` table (`stage`, `lost_reason`, `close_reason`, `seller_id`, `lead_id` joined with `leads.source`)

**Analyses:**

1. **Lost Reasons Breakdown:**
   - Group `lost_reason` values, count per reason
   - Top 5 reasons as horizontal bar chart
   - Predefined reason categories: `price`, `competitor`, `timing`, `no_budget`, `no_response`, `other`

2. **Win Rate by Seller:**
   - Per seller: total opportunities, won, lost, win rate %
   - Ranked table with progress bars

3. **Win Rate by Source:**
   - Per lead source (meta_ads, referral, apify, organic): conversion funnel and win rate
   - Identifies highest-quality lead sources

4. **Win Rate by Month:**
   - Monthly win rate trend to detect seasonality or team improvement

5. **Deal Value Distribution (Won vs Lost):**
   - Are larger deals harder to win? Compare avg value of won vs lost

**Visualization:**
- `PieChart` or horizontal `BarChart` for lost reasons
- Seller ranking table with inline sparklines
- `LineChart` for monthly win rate trend
- Source comparison cards with conversion metrics

### 2.E Cohort Analysis

**Goal:** Track how leads acquired in the same month convert over time.

**Cohort definition:** Leads grouped by `DATE_TRUNC('month', created_at)` -- acquisition month.

**Metrics per cohort:**
- Total leads acquired
- Conversion to each stage at 7d, 14d, 30d, 60d, 90d after acquisition
- Revenue generated per cohort

**Visualization:**
- Cohort heatmap table: rows = acquisition month, columns = time intervals (7d, 14d, 30d, 60d, 90d)
- Cell color intensity based on conversion rate (white/transparent = 0%, deep blue = high conversion)
- Click on a cell to see the individual leads in that cohort/interval

---

## 3. Backend

### 3.1 New Endpoints

All endpoints require `Depends(verify_admin_token)`. Tenant isolation via JWT-extracted `tenant_id`.

#### `GET /admin/core/crm/analytics/funnel`

**Query params:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `period` | string | `30d` | `7d`, `30d`, `90d`, `ytd`, `custom` |
| `start_date` | date | null | Required if period=custom |
| `end_date` | date | null | Required if period=custom |
| `seller_id` | UUID | null | Filter by seller |
| `source` | string | null | Filter by lead source |

**Response:**
```json
{
  "stages": [
    {
      "stage": "new",
      "current_count": 142,
      "historical_count": 580,
      "conversion_rate_to_next": 68.5,
      "avg_days_in_stage": 2.3,
      "drop_off_count": 183
    },
    {
      "stage": "contacted",
      "current_count": 89,
      "historical_count": 397,
      "conversion_rate_to_next": 52.1,
      "avg_days_in_stage": 4.7,
      "drop_off_count": 190
    }
  ],
  "total_leads": 580,
  "overall_conversion_rate": 12.4,
  "period": { "start": "2026-02-25", "end": "2026-03-27" }
}
```

**SQL strategy:**
- Current counts: `SELECT status, COUNT(*) FROM leads WHERE tenant_id = $1 AND created_at BETWEEN $2 AND $3 GROUP BY status`
- Historical flow: Query `lead_status_history` to count transitions between stages
- Avg days in stage: `AVG(EXTRACT(EPOCH FROM (exited_at - entered_at)) / 86400)` from `lead_status_history`
- If `lead_status_history` has insufficient data, fall back to snapshot counts from `leads` table

#### `GET /admin/core/crm/analytics/forecast`

**Query params:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `months_ahead` | int | `3` | Forecast horizon (1-12) |
| `seller_id` | UUID | null | Filter by seller |
| `group_by` | string | `month` | `month`, `stage`, `seller` |

**Response:**
```json
{
  "summary": {
    "total_pipeline": 485000.00,
    "weighted_forecast": 187250.00,
    "closed_this_month": 62000.00,
    "forecast_accuracy_pct": 84.2,
    "open_opportunities": 47
  },
  "by_month": [
    {
      "month": "2026-04",
      "weighted_value": 72500.00,
      "unweighted_value": 185000.00,
      "opportunity_count": 12
    },
    {
      "month": "2026-05",
      "weighted_value": 58300.00,
      "unweighted_value": 150000.00,
      "opportunity_count": 18
    }
  ],
  "by_stage": [
    {
      "stage": "prospecting",
      "count": 15,
      "total_value": 120000.00,
      "weighted_value": 12000.00,
      "default_probability": 10
    },
    {
      "stage": "negotiation",
      "count": 8,
      "total_value": 95000.00,
      "weighted_value": 71250.00,
      "default_probability": 75
    }
  ],
  "by_seller": [
    {
      "seller_id": "uuid",
      "seller_name": "Ana Lopez",
      "pipeline_value": 125000.00,
      "weighted_value": 48750.00,
      "open_deals": 11
    }
  ],
  "historical_accuracy": [
    {
      "month": "2026-01",
      "forecasted": 55000.00,
      "actual": 48200.00,
      "accuracy_pct": 87.6
    }
  ]
}
```

**SQL strategy:**
- Weighted pipeline: `SELECT stage, SUM(value) as total, SUM(value * probability / 100) as weighted FROM opportunities WHERE tenant_id = $1 AND stage NOT IN ('closed_won','closed_lost') GROUP BY stage`
- By month: Group by `DATE_TRUNC('month', expected_close_date)`
- By seller: Group by `seller_id`, join `users` for name
- Historical accuracy: Compare `SUM(value)` of `closed_won` in past months against the weighted forecast that was calculable at that time (sum of opportunity values * probability for opportunities that existed before the month started)

#### `GET /admin/core/crm/analytics/velocity`

**Query params:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `period` | string | `90d` | `30d`, `90d`, `180d`, `365d`, `ytd` |
| `seller_id` | UUID | null | Filter by seller |

**Response:**
```json
{
  "velocity_score": 14250.00,
  "avg_days_to_close": 23.4,
  "deals_per_month": 8.2,
  "avg_deal_size": 12500.00,
  "win_rate": 34.7,
  "trend": [
    {
      "month": "2026-01",
      "velocity": 11200.00,
      "avg_cycle": 27.1,
      "deals_closed": 6,
      "avg_size": 11800.00,
      "win_rate": 30.0
    }
  ],
  "by_seller": [
    {
      "seller_id": "uuid",
      "seller_name": "Ana Lopez",
      "velocity": 18500.00,
      "avg_cycle": 19.2,
      "deals_closed": 14,
      "win_rate": 42.1
    }
  ],
  "win_loss": {
    "total_won": 24,
    "total_lost": 45,
    "win_rate": 34.7,
    "lost_reasons": [
      { "reason": "price", "count": 15, "pct": 33.3 },
      { "reason": "competitor", "count": 12, "pct": 26.7 },
      { "reason": "no_response", "count": 8, "pct": 17.8 },
      { "reason": "timing", "count": 6, "pct": 13.3 },
      { "reason": "no_budget", "count": 4, "pct": 8.9 }
    ],
    "win_rate_by_source": [
      { "source": "meta_ads", "won": 10, "lost": 18, "rate": 35.7 },
      { "source": "referral", "won": 8, "lost": 5, "rate": 61.5 }
    ],
    "win_rate_by_month": [
      { "month": "2026-01", "won": 6, "lost": 14, "rate": 30.0 },
      { "month": "2026-02", "won": 9, "lost": 16, "rate": 36.0 }
    ]
  },
  "cohorts": [
    {
      "acquisition_month": "2025-10",
      "total_leads": 45,
      "conversions": {
        "7d": { "contacted": 32, "rate": 71.1 },
        "14d": { "interested": 18, "rate": 40.0 },
        "30d": { "negotiation": 10, "rate": 22.2 },
        "60d": { "closed_won": 5, "rate": 11.1 },
        "90d": { "closed_won": 7, "rate": 15.6 }
      },
      "revenue": 87500.00
    }
  ]
}
```

**SQL strategy:**
- Avg days to close: `SELECT AVG(EXTRACT(EPOCH FROM (closed_at - created_at)) / 86400) FROM opportunities WHERE stage = 'closed_won' AND tenant_id = $1 AND closed_at BETWEEN $2 AND $3`
- Deals per month: `SELECT DATE_TRUNC('month', closed_at) as m, COUNT(*) FROM opportunities WHERE stage = 'closed_won' ... GROUP BY m`
- Win rate: `SELECT COUNT(*) FILTER (WHERE stage='closed_won') as won, COUNT(*) FILTER (WHERE stage='closed_lost') as lost FROM opportunities WHERE stage IN ('closed_won','closed_lost') AND ...`
- Lost reasons: `SELECT lost_reason, COUNT(*) FROM opportunities WHERE stage = 'closed_lost' AND tenant_id = $1 GROUP BY lost_reason ORDER BY count DESC LIMIT 10`
- Win rate by source: Join `opportunities o JOIN leads l ON o.lead_id = l.id`, group by `l.source`
- Cohorts: `SELECT DATE_TRUNC('month', l.created_at) as cohort, ...` with lateral joins or window functions to check status at N days after creation

### 3.2 Backend File Structure

New service file:

```
orchestrator_service/
  services/
    crm_analytics_service.py    # NEW -- all forecast/funnel/velocity computation
  core/
    services/
      (existing service files)
```

New route registration in `admin_routes.py` (or a dedicated `crm_analytics_routes.py` if preferred for separation):

```python
# In admin_routes.py or new file crm_analytics_routes.py
from services.crm_analytics_service import CrmAnalyticsService

analytics_svc = CrmAnalyticsService()

@router.get("/admin/core/crm/analytics/funnel")
async def get_funnel(period: str = "30d", ..., user=Depends(verify_admin_token)):
    tenant_id = user["tenant_id"]
    return await analytics_svc.get_funnel(tenant_id, period, ...)

@router.get("/admin/core/crm/analytics/forecast")
async def get_forecast(months_ahead: int = 3, ..., user=Depends(verify_admin_token)):
    tenant_id = user["tenant_id"]
    return await analytics_svc.get_forecast(tenant_id, months_ahead, ...)

@router.get("/admin/core/crm/analytics/velocity")
async def get_velocity(period: str = "90d", ..., user=Depends(verify_admin_token)):
    tenant_id = user["tenant_id"]
    return await analytics_svc.get_velocity(tenant_id, period, ...)
```

### 3.3 Performance Considerations

- All queries filter by `tenant_id` first (leverages existing indexes)
- Existing indexes: `idx_opportunities_tenant`, `idx_opportunities_stage`, `idx_opportunities_expected_close`, `idx_opportunities_seller`
- For cohort analysis, consider adding index: `CREATE INDEX idx_leads_tenant_created ON leads(tenant_id, created_at)`
- Queries that span >90 days should use materialized aggregation or Redis cache (60s TTL) to avoid repeated full scans
- Max cohort lookback: 12 months

### 3.4 Default Stage Probabilities

When `opportunities.probability` is NULL or 0, use these defaults for weighted pipeline:

| Stage | Default Probability |
|-------|-------------------|
| `prospecting` | 10% |
| `qualification` | 25% |
| `proposal` | 50% |
| `negotiation` | 75% |
| `closed_won` | 100% |
| `closed_lost` | 0% |

---

## 4. Frontend

### 4.1 New View: `SalesAnalyticsView.tsx`

**Location:** `frontend_react/src/views/SalesAnalyticsView.tsx`

**Layout:**
```
+------------------------------------------------------------------+
|  Sales Analytics                              [Period: 30d v]     |
+------------------------------------------------------------------+
|  [Funnel]  [Forecast]  [Velocity]  [Win/Loss]  [Cohorts]         |
+------------------------------------------------------------------+
|                                                                   |
|  (tab content area — scrollable, flex-1 min-h-0 overflow-y-auto) |
|                                                                   |
+------------------------------------------------------------------+
```

**Global controls (shared across all tabs):**
- Period selector: segmented control with options `7d`, `30d`, `90d`, `YTD`, `Custom`
- Custom date range: two date inputs (shown only when "Custom" is selected)
- Seller filter dropdown (optional, default "All")
- Source filter dropdown (optional, default "All")

**Scroll isolation:**
- Outer container: `h-screen overflow-hidden`
- Tab content: `flex-1 min-h-0 overflow-y-auto`

### 4.2 Tab: Funnel

**Components:**
- Custom SVG funnel or Recharts `BarChart` (horizontal) with bars of decreasing width
- Each stage bar shows: label, count, percentage of total
- Between bars: conversion rate badge (e.g., "68.5%") with arrow
- Below funnel: table with columns: Stage | Count | Conversion % | Avg Days | Drop-off

**Cards above funnel (GlassCard):**
- Total Leads (in period)
- Overall Conversion Rate (new -> closed_won)
- Avg Time to Convert (days)
- Biggest Drop-off Stage

### 4.3 Tab: Forecast

**Components:**
- Top row: 4 GlassCard KPI cards
  - Total Pipeline (unweighted sum)
  - Weighted Forecast (sum of value * probability)
  - Closed This Month (actual revenue)
  - Forecast Accuracy (vs last month's forecast)

- Main chart: Recharts `AreaChart`
  - X: months (past 3 + future N based on `months_ahead`)
  - Y: revenue
  - Area 1: Weighted Forecast (fill: `#3b82f6`, opacity 0.15)
  - Line: Actual Closed (stroke: `#22c55e`, strokeWidth 2)
  - Dashed line: Unweighted Best Case (stroke: `#8b5cf6`, strokeDasharray "5 5")

- Secondary chart: Recharts `BarChart` (stacked) showing pipeline by stage
  - Each stage has a distinct color
  - Stacked bars show total pipeline composition per month

- Seller table: Name | Pipeline | Weighted | Open Deals | progress bar

### 4.4 Tab: Velocity

**Components:**
- Top row: 4 GlassCard KPI cards
  - Velocity Score (currency/day metric)
  - Avg Days to Close
  - Deals per Month
  - Avg Deal Size

- Trend chart: Recharts `LineChart`
  - X: months, Y: velocity score
  - Secondary Y-axis: avg cycle days
  - Two lines: velocity (blue) and cycle days (orange)

- Deals per month: Recharts `BarChart`
  - Stacked: won (green) vs lost (red) per month

- Seller comparison: table with sparklines per seller

### 4.5 Tab: Win/Loss

**Components:**
- Win Rate KPI card (big number, trend arrow)

- Lost Reasons: horizontal `BarChart`
  - Top 5 reasons, bars colored by severity
  - Shows count and percentage

- Win Rate by Source: `BarChart` grouped
  - X: source, Y: win rate %
  - Bar labels show won/total

- Win Rate by Month: `LineChart`
  - Trend line with month labels

- Win Rate by Seller: ranked table
  - Columns: Seller | Won | Lost | Rate % | progress bar

### 4.6 Tab: Cohorts

**Components:**
- Heatmap table
  - Rows: acquisition month (newest at top)
  - Columns: 7d, 14d, 30d, 60d, 90d
  - Cell: conversion rate % with background color intensity
  - Color scale: `bg-blue-500/10` (low) to `bg-blue-500/80` (high)

- Cohort size bar on the left of each row

- Revenue per cohort column on the right

### 4.7 Dark Theme Classes

All components follow the CRM dark palette:

| Element | Classes |
|---------|---------|
| Page background | `bg-[#06060e]` |
| Cards | `GlassCard` component (Ken Burns hover) |
| Tab bar | `bg-white/[0.04] border-b border-white/[0.06]` |
| Active tab | `text-white border-b-2 border-blue-400` |
| Inactive tab | `text-white/50 hover:text-white/70` |
| Chart container | `bg-white/[0.02] rounded-xl border border-white/[0.06] p-4` |
| Table header | `text-white/50 text-xs uppercase tracking-wider` |
| Table row | `border-b border-white/[0.04] hover:bg-white/[0.03]` |
| Period selector | `bg-white/[0.04] border border-white/[0.08] rounded-lg` |
| Active period | `bg-white text-[#0a0e1a] rounded-md` |
| Tooltip | `bg-[#0d1117] border border-white/[0.1] text-white text-sm` |

**Recharts theme overrides:**
```tsx
const chartColors = {
  primary: '#3b82f6',     // blue-500
  success: '#22c55e',     // green-500
  danger: '#ef4444',      // red-500
  warning: '#f59e0b',     // amber-500
  purple: '#8b5cf6',      // violet-500
  grid: 'rgba(255,255,255,0.04)',
  axis: 'rgba(255,255,255,0.3)',
  tooltip: '#0d1117',
};
```

### 4.8 API Integration

All API calls use the shared Axios instance (`import api from '../api/axios'`):

```typescript
// services/analyticsApi.ts
export const fetchFunnel = (params: FunnelParams) =>
  api.get('/admin/core/crm/analytics/funnel', { params });

export const fetchForecast = (params: ForecastParams) =>
  api.get('/admin/core/crm/analytics/forecast', { params });

export const fetchVelocity = (params: VelocityParams) =>
  api.get('/admin/core/crm/analytics/velocity', { params });
```

### 4.9 i18n Keys

Add to `es.json`, `en.json`, `fr.json`:

```json
{
  "nav.sales_analytics": "Analytics de Ventas",
  "analytics.funnel": "Embudo",
  "analytics.forecast": "Pronóstico",
  "analytics.velocity": "Velocidad",
  "analytics.win_loss": "Gan/Per",
  "analytics.cohorts": "Cohortes",
  "analytics.total_pipeline": "Pipeline Total",
  "analytics.weighted_forecast": "Pronóstico Ponderado",
  "analytics.closed_this_month": "Cerrado Este Mes",
  "analytics.forecast_accuracy": "Precisión del Pronóstico",
  "analytics.velocity_score": "Velocidad de Venta",
  "analytics.avg_days_close": "Días Promedio al Cierre",
  "analytics.deals_per_month": "Negocios por Mes",
  "analytics.avg_deal_size": "Tamaño Promedio",
  "analytics.win_rate": "Tasa de Cierre",
  "analytics.lost_reasons": "Motivos de Pérdida",
  "analytics.by_source": "Por Fuente",
  "analytics.by_seller": "Por Vendedor",
  "analytics.by_month": "Por Mes",
  "analytics.period_7d": "7 días",
  "analytics.period_30d": "30 días",
  "analytics.period_90d": "90 días",
  "analytics.period_ytd": "Este Año",
  "analytics.period_custom": "Personalizado",
  "analytics.conversion_rate": "Tasa de Conversión",
  "analytics.drop_off": "Abandono",
  "analytics.avg_time_stage": "Tiempo Promedio en Etapa",
  "analytics.acquisition_month": "Mes de Adquisición",
  "analytics.cohort_size": "Tamaño Cohorte"
}
```

---

## 5. Acceptance Criteria (Gherkin)

```gherkin
Scenario: Conversion funnel displays accurate stage counts and rates
  Given the tenant has 100 leads created in the last 30 days
  And 68 leads have transitioned from "new" to "contacted"
  And 35 leads have transitioned from "contacted" to "interested"
  When I navigate to "/crm/analytics" and select the "Funnel" tab
  And I set the period to "30d"
  Then I see a funnel with stages: new (100), contacted (68), interested (35), negotiation, closed_won, closed_lost
  And the conversion rate between "new" and "contacted" shows "68.0%"
  And the conversion rate between "contacted" and "interested" shows "51.5%"

Scenario: Revenue forecast shows weighted pipeline by month
  Given the tenant has 5 open opportunities in "proposal" stage with total value $50,000
  And 3 open opportunities in "negotiation" stage with total value $30,000
  And no custom probability is set on any opportunity
  When I navigate to "/crm/analytics" and select the "Forecast" tab
  Then the "Total Pipeline" card shows "$80,000"
  And the "Weighted Forecast" card shows "$47,500"
  Because proposal ($50,000 * 50%) = $25,000 and negotiation ($30,000 * 75%) = $22,500
  And the area chart shows projected revenue for the next 3 months grouped by expected_close_date

Scenario: Sales velocity calculates correctly across the period
  Given the tenant has closed 12 won deals in the last 90 days
  And those deals had an average value of $10,000
  And the average time from opportunity creation to close was 25 days
  And 20 deals were lost in the same period (win rate = 37.5%)
  When I navigate to "/crm/analytics" and select the "Velocity" tab
  And I set the period to "90d"
  Then the "Avg Days to Close" card shows "25"
  And the "Deals per Month" card shows "4.0"
  And the "Avg Deal Size" card shows "$10,000"
  And the "Win Rate" shows "37.5%"
  And the velocity score is calculated as (12 * 10000 * 0.375) / 25 = $1,800/day

Scenario: Win/Loss analysis shows lost reasons and seller ranking
  Given the tenant has 15 lost deals with reasons: "price" (6), "competitor" (4), "no_response" (3), "timing" (2)
  And seller "Ana" has won 8 and lost 5 deals (win rate 61.5%)
  And seller "Carlos" has won 3 and lost 10 deals (win rate 23.1%)
  When I navigate to "/crm/analytics" and select the "Win/Loss" tab
  Then the lost reasons chart shows "price" as the top reason with 40.0%
  And the seller ranking table shows "Ana" first with 61.5% win rate
  And the seller ranking table shows "Carlos" second with 23.1% win rate
```

---

## 6. Files to Create / Modify

### New Files

| File | Purpose |
|------|---------|
| `orchestrator_service/services/crm_analytics_service.py` | Service class with `get_funnel()`, `get_forecast()`, `get_velocity()` methods |
| `frontend_react/src/views/SalesAnalyticsView.tsx` | Main view with 5 tabs (Funnel, Forecast, Velocity, Win/Loss, Cohorts) |
| `frontend_react/src/services/analyticsApi.ts` | API client functions for the 3 analytics endpoints |

### Modified Files

| File | Change |
|------|--------|
| `orchestrator_service/admin_routes.py` | Add 3 new `GET /admin/core/crm/analytics/*` endpoints (or import from new route file) |
| `frontend_react/src/App.tsx` | Add route: `<Route path="crm/analytics" element={<SalesAnalyticsView />} />` |
| `frontend_react/src/components/Sidebar.tsx` | Add menu item: `{ id: 'analytics', labelKey: 'nav.sales_analytics', icon: <TrendingUp size={20} />, path: '/crm/analytics', roles: ['ceo'] }` |
| `frontend_react/src/locales/es.json` | Add `nav.sales_analytics` + all `analytics.*` keys |
| `frontend_react/src/locales/en.json` | Add `nav.sales_analytics` + all `analytics.*` keys |
| `frontend_react/src/locales/fr.json` | Add `nav.sales_analytics` + all `analytics.*` keys |

### Optional: New Index (migration)

If cohort query performance is insufficient:
```sql
-- migrations/patch_NNN_analytics_indexes.sql
CREATE INDEX IF NOT EXISTS idx_leads_tenant_created ON leads(tenant_id, created_at);
CREATE INDEX IF NOT EXISTS idx_opportunities_closed_at ON opportunities(tenant_id, closed_at);
```

---

## 7. Route & Sidebar Integration

### App.tsx Route

```tsx
import SalesAnalyticsView from './views/SalesAnalyticsView';

// Inside the Route tree, after existing crm/* routes:
<Route path="crm/analytics" element={<SalesAnalyticsView />} />
```

### Sidebar Entry

```tsx
// In Sidebar.tsx menuItems array, between 'marketing' and 'sellers':
{
  id: 'analytics',
  labelKey: 'nav.sales_analytics' as const,
  icon: <TrendingUp size={20} />,
  path: '/crm/analytics',
  roles: ['ceo']
},
```

Import `TrendingUp` from `lucide-react` at the top of `Sidebar.tsx`.

---

## 8. Out of Scope

- AI-powered forecast adjustments (future: use historical accuracy to auto-calibrate probabilities)
- Custom pipeline stage configuration (assumes fixed 6-stage pipeline)
- Real-time WebSocket updates for analytics (use polling or manual refresh)
- Export to PDF/CSV (can be added later as a follow-up)
- Goal/quota setting UI (future spec)

---

## 9. Dependencies

- **Recharts** -- already installed in the CRM frontend
- **lucide-react** -- already installed (need `TrendingUp` icon)
- **date-fns** or built-in `Intl.DateTimeFormat` -- for date formatting in charts
- No new backend dependencies required -- all computation uses raw SQL via asyncpg
