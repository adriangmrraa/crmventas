# 🔧 META ADS BACKEND IMPLEMENTATION - CRM VENTAS

## 📊 RESUMEN TÉCNICO

**Objetivo:** Implementar backend completo para Meta Ads Marketing Hub y HSM Automation en CRM Ventas, migrando y adaptando el código de ClinicForge.

**Código Fuente ClinicForge:**
- `orchestrator_service/services/meta_ads_service.py`
- `orchestrator_service/services/marketing_service.py`
- `orchestrator_service/services/automation_service.py`
- `orchestrator_service/routes/marketing.py`
- `orchestrator_service/routes/meta_auth.py`

---

## 🏗️ ARQUITECTURA BACKEND

### **1. SERVICIOS PRINCIPALES**

#### **1.1. MetaAdsService (Cliente Graph API)**
```python
# Ubicación: orchestrator_service/services/meta_ads_service.py
# Responsabilidad: Comunicación con Meta Graph API

class MetaAdsClient:
    async def get_ad_accounts(self, access_token: str) -> List[Dict]:
        """Obtiene cuentas de anuncios del Business Manager."""
    
    async def get_campaigns_with_insights(self, ad_account_id: str, access_token: str) -> List[Dict]:
        """Obtiene campañas con métricas de rendimiento."""
    
    async def get_ad_details(self, ad_id: str, access_token: str) -> Dict:
        """Obtiene detalles específicos de un anuncio."""
    
    async def get_ads_insights(self, ad_account_id: str, access_token: str, time_range: Dict) -> List[Dict]:
        """Obtiene insights de anuncios para un período."""
```

#### **1.2. MarketingService (Lógica de Negocio)**
```python
# Ubicación: orchestrator_service/services/marketing_service.py
# Responsabilidad: Cálculo de ROI y estadísticas

class MarketingService:
    async def get_roi_stats(self, tenant_id: int, time_range: str) -> Dict:
        """Calcula ROI real basado en leads → oportunidades → ventas."""
    
    async def get_campaign_stats(self, tenant_id: int, access_token: str) -> List[Dict]:
        """Obtiene estadísticas de campañas desde Meta API."""
    
    async def get_token_status(self, tenant_id: int) -> Dict:
        """Verifica estado de conexión Meta OAuth."""
    
    async def calculate_cpa(self, spend: float, leads: int) -> float:
        """Calcula Costo Por Adquisición."""
```

#### **1.3. AutomationService (HSM Automation)**
```python
# Ubicación: orchestrator_service/services/automation_service.py
# Responsabilidad: Automatización WhatsApp HSM

class AutomationService:
    async def send_hsm_message(self, template_name: str, phone: str, parameters: Dict) -> bool:
        """Envía mensaje HSM de WhatsApp."""
    
    async def check_template_approval(self, template_name: str) -> bool:
        """Verifica si template está aprobado por Meta."""
    
    async def log_automation(self, tenant_id: int, lead_id: int, trigger: str, status: str):
        """Registra log de automatización."""
```

### **2. ENDPOINTS API**

#### **2.1. Marketing Endpoints (`/crm/marketing/*`)**
```python
# Basado en: clinicforge/orchestrator_service/routes/marketing.py
# Adaptar: /admin/marketing/ → /crm/marketing/

@router.get("/stats")
@audit_access("view_marketing_stats")
@limiter.limit("100/minute")
async def get_marketing_stats(
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
    time_range: str = "7d"
):
    """
    Dashboard principal de marketing.
    Retorna: leads, oportunidades, ingresos, inversión, ROI.
    """

@router.get("/stats/roi")
@audit_access("view_roi_details")
async def get_roi_details(
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
):
    """
    Detalles específicos de ROI.
    Incluye: CPA, LTV, ROAS, attribution window.
    """

@router.get("/token-status")
@audit_access("check_token_status")
async def get_token_status(
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
):
    """
    Verifica estado de conexión Meta OAuth.
    Retorna: connected, expired, missing.
    """

@router.get("/meta-portfolios")
@audit_access("list_meta_portfolios")
async def get_meta_portfolios(
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
):
    """
    Lista Business Managers conectados.
    """

@router.get("/meta-accounts")
@audit_access("list_meta_accounts")
async def get_meta_accounts(
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
    portfolio_id: Optional[str] = None
):
    """
    Lista cuentas de anuncios de Meta.
    """

@router.post("/connect")
@audit_access("connect_meta_account")
async def connect_meta_account(
    data: Dict,
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
):
    """
    Conecta cuenta de Meta a tenant.
    """

@router.get("/automation-logs")
@audit_access("view_automation_logs")
async def get_automation_logs(
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
    limit: int = 100,
    offset: int = 0
):
    """
    Obtiene logs de automatización HSM.
    """
```

#### **2.2. OAuth Endpoints (`/crm/auth/meta/*`)**
```python
# Basado en: clinicforge/orchestrator_service/routes/meta_auth.py

@router.get("/url")
async def get_meta_auth_url(
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
):
    """
    Genera URL OAuth para conectar cuenta Meta.
    Incluye state=tenant_{tenant_id} para seguridad.
    """

@router.get("/callback")
async def meta_auth_callback(
    code: str,
    state: str,
    request: Request
):
    """
    Callback handler OAuth.
    Intercambia code por access_token (long-lived).
    Guarda token en credentials table.
    Redirige a /crm/marketing?success=connected
    """

@router.post("/disconnect")
@audit_access("disconnect_meta")
async def disconnect_meta(
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id)
):
    """
    Desconecta cuenta Meta del tenant.
    Elimina token de credentials table.
    """
```

### **3. ADAPTACIONES PARA CRM VENTAS**

#### **3.1. Terminología a Cambiar:**
```python
# ClinicForge → CRM Ventas
"patients" → "leads"
"appointments" → "opportunities"
"dental revenue" → "sales revenue"
"clinic" → "account" o "business"
"professional" → "seller" o "closer"
"acquisition_source" → "lead_source"
```

#### **3.2. Fórmulas de ROI Adaptadas:**
```python
# ROI para CRM Ventas (vs ClinicForge dental)
def calculate_roi_crm(tenant_id: int, time_range: str) -> Dict:
    """
    Fórmula adaptada para ventas:
    1. Leads atribuidos a Meta Ads
    2. Oportunidades generadas
    3. Ventas cerradas (ingresos)
    4. Inversión en Meta Ads
    5. ROI = (ingresos - inversión) / inversión * 100
    """
    
    # 1. Leads de Meta Ads
    meta_leads = await db.pool.fetchval("""
        SELECT COUNT(*) FROM leads 
        WHERE tenant_id = $1 AND lead_source = 'META_ADS'
        AND created_at >= NOW() - $2::interval
    """, tenant_id, time_range)
    
    # 2. Oportunidades generadas
    opportunities = await db.pool.fetchval("""
        SELECT COUNT(DISTINCT o.id) 
        FROM opportunities o
        JOIN leads l ON o.lead_id = l.id
        WHERE l.tenant_id = $1 AND l.lead_source = 'META_ADS'
        AND o.created_at >= NOW() - $2::interval
    """, tenant_id, time_range)
    
    # 3. Ventas cerradas (ingresos)
    sales_revenue = await db.pool.fetchval("""
        SELECT COALESCE(SUM(amount), 0)
        FROM sales_transactions t
        JOIN leads l ON t.lead_id = l.id
        WHERE l.tenant_id = $1 AND l.lead_source = 'META_ADS'
        AND t.status = 'completed'
        AND t.created_at >= NOW() - $2::interval
    """, tenant_id, time_range)
    
    # 4. Inversión (desde Meta API)
    marketing_spend = await get_meta_spend(tenant_id, time_range)
    
    # 5. Cálculos
    cpa = marketing_spend / meta_leads if meta_leads > 0 else 0
    roi = ((sales_revenue - marketing_spend) / marketing_spend * 100) if marketing_spend > 0 else 0
    
    return {
        "leads": meta_leads,
        "opportunities": opportunities,
        "sales_revenue": sales_revenue,
        "marketing_spend": marketing_spend,
        "cpa": cpa,
        "roi_percentage": roi
    }
```

#### **3.3. HSM Automation para CRM:**
```python
# Triggers adaptados para ventas (vs recordatorios dentales)
TRIGGERS = {
    'lead_followup': {
        'condition': "lead.status == 'new' AND hours_since_creation > 24",
        'action': "send_whatsapp_template('lead_followup', lead.phone)",
        'description': "Seguimiento automático 24h después de crear lead"
    },
    'opportunity_reminder': {
        'condition': "opportunity.status == 'pending' AND hours_before_deadline < 2",
        'action': "send_whatsapp_template('opportunity_reminder', lead.phone)",
        'description': "Recordatorio 2h antes de deadline de oportunidad"
    },
    'post_sale_feedback': {
        'condition': "sale.completed_at IS NOT NULL AND days_since_sale == 7",
        'action': "send_whatsapp_template('post_sale_feedback', lead.phone)",
        'description': "Solicitud de feedback 7 días después de venta"
    },
    'abandoned_cart': {
        'condition': "cart.last_activity > 1 AND hours_since_last_activity > 48",
        'action': "send_whatsapp_template('abandoned_cart', lead.phone)",
        'description': "Recuperación de carrito abandonado (48h)"
    }
}
```

### **4. MIGRACIÓN PASO A PASO**

#### **Paso 1: Copiar Servicios de ClinicForge**
```bash
# Desde directorio de CRM Ventas
cp ../clinicforge/orchestrator_service/services/meta_ads_service.py orchestrator_service/services/
cp ../clinicforge/orchestrator_service/services/marketing_service.py orchestrator_service/services/
cp ../clinicforge/orchestrator_service/services/automation_service.py orchestrator_service/services/
```

#### **Paso 2: Adaptar Terminología**
```python
# En marketing_service.py - Reemplazar globalmente:
# patients → leads
# appointments → opportunities
# dental → sales
# clinic → account
# acquisition_source → lead_source
```

#### **Paso 3: Crear Routes Marketing**
```python
# Crear orchestrator_service/routes/marketing.py
# Basado en clinicforge/orchestrator_service/routes/marketing.py
# Cambiar:
# - /admin/marketing/ → /crm/marketing/
# - Importar servicios adaptados
# - Actualizar fórmulas ROI
```

#### **Paso 4: Crear Routes Meta Auth**
```python
# Crear orchestrator_service/routes/meta_auth.py
# Basado en clinicforge/orchestrator_service/routes/meta_auth.py
# Cambiar:
# - /auth/meta/ → /crm/auth/meta/
# - Redirección a /crm/marketing?success=connected
```

#### **Paso 5: Integrar en Main.py**
```python
# En orchestrator_service/main.py
from routes.marketing import router as marketing_router
from routes.meta_auth import router as meta_auth_router

# Agregar routers
app.include_router(marketing_router, prefix="/crm/marketing", tags=["Marketing"])
app.include_router(meta_auth_router, prefix="/crm/auth/meta", tags=["Meta OAuth"])
```

### **5. VARIABLES DE ENTORNO REQUERIDAS**

```bash
# .env del backend CRM Ventas
META_APP_ID=tu_meta_app_id
META_APP_SECRET=tu_meta_app_secret
META_REDIRECT_URI=https://tu-crm.com/crm/auth/meta/callback
META_GRAPH_API_VERSION=v21.0

# Credenciales encriptadas (usar generate_env_vars.py)
JWT_SECRET_KEY=...
ADMIN_TOKEN=...
CREDENTIALS_FERNET_KEY=...

# WhatsApp Business API (para HSM)
YCLOUD_API_KEY=...
YCLOUD_WEBHOOK_SECRET=...
YCLOUD_WHATSAPP_NUMBER=5491100000000
```

### **6. TESTING BACKEND**

#### **6.1. Unit Testing:**
```python
# tests/services/test_meta_ads_service.py
import pytest
from services.meta_ads_service import MetaAdsClient

@pytest.mark.asyncio
async def test_get_ad_accounts():
    """Test obtención de cuentas de anuncios."""
    client = MetaAdsClient()
    # Mock de access_token
    accounts = await client.get_ad_accounts("mock_token")
    assert isinstance(accounts, list)

@pytest.mark.asyncio  
async def test_calculate_roi_crm():
    """Test cálculo de ROI para CRM."""
    from services.marketing_service import MarketingService
    service = MarketingService()
    stats = await service.get_roi_stats(tenant_id=1, time_range="7d")
    assert "roi_percentage" in stats
    assert "cpa" in stats
```

#### **6.2. Integration Testing:**
```python
# tests/routes/test_marketing.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_marketing_stats_endpoint():
    """Test endpoint /crm/marketing/stats."""
    # Mock authentication
    headers = {"Authorization": "Bearer mock_token", "X-Admin-Token": "mock_admin"}
    response = client.get("/crm/marketing/stats", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "leads" in data
    assert "opportunities" in data
```

#### **6.3. OAuth Flow Testing:**
```python
# test_oauth_flow.py
import asyncio
from routes.meta_auth import get_meta_auth_url, meta_auth_callback

async def test_oauth_flow():
    """Test flujo completo OAuth."""
    # 1. Generar URL
    auth_url = await get_meta_auth_url(tenant_id=1)
    assert "facebook.com" in auth_url
    assert "state=tenant_1" in auth_url
    
    # 2. Simular callback (mock)
    # ... código de testing
```

### **7. SEGURIDAD BACKEND**

#### **7.1. Validación Multi-Tenant:**
```python
# Todas las queries deben incluir tenant_id
async def get_leads(tenant_id: int):
    leads = await db.pool.fetch("""
        SELECT * FROM leads 
        WHERE tenant_id = $1
        ORDER BY created_at DESC
    """, tenant_id)
    return leads
```

#### **7.2. Rate Limiting:**
```python
# Aplicar rate limiting a endpoints sensibles
@router.get("/stats")
@limiter.limit("100/minute")  # 100 requests por minuto
async def get_marketing_stats(...):
    # ... código
```

#### **7.3. Auditoría:**
```python
# Todos los endpoints deben tener @audit_access
@router.get("/stats")
@audit_access("view_marketing_stats")
async def get_marketing_stats(...):
    # ... código
```

#### **7.4. Encriptación de Tokens:**
```python
# Tokens OAuth deben encriptarse con Fernet
from core.credentials import encrypt_value, decrypt_value

encrypted_token = encrypt_value(access_token)
await save_tenant_credential(tenant_id, "META_USER_LONG_TOKEN", encrypted_token, "meta_ads")
```

### **8. MONITORING Y LOGGING**

#### **8.1. Log