# SPEC F-12: Dashboard Enhancements

**Priority:** Baja
**Complexity:** Baja
**Estado:** Draft
**Fecha:** 2026-04-14

---

## Contexto actual

`CrmDashboardView.tsx` funciona correctamente con:
- 4 KPI cards: Total Leads, Active Leads, Conversion Rate, Total Revenue
- Gráfico de torta: Lead Status Distribution (Pie chart con `recharts`)
- Gráfico de barras: Revenue & Leads Trend (BarChart con `recharts`)
- Tabla de Recent Leads con selección múltiple y bulk status update
- Selector de período: Weekly / Monthly
- Datos reales desde `GET /admin/core/crm/stats/summary`

Los trends de las KPI cards están hardcodeados (`+12%`, `+8%`, `+2.5%`, `+15%`). No hay quick actions, feed de actividad en tiempo real, ni widget de check-in. Los datos se cargan una vez al montar — no hay refresh automático ni Socket.IO.

---

## Requisitos funcionales

### RF-12.1: Quick Action Buttons — modales inline

- Cuatro botones de acción rápida en el header o en una barra de acciones:
  - **Nuevo Lead** → abre modal de creación de lead (nombre, teléfono, fuente, estado inicial)
  - **Nueva Llamada** → abre modal de registro de llamada (lead vinculado, duración, resultado, notas)
  - **Nuevo Deal** → abre modal de creación de oportunidad (lead vinculado, monto estimado, etapa)
  - **Nueva Cita** → abre modal de agendado de cita (lead, fecha/hora, tipo)
- Los modales deben ser componentes propios o reutilizar modales existentes en `src/components/`.
- Al confirmar el modal: POST al endpoint correspondiente + recargar las stats del dashboard.
- Comportamiento: los botones no navegan a otra página, abren modal in-place.

**No implementar:** lógica de negocio compleja dentro del modal. Solo el formulario básico con los campos mínimos necesarios.

### RF-12.2: Feed de actividad en tiempo real via Socket.IO

- Sección "Actividad Reciente" en el dashboard (bajo los gráficos o en sidebar lateral).
- Muestra los últimos N eventos del CRM: nuevo lead, cambio de estado, cita agendada, llamada registrada, deal cerrado.
- Se actualiza en tiempo real via Socket.IO: suscribir al evento `crm_activity` al montar el componente.
- Si Socket.IO no está disponible (conexión fallida), el feed muestra los últimos eventos cargados en el mount inicial (fallback estático).
- El backend debe emitir `crm_activity` con payload:
  ```json
  {
    "type": "lead_created" | "status_changed" | "appointment_created" | "deal_closed",
    "actor": "Nombre del usuario",
    "target": "Nombre del lead / deal",
    "timestamp": "ISO string"
  }
  ```
- El feed muestra máximo 20 eventos, scroll interno si hay más.

**Nota:** Si el evento Socket.IO `crm_activity` no existe en el backend → es parte del trabajo de este spec. El evento debe emitirse desde los endpoints relevantes de `admin_routes.py` o los routers de leads/deals.

### RF-12.3: Check-in widget integrado

- Widget compacto en el dashboard que muestra el estado del check-in del día del usuario autenticado.
- Si no hay check-in: botón "Iniciar jornada" que abre un mini-form inline (solo campo `llamadas_planeadas`).
- Si hay check-in abierto: muestra `llamadas_planeadas`, hora de inicio, y botón "Cerrar jornada".
- Si ya cerrado: muestra resumen del día (llamadas logradas, tasa de contacto).
- Datos: `GET /admin/core/checkin/today` al montar.
- Acciones: `POST /admin/core/checkin/` para check-in, `POST /admin/core/checkin/{id}/checkout` para checkout.
- El widget se coloca en la primera fila del dashboard, a la derecha de las KPI cards o como quinta card.

### RF-12.4: Banner de vendors pendientes (solo CEO/admin)

- Si el usuario tiene role `ceo` o `admin`, y hay vendors sin check-in del día: mostrar banner informativo.
- Datos: `GET /admin/core/checkin/ceo/today` → campo `count_sin_checkin`.
- Si `count_sin_checkin > 0`: banner amarillo en la parte superior con "N vendedores sin check-in hoy" y link "Ver panel".
- Si `count_sin_checkin === 0`: banner oculto.
- El banner no bloquea el contenido, es un strip informativo de una línea.

### RF-12.5: Badge de notificaciones

- El layout principal (navbar o sidebar) debe mostrar un badge numérico en el ítem de navegación o en un ícono de campana.
- Count se obtiene de `GET /admin/core/crm/vendor-tasks/pending-count` para el usuario autenticado.
- Se actualiza al montar y cada 5 minutos (polling simple, no Socket.IO para este caso).
- Si count = 0: badge oculto. Si count > 9: mostrar "9+".

**Nota:** Si el endpoint `pending-count` no existe → ver SPEC F-11 sección "Mis Notas". Esta funcionalidad depende de F-11.

### RF-12.6: Revenue trend chart con selector de período

- El chart "Revenue & Leads Trend" ya existe. Mejoras:
  - Agregar selector de período al chart: 3M / 6M / 12M (actualmente solo existe Weekly/Monthly a nivel global).
  - El selector es local al chart (no cambia el período global del dashboard).
  - Cada opción llama `GET /admin/core/crm/stats/summary?range=3m|6m|12m` solo para los datos del trend.
  - Las KPI cards mantienen el período global (Weekly/Monthly).
- Los trends de las KPI cards (`+12%`, etc.) deben calcularse comparando período actual vs período anterior. El backend debe devolver `trend_percent` por KPI o el frontend calcula si tiene datos de período anterior.

### RF-12.7: Pipeline breakdown con click-through

- Añadir una sección "Pipeline por Etapa" debajo de los gráficos actuales.
- Muestra las etapas del pipeline con count y valor total estimado por etapa: `new`, `contacted`, `interested`, `negotiation`, `closed_won`, `closed_lost`.
- Datos provienen de `status_distribution` que ya existe en la respuesta de `stats/summary`.
- Click en una etapa navega a `/crm/leads?status={stage}` (lista de leads filtrada por esa etapa).
- Barra de progreso horizontal proporcional al count total.

### RF-12.8: Indicadores de equipo online

- Sección compacta "Equipo Online" con avatares de usuarios que están activos actualmente.
- "Activo" definido como: hizo check-in hoy + `last_seen` en los últimos 30 minutos (si el campo existe).
- Datos: `GET /admin/core/checkin/ceo/today` (solo visible para CEO/admin) o un endpoint simplificado.
- Si el usuario no es CEO/admin: esta sección no se muestra.
- Avatares con iniciales del nombre, punto verde si online, gris si inactivo.
- Solo visible para roles `ceo` y `admin`.

---

## Contratos de API — existentes que se reutilizan

### GET `/admin/core/crm/stats/summary`

Ya existe. Verificar que devuelve los campos que el dashboard consume:

```json
{
  "total_leads": 234,
  "total_clients": 45,
  "active_leads": 89,
  "converted_leads": 34,
  "total_revenue": 1250000,
  "conversion_rate": 14.5,
  "revenue_leads_trend": [
    { "month": "Ene", "revenue": 80000, "leads": 28 },
    { "month": "Feb", "revenue": 95000, "leads": 32 }
  ],
  "status_distribution": [
    { "status": "new", "count": 45, "color": "#8b5cf6" },
    { "status": "contacted", "count": 32, "color": "#f59e0b" }
  ],
  "recent_leads": [
    {
      "id": "uuid",
      "name": "Juan Pérez",
      "phone": "+5491155551234",
      "status": "interested",
      "source": "META_ADS",
      "niche": "crm_sales",
      "created_at": "2026-04-14T10:00:00Z"
    }
  ]
}
```

**Agregar campo `trend_percent` por KPI** (si no existe):
```json
{
  "kpi_trends": {
    "total_leads": 12.5,
    "active_leads": 8.3,
    "conversion_rate": 2.1,
    "total_revenue": 15.2
  }
}
```

---

## Contratos de API — nuevos o a verificar

### Socket.IO evento `crm_activity`

Emitido desde el backend cuando ocurre cualquiera de estos eventos:
- Lead creado (`POST /admin/core/crm/leads`)
- Estado de lead cambiado
- Cita agendada
- Deal cerrado / ganado

**Payload:**
```json
{
  "type": "lead_created",
  "actor": "María González",
  "actor_id": "user_uuid",
  "target": "Carlos López",
  "target_id": "lead_uuid",
  "metadata": { "status": "new", "source": "META_ADS" },
  "timestamp": "2026-04-14T11:30:00Z"
}
```

El evento se emite al room del tenant: `tenant_{tenant_id}`.

El frontend se suscribe al montar `CrmDashboardView`:
```ts
socket.on('crm_activity', (event) => {
  setActivityFeed(prev => [event, ...prev].slice(0, 20));
});
```

### GET `/admin/core/crm/vendor-tasks/pending-count`

Ver SPEC F-11. Respuesta:
```json
{ "count": 3 }
```

---

## Impacto en archivos existentes

| Archivo | Cambio requerido |
|---------|-----------------|
| `CrmDashboardView.tsx` | Agregar RF-12.1 (quick actions), RF-12.2 (feed), RF-12.3 (check-in widget), RF-12.6 (selector chart), RF-12.7 (pipeline) |
| `CrmDashboardView.tsx` | RF-12.4 (banner CEO) y RF-12.8 (team online) solo si `userRole === 'ceo' || 'admin'` |
| Layout/Navbar (pendiente identificar) | RF-12.5 (notification badge) |
| `admin_routes.py` o router de leads | Agregar emit de `crm_activity` Socket.IO en endpoints relevantes |

---

## Orden de implementación recomendado

1. RF-12.7 — Pipeline breakdown (solo lectura, no nuevo código de backend)
2. RF-12.6 — Selector de período en chart Revenue (UX improvement, backend ya tiene el endpoint)
3. RF-12.3 — Check-in widget (depende de SPEC F-11 check-in backend)
4. RF-12.5 — Badge de notificaciones (depende de SPEC F-11 pending-count endpoint)
5. RF-12.4 — Banner CEO (depende de SPEC F-11 check-in CEO endpoint)
6. RF-12.1 — Quick actions modales (nuevo código UI)
7. RF-12.2 — Feed Socket.IO (requiere cambios en backend + frontend)
8. RF-12.8 — Team online (depende del check-in CEO + Socket.IO)

---

## Escenarios de prueba

**Escenario 1 — Quick action "Nuevo Lead":**
- Click en botón "Nuevo Lead" en el dashboard
- Modal se abre con campos: nombre, teléfono, fuente
- Completar y confirmar → POST al backend → modal cierra → stats se recargan
- El nuevo lead aparece en "Recent Leads" de la tabla

**Escenario 2 — Feed de actividad en tiempo real:**
- Dashboard abierto en dos tabs/ventanas
- Tab A: crear un nuevo lead
- Tab B: sin refrescar, el feed de actividad muestra "María González creó lead Carlos López" dentro de 2 segundos

**Escenario 3 — Check-in widget, usuario sin check-in:**
- Montar dashboard → widget muestra botón "Iniciar jornada"
- Click → mini-form con campo "Llamadas planeadas"
- Submit con `llamadas_planeadas: 20` → widget actualiza a "Jornada abierta: 20 llamadas / 08:30"

**Escenario 4 — Banner CEO con vendors sin check-in:**
- CEO accede al dashboard
- `GET /admin/core/checkin/ceo/today` → `count_sin_checkin: 3`
- Banner amarillo: "3 vendedores sin check-in hoy — Ver panel"
- Click en "Ver panel" → navega a la vista de check-in CEO

**Escenario 5 — Pipeline breakdown click-through:**
- Sección Pipeline muestra barra "interested: 32 leads"
- Click en la barra → navega a `/crm/leads?status=interested`
- La lista de leads ya está filtrada por ese estado

**Escenario 6 — KPI trends reales:**
- Dashboard carga período "Monthly"
- KPI "Total Leads" muestra 234 con badge "+12.5%"
- El 12.5% es calculado comparando con el mes anterior (no hardcodeado)

---

## Dependencias entre specs

- RF-12.3 (check-in widget) depende de SPEC F-11 §2 (Daily Check-in backend verificado)
- RF-12.4 (banner CEO) depende de SPEC F-11 §2 endpoint `GET /ceo/today` funcionando
- RF-12.5 (notification badge) depende de SPEC F-11 §3 endpoint `GET /pending-count` existente
- RF-12.2 (Socket.IO feed) es independiente pero complementa SPEC F-11 §1 (Chat Interno Socket.IO)
