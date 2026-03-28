# SPEC: Lead Scoring System — CRM VENTAS

**Fecha:** 2026-03-27
**Prioridad:** Alta (impacto directo en conversion rate)
**Esfuerzo:** Medio (backend service + frontend badges + migration)
**Confidence:** 90%

---

## 1. Contexto y Problema

### Por que Lead Scoring es critico

Actualmente los vendedores del CRM priorizan leads de forma manual, revisando conversaciones de WhatsApp una por una. Esto genera tres problemas graves:

1. **Leads calientes se enfrian**: Un lead que pidio demo y pregunto precios puede quedar enterrado debajo de 50 leads frios si el vendedor no lo ve a tiempo.
2. **Tiempo desperdiciado**: Los vendedores gastan energia en leads que nunca van a convertir, en lugar de enfocarse en los que muestran senales claras de compra.
3. **Sin prediccion de conversion**: No hay forma objetiva de saber que porcentaje del pipeline tiene probabilidad real de cierre.

### Objetivo

Implementar un sistema de scoring automatico (0-100) que:
- Priorice leads calientes en tiempo real
- Alimente la vista de Kanban, lista y detalle con indicadores visuales
- Decaiga con el tiempo si el lead deja de interactuar
- Se recalcule automaticamente ante cada evento relevante

---

## 2. Modelo de Scoring (0-100)

El score total es la suma de tres dimensiones independientes:

```
TOTAL_SCORE = Engagement (0-40) + Fit (0-30) + Behavior (0-30)
```

### 2.1 Engagement Score (0-40 puntos)

Mide la intensidad y recencia de la interaccion del lead.

| Factor | Metrica | Puntos | Logica |
|--------|---------|--------|--------|
| **Frecuencia de mensajes** | Mensajes en ultimos 7 dias | 0-12 | 0 msgs=0, 1-2=3, 3-5=6, 6-10=9, 11+=12 |
| **Velocidad de respuesta** | Tiempo promedio de respuesta del lead | 0-10 | <5min=10, 5-30min=8, 30min-2h=5, 2-12h=3, >12h=0 |
| **Profundidad de conversacion** | Total de mensajes intercambiados | 0-8 | <3=0, 3-10=3, 11-25=5, 26-50=7, 50+=8 |
| **Recencia de actividad** | Tiempo desde ultimo mensaje del lead | 0-10 | <1h=10, 1-6h=8, 6-24h=6, 1-3d=3, 3-7d=1, >7d=0 |

**Decay rule**: Si `last_activity > 7 dias`, el Engagement Score se multiplica por `max(0, 1 - (days_since_activity - 7) * 0.1)`. Despues de 17 dias sin actividad, Engagement = 0.

### 2.2 Fit Score (0-30 puntos)

Mide que tan bien encaja el lead con el perfil ideal de cliente.

| Factor | Metrica | Puntos | Logica |
|--------|---------|--------|--------|
| **Calidad de fuente** | Campo `source` del lead | 0-12 | `meta_ads`=12, `referral`=10, `website`=8, `organic`=6, `manual`=3, `unknown`=0 |
| **Tamano de empresa** | Campo `company_size` o inferido | 0-10 | `enterprise`(250+)=10, `mid`(50-249)=8, `small`(10-49)=5, `micro`(1-9)=2, `unknown`=0 |
| **Match de industria** | Campo `industry` vs lista de industrias target | 0-8 | Match exacto con industria target=8, Match parcial=4, Sin dato o no-match=0 |

**Nota**: Las industrias target se configuran por tenant en `tenants.config.target_industries` (JSONB array). Si no esta configurado, industry match otorga 4 puntos por defecto a todo lead con industria definida.

### 2.3 Behavior Score (0-30 puntos)

Mide senales explicitas de intencion de compra detectadas en los mensajes de WhatsApp.

| Senal | Deteccion | Puntos | Acumulable |
|-------|-----------|--------|------------|
| **Solicito demo** | Keywords: "demo", "demostracion", "ver funcionando", "prueba gratuita", "probar" | +10 | No (max 10) |
| **Pregunto por precios** | Keywords: "precio", "costo", "cuanto sale", "planes", "cotizacion", "presupuesto" | +8 | No (max 8) |
| **Menciono competidores** | Keywords: lista configurable en tenant config | +5 | No (max 5) |
| **Senales de urgencia** | Keywords: "urgente", "lo antes posible", "esta semana", "rapido", "necesitamos ya", "cuanto antes" | +7 | No (max 7) |

**Deteccion**: Se analizan los mensajes entrantes del lead (no los del vendedor). La busqueda de keywords es case-insensitive y soporta variaciones con/sin tildes.

---

## 3. Clasificacion por Temperatura

| Rango | Temperatura | Color | Badge CSS |
|-------|-------------|-------|-----------|
| 80-100 | Hot | Rojo | `bg-red-500/10 text-red-400` |
| 50-79 | Warm | Naranja | `bg-orange-500/10 text-orange-400` |
| 20-49 | Cool | Azul | `bg-blue-500/10 text-blue-400` |
| 0-19 | Cold | Gris | `bg-white/5 text-white/30` |

---

## 4. Backend

### 4.1 Servicio: `lead_scoring_service.py`

**Ubicacion:** `backend/services/lead_scoring_service.py`

```python
# Estructura del servicio
class LeadScoringService:
    """Calcula y actualiza el score de leads (0-100)."""

    async def calculate_score(self, tenant_id: int, lead_id: int) -> dict:
        """
        Calcula score completo para un lead.
        Returns: {
            "total": 72,
            "engagement": {"total": 30, "message_frequency": 9, "response_speed": 8, "conversation_depth": 5, "recency": 8},
            "fit": {"total": 22, "source_quality": 12, "company_size": 5, "industry_match": 5},
            "behavior": {"total": 20, "requested_demo": 10, "asked_pricing": 8, "mentioned_competitors": 0, "urgency_signals": 2},
            "temperature": "warm",
            "calculated_at": "2026-03-27T14:30:00Z"
        }
        """

    async def recalculate_all(self, tenant_id: int) -> int:
        """Recalcula scores para todos los leads activos de un tenant. Returns count."""

    async def apply_decay(self, tenant_id: int) -> int:
        """Aplica decay a leads inactivos. Returns count of updated leads."""

    def _detect_behavior_signals(self, messages: list[str]) -> dict:
        """Detecta senales de comportamiento en mensajes del lead."""

    def _calculate_engagement(self, messages: list[dict], now: datetime) -> dict:
        """Calcula sub-scores de engagement."""

    def _calculate_fit(self, lead: dict, target_industries: list[str]) -> dict:
        """Calcula sub-scores de fit."""
```

### 4.2 Triggers de Recalculo

El score se recalcula en estos eventos:

| Evento | Trigger | Mecanismo |
|--------|---------|-----------|
| **Nuevo mensaje entrante** | Webhook de WhatsApp / mensaje procesado | Llamada directa desde el handler de mensajes |
| **Cambio de estado del lead** | `PATCH /admin/leads/{id}` (status change) | Hook en el endpoint de update |
| **Asignacion de vendedor** | `PATCH /admin/leads/{id}` (seller change) | Hook en el endpoint de update |
| **Decay periodico** | Cada 15 minutos | Background job con `asyncio.create_task` o scheduler |

### 4.3 Background Job: Decay

```python
# En main.py o jobs/lead_scoring_job.py
async def lead_scoring_decay_job():
    """Recalcula scores cada 15 minutos para aplicar decay por inactividad."""
    while True:
        await asyncio.sleep(900)  # 15 minutos
        tenants = await get_all_active_tenants()
        for tenant in tenants:
            scoring_service = LeadScoringService()
            updated = await scoring_service.apply_decay(tenant["id"])
            if updated > 0:
                logger.info(f"Decay applied to {updated} leads for tenant {tenant['id']}")
```

### 4.4 Endpoints

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| `GET` | `/admin/leads/{id}/score` | Score actual con breakdown completo |
| `POST` | `/admin/leads/{id}/score/recalculate` | Forzar recalculo manual |
| `GET` | `/admin/leads/scores/summary` | Resumen: count por temperatura, promedio general |

Todos los endpoints requieren `Depends(verify_admin_token)` y filtran por `tenant_id` del JWT.

### 4.5 Almacenamiento

Los scores se persisten directamente en la tabla `leads`:

```sql
-- Nuevas columnas en leads
score          INT       DEFAULT 0      -- Score total 0-100
score_breakdown JSONB    DEFAULT '{}'   -- Breakdown por dimension
score_updated_at TIMESTAMPTZ           -- Ultima vez que se calculo
```

El campo `score_breakdown` contiene el JSON completo del calculo (engagement, fit, behavior con sub-scores) para debugging y para mostrar tooltips en el frontend sin queries adicionales.

---

## 5. Migracion de Base de Datos

### Alembic Migration

**Archivo:** `backend/alembic/versions/XXX_add_lead_scoring_columns.py`

```python
"""Add lead scoring columns

Revision ID: auto-generated
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

def upgrade():
    op.add_column('leads', sa.Column('score', sa.Integer(), server_default='0', nullable=False))
    op.add_column('leads', sa.Column('score_breakdown', JSONB(), server_default='{}', nullable=False))
    op.add_column('leads', sa.Column('score_updated_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_leads_score', 'leads', ['score', 'tenant_id'], unique=False)

def downgrade():
    op.drop_index('ix_leads_score', table_name='leads')
    op.drop_column('leads', 'score_updated_at')
    op.drop_column('leads', 'score_breakdown')
    op.drop_column('leads', 'score')
```

**Indice compuesto** `(score, tenant_id)` para queries de ordenamiento por score dentro de un tenant.

**Actualizar modelo ORM** en el archivo de modelos correspondiente:

```python
class Lead(Base):
    # ... existing columns ...
    score = Column(Integer, default=0, server_default="0", nullable=False)
    score_breakdown = Column(JSONB, default=dict, server_default="{}", nullable=False)
    score_updated_at = Column(DateTime(timezone=True), nullable=True)
```

---

## 6. Frontend

### 6.1 Componente: `ScoreBadge.tsx`

**Ubicacion:** `frontend_react/src/components/ScoreBadge.tsx`

```tsx
interface ScoreBadgeProps {
  score: number;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

// Logica de color:
// 80-100 -> bg-red-500/10 text-red-400    "Hot"
// 50-79  -> bg-orange-500/10 text-orange-400  "Warm"
// 20-49  -> bg-blue-500/10 text-blue-400   "Cool"
// 0-19   -> bg-white/5 text-white/30       "Cold"
```

- `sm`: pill compacto, solo numero (para listas densas y kanban cards)
- `md`: pill con numero + label de temperatura (para headers de detalle)
- `lg`: circulo con porcentaje + label + icono de llama/copo (para hero sections)

### 6.2 Componente: `ScoreBreakdown.tsx`

**Ubicacion:** `frontend_react/src/components/ScoreBreakdown.tsx`

Tooltip o panel expandible que muestra las tres dimensiones con barras de progreso:

```
Engagement   ████████░░  30/40
Fit          ██████░░░░  22/30
Behavior     ██████░░░░  20/30
─────────────────────────────
Total                    72/100
```

Cada barra usa el color de la dimension: engagement=purple, fit=cyan, behavior=green.

### 6.3 Integracion en Vistas

| Vista | Ubicacion del Score | Formato |
|-------|---------------------|---------|
| **LeadsView** (lista) | Columna nueva "Score" en la tabla, ordenable | `ScoreBadge size="sm"` |
| **LeadsView** (filtros) | Nuevo filtro dropdown: "Todos / Hot / Warm / Cool / Cold" | Select con colores |
| **LeadDetailView** (header) | Al lado del nombre del lead | `ScoreBadge size="md"` + `ScoreBreakdown` en hover |
| **Kanban** (cards) | Esquina superior derecha de cada card | `ScoreBadge size="sm"` |
| **Dashboard** | KPI card: "Leads Hot: X, Warm: Y" | Contadores con colores |

### 6.4 Ordenamiento por Defecto

La vista de leads cambia su ordenamiento default de `created_at DESC` a `score DESC, last_activity DESC`. El vendedor ve primero los leads mas calientes y recientes.

### 6.5 i18n

Agregar a los archivos de locales (`es.json`, `en.json`):

```json
{
  "leadScoring": {
    "score": "Puntuacion",
    "hot": "Caliente",
    "warm": "Tibio",
    "cool": "Frio",
    "cold": "Muy frio",
    "engagement": "Interaccion",
    "fit": "Perfil",
    "behavior": "Comportamiento",
    "lastCalculated": "Ultima actualizacion",
    "recalculate": "Recalcular",
    "filterByTemperature": "Filtrar por temperatura"
  }
}
```

---

## 7. Criterios de Aceptacion (Gherkin)

### Scenario 1: Score se calcula al recibir un mensaje

```gherkin
Given un lead "Empresa ABC" con score 0 y sin mensajes previos
When el lead envia un mensaje de WhatsApp diciendo "Hola, me interesa ver una demo del producto"
Then el score del lead se recalcula automaticamente
  And el score de engagement es > 0 (por frecuencia y recencia)
  And el score de behavior incluye "requested_demo": 10
  And el score total se persiste en la columna leads.score
  And el score_breakdown se persiste como JSONB con las tres dimensiones
```

### Scenario 2: Score decae por inactividad

```gherkin
Given un lead "Empresa XYZ" con score 75 y ultima actividad hace 10 dias
When el background job de decay se ejecuta
Then el engagement score se multiplica por el factor de decay (1 - (10-7)*0.1 = 0.7)
  And el score total disminuye proporcionalmente
  And score_updated_at se actualiza al timestamp actual
```

### Scenario 3: Badge visual refleja la temperatura correcta

```gherkin
Given un lead con score 85
When el vendedor abre la vista de leads (lista o kanban)
Then el badge del lead muestra "85" con color rojo (bg-red-500/10 text-red-400)
  And el label dice "Caliente" (o "Hot" si el idioma es ingles)
When el vendedor hace hover sobre el badge en LeadDetailView
Then se muestra el breakdown: Engagement X/40, Fit Y/30, Behavior Z/30
```

### Scenario 4: Filtro por temperatura funciona correctamente

```gherkin
Given 20 leads con scores variados: 5 hot (80+), 8 warm (50-79), 4 cool (20-49), 3 cold (<20)
When el vendedor selecciona el filtro "Caliente" en LeadsView
Then solo se muestran los 5 leads con score >= 80
  And estan ordenados por score descendente
When el vendedor cambia el filtro a "Todos"
Then se muestran los 20 leads ordenados por score DESC, last_activity DESC
```

---

## 8. Archivos a Crear / Modificar

### Crear

| Archivo | Proposito |
|---------|-----------|
| `backend/services/lead_scoring_service.py` | Servicio de calculo de scores |
| `backend/jobs/lead_scoring_job.py` | Background job de decay cada 15min |
| `backend/alembic/versions/XXX_add_lead_scoring_columns.py` | Migracion de BD |
| `frontend_react/src/components/ScoreBadge.tsx` | Badge visual de score |
| `frontend_react/src/components/ScoreBreakdown.tsx` | Tooltip/panel de breakdown |

### Modificar

| Archivo | Cambio |
|---------|--------|
| `backend/models.py` | Agregar columnas `score`, `score_breakdown`, `score_updated_at` al modelo Lead |
| `backend/admin_routes.py` | Agregar endpoints `/leads/{id}/score`, `/leads/scores/summary`; hooks de recalculo en update |
| `backend/main.py` | Registrar background job de decay en startup |
| `frontend_react/src/views/LeadsView.tsx` | Columna score, filtro por temperatura, ordenamiento default |
| `frontend_react/src/views/LeadDetailView.tsx` | ScoreBadge + ScoreBreakdown en header |
| `frontend_react/src/components/KanbanCard.tsx` | ScoreBadge en esquina de card (o componente equivalente de kanban) |
| `frontend_react/src/views/DashboardView.tsx` | KPI card con conteo por temperatura |
| `frontend_react/src/locales/es.json` | Keys de `leadScoring.*` |
| `frontend_react/src/locales/en.json` | Keys de `leadScoring.*` |
| Handler de mensajes WhatsApp | Trigger de recalculo al procesar mensaje entrante |

---

## 9. Riesgos y Mitigaciones

| Riesgo | Impacto | Probabilidad | Mitigacion |
|--------|---------|--------------|------------|
| **Decay job sobrecarga la BD** | Alto | Media | Limitar recalculo a leads con `last_activity > 7d AND score > 0`. Usar batch updates con `UPDATE ... WHERE` en lugar de N queries individuales. |
| **Keywords de behavior generan falsos positivos** | Medio | Alta | Usar frases compuestas (no solo "precio" sino "cuanto sale", "que precio"). Permitir config de keywords por tenant. Log de detecciones para auditar. |
| **Score no refleja realidad del negocio** | Alto | Media | Los pesos (40/30/30) son iniciales. Agregar endpoint de config para ajustar pesos por tenant en fase 2. Monitorear correlacion score vs conversion real despues de 30 dias. |
| **Mensajes de WhatsApp no accesibles para analisis** | Alto | Baja | Verificar que los mensajes se persisten en BD (tabla `chat_messages` o equivalente del CRM). Si solo estan en Chatwoot, agregar sync. |
| **Race condition en recalculo concurrente** | Bajo | Baja | Usar `UPDATE leads SET score = $1 ... WHERE id = $2 AND tenant_id = $3` (atomico). No necesita lock explicito porque el score es idempotente para un estado dado. |
| **Rendimiento de queries con ORDER BY score** | Medio | Baja | Indice compuesto `(score, tenant_id)` en la migracion. Para tenants con >10K leads, considerar materialized view en fase 2. |

---

## 10. Fases de Implementacion

| Fase | Scope | Estimacion |
|------|-------|------------|
| **Fase 1** (MVP) | Migracion + servicio de scoring + triggers en mensajes + ScoreBadge en lista y kanban | 2-3 dias |
| **Fase 2** (Polish) | ScoreBreakdown tooltip + filtros + dashboard KPI + decay job | 1-2 dias |
| **Fase 3** (Tuning) | Config de pesos por tenant + config de keywords + analytics de correlacion score/conversion | 2-3 dias |
