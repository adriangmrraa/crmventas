# Despliegue en EasyPanel / Docker - Guía Completa

Este proyecto está optimizado para EasyPanel, un orquestador de contenedores basado en Docker.

## 1. Estructura del Proyecto en EasyPanel

### 1.1 Crear un Nuevo Proyecto

``` 
EasyPanel Dashboard
  → New Project
  → Select Source: GitHub (o Git Repo)
  → Seleccionar este repositorio
``` 

### 1.2 Agregar Infraestructura (Add-ons)

#### PostgreSQL
```
1. Click "Add Service" → Search "PostgreSQL"
2. Configurar:
   - Version: 13+ (recomendado 13 o 15)
   - Username: postgres
   - Password: (strong password)
   - Database: nexus_db
3. Copiar conexión string: postgres://user:pass@host:5432/nexus_db
4. Asignar a POSTGRES_DSN
```

#### Redis
```
1. Click "Add Service" → Search "Redis"
2. Configurar:
   - Version: Alpine (más liviano)
   - Password: (optional pero recomendado)
3. Copiar conexión string: redis://host:6379
4. Asignar a REDIS_URL
```

## 2. Despliegue de Microservicios

### 2.1 WhatsApp Service (Puerto 8002) - PÚBLICO

```
1. Add Service → Docker
2. Nombre: whatsapp-service
3. Dockerfile: whatsapp_service/Dockerfile
4. Puerto: 8002
5. Dominio: wa.tudominio.com (HTTPS automático con Let's Encrypt)
6. Healthcheck:
   - Path: /health
   - Port: 8002
   - Interval: 30s
   - Timeout: 10s
7. Variables de Entorno:
   - YCLOUD_API_KEY=...
   - YCLOUD_WEBHOOK_SECRET=...
   - INTERNAL_API_TOKEN=...
   - ORCHESTRATOR_SERVICE_URL=http://orchestrator_service:8000
   - REDIS_URL=...
8. Deploy
```

**Importante:** El servicio acepta webhooks en `/webhook` y `/webhook/ycloud` para máxima compatibilidad con el panel de YCloud.
```
https://wa.tudominio.com/webhook
```

### 2.2 Orchestrator Service (Puerto 8000) - INTERNO

```
1. Add Service → Docker
2. Nombre: orchestrator-service
3. Dockerfile: orchestrator_service/Dockerfile
4. Puerto: 8000
5. Dominio: (OPCIONAL - puedes usar nombre de servicio internamente)
6. Healthcheck:
   - Path: /health
   - Port: 8000
   - Interval: 30s
7. Variables de Entorno:
   - OPENAI_API_KEY=...
   - POSTGRES_DSN=... (copiada de PostgreSQL add-on)
   - REDIS_URL=... (copiada de Redis add-on)
   - INTERNAL_API_TOKEN=...
   - STORE_NAME=...
   - BOT_PHONE_NUMBER=...
   - TIENDANUBE_STORE_ID=...
   - TIENDANUBE_ACCESS_TOKEN=...
   - HANDOFF_EMAIL=...
   - SMTP_HOST=...
   - SMTP_PORT=...
   - SMTP_USER=...
   - SMTP_PASS=...
   - ADMIN_TOKEN=...
   - CORS_ALLOWED_ORIGINS=...
8. Deploy
```

**Nota:** El Orchestrator ejecuta migraciones de BD automáticamente en startup (via lifespan event).

### 2.3 Frontend React (Puerto 80) - PÚBLICO

```
1. Add Service → Docker
2. Nombre: frontend-react
3. Dockerfile: frontend_react/Dockerfile
4. Puerto: 80
5. Dominio: admin.tudominio.com (HTTPS)
6. Healthcheck: (la UI es React, puede no tener endpoint /health)
7. Variables de Entorno:
   - ADMIN_TOKEN=... (copia el mismo del Orchestrator)
   - ORCHESTRATOR_URL=http://orchestrator_service:8000 (o deja en blanco para auto-detectar)
8. Deploy
```

**Auto-detección de URL:**
Si no especificas `ORCHESTRATOR_URL`, el Frontend React lo detecta automáticamente:
- `localhost` → `http://localhost:8000`
- `frontend-react.domain.com` → `orchestrator-service.domain.com`

## 3. Mapeo de Puertos y Networking

| Servicio | Puerto Interno | Exposición Pública | URL |
| :--- | :--- | :--- | :--- |
| whatsapp_service | 8002 | ✅ SÍ | `https://wa.tudominio.com` |
| orchestrator_service | 8000 | ❌ NO (interno) | `http://orchestrator_service:8000` (red interna) |
| frontend_react | 80 | ✅ SÍ | `https://admin.tudominio.com` |
| postgres | 5432 | ❌ NO (solo desde servicios) | `postgres://...@postgres:5432` |
| redis | 6379 | ❌ NO (solo desde servicios) | `redis://redis:6379` |

## 4. Pasos Críticos Post-Deploy

### 4.1 Migraciones de Base de Datos

El `orchestrator_service` ejecuta migraciones automáticamente en startup:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Conecta a DB
    await db.connect()
    
    # Ejecuta schema (dentalogic_schema.sql)
    # El sistema usa un Smart Splitter para ejecutar cada sentencia individualmente
    # garantizando compatibilidad con funciones PL/pgSQL complejas.
    await sync_environment()
```

**Si la BD es nueva:**
- Se crean tablas desde `dentalogic_schema.sql` (ejecutar manualmente)
- Se crea un "default tenant" usando las variables de entorno

**Si ya existe:**
- Las migraciones son idempotentes (CREATE TABLE IF NOT EXISTS)
- No sobreescriben datos existentes (por defecto)

**Para resetear BD (en desarrollo):**
```bash
# Conectar a PostgreSQL (via EasyPanel console)
psql -U postgres -d nexus_db

# Dropear y recrear
DROP TABLE IF EXISTS chat_messages CASCADE;
DROP TABLE IF EXISTS chat_conversations CASCADE;
-- Luego reiniciar orchestrator_service
-- Las migraciones se ejecutan automáticamente
```

### 4.2 Configuración de Webhooks (YCloud)

1. Ve a panel de YCloud
2. Busca "Webhook Settings" o "API Configuration"
3. Configura:
   - **URL:** `https://wa.tudominio.com/webhook/ycloud`
   - **Secret:** El valor de `YCLOUD_WEBHOOK_SECRET` (debe coincidir con el valor guardado en **The Vault**).
   - **Events:** Message, MessageStatus, etc.
4. **The Vault (Sovereign Credentials)**:
   - Es **obligatorio** cargar el `YCLOUD_API_KEY` y `YCLOUD_WEBHOOK_SECRET` en la tabla `credentials` para cada `tenant_id`. 
   - El sistema prioriza estos valores sobre las variables de entorno para permitir el aislamiento multi-sede.
5. **Tipado Crítico**: Asegúrate de que el `tenant_id` se maneje siempre como un **entero** en las comunicaciones internas (el sistema v7.8 incluye casts automáticos para prevenir errores de tipo).

### 4.3 Verificar Conectividad

```bash
# Desde la consola de EasyPanel:

# ¿Orchestrator arrancó?
curl http://orchestrator_service:8000/health

# ¿WhatsApp Service arrancó?
curl http://whatsapp_service:8002/health

# ¿PostgreSQL accesible?
psql -U postgres -h postgres -d nexus_db -c "SELECT 1"

# ¿Redis accesible?
redis-cli -h redis ping
```

### 4.4 Validar Migraciones de BD

```bash
psql -U postgres -h postgres -d nexus_db

# Ver tablas creadas
\dt

# Ver tenants
SELECT * FROM tenants;

# Ver tabla de conversaciones (debe estar vacía inicialmente)
### 4.5 Configuración de Google Calendar (Service Account)

Para que el sistema sincronice eventos, es **CRÍTICO** compartir cada calendario con la Service Account:

1.  **Obtener Email de Service Account**:
    - Desde Google Cloud Console > IAM & Admin > Service Accounts.
    - Copiar el email (ej: `dental-bot@project-id.iam.gserviceaccount.com`).
2.  **Compartir Calendario**:
    - Ir a Google Calendar (dueño del calendario).
    - Configuración > "Integrar el calendario" o "Compartir con personas específicas".
    - Agregar el email de la Service Account.
    - Permisos: **"Hacer cambios en eventos"** (Make changes to events).
3.  **Obtener Calendar ID**:
    - Copiar el "ID de calendario" (normalmente el email del dueño o un string largo `...group.calendar.google.com`).
    - Asignar este ID al profesional correspondiente en el panel admin (`/admin/professionals`).

## 5. Variables de Entorno en EasyPanel

### Método 1: Panel UI
```
Service → Settings → Environment Variables
  → Add
  → Key: OPENAI_API_KEY
  → Value: sk-proj-xxxxx
  → Save
  → Deploy
```

### Método 2: Archivo .env
Si el servicio soporta, subir `.env` a la raíz del Dockerfile:
```dockerfile
FROM python:3.11
COPY .env /app/.env
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]
```

### Método 3: Secrets (Recomendado para producción)
EasyPanel puede almacenar secretos encriptados:
```
Project → Secrets
  → Add Secret
  → SMTP_PASS=xxxxx (se almacena encriptado)
  → Los servicios acceden vía variable de entorno
```

## 6. Healthchecks y Readiness Probes

### Orchestrator
```
GET /health
Respuesta: 200 {"status": "ok"}

GET /ready
Respuesta: 200 {"status": "ok"} (si DB conectada)
```

### WhatsApp Service
```
GET /health
Respuesta: 200 {"status": "ok"}
```

### Platform UI
```
GET / (página HTML)
Respuesta: 200 (HTML del dashboard)
```

## 7. Logs y Debugging

### Ver logs en tiempo real (EasyPanel)
```
Service → Logs
  → Ver output del contenedor
```

### Buscar errores específicos
```
Logs → Search
  → "error"
  → "migration_failed"
  → "request_failed"
```

### Acceder al contenedor
```
Service → Console (SSH)
  → Ejecutar comandos
  → Ej: curl http://localhost:8000/health
```

## 8. Troubleshooting

### Error: 500 en /chat

**Causa:** Variable de entorno faltante o error de conexión

**Solución:**
```
1. Ver logs de orchestrator_service
2. Buscar "error" o "CRITICAL"
3. Comunes:
   - OPENAI_API_KEY no configurada
   - POSTGRES_DSN no válida
   - TIENDANUBE_ACCESS_TOKEN expirado
```

### Error: Bot no responde

**Causa:** ORCHESTRATOR_SERVICE_URL incorrecto

**Solución:**
```
1. Verificar en whatsapp_service que:
   ORCHESTRATOR_SERVICE_URL=http://orchestrator_service:8000
   (Si usas dominio, debe ser resuelto internamente)
2. Hacer curl desde WhatsApp Service:
   curl http://orchestrator_service:8000/health
3. Si falla:
   - Revisar nombre del servicio en EasyPanel
   - Revisar que servicios estén en la misma red Docker
```

### Error: Bot responde doble

**Causa:** Deduplicación en Redis no funciona

**Solución:**
```
1. Verificar REDIS_URL:
   redis://redis:6379 (debe ser resuelto internamente)
2. Validar que Redis esté corriendo:
   redis-cli -h redis ping
3. Si Redis está en otro host:
   REDIS_URL=redis://redis.host.com:6379
```

### Error: SMTP/Mail no se envía

**Causa:** Credenciales SMTP inválidas

**Solución:**
```
1. Verificar SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS
2. Para Gmail:
   - SMTP_HOST=smtp.gmail.com
   - SMTP_PORT=465
   - SMTP_PASS=(contraseña de aplicación, no contraseña normal)
3. Revisar logs en system_events table:
   SELECT * FROM system_events WHERE event_type='smtp_failed';
```

## 9. Performance y Escalabilidad

### Recomendaciones de recursos (EasyPanel)

```
Orchestrator Service:
  - CPU: 2 vCPUs (mínimo 1)
  - RAM: 1GB (mínimo 512MB)
  - Restart policy: Always

WhatsApp Service:
  - CPU: 1 vCPU
  - RAM: 512MB

Platform UI:
  - CPU: 1 vCPU
  - RAM: 256MB

PostgreSQL:
  - CPU: 2 vCPUs
  - RAM: 2GB
  - Storage: 20GB (ajustar según uso)

Redis:
  - CPU: 1 vCPU
  - RAM: 512MB
```

### Auto-scaling (si EasyPanel lo soporta)

```
Orchestrator Service:
  - Min replicas: 1
  - Max replicas: 3
  - CPU trigger: 70%
  - RAM trigger: 80%
```

## 10. Despliegue Alternativo: Docker Compose (Desarrollo)

Para desarrollo local:

```bash
# Clonar repo
git clone https://github.com/tu-repo/nexus.git
cd nexus

# Configurar .env
cp .env.example .env
# Editar .env con valores locales

# Levantar servicios
docker-compose up --build

# Acceso:
# - Orchestrator: http://localhost:8000
# - WhatsApp Service: http://localhost:8002
# - Frontend React: http://localhost:5173
```

**docker-compose.yml incluye:**
- orchestrator_service
- whatsapp_service
- frontend_react
- postgres
- redis

---

*Guía de Despliegue Nexus v3 © 2025*


## Marketing Hub Deployment

Nuevo módulo implementado en Febrero 2026 que requiere configuración adicional para Meta (Facebook/Instagram) Ads y WhatsApp HSM Automation.

### Prerrequisitos

1. **Meta Developers Account**
   - Cuenta en [developers.facebook.com](https://developers.facebook.com/)
   - App tipo "Business" creada
   - App ID y App Secret obtenidos

2. **Business Verification** (Recomendado)
   - Verificación de negocio en Meta Business Manager
   - Permisos para `ads_management` y `business_management`

3. **WhatsApp Business Account** (Para HSM)
   - Número WhatsApp Business verificado
   - Aprobación para plantillas HSM

### Pasos de Configuración

#### Paso 1: Configurar Meta Developers App

```bash
# 1. Ir a https://developers.facebook.com/
# 2. Crear nueva App → Business → Nombre: "CRM Ventas Marketing Hub"
# 3. Agregar producto "Facebook Login" → Configurar OAuth
# 4. Agregar producto "Marketing API" → Solicitar permisos
# 5. Agregar producto "WhatsApp Business Platform" (para HSM)
```

**Configuración OAuth:**
- **Valid OAuth Redirect URIs**: `https://tu-crm.com/crm/auth/meta/callback`
- **App Domains**: `tu-crm.com`
- **Privacy Policy URL**: `https://tu-crm.com/privacy`

**Permisos API Requeridos:**
- `ads_management` - Gestión campañas publicitarias
- `business_management` - Gestión Business Manager
- `whatsapp_business_management` - HSM templates (opcional)
- `whatsapp_business_messaging` - Envío mensajes (opcional)

#### Paso 2: Configurar Variables de Entorno

```bash
# Archivo: .env.production
META_APP_ID=tu_app_id_facebook
META_APP_SECRET=tu_app_secret_facebook
META_REDIRECT_URI=https://tu-crm.com/crm/auth/meta/callback
META_API_VERSION=v20.0
```

#### Paso 3: Ejecutar Migraciones Database

```bash
cd /home/node/.openclaw/workspace/projects/crmventas/orchestrator_service
python3 run_meta_ads_migrations.py
```

**Script incluye:**
- Creación 8 tablas marketing
- Columnas adicionales en tabla `leads`
- Rollback automático en caso de error
- Verificación de éxito

#### Paso 4: Verificar Implementación

```bash
# 1. Iniciar servicios
docker-compose up -d  # o sistema equivalente

# 2. Verificar endpoints
curl -X GET "http://localhost:8000/crm/marketing/stats" \
  -H "Authorization: Bearer <JWT>" \
  -H "X-Admin-Token: <ADMIN_TOKEN>"

# 3. Probar OAuth flow
# Navegar a: http://localhost:3000/crm/marketing
# Click "Connect Meta Account"
```

### Configuración EasyPanel

Si usas EasyPanel para deployment:

1. **Agregar Variables Entorno:**
   - `META_APP_ID`, `META_APP_SECRET`, `META_REDIRECT_URI`
   - Reiniciar servicio después de agregar

2. **Database Permissions:**
   - Usuario DB necesita permisos CREATE TABLE
   - Ejecutar migraciones manualmente o via script

3. **SSL/HTTPS:**
   - Certificado SSL válido para OAuth callback
   - `META_REDIRECT_URI` debe usar HTTPS

### Troubleshooting

#### Error: "Invalid OAuth redirect_uri"
- Verificar que `META_REDIRECT_URI` coincida exactamente con Meta Developers
- Incluir protocolo HTTPS en producción

#### Error: "App not approved for permissions"
- Solicitar revisión de permisos en Meta Developers
- Proporcionar caso de uso claro (marketing automation)

#### Error: "Database migration failed"
- Verificar permisos usuario PostgreSQL
- Ejecutar script con usuario admin temporalmente
- Ver logs: `python3 run_meta_ads_migrations.py --verbose`

#### Error: "Rate limit exceeded"
- Meta API tiene límite 200 calls/hour
- Implementar caching en `MarketingService`
- Considerar batch processing para datos históricos

### Monitoreo Post-Deployment

1. **Logs OAuth:** `meta_oauth.log` (si configurado)
2. **API Errors:** Errores Meta Graph API
3. **ROI Tracking:** Conversiones atribuidas a campañas
4. **Token Expiry:** Notificar 7 días antes de expiración

### Herramientas de Diagnóstico Post-Deployment

#### **1. Verificar Estadísticas Marketing:**
```bash
cd /home/node/.openclaw/workspace/projects/crmventas
python debug_marketing_stats.py
```

#### **2. Diagnóstico Automatización:**
```bash
cd /home/node/.openclaw/workspace/projects/crmventas/orchestrator_service
python check_automation.py
```

#### **3. Verificar Leads Database:**
```bash
cd /home/node/.openclaw/workspace/projects/crmventas/orchestrator_service
python check_leads.py
```

### Configuración Webhooks (Actualizado Febrero 2026)

#### **URLs Webhook Disponibles:**
- **YCloud Webhook**: `{base_url}/webhook/ycloud`
- **Meta Webhook**: `{base_url}/crm/webhook/meta`

#### **Obtener URLs de Configuración:**
```bash
# API endpoint para obtener URLs configuración
curl -X GET "http://localhost:8000/admin/config/deployment" \
  -H "Authorization: Bearer <JWT>" \
  -H "X-Admin-Token: <ADMIN_TOKEN>"

# Respuesta:
{
  "webhook_ycloud_url": "https://tu-crm.com/webhook/ycloud",
  "webhook_meta_url": "https://tu-crm.com/crm/webhook/meta",
  "orchestrator_url": "https://tu-crm.com",
  "environment": "production"
}
```

#### **Configurar en Meta Developers:**
1. **Meta Developers → App → Webhooks**
2. **Leadgen Webhook:**
   - URL: `https://tu-crm.com/crm/webhook/meta`
   - Verify Token: `WEBHOOK_META_VERIFY_TOKEN` (si configurado)
   - Secret: `WEBHOOK_META_SECRET` (si configurado)
3. **Subscribe to Fields:** `leadgen`

#### **Configurar en YCloud:**
1. **YCloud Dashboard → Webhook Settings**
2. **Webhook URL:** `https://tu-crm.com/webhook/ycloud`
3. **Secret:** `WEBHOOK_YCLOUD_SECRET` (si configurado)
4. **Events:** Message, MessageStatus, TemplateStatus

### Páginas Legales Requeridas (Meta OAuth)

Para aprobación Meta OAuth, se requieren URLs públicas:

1. **Privacy Policy URL:** `https://tu-crm.com/privacy`
2. **Terms of Service URL:** `https://tu-crm.com/terms`

**Implementadas en:** `frontend_react/src/views/PrivacyTermsView.tsx`
**Rutas disponibles:** `/legal`, `/privacy`, `/terms`

### Mejoras Recientes (Febrero 2026)

#### **Frontend:**
- **MetaConnectionWizard.tsx**: UI/UX mejorada, flujo paso a paso optimizado
- **ConfigView.tsx**: Gestión credenciales CRUD completa
- **MarketingHubView.tsx**: Dashboard mejorado con webhook configuration
- **Responsive Design**: Scroll optimizado para móviles

#### **Backend:**
- **admin_routes.py**: Nuevas rutas administrativas + deployment config
- **meta_ads_service.py**: Manejo errores robusto + filtros expandidos
- **whatsapp_service/main.py**: Refactorización completa + logging mejorado
- **Credentials Management**: Sistema centralizado multi-tenant

#### **Security:**
- **Webhook URLs**: Incluidas en configuración deployment
- **Rate Limiting**: Endpoints marketing con límites específicos
- **Audit Logging**: Todas las acciones registradas
- **Token Encryption**: Almacenamiento seguro con rotación automática

### Rollback Procedure

Si necesitas deshabilitar Marketing Hub:

1. **Remover Variables Entorno:** `META_APP_ID`, `META_APP_SECRET`
2. **Deshabilitar Endpoints:** Comentar rutas en `main.py`
3. **Mantener Data:** Las tablas marketing pueden permanecer
4. **Frontend:** Ocultar menú Marketing en `Sidebar.tsx`

### Documentación Adicional

- `FINAL_IMPLEMENTATION_SUMMARY.md` - Resumen técnico completo
- `ENV_EXAMPLE.md` - Template variables entorno
- `SPRINT3_OAUTH_CONFIGURATION.md` - Guía paso a paso OAuth
- `AUDITORIA_FINAL_CONCLUSION.md` - Resultados auditoría
