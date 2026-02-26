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

### 3. Frontend Components (Actualizado Febrero 2026)

**MarketingHubView.tsx** - Dashboard principal mejorado:
- Métricas ROI, conversiones, spend
- Gráficos campañas performance
- **Webhook Configuration**: URLs copiables para Meta y YCloud
- **Tablas Creativos**: Filtros, ordenamiento, paginación mejorados
- **Responsive Design**: Scroll optimizado para móviles (`overflow-y-auto`)

**MetaConnectionWizard.tsx** - Wizard 4 pasos optimizado:
1. **Init OAuth** → Meta Login con mejor UX
2. **Select Business Manager** - Carga datos iniciales entidad
3. **Select Ad Accounts** - Filtrado por portfolio seleccionado
4. **Confirm & Save** - Manejo errores mejorado con mensajes específicos
- **UI/UX**: Gradientes, iconos, espaciado mejorado
- **Error Handling**: Mensajes específicos por tipo error

**MetaTemplatesView.tsx** - Gestión HSM:
- Lista plantillas aprobadas
- Crear nueva plantilla
- Historial envíos
- **Automation Logs**: Visualización logs ejecución automatización

**MarketingPerformanceCard.tsx** - Componente reutilizable:
- Display métricas KPI
- Trend arrows (↑↓)
- Comparison period
- **Data Structure Compatibility**: Soporte `data.data || data`

**MetaTokenBanner.tsx** - Banner estado:
- Token expiry countdown
- Connection status
- Refresh/Reconnect actions
- **Endpoint Correction**: Usa `/crm/marketing/token-status`

**ConfigView.tsx** - Nueva vista configuración:
- **Gestión Credenciales CRUD**: Crear, leer, actualizar, eliminar
- **Categorización**: Credenciales por categoría (global/tenant)
- **Integraciones**: YCloud, Chatwoot, Meta
- **UI Profesional**: Modales, formularios, validaciones

**PrivacyTermsView.tsx** - Páginas legales:
- **Vista única**: Maneja 3 URLs (`/legal`, `/privacy`, `/terms`)
- **i18n Completo**: Español e inglés con interpolación dinámica
- **Diseño Responsive**: Mobile-first, navegación por anclas
- **Contenido específico**: Menciona Meta Ads API para aprobación OAuth

### 4. Meta Webhooks (`meta_webhooks.py`)
Módulo encargado de recibir notificaciones asíncronas de Meta:
- **Verification**: Handshake inicial para validar el webhook con Meta Graph API.
- **LeadGen Processing**: 
  - Al recibir un `leadgen_id`, el sistema usa el `page_id` del payload para encontrar el `tenant_id` en la tabla `meta_tokens`.
  - Recupera los datos del lead (nombre, email, teléfono) y realiza e **upsert** en el CRM.
  - Genera notificaciones Socket.IO en tiempo real para el Dashboard.

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

### Flujo 3: HSM Automation (v7.8)

```
Evento (Recordatorio/Recuperación) → AutomationService
    ↓
Check de Reglas (automation_rules)
    ↓
Send via WhatsApp Business API (YCloudClient)
    ↓
1. Log en automation_logs (Estado del trigger)
2. Log en chat_messages (Visibilidad en CRM) ✅ NEW v7.8
    ↓
Lead status update
```

**Nota Técnica v7.8**: Se sincronizaron las firmas de `YCloudClient.send_template` entre microservicios para evitar fallos de tipo (`TypeError`) que interrumpían el flujo de registro, previniendo bucles de reintentos infinitos ("Mensajes Fantasma").

---

## Protocolos de Seguridad y Estabilidad v7.8 (Crítico)

Durante la estabilización de Febrero 2026, se implementaron cambios clave en la relación con **YCloud** y el manejo de **Tenants**:

### 1. The Vault: Credenciales Soberanas
- **Eliminación de Hardcoding**: Las claves `YCLOUD_API_KEY` y `YCLOUD_WEBHOOK_SECRET` ya no dependen exclusivamente de variables de entorno globales.
- **Jerarquía de Carga**: El sistema busca primero en la tabla `credentials` ("The Vault") filtrando por `tenant_id`. Las variables de entorno actúan solo como *fallback* de emergencia.
- **Encriptación**: Todos los secretos en "The Vault" se almacenan mediante **Fernet (AES-256)**.

### 2. Aislamiento Multi-tenant Robusto
- **Tipado Estricto**: Se identificó que el paso de `tenant_id` como string causaba fallos silenciosos en la firma de mensajes. **Regla**: El `tenant_id` debe ser siempre un entero (`int`) en todo el pipeline de comunicación.
- **Deduplicación por Sede**: La lógica de Redis ahora incorpora el `tenant_id` para evitar colisiones de mensajes entre diferentes clínicas compartiendo infraestructura.

### 3. Registro Espejo (HSM Visibility)
- Todo mensaje saliente generado por automatizaciones (HSM) ahora se registra obligatoriamente en `chat_messages`. 
- Esto garantiza que el operador humano vea qué le dijo la IA al paciente, evitando el problema de "Mensajes Fantasma" (mensajes que se enviaban pero no se veían en el CRM).

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
    page_id VARCHAR(255),  -- ID de la página de Facebook vinculada
    encrypted_data BYTEA,  -- Datos adicionales encriptados
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_meta_tokens_page_id ON meta_tokens(page_id);

-- Campañas Meta Ads
CREATE TABLE meta_ads_campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    meta_campaign_id VARCHAR(255) NOT NULL,
    meta_account_id VARCHAR(255) NOT NULL,
    name TEXT NOT NULL,
    objective TEXT,
    status TEXT,
    daily_budget DECIMAL(12,2),
    lifetime_budget DECIMAL(12,2),
    spend DECIMAL(12,2) DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    leads_count INTEGER DEFAULT 0,
    roi_percentage DECIMAL(5,2) DEFAULT 0,
    last_synced_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_meta_campaign_per_tenant UNIQUE (tenant_id, meta_campaign_id)
);

-- Insights diarios campañas
CREATE TABLE meta_ads_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    meta_campaign_id VARCHAR(255) NOT NULL,
    date DATE NOT NULL,
    spend DECIMAL(12,2) DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    leads INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_insight_per_day UNIQUE (tenant_id, meta_campaign_id, date)
);

-- Plantillas HSM WhatsApp
CREATE TABLE meta_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    meta_template_id VARCHAR(255) NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    language TEXT DEFAULT 'es',
    status TEXT,
    components JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_meta_template_per_tenant UNIQUE (tenant_id, meta_template_id)
);

-- Reglas automatización marketing
CREATE TABLE automation_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    name TEXT NOT NULL,
    trigger_type TEXT NOT NULL,
    trigger_conditions JSONB NOT NULL,
    action_type TEXT NOT NULL,
    action_config JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Pipeline de Ventas (ROI Tracking)
CREATE TABLE opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    lead_id UUID REFERENCES leads(id) NOT NULL,
    seller_id UUID REFERENCES users(id),
    name TEXT NOT NULL,
    value DECIMAL(12,2) NOT NULL,
    stage TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sales_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    opportunity_id UUID REFERENCES opportunities(id),
    amount DECIMAL(12,2) NOT NULL,
    attribution_source TEXT,
    meta_campaign_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

### Debug Endpoints y Herramientas (Actualizado Febrero 2026)

#### **Endpoints Debug API:**
```bash
# Health check marketing endpoints
curl -X GET "http://localhost:8000/crm/marketing/stats" \
  -H "X-Admin-Token: $ADMIN_TOKEN"

# Test OAuth URL generation
curl -X GET "http://localhost:8000/crm/auth/meta/url" \
  -H "Authorization: Bearer $JWT" \
  -H "X-Admin-Token: $ADMIN_TOKEN"

# Debug marketing stats (raw API responses)
curl -X GET "http://localhost:8000/crm/marketing/debug/stats" \
  -H "Authorization: Bearer $JWT" \
  -H "X-Admin-Token: $ADMIN_TOKEN"
```

#### **Herramientas de Diagnóstico Scripts:**

**1. debug_marketing_stats.py**
```bash
# Uso: python debug_marketing_stats.py
# Propósito: Debugging estadísticas marketing tenant 1
# Funcionalidad: Consulta stats campañas, creativos, account total spend
```

**2. check_automation.py**
```bash
# Uso: python check_automation.py
# Propósito: Diagnóstico automatización
# Funcionalidad: Verifica reglas activas, logs recientes, status leads específicos
```

**3. check_leads.py**
```bash
# Uso: python check_leads.py
# Propósito: Verificación leads base datos
# Funcionalidad: Lista leads tenant 1 + números chat para cross-reference
```

#### **Variables Entorno Debug:**
```bash
# Archivo .env.production
DEBUG_MARKETING_STATS=true          # Activar debugging estadísticas
LOG_META_API_CALLS=true             # Log detallado llamadas API Meta
ENABLE_AUTOMATION_DIAGNOSTICS=true  # Activar diagnósticos automatización
META_API_DEBUG_MODE=true            # Modo debug API Meta (respuestas raw)
```

#### **Configuración Webhook (Nuevo):**
```bash
# Obtener URLs configuración webhook
curl -X GET "http://localhost:8000/admin/config/deployment" \
  -H "Authorization: Bearer $JWT" \
  -H "X-Admin-Token: $ADMIN_TOKEN"

# Respuesta incluye:
{
  "webhook_ycloud_url": "https://tu-crm.com/webhook/ycloud",
  "webhook_meta_url": "https://tu-crm.com/crm/webhook/meta",
  "orchestrator_url": "https://tu-crm.com",
  "environment": "production"
}
```

#### **Páginas Legales (Meta OAuth):**
- **Privacy Policy URL:** `https://tu-crm.com/privacy`
- **Terms of Service URL:** `https://tu-crm.com/terms`
- **Implementadas en:** `frontend_react/src/views/PrivacyTermsView.tsx`
- **Rutas disponibles:** `/legal`, `/privacy`, `/terms`

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
