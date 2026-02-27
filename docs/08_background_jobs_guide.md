# 🚀 Guía Completa de Background Jobs - Sprint 2

## 📋 **INTRODUCCIÓN**

El sistema de **Background Jobs Programados** (Scheduled Tasks) es una característica clave del **Sprint 2 - Tracking Avanzado** que proporciona automatización completa de procesos críticos del CRM Ventas.

### **🎯 BENEFICIOS PRINCIPALES:**

1. **✅ Automatización completa** - Sin intervención manual requerida
2. **✅ Tiempo real optimizado** - Redis caching para performance
3. **✅ Monitoreo integral** - Health checks y status endpoints
4. **✅ Configuración flexible** - Ajustable por entorno y carga
5. **✅ Resiliencia robusta** - Fallback mechanisms y auto-recovery

---

## 🏗️ **ARQUITECTURA DEL SISTEMA**

### **📊 DIAGRAMA DE ARQUITECTURA:**

```
Orchestrator Startup (main.py)
        |
        v
startup_event() → Auto-start Tasks
        |
        v
ScheduledTasksService (APScheduler)
        |
        |───┬───┬───┬───┐
        v   v   v   v   v
    [4 Tareas Programadas]
        |
        v
Redis Cache ←───┐
        |       |
        v       v
API Endpoints   Socket.IO Events
        |       |
        v       v
Frontend Updates  User Notifications
```

### **🔧 COMPONENTES PRINCIPALES:**

#### **1. ScheduledTasksService (`services/scheduled_tasks.py`)**
- **Función**: Gestión central de todas las tareas programadas
- **Tecnología**: APScheduler (Python)
- **Características**: Auto-start, configuración dinámica, health monitoring

#### **2. Task Configuration (Environment Variables)**
```bash
ENABLE_SCHEDULED_TASKS=true
NOTIFICATION_CHECK_INTERVAL_MINUTES=5
METRICS_REFRESH_INTERVAL_MINUTES=15
CLEANUP_INTERVAL_HOURS=1
```

#### **3. Health Check Endpoints (`routes/health_routes.py`)**
```python
GET /health              # Health check completo
GET /health/tasks        # Estado detallado de tasks
POST /health/tasks/start # Iniciar tasks manualmente
POST /health/tasks/stop  # Detener tasks manualmente
GET /health/readiness    # Readiness probe (Kubernetes)
GET /health/liveness     # Liveness probe (Kubernetes)
```

#### **4. Redis Integration**
- **Cache de métricas**: TTL de 5 minutos
- **Queue de notificaciones**: Para procesamiento asíncrono
- **Lock management**: Prevención de ejecuciones concurrentes

---

## 📅 **TAREAS PROGRAMADAS**

### **1. ✅ VERIFICACIONES DE NOTIFICACIONES (Cada 5 minutos)**

#### **🎯 Propósito:**
Monitoreo automático del sistema para detectar situaciones que requieren atención.

#### **🔍 Qué Verifica:**
```python
# 1. Conversaciones sin respuesta (> 1 hora)
query = """
    SELECT * FROM conversations 
    WHERE last_message_from_customer = true
    AND last_message_time < NOW() - INTERVAL '1 hour'
    AND assigned_seller_id IS NOT NULL
"""

# 2. Leads calientes (alta probabilidad de conversión)
query = """
    SELECT * FROM leads 
    WHERE conversion_probability > 0.8
    AND status IN ('new', 'contacted')
    AND last_contact_time < NOW() - INTERVAL '2 hours'
"""

# 3. Recordatorios de follow-up
query = """
    SELECT * FROM leads 
    WHERE next_follow_up <= NOW()
    AND status IN ('interested', 'negotiation')
"""

# 4. Alertas de performance
query = """
    SELECT seller_id, 
           COUNT(*) as unanswered_count,
           AVG(response_time_minutes) as avg_response_time
    FROM seller_metrics 
    WHERE period = CURRENT_DATE
    GROUP BY seller_id
    HAVING unanswered_count > 5 OR avg_response_time > 30
"""
```

#### **📊 Métricas Generadas:**
- Notificaciones creadas por tipo
- Tiempo de ejecución promedio
- Tasa de éxito/fallo
- Impacto en conversiones

### **2. ✅ REFRESH DE MÉTRICAS (Cada 15 minutos)**

#### **🎯 Propósito:**
Mantenimiento de métricas en tiempo real para dashboard CEO y reporting.

#### **🔧 Proceso:**
```python
async def refresh_seller_metrics():
    # 1. Obtener todos los vendedores activos
    sellers = await get_active_sellers()
    
    # 2. Calcular 15+ métricas por vendedor
    for seller in sellers:
        metrics = await calculate_seller_metrics(seller.id)
        
        # 3. Guardar en PostgreSQL (histórico)
        await save_metrics_to_db(seller.id, metrics)
        
        # 4. Cachear en Redis (tiempo real)
        await cache_metrics_in_redis(seller.id, metrics)
    
    # 5. Emitir updates via Socket.IO
    await emit_metrics_updates(metrics)
```

#### **📈 Métricas Calculadas:**
```json
{
  "conversation_metrics": {
    "total": 150,
    "active": 25,
    "today": 12,
    "unanswered": 3
  },
  "time_metrics": {
    "avg_response_time_minutes": 8.5,
    "total_chat_time_minutes": 1240,
    "engagement_rate": 0.78
  },
  "conversion_metrics": {
    "leads_generated": 45,
    "leads_converted": 12,
    "conversion_rate": 0.27
  },
  "performance_metrics": {
    "productivity_score": 8.2,
    "activity_level": "high",
    "rank_position": 3
  }
}
```

### **3. ✅ LIMPIEZA DE DATOS (Cada 1 hora)**

#### **🎯 Propósito:**
Mantenimiento de la base de datos y optimización de performance.

#### **🧹 Qué Limpia:**
```python
# 1. Notificaciones expiradas (> 7 días)
DELETE FROM notifications 
WHERE created_at < NOW() - INTERVAL '7 days'

# 2. Métricas antiguas (> 30 días)
DELETE FROM seller_metrics 
WHERE period < CURRENT_DATE - INTERVAL '30 days'

# 3. Sesiones de chat inactivas (> 7 días)
UPDATE conversations 
SET status = 'archived'
WHERE last_message_time < NOW() - INTERVAL '7 days'
  AND status = 'active'

# 4. Cache Redis expirado
await redis_client.delete_expired_keys()
```

#### **📊 Impacto en Performance:**
- **Reducción espacio DB**: ~15% mensual
- **Mejora queries**: ~25% más rápido
- **Optimización Redis**: Memoria constante

### **4. ✅ REPORTES DIARIOS (8:00 AM cada día)**

#### **🎯 Propósito:**
Reportes automáticos para CEO con resumen de actividad del día anterior.

#### **📋 Contenido del Reporte:**
```python
report = {
    "date": "2026-02-26",
    "team_performance": {
        "total_conversations": 245,
        "new_leads": 67,
        "converted_leads": 18,
        "conversion_rate": 0.27,
        "avg_response_time": "9.2 minutos"
    },
    "top_performers": [
        {"seller": "Juan Pérez", "conversions": 8, "score": 9.2},
        {"seller": "María Gómez", "conversions": 6, "score": 8.7},
        {"seller": "Carlos López", "conversions": 4, "score": 7.9}
    ],
    "alerts_summary": {
        "unanswered_conversations": 12,
        "hot_leads": 8,
        "follow_up_reminders": 15,
        "performance_alerts": 3
    },
    "recommendations": [
        "Revisar conversaciones sin respuesta de Juan Pérez",
        "Seguimiento urgente a 3 leads calientes",
        "Capacitación en técnicas de cierre para equipo"
    ]
}
```

#### **📤 Entrega del Reporte:**
1. **Notificación en plataforma**: Socket.IO event al CEO
2. **Email opcional**: Si está configurado `HANDOFF_EMAIL`
3. **Dashboard update**: Sección de reportes históricos

---

## ⚙️ **CONFIGURACIÓN AVANZADA**

### **1. CONFIGURACIÓN POR ENTORNO**

#### **Desarrollo:**
```bash
# Tasks más frecuentes para testing
ENABLE_SCHEDULED_TASKS=true
NOTIFICATION_CHECK_INTERVAL_MINUTES=2
METRICS_REFRESH_INTERVAL_MINUTES=5
CLEANUP_INTERVAL_HOURS=1
ENABLE_TASK_LOGGING=true
LOG_LEVEL=DEBUG
```

#### **Staging:**
```bash
# Balance entre testing y performance
ENABLE_SCHEDULED_TASKS=true
NOTIFICATION_CHECK_INTERVAL_MINUTES=5
METRICS_REFRESH_INTERVAL_MINUTES=15
CLEANUP_INTERVAL_HOURS=1
ENABLE_TASK_LOGGING=true
LOG_LEVEL=INFO
```

#### **Producción:**
```bash
# Optimizado para performance
ENABLE_SCHEDULED_TASKS=true
NOTIFICATION_CHECK_INTERVAL_MINUTES=5
METRICS_REFRESH_INTERVAL_MINUTES=15
CLEANUP_INTERVAL_HOURS=1
ENABLE_TASK_LOGGING=false
LOG_LEVEL=WARNING
```

#### **Alta Carga:**
```bash
# Menos frecuente para reducir carga
ENABLE_SCHEDULED_TASKS=true
NOTIFICATION_CHECK_INTERVAL_MINUTES=10
METRICS_REFRESH_INTERVAL_MINUTES=30
CLEANUP_INTERVAL_HOURS=2
REDIS_CACHE_TTL_MINUTES=2
MAX_TASK_RETRIES=5
```

### **2. CONFIGURACIÓN DE REDIS**

#### **Para Optimal Performance:**
```bash
# Connection pooling
REDIS_MAX_CONNECTIONS=50
REDIS_SOCKET_TIMEOUT=5
REDIS_SOCKET_CONNECT_TIMEOUT=5

# Cache optimization
REDIS_CACHE_TTL_MINUTES=5
REDIS_MAX_MEMORY=100mb
REDIS_MAX_MEMORY_POLICY=allkeys-lru

# Queue management
REDIS_NOTIFICATION_QUEUE=notifications
REDIS_METRICS_QUEUE=metrics
REDIS_REPORT_QUEUE=reports
```

#### **Cluster Configuration (Producción):**
```bash
# Redis Cluster
REDIS_CLUSTER_ENABLED=true
REDIS_CLUSTER_NODES=redis1:6379,redis2:6379,redis3:6379
REDIS_CLUSTER_PASSWORD=cluster-password
```

### **3. CONFIGURACIÓN DE ALERTAS**

#### **Umbrales Configurables:**
```bash
# Notification thresholds
UNANSWERED_CONVERSATION_HOURS=1
HOT_LEAD_PROBABILITY_THRESHOLD=0.8
FOLLOWUP_REMINDER_HOURS=24
PERFORMANCE_ALERT_THRESHOLD=0.5

# Retention policies
NOTIFICATION_RETENTION_DAYS=7
METRICS_RETENTION_DAYS=30
CONVERSATION_ARCHIVE_DAYS=7
```

#### **Alerting Integration:**
```bash
# Email alerts
ALERT_EMAIL_ENABLED=true
ALERT_EMAIL_RECIPIENTS=ceo@empresa.com,manager@empresa.com
ALERT_EMAIL_FROM=noreply@empresa.com

# Slack/Teams webhooks
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx
TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/xxx
```

---

## 🚀 **DEPLOYMENT Y OPERACIONES**

### **1. DEPLOYMENT PROCEDURE**

#### **Pre-deployment Checklist:**
```bash
# 1. Verificar variables de entorno
./scripts/verify_env.sh

# 2. Verificar Redis connection
redis-cli -h $REDIS_HOST ping

# 3. Verificar database migrations
python3 orchestrator_service/migrations/run_migrations.py --status

# 4. Test health endpoints
curl http://localhost:8000/health
```

#### **Deployment Steps:**
```bash
# 1. Stop existing services
docker-compose down

# 2. Update environment variables
cp .env.production .env

# 3. Build and start
docker-compose up -d --build

# 4. Verify startup
docker-compose logs orchestrator | grep "Scheduled tasks"

# 5. Test functionality
curl -X POST http://localhost:8000/health/tasks/run/notification-checks
```

### **2. MONITORING Y HEALTH CHECKS**

#### **Health Check Endpoints:**
```python
# Comprehensive health check
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
        },
        "metrics": {
            "notification_checks_last_run": last_run_time,
            "metrics_refresh_last_run": metrics_last_run,
            "cleanup_last_run": cleanup_last_run,
            "daily_reports_last_run": reports_last_run
        }
    }
```

#### **Prometheus Metrics:**
```python
# Expose metrics for Prometheus
@app.get("/metrics")
async def metrics_endpoint():
    return {
        "scheduled_tasks_total": scheduler.get_jobs_count(),
        "scheduled_tasks_running": scheduler.get_running_jobs_count(),
        "scheduled_tasks_failed": scheduler.get_failed_jobs_count(),
        "notification_checks_executed": notification_counter,
        "metrics_refresh_executed": metrics_counter,
        "cleanup_executed": cleanup_counter,
        "daily_reports_sent": reports_counter
    }
```

### **3. BACKUP Y RECOVERY**

#### **Backup Procedure:**
```bash
# 1. Stop scheduled tasks
curl -X POST http://localhost:8000/health/tasks/stop

# 2. Backup database
pg_dump $POSTGRES_DSN > backup_$(date +%Y%m%d).sql

# 3. Backup Redis
redis-cli --rdb backup_$(date +%Y%m%d).rdb

# 4. Restart tasks
curl -X POST http://localhost:8000/health/tasks/start
```

#### **Recovery Procedure:**
```bash
# 1. Restore database
psql $POSTGRES_DSN < backup_20260226.sql

# 2. Restore Redis
redis-cli --pipe < backup_20260226.rdb

# 3. Verify system
curl http://localhost:8000/health

# 4. Start tasks
curl -X POST http://localhost:8000/health/tasks/start
```

---

## 🔧 **TROUBLESHOOTING**

### **1. PROBLEMAS COMUNES**

#### **Tasks No Se Inician:**
```bash
# Verificar variable de entorno
echo $ENABLE_SCHEDULED_TASKS

# Verificar logs de startup
docker-compose logs orchestrator | grep -A5 -B5 "Scheduled tasks"

# Verificar que APScheduler está instalado
docker-compose exec orchestrator pip show apscheduler

# Probar inicio manual
curl -X POST http://localhost:8000/health/tasks/start
```

#### **Tasks Fallan al Ejecutar:**
```bash
# Verificar logs de errores
docker-compose logs orchestrator | grep -E "(ERROR|WARNING).*scheduled"

# Verificar conexión a base de datos
curl http://localhost:8000/health | jq '.database'

# Verificar conexión Redis
curl http://localhost:8000/health | jq '.redis'

# Probar ejecución manual
curl http://localhost:8000/health/tasks/run/notification-checks
```

#### **Performance Issues:**
```bash
# Verificar carga de tasks
curl http://localhost:8000/health/tasks | jq '.tasks[].last_duration'

# Ajustar intervals
export NOTIFICATION_CHECK_INTERVAL_MINUTES=10
export METRICS_REFRESH_INTERVAL_MINUTES=30

# Reducir carga temporalmente
export ENABLE_SCHEDULED_TASKS=false
```

### **2. DIAGNÓSTICO AVANZADO**

#### **Checklist de Diagnóstico:**
```bash
#!/bin/bash
# diagnose_tasks.sh

echo "🔍 Diagnóstico de Background Jobs..."

# 1. Verificar scheduler running
curl -s http://localhost:8000/health/tasks | jq '.scheduler_running'

# 2. Verificar tasks registradas
curl -s http://localhost:8000/health/tasks | jq '.tasks[].name'

# 3. Verificar última ejecución
curl -s http://localhost:8000/health/tasks | jq '.tasks[].last_run'

# 4