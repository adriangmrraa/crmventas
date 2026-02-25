# 🚀 PLAN DE IMPLEMENTACIÓN PASO A PASO - SPRINTS 3 & 4

## 📊 RESUMEN EJECUTIVO

**Objetivo:** Completar la implementación de Meta Ads Marketing Hub y HSM Automation con integración OAuth y deployment a producción
**Sprints:** 3 (Integración OAuth) + 4 (Testing & Deployment) = 4 días
**Prerrequisito:** Sprints 1 & 2 completados (backend + frontend básico)
**Estado Deseado:** Sistema completo funcionando en producción

---

## 📅 SPRINT 3: INTEGRACIÓN META OAUTH (2 DÍAS)

### **DÍA 7: CONFIGURACIÓN META DEVELOPERS**

#### **Paso 7.1: Crear App en Meta Developers**
```bash
# 1. Acceder a https://developers.facebook.com/
# 2. Crear nueva App → Business → Otro
# 3. Nombre: "CRM Ventas Marketing Hub"
# 4. Contact email: tu_email@empresa.com
```

#### **Paso 7.2: Configurar Productos Requeridos**
```
Productos a agregar:
1. WhatsApp → Business Management API
2. Facebook Login → OAuth 2.0
3. Marketing API → Ads Management
```

#### **Paso 7.3: Configurar OAuth Settings**
```yaml
# Configuración en Meta Developers Dashboard:
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

#### **Paso 7.4: Solicitar Permisos de API**
```python
# Permisos requeridos (scopes):
REQUIRED_SCOPES = [
    'ads_management',           # Gestionar anuncios
    'business_management',      # Acceder a Business Manager
    'whatsapp_business_management',  # HSM Automation
    'pages_read_engagement',    # Leer páginas
    'read_insights',           # Leer métricas
]

# Enviar para revisión de Meta (puede tomar 1-3 días)
```

#### **Paso 7.5: Configurar Variables de Entorno**
```bash
# Archivo: .env.production
META_APP_ID=tu_app_id_obtenido
META_APP_SECRET=tu_app_secret_obtenido
META_REDIRECT_URI=https://tu-crm.com/crm/auth/meta/callback
META_GRAPH_API_VERSION=v21.0
META_VERIFY_TOKEN=token_aleatorio_para_webhooks
```

### **DÍA 8: IMPLEMENTACIÓN FLUJO OAUTH COMPLETO**

#### **Paso 8.1: Completar Endpoint /crm/auth/meta/url**
```python
# Archivo: orchestrator_service/routes/meta_auth.py
import secrets
from urllib.parse import urlencode

@router.get("/url")
async def get_meta_auth_url(
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
):
    """
    Genera URL OAuth para conectar cuenta Meta.
    """
    app_id = os.getenv("META_APP_ID")
    redirect_uri = os.getenv("META_REDIRECT_URI")
    
    # State para seguridad (tenant_id + nonce)
    state_nonce = secrets.token_urlsafe(16)
    state = f"tenant_{tenant_id}_{state_nonce}"
    
    # Guardar state en session/cache para validación
    await cache.set(f"meta_oauth_state:{state}", {
        "tenant_id": tenant_id,
        "user_id": user_data.user_id,
        "created_at": datetime.utcnow().isoformat()
    }, ex=300)  # Expira en 5 minutos
    
    # Parámetros OAuth
    params = {
        "client_id": app_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "response_type": "code",
        "scope": ",".join(REQUIRED_SCOPES),
        "auth_type": "rerequest",  # Re-pedir permisos si ya autorizado
    }
    
    auth_url = f"https://www.facebook.com/v{GRAPH_API_VERSION}/dialog/oauth?{urlencode(params)}"
    
    return {"url": auth_url, "state": state}
```

#### **Paso 8.2: Implementar Callback Handler**
```python
@router.get("/callback")
async def meta_auth_callback(
    code: str,
    state: str,
    request: Request,
    db=Depends(get_db)
):
    """
    Callback handler OAuth.
    """
    # 1. Validar state
    state_data = await cache.get(f"meta_oauth_state:{state}")
    if not state_data:
        raise HTTPException(status_code=400, detail="State inválido o expirado")
    
    tenant_id = state_data["tenant_id"]
    
    # 2. Intercambiar code por access_token
    app_id = os.getenv("META_APP_ID")
    app_secret = os.getenv("META_APP_SECRET")
    redirect_uri = os.getenv("META_REDIRECT_URI")
    
    token_url = "https://graph.facebook.com/v{}/oauth/access_token".format(
        os.getenv("META_GRAPH_API_VERSION", "21.0")
    )
    
    async with httpx.AsyncClient() as client:
        response = await client.get(token_url, params={
            "client_id": app_id,
            "client_secret": app_secret,
            "redirect_uri": redirect_uri,
            "code": code
        })
        
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Error obteniendo access token")
        
        token_data = response.json()
        access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", 5184000)  # 60 días por defecto
    
    # 3. Obtener long-lived token (60 días)
    exchange_url = f"https://graph.facebook.com/v{GRAPH_API_VERSION}/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": access_token
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(exchange_url, params=params)
        if response.status_code == 200:
            long_lived_data = response.json()
            access_token = long_lived_data.get("access_token")
            expires_in = long_lived_data.get("expires_in", 5184000)
    
    # 4. Obtener user_id y verificar permisos
    debug_url = f"https://graph.facebook.com/v{GRAPH_API_VERSION}/debug_token"
    debug_params = {
        "input_token": access_token,
        "access_token": f"{app_id}|{app_secret}"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(debug_url, params=debug_params)
        if response.status_code == 200:
            debug_data = response.json()["data"]
            user_id = debug_data["user_id"]
            scopes = debug_data.get("scopes", [])
            
            # Verificar que tenemos todos los scopes requeridos
            missing_scopes = [s for s in REQUIRED_SCOPES if s not in scopes]
            if missing_scopes:
                raise HTTPException(
                    status_code=400,
                    detail=f"Faltan permisos: {', '.join(missing_scopes)}"
                )
    
    # 5. Guardar token encriptado en credentials table
    from core.credentials import encrypt_value
    
    encrypted_token = encrypt_value(access_token)
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    
    await db.pool.execute("""
        INSERT INTO credentials (tenant_id, name, value, category, expires_at)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (tenant_id, name) DO UPDATE 
        SET value = $3, expires_at = $5, updated_at = NOW()
    """, tenant_id, "META_USER_LONG_TOKEN", encrypted_token, "meta_ads", expires_at)
    
    # 6. Redirigir a dashboard con success message
    frontend_url = os.getenv("FRONTEND_URL", "https://app.tu-crm.com")
    redirect_url = f"{frontend_url}/crm/marketing?success=connected&user_id={user_id}"
    
    return RedirectResponse(url=redirect_url, status_code=302)
```

#### **Paso 8.3: Implementar Token Refresh Automático**
```python
# Archivo: orchestrator_service/services/marketing/token_service.py
import asyncio
from datetime import datetime, timedelta

class TokenRefreshService:
    def __init__(self):
        self.refresh_queue = asyncio.Queue()
        
    async def start_refresh_daemon(self):
        """Daemon que refresca tokens expirados automáticamente."""
        while True:
            try:
                # Buscar tokens que expiran en < 7 días
                expiring_tokens = await self.get_expiring_tokens(days=7)
                
                for token in expiring_tokens:
                    await self.refresh_token(token)
                    
                # Esperar 1 hora antes de revisar nuevamente
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error en token refresh daemon: {e}")
                await asyncio.sleep(300)  # Reintentar en 5 minutos
    
    async def refresh_token(self, token_data):
        """Refresca un token específico."""
        try:
            # Obtener app access token
            app_token = await self.get_app_access_token()
            
            # Refrescar token
            refresh_url = f"https://graph.facebook.com/v{GRAPH_API_VERSION}/oauth/access_token"
            params = {
                "grant_type": "fb_exchange_token",
                "client_id": META_APP_ID,
                "client_secret": META_APP_SECRET,
                "fb_exchange_token": token_data["decrypted_token"]
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(refresh_url, params=params)
                if response.status_code == 200:
                    new_token_data = response.json()
                    
                    # Actualizar en base de datos
                    await self.update_token_in_db(
                        token_data["tenant_id"],
                        new_token_data["access_token"],
                        new_token_data.get("expires_in", 5184000)
                    )
                    
                    logger.info(f"Token refreshed for tenant {token_data['tenant_id']}")
                    
        except Exception as e:
            logger.error(f"Error refreshing token for tenant {token_data['tenant_id']}: {e}")
            # Notificar al usuario que necesita reconectar
            await self.notify_token_expiry(token_data["tenant_id"])
```

#### **Paso 8.4: Implementar Wizard de Selección de Cuenta**
```python
# Archivo: orchestrator_service/routes/marketing.py
@router.get("/meta-accounts")
@audit_access("list_meta_accounts")
async def get_meta_accounts(
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
):
    """
    Lista cuentas de anuncios disponibles después de OAuth.
    """
    # 1. Obtener token del tenant
    token = await get_tenant_meta_token(tenant_id)
    if not token:
        raise HTTPException(status_code=400, detail="No hay token Meta configurado")
    
    # 2. Obtener Business Managers del usuario
    client = MetaAdsClient(token)
    business_managers = await client.get_business_managers()
    
    # 3. Para cada BM, obtener cuentas de anuncios
    accounts = []
    for bm in business_managers:
        bm_accounts = await client.get_ad_accounts(bm["id"])
        accounts.extend([
            {
                "id": acc["id"],
                "name": acc["name"],
                "type": "AD_ACCOUNT",
                "business_manager_id": bm["id"],
                "business_manager_name": bm["name"],
                "currency": acc.get("currency"),
                "timezone": acc.get("timezone_name"),
                "status": acc.get("account_status"),
                "amount_spent": acc.get("amount_spent"),
                "balance": acc.get("balance"),
            }
            for acc in bm_accounts
        ])
    
    return {"accounts": accounts}

@router.post("/connect")
@audit_access("connect_meta_account")
async def connect_meta_account(
    data: MetaAccountConnect,
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
    db=Depends(get_db)
):
    """
    Conecta una cuenta de Meta específica al tenant.
    """
    # 1. Validar que la cuenta existe y es accesible
    token = await get_tenant_meta_token(tenant_id)
    client = MetaAdsClient(token)
    
    try:
        account_info = await client.get_ad_account(data.account_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cuenta no accesible: {str(e)}")
    
    # 2. Guardar relación tenant → cuenta Meta
    await db.pool.execute("""
        INSERT INTO tenant_meta_accounts (tenant_id, account_id, account_name, connected_at)
        VALUES ($1, $2, $3, NOW())
        ON CONFLICT (tenant_id, account_id) DO UPDATE
        SET account_name = $3, connected_at = NOW()
    """, tenant_id, data.account_id, account_info["name"])
    
    # 3. Sincronizar campañas iniciales
    asyncio.create_task(sync_initial_campaigns(tenant_id, data.account_id))
    
    return {
        "status": "connected",
        "account_id": data.account_id,
        "account_name": account_info["name"],
        "message": "Cuenta conectada exitosamente. Sincronizando campañas..."
    }
```

#### **Paso 8.5: Testing OAuth Flow**
```python
# Archivo: tests/integration/test_meta_oauth.py
import pytest
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_oauth_flow_complete():
    """Test flujo completo OAuth."""
    
    # Mock de Meta API responses
    with patch('httpx.AsyncClient.get') as mock_get:
        # Mock token exchange
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "access_token": "test_access_token",
            "expires_in": 5184000
        }
        
        # Mock debug token
        mock_get.return_value.json.return_value = {
            "data": {
                "user_id": "123456789",
                "scopes": ["ads_management", "business_management"],
                "is_valid": True
            }
        }
        
        # Simular callback
        response = await client.get(
            "/crm/auth/meta/callback",
            params={"code": "test_code", "state": "test_state"}
        )
        
        assert response.status_code == 302  # Redirect
        assert "success=connected" in response.headers["location"]
```

---

## 📅 SPRINT 4: TESTING Y DEPLOYMENT (2 DÍAS)

### **DÍA 9: TESTING INTEGRAL**

#### **Paso 9.1: Testing End-to-End Completo**
```python
# Archivo: tests/e2e/test_marketing_flow.py
import pytest
from playwright.sync_api import Page, expect

def test_complete_marketing_flow(page: Page):
    """Test E2E completo: login → connect meta → view dashboard."""
    
    # 1. Login
    page.goto("https://app.tu-crm.com/login")
    page.fill('input[name="email"]', "ceo@example.com")
    page.fill('input[name="password"]', "password123")
    page.click('button[type="submit"]')
    
    # 2. Navegar a Marketing Hub
    page.click('[data-testid="sidebar-marketing"]')
    expect(page).to_have_url("https://app.tu-crm.com/crm/marketing")
    
    # 3. Conectar cuenta Meta (simulado)
    page.click('button:has-text("Conectar Meta Ads")')
    page.click('button:has-text("Continuar con Meta")')
    
    # Simular OAuth callback
    page.goto("https://app.tu-crm.com/crm/marketing?success=connected&user_id=123")
    
    # 4. Seleccionar cuenta
    page.click('[data-testid="account-123456789"]')
    page.click('button:has-text("Conectar cuenta")')
    
    # 5. Verificar dashboard carga datos
    expect(page.locator('[data-testid="marketing-stats"]')).to_be_visible()
    expect(page.locator('text="Leads"')).to_be_visible()
    expect(page.locator('text="ROI"')).to_be_visible()
    
    # 6. Navegar a HSM Automation
    page.click('[data-testid="sidebar-hsm"]')
    expect(page).to_have_url("https://app.tu-crm.com/crm/hsm")
    
    # 7. Crear regla de automatización
    page.click('button:has-text("Nueva regla")')
    page.fill('input[name="rule_name"]', "Follow-up Leads 24h")
    page.select_option('select[name="trigger_type"]', "lead_followup")
    page.click('button:has-text("Guardar")')
    
    expect(page.locator('text="Regla creada exitosamente"')).to_be_visible()
```

#### **Paso 9.2: Performance Testing**
```python
# Archivo: tests/performance/test_marketing_performance.py
import asyncio
import time
import statistics
from typing import List

async def test_marketing_endpoint_performance():
    """Test de performance para endpoints de marketing."""
    
    endpoint = "/crm/marketing/stats"
    num_requests = 100
    latencies: List[float] = []
    
    headers = {
        "Authorization": "Bearer test_token",
        "X-Admin-Token": "test_admin"
    }
    
    for i in range(num_requests):
        start_time = time.time()
        
        response = await client.get(endpoint, headers=headers)
        
        end_time = time.time()
        latency = (end_time - start_time) * 1000  # ms
        latencies.append(latency)
        
        assert response.status_code == 200
    
    # Análisis de resultados
    avg_latency = statistics.mean(latencies)
    p95_latency = statistics.quantiles(latencies, n=20)[18]  # Percentil 95
    max_latency = max(latencies)
    
    print(f"Performance Results for {endpoint}:")
    print(f"  Requests: {num_requests}")
    print(f"  Avg Latency: {avg_latency:.2f}ms")
    print(f"  P95 Latency: {p95_latency:.2f}ms")
    print(f"  Max Latency: {max_latency:.2f}ms")
    
    # Assert performance requirements
    assert avg_latency < 500, f"Avg latency too high: {avg_latency}ms"
    assert p95_latency < 1000, f"P95 latency too high: {p95_latency}ms"
```

#### **Paso 9.3: Load Testing con k6**
```javascript
// Archivo: load_tests/marketing_load_test.js
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

export const errorRate = new Rate('errors');

export const options = {
  stages: [
    { duration: '1m', target: 50 },   // Ramp up to 50 users
    { duration: '3m', target: 50 },   // Stay at 50 users
    { duration: '1m', target: 100 },  // Ramp up to 100 users
    { duration: '3m', target: 100 },  // Stay at 100 users
    { duration: '1m', target: 0 },    // Ramp down to 0
  ],
  thresholds: {
    http_req_duration: ['p(95)<1000'], // 95% of requests < 1s
    errors: ['rate<0.01'],             // Error rate < 1%
  },
};

export default function () {
  const headers = {
    'Authorization': 'Bearer test_token',
    'X-Admin-Token': 'test_admin_token',
  };

  // Test marketing stats endpoint
  const statsRes = http.get('http://localhost:8000/crm/marketing/stats', { headers });
  
  check(statsRes, {
    'stats status is 200': (r) => r.status === 200,
    'stats response time < 500ms': (r) => r.timings.duration < 500,
  }) || errorRate.add(1);

  // Test HSM templates endpoint
  const templatesRes = http.get('http://localhost:8000/crm/marketing/hsm/templates', { headers });
  
  check(templatesRes, {
    'templates status is 200': (r) => r.status === 200,
  }) || errorRate.add(1);

  sleep(1); // Wait 1 second between iterations
}
```

#### **Paso 9.4: Security Testing**
```python
# Archivo: tests/security/test_marketing_security.py
import pytest
from security_headers import analyze_headers

def test_marketing_endpoints_security_headers():
    """Verificar headers de seguridad en endpoints de marketing."""
    
    endpoints = [
        "/crm/marketing/stats",
        "/crm/marketing/stats/roi",
        "/crm/marketing/token-status",
        "/crm/auth/meta/url",
    ]
    
    headers = {
        "Authorization": "Bearer test_token",
        "X-Admin-Token": "test_admin"
    }
    
    for endpoint in endpoints:
        response = client.get(endpoint, headers=headers)
        
        # Verificar headers de seguridad
        security_analysis = analyze_headers(response.headers)
        
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"
        
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        
        assert "Content-Security-Policy" in response.headers
        assert "default-src 'self'" in response.headers["Content-Security-Policy"]
        
        print(f"Security headers OK for {endpoint}")

def test_multi_tenant_isolation():
    """Verificar que usuarios no pueden acceder datos de otros tenants."""
    
    # User 1 (tenant 1)
    headers1 = {
        "Authorization": "Bearer user1_token",
        "X-Admin-Token": "admin1",
        "X-Tenant-ID": "1"
    }
    
    # User 2 (tenant 2) - intentando acceder datos de tenant 1
    headers2 = {
        "Authorization": "Bearer user2_token", 
        "X-Admin-Token": "admin2",
        "X-Tenant-ID": "1"  # Intentando spoof tenant 1
    }
    
    # User 1 crea datos
    response1 = client.post("/crm/marketing/connect", 
        json={"account_id": "act_123", "account_name": "Test Account"},
        headers=headers1
    )
    assert response1.status_code == 200
    
    # User 2 intenta acceder esos datos
    response2 = client.get("/crm/marketing/stats", headers=headers2)
    
    # Debería ver datos vacíos o error (no datos de tenant 1)
    assert response2.status_code in [200, 403, 404]
    if response2.status_code == 200:
        data = response2.json()
        # Verificar que no contiene datos de tenant 1
        assert data.get("leads", 0) == 0
```

### **DÍA 10: DEPLOYMENT Y MONITORING**

#### **Paso 10.1: Preparar Deployment a Producción**
```bash
# 1. Actualizar docker-compose.production.yml
version: '3.8'
services:
  orchestrator_service:
    build: ./orchestrator_service
    environment:
      - META_APP_ID=${META_APP_ID}
      - META_APP_SECRET=${META_APP_SECRET}
      - META_REDIRECT_URI=${META_REDIRECT_URI}
      - META_GRAPH_API_VERSION=${META_GRAPH_API_VERSION}
    # ... resto de configuración

# 2. Crear script de deployment
#!/bin/bash
# deploy_marketing.sh

echo "🚀 Iniciando deployment de Marketing Hub..."

# 1. Pull latest code
git pull origin main

# 2. Build frontend
cd frontend_react
npm run build
cd ..

# 3. Build backend
cd orchestrator_service
docker build -t crmventas-orchestrator:latest .
cd ..

# 4. Run database migrations
docker-compose -f docker-compose.production.yml run --rm orchestrator_service \
  python -c "from db import run_migrations; import asyncio; asyncio.run(run_migrations())"

# 5. Restart services
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml up -d

echo "✅ Deployment completado!"
```

#### **Paso 10.2: Configurar Monitoring**
```python
# Archivo: orchestrator_service/monitoring/marketing_metrics.py
from prometheus_client import Counter, Gauge, Histogram
import time

# Métricas para marketing
MARKETING_REQUESTS = Counter(
    'marketing_requests_total',
    'Total marketing API requests',
    ['endpoint', 'method', 'status']
)

MARKETING_REQUEST_DURATION = Histogram(
    'marketing_request_duration_seconds',
    'Marketing request duration',
    ['endpoint']
)

META_API_CALLS = Counter(
    'meta_api_calls_total',
    'Total Meta Graph API calls',
    ['endpoint', 'status']
)

HSM_MESSAGES_SENT = Counter(
    'hsm_messages_sent_total',
    'Total HSM messages sent',
    ['template', 'status']
)

CAMPAIGN_SYNC_DURATION = Gauge(
    'campaign_sync_duration_seconds',
    'Duration of campaign sync from Meta API'
)

# Middleware para tracking
@app.middleware("http")
async def track_marketing_metrics(request: Request, call_next):
    start_time = time.time()
    
    # Solo trackear endpoints de marketing
    if request.url.path.startswith("/crm/marketing") or request.url.path.startswith("/crm/auth/meta"):
        endpoint = request.url.path
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        
        # Registrar métricas
        MARKETING_REQUESTS.labels(
            endpoint=endpoint,
            method=request.method,
            status=response.status_code
        ).inc()
        
        MARKETING_REQUEST_DURATION.labels(endpoint=endpoint).observe(duration)
        
        return response
    
    return await call_next(request)
```

#### **Paso 10.3: Configurar Alertas**
```yaml
# Archivo: monitoring/alerts.yml
groups:
  - name: marketing_alerts
    rules:
      - alert: HighMarketingLatency
        expr: histogram_quantile(0.95, rate(marketing_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency in marketing endpoints"
          description: "95th percentile latency > 1s for marketing endpoints"
      
      - alert: MetaAPIFailures
        expr: rate(meta_api_calls_total{status=~"4..|5.."}[5m]) > 0.1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High Meta API failure rate"
          description: "More than 10% of Meta API calls are failing"
      
      - alert: TokenExpiryWarning
        expr: time() - credentials_expires_at{name="META_USER_LONG_TOKEN"} < 604800
        for: 0m
        labels:
          severity: warning
        annotations:
          summary: "Meta token expiring soon"
          description: "Meta OAuth token expires in less than 7 days"
      
      - alert: HSMMessageFailures
        expr: rate(hsm_messages_sent_total{status="FAILED"}[15m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High HSM message failure rate"
          description: "More than 5% of HSM messages are failing"
```

#### **Paso 10.4: Configurar Logging Centralizado**
```python
# Archivo: orchestrator_service/logging/marketing_logger.py
import logging
import json
from datetime import datetime

class MarketingLogger:
    def __init__(self):
        self.logger = logging.getLogger("marketing")
        
    def log_oauth_connection(self, tenant_id: int, user_id: str, success: bool, error: str = None):
        """Log de conexión OAuth."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "oauth_connection",
            "tenant_id": tenant_id,
            "user_id": user_id,
            "success": success,
            "error": error,
            "level": "INFO" if success else "ERROR"
        }
        
        self.logger.info(json.dumps(log_entry))
    
    def log_campaign_sync(self, tenant_id: int, account_id: str, campaigns_synced: int, duration: float):
        """Log de sincronización de campañas."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "campaign_sync",
            "tenant_id": tenant_id,
            "account_id": account_id,
            "campaigns_synced": campaigns_synced,
            "duration_seconds": duration,
            "level": "INFO"
        }
        
        self.logger.info(json.dumps(log_entry))
    
    def log_hsm_message(self, tenant_id: int, rule_id: str, template_id: str, status: str, error: str = None):
        """Log de envío de mensaje HSM."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "hsm_message",
            "tenant_id": tenant_id,
            "rule_id": rule_id,
            "template_id": template_id,
            "status": status,
            "error": error,
            "level": "INFO" if status == "SENT" else "ERROR"
        }
        
        self.logger.info(json.dumps(log_entry))
```

#### **Paso 10.5: Rollback Plan**
```bash
#!/bin/bash
# rollback_marketing.sh

echo "🔄 Iniciando rollback de Marketing Hub..."

# 1. Revertir migración de base de datos
BACKUP_FILE="/backups/pre_marketing_migration.dump"
if [ -f "$BACKUP_FILE" ]; then
    echo "Restaurando backup de base de datos..."
    pg_restore -h localhost -U postgres -d crmventas --clean --if-exists "$BACKUP_FILE"
else
    echo "⚠️  No hay backup disponible, ejecutando migración inversa..."
    psql -h localhost -U postgres -d crmventas -f migrations/rollback_marketing.sql
fi

# 2. Revertir cambios de frontend
cd frontend_react
git checkout HEAD~1 -- src/views/marketing/ src/components/marketing/ src/App.tsx src/components/Sidebar.tsx
npm run build
cd ..

# 3. Revertir cambios de backend
cd orchestrator_service
git checkout HEAD~1 -- routes/marketing.py routes/meta_auth.py services/marketing/ main.py
cd ..

# 4. Restart services
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml up -d

echo "✅ Rollback completado!"
```

```sql
-- Archivo: migrations/rollback_marketing.sql
BEGIN;

-- Eliminar tablas de marketing (si existen)
DROP TABLE IF EXISTS automation_logs CASCADE;
DROP TABLE IF EXISTS automation_rules CASCADE;
DROP TABLE IF EXISTS meta_templates CASCADE;
DROP TABLE IF EXISTS meta_ads_insights CASCADE;
DROP TABLE IF EXISTS meta_ads_campaigns CASCADE;

-- Eliminar campos de leads
ALTER TABLE leads 
DROP COLUMN IF EXISTS lead_source,
DROP COLUMN IF EXISTS meta_campaign_id,
DROP COLUMN IF EXISTS meta_ad_id,
DROP COLUMN IF EXISTS meta_ad_headline,
DROP COLUMN IF EXISTS meta_ad_body,
DROP COLUMN IF EXISTS external_ids;

-- Eliminar índices
DROP INDEX IF EXISTS idx_leads_lead_source;
DROP INDEX IF EXISTS idx_leads_meta_campaign;
DROP INDEX IF EXISTS idx_leads_meta_ad;
DROP INDEX IF EXISTS idx_leads_external_ids;

COMMIT;
```

---

## 📋 CHECKLIST COMPLETO SPRINTS 3 & 4

### **SPRINT 3 - INTEGRACIÓN OAUTH (Días 7-8)**

#### **Día 7 - Configuración Meta Developers:**
- [ ] Crear App en Meta Developers
- [ ] Configurar productos (WhatsApp, Facebook Login, Marketing API)
- [ ] Configurar OAuth redirect URIs
- [ ] Solicitar permisos de API (ads_management, business_management, etc.)
- [ ] Configurar variables de entorno de producción

#### **Día 8 - Implementación Flujo OAuth Completo:**
- [ ] Completar endpoint `/crm/auth/meta/url` con state validation
- [ ] Implementar callback handler `/crm/auth/meta/callback`
- [ ] Implementar token refresh automático
- [ ] Crear wizard de selección de cuenta
- [ ] Implementar endpoints `GET /crm/marketing/meta-accounts`
- [ ] Implementar `POST /crm/marketing/connect`
- [ ] Testing OAuth flow completo

### **SPRINT 4 - TESTING & DEPLOYMENT (Días 9-10)**

#### **Día 9 - Testing Integral:**
- [ ] Testing end-to-end con Playwright
- [ ] Performance testing de endpoints
- [ ] Load testing con k6 (50 → 100 usuarios)
- [ ] Security testing (headers, multi-tenant isolation)
- [ ] Integration testing con Meta Sandbox API

#### **Día 10 - Deployment y Monitoring:**
- [ ] Preparar docker-compose.production.yml
- [ ] Crear script de deployment
- [ ] Configurar monitoring con Prometheus
- [ ] Configurar alertas (latencia, fallos, tokens)
- [ ] Configurar logging centralizado
- [ ] Crear rollback plan
- [ ] Ejecutar deployment a producción

---

## 🚨 RIESGOS Y MITIGACIONES SPRINTS 3 & 4

### **Riesgos OAuth:**
1. **Rechazo de permisos por Meta:**
   - **Mitigación:** Solicitar solo permisos esenciales, documentar uso claro
   - **Fallback:** Usar Meta Sandbox para desarrollo

2. **Tokens expiran sin refresh automático:**
   - **Mitigación:** Implementar daemon de refresh + notificaciones
   - **Alertas:** Monitorear expiración < 7 días

3. **Rate limiting de Graph API:**
   - **Mitigación:** Implementar caching + exponential backoff
   - **Monitoring:** Alertas para high error rates

### **Riesgos Deployment:**
1. **Migración falla en producción:**
   - **Mitigación:** Backup completo pre-deployment
   - **Rollback:** Script de rollback probado

2. **Performance issues en producción:**
   - **Mitigación:** Load testing previo + auto-scaling config
   - **Monitoring:** Alertas tempranas para alta latencia

3. **Integración con sistemas existentes:**
   - **Mitigación:** Feature flags + rollout gradual
   - **Testing:** Staging environment idéntico a producción

---

## 🔧 HERRAMIENTAS Y COMANDOS SPRINTS 3 & 4

### **Meta Developers:**
```bash
# Verificar configuración OAuth
curl -X GET "https://graph.facebook.com/v21.0/oauth/access_token?\
  client_id=APP_ID&\
  client_secret=APP_SECRET&\
  grant_type=client_credentials"

# Testear permisos
curl -X GET "https://graph.facebook.com/v21.0/debug_token?\
  input_token=USER_TOKEN&\
  access_token=APP_ID|APP_SECRET"
```

### **Testing:**
```bash
# Ejecutar tests E2E
npx playwright test tests/e2e/marketing_flow.spec.ts

# Load testing con k6
k6 run load_tests/marketing_load_test.js

# Performance testing
python -m pytest tests/performance/test_marketing_performance.py -v
```

### **Deployment:**
```bash
# Deployment completo
./deploy_marketing.sh

# Verificar deployment
curl -H "Authorization: Bearer token" https://tu-crm.com/crm/marketing/stats

# Monitorear logs
docker-compose -f docker-compose.production.yml logs -f orchestrator_service

# Rollback si es necesario
./rollback_marketing.sh
```

### **Monitoring:**
```bash
# Ver métricas Prometheus
curl http://localhost:9090/api/v1/query?query=marketing_requests_total

# Ver logs estructurados
docker-compose -f docker-compose.production.yml exec orchestrator_service \
  tail -f /var/log/marketing.json
```

---

## 📞 SOPORTE POST-DEPLOYMENT

### **Problemas Comunes y Soluciones:**

1. **"Error 400: redirect_uri mismatch"**
   ```bash
   # Verificar redirect_uri en Meta Developers Dashboard
   # Debe coincidir exactamente con META_REDIRECT_URI en .env
   ```

2. **"Token expired or invalid"**
   ```bash
   # Verificar refresh daemon está corriendo
   docker-compose -f docker-compose.production.yml ps | grep token_refresh
   
   # Forzar refresh manual
   curl -X POST https://tu-crm.com/crm/auth/meta/refresh-tokens
   ```

3. **"HSM templates not approved"**
   ```bash
   # Verificar estado en Meta Business Suite
   # Revisar rejected_reason en tabla meta_templates
   psql -h localhost -U postgres -d crmventas -c \
     "SELECT name, status, rejected_reason FROM meta_templates WHERE status = 'REJECTED';"
   ```

4. **"High latency in marketing dashboard"**
   ```bash
   # Verificar índices de base de datos
   psql -h localhost -U postgres -d crmventas -c "\di idx_meta_*"
   
   # Verificar caching
   redis-cli info | grep keyspace_hits
   ```

### **Procedimiento de Escalación:**
```
Nivel 1: Monitoreo automático (alertas)
  ↓
Nivel 2: Scripts de recuperación automática
  ↓  
Nivel 3: Intervención manual (soporte)
  ↓
Nivel 4: Rollback a versión estable
```

---

## 🎯 CRITERIOS DE ACEPTACIÓN SPRINTS 3 & 4

### **Sprint 3 - OAuth:**
- ✅ Usuario puede conectar cuenta Meta en < 2 minutos
- ✅ Token se refresca automáticamente antes de expirar
- ✅ Wizard de selección de cuenta funciona correctamente
- ✅ Permisos requeridos están aprobados por Meta
- ✅ Multi-tenant isolation mantenido en OAuth flow

### **Sprint 4 - Deployment:**
- ✅ Deployment a producción sin downtime
- ✅ Performance: P95 latency < 1s bajo carga de 100 usuarios
- ✅ Disponibilidad: 99.9% uptime primera semana
- ✅ Monitoring: Alertas funcionando para problemas críticos
- ✅ Rollback: Puede revertirse en < 15 minutos si es necesario

### **Integración Completa:**
- ✅ Marketing Hub muestra datos reales de campañas Meta
- ✅ HSM Automation envía mensajes automáticamente
- ✅ ROI calculation funciona con datos reales
- ✅ Sistema escala automáticamente bajo carga
- ✅ Seguridad Nexus v7.7.1 mantenida en todas las capas

---

## 🚀 PRÓXIMOS PASOS POST-IMPLEMENTACIÓN

### **Semana 1 Post-Deployment:**
1. **Monitoring intensivo** - Revisar métricas cada 4 horas
2. **Soporte usuario** - Responder preguntas y issues
3. **Performance tuning** - Optimizar basado en datos reales
4. **Bug fixing** - Corregir issues reportados por usuarios

### **Mes 1:**
1. **Training usuarios** - Webinars y documentación
2. **Feedback collection** - Encuestas y entrevistas
3. **Optimización continua** - Mejoras basadas en uso real
4. **Plan de expansión** - Nuevas features solicitadas

### **Roadmap Futuro:**
1. **Integración Google Ads** - Multi-platform marketing
2. **Advanced analytics** - Machine learning para optimización
3. **Multi-channel automation** - Email + SMS + WhatsApp
4. **Predictive ROI** - Forecasting basado en historical data

---

**Documentación creada por:** DevFusa  
**Fecha:** 25 de Febrero 2026  
**Repositorio:** CRM Ventas  
**Estado:** Plan completo Sprints 3 & 4 listo  
**Tiempo estimado:** 4 días (Sprints 3 & 4)  
**Total proyecto:** 10 días (Sprints 1-4)

*"Implementación completa de Meta Ads Marketing Hub y HSM Automation en CRM Ventas."*