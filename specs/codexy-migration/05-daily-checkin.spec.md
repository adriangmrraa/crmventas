# SPEC-05: Daily Check-in System

**Proyecto:** CRM VENTAS
**Origen:** Migración desde crmcodexy
**Prioridad:** Media
**Complejidad:** Media
**Estado:** Draft
**Fecha:** 2026-04-14
**Autor:** SDD Agent

---

## 1. Contexto y Motivación

### El problema

crmcodexy tiene una feature funcional de Daily Check-in que resuelve una necesidad real: visibilidad en tiempo real del estado operativo del equipo de ventas durante la jornada. El CEO puede ver quién arrancó, quién cerró, y cuánto cumplieron sus objetivos de llamadas — todo actualizado en vivo.

CRM VENTAS tiene el 80% de la infraestructura necesaria ya en pie (`seller_metrics_service`, APScheduler, Socket.IO, `SellerPerformanceView`), pero no tiene el concepto de jornada diaria explícita con check-in/check-out.

Migrar esta feature es añadir el 20% faltante encima de lo que ya existe, no construir desde cero.

### Qué aporta al producto

- **Accountability diaria**: los vendedores se comprometen con un número de llamadas al inicio de la jornada.
- **Panel CEO en tiempo real**: visibilidad operacional inmediata sin tener que calcular métricas históricas.
- **Tasa de éxito semanal**: insumo para el análisis de performance en `SellerPerformanceView`.
- **Integración con `seller_metrics_service`**: el check-in/check-out alimenta las 15+ métricas existentes con un campo nuevo: cumplimiento de jornada.

---

## 2. Alcance

### IN SCOPE

- Tabla `daily_checkins` en PostgreSQL (multi-tenant, con `tenant_id`)
- Modelo SQLAlchemy `DailyCheckin` en `models.py`
- Migración `patch_019_daily_checkins.sql`
- Servicio `DailyCheckinService` en `orchestrator_service/services/`
- Rutas FastAPI en `orchestrator_service/routes/checkin_routes.py`
- Eventos Socket.IO para broadcast en tiempo real al panel CEO
- APScheduler job: auto-cierre de jornadas abiertas a las 23:59
- APScheduler job: generación de resumen semanal de tasa de éxito
- Componente frontend `DailyCheckinView` (vista del vendedor)
- Componente frontend `CeoCheckinPanel` (panel CEO, reemplaza "Vendedores Hoy" de crmcodexy)
- Hook `useCheckinSocket` para suscripción en tiempo real
- Integración con `seller_metrics_service`: enriquecer métricas diarias con cumplimiento de jornada

### OUT OF SCOPE

- Notificaciones push por inactividad (eso es `seller_notification_service`, fase futura)
- Reporte PDF de check-ins (puede derivarse de `SalesAnalyticsView`)
- Check-in por geolocalización
- Historial de check-ins anterior a la migración

---

## 3. Modelo de Datos

### 3.1 Tabla `daily_checkins`

```sql
CREATE TABLE daily_checkins (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    seller_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    fecha           DATE NOT NULL DEFAULT CURRENT_DATE,

    -- Check-in data
    llamadas_planeadas  INTEGER NOT NULL CHECK (llamadas_planeadas > 0),
    checkin_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Check-out data (nullable hasta que el vendedor cierre)
    llamadas_logradas   INTEGER CHECK (llamadas_logradas >= 0),
    contactos_logrados  INTEGER CHECK (contactos_logrados >= 0),
    notas               TEXT,
    checkout_at         TIMESTAMP WITH TIME ZONE,

    -- Estado derivado (calculado)
    -- 'active'    = check-in hecho, sin check-out
    -- 'completed' = check-out hecho
    -- 'auto_closed' = cerrado por scheduler a las 23:59
    estado          TEXT NOT NULL DEFAULT 'active'
                        CHECK (estado IN ('active', 'completed', 'auto_closed')),

    -- Cumplimiento calculado al hacer checkout
    cumplimiento_pct    DECIMAL(5,2),  -- (logradas/planeadas) * 100

    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Un vendedor solo puede tener un check-in por día por tenant
    UNIQUE (tenant_id, seller_id, fecha)
);

CREATE INDEX idx_daily_checkins_tenant_fecha
    ON daily_checkins(tenant_id, fecha DESC);

CREATE INDEX idx_daily_checkins_seller_fecha
    ON daily_checkins(seller_id, fecha DESC);
```

### 3.2 Modelo SQLAlchemy

Agregar en `orchestrator_service/models.py`:

```python
class DailyCheckin(Base):
    __tablename__ = "daily_checkins"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    seller_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    fecha = Column(Date, nullable=False, server_default=func.current_date())

    # Check-in
    llamadas_planeadas = Column(Integer, nullable=False)
    checkin_at = Column(DateTime(timezone=True), server_default=func.now())

    # Check-out
    llamadas_logradas = Column(Integer, nullable=True)
    contactos_logrados = Column(Integer, nullable=True)
    notas = Column(Text, nullable=True)
    checkout_at = Column(DateTime(timezone=True), nullable=True)

    estado = Column(String(20), nullable=False, default="active")
    cumplimiento_pct = Column(DECIMAL(5, 2), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "seller_id", "fecha", name="uq_checkin_per_day"),
    )
```

---

## 4. Lógica de Negocio

### 4.1 Estados y transiciones

```
Sin check-in  ──checkin()──►  active  ──checkout()──►  completed
                                  │
                         scheduler 23:59
                                  │
                                  ▼
                             auto_closed
```

**Reglas:**
- Solo se puede hacer check-in una vez por día. Si el vendedor intenta un segundo check-in el mismo día: `409 Conflict`.
- No se puede hacer check-out sin check-in previo: `404 Not Found`.
- No se puede hacer check-out si `estado` ya es `completed` o `auto_closed`: `409 Conflict`.
- `cumplimiento_pct` se calcula SOLO al hacer check-out: `(llamadas_logradas / llamadas_planeadas) * 100`, redondeado a 2 decimales.
- Si `llamadas_planeadas = 0` (no debería ocurrir por la constraint, pero defensive): `cumplimiento_pct = 0`.

### 4.2 Colores de cumplimiento

| Rango | Color | Label |
|-------|-------|-------|
| ≥ 80% | verde (#22c55e) | Excelente |
| ≥ 50% y < 80% | amarillo (#f59e0b) | Regular |
| < 50% | rojo (#ef4444) | Bajo |
| `null` (sin checkout) | gris (#6b7280) | En jornada |

### 4.3 Status badge (panel CEO)

| Estado | Badge | Descripción |
|--------|-------|-------------|
| `completed` | Verde — "Jornada cerrada" | Hizo check-out |
| `auto_closed` | Naranja — "Cerrada automáticamente" | Scheduler |
| `active` | Azul — "En jornada" | Tiene check-in abierto |
| Sin registro | Gris — "Sin check-in" | No arrancó |

### 4.4 Tasa de éxito semanal

```
tasa_exito = (sum(llamadas_logradas) / sum(llamadas_planeadas)) * 100
             filtrado por los últimos 7 días, solo jornadas completed/auto_closed
```

Este valor se expone en:
- `SellerPerformanceView` (ya existente) como campo adicional
- Panel CEO en la sección de resumen semanal

---

## 5. API Endpoints

### Base path: `/admin/core/checkin`

| Método | Path | Descripción | Roles |
|--------|------|-------------|-------|
| POST | `/` | Hacer check-in del día | setter, closer, professional |
| POST | `/{checkin_id}/checkout` | Hacer check-out | seller owner |
| GET | `/today` | Mis datos de hoy | seller owner |
| GET | `/ceo/today` | Panel CEO: todos los vendedores hoy | ceo, admin |
| GET | `/ceo/weekly` | Resumen semanal por vendedor | ceo, admin |
| GET | `/history` | Historial del vendedor autenticado | seller owner |

### 5.1 POST `/admin/core/checkin/`

**Request body:**
```json
{
  "llamadas_planeadas": 20
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "seller_id": "uuid",
  "fecha": "2026-04-14",
  "llamadas_planeadas": 20,
  "estado": "active",
  "checkin_at": "2026-04-14T09:00:00Z"
}
```

**Errors:**
- `409` si ya existe check-in para hoy
- `400` si `llamadas_planeadas <= 0`

### 5.2 POST `/admin/core/checkin/{checkin_id}/checkout`

**Request body:**
```json
{
  "llamadas_logradas": 17,
  "contactos_logrados": 5,
  "notas": "Buen día, muchos leads calificados"
}
```

**Response 200:**
```json
{
  "id": "uuid",
  "llamadas_planeadas": 20,
  "llamadas_logradas": 17,
  "contactos_logrados": 5,
  "cumplimiento_pct": 85.00,
  "estado": "completed",
  "checkout_at": "2026-04-14T18:30:00Z"
}
```

**Errors:**
- `404` si el check-in no existe o no pertenece al vendedor
- `409` si ya está en estado `completed` o `auto_closed`

### 5.3 GET `/admin/core/checkin/ceo/today`

**Response 200:**
```json
{
  "fecha": "2026-04-14",
  "total_sellers": 5,
  "con_checkin": 4,
  "completados": 2,
  "vendedores": [
    {
      "seller_id": "uuid",
      "first_name": "Juan",
      "last_name": "Pérez",
      "estado": "completed",
      "llamadas_planeadas": 20,
      "llamadas_logradas": 17,
      "contactos_logrados": 5,
      "cumplimiento_pct": 85.00,
      "checkin_at": "2026-04-14T09:00:00Z",
      "checkout_at": "2026-04-14T18:30:00Z"
    },
    {
      "seller_id": "uuid",
      "first_name": "María",
      "last_name": "Gómez",
      "estado": "active",
      "llamadas_planeadas": 15,
      "llamadas_logradas": null,
      "contactos_logrados": null,
      "cumplimiento_pct": null,
      "checkin_at": "2026-04-14T08:45:00Z",
      "checkout_at": null
    },
    {
      "seller_id": "uuid",
      "first_name": "Carlos",
      "last_name": "López",
      "estado": "sin_checkin",
      "llamadas_planeadas": null,
      "llamadas_logradas": null,
      "contactos_logrados": null,
      "cumplimiento_pct": null,
      "checkin_at": null,
      "checkout_at": null
    }
  ]
}
```

**Nota:** incluye vendedores sin check-in haciendo LEFT JOIN con `users`.

### 5.4 GET `/admin/core/checkin/ceo/weekly`

**Query params:** `?weeks=1` (default 1, max 4)

**Response 200:**
```json
{
  "period": {
    "from": "2026-04-07",
    "to": "2026-04-14"
  },
  "vendedores": [
    {
      "seller_id": "uuid",
      "first_name": "Juan",
      "last_name": "Pérez",
      "jornadas_total": 5,
      "jornadas_completadas": 5,
      "llamadas_planeadas_total": 100,
      "llamadas_logradas_total": 87,
      "contactos_total": 23,
      "tasa_exito": 87.00,
      "cumplimiento_promedio": 85.40
    }
  ]
}
```

---

## 6. Servicio: `DailyCheckinService`

**Archivo:** `orchestrator_service/services/daily_checkin_service.py`

### Métodos públicos

```python
class DailyCheckinService:
    async def checkin(
        self,
        seller_id: UUID,
        tenant_id: int,
        llamadas_planeadas: int
    ) -> Dict

    async def checkout(
        self,
        checkin_id: UUID,
        seller_id: UUID,
        tenant_id: int,
        llamadas_logradas: int,
        contactos_logrados: int,
        notas: Optional[str]
    ) -> Dict

    async def get_today_for_seller(
        self,
        seller_id: UUID,
        tenant_id: int
    ) -> Optional[Dict]

    async def get_ceo_panel_today(
        self,
        tenant_id: int
    ) -> Dict  # LEFT JOIN users + daily_checkins WHERE fecha = TODAY

    async def get_weekly_summary(
        self,
        tenant_id: int,
        weeks: int = 1
    ) -> Dict

    async def get_seller_history(
        self,
        seller_id: UUID,
        tenant_id: int,
        limit: int = 30
    ) -> List[Dict]

    async def auto_close_open_checkins(
        self,
        tenant_id: int
    ) -> Dict  # Llamado por APScheduler

    async def broadcast_checkin_update(
        self,
        tenant_id: int,
        event: str,
        payload: Dict
    ) -> None  # Emite via Socket.IO
```

### Interacción con `seller_metrics_service`

Al hacer checkout, el servicio llama:
```python
await seller_metrics_service.update_metrics_for_checkout(
    seller_id=seller_id,
    tenant_id=tenant_id,
    llamadas_logradas=llamadas_logradas,
    cumplimiento_pct=cumplimiento_pct
)
```

Esto enriquece las métricas diarias existentes con el dato de jornada completada. Se agrega el método `update_metrics_for_checkout` a `SellerMetricsService`.

---

## 7. Tiempo Real: Socket.IO

### Room

Los clientes CEO se suscriben al room: `checkin:{tenant_id}`

### Eventos emitidos (server → client)

| Evento | Cuándo | Payload |
|--------|--------|---------|
| `checkin_created` | vendedor hace check-in | `{ seller_id, first_name, last_name, llamadas_planeadas, checkin_at, estado }` |
| `checkin_completed` | vendedor hace check-out | `{ seller_id, llamadas_logradas, contactos_logrados, cumplimiento_pct, checkout_at, estado }` |
| `checkin_auto_closed` | scheduler cierra jornada | `{ seller_id, checkout_at, estado: 'auto_closed' }` |

### Eventos recibidos (client → server)

| Evento | Descripción |
|--------|-------------|
| `subscribe_checkin` | `{ tenant_id }` — CEO se suscribe al panel |
| `unsubscribe_checkin` | `{ tenant_id }` — CEO se desuscribe |

### Registro en `socket_notifications.py`

Los handlers se registran en `register_notification_socket_handlers()` siguiendo el mismo patrón de `subscribe_lead_notes`.

---

## 8. APScheduler Jobs

Agregar en `ScheduledTasksService.start_all_tasks()`:

### Job 1: Auto-cierre de jornadas

```python
# Ejecutar a las 23:59 todos los días
self.scheduler.add_job(
    self.auto_close_open_checkins,
    CronTrigger(hour=23, minute=59),
    id='auto_close_checkins',
    name='Auto-close Open Check-ins',
    replace_existing=True
)
```

Comportamiento: busca todos los `daily_checkins` con `estado='active'` y `fecha=TODAY` para todos los tenants activos. Los marca como `auto_closed` y emite `checkin_auto_closed` por Socket.IO.

### Job 2: Resumen semanal (lunes 07:00)

```python
self.scheduler.add_job(
    self.generate_weekly_checkin_summary,
    CronTrigger(day_of_week='mon', hour=7, minute=0),
    id='weekly_checkin_summary',
    name='Weekly Check-in Summary',
    replace_existing=True
)
```

Comportamiento: calcula `tasa_exito` de la semana anterior por vendedor y la persiste en `seller_metrics` para consumo de `SellerPerformanceView`.

---

## 9. Frontend

### 9.1 Estructura de archivos

```
frontend_react/src/modules/crm_sales/
├── views/
│   ├── DailyCheckinView.tsx        # Vista del vendedor
│   └── CeoCheckinPanelView.tsx     # Panel CEO (nuevo)
├── components/
│   ├── CheckinForm.tsx             # Form check-in (nombre vendedor + llamadas_planeadas)
│   ├── CheckoutForm.tsx            # Form check-out (logradas + contactos + notas)
│   ├── CumplimientoBar.tsx         # Barra de progreso con color coding
│   └── SellerCheckinCard.tsx       # Card individual en panel CEO
└── hooks/
    └── useCheckinSocket.ts         # Suscripción Socket.IO al panel
```

### 9.2 `DailyCheckinView.tsx`

Lógica de estados en el frontend:

```
Estado local: 'idle' | 'checking_in' | 'active' | 'checking_out' | 'completed'

- idle:         Muestra CheckinForm
- active:       Muestra estado actual + botón "Cerrar jornada"
- completed:    Muestra resumen del día con CumplimientoBar
```

Al cargar, llama `GET /admin/core/checkin/today` para determinar el estado inicial.

### 9.3 `CeoCheckinPanelView.tsx`

- Al montar: llama `GET /admin/core/checkin/ceo/today` para estado inicial
- Al montar: llama `useCheckinSocket(tenantId)` para actualizaciones en tiempo real
- Muestra cards de todos los vendedores con `SellerCheckinCard`
- Muestra resumen: total con check-in, completados, en jornada, sin check-in
- Incluye tab "Resumen Semanal" que carga `GET /admin/core/checkin/ceo/weekly`

### 9.4 `CumplimientoBar.tsx`

```tsx
interface CumplimientoBarProps {
  planeadas: number;
  logradas: number | null;
  pct: number | null;
}
// Color: verde >= 80, amarillo >= 50, rojo < 50, gris si pct === null
```

### 9.5 `useCheckinSocket.ts`

```ts
function useCheckinSocket(tenantId: number) {
  // Retorna: { sellers: SellerCheckinState[], isConnected: boolean }
  // Suscribe al room `checkin:{tenantId}`
  // Maneja eventos: checkin_created, checkin_completed, checkin_auto_closed
  // Merge con estado local sin refetch completo
}
```

---

## 10. Seguridad y Multi-tenant

- Todos los endpoints requieren `tenant_id` resuelto via `get_resolved_tenant_id` (ya existente).
- El check-out valida que `seller_id` del token coincide con `seller_id` del registro (no puede hacer checkout por otro vendedor).
- El panel CEO requiere `role IN ('ceo', 'admin')` via `require_role`.
- Socket.IO: el evento `subscribe_checkin` valida que el `tenant_id` del token coincide con el solicitado.

---

## 11. Escenarios de Prueba

### Backend (TDD — obligatorio)

**Checkin Service:**

```
SCENARIO: Check-in exitoso
  DADO que el vendedor no tiene check-in hoy
  CUANDO llama a checkin(seller_id, tenant_id, llamadas_planeadas=20)
  ENTONCES retorna registro con estado='active'
  Y emite evento Socket.IO 'checkin_created'

SCENARIO: Check-in duplicado
  DADO que el vendedor ya tiene check-in hoy
  CUANDO llama a checkin() por segunda vez
  ENTONCES lanza excepción con código 409

SCENARIO: Checkout exitoso
  DADO que el vendedor tiene check-in en estado='active'
  CUANDO llama a checkout(llamadas_logradas=17, contactos_logrados=5)
  ENTONCES retorna registro con estado='completed'
  Y cumplimiento_pct = 85.00
  Y emite evento Socket.IO 'checkin_completed'

SCENARIO: Cumplimiento verde
  DADO checkout con planeadas=20, logradas=16
  ENTONCES cumplimiento_pct = 80.00
  Y color_class = 'green'

SCENARIO: Cumplimiento amarillo
  DADO checkout con planeadas=20, logradas=10
  ENTONCES cumplimiento_pct = 50.00
  Y color_class = 'yellow'

SCENARIO: Cumplimiento rojo
  DADO checkout con planeadas=20, logradas=9
  ENTONCES cumplimiento_pct = 45.00
  Y color_class = 'red'

SCENARIO: Auto-cierre scheduler
  DADO que existen check-ins activos al ejecutarse el job a las 23:59
  CUANDO se ejecuta auto_close_open_checkins()
  ENTONCES todos pasan a estado='auto_closed'
  Y se emite 'checkin_auto_closed' por Socket.IO

SCENARIO: Panel CEO incluye vendedores sin check-in
  DADO tenant con 3 vendedores activos, solo 2 hicieron check-in
  CUANDO se llama get_ceo_panel_today()
  ENTONCES retorna los 3 vendedores
  Y el tercero tiene estado='sin_checkin' y campos null
```

**Rutas (integración):**

```
SCENARIO: Vendedor hace checkout de checkin ajeno
  DADO checkin_id perteneciente a otro vendedor
  CUANDO POST /checkout con token de vendedor A
  ENTONCES 404 Not Found

SCENARIO: CEO accede al panel con rol setter
  CUANDO GET /ceo/today con token de setter
  ENTONCES 403 Forbidden
```

### Frontend

```
SCENARIO: DailyCheckinView — estado inicial sin check-in
  DADO que el vendedor no tiene check-in hoy
  CUANDO carga la vista
  ENTONCES muestra CheckinForm

SCENARIO: DailyCheckinView — transición a 'active'
  DADO que el form es válido
  CUANDO el vendedor submittea el check-in
  ENTONCES la vista muestra estado activo y botón "Cerrar jornada"

SCENARIO: CumplimientoBar — colores correctos
  DADO pct=85
  CUANDO renderiza
  ENTONCES barra es verde

SCENARIO: CeoCheckinPanelView — actualización en tiempo real
  DADO que el panel está abierto
  CUANDO llega evento 'checkin_created' por Socket
  ENTONCES se agrega el vendedor al panel sin reload
```

---

## 12. Dependencias y Orden de Implementación

```
1. patch_019_daily_checkins.sql
2. DailyCheckin model en models.py
3. DailyCheckinService (con TDD)
4. Método update_metrics_for_checkout en SellerMetricsService
5. checkin_routes.py
6. Socket.IO handlers en socket_notifications.py
7. APScheduler jobs en scheduled_tasks.py
8. Frontend: hooks/useCheckinSocket.ts
9. Frontend: components/CumplimientoBar.tsx
10. Frontend: components/CheckinForm.tsx + CheckoutForm.tsx + SellerCheckinCard.tsx
11. Frontend: views/DailyCheckinView.tsx
12. Frontend: views/CeoCheckinPanelView.tsx
13. Routing: agregar rutas en App.tsx
```

---

## 13. Archivos Afectados

| Archivo | Acción |
|---------|--------|
| `orchestrator_service/models.py` | Agregar `DailyCheckin` |
| `orchestrator_service/migrations/patch_019_daily_checkins.sql` | Crear |
| `orchestrator_service/services/daily_checkin_service.py` | Crear |
| `orchestrator_service/services/seller_metrics_service.py` | Agregar `update_metrics_for_checkout` |
| `orchestrator_service/routes/checkin_routes.py` | Crear |
| `orchestrator_service/main.py` | Registrar router |
| `orchestrator_service/services/scheduled_tasks.py` | Agregar 2 jobs |
| `orchestrator_service/core/socket_notifications.py` | Agregar handlers `subscribe_checkin` |
| `frontend_react/src/modules/crm_sales/hooks/useCheckinSocket.ts` | Crear |
| `frontend_react/src/modules/crm_sales/components/CumplimientoBar.tsx` | Crear |
| `frontend_react/src/modules/crm_sales/components/CheckinForm.tsx` | Crear |
| `frontend_react/src/modules/crm_sales/components/CheckoutForm.tsx` | Crear |
| `frontend_react/src/modules/crm_sales/components/SellerCheckinCard.tsx` | Crear |
| `frontend_react/src/modules/crm_sales/views/DailyCheckinView.tsx` | Crear |
| `frontend_react/src/modules/crm_sales/views/CeoCheckinPanelView.tsx` | Crear |
| `frontend_react/src/App.tsx` | Agregar rutas |

---

## 14. Decisiones de Diseño

**¿Por qué `estado` como columna explícita y no derivado?**
Simplifica las queries del panel CEO. Un `estado` derivado requeriría `CASE WHEN` en cada query. Con columna explícita, el scheduler lo setea una vez y todos leen directo.

**¿Por qué Socket.IO y no polling?**
CRM VENTAS ya tiene Socket.IO configurado y en uso para notificaciones y lead notes. Reutilizamos la misma infraestructura. Polling de 30s sería degradación comparado con crmcodexy que tenía Supabase Realtime.

**¿Por qué `seller_id` como UUID FK a `users` y no nombre de texto como crmcodexy?**
CRM VENTAS es multi-tenant con autenticación real. El "vendedor" en crmcodexy era texto libre — en la migración se mapea al usuario autenticado. El `first_name + last_name` se obtiene via JOIN para mostrar en el panel.

**¿Por qué no un microservicio separado?**
El check-in es inseparable de `seller_metrics_service` y de las notificaciones de vendedores. Vivir en `orchestrator_service` evita una llamada extra y comparte el pool de DB.
