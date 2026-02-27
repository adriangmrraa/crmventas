# 🚀 DEPLOYMENT PLAN - SPRINT 2 A STAGING

## 📋 **INFORMACIÓN DEL DEPLOYMENT**

### **ENTORNO:**
- **Nombre:** Staging Environment
- **Propósito:** Testing de Sprint 2 (Tracking Avanzado)
- **URL:** `https://staging.crmventas.com` (ejemplo)
- **Base de datos:** PostgreSQL separada de producción
- **Cache:** Redis separado

### **VERSIÓN:**
- **Sprint:** 2 - Tracking Avanzado
- **Branch:** `sprint2-tracking-avanzado`
- **Commit:** `HEAD`
- **Fecha:** 27 de Febrero 2026

---

## 🎯 **OBJETIVOS DEL DEPLOYMENT**

### **✅ VERIFICAR:**
1. Sistema de métricas en tiempo real funcionando
2. Dashboard CEO mejorado con gráficos
3. Pestaña FORMULARIO META completa
4. Sistema de notificaciones operativo
5. Background jobs ejecutándose correctamente
6. Performance dentro de objetivos

### **✅ TESTEAR:**
1. Flujos completos de usuario
2. Integración entre componentes
3. Escalabilidad y concurrencia
4. Data integrity y consistencia
5. Seguridad y permisos

---

## 📅 **PLAN DE DEPLOYMENT PASO A PASO**

### **FASE 1: PREPARACIÓN (1 hora)**

#### **1.1 Verificar código fuente:**
```bash
# Verificar que estamos en la branch correcta
git checkout sprint2-tracking-avanzado
git pull origin sprint2-tracking-avanzado

# Verificar cambios del Sprint 2
git log --oneline -20

# Verificar que no haya conflictos
git status
```

#### **1.2 Verificar migraciones:**
```bash
# Listar migraciones del Sprint 2
ls -la orchestrator_service/migrations/patch_0*.py | tail -5

# Verificar que patch_016_notifications.py existe
test -f orchestrator_service/migrations/patch_016_notifications.py && echo "✅ Migración de notificaciones lista"
```

#### **1.3 Verificar dependencias:**
```bash
# Backend dependencies
cat orchestrator_service/requirements.txt | grep -E "apscheduler|redis"

# Frontend dependencies
cat frontend_react/package.json | grep -E "date-fns|socket.io"
```

### **FASE 2: CONFIGURACIÓN DE ENTORNO (2 horas)**

#### **2.1 Configurar variables de entorno staging:**
```bash
# Crear archivo .env.staging
cat > .env.staging << EOF
# Database
POSTGRES_DSN=postgresql://user:pass@staging-db.crmventas.com:5432/crmventas_staging

# Redis
REDIS_HOST=staging-redis.crmventas.com
REDIS_PORT=6379
REDIS_PASSWORD=staging_redis_pass

# API Keys
OPENAI_API_KEY=sk-staging-...
META_APP_ID=staging-app-id
META_APP_SECRET=staging-app-secret

# URLs
FRONTEND_URL=https://staging.crmventas.com
BACKEND_URL=https://api.staging.crmventas.com

# Features
ENABLE_NOTIFICATIONS=true
ENABLE_SCHEDULED_TASKS=true
ENABLE_METRICS_CACHE=true

# Logging
LOG_LEVEL=INFO
SENTRY_DSN=staging-sentry-dsn
EOF
```

#### **2.2 Configurar base de datos staging:**
```sql
-- Crear database si no existe
CREATE DATABASE crmventas_staging;

-- Crear usuario con permisos
CREATE USER staging_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE crmventas_staging TO staging_user;

-- Configurar extensions
\c crmventas_staging
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
```

#### **2.3 Configurar Redis staging:**
```bash
# Crear instancia Redis (ejemplo para AWS ElastiCache)
aws elasticache create-cache-cluster \
    --cache-cluster-id crmventas-staging \
    --cache-node-type cache.t3.micro \
    --engine redis \
    --num-cache-nodes 1 \
    --security-group-ids sg-xxx
```

### **FASE 3: DEPLOYMENT BACKEND (2 horas)**

#### **3.1 Build de Docker image:**
```dockerfile
# Dockerfile.staging
FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY orchestrator_service/requirements.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY orchestrator_service/ .

# Variables de entorno
ENV PYTHONPATH=/app
ENV ENVIRONMENT=staging

# Puerto
EXPOSE 8000

# Comando de inicio
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### **3.2 Ejecutar migraciones:**
```bash
# Ejecutar todas las migraciones
python3 orchestrator_service/migrations/run_migrations.py \
    --dsn postgresql://user:pass@staging-db.crmventas.com:5432/crmventas_staging \
    --apply-all

# Verificar migraciones aplicadas
python3 orchestrator_service/migrations/run_migrations.py \
    --dsn postgresql://user:pass@staging-db.crmventas.com:5432/crmventas_staging \
    --status
```

#### **3.3 Deploy a servidor staging:**
```bash
# Build image
docker build -f Dockerfile.staging -t crmventas-backend:staging .

# Push a registry
docker tag crmventas-backend:staging registry.crmventas.com/crmventas-backend:staging
docker push registry.crmventas.com/crmventas-backend:staging

# Deploy en servidor staging
ssh staging-server "docker pull registry.crmventas.com/crmventas-backend:staging"
ssh staging-server "docker stop crmventas-backend || true"
ssh staging-server "docker rm crmventas-backend || true"
ssh staging-server "docker run -d \
    --name crmventas-backend \
    --env-file /opt/crmventas/.env.staging \
    -p 8000:8000 \
    registry.crmventas.com/crmventas-backend:staging"
```

### **FASE 4: DEPLOYMENT FRONTEND (1 hora)**

#### **4.1 Build de producción:**
```bash
cd frontend_react

# Instalar dependencias
npm ci

# Build con variables de staging
VITE_API_URL=https://api.staging.crmventas.com \
VITE_ENVIRONMENT=staging \
npm run build

# El build se genera en /dist
```

#### **4.2 Deploy a hosting (ejemplo Vercel):**
```bash
# Configurar Vercel
vercel link --project crmventas-staging

# Deploy
vercel --prod --env VITE_API_URL=https://api.staging.crmventas.com

# O usando el dashboard de Vercel/Netlify
```

#### **4.3 Configurar CDN y SSL:**
```bash
# Configurar custom domain
vercel domains add staging.crmventas.com

# Forzar SSL
# (Configuración en dashboard del hosting)
```

### **FASE 5: CONFIGURACIÓN DE SERVICIOS (1 hora)**

#### **5.1 Iniciar scheduled tasks:**
```bash
# Verificar que el scheduler se inicie automáticamente
# En main.py, agregar al final:
if __name__ == "__main__":
    scheduled_tasks_service.start_all_tasks()

# O iniciar manualmente via API
curl -X POST "https://api.staging.crmventas.com/scheduled-tasks/start" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

#### **5.2 Configurar health checks:**
```bash
# Health check endpoint
curl "https://api.staging.crmventas.com/health"

# Scheduler health
curl "https://api.staging.crmventas.com/scheduled-tasks/health"

# Database health
curl "https://api.staging.crmventas.com/admin/health/db"
```

#### **5.3 Configurar monitoring:**
```bash
# Configurar Sentry para staging
# Configurar Logging a CloudWatch/Papertrail
# Configurar alertas para errores > 5%
```

### **FASE 6: SMOKE TESTS (1 hora)**

#### **6.1 Tests básicos de funcionalidad:**
```bash
#!/bin/bash
# smoke_tests.sh

echo "🚀 RUNNING SMOKE TESTS - SPRINT 2"

# 1. Health checks
echo "1. Testing health endpoints..."
curl -f "https://api.staging.crmventas.com/health" || exit 1
curl -f "https://api.staging.crmventas.com/scheduled-tasks/health" || exit 1

# 2. Authentication
echo "2. Testing authentication..."
LOGIN_RESPONSE=$(curl -s -X POST "https://api.staging.crmventas.com/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@staging.com","password":"test123"}')
TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')

if [ "$TOKEN" = "null" ]; then
  echo "❌ Login failed"
  exit 1
fi

# 3. Metrics endpoints
echo "3. Testing metrics endpoints..."
curl -f -H "Authorization: Bearer $TOKEN" \
  "https://api.staging.crmventas.com/admin/core/sellers/dashboard/overview?tenant_id=1" || exit 1

# 4. Notification endpoints
echo "4. Testing notification endpoints..."
curl -f -H "Authorization: Bearer $TOKEN" \
  "https://api.staging.crmventas.com/notifications/count" || exit 1

# 5. Meta leads endpoint
echo "5. Testing meta leads endpoint..."
curl -f -H "Authorization: Bearer $TOKEN" \
  "https://api.staging.crmventas.com/crm/meta/leads?tenant_id=1" || exit 1

echo "✅ ALL SMOKE TESTS PASSED"
```

#### **6.2 Tests de integración:**
```python
# integration_tests.py
import requests
import pytest

BASE_URL = "https://api.staging.crmventas.com"

def test_full_notification_flow():
    """Test flujo completo de notificaciones"""
    # 1. Login
    # 2. Crear conversación de prueba
    # 3. Esperar notificación de "sin respuesta"
    # 4. Verificar que llegó la notificación
    # 5. Marcar como leída
    # 6. Verificar count actualizado
    pass

def test_metrics_calculation():
    """Test cálculo de métricas en tiempo real"""
    # 1. Simular actividad de vendedor
    # 2. Trigger refresh de métricas
    # 3. Verificar que métricas se actualizaron
    # 4. Verificar dashboard muestra datos correctos
    pass
```

#### **6.3 Tests de performance:**
```bash
# Ejecutar performance tests
python3 test_performance_metrics.py \
  --base-url https://api.staging.crmventas.com \
  --tenant-id 1 \
  --output performance_staging.json

# Verificar que cumple objetivos
python3 check_performance_targets.py performance_staging.json
```

### **FASE 7: VALIDACIÓN Y MONITOREO (Continuo)**

#### **7.1 Validación manual:**
1. **Login** en staging.crmventas.com
2. **Verificar sidebar** tiene "FORMULARIO META"
3. **Probar dashboard CEO** - Gráficos y métricas
4. **Probar notificaciones** - Bell icon funciona
5. **Probar meta leads** - Tabla carga y filtra
6. **Probar asignaciones** - Vendedores pueden asignarse
7. **Probar background jobs** - Verificar logs

#### **7.2 Checklist de validación:**
- [ ] Frontend carga sin errores en consola
- [ ] API responde en < 500ms (p95)
- [ ] Base de datos conectada y responsive
- [ ] Redis cache funcionando
- [ ] Scheduled tasks ejecutándose
- [ ] Notificaciones llegando en tiempo real
- [ ] Métricas actualizándose correctamente
- [ ] Permisos funcionando (CEO vs vendedor)
- [ ] Data integrity preservada

#### **7.3 Monitoreo post-deployment:**
```bash
# Monitorear logs
tail -f /var/log/crmventas/staging.log | grep -E "(ERROR|WARNING|notification|metric)"

# Monitorear métricas
watch -n 5 'curl -s https://api.staging.crmventas.com/health | jq'

# Monitorear errores en Sentry
# (Dashboard de Sentry para staging)
```

---

## 🚨 **PLAN DE ROLLBACK**

### **CONDICIONES PARA ROLLBACK:**
1. Error rate > 10% por más de 5 minutos
2. Critical functionality broken (login, dashboard)
3. Data corruption detected
4. Performance degradation > 50%
5. Security vulnerability found

### **PROCEDIMIENTO DE ROLLBACK:**
```bash
# 1. Revertir frontend a versión anterior
vercel --prod -A ./vercel-prev.json

# 2. Revertir backend
ssh staging-server "docker run -d \
    --name crmventas-backend \
    --env-file /opt/crmventas/.env.staging \
    -p 8000:8000 \
    registry.crmventas.com/crmventas-backend:prev-stable"

# 3. Revertir migraciones si es necesario
python3 orchestrator_service/migrations/run_migrations.py \
    --dsn $STAGING_DSN \
    --rollback 16  # Revertir patch de notificaciones

# 4. Notificar al equipo
curl -X POST $SLACK_WEBHOOK \
  -d '{"text":"🚨 ROLLBACK EJECUTADO en staging. Issues encontrados: <lista>"}'
```

---

## 📊 **MÉTRICAS DE ÉXITO**

### **OBJETIVOS DE PERFORMANCE:**
- ✅ API response time p95 < 500ms
- ✅ Frontend load time < 3s
- ✅ Database query time < 100ms (p95)
- ✅ Notification delivery < 5s
- ✅ Metrics calculation < 30s (full tenant)

### **OBJETIVOS DE CALIDAD:**
- ✅ 0 errores críticos en logs
- ✅ 100% de smoke tests pasan
- ✅ 95%+ de user acceptance tests pasan
- ✅ Data integrity 100% preservada
- ✅ Security tests pasan (OWASP básico)

### **OBJETIVOS DE USABILIDAD:**
- ✅ CEO puede ver dashboard completo
- ✅ Vendedores reciben notificaciones
- ✅ Meta leads se cargan y filtran
- ✅ Sistema responde en tiempo real
- ✅ UI/UX consistente y sin bugs

---

## 👥 **RESPONSABILIDADES**

### **DEV TEAM:**
- ✅ Preparar código y migraciones
- ✅ Ejecutar deployment backend
- ✅ Ejecutar smoke tests
- ✅ Monitorear post-deployment

### **QA TEAM:**
- ✅ Ejecutar tests de integración
- ✅ Validar funcionalidad manual
- ✅ Reportar bugs encontrados
- ✅ Verificar performance

### **OPS TEAM:**
- ✅ Configurar infraestructura
- ✅ Configurar monitoring
- ✅ Gestionar rollback si es necesario
- ✅ Mantener documentación actualizada

---

## 📞 **CONTACTOS DE EMERGENCIA**

### **DURANTE DEPLOYMENT:**
- **Lead Dev:** @devlead - 555-0101
- **QA Lead:** @qalead - 555-0102
- **Ops Lead:** @opslead - 555-0103

### **POST-DEPLOYMENT:**
- **On-call Engineer:** @oncall - 555-0200
- **Support:** support@crmventas.com

---

## 🎉 **CELEBRACIÓN DE ÉXITO**

### **CUANDO TODO FUNCIONE:**
1. **Actualizar documentación** con lecciones aprendidas
2. **Notificar al equipo** de éxito del deployment
3. **Programar demo** para stakeholders
4. **Planificar next steps** para producción
5. **Celebrar** 🎊

### **ENTREGABLES FINALES:**
- ✅ Sistema funcionando en staging
- ✅ Reporte de smoke tests
- ✅ Reporte de performance
- ✅ Lista de bugs conocidos (si hay)
- ✅ Plan para producción

---

**¡BUENA SUERTE CON EL DEPLOYMENT!** 🚀

*Última actualización: 27 de Febrero 2026*