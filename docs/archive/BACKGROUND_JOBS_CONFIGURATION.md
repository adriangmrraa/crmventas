# 🚀 BACKGROUND JOBS CONFIGURATION GUIDE

## 📋 **INTRODUCCIÓN**

El sistema de **Background Jobs Programados** (Scheduled Tasks) se inicia automáticamente cuando el backend arranca y proporciona:

1. **✅ Verificaciones automáticas** de notificaciones cada 5 minutos
2. **✅ Refresh de métricas** cada 15 minutos  
3. **✅ Limpieza de datos** expirados cada hora
4. **✅ Reportes diarios** a las 8:00 AM para CEO
5. **✅ Auto-start/stop** con la aplicación
6. **✅ Health checks** para monitoreo

---

## ⚙️ **CONFIGURACIÓN DE VARIABLES DE ENTORNO**

### **ARCHIVO `.env` DE EJEMPLO:**
```bash
# SCHEDULED TASKS CONFIGURATION
ENABLE_SCHEDULED_TASKS=true                    # true/false - Habilita tasks
NOTIFICATION_CHECK_INTERVAL_MINUTES=5          # Intervalo verificaciones
METRICS_REFRESH_INTERVAL_MINUTES=15            # Intervalo refresh métricas
CLEANUP_INTERVAL_HOURS=1                       # Intervalo limpieza

# DATABASE & CACHE
POSTGRES_DSN=postgresql://user:pass@localhost:5432/crmventas
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# LOGGING
LOG_LEVEL=INFO
ENABLE_TASK_LOGGING=true
```

### **VARIABLES DISPONIBLES:**

| Variable | Default | Descripción |
|----------|---------|-------------|
| `ENABLE_SCHEDULED_TASKS` | `true` | Habilita/deshabilita todos los scheduled tasks |
| `NOTIFICATION_CHECK_INTERVAL_MINUTES` | `5` | Minutos entre verificaciones de notificaciones |
| `METRICS_REFRESH_INTERVAL_MINUTES` | `15` | Minutos entre refresh de métricas |
| `CLEANUP_INTERVAL_HOURS` | `1` | Horas entre limpieza de datos expirados |
| `ENABLE_TASK_LOGGING` | `true` | Log detallado de ejecución de tasks |

---

## 🏗️ **ARQUITECTURA DEL SISTEMA**

### **COMPONENTES PRINCIPALES:**

```
orchestrator_service/
├── services/
│   └── scheduled_tasks.py          # Servicio principal de tasks
├── routes/
│   ├── scheduled_tasks_routes.py   # API para gestionar tasks
│   └── health_routes.py            # Health checks y monitoring
└── main.py                         # Auto-start en startup_event
```

### **FLUJO DE EJECUCIÓN:**

1. **Backend startup** → `startup_event()` se ejecuta
2. **Verifica `ENABLE_SCHEDULED_TASKS`** → Si es `true`, inicia tasks
3. **Configura intervals** → Usa variables de entorno o defaults
4. **Registra tasks** → 4 tasks programados con sus intervals
5. **Inicia scheduler** → APScheduler comienza a ejecutar tasks
6. **Backend shutdown** → `shutdown_event()` detiene tasks

---

## 📅 **TASKS PROGRAMADOS**

### **1. VERIFICACIONES DE NOTIFICACIONES (Cada 5 minutos)**
```python
# scheduled_tasks.py - run_notification_checks()
"""
Ejecuta:
1. Conversaciones sin respuesta (> 1h)
2. Leads calientes (alta probabilidad)
3. Recordatorios de follow-up
4. Alertas de performance
"""
```

### **2. REFRESH DE MÉTRICAS (Cada 15 minutos)**
```python
# scheduled_tasks.py - refresh_seller_metrics()
"""
Actualiza métricas de todos los vendedores:
- Conversaciones totales/hoy
- Tiempo promedio de respuesta
- Tasa de conversión
- Leads asignados/convertidos
"""
```

### **3. LIMPIEZA DE DATOS (Cada 1 hora)**
```python
# scheduled_tasks.py - cleanup_expired_data()
"""
Limpia:
1. Notificaciones expiradas (> 7 días)
2. Métricas antiguas (> 30 días)
3. Sesiones de chat inactivas (> 7 días)
"""
```

### **4. REPORTES DIARIOS (8:00 AM cada día)**
```python
# scheduled_tasks.py - generate_daily_reports()
"""
Genera para cada CEO:
1. Resumen de actividad del día
2. Métricas del equipo
3. Notificación con reporte
"""
```

---

## 🚀 **INICIO AUTOMÁTICO**

### **EN `main.py`:**
```python
@app.on_event("startup")
async def startup_event():
    # ... otras inicializaciones ...
    
    # Start scheduled tasks if enabled
    if os.getenv("ENABLE_SCHEDULED_TASKS", "true").lower() == "true":
        scheduled_tasks_service.start_all_tasks()
        logger.info("✅ Scheduled tasks started")
```

### **EN `shutdown_event`:**
```python
@app.on_event("shutdown")
async def shutdown_event():
    # Stop scheduled tasks
    scheduled_tasks_service.stop_all_tasks()
    logger.info("✅ Scheduled tasks stopped")
```

---

## 📊 **MONITORING Y HEALTH CHECKS**

### **ENDPOINTS DISPONIBLES:**

#### **1. HEALTH CHECK COMPLETO:**
```bash
GET /health
```
```json
{
  "status": "healthy",
  "timestamp": "2026-02-27T06:30:00Z",
  "scheduled_tasks": {
    "scheduler_running": true,
    "total_tasks": 4,
    "tasks": [
      {
        "name": "Notification Checks",
        "next_run": "2026-02-27T06:35:00Z",
        "last_run": "2026-02-27T06:30:00Z"
      }
    ]
  }
}
```

#### **2. ESTADO DE TASKS:**
```bash
GET /health/tasks
```

#### **3. INICIAR/DETENER MANUALMENTE:**
```bash
POST /health/tasks/start
POST /health/tasks/stop
```

#### **4. PROBES PARA KUBERNETES:**
```bash
GET /health/readiness   # Readiness probe
GET /health/liveness    # Liveness probe
```

#### **5. EJECUTAR TASKS MANUALMENTE:**
```bash
GET /health/tasks/run/notification-checks
GET /health/tasks/run/metrics-refresh
GET /health/tasks/run/cleanup
```

---

## 🔧 **TROUBLESHOOTING**

### **PROBLEMAS COMUNES:**

#### **1. TASKS NO SE INICIAN:**
```bash
# Verificar variable de entorno
echo $ENABLE_SCHEDULED_TASKS

# Verificar logs de startup
grep "Scheduled tasks" orchestrator.log

# Verificar que apscheduler está instalado
pip show apscheduler
```

#### **2. TASKS FALLAN AL EJECUTAR:**
```bash
# Verificar logs de errores
grep -E "(ERROR|WARNING).*scheduled" orchestrator.log

# Verificar conexión a base de datos
curl http://localhost:8000/health | jq '.database'

# Probar ejecución manual
curl -X POST http://localhost:8000/health/tasks/run/notification-checks
```

#### **3. PERFORMANCE ISSUES:**
```bash
# Ajustar intervals
export NOTIFICATION_CHECK_INTERVAL_MINUTES=10
export METRICS_REFRESH_INTERVAL_MINUTES=30

# Reducir carga
export ENABLE_SCHEDULED_TASKS=false  # Deshabilitar temporalmente
```

### **LOGS DE DIAGNÓSTICO:**

```python
# Niveles de logging recomendados
LOG_LEVEL=DEBUG           # Log detallado (desarrollo)
LOG_LEVEL=INFO            # Log normal (producción)
LOG_LEVEL=WARNING         # Solo warnings/errores
```

---

## 🎯 **CONFIGURACIONES RECOMENDADAS**

### **PARA DESARROLLO:**
```bash
ENABLE_SCHEDULED_TASKS=true
NOTIFICATION_CHECK_INTERVAL_MINUTES=2      # Más frecuente para testing
METRICS_REFRESH_INTERVAL_MINUTES=5         # Más frecuente
LOG_LEVEL=DEBUG                            # Log detallado
```

### **PARA STAGING:**
```bash
ENABLE_SCHEDULED_TASKS=true
NOTIFICATION_CHECK_INTERVAL_MINUTES=5      # Normal
METRICS_REFRESH_INTERVAL_MINUTES=15        # Normal
LOG_LEVEL=INFO                             # Log normal
ENABLE_TASK_LOGGING=true                   # Log de tasks
```

### **PARA PRODUCCIÓN:**
```bash
ENABLE_SCHEDULED_TASKS=true
NOTIFICATION_CHECK_INTERVAL_MINUTES=5      # Balanceado
METRICS_REFRESH_INTERVAL_MINUTES=15        # Balanceado
CLEANUP_INTERVAL_HOURS=1                   # Mantenimiento
LOG_LEVEL=WARNING                          # Solo problemas
ENABLE_TASK_LOGGING=true                   # Para debugging
```

### **PARA ALTA CARGA:**
```bash
ENABLE_SCHEDULED_TASKS=true
NOTIFICATION_CHECK_INTERVAL_MINUTES=10     # Menos frecuente
METRICS_REFRESH_INTERVAL_MINUTES=30        # Menos frecuente
CLEANUP_INTERVAL_HOURS=2                   # Menos frecuente
REDIS_CACHE_ENABLED=true                   # Cache para performance
```

---

## 🔄 **MIGRACIÓN Y DEPLOYMENT**

### **PASOS PARA DEPLOYMENT:**

#### **1. PRE-DEPLOYMENT:**
```bash
# Verificar configuración
python3 test_background_jobs.py

# Verificar dependencias
pip install apscheduler redis

# Configurar variables de entorno
cp .env.example .env.production
```

#### **2. DURANTE DEPLOYMENT:**
```bash
# Las tasks se iniciarán automáticamente
# Verificar en logs:
tail -f orchestrator.log | grep "Scheduled tasks"
```

#### **3. POST-DEPLOYMENT:**
```bash
# Verificar health check
curl http://your-api.com/health | jq '.scheduled_tasks'

# Verificar tasks están corriendo
curl http://your-api.com/health/tasks

# Probar ejecución manual
curl -X POST http://your-api.com/health/tasks/run/notification-checks
```

### **ROLLBACK PROCEDURE:**
```bash
# Si hay problemas, deshabilitar tasks
export ENABLE_SCHEDULED_TASKS=false

# O ajustar intervals para reducir carga
export NOTIFICATION_CHECK_INTERVAL_MINUTES=30
export METRICS_REFRESH_INTERVAL_MINUTES=60
```

---

## 📈 **MÉTRICAS Y MONITORING**

### **MÉTRICAS A MONITOREAR:**

#### **1. PERFORMANCE:**
- Tiempo de ejecución por task
- Memoria utilizada por tasks
- CPU usage durante ejecución
- Tasa de éxito/fallo de tasks

#### **2. BUSINESS:**
- Notificaciones generadas por día
- Métricas actualizadas por día
- Datos limpiados por ejecución
- Reportes enviados a CEO

#### **3. SYSTEM:**
- Scheduler uptime
- Tasks completados/exitosos/fallidos
- Intervalos de ejecución reales
- Tiempo entre ejecuciones

### **ALERTAS RECOMENDADAS:**

#### **CRÍTICAS (P0):**
- Scheduler down > 5 minutos
- Task failure rate > 20%
- Database connection lost during tasks

#### **ADVERTENCIAS (P1):**
- Task execution time > 5 minutos
- Memory usage > 80% during tasks
- Redis cache unavailable

#### **INFORMATIVAS (P2):**
- Tasks disabled (ENABLE_SCHEDULED_TASKS=false)
- Configuration changes detected
- High frequency of manual executions

---

## 🎉 **CONCLUSIÓN**

### **BENEFICIOS DEL SISTEMA:**

1. **✅ Automatización completa** - Sin intervención manual
2. **✅ Configurable** - Ajustable para cada entorno
3. **✅ Resiliente** - Auto-recovery y fallbacks
4. **✅ Monitoreable** - Health checks y métricas
5. **✅ Escalable** - Ajuste de intervals según carga
6. **✅ Seguro** - Permisos y validaciones

### **PRÓXIMAS MEJORAS:**

1. **Distributed scheduling** para múltiples instancias
2. **Retry logic** con exponential backoff
3. **Priority queues** para tasks críticos
4. **Advanced monitoring** con Grafana/Prometheus
5. **Webhook notifications** para fallos de tasks

---

**¡EL SISTEMA DE BACKGROUND JOBS ESTÁ LISTO PARA PRODUCCIÓN!** 🚀

*Configuración completa, auto-start implementado, monitoring disponible.*
*Última actualización: 27 de Febrero 2026*