# Variables de Entorno - Guía Completa (Actualizado Sprint 2)

Este proyecto se configura completamente mediante variables de entorno. En despliegue de EasyPanel, carga estas variables para cada microservicio.

## 📋 **ÍNDICE**

1. [Variables Globales](#1-variables-globales-todos-los-servicios)
2. [Orchestrator Service](#2-orchestrator-service-8000)
3. [WhatsApp Service](#3-whatsapp-service-8002)
4. [Frontend React](#4-frontend-react-5173)
5. [Sprint 2 - Nuevas Variables](#5-sprint-2---tracking-avanzado-nuevas-variables)
6. [Configuración de Producción](#6-configuración-de-producción)
7. [Ejemplo .env Completo](#7-ejemplo-env-completo)

---

## 1. Variables Globales (Todos los Servicios)

| Variable | Descripción | Ejemplo | Requerida |
| :--- | :--- | :--- | :--- |
| `INTERNAL_API_TOKEN` | Token de seguridad entre microservicios | `compu-global-hyper-mega-net` | ✅ |
| `OPENAI_API_KEY` | Clave API de OpenAI (GPT-4o-mini + Whisper) | `sk-proj-xxxxx` | ✅ |
| `REDIS_URL` | URL de conexión a Redis | `redis://redis:6379` | ✅ |
| `POSTGRES_DSN` | URL de conexión a PostgreSQL | `postgres://user:pass@db:5432/database` | ✅ |
| `NODE_ENV` | Entorno de ejecución | `production`, `development`, `staging` | ✅ |

## 2. Orchestrator Service (8000)

### 2.1 Identidad y Branding (Whitelabel)

| Variable | Descripción | Ejemplo | Requerida |
| :--- | :--- | :--- | :--- |
| `STORE_NAME` | Nombre del negocio (legacy/fallback) | `CRM Ventas` | ❌ |
| `BOT_PHONE_NUMBER` | Número de WhatsApp del bot (fallback) | `+5493756123456` | ❌ |
| `COMPANY_NAME` | Nombre de la empresa usado como fallback | `Empresa de Ventas` | ❌ |
| `STORE_LOCATION` | Ciudad/País | `Buenos Aires, Argentina` | ❌ |
| `STORE_WEBSITE` | URL del negocio | `https://www.empresa.com` | ❌ |

### 2.2 Seguridad y RBAC (Nexus v7.6)

| Variable | Descripción | Ejemplo | Requerida |
| :--- | :--- | :--- | :--- |
| `JWT_SECRET_KEY` | Clave para firmar tokens JWT | `supersecretkey123` | ✅ |
| `ADMIN_TOKEN` | Token para rutas `/admin/*` (X-Admin-Token) | `admin-super-secret-token` | ✅ |
| `CREDENTIALS_FERNET_KEY` | Clave para cifrar credenciales de Google Calendar | (32 bytes base64) | ❌ |
| `CORS_ORIGINS` | Orígenes permitidos para CORS | `http://localhost:5173,https://app.empresa.com` | ✅ |

### 2.3 Google Calendar (Opcional)

| Variable | Descripción | Ejemplo | Requerida |
| :--- | :--- | :--- | :--- |
| `GOOGLE_CREDENTIALS` | Credenciales de servicio JSON (base64) | `eyJ0eXBlI...` | ❌ |
| `GOOGLE_CALENDAR_ID` | ID del calendario principal | `primary` | ❌ |

### 2.4 Logging y Monitoreo

| Variable | Descripción | Ejemplo | Requerida |
| :--- | :--- | :--- | :--- |
| `LOG_LEVEL` | Nivel de logging | `INFO`, `DEBUG`, `WARNING` | ❌ |
| `SENTRY_DSN` | DSN de Sentry para error tracking | `https://xxx@sentry.io/xxx` | ❌ |
| `METRICS_PORT` | Puerto para métricas Prometheus | `9090` | ❌ |

## 3. WhatsApp Service (8002)
  
### 3.1 YCloud Integration

| Variable | Descripción | Ejemplo | Requerida |
| :--- | :--- | :--- | :--- |
| `YCLOUD_API_KEY` | API Key de YCloud | `ycloud_xxxxx` | ✅ |
| `YCLOUD_WEBHOOK_SECRET` | Secreto para validar webhooks | `webhook_secret_123` | ✅ |
| `YCLOUD_BOT_PHONE_NUMBER` | Número de teléfono del bot en YCloud | `+5493756123456` | ✅ |

### 3.2 Transcripción de Audio

| Variable | Descripción | Ejemplo | Requerida |
| :--- | :--- | :--- | :--- |
| `WHISPER_MODEL` | Modelo de Whisper a usar | `whisper-1` | ❌ |
| `MAX_AUDIO_SIZE_MB` | Tamaño máximo de audio a transcribir | `25` | ❌ |

## 4. Frontend React (5173)

### 4.1 Configuración de API

| Variable | Descripción | Ejemplo | Requerida |
| :--- | :--- | :--- | :--- |
| `VITE_API_URL` | URL base del Orchestrator | `http://localhost:8000` | ✅ |
| `VITE_WS_URL` | URL WebSocket para Socket.IO | `ws://localhost:8000` | ✅ |
| `VITE_ADMIN_TOKEN` | Token para rutas admin (X-Admin-Token) | `admin-super-secret-token` | ✅ |

### 4.2 Internacionalización

| Variable | Descripción | Ejemplo | Requerida |
| :--- | :--- | :--- | :--- |
| `VITE_DEFAULT_LANGUAGE` | Idioma por defecto | `es`, `en`, `fr` | ❌ |
| `VITE_SUPPORTED_LANGUAGES` | Idiomas soportados | `es,en,fr` | ❌ |

## 5. Sprint 2 - Tracking Avanzado (Nuevas Variables)

### 5.1 Background Jobs Configuration

| Variable | Descripción | Default | Requerida |
| :--- | :--- | :--- | :--- |
| `ENABLE_SCHEDULED_TASKS` | Habilita/deshabilita background jobs | `true` | ❌ |
| `NOTIFICATION_CHECK_INTERVAL_MINUTES` | Intervalo verificaciones notificaciones | `5` | ❌ |
| `METRICS_REFRESH_INTERVAL_MINUTES` | Intervalo refresh métricas | `15` | ❌ |
| `CLEANUP_INTERVAL_HOURS` | Intervalo limpieza datos | `1` | ❌ |
| `ENABLE_TASK_LOGGING` | Log detallado de ejecución tasks | `true` | ❌ |
| `MAX_TASK_RETRIES` | Intentos máximos por task fallido | `3` | ❌ |

### 5.2 Redis Configuration (Optimizado)

| Variable | Descripción | Default | Requerida |
| :--- | :--- | :--- | :--- |
| `REDIS_HOST` | Host de Redis | `localhost` | ✅ |
| `REDIS_PORT` | Puerto de Redis | `6379` | ✅ |
| `REDIS_PASSWORD` | Password de Redis (si aplica) | ` ` | ❌ |
| `REDIS_DB` | Database de Redis a usar | `0` | ❌ |
| `REDIS_CACHE_TTL_MINUTES` | TTL para cache de métricas | `5` | ❌ |
| `REDIS_NOTIFICATION_QUEUE` | Nombre de queue para notificaciones | `notifications` | ❌ |

### 5.3 Socket.IO Configuration

| Variable | Descripción | Default | Requerida |
| :--- | :--- | :--- | :--- |
| `SOCKETIO_CORS_ORIGINS` | Orígenes permitidos Socket.IO | `*` | ❌ |
| `SOCKETIO_PING_TIMEOUT` | Timeout ping WebSocket (ms) | `20000` | ❌ |
| `SOCKETIO_PING_INTERVAL` | Intervalo ping WebSocket (ms) | `25000` | ❌ |
| `SOCKETIO_MAX_HTTP_BUFFER_SIZE` | Tamaño máximo buffer (MB) | `1e6` | ❌ |

### 5.4 Notification System

| Variable | Descripción | Default | Requerida |
| :--- | :--- | :--- | :--- |
| `NOTIFICATION_RETENTION_DAYS` | Días retención notificaciones | `7` | ❌ |
| `UNANSWERED_CONVERSATION_HOURS` | Horas para considerar sin respuesta | `1` | ❌ |
| `HOT_LEAD_PROBABILITY_THRESHOLD` | Umbral probabilidad lead caliente | `0.8` | ❌ |
| `FOLLOWUP_REMINDER_HOURS` | Horas para recordatorio follow-up | `24` | ❌ |
| `PERFORMANCE_ALERT_THRESHOLD` | Umbral alertas performance | `0.5` | ❌ |

### 5.5 Metrics System

| Variable | Descripción | Default | Requerida |
| :--- | :--- | :--- | :--- |
| `METRICS_RETENTION_DAYS` | Días retención métricas | `30` | ❌ |
| `REAL_TIME_METRICS_ENABLED` | Habilita métricas tiempo real | `true` | ❌ |
| `LEADERBOARD_UPDATE_INTERVAL` | Intervalo update leaderboard (min) | `5` | ❌ |
| `CEO_REPORT_TIME` | Hora reporte diario CEO | `08:00` | ❌ |

## 6. Configuración de Producción

### 6.1 Entorno de Producción Mínimo

```bash
# PostgreSQL
POSTGRES_DSN=postgresql://user:strongpassword@postgres-host:5432/crmventas

# Redis
REDIS_HOST=redis-host
REDIS_PORT=6379
REDIS_PASSWORD=redis-password

# OpenAI
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxx

# Security
JWT_SECRET_KEY=supersecretkeychangemeinproduction
ADMIN_TOKEN=admin-super-secret-token-changeme
INTERNAL_API_TOKEN=internal-token-changeme

# YCloud
YCLOUD_API_KEY=ycloud_xxxxxxxxxxxxxxxx
YCLOUD_WEBHOOK_SECRET=webhook-secret-changeme
YCLOUD_BOT_PHONE_NUMBER=+5491111111111

# Sprint 2 - Background Jobs
ENABLE_SCHEDULED_TASKS=true
NOTIFICATION_CHECK_INTERVAL_MINUTES=5
METRICS_REFRESH_INTERVAL_MINUTES=15
CLEANUP_INTERVAL_HOURS=1

# Frontend
VITE_API_URL=https://api.empresa.com
VITE_WS_URL=wss://api.empresa.com
VITE_ADMIN_TOKEN=admin-super-secret-token-changeme
```

### 6.2 Configuración por Entorno

#### **Desarrollo:**
```bash
NODE_ENV=development
LOG_LEVEL=DEBUG
ENABLE_SCHEDULED_TASKS=true
NOTIFICATION_CHECK_INTERVAL_MINUTES=2  # Más frecuente para testing
```

#### **Staging:**
```bash
NODE_ENV=staging
LOG_LEVEL=INFO
ENABLE_SCHEDULED_TASKS=true
ENABLE_TASK_LOGGING=true
```

#### **Producción:**
```bash
NODE_ENV=production
LOG_LEVEL=WARNING
ENABLE_SCHEDULED_TASKS=true
ENABLE_TASK_LOGGING=false  # Menos logs en producción
SENTRY_DSN=https://xxx@sentry.io/xxx  # Error tracking
```

### 6.3 Configuración de Alta Carga

```bash
# Optimización Redis
REDIS_CACHE_TTL_MINUTES=2  # Cache más fresco
REDIS_MAX_CONNECTIONS=50

# Background Jobs optimizados
NOTIFICATION_CHECK_INTERVAL_MINUTES=10  # Menos frecuente
METRICS_REFRESH_INTERVAL_MINUTES=30     # Menos frecuente
CLEANUP_INTERVAL_HOURS=2                # Menos frecuente

# Socket.IO optimizado
SOCKETIO_PING_TIMEOUT=30000
SOCKETIO_PING_INTERVAL=30000
SOCKETIO_MAX_HTTP_BUFFER_SIZE=5e6
```

## 7. Ejemplo .env Completo

```bash
# ============================================
# CRM VENTAS - CONFIGURACIÓN COMPLETA
# Sprint 2 - Tracking Avanzado Implementado
# ============================================

# ENVIRONMENT
NODE_ENV=production

# DATABASE
POSTGRES_DSN=postgresql://crmuser:StrongPass123@postgres-host:5432/crmventas

# REDIS
REDIS_HOST=redis-host
REDIS_PORT=6379
REDIS_PASSWORD=RedisPass123
REDIS_CACHE_TTL_MINUTES=5
REDIS_NOTIFICATION_QUEUE=notifications

# OPENAI
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# SECURITY
JWT_SECRET_KEY=jwt-super-secret-key-change-in-production
ADMIN_TOKEN=admin-token-change-in-production
INTERNAL_API_TOKEN=internal-api-token-change
CREDENTIALS_FERNET_KEY=fernet-key-base64-32-bytes==
CORS_ORIGINS=https://app.empresa.com,https://admin.empresa.com

# YCLOUD
YCLOUD_API_KEY=ycloud_xxxxxxxxxxxxxxxxxxxxxxxx
YCLOUD_WEBHOOK_SECRET=webhook-secret-change-in-production
YCLOUD_BOT_PHONE_NUMBER=+5491111111111

# SPRINT 2 - BACKGROUND JOBS
ENABLE_SCHEDULED_TASKS=true
NOTIFICATION_CHECK_INTERVAL_MINUTES=5
METRICS_REFRESH_INTERVAL_MINUTES=15
CLEANUP_INTERVAL_HOURS=1
ENABLE_TASK_LOGGING=true
MAX_TASK_RETRIES=3

# SPRINT 2 - NOTIFICATION SYSTEM
NOTIFICATION_RETENTION_DAYS=7
UNANSWERED_CONVERSATION_HOURS=1
HOT_LEAD_PROBABILITY_THRESHOLD=0.8
FOLLOWUP_REMINDER_HOURS=24
PERFORMANCE_ALERT_THRESHOLD=0.5

# SPRINT 2 - METRICS SYSTEM
METRICS_RETENTION_DAYS=30
REAL_TIME_METRICS_ENABLED=true
LEADERBOARD_UPDATE_INTERVAL=5
CEO_REPORT_TIME=08:00

# SOCKET.IO
SOCKETIO_CORS_ORIGINS=*
SOCKETIO_PING_TIMEOUT=20000
SOCKETIO_PING_INTERVAL=25000
SOCKETIO_MAX_HTTP_BUFFER_SIZE=1e6

# FRONTEND
VITE_API_URL=https://api.empresa.com
VITE_WS_URL=wss://api.empresa.com
VITE_ADMIN_TOKEN=admin-token-change-in-production
VITE_DEFAULT_LANGUAGE=es
VITE_SUPPORTED_LANGUAGES=es,en,fr

# LOGGING & MONITORING
LOG_LEVEL=INFO
SENTRY_DSN=https://xxx@sentry.io/xxx
METRICS_PORT=9090

# GOOGLE CALENDAR (Opcional)
GOOGLE_CREDENTIALS=eyJ0eXBlIjoic2VydmljZV9hY2NvdW50IiwiY2xpZW50X2lkIjoi...
GOOGLE_CALENDAR_ID=primary

# BRANDING
COMPANY_NAME=Empresa de Ventas
STORE_LOCATION=Buenos Aires, Argentina
STORE_WEBSITE=https://www.empresa.com
```

## 8. Verificación de Configuración

### 8.1 Script de Verificación

```bash
#!/bin/bash
# verify_env.sh

echo "🔍 Verificando variables de entorno..."

# Variables requeridas
required_vars=(
  "POSTGRES_DSN"
  "REDIS_HOST"
  "OPENAI_API_KEY"
  "JWT_SECRET_KEY"
  "ADMIN_TOKEN"
  "YCLOUD_API_KEY"
)

for var in "${required_vars[@]}"; do
  if [ -z "${!var}" ]; then
    echo "❌ Variable requerida faltante: $var"
    exit 1
  else
    echo "✅ $var: Configurada"
  fi
done

# Variables Sprint 2
sprint2_vars=(
  "ENABLE_SCHEDULED_TASKS"
  "NOTIFICATION_CHECK_INTERVAL_MINUTES"
  "METRICS_REFRESH_INTERVAL_MINUTES"
)

for var in "${sprint2_vars[@]}"; do
  if [ -z "${!var}" ]; then
    echo "⚠️  Variable Sprint 2 faltante: $var (usando default)"
  else
    echo "✅ $var: ${!var}"
  fi
done

echo "🎯 Configuración verificada exitosamente!"
```

### 8.2 Health Check Endpoints

Después de configurar las variables, puedes verificar el sistema con:

```bash
# Health check completo
curl https://api.empresa.com/health

# Estado de background jobs
curl https://api.empresa.com/health/tasks

# Readiness probe (Kubernetes)
curl https://api.empresa.com/health/readiness

# Liveness probe (Kubernetes)
curl https://api.empresa.com/health/liveness
```

## 9. Troubleshooting

### 9.1 Problemas Comunes

#### **Background Jobs No Inician:**
```bash
# Verificar variable
echo $ENABLE_SCHEDULED_TASKS

# Verificar logs
docker logs orchestrator | grep "Scheduled tasks"

# Probar manualmente
curl -X POST https://api.empresa.com/health/tasks/start
```

#### **Redis Connection Issues:**
```bash
# Verificar conexión
redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD ping

# Verificar en health check
curl https://api.empresa.com/health | jq '.redis'
```

#### **Socket.IO Connection Issues:**
```bash
# Verificar CORS origins
echo $SOCKETIO_CORS_ORIGINS

# Verificar frontend config
echo $VITE_WS_URL

# Probar conexión WebSocket
wscat -c wss://api.empresa.com
```

### 9.2 Performance Optimization

#### **Para Alta Carga:**
```bash
# Aumentar Redis connections
REDIS_MAX_CONNECTIONS=100

# Reducir frecuencia de tasks
NOTIFICATION_CHECK_INTERVAL_MINUTES=10
METRICS_REFRESH_INTERVAL_MINUTES=30

# Optimizar cache TTL
REDIS_CACHE_TTL_MINUTES=2
```

#### **Para Desarrollo:**
```bash
# Más logs
LOG_LEVEL=DEBUG
ENABLE_TASK_LOGGING=true

# Tasks más frecuentes
NOTIFICATION_CHECK_INTERVAL_MINUTES=2
METRICS_REFRESH_INTERVAL_MINUTES=5
```

## 10. Actualización de Variables

### 10.1 Migración desde Versión Anterior

Si actualizas desde una versión anterior del CRM Ventas:

1. **Agregar nuevas variables Sprint 2:**
```bash
ENABLE_SCHEDULED_TASKS=true
NOTIFICATION_CHECK_INTERVAL_MINUTES=5
METRICS_REFRESH_INTERVAL_MINUTES=15
CLEANUP_INTERVAL_HOURS=1
```

2. **Configurar Redis (si no estaba):**
```bash
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
```

3. **Actualizar frontend:**
```bash
VITE_WS_URL=ws://localhost:8000  # Agregar WebSocket URL
```

### 10.2 Rollback Procedure

Si hay problemas con las nuevas variables:

```bash
# Deshabilitar Sprint 2 features
ENABLE_SCHEDULED_TASKS=false

# O usar configuraciones conservadoras
NOTIFICATION_CHECK_INTERVAL_MINUTES=30
METRICS_REFRESH_INTERVAL_MINUTES=60
CLEANUP_INTERVAL_HOURS=4
```

---

## 📋 **RESUMEN DE CAMBIOS SPRINT 2**

### **Nuevas Variables Agregadas:**
1. **Background Jobs**: 6 nuevas variables para scheduled tasks
2. **Redis Optimization**: 4 nuevas variables para cache y performance
3. **Socket.IO**: 4 nuevas variables para WebSocket configuration
4. **Notification System**: 5 nuevas variables para umbrales y retención
5. **Metrics System**: 4 nuevas variables para analytics en tiempo real

### **Variables Actualizadas:**
1. **`REDIS_URL`** → Separado en `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`
2. **Frontend**: Agregado `VITE_WS_URL` para WebSocket connection

### **Recomendaciones de Producción:**
1. **Habilitar background jobs**: `ENABLE_SCHEDULED_TASKS=true`
2. **Configurar Redis**: Requerido para optimal performance
3. **Health checks**: Usar endpoints `/health/*` para monitoring
4. **Logging**: Configurar según entorno (DEBUG dev, WARNING prod)

---

**¡Configuración completa lista para producción con Sprint 2 features!** 🚀

*Última actualización: 27 de Febrero 2026 - Sprint 2 Completado*
*Documentación para CRM Ventas v2.0 - Tracking Avanzado*