# 🎯 PLAN DE IMPLEMENTACIÓN: META ADS CLINICFORGE → CRM SALES

## 📊 RESUMEN EJECUTIVO

**Objetivo:** Implementar las funcionalidades de **Marketing Hub** y **HSM Automation** de ClinicForge en el sidebar del CRM Sales.

**Estado Actual:**
- ✅ **ClinicForge:** Sistema completo con Meta Ads integrado (Marketing Hub + HSM Automation)
- ✅ **CRM Sales:** Sistema CRM básico sin funcionalidades de marketing
- 🔄 **Migración:** Transferir componentes, servicios y endpoints de ClinicForge a CRM Sales

---

## 🏗️ ARQUITECTURA CLINICFORGE (ORIGEN)

### **1. FRONTEND - React/TypeScript**

#### **Componentes Clave:**
- **`MarketingHubView.tsx`** - Dashboard principal de marketing
- **`MetaTemplatesView.tsx`** - HSM Automation y templates
- **`MetaConnectionWizard.tsx`** - Wizard de conexión OAuth
- **`MarketingPerformanceCard.tsx`** - Card de métricas ROI
- **`MetaTokenBanner.tsx`** - Banner de estado de conexión
- **`AdContextCard.tsx`** - Card de contexto de anuncios

#### **Rutas (React Router):**
```typescript
// En App.tsx o routing config
{
  path: "/marketing",
  element: <MarketingHubView />
},
{
  path: "/hsm",
  element: <MetaTemplatesView />
}
```

#### **Sidebar Integration:**
```typescript
// En Sidebar.tsx - ClinicForge
const menuItems = [
  // ... otros items
  { id: 'marketing', label: 'Marketing Hub', icon: <Megaphone />, path: '/marketing' },
  { id: 'hsm', label: 'HSM Automation', icon: <Layout />, path: '/hsm' }
];
```

### **2. BACKEND - FastAPI/Python**

#### **Servicios Principales:**
1. **`meta_ads_service.py`** - Cliente Graph API de Meta
   - `get_ad_details()` - Detalles de anuncios
   - `get_ads_insights()` - Métricas de rendimiento
   - `get_portfolios()` - Business Managers
   - `get_ad_accounts()` - Cuentas de anuncios
   - `get_campaigns_with_insights()` - Campañas con métricas

2. **`marketing_service.py`** - Lógica de negocio
   - `get_roi_stats()` - Cálculo de ROI real
   - `get_campaign_stats()` - Estadísticas de campañas
   - `get_token_status()` - Estado de conexión

3. **`automation_service.py`** - Automatización HSM
   - Triggers de WhatsApp automatizados
   - Logs de envíos automáticos

#### **Endpoints API:**
```python
# marketing.py
GET  /admin/marketing/stats           # Dashboard principal
GET  /admin/marketing/stats/roi       # ROI específico
GET  /admin/marketing/token-status    # Estado conexión
GET  /admin/marketing/meta-portfolios # Portafolios Meta
GET  /admin/marketing/meta-accounts   # Cuentas de anuncios
POST /admin/marketing/connect         # Conectar cuenta
GET  /admin/marketing/automation-logs # Logs HSM
```

#### **Base de Datos:**
- **Tabla `patients`:** Campo `acquisition_source = 'META_ADS'`
- **Tabla `accounting_transactions`:** Ingresos atribuibles
- **Tabla `credentials`:** Tokens OAuth (`META_USER_LONG_TOKEN`)
- **Tabla `automation_logs`:** Logs de HSM Automation

### **3. FLUJO DE AUTENTICACIÓN OAUTH**

```
1. Usuario click "Conectar Meta" → Frontend llama /admin/marketing/meta-auth/url
2. Backend genera URL OAuth con state=tenant_{id} → Redirige a Meta
3. Meta autentica → Callback a /auth/meta/callback con code
4. Backend intercambia code por access_token (long-lived)
5. Guarda token en credentials table → Redirige a /marketing?success=connected
6. Frontend detecta success → Abre wizard de selección de cuenta
```

---

## 🛠️ CRM SALES (DESTINO) - ANÁLISIS ACTUAL

### **1. ESTRUCTURA EXISTENTE**

#### **Frontend:**
- **Ubicación:** `/home/node/.openclaw/workspace/projects/crmventas/frontend_react/`
- **Framework:** React 18 + TypeScript + Vite + Tailwind
- **Routing:** React Router (ver `App.tsx`)
- **Sidebar:** `src/components/Sidebar.tsx` - Menú actual:
  ```typescript
  const menuItems = [
    { id: 'dashboard', path: '/', icon: <Home /> },
    { id: 'leads', path: '/crm/leads', icon: <Users /> },
    { id: 'clients', path: '/crm/clientes', icon: <Users /> },
    { id: 'crm_agenda', path: '/crm/agenda', icon: <Calendar /> },
    { id: 'prospecting', path: '/crm/prospeccion', icon: <Search /> },
    { id: 'chats', path: '/chats', icon: <MessageSquare /> },
    { id: 'sellers', path: '/crm/vendedores', icon: <ShieldCheck /> },
    // FALTAN: marketing, hsm_automation
  ];
  ```

#### **Backend:**
- **Ubicación:** `/home/node/.openclaw/workspace/projects/crmventas/orchestrator_service/`
- **Framework:** FastAPI (similar a ClinicForge)
- **Base de Datos:** PostgreSQL con multi-tenant
- **Estructura actual:** CRM básico sin módulos de marketing

### **2. DIFERENCIAS CLAVE CRM vs CLINICFORGE**

| Aspecto | ClinicForge | CRM Sales | Acción Requerida |
|---------|------------|-----------|------------------|
| **Dominio** | Salud dental | Ventas/CRM | Adaptar terminología |
| **Entidad principal** | Pacientes | Leads/Clientes | Mapear `patients` → `leads` |
| **Atribución** | `acquisition_source` | `lead_source` | Renombrar campo |
| **Conversión** | Citas → Ingresos | Oportunidades → Ventas | Adaptar métricas |
| **Automatización** | Recordatorios citas | Follow-ups ventas | Adaptar triggers HSM |

---

## 🚀 PLAN DE IMPLEMENTACIÓN - FASE POR FASE

### **FASE 1: INFRAESTRUCTURA BACKEND**

#### **1.1. Migrar Servicios de ClinicForge:**
```bash
# Copiar servicios esenciales
cp clinicforge/orchestrator_service/services/meta_ads_service.py crmventas/orchestrator_service/services/
cp clinicforge/orchestrator_service/services/marketing_service.py crmventas/orchestrator_service/services/
cp clinicforge/orchestrator_service/services/automation_service.py crmventas/orchestrator_service/services/
```

#### **1.2. Adaptar Servicios para CRM:**
```python
# En marketing_service.py - Adaptar para CRM
# Cambiar:
# - patients → leads
# - appointments → opportunities
# - accounting_transactions → sales_transactions
# - acquisition_source = 'META_ADS' → lead_source = 'META_ADS'
```

#### **1.3. Crear Endpoints CRM:**
```python
# crmventas/orchestrator_service/routes/marketing.py
# Basado en clinicforge/orchestrator_service/routes/marketing.py
# Adaptar:
# - /admin/marketing/ → /crm/marketing/
# - Referencias a tenants/clinics → accounts/businesses
```

#### **1.4. Configurar Base de Datos:**
```sql
-- Agregar campos a tabla leads
ALTER TABLE leads ADD COLUMN IF NOT EXISTS lead_source VARCHAR(50);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS meta_ad_id VARCHAR(100);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS meta_campaign_id VARCHAR(100);

-- Crear tabla automation_logs (similar a ClinicForge)
CREATE TABLE IF NOT EXISTS automation_logs (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL,
    lead_id INTEGER REFERENCES leads(id),
    trigger_type VARCHAR(50),
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW(),
    error_details TEXT
);

-- Crear tabla sales_transactions para ROI
CREATE TABLE IF NOT EXISTS sales_transactions (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL,
    lead_id INTEGER REFERENCES leads(id),
    amount DECIMAL(10,2),
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### **FASE 2: FRONTEND - COMPONENTES Y VISTAS**

#### **2.1. Migrar Componentes React:**
```bash
# Crear estructura de marketing en CRM
mkdir -p crmventas/frontend_react/src/views/marketing/
mkdir -p crmventas/frontend_react/src/components/marketing/

# Copiar y adaptar componentes
cp clinicforge/frontend_react/src/views/MarketingHubView.tsx crmventas/frontend_react/src/views/marketing/
cp clinicforge/frontend_react/src/views/MetaTemplatesView.tsx crmventas/frontend_react/src/views/marketing/
cp clinicforge/frontend_react/src/components/MarketingPerformanceCard.tsx crmventas/frontend_react/src/components/marketing/
cp clinicforge/frontend_react/src/components/integrations/MetaConnectionWizard.tsx crmventas/frontend_react/src/components/marketing/
```

#### **2.2. Adaptar Terminología CRM:**
```typescript
// En MarketingHubView.tsx - Cambiar:
// - "patients" → "leads"
// - "appointments" → "opportunities"
// - "clinic" → "account"
// - "dental" → "sales"
```

#### **2.3. Integrar en Sidebar:**
```typescript
// En crmventas/frontend_react/src/components/Sidebar.tsx
import { Megaphone, Layout } from 'lucide-react';

const menuItems = [
  // ... items existentes
  { 
    id: 'marketing', 
    labelKey: 'nav.marketing' as const, 
    icon: <Megaphone size={20} />, 
    path: '/crm/marketing',
    roles: ['ceo', 'professional'] 
  },
  { 
    id: 'hsm_automation', 
    labelKey: 'nav.hsm_automation' as const, 
    icon: <Layout size={20} />, 
    path: '/crm/hsm',
    roles: ['ceo'] 
  },
];
```

#### **2.4. Agregar Rutas:**
```typescript
// En crmventas/frontend_react/src/App.tsx
import MarketingHubView from './views/marketing/MarketingHubView';
import MetaTemplatesView from './views/marketing/MetaTemplatesView';

// Agregar rutas dentro del Layout
<Route path="crm/marketing" element={<MarketingHubView />} />
<Route path="crm/hsm" element={<MetaTemplatesView />} />
```

### **FASE 3: INTEGRACIÓN OAUTH Y CONEXIÓN META**

#### **3.1. Configurar Variables de Entorno:**
```bash
# .env del backend CRM
META_APP_ID=tu_app_id
META_APP_SECRET=tu_app_secret
META_REDIRECT_URI=https://tu-crm.com/auth/meta/callback
META_GRAPH_API_VERSION=v21.0
```

#### **3.2. Implementar Endpoints OAuth:**
```python
# Basado en clinicforge/orchestrator_service/routes/auth.py
# Crear endpoints:
# GET  /crm/auth/meta/url        # Generar URL OAuth
# GET  /crm/auth/meta/callback   # Callback handler
# POST /crm/auth/meta/disconnect # Desconectar
```

#### **3.3. Sistema de Credenciales Multi-Tenant:**
```python
# Usar mismo sistema que ClinicForge
# credentials table: tenant_id, key, value, category
# Ejemplo:
# tenant_id=1, key='META_USER_LONG_TOKEN', value='EAAG...', category='meta_ads'
```

### **FASE 4: HSM AUTOMATION PARA CRM**

#### **4.1. Triggers Adaptados para Ventas:**
```python
# En automation_service.py - Nuevos triggers CRM:
TRIGGERS = {
    'lead_followup': {
        'condition': "lead.status == 'new' AND hours_since_creation > 24",
        'action': "send_whatsapp_template('lead_followup', lead.phone)"
    },
    'opportunity_reminder': {
        'condition': "opportunity.status == 'pending' AND hours_before_deadline < 2",
        'action': "send_whatsapp_template('opportunity_reminder', lead.phone)"
    },
    'post_sale_feedback': {
        'condition': "sale.completed_at IS NOT NULL AND days_since_sale == 7",
        'action': "send_whatsapp_template('post_sale_feedback', lead.phone)"
    }
}
```

#### **4.2. Templates WhatsApp para CRM:**
```json
{
  "lead_followup": {
    "name": "lead_followup",
    "components": [
      {
        "type": "body",
        "text": "Hola {{1}}, soy {{2}} de {{3}}. Vimos tu interés en {{4}} ¿Te gustaría agendar una llamada para contarte más?"
      }
    ]
  }
}
```

#### **4.3. Panel de Configuración HSM:**
- UI para activar/desactivar triggers
- Configurar templates personalizados
- Ver logs de automatización en tiempo real
- Métricas de efectividad (open rates, response rates)

---

## 🔧 DETALLES TÉCNICOS DE IMPLEMENTACIÓN

### **1. ESTRUCTURA DE ARCHIVOS FINAL CRM:**

```
crmventas/
├── frontend_react/
│   ├── src/
│   │   ├── views/marketing/
│   │   │   ├── MarketingHubView.tsx      # Dashboard marketing
│   │   │   └── MetaTemplatesView.tsx     # HSM automation
│   │   ├── components/marketing/
│   │   │   ├── MarketingPerformanceCard.tsx
│   │   │   ├── MetaConnectionWizard.tsx
│   │   │   └── MetaTokenBanner.tsx
│   │   └── components/Sidebar.tsx        # Actualizado con nuevos items
│
└── orchestrator_service/
    ├── services/
    │   ├── meta_ads_service.py           # Cliente Graph API
    │   ├── marketing_service.py          # Lógica ROI/estadísticas
    │   └── automation_service.py         # HSM automation
    ├── routes/
    │   ├── marketing.py                  # Endpoints marketing
    │   └── auth.py                       # Endpoints OAuth Meta
    └── db/
        └── migrations/                   # Migraciones BD
```

### **2. ENDPOINTS API CRM MARKETING:**

```
GET    /crm/marketing/stats           # Dashboard principal
GET    /crm/marketing/stats/roi       # ROI específico
GET    /crm/marketing/token-status    # Estado conexión Meta
GET    /crm/marketing/meta-portfolios # Listar Business Managers
GET    /crm/marketing/meta-accounts   # Listar cuentas anuncios
POST   /crm/marketing/connect         # Conectar cuenta a tenant
GET    /crm/marketing/automation-logs # Logs HSM automation
POST   /crm/marketing/automation/trigger # Disparar automation manual
GET    /crm/auth/meta/url             # URL OAuth
GET    /crm/auth/meta/callback        # Callback OAuth
POST   /crm/auth/meta/disconnect      # Desconectar Meta
```

### **3. CÁLCULO ROI PARA CRM:**

```python
# Fórmula adaptada para ventas
def calculate_roi_crm(tenant_id, time_range):
    # 1. Leads atribuidos a Meta Ads
    meta_leads = db.query("""
        SELECT COUNT(*) FROM leads 
        WHERE tenant_id = $1 AND lead_source = 'META_ADS'
        AND created_at >= NOW() - $2::interval
    """)
    
    # 2. Oportunidades generadas
    opportunities = db.query("""
        SELECT COUNT(DISTINCT o.id) 
        FROM opportunities o
        JOIN leads l ON o.lead_id = l.id
        WHERE l.tenant_id = $1 AND l.lead_source = 'META_ADS'
        AND o.created_at >= NOW() - $2::interval
    """)
    
    # 3. Ventas cerradas (ingresos)
    total_revenue = db.query("""
        SELECT SUM(amount) 
        FROM sales_transactions t
        JOIN leads l ON t.lead_id = l.id
        WHERE l.tenant_id = $1 AND l.lead_source = 'META_ADS'
        AND t.status = 'completed'
        AND t.created_at >= NOW() - $2::interval
    """)
    
    # 4. Inversión (spend) desde Meta API
    total_spend = get_meta_spend(tenant_id, time_range)
    
    # 5. Cálculos finales
    cpa = total_spend / meta_leads if meta_leads > 0 else 0
    roi = ((total_revenue - total_spend) / total_spend * 100) if total_spend > 0 else 0
    
    return {
        "leads": meta_leads,
        "opportunities": opportunities,
        "sales_revenue": total_revenue,
        "marketing_spend": total_spend,
        "cpa": cpa,
        "roi_percentage": roi
    }
```

### **4. COMPONENTES REACT A ADAPTAR:**

#### **MarketingHubView.tsx - Cambios clave:**
```typescript
// Terminología CRM
const metrics = {
  // ClinicForge: patients, appointments, dental revenue
  // CRM Sales: leads, opportunities, sales revenue
  leads: stats?.leads || 0,
  opportunities: stats?.opportunities || 0,
  revenue: stats?.sales_revenue || 0,
  spend: stats?.marketing_spend || 0,
  roi: stats?.roi_percentage || 0
};

// Tablas adaptadas
const tableColumns = [
  { header: 'Campaña/Anuncio', accessor: 'ad_name' },
  { header: 'Inversión', accessor: 'spend' },
  { header: 'Leads', accessor: 'leads' },
  { header: 'Oportunidades', accessor: 'opportunities' }, // En lugar de "Citas"
  { header: 'ROI', accessor: 'roi' },
  { header: 'Estado', accessor: 'status' }
];
```

#### **MetaTemplatesView.tsx - HSM Automation CRM:**
```typescript
// Triggers adaptados para ventas
const automationRules = [
  {
    id: 'lead_followup',
    name: 'Seguimiento automático de leads',
    description: 'Envía WhatsApp 24h después de crear lead',
    enabled: true
  },
  {
    id: 'opportunity_reminder', 
    name: 'Recordatorio de oportunidad',
    description: 'Notifica 2h antes de deadline',
    enabled: true
  },
  {
    id: 'post_sale_feedback',
    name: 'Feedback post-venta',
    description: 'Solicita feedback 7 días después de venta',
    enabled: true
  }
];
```

---

## 📋 CHECKLIST DE IMPLEMENTACIÓN

### **BACKEND (FastAPI)**
- [ ] Copiar `meta_ads_service.py` de ClinicForge
- [ ] Adaptar `marketing_service.py` para CRM (leads vs patients)
- [ ] Crear `routes/marketing.py` con endpoints CRM
- [ ] Implementar endpoints OAuth (`/crm/auth/meta/*`)
- [ ] Configurar sistema de credenciales multi-tenant
- [ ] Crear migraciones BD para campos marketing
- [ ] Implementar `automation_service.py` con triggers CRM

### **FRONTEND (React)**
- [ ] Crear carpeta `src/views/marketing/`
- [ ] Adaptar `MarketingHubView.tsx` para CRM
- [ ] Adaptar `MetaTemplatesView.tsx` para HSM CRM
- [ ] Copiar y adaptar componentes marketing
- [ ] Actualizar `Sidebar.tsx` con nuevos items
- [ ] Agregar rutas en `App.tsx`
- [ ] Actualizar traducciones (i18n) para términos marketing
- [ ] Implementar wizard de conexión Meta

### **BASE DE DATOS**
- [ ] Agregar `lead_source` a tabla `leads`
- [ ] Agregar campos Meta IDs a `leads`
- [ ] Crear tabla `automation_logs`
- [ ] Crear tabla `sales_transactions` (si no existe)
- [ ] Verificar sistema `credentials` para tokens OAuth

### **INTEGRACIÓN META ADS**
- [ ] Crear App en Meta Developers
- [ ] Configurar OAuth redirect URI
- [ ] Solicitar permisos: `ads_management`, `business_management`
- [ ] Configurar variables de entorno
- [ ] Probar flujo completo OAuth
- [ ] Probar obtención de datos Graph API

### **HSM AUTOMATION (WhatsApp)**
- [ ] Configurar WhatsApp Business API
- [ ] Crear templates aprobados para CRM
- [ ] Implementar sistema de triggers
- [ ] Crear panel de configuración HSM
- [ ] Implementar logging y métricas

---

## ⚡ PLAN DE EJECUCIÓN RÁPIDO

### **DÍA 1: Infraestructura Backend**
1. Migrar servicios de ClinicForge
2. Adaptar terminología para CRM
3. Crear endpoints básicos
4. Configurar BD

### **DÍA 2: Frontend y UI**
1. Migrar componentes React
2. Adaptar vistas para CRM
3. Integrar en sidebar
4. Configurar routing

### **DÍA 3: Integración Meta OAuth**
1. Configurar App Meta Developers
2. Implementar flujo OAuth completo
3. Probar conexión y obtención de datos
4. Implementar desconexión

### **DÍA 4: HSM Automation**
1. Configurar WhatsApp Business API
2. Implementar triggers CRM
3. Crear panel de configuración
4. Probar automatización end-to-end

### **DÍA 5: Testing y Depuración**
1. Probar flujo completo
2. Depurar problemas de integración
3. Optimizar performance
4. Documentar uso

---

## 🚨 RIESGOS Y CONSIDERACIONES

### **Riesgos Técnicos:**
1. **Diferencias de modelo de datos:** ClinicForge (salud) vs CRM (ventas)
2. **Permisos Meta API:** Necesarios `ads_management`, `business_management`
3. **Rate limiting:** Graph API tiene límites estrictos
4. **WhatsApp templates:** Requieren aprobación previa de Meta

### **Consideraciones de Negocio:**
1. **Privacidad datos:** Tokens OAuth deben almacenarse seguros
2. **Multi-tenant:** Cada cliente debe tener sus propias credenciales
3. **Costo:** WhatsApp Business API tiene costos por mensaje
4. **Compliance:** Regulaciones de marketing y privacidad

### **Mitigaciones:**
- Usar mismo sistema de credenciales que ClinicForge (probado)
- Implementar caching para evitar rate limits
- Logging detallado para debugging
- Fallback graceful cuando Meta API falle

---

## 📈 MÉTRICAS DE ÉXITO

### **Técnicas:**
- ✅ Conexión OAuth funcional en < 2 minutos
- ✅ Dashboard carga datos Meta en < 3 segundos
- ✅ HSM automation envía mensajes en < 10 segundos del trigger
- ✅ Sistema maneja rate limits sin caídas

### **De Negocio:**
- 📊 ROI visible en dashboard marketing
- 🤖 Automatización reduce trabajo manual de follow-ups
- 🔍 Atribución clara de leads a campañas Meta
- 💬 Mejora en tasa de respuesta con HSM automation

---

## 🎯 CONCLUSIÓN

La implementación de **Marketing Hub** y **HSM Automation** de ClinicForge en CRM Sales es **altamente factible** debido a:

1. **Arquitectura similar:** Ambos usan FastAPI + React + PostgreSQL
2. **Código reusable:** 80% del código de ClinicForge es transferible
3. **Patrones probados:** OAuth flow y Graph API ya funcionan en producción
4. **Multi-tenant ready:** Sistema de credenciales ya soporta multi-tenant

**Esfuerzo estimado:** 5 días de desarrollo intensivo
**Complejidad:** Media-Alta (principalmente adaptación de terminología)
**Riesgo:** Bajo-Medio (código ya probado en ClinicForge)

**Recomendación:** Proceder con la implementación siguiendo el plan faseado. Comenzar con backend, luego frontend, luego integraciones.

---

## 📞 SOPORTE Y DEBUGGING

### **Problemas comunes esperados:**
1. **OAuth errors:** Verificar redirect URI y App ID/Secret
2. **Graph API 401:** Tokens expirados (renovar cada 60 días)
3. **Zero data en dashboard:** Verificar permisos `ads_management`
4. **HSM no envía:** Verificar templates aprobados y phone numbers

### **Herramientas de debugging:**
- `meta_diagnostic.py` (de ClinicForge) adaptado para CRM
- Logs detallados en `marketing_service.py`
- Graph API Explorer de Meta para testing manual
- Webhooks para debug de WhatsApp messages

---

**Documentación creada por:** DevFusa  
**Fecha:** 25 de Febrero 2026  
**Repositorio:** CRM Ventas  
**Estado:** Listo para implementación  

*"Del código probado en ClinicForge al CRM Sales en 5 días."*