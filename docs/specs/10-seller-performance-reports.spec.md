# SPEC: Admin — Reportes de Performance Individual por Vendedor

**Ticket:** DEV-41
**Fecha:** 2026-03-28
**Prioridad:** Media-Alta
**Esfuerzo:** Medio (3-4 dias)
**Confidence:** 91%

---

## 1. Contexto

El CRM tiene `seller_metrics` con KPIs agregados y un leaderboard. Pero no existe una vista detallada de performance individual donde el CEO pueda ver la evolución de un vendedor en el tiempo: tendencias, comparación hoy vs semana vs mes, breakdown por tipo de acción.

### Estado actual

| Componente | Estado |
|------------|--------|
| `SellerMetrics` model (leads_assigned, conversion_rate, etc.) | Existente |
| `GET /admin/core/sellers/{id}/metrics` | Existente |
| `GET /admin/core/sellers/leaderboard` | Existente |
| `GET /admin/core/sellers/team/metrics` | Existente |
| `activity_events` (DEV-39) | Existente |
| Vista detallada individual de vendedor | **NO existe** |
| Gráficas de tendencia temporal | **NO existe** |
| Comparativa vendedor vs promedio equipo | **NO existe** |

---

## 2. Requerimientos Técnicos

### 2.1 Backend: Endpoints

#### `GET /admin/core/sellers/{user_id}/performance`
KPIs detallados de un vendedor con breakdown temporal.

**Response:**
```json
{
  "seller": {"id": "uuid", "name": "Tomás García", "role": "setter"},
  "period": {"from": "2026-03-01", "to": "2026-03-28"},
  "kpis": {
    "leads_assigned": 45,
    "leads_converted": 12,
    "conversion_rate": 26.7,
    "avg_first_response_seconds": 180,
    "total_notes": 89,
    "total_calls": 34,
    "total_messages": 156,
    "active_leads_now": 15
  },
  "daily_breakdown": [
    {"date": "2026-03-28", "leads_assigned": 3, "leads_converted": 1, "actions": 12},
    {"date": "2026-03-27", "leads_assigned": 5, "leads_converted": 2, "actions": 18}
  ],
  "team_avg": {
    "conversion_rate": 22.1,
    "avg_first_response_seconds": 240
  },
  "event_type_breakdown": {
    "note_added": 89,
    "lead_status_changed": 67,
    "chat_message_sent": 156,
    "call_logged": 34,
    "lead_handoff": 8
  }
}
```

**Query params:** `date_from`, `date_to` (default: último mes)

### 2.2 Frontend: Vista SellerPerformanceView

- Ruta: `/crm/vendedores/{user_id}/performance`
- Acceso: CEO only
- Accesible desde: click en un vendedor en SellersView o TeamActivityView

**Layout:**
- Header con info del vendedor y período
- KPI cards (4-6 métricas principales)
- Gráfica de barras: acciones diarias (últimos 30 días)
- Gráfica de dona: breakdown por tipo de evento
- Comparativa: vendedor vs promedio del equipo (barras horizontales)
- Tabla: leads activos de este vendedor con último estado

---

## 3. Criterios de Aceptación

### Scenario 1: Ver performance de un vendedor
```gherkin
Given el CEO navega a /crm/vendedores/{id}/performance
Then ve los KPIs del vendedor con datos del último mes
And ve una gráfica de actividad diaria
And ve un breakdown por tipo de acción
```

### Scenario 2: Comparativa con equipo
```gherkin
Given el CEO ve la performance de "Tomás García"
Then ve su tasa de conversión (26.7%) vs promedio del equipo (22.1%)
And ve su tiempo de respuesta vs promedio del equipo
And los valores superiores al promedio se muestran en verde, inferiores en rojo
```

### Scenario 3: Filtro por período
```gherkin
Given el CEO cambia el rango de fechas a "última semana"
Then los KPIs y gráficas se actualizan para ese período
```

### Scenario 4: Acceso desde otros puntos
```gherkin
Given el CEO está en /crm/vendedores
When hace click en "Ver performance" de un vendedor
Then navega a /crm/vendedores/{id}/performance
```

---

## 4. Fuera de Alcance (v1)
- Export PDF del reporte
- Gráficas de tendencia semanal/mensual (solo diaria)
- Comparativa vendedor vs vendedor (1 vs equipo promedio)
- Objetivos/metas configurables por vendedor
