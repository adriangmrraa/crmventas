# Arquitectura del Sistema - CRM Ventas (Actualizado Sprint 2)

Este documento describe la estructura técnica, el flujo de datos y la interacción entre los componentes de la plataforma CRM Ventas, incluyendo las nuevas funcionalidades del **Sprint 2 - Tracking Avanzado**.

## 1. Diagrama de Bloques (Conceptual)

```
Usuario WhatsApp (Lead/Cliente)
        |
        | Audio/Texto
        v
WhatsApp Service (8002)
  - YCloud Webhook
  - Deduplicación (Redis)
  - Transcripción (Whisper)
        |
        | POST /chat
        v
Orchestrator Service (8000)
  - LangChain Agent (Asistente de Ventas)
  - Tools CRM (Agenda, Lead Scoring, Asignación)
  - Memoria Histórica (Postgres)
  - Socket.IO Server (Real-time)
  - Background Jobs (APScheduler)
        |
    ____|____
   /    |    \
  v     v     v
PostgreSQL Redis OpenAI
(Leads, Métricas)(Cache, Notificaciones)(LLM)
   |
   v
Frontend React (5173)
Centro de Operaciones CRM
   |
   | WebSocket (Socket.IO)
   v
Dashboard CEO / ChatsView / Métricas
   - Real-time updates
   - Notificaciones inteligentes
   - Background jobs monitoring
```

## 2. Estructura de Microservicios (CRM Ventas)

### A. WhatsApp Service (Puerto 8002)

**Tecnología:** FastAPI + httpx + Redis

**Función:** Interfaz de comunicación con leads vía YCloud.

**Componentes:**
- `ycloud_client.py`: Cliente para YCloud API
- `whisper_service.py`: Transcripción de audios (OpenAI Whisper)
- `deduplication.py`: Prevención de mensajes duplicados (Redis)

**Flujo:**
1. YCloud envía webhook → `/webhooks/ycloud`
2. Validación de firma HMAC
3. Deduplicación (Redis SETEX)
4. Si es audio → transcripción con Whisper
5. POST a `/chat` (Orchestrator)

### B. Orchestrator Service (Puerto 8000)

**Tecnología:** FastAPI + LangChain + Socket.IO + APScheduler

**Función:** Cerebro central del CRM. Gestiona leads, conversaciones, agenda, métricas y notificaciones.

**Componentes Principales:**

#### **Core Services (Sprint 2):**
1. **`SellerMetricsService`**: Cálculo de 15+ métricas en tiempo real con Redis cache
2. **`SellerNotificationService`**: Sistema de notificaciones inteligentes (4 tipos)
3. **`ScheduledTasksService`**: Background jobs programados con auto-start
4. **`SellerAssignmentService`**: Lógica de asignación de leads a vendedores

#### **Real-time Components:**
1. **`SocketNotificationService`**: WebSocket handlers para notificaciones en tiempo real
2. **`SocketManager`**: Configuración central de Socket.IO
3. **Health Checks**: Endpoints de monitoreo del sistema

#### **API Routes (Nuevas - Sprint 2):**
1. **`/admin/core/sellers/*`**: Gestión de vendedores y métricas
2. **`/notifications/*`**: Sistema de notificaciones
3. **`/scheduled-tasks/*`**: Gestión de background jobs
4. **`/health/*`**: Health checks y monitoring

### C. Frontend React (Puerto 5173)

**Tecnología:** React 18 + TypeScript + Vite + Socket.IO Client

**Función:** Centro de Operaciones CRM con interface moderna y real-time updates.

**Componentes Nuevos (Sprint 2):**

#### **Real-time Context:**
- **`SocketContext.tsx`**: Contexto React para Socket.IO con auto-connect
- **`useSocketNotifications`**: Hook personalizado para notificaciones

#### **UI Components:**
1. **`NotificationBell.tsx`**: Badge con count de notificaciones
2. **`NotificationCenter.tsx`**: Centro completo de gestión de notificaciones
3. **`SellerBadge.tsx`**: Badge de vendedor en conversaciones
4. **`SellerSelector.tsx`**: Modal para asignación de vendedores
5. **`SellerMetricsDashboard.tsx`**: Dashboard CEO con métricas avanzadas
6. **`MetaLeadsView.tsx`**: Vista especializada para leads de Meta Ads

#### **Views Actualizadas:**
- **`ChatsView.tsx`**: Integración completa con sistema de vendedores
- **`Layout.tsx`**: Integración de NotificationBell en header

## 3. Arquitectura de Background Jobs (Nuevo - Sprint 2)

### **🏗️ Sistema de Tareas Programadas:**

```
Orchestrator Startup
        |
        v
startup_event() → scheduled_tasks_service.start_all_tasks()
        |
        v
[4 Tareas Programadas]
├── Notification Checks (cada 5 minutos)
│   ├── Conversaciones sin respuesta (> 1h)
│   ├── Leads calientes (alta probabilidad)
│   ├── Recordatorios de follow-up
│   └── Alertas de performance
│
├── Metrics Refresh (cada 15 minutos)
│   ├── Actualización métricas vendedores
│   ├── Cache Redis actualizado
│   └── Socket.IO updates enviados
│
├── Data Cleanup (cada 1 hora)
│   ├── Notificaciones expiradas (> 7 días)
│   ├── Métricas antiguas (> 30 días)
│   └── Sesiones inactivas (> 7 días)
│
└── Daily Reports (8:00 AM cada día)
    ├── Resumen actividad diaria
    ├── Métricas del equipo
    └── Notificación a CEO
```

### **🔧 Configuración:**
```bash
# Variables de entorno
ENABLE_SCHEDULED_TASKS=true
NOTIFICATION_CHECK_INTERVAL_MINUTES=5
METRICS_REFRESH_INTERVAL_MINUTES=15
CLEANUP_INTERVAL_HOURS=1
```

### **📊 Health Monitoring:**
```
GET /health              # Health check completo
GET /health/tasks        # Estado de background jobs
GET /health/readiness    # Readiness probe (Kubernetes)
GET /health/liveness     # Liveness probe (Kubernetes)
POST /health/tasks/start # Iniciar tasks manualmente
POST /health/tasks/stop  # Detener tasks manualmente
```

## 4. Arquitectura de Notificaciones en Tiempo Real (Nuevo - Sprint 2)

### **⚡ Sistema Socket.IO:**

```
Frontend (React)
        |
        | WebSocket Connection
        v
Socket.IO Server (Orchestrator)
        |
        | Event Handlers
        v
[5 Eventos Principales]
├── notification_connected     # Conexión establecida
├── notification_subscribed    # Usuario suscrito
├── new_notification          # Nueva notificación
├── notification_count_update # Count actualizado
└── notification_marked_read  # Notificación leída
```

### **🔗 Integración Frontend:**
```typescript
// SocketContext.tsx
const SocketProvider = ({ children }) => {
  const socket = useSocket(); // Auto-connect con exponential backoff
  
  return (
    <SocketContext.Provider value={socket}>
      {children}
    </SocketContext.Provider>
  );
};

// NotificationBell.tsx
const NotificationBell = () => {
  const { socketConnected, notifications } = useSocketNotifications();
  
  return (
    <div>
      {socketConnected ? '🔔' : '📡'}
      <span>{notifications.length}</span>
    </div>
  );
};
```

### **🔄 Fallback Mechanism:**
1. **Primary**: Socket.IO WebSocket connection
2. **Fallback**: API polling cada 30 segundos
3. **Status Indicators**: UI muestra estado de conexión

## 5. Arquitectura de Métricas en Tiempo Real (Nuevo - Sprint 2)

### **📈 Sistema de Métricas:**

```
Data Sources
├── Conversaciones (PostgreSQL)
├── Leads (PostgreSQL)
├── Asignaciones (PostgreSQL)
└── Actividad (Redis)

        |
        v
SellerMetricsService
├── Cálculo 15+ métricas
├── Redis Cache (5 minutos)
└── Background refresh (15 minutos)

        |
        v
API Endpoints
├── GET /admin/core/sellers/metrics
├── GET /admin/core/sellers/leaderboard
└── GET /admin/core/sellers/dashboard

        |
        v
Frontend Dashboard
├── Gráficos en tiempo real
├── Leaderboard ranking
└── Filtros por fecha/tenant
```

### **🔍 Métricas Calculadas:**
1. **Conversaciones**: Totales, activas, hoy, por vendedor
2. **Tiempos**: Respuesta promedio, tiempo en chat
3. **Conversiones**: Leads generados, convertidos, tasa
4. **Performance**: Engagement, actividad, productividad
5. **Team Metrics**: Totales equipo, comparativas

## 6. Flujo de Datos Multi-Tenant

### **🔐 Aislamiento de Datos:**

```python
# Todas las queries incluyen tenant_id
async def get_seller_metrics(tenant_id: int, seller_id: int):
    query = """
        SELECT * FROM seller_metrics 
        WHERE tenant_id = $1 AND seller_id = $2
    """
    return await db.fetchrow(query, tenant_id, seller_id)

# JWT validation incluye tenant
def get_current_tenant(request: Request):
    token = request.headers.get("Authorization")
    payload = decode_jwt(token)
    return payload.get("tenant_id")
```

### **👥 Roles y Permisos:**
1. **CEO**: Acceso completo a todos los tenants
2. **Seller**: Solo su tenant asignado, solo sus métricas
3. **Secretary**: Solo lectura, no modificación
4. **Professional**: Acceso limitado según configuración

## 7. Base de Datos (Actualizado Sprint 2)

### **🗄️ Tablas Nuevas:**

```sql
-- Notificaciones (Sprint 2)
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    type VARCHAR(50) NOT NULL, -- 'unanswered', 'hot_lead', 'follow_up', 'performance'
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    data JSONB DEFAULT '{}',
    read BOOLEAN DEFAULT FALSE,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Configuración notificaciones
CREATE TABLE notification_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    notification_types JSONB DEFAULT '["unanswered", "hot_lead", "follow_up", "performance"]',
    email_notifications BOOLEAN DEFAULT FALSE,
    push_notifications BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Métricas vendedores (Sprint 2)
CREATE TABLE seller_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    seller_id INTEGER REFERENCES users(id) NOT NULL,
    period DATE NOT NULL, -- Fecha de las métricas
    metrics JSONB NOT NULL, -- 15+ métricas en JSON
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, seller_id, period)
);
```

### **📊 Índices de Performance:**
```sql
CREATE INDEX idx_notifications_tenant_user ON notifications(tenant_id, user_id);
CREATE INDEX idx_notifications_unread ON notifications(tenant_id, user_id, read) WHERE read = FALSE;
CREATE INDEX idx_seller_metrics_period ON seller_metrics(tenant_id, period);
CREATE INDEX idx_seller_metrics_seller ON seller_metrics(tenant_id, seller_id, period DESC);
```

## 8. Deployment y Escalabilidad

### **🐳 Docker Compose (Actualizado):**

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: crmventas
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data

  orchestrator:
    build: ./orchestrator_service
    environment:
      - POSTGRES_DSN=postgresql://user:password@postgres:5432/crmventas
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379
      - ENABLE_SCHEDULED_TASKS=true
      - NOTIFICATION_CHECK_INTERVAL_MINUTES=5
      - METRICS_REFRESH_INTERVAL_MINUTES=15
    depends_on:
      - postgres
      - redis

  frontend:
    build: ./frontend_react
    ports:
      - "5173:5173"
    depends_on:
      - orchestrator

volumes:
  postgres_data:
  redis_data:
```

### **📈 Consideraciones de Escalabilidad:**

1. **Redis Cluster**: Para alta carga de métricas en tiempo real
2. **WebSocket Load Balancer**: Sticky sessions para Socket.IO
3. **Background Workers**: Separación de scheduled tasks a workers dedicados
4. **Database Read Replicas**: Para reporting y analytics

## 9. Monitoreo y Alerting (Nuevo - Sprint 2)

### **🔍 Health Checks:**

```python
# Health check endpoints
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": await check_database(),
            "redis": await check_redis(),
            "scheduled_tasks": scheduled_tasks_service.get_status(),
            "socket_io": socket_manager.get_connection_count()
        }
    }
```

### **🚨 Alertas Configurables:**

1. **Critical**: Scheduler down > 5 minutos
2. **Warning**: Task failure rate > 20%
3. **Info**: High notification volume detected

## 10. Conclusión

La arquitectura de CRM Ventas después del **Sprint 2 - Tracking Avanzado** incluye:

### **✅ Nuevas Capacidades:**
1. **Sistema completo de control CEO** sobre equipo de ventas
2. **Notificaciones inteligentes** en tiempo real con Socket.IO
3. **Background jobs automáticos** con health monitoring
4. **Métricas avanzadas** con Redis caching
5. **Dashboard profesional** con analytics en tiempo real

### **✅ Beneficios Arquitectónicos:**
1. **Escalabilidad**: Redis para caching, WebSockets para real-time
2. **Resiliencia**: Fallback mechanisms, auto-recovery
3. **Monitoreo**: Comprehensive health checks y alerting
4. **Mantenibilidad**: Code modular, documentation completa
5. **Performance**: Optimized queries, background processing

### **✅ Listo para Producción:**
- Docker Compose configurado
- Health checks implementados
- Monitoring endpoints disponibles
- Documentation completa
- Testing automatizado

**La plataforma está 100% implementada y lista para deployment a producción.** 🚀

---

*Última actualización: 27 de Febrero 2026 - Sprint 2 Completado*
*Versión: CRM Ventas v2.0 - Tracking Avanzado*