# 📘 INVESTIGACIÓN: Google Ads + Google OAuth para CRM Ventas

## 🎯 OBJETIVO
Implementar integración con Google Ads (similar a Meta Ads) y Google OAuth login en CRM Ventas.

## 🔍 ANÁLISIS DE LA IMPLEMENTACIÓN ACTUAL (META ADS)

### **Estructura Actual de Meta Ads:**

#### **1. FRONTEND:**
- **`MarketingHubView.tsx`** - Vista principal del hub de marketing
- **`MetaConnectionWizard.tsx`** - Wizard para conexión OAuth
- **`MetaTemplatesView.tsx`** - Templates de Meta
- **`/api/marketing.ts`** - API calls para marketing
- **`/types/marketing.ts`** - Tipos TypeScript

#### **2. BACKEND:**
- **`routes/meta_auth.py`** - Rutas OAuth de Meta
- **`services/marketing/meta_ads_service.py`** - Servicio de Meta Ads
- **`core/credentials.py`** - Gestión de credenciales

#### **3. FLUJO OAuth DE META:**
```
1. Frontend: GET /crm/auth/meta/url → Obtiene URL de autorización
2. Redirige a: https://www.facebook.com/v19.0/dialog/oauth
3. Usuario autoriza → Callback a: /crm/auth/meta/callback
4. Backend intercambia code por token
5. Almacena token en tabla `credentials` (META_USER_LONG_TOKEN)
6. Redirige a frontend con ?success=connected
```

#### **4. ESTRUCTURA DE DATOS:**
```sql
-- Tabla credentials (existente)
CREATE TABLE credentials (
    tenant_id INT,
    name VARCHAR(255),  -- Ej: "META_USER_LONG_TOKEN"
    value TEXT,         -- Token encriptado
    category VARCHAR(100),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

## 🔧 GOOGLE ADS API - INVESTIGACIÓN

### **1. REQUISITOS DE GOOGLE ADS API:**

#### **Scopes Necesarios:**
```python
GOOGLE_ADS_SCOPES = [
    "https://www.googleapis.com/auth/adwords",  # Acceso completo a Google Ads
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile"
]
```

#### **Tipos de Autenticación:**
1. **OAuth 2.0 para aplicaciones web** (similar a Meta)
2. **Service Account** (para backend-to-backend)
3. **API Key** (limitado, no recomendado para producción)

#### **Endpoints Principales:**
- **Autorización:** `https://accounts.google.com/o/oauth2/v2/auth`
- **Token:** `https://oauth2.googleapis.com/token`
- **API Google Ads:** `https://googleads.googleapis.com/v16/customers/{customerId}/googleAds:search`

### **2. FLUJO OAuth 2.0 DE GOOGLE:**

```
1. GET /crm/auth/google/url → Genera URL de autorización Google
2. Redirige a: https://accounts.google.com/o/oauth2/v2/auth
   ?client_id=CLIENT_ID
   &redirect_uri=REDIRECT_URI
   &response_type=code
   &scope=SCOPES
   &access_type=offline  # IMPORTANTE: Para refresh tokens
   &prompt=consent       # Forzar consentimiento para refresh token
3. Usuario autoriza → Callback a: /crm/auth/google/callback
4. Backend intercambia code por access_token + refresh_token
5. Almacena ambos tokens en `credentials`
6. Redirige a frontend
```

### **3. REFRESH TOKENS (CRÍTICO):**
- Google access tokens expiran en **1 hora**
- **Refresh tokens** son permanentes (hasta que se revoquen)
- Necesario almacenar `refresh_token` para renovaciones automáticas

## 🔐 GOOGLE OAUTH LOGIN - INVESTIGACIÓN

### **1. FLUJO DE LOGIN CON GOOGLE:**

#### **Para Registro/Login:**
```
1. Frontend: Botón "Sign in with Google"
2. Redirige a Google OAuth con scopes de perfil
3. Usuario autoriza → Callback
4. Backend verifica/crea usuario en base de datos
5. Crea sesión JWT (igual que login normal)
6. Redirige a dashboard
```

#### **Scopes para Login:**
```python
GOOGLE_LOGIN_SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid"
]
```

### **2. INTEGRACIÓN CON USUARIOS EXISTENTES:**

#### **Tabla `users` actual:**
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),  -- NULL para usuarios Google
    full_name VARCHAR(255),
    role VARCHAR(50),
    tenant_id INT,
    google_id VARCHAR(255) UNIQUE,  -- NUEVO: ID único de Google
    google_email VARCHAR(255),      -- NUEVO: Email de Google
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### **Flujo de registro/login:**
1. Usuario hace login con Google
2. Backend recibe `google_id` y `email`
3. Busca usuario por `google_id` o `email`
4. Si no existe, crea nuevo usuario (sin password)
5. Si existe, actualiza `google_id` si es necesario
6. Crea sesión JWT

## 🏗️ ARQUITECTURA PROPUESTA

### **1. ESTRUCTURA DE ARCHIVOS:**

#### **BACKEND (Python/FastAPI):**
```
orchestrator_service/
├── routes/
│   ├── google_auth.py          # Rutas OAuth Google (Ads + Login)
│   └── google_ads_routes.py    # Rutas específicas de Google Ads API
├── services/
│   └── marketing/
│       ├── google_ads_service.py    # Servicio Google Ads
│       └── google_oauth_service.py  # Servicio OAuth Google
└── core/
    └── google_credentials.py   # Gestión específica de credenciales Google
```

#### **FRONTEND (React/TypeScript):**
```
frontend_react/src/
├── views/marketing/
│   ├── GoogleAdsView.tsx       # Nueva pestaña para Google Ads
│   └── GoogleConnectionWizard.tsx
├── components/marketing/
│   ├── GoogleAdsPerformanceCard.tsx
│   └── GoogleConnectionButton.tsx
├── api/
│   └── google_ads.ts           # API calls para Google Ads
├── types/
│   └── google_ads.ts           # Tipos TypeScript
└── hooks/
    └── useGoogleAds.ts         # Hook para Google Ads
```

### **2. MODIFICACIONES EN MARKETING HUB:**

#### **MarketingHubView.tsx - Añadir pestañas:**
```tsx
// Nueva estructura de tabs
const [activePlatform, setActivePlatform] = useState<'meta' | 'google'>('meta');

// En el render:
<div className="flex bg-gray-100 p-1 rounded-xl">
  <button onClick={() => setActivePlatform('meta')}>Meta Ads</button>
  <button onClick={() => setActivePlatform('google')}>Google Ads</button>
</div>

// Render condicional:
{activePlatform === 'meta' && <MetaAdsContent />}
{activePlatform === 'google' && <GoogleAdsContent />}
```

### **3. BASE DE DATOS - MODIFICACIONES:**

#### **Nuevas credenciales:**
```sql
-- Credenciales Google Ads
GOOGLE_ADS_ACCESS_TOKEN
GOOGLE_ADS_REFRESH_TOKEN
GOOGLE_ADS_CLIENT_ID
GOOGLE_ADS_CLIENT_SECRET
GOOGLE_ADS_DEVELOPER_TOKEN  -- Específico de Google Ads API
GOOGLE_ADS_CUSTOMER_ID      -- Customer ID de Google Ads

-- Credenciales Google OAuth (login)
GOOGLE_OAUTH_CLIENT_ID
GOOGLE_OAUTH_CLIENT_SECRET
```

#### **Nuevas columnas en `users`:**
```sql
ALTER TABLE users ADD COLUMN google_id VARCHAR(255);
ALTER TABLE users ADD COLUMN google_email VARCHAR(255);
ALTER TABLE users ADD COLUMN google_profile_picture TEXT;
CREATE INDEX idx_users_google_id ON users(google_id);
```

## 🔄 FLUJOS DE TRABAJO

### **1. CONEXIÓN GOOGLE ADS:**
```
Usuario → Marketing Hub → Click "Connect Google Ads" 
→ GET /crm/auth/google/ads/url 
→ Redirige a Google OAuth 
→ Usuario autoriza acceso a Google Ads
→ Callback: /crm/auth/google/ads/callback
→ Almacena tokens
→ Redirige a Marketing Hub con ?success=connected
```

### **2. LOGIN CON GOOGLE:**
```
Usuario → Login page → Click "Sign in with Google"
→ GET /crm/auth/google/login/url
→ Redirige a Google OAuth
→ Usuario autoriza acceso básico
→ Callback: /crm/auth/google/login/callback
→ Verifica/crea usuario
→ Crea JWT session
→ Redirige a dashboard
```

### **3. SINCRONIZACIÓN DE DATOS GOOGLE ADS:**
```
Background job cada 1 hora:
1. Verifica token no expirado (renueva con refresh_token si es necesario)
2. Obtiene campañas, ads, métricas
3. Almacena en tablas de marketing_metrics
4. Actualiza dashboard en tiempo real
```

## ⚠️ CONSIDERACIONES DE SEGURIDAD

### **1. GOOGLE ADS API:**
- **Developer Token:** Requiere aprobación de Google
- **Test Account:** Necesario para desarrollo
- **Quotas:** Límites estrictos de API calls
- **Customer ID:** Identificador único de cuenta de Google Ads

### **2. ALMACENAMIENTO DE TOKENS:**
- **Access tokens:** Encriptados, expiran en 1 hora
- **Refresh tokens:** Encriptados, permanentes
- **Developer token:** Encriptado, sensible
- **Customer ID:** Encriptado

### **3. MULTI-TENANT:**
- Cada tenant tiene sus propias credenciales Google
- Aislamiento estricto por `tenant_id`
- Tokens no compartidos entre tenants

## 📊 COMPARACIÓN META ADS vs GOOGLE ADS

| Característica | Meta Ads | Google Ads |
|----------------|----------|------------|
| **API Version** | Graph API v19.0 | Google Ads API v16 |
| **OAuth Flow** | Facebook Login | Google OAuth 2.0 |
| **Token Expiración** | 60 días | 1 hora (access), permanente (refresh) |
| **Scopes** | ads_management, ads_read | https://www.googleapis.com/auth/adwords |
| **Métricas** | spend, leads, impressions | clicks, conversions, cost |
| **Estructura** | Campaign → AdSet → Ad | Campaign → AdGroup → Ad |
| **Atribución** | UTM parameters, referral | gclid, conversion tracking |

## 🚀 PRÓXIMOS PASOS

### **FASE 1: INVESTIGACIÓN Y PLANIFICACIÓN** ✅
- [x] Analizar implementación actual de Meta Ads
- [x] Investigar Google Ads API
- [x] Investigar Google OAuth para login
- [x] Documentar arquitectura propuesta

### **FASE 2: CONFIGURACIÓN GOOGLE CLOUD**
- [ ] Crear proyecto en Google Cloud Console
- [ ] Habilitar Google Ads API
- [ ] Habilitar Google OAuth 2.0
- [ ] Obtener Client ID y Client Secret
- [ ] Solicitar Developer Token de Google Ads
- [ ] Configurar Redirect URIs

### **FASE 3: BACKEND IMPLEMENTATION**
- [ ] Crear `routes/google_auth.py`
- [ ] Crear `services/marketing/google_ads_service.py`
- [ ] Modificar `core/credentials.py`
- [ ] Crear migraciones de base de datos
- [ ] Implementar refresh token automation

### **FASE 4: FRONTEND IMPLEMENTATION**
- [ ] Crear `GoogleAdsView.tsx`
- [ ] Crear `GoogleConnectionWizard.tsx`
- [ ] Modificar `MarketingHubView.tsx` para tabs
- [ ] Crear componentes de UI
- [ ] Implementar API calls

### **FASE 5: GOOGLE OAUTH LOGIN**
- [ ] Modificar tabla `users`
- [ ] Crear rutas de login con Google
- [ ] Implementar frontend de login
- [ ] Manejar usuarios existentes/nuevos

### **FASE 6: TESTING Y DEPLOYMENT**
- [ ] Testing con sandbox de Google Ads
- [ ] Testing OAuth flows
- [ ] Testing multi-tenant
- [ ] Deployment a staging
- [ ] Monitoring y logs

## 📚 RECURSOS

### **Documentación Oficial:**
1. **Google Ads API:** https://developers.google.com/google-ads/api/docs/start
2. **Google OAuth 2.0:** https://developers.google.com/identity/protocols/oauth2
3. **Google Identity Services:** https://developers.google.com/identity

### **Librerías Recomendadas:**
- **Python:** `google-ads` (oficial), `google-auth`, `google-auth-oauthlib`
- **JavaScript:** `@react-oauth/google`, `google-auth-library`

### **Herramientas de Testing:**
- **Google Ads API Test Account:** https://developers.google.com/google-ads/api/docs/first-call/test-account
- **OAuth Playground:** https://developers.google.com/oauthplayground

---

**NOTA:** Esta implementación requiere aprobación de Google para el Developer Token, lo cual puede tomar varios días. Se recomienda comenzar con el sandbox de desarrollo.