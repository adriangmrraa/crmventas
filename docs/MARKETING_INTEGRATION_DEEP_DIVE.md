# Marketing Integration Deep Dive

Análisis técnico profundo de la integración Meta Ads Marketing Hub en CRM Ventas.

**Fecha implementación:** Febrero 2026  
**Estado:** ✅ Implementación 100% completa  
**Auditoría:** ✅ Pasada exitosamente  

---

## Visión General

El Marketing Hub extiende CRM Ventas con capacidades de:
1. **Publicidad Digital**: Gestión campañas Meta Ads (Facebook/Instagram)
2. **HSM Automation**: Plantillas WhatsApp aprobadas para marketing
3. **ROI Tracking**: Atribución leads → opportunities → sales
4. **OAuth Integration**: Conexión segura con cuentas Meta

### Business Value

- **10+ horas/semana** ahorro en gestión manual campañas
- **ROI medible** por campaña, canal, segmento
- **Automation** follow-up leads via WhatsApp HSM
- **Single Dashboard** para todo marketing digital

---

## Arquitectura Técnica

### Stack Tecnológico

| Capa | Tecnología | Propósito |
|------|------------|-----------|
| **Frontend** | React 18 + TypeScript + Vite + Tailwind | Dashboard marketing, wizard OAuth, HSM management |
| **Backend** | FastAPI + async/await + PostgreSQL | API endpoints, business logic, OAuth flow |
| **OAuth** | Meta Graph API v20.0 | Authentication, token management, API calls |
| **Database** | 8 nuevas tablas marketing | Almacenamiento tokens, campañas, insights, templates |
| **Security** | Nexus v7.7.1 | Rate limiting, audit logging, multi-tenant isolation |

### Diagrama de Flujo

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   Usuario   │────▶│   Frontend   │────▶│    OAuth     │
│   CRM       │     │   React      │     │   Meta Flow  │
└─────────────┘     └──────────────┘     └──────┬───────┘
                                                 │
┌─────────────┐     ┌──────────────┐     ┌──────▼───────┐
│   Meta API  │◀────│   Backend    │◀────│   Token      │
│   (Graph)   │     │   FastAPI    │     │   Storage    │
└─────────────┘     └──────────────┘     └──────────────┘
        │                   │                    │
        ▼                   ▼                    ▼
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   Campaign  │     │   Marketing  │     │   Database   │
│   Data      │     │   Logic      │     │   PostgreSQL │
└─────────────┘     └──────────────┘     └──────────────┘
```

---

## Componentes Clave

### 1. MetaOAuthService (`meta_ads_service.py`)

Servicio principal para integración Meta OAuth:

```python
class MetaOAuthService:
    async def exchange_code_for_token(self, code: str, tenant_id: int) -> Dict
    async def get_long_lived_token(self, short_token: str) -> str
    async def get_business_managers_with_token(self, access_token: str) -> List[Dict]
    async def store_meta_token(self, tenant_id: int, token_data: Dict) -> bool
    async def remove_meta_token(self, tenant_id: int) -> bool
    async def validate_token(self, access_token: str) -> bool
    async def test_connection(self, tenant_id: int) -> Dict
```

**Características de seguridad:**
- **State validation** para prevenir CSRF
- **Token encryption** con Fernet antes de almacenar
- **Automatic refresh** 7 días antes de expiración
- **Multi-tenant isolation** por `tenant_id`

### 2. MarketingService (`marketing_service.py`)

Servicio para métricas y gestión marketing:

```python
class MarketingService:
    async def get_marketing_stats(self, tenant_id: int, days: int = 30) -> Dict
    async def get_campaigns(self, tenant_id: int, status: str = "active") -> List[Dict]
    async def get_campaign_insights(self, tenant_id: int, campaign_id: str) -> Dict
    async def get_hsm_templates(self, tenant_id: int, status: str = "approved") -> List[Dict]
    async def create_hsm_template(self, tenant_id: int, template_data: Dict) -> Dict
    async def get_automation_rules(self, tenant_id: int) -> List[Dict]
    async def create_automation_rule(self, tenant_id: int, rule_data: Dict) -> Dict
```

### 3. Frontend Components

**MarketingHubView.tsx** - Dashboard principal:
- Métricas ROI, conversiones, spend
- Gráficos campañas performance
- Quick actions: connect Meta, create campaign

**MetaConnectionWizard.tsx** - Wizard 4 pasos:
1. Init OAuth → Meta Login
2. Select Business Manager
3. Select Ad Accounts
4. Confirm & Save

**MetaTemplatesView.tsx** - Gestión HSM:
- Lista plantillas aprobadas
- Crear nueva plantilla
- Historial envíos

**MarketingPerformanceCard.tsx** - Componente reutilizable:
- Display métricas KPI
- Trend arrows (↑↓)
- Comparison period

**MetaTokenBanner.tsx** - Banner estado:
- Token expiry countdown
- Connection status
- Refresh/Reconnect actions

---

## Flujos de Trabajo

### Flujo 1: Conectar Cuenta Meta

```
Usuario → /crm/marketing → Click "Connect" → Wizard 4 pasos
    ↓
Paso 1: GET /crm/auth/meta/url → Redirect Meta Login
    ↓
Paso 2: Meta Login → Callback /crm/auth/meta/callback
    ↓
Paso 3: Exchange code → Store token encrypted
    ↓
Paso 4: Fetch Business Managers → User selection
    ↓
Completion: Token stored, banner shows "Connected"
```

### Flujo 2: Sincronizar Campañas

```
Cron Job (cada 4 horas) → Meta API → Campaigns + Insights
    ↓
Process data → Calculate ROI, conversions
    ↓
Store in DB → meta_ads_campaigns, meta_ads_insights
    ↓
Update cache → Frontend muestra datos actualizados
```

### Flujo 3: HSM Automation

```
Marketing event trigger → Check automation rules
    ↓
Rule matches → Get HSM template
    ↓
Send via WhatsApp Business API
    ↓
Log in automation_logs → Update lead status
```

---

## Database Schema

### Tablas Principales

```sql
-- Tokens OAuth por tenant
CREATE TABLE meta_tokens (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    access_token TEXT NOT NULL,
    token_type VARCHAR(50),
    expires_at TIMESTAMP,
    meta_user_id VARCHAR(100),
    business_manager_id VARCHAR(100),
    encrypted_data BYTEA,  -- Datos adicionales encriptados
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Campañas Meta Ads
CREATE TABLE meta_ads_campaigns (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    campaign_id VARCHAR(100) NOT NULL,
    campaign_name VARCHAR(255),
    objective VARCHAR(100),
    status VARCHAR(50),
    daily_budget DECIMAL(10,2),
    lifetime_budget DECIMAL(10,2),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    meta_data JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tenant_id, campaign_id)
);

-- Insights diarios campañas
CREATE TABLE meta_ads_insights (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    campaign_id VARCHAR(100) NOT NULL,
    date DATE NOT NULL,
    impressions INTEGER,
    clicks INTEGER,
    spend DECIMAL(10,2),
    conversions INTEGER,
    conversion_value DECIMAL(10,2),
    cpm DECIMAL(10,2),
    cpc DECIMAL(10,2),
    roas DECIMAL(10,2),
    meta_data JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tenant_id, campaign_id, date)
);

-- Plantillas HSM WhatsApp
CREATE TABLE meta_templates (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    template_name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    language VARCHAR(10),
    components JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    meta_template_id VARCHAR(100),
    rejection_reason TEXT,
    approved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Reglas automatización marketing
CREATE TABLE automation_rules (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    rule_name VARCHAR(255) NOT NULL,
    trigger_type VARCHAR(100),  -- lead_status_change, campaign_conversion, etc.
    trigger_config JSONB,
    action_type VARCHAR(100),   -- send_hsm, update_lead, create_opportunity
    action_config JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## Seguridad

### OAuth Security

1. **State Parameter**: Unique state per request, validated in callback
2. **PKCE (opcional)**: Code verifier/challenge para public clients
3. **Token Encryption**: Fernet encryption antes de almacenar
4. **HttpOnly Cookies**: Para session management (no tokens OAuth)

### API Security

```python
# Todos los endpoints incluyen:
@router.get("/stats")
@audit_access("get_marketing_stats")  # Audit logging
@limiter.limit("20/minute")           # Rate limiting
async def get_marketing_stats(
    request: Request,
    tenant_id: int = Depends(get_resolved_tenant_id),  # Multi-tenant
    admin_token: str = Depends(verify_admin_token)     # X-Admin-Token
):
```

### Data Protection

- **GDPR Compliance**: User data minimization in Meta API calls
- **Token Isolation**: Cada tenant tiene tokens separados
- **Audit Trail**: Todas las acciones logueadas en `system_events`
- **Data Retention**: Configurable por variable entorno

---

## Performance Considerations

### Caching Strategy

```python
# MarketingService con caching
@cached(ttl=900)  # 15 minutos
async def get_marketing_stats(self, tenant_id: int, days: int = 30):
    # Lógica con cache Redis/memory
```

### Rate Limit Management

- **Meta API**: 200 calls/hour límite
- **Implementación**: Exponential backoff + retry logic
- **Bulk Operations**: Batch requests cuando posible

### Database Optimization

- **Indexes**: `(tenant_id, campaign_id, date)` en insights
- **Partitioning**: Considerar por fecha para datos históricos
- **Archiving**: Mover datos > 1 año a cold storage

---

## Testing Strategy

### Unit Tests

```python
# test_marketing_backend.py
class TestMarketingEndpoints:
    def test_get_marketing_stats(self):
        # Mock Meta API responses
        # Test business logic
        # Verify audit logging
        
    def test_oauth_flow(self):
        # Test state validation
        # Test token exchange
        # Test error handling
```

### Integration Tests

```python
# test_meta_oauth.py
class TestMetaOAuthIntegration:
    @pytest.mark.integration
    async def test_full_oauth_flow(self):
        # Simula flujo completo OAuth
        # Usa test credentials
        # Verifica token storage
```

### E2E Tests (Playwright)

```typescript
// marketing-hub.spec.ts
test('connect meta account', async ({ page }) => {
  await page.goto('/crm/marketing');
  await page.click('button:has-text("Connect Meta Account")');
  // Simula OAuth flow
  await expect(page.locator('.connection-status')).toHaveText('Connected');
});
```

---

## Deployment Checklist

### Pre-Deployment
- [ ] Meta Developers App creada y configurada
- [ ] Variables entorno configuradas (.env.production)
- [ ] Database migrations ejecutadas
- [ ] SSL certificate válido para OAuth callback

### Post-Deployment Verification
- [ ] Endpoints marketing responden (200 OK)
- [ ] OAuth flow funciona (test con test user)
- [ ] Database tables creadas correctamente
- [ ] Frontend components cargan sin errores
- [ ] Audit logging funciona para acciones marketing

### Monitoring
- [ ] Logs OAuth accesibles
- [ ] Error tracking configurado (Sentry/LogRocket)
- [ ] Alerts para token expiry (7 días antes)
- [ ] ROI metrics visible en dashboard

---

## Troubleshooting Guide

### Common Issues

#### "Invalid redirect_uri"
```bash
# Verificar:
echo $META_REDIRECT_URI
# Debe coincidir EXACTAMENTE con Meta Developers
# Incluir https:// en producción
```

#### "App not approved for permissions"
1. Ir a Meta Developers → App Review
2. Solicitar permisos necesarios
3. Proporcionar screencast caso de uso
4. Esperar 1-3 días aprobación

#### "Rate limit exceeded"
```python
# Implementar exponential backoff
import asyncio

async def call_meta_api_with_retry():
    for attempt in range(3):
        try:
            return await call_meta_api()
        except RateLimitError:
            wait = 2 ** attempt  # 1, 2, 4 segundos
            await asyncio.sleep(wait)
```

#### "Token expired"
- Sistema automático intenta refresh 7 días antes
- Si falla, notificar usuario para reconnect
- Log error para debugging

### Debug Endpoints

```bash
# Health check marketing endpoints
curl -X GET "http://localhost:8000/crm/marketing/stats" \
  -H "X-Admin-Token: $ADMIN_TOKEN"

# Test OAuth URL generation
curl -X GET "http://localhost:8000/crm/auth/meta/url" \
  -H "Authorization: Bearer $JWT" \
  -H "X-Admin-Token: $ADMIN_TOKEN"
```

---

## Future Enhancements

### Short-term (Q2 2026)
- [ ] Google Ads integration
- [ ] TikTok Ads integration
- [ ] Email marketing automation
- [ ] SMS marketing integration

### Medium-term (Q3 2026)
- [ ] AI-powered campaign optimization
- [ ] Predictive ROI modeling
- [ ] Multi-channel attribution
- [ ] Advanced segmentation

### Long-term (Q4 2026)
- [ ] Marketplace for marketing templates
- [ ] Agency collaboration features
- [ ] White-label reporting
- [ ] API for external tools

---

## Recursos

### Documentación Relacionada
- `API_REFERENCE.md` - Endpoints marketing y OAuth
- `01_architecture.md` - Arquitectura sistema completo
- `03_deployment_guide.md` - Guía deployment marketing
- `FINAL_IMPLEMENTATION_SUMMARY.md` - Resumen implementación

### Enlaces Externos
- [Meta Graph API Documentation](https://developers.facebook.com/docs/graph-api)
- [WhatsApp Business API](https://developers.facebook.com/docs/whatsapp)
- [OAuth 2.0 Specification](https://oauth.net/2/)

### Soporte
- **Issues**: Crear issue en GitHub repo
- **Questions**: Discord community #marketing-hub
- **Bugs**: Usar template bug report con logs

---

**Última actualización:** Febrero 2026  
**Versión:** 1.0.0  
**Estado:** ✅ Production Ready  
**Auditoría:** ✅ ClinicForge vs CRM Ventas - PASADA  
