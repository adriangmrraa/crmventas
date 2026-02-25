# 🚀 META ADS DEVELOPMENT ROADMAP - CRM VENTAS

## 📊 RESUMEN EJECUTIVO

**Objetivo:** Implementar **Meta Ads Marketing Hub** y **HSM Automation** de ClinicForge en CRM Ventas como dos páginas funcionales completamente integradas.

**Estado Actual:**
- ✅ **ClinicForge:** Sistema completo funcionando en producción
- ⚠️ **CRM Ventas:** Sin funcionalidades de marketing
- 🔄 **Migración:** Transferir 2 vistas + componentes + servicios + endpoints

**Repositorios Accesibles:**
1. **Origen:** `adriangmrraa/clinicforge` (sistema completo)
2. **Destino:** `adriangmrraa/crmventas` (CRM básico)

---

## 🎯 COMPONENTES A IMPLEMENTAR

### **1. MARKETING HUB (Meta Ads Dashboard)**
- **Vista:** `MarketingHubView.tsx`
- **Componentes:** `MarketingPerformanceCard.tsx`, `AdContextCard.tsx`
- **Servicios:** `meta_ads_service.py`, `marketing_service.py`
- **Endpoints:** `/crm/marketing/*`

### **2. HSM AUTOMATION (Meta Templates)**
- **Vista:** `MetaTemplatesView.tsx`
- **Componentes:** `MetaConnectionWizard.tsx`, `MetaTokenBanner.tsx`
- **Servicios:** `automation_service.py`
- **Endpoints:** `/crm/hsm/*`

---

## 📅 PLAN DE IMPLEMENTACIÓN - 4 SPRINTS

### **SPRINT 1: INFRAESTRUCTURA BACKEND (3 días)**

#### **Día 1: Migración de Servicios**
```bash
# 1. Copiar servicios de ClinicForge
cp clinicforge/orchestrator_service/services/meta_ads_service.py crmventas/orchestrator_service/services/
cp clinicforge/orchestrator_service/services/marketing_service.py crmventas/orchestrator_service/services/
cp clinicforge/orchestrator_service/services/automation_service.py crmventas/orchestrator_service/services/

# 2. Adaptar terminología para CRM
# patients → leads, appointments → opportunities, dental → sales
```

#### **Día 2: Endpoints y Rutas**
```bash
# 1. Crear routes/marketing.py basado en ClinicForge
# 2. Crear routes/meta_auth.py para OAuth
# 3. Integrar en main.py
```

#### **Día 3: Base de Datos**
```sql
-- 1. Agregar campos a leads
ALTER TABLE leads ADD COLUMN lead_source VARCHAR(50);
ALTER TABLE leads ADD COLUMN meta_ad_id VARCHAR(100);
ALTER TABLE leads ADD COLUMN meta_campaign_id VARCHAR(100);

-- 2. Crear tablas de marketing
CREATE TABLE meta_ads_campaigns (...);
CREATE TABLE meta_ads_insights (...);
CREATE TABLE automation_logs (...);
```

### **SPRINT 2: FRONTEND Y UI (3 días)**

#### **Día 4: Migración de Componentes**
```bash
# 1. Crear estructura de marketing
mkdir -p frontend_react/src/views/marketing/
mkdir -p frontend_react/src/components/marketing/

# 2. Copiar y adaptar vistas
cp clinicforge/frontend_react/src/views/MarketingHubView.tsx crmventas/frontend_react/src/views/marketing/
cp clinicforge/frontend_react/src/views/MetaTemplatesView.tsx crmventas/frontend_react/src/views/marketing/
```

#### **Día 5: Integración en Sidebar**
```typescript
// En Sidebar.tsx - Agregar nuevos items
{
  id: 'marketing',
  labelKey: 'nav.marketing',
  icon: <Megaphone size={20} />,
  path: '/crm/marketing',
  roles: ['ceo', 'admin']
},
{
  id: 'hsm_automation',
  labelKey: 'nav.hsm_automation',
  icon: <Layout size={20} />,
  path: '/crm/hsm',
  roles: ['ceo']
}
```

#### **Día 6: Routing y Estado**
```typescript
// En App.tsx - Agregar rutas
<Route path="crm/marketing" element={<MarketingHubView />} />
<Route path="crm/hsm" element={<MetaTemplatesView />} />
```

### **SPRINT 3: INTEGRACIÓN META OAUTH (2 días)**

#### **Día 7: Configuración OAuth**
```bash
# 1. Crear App en Meta Developers
# 2. Configurar redirect URI
# 3. Solicitar permisos: ads_management, business_management
```

#### **Día 8: Implementación Flujo Completo**
```python
# 1. Endpoints OAuth: /crm/auth/meta/url, /crm/auth/meta/callback
# 2. Sistema de tokens multi-tenant
# 3. Wizard de conexión en frontend
```

### **SPRINT 4: TESTING Y DEPLOYMENT (2 días)**

#### **Día 9: Testing Integral**
```bash
# 1. Testing de endpoints
# 2. Testing de componentes
# 3. Testing de integración OAuth
# 4. Testing de performance
```

#### **Día 10: Deployment y Monitoreo**
```bash
# 1. Deploy a producción
# 2. Configurar monitoring
# 3. Documentación final
```

---

## 🗂️ ESTRUCTURA DE ARCHIVOS FINAL

### **BACKEND CRM VENTAS:**
```
orchestrator_service/
├── services/
│   ├── meta_ads_service.py      # Cliente Graph API
│   ├── marketing_service.py     # Lógica ROI/estadísticas
│   └── automation_service.py    # HSM automation
├── routes/
│   ├── marketing.py             # Endpoints marketing
│   └── meta_auth.py             # Endpoints OAuth
└── db.py                        # Migraciones
```

### **FRONTEND CRM VENTAS:**
```
frontend_react/
├── src/
│   ├── views/marketing/
│   │   ├── MarketingHubView.tsx     # Dashboard marketing
│   │   └── MetaTemplatesView.tsx    # HSM automation
│   ├── components/marketing/
│   │   ├── MarketingPerformanceCard.tsx
│   │   ├── AdContextCard.tsx
│   │   ├── MetaConnectionWizard.tsx
│   │   └── MetaTokenBanner.tsx
│   └── components/Sidebar.tsx       # Actualizado
```

### **BASE DE DATOS:**
```sql
-- Tablas nuevas
meta_ads_campaigns
meta_ads_insights
automation_logs
meta_templates

-- Campos nuevos en leads
lead_source
meta_ad_id
meta_campaign_id
meta_ad_headline
meta_ad_body
```

---

## 🔗 DEPENDENCIAS ENTRE COMPONENTES

### **Dependencias Backend:**
```
meta_ads_service.py
    ├── marketing_service.py
    └── routes/marketing.py
        └── main.py
```

### **Dependencias Frontend:**
```
MarketingHubView.tsx
    ├── MarketingPerformanceCard.tsx
    ├── AdContextCard.tsx
    └── api/marketing.ts
```

### **Dependencias Database:**
```
leads (tabla existente)
    └── meta_ads_campaigns (FK)
        └── meta_ads_insights (FK)
```

---

## 📋 CHECKLIST POR SPRINT

### **SPRINT 1 - Backend (3 días)**
- [ ] Servicios migrados y adaptados
- [ ] Endpoints creados
- [ ] Base de datos actualizada
- [ ] Testing unitario backend

### **SPRINT 2 - Frontend (3 días)**
- [ ] Componentes migrados y adaptados
- [ ] Sidebar actualizado
- [ ] Routing configurado
- [ ] Testing unitario frontend

### **SPRINT 3 - Integración (2 días)**
- [ ] OAuth configurado en Meta
- [ ] Flujo completo implementado
- [ ] Tokens multi-tenant funcionando
- [ ] Testing de integración

### **SPRINT 4 - Finalización (2 días)**
- [ ] Testing integral completo
- [ ] Performance optimizado
- [ ] Documentación actualizada
- [ ] Deploy a producción

---

## ⚠️ RIESGOS Y MITIGACIONES

### **Riesgos Técnicos:**
1. **Diferencias de modelo de datos:** ClinicForge (salud) vs CRM (ventas)
   - **Mitigación:** Mapeo claro: patients→leads, appointments→opportunities

2. **Permisos Meta API:** Necesarios `ads_management`, `business_management`
   - **Mitigación:** Solicitar todos los permisos desde el inicio

3. **Rate limiting Graph API:** Límites estrictos de Meta
   - **Mitigación:** Implementar caching y manejo de errores

### **Riesgos de Negocio:**
1. **Costo WhatsApp Business API:** Costos por mensaje
   - **Mitigación:** Configurar límites de envíos automáticos

2. **Compliance marketing:** Regulaciones de privacidad
   - **Mitigación:** Implementar consentimiento explícito

### **Mitigaciones Específicas:**
- **Rollback Plan:** Poder revertir cambios rápidamente
- **Feature Flags:** Activar gradualmente
- **Monitoring:** Alertas tempranas para problemas

---

## 📊 MÉTRICAS DE ÉXITO

### **Técnicas:**
- ✅ Conexión OAuth funcional en < 2 minutos
- ✅ Dashboard carga datos en < 3 segundos
- ✅ HSM automation envía mensajes en < 10 segundos
- ✅ 0 errores en producción primera semana

### **De Negocio:**
- 📊 ROI visible en dashboard marketing
- 🤖 Automatización reduce trabajo manual 40%
- 🔍 Atribución clara de leads a campañas
- 💬 Mejora en tasa de respuesta con HSM

### **De Usuario:**
- 🎯 UX intuitiva para no técnicos
- 🔄 Flujos completos sin interrupciones
- 📱 Responsive en desktop y mobile
- 🚀 Performance aceptable en conexiones lentas

---

## 🧪 PLAN DE TESTING

### **Testing Backend:**
```bash
# 1. Unit testing servicios
pytest tests/services/test_meta_ads_service.py

# 2. Integration testing endpoints
pytest tests/routes/test_marketing.py

# 3. OAuth flow testing
python3 test_oauth_flow.py
```

### **Testing Frontend:**
```bash
# 1. Component testing
npm test -- MarketingHubView.test.tsx

# 2. Integration testing
npm run test:integration

# 3. E2E testing
npm run test:e2e
```

### **Testing Performance:**
```bash
# 1. Load testing endpoints
k6 run load_test_marketing.js

# 2. Graph API rate limit testing
python3 test_rate_limits.py
```

---

## 📞 SOPORTE Y DEBUGGING

### **Problemas Comunes Esperados:**
1. **OAuth errors:** Verificar redirect URI y App ID/Secret
2. **Graph API 401:** Tokens expirados (renovar cada 60 días)
3. **Zero data en dashboard:** Verificar permisos `ads_management`
4. **HSM no envía:** Verificar templates aprobados

### **Herramientas de Debugging:**
- **Meta Debug Tool:** `debug_meta_ads.py` (de ClinicForge)
- **Graph API Explorer:** Testing manual de endpoints
- **Logs detallados:** `marketing_service.py` con logging nivel DEBUG
- **Webhooks debug:** Testing de WhatsApp messages

### **Procedimiento de Troubleshooting:**
```
1. Verificar tokens OAuth (validez, permisos)
2. Verificar conexión Graph API (health check)
3. Verificar datos en base de datos
4. Verificar frontend state y API calls
5. Revisar logs de aplicación
```

---

## 🎯 CONCLUSIÓN

### **Esfuerzo Total Estimado: 10 días**
### **Complejidad: Media-Alta** (integración con APIs externas)
### **Riesgo: Medio** (código ya probado en ClinicForge)

### **Recomendaciones:**
1. **Seguir plan sprint por sprint**
2. **Testing continuo desde día 1**
3. **Feature flags para rollout gradual**
4. **Monitoring intensivo primera semana**

### **Valor de Negocio:**
- **ROI medible** desde primera campaña
- **Automatización** que escala sin costo humano
- **Atribución** que justifica inversión en marketing
- **Competitividad** frente a otros CRMs

---

**Documentación creada por:** DevFusa  
**Fecha:** 25 de Febrero 2026  
**Repositorio:** CRM Ventas  
**Estado:** Roadmap listo para implementación  
**Versión:** 1.0 - Plan inicial

*"Del código probado en ClinicForge al CRM Ventas en 10 días."*