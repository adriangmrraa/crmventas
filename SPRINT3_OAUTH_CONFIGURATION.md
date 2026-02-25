# 🚀 SPRINT 3: CONFIGURACIÓN OAUTH META - PLAN DE IMPLEMENTACIÓN

## 📋 RESUMEN DE ESTADO ACTUAL

### ✅ **IMPLEMENTADO:**
1. **Backend OAuth Routes** - 5 endpoints completos en `meta_auth.py`
2. **MetaOAuthService** - Métodos para token exchange, validation, storage
3. **Frontend Components** - Wizard, banner, dashboard con integración
4. **Database Schema** - Tabla `meta_tokens` lista en migraciones

### ⚠️ **PENDIENTE DE CONFIGURACIÓN:**
1. **Meta Developers App** - App ID y Secret
2. **Variables de Entorno** - Configuración producción
3. **Testing OAuth Flow** - Validación end-to-end
4. **Token Refresh Automático** - Implementación completa

---

## 🔧 **PASO 1: CONFIGURACIÓN META DEVELOPERS**

### **1.1 Crear App en Meta Developers:**
```
URL: https://developers.facebook.com/
Acción: Crear nueva App → Business → Otro
Nombre: "CRM Ventas Marketing Hub"
Contact Email: [tu_email@empresa.com]
```

### **1.2 Agregar Productos Requeridos:**
```
Productos a agregar:
1. WhatsApp → Business Management API
2. Facebook Login → OAuth 2.0  
3. Marketing API → Ads Management
```

### **1.3 Configurar OAuth Settings:**
```yaml
# En Meta Developers Dashboard:
Valid OAuth Redirect URIs:
  - https://tu-crm.com/crm/auth/meta/callback
  - https://app.tu-crm.com/crm/auth/meta/callback
  - http://localhost:8000/crm/auth/meta/callback (development)

App Domains:
  - tu-crm.com
  - app.tu-crm.com

Privacy Policy URL: https://tu-crm.com/privacy
Terms of Service URL: https://tu-crm.com/terms
```

### **1.4 Solicitar Permisos de API:**
```python
# Permisos requeridos (scopes):
REQUIRED_SCOPES = [
    'ads_management',           # Gestionar anuncios
    'business_management',      # Acceder a Business Manager
    'whatsapp_business_management',  # HSM Automation
    'pages_read_engagement',    # Leer páginas
    'read_insights',           # Leer métricas
]

# IMPORTANTE: Enviar para revisión de Meta (puede tomar 1-3 días)
```

---

## 🔧 **PASO 2: CONFIGURACIÓN VARIABLES ENTORNO**

### **2.1 Archivo `.env.production`:**
```bash
# Meta OAuth Configuration
META_APP_ID=tu_app_id_obtenido
META_APP_SECRET=tu_app_secret_obtenido
META_REDIRECT_URI=https://tu-crm.com/crm/auth/meta/callback
META_GRAPH_API_VERSION=v21.0
META_VERIFY_TOKEN=token_aleatorio_para_webhooks

# Database Configuration
POSTGRES_DSN=postgresql://user:password@host:5432/crmventas

# Security
JWT_SECRET_KEY=tu_jwt_secret_key
ENCRYPTION_KEY=tu_encryption_key_32_bytes

# Application
API_BASE_URL=https://api.tu-crm.com
FRONTEND_URL=https://app.tu-crm.com
```

### **2.2 Archivo `.env.development`:**
```bash
# Meta OAuth Configuration (Development)
META_APP_ID=tu_app_id_development
META_APP_SECRET=tu_app_secret_development  
META_REDIRECT_URI=http://localhost:8000/crm/auth/meta/callback
META_GRAPH_API_VERSION=v21.0

# Database Configuration (Local)
POSTGRES_DSN=postgresql://postgres:postgres@localhost:5432/crmventas_dev

# Security (Development)
JWT_SECRET_KEY=development_secret_key_change_in_production
ENCRYPTION_KEY=development_encryption_key_32_bytes

# Application (Local)
API_BASE_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
```

---

## 🔧 **PASO 3: IMPLEMENTACIÓN FLUJO OAUTH COMPLETO**

### **3.1 Endpoints Implementados:**

#### **GET `/crm/auth/meta/url`**
```python
# Genera URL OAuth con state parameter
# State: tenant_{tenant_id}_{nonce}
# Expiración: 5 minutos
# Almacenamiento: Redis o memoria temporal
```

#### **GET `/crm/auth/meta/callback`**
```python
# 1. Valida state parameter
# 2. Intercambia code por token (short-lived)
# 3. Obtiene long-lived token (60 días)
# 4. Obtiene Business Managers y Ad Accounts
# 5. Almacena token en base de datos
# 6. Retorna éxito con metadata
```

#### **POST `/crm/auth/meta/disconnect`**
```python
# 1. Elimina token de base de datos
# 2. Logs evento de auditoría
# 3. Retorna confirmación
```

#### **GET `/crm/auth/meta/test-connection`**
```python
# 1. Obtiene token de base de datos
# 2. Valida token con Meta API
# 3. Verifica expiración
# 4. Retorna estado de conexión
```

### **3.2 Métodos del Servicio:**

#### **`MetaOAuthService.exchange_code_for_token()`**
```python
# Intercambia código OAuth por access token
# URL: https://graph.facebook.com/v21.0/oauth/access_token
# Params: client_id, client_secret, redirect_uri, code
# Retorna: access_token, expires_in, token_type
```

#### **`MetaOAuthService.get_long_lived_token()`**
```python
# Obtiene long-lived token (60 días)
# URL: https://graph.facebook.com/v21.0/oauth/access_token  
# Params: grant_type=fb_exchange_token, fb_exchange_token
# Retorna: access_token, expires_in (5184000 segundos)
```

#### **`MetaOAuthService.get_business_managers_with_token()`**
```python
# Obtiene Business Managers asociados
# URL: https://graph.facebook.com/v21.0/me/businesses
# Fields: id,name,primary_page{id,name,category}
# Enriquecido con: owned_ad_accounts
```

#### **`MetaOAuthService.store_meta_token()`**
```python
# Almacena token en tabla meta_tokens
# Campos: tenant_id, access_token, token_type, expires_at, scopes, business_managers
# Upsert: Actualiza si existe, inserta si no
```

#### **`MetaOAuthService.validate_token()`**
```python
# Valida token con llamada simple
# URL: https://graph.facebook.com/v21.0/me
# Fields: id,name
# Retorna: valid, user_id, user_name
```

---

## 🔧 **PASO 4: INTEGRACIÓN FRONTEND**

### **4.1 Componente `MetaConnectionWizard.tsx`:**
```typescript
// 4-step wizard:
// 1. Generate Auth URL → GET /crm/auth/meta/url
// 2. Redirect to Meta OAuth
// 3. Return with code → handled by backend callback
// 4. Select Business Manager & Ad Account
// 5. Confirm connection
```

### **4.2 Componente `MetaTokenBanner.tsx`:**
```typescript
// Muestra estado de conexión:
// - Conectado: Token válido, expiración, reconectar
// - Desconectado: Botón conectar
// - Expirado: Alerta, botón refresh
// - Error: Mensaje error, reconectar
```

### **4.3 API Client `marketing.ts`:**
```typescript
// Métodos implementados:
getMetaAuthUrl() → Promise<AuthUrl>
disconnectMeta() → Promise<DisconnectResult>
testMetaConnection() → Promise<TestResult>
getMetaPortfolios() → Promise<BusinessManager[]>
connectMetaAccount(data) → Promise<ConnectionResult>
```

---

## 🔧 **PASO 5: TESTING OAUTH FLOW**

### **5.1 Testing Local (Development):**
```bash
# 1. Configurar .env.development
# 2. Iniciar backend: uvicorn main:app --reload --port 8000
# 3. Iniciar frontend: npm run dev --port 3000
# 4. Navegar a: http://localhost:3000/crm/marketing
# 5. Click "Connect Meta Account"
# 6. Completar wizard OAuth
```

### **5.2 Testing Integration:**
```python
# Archivo: tests/test_meta_oauth.py
import pytest
from fastapi.testclient import TestClient

def test_meta_auth_url_generation():
    """Test genera URL OAuth válida"""
    response = client.get("/crm/auth/meta/url")
    assert response.status_code == 200
    assert "auth_url" in response.json()["data"]
    assert response.json()["data"]["auth_url"].startswith("https://www.facebook.com")

def test_meta_auth_callback_invalid_state():
    """Test callback con state inválido"""
    response = client.get("/crm/auth/meta/callback?code=test&state=invalid")
    assert response.status_code == 400
    assert "Invalid or expired OAuth state" in response.json()["detail"]

def test_meta_disconnect():
    """Test desconexión cuenta Meta"""
    response = client.post("/crm/auth/meta/disconnect")
    assert response.status_code == 200
    assert response.json()["data"]["disconnected"] == True
```

### **5.3 Testing End-to-End:**
```bash
# Script: test_oauth_e2e.sh
#!/bin/bash
echo "🔧 Testing Meta OAuth Flow E2E..."

# 1. Start services
docker-compose up -d postgres redis
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

# 2. Run tests
pytest tests/test_meta_oauth.py -v

# 3. Cleanup
kill $BACKEND_PID
docker-compose down

echo "✅ E2E testing completed"
```

---

## 🔧 **PASO 6: DEPLOYMENT & MONITORING**

### **6.1 Deployment Checklist:**
- [ ] Variables de entorno configuradas en producción
- [ ] Meta App ID y Secret válidos
- [ ] Redirect URI configurado en Meta Developers
- [ ] Permisos de API aprobados por Meta
- [ ] SSL/TLS certificados instalados (HTTPS requerido)
- [ ] Database migrations ejecutadas
- [ ] Rate limiting configurado
- [ ] Audit logging habilitado

### **6.2 Monitoring Configuration:**
```yaml
# Prometheus metrics
meta_oauth_requests_total{endpoint, status}
meta_token_validations_total{result}
meta_api_response_time_seconds{endpoint}

# Alert rules
- alert: MetaTokenExpiringSoon
  expr: meta_token_expires_in_hours < 24
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Meta token expiring in {{ $value }} hours"

- alert: MetaOAuthErrorRateHigh
  expr: rate(meta_oauth_errors_total[5m]) > 0.1
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "High error rate in Meta OAuth flow"
```

### **6.3 Rollback Plan:**
```bash
# Si OAuth falla en producción:
1. Revertir deployment a versión anterior
2. Deshabilitar botones de conexión Meta en frontend
3. Notificar usuarios sobre mantenimiento
4. Debuggear en ambiente staging
5. Re-deploy con fixes
```

---

## 🎯 **PLAN DE TRABAJO SPRINT 3**

### **Día 1: Configuración Meta Developers**
1. Crear App en Meta Developers
2. Configurar productos y OAuth settings
3. Solicitar permisos de API
4. Configurar variables de entorno

### **Día 2: Implementación Completa**
1. Completar métodos faltantes en MetaOAuthService
2. Testear flujo OAuth localmente
3. Integrar frontend wizard con backend
4. Implementar token refresh automático
5. Crear tests unitarios e integración

### **Entregables Día 2:**
- ✅ MetaOAuthService completo con todos los métodos
- ✅ Flujo OAuth funcionando end-to-end
- ✅ Frontend wizard integrado con backend
- ✅ Tests unitarios e integración
- ✅ Documentación de deployment

---

## 🚨 **PROBLEMAS COMUNES & SOLUCIONES**

### **1. Error: "Invalid redirect_uri"**
```bash
# Solución:
# 1. Verificar META_REDIRECT_URI en .env
# 2. Asegurar que coincide exactamente con Meta Developers
# 3. Incluir protocolo (https://) y path completo
# 4. Para localhost: usar http://localhost:8000/crm/auth/meta/callback
```

### **2. Error: "App not approved for permissions"**
```bash
# Solución:
# 1. Solicitar revisión de permisos en Meta Developers
# 2. Proporcionar video demostrando uso de cada permiso
# 3. Puede tomar 1-3 días para aprobación
# 4. Usar sandbox mode para desarrollo
```

### **3. Error: "Token expired or invalid"**
```bash
# Solución:
# 1. Implementar token refresh automático
# 2. Verificar expiración en store_meta_token()
# 3. Usar long-lived tokens (60 días)
# 4. Manejar re-autenticación en frontend
```

### **4. Error: "Rate limit exceeded"**
```bash
# Solución:
# 1. Implementar rate limiting en backend
# 2. Cachear respuestas de Meta API
# 3. Exponential backoff para retries
# 4. Monitorear métricas de rate limiting
```

---

## 📊 **MÉTRICAS DE ÉXITO SPRINT 3**

### **Technical Metrics:**
- ✅ OAuth flow completo funcionando
- ✅ Token storage seguro en PostgreSQL
- ✅ Frontend-backend integration completa
- ✅ 100% test coverage para OAuth endpoints
- ✅ < 2 minutos para conexión completa

### **Business Metrics:**
- ✅ Usuarios pueden conectar cuentas Meta en < 2 minutos
- ✅ Token refresh automático sin intervención usuario
- ✅ Error rate < 1% en flujo OAuth
- ✅ Uptime 99.9% para endpoints OAuth
- ✅ Soporte multi-tenant funcionando

---

## 🔗 **ENLACES ÚTILES**

### **Meta Developers Documentation:**
- [OAuth Guide](https://developers.facebook.com/docs/facebook-login/guides/advanced/)
- [Access Tokens](https://developers.facebook.com/docs/facebook-login/access-tokens/)
- [Permissions Reference](https://developers.facebook.com/docs/permissions/reference/)
- [Graph API Explorer](https://developers.facebook.com/tools/explorer/)

### **CRM Ventas Documentation:**
- [Sprint 1 Report](../SPRINT1_COMPLETION_REPORT.md)
- [Sprint 2 Report](../SPRINT2_COMPLETION_REPORT.md)
- [Sprints 3-4 Plan](../META_ADS_SPRINTS_3_4_IMPLEMENTATION.md)
- [GitHub Repository](https://github.com/adriangmrraa/crmventas)

---

**Estado:** ✅ **LISTO PARA IMPLEMENTACIÓN**  
**Próximo paso:** Configurar Meta Developers App y variables de entorno  
**Timeline:** 2 días para completar Sprint 3