# 🎯 SPECIFICATION: META ADS SPRINTS 1 & 2 IMPLEMENTATION

## 📊 EXECUTIVE SUMMARY

**Project:** Implement Meta Ads Marketing Hub & HSM Automation in CRM Ventas  
**Sprints:** 1 (Backend) + 2 (Frontend) = 6 days  
**Source:** ClinicForge production code (adapt for CRM)  
**Target:** CRM Ventas with Nexus v7.7.1 security  
**Status:** Ready for implementation  

---

## 🎯 BUSINESS REQUIREMENTS

### **Primary Goals:**
1. **Marketing Hub Dashboard** - Real-time Meta Ads performance metrics
2. **HSM Automation** - WhatsApp automation for sales follow-ups
3. **Meta OAuth Integration** - Secure account connection
4. **ROI Tracking** - Measure marketing investment vs sales revenue

### **User Stories:**
```
As a CEO, I want to see ROI from Meta Ads campaigns
So that I can optimize marketing spend

As a Sales Manager, I want automated WhatsApp follow-ups
So that leads don't fall through the cracks

As a Marketing Specialist, I want campaign performance data
So that I can adjust targeting and creatives
```

### **Success Metrics:**
- ✅ Marketing Hub loads in < 3 seconds
- ✅ HSM automation reduces manual follow-ups by 40%
- ✅ ROI calculation accurate within 5%
- ✅ OAuth connection works in < 2 minutes

---

## 🏗️ TECHNICAL ARCHITECTURE

### **System Context:**
```
ClinicForge (Source) → CRM Ventas (Target)
├── Backend: FastAPI → FastAPI (same)
├── Frontend: React → React (same)
├── Database: PostgreSQL → PostgreSQL (same)
└── Security: Nexus v7.7.1 → Nexus v7.7.1 (already implemented)
```

### **Adaptation Mapping:**
| ClinicForge | CRM Ventas | Notes |
|-------------|------------|-------|
| `patients` | `leads` | Primary entity |
| `appointments` | `opportunities` | Conversion step |
| `dental revenue` | `sales revenue` | Financial metric |
| `clinic` | `account` / `business` | Tenant context |
| `acquisition_source` | `lead_source` | Attribution field |
| `professional` | `seller` / `closer` | User role |

### **Security Context:**
- ✅ Nexus v7.7.1 already implemented
- ✅ HttpOnly Cookies for XSS protection
- ✅ Rate limiting active
- ✅ Audit logging with `system_events`
- ✅ Multi-tenant isolation enforced

---

## 📅 SPRINT 1: BACKEND INFRASTRUCTURE (3 DAYS)

### **DAY 1: SERVICE MIGRATION**

#### **1.1 Directory Structure:**
```
orchestrator_service/
├── services/marketing/           # New directory
│   ├── meta_ads_service.py      # Graph API client
│   ├── marketing_service.py     # ROI calculations
│   └── automation_service.py    # HSM automation
├── routes/
│   ├── marketing.py             # Marketing endpoints
│   └── meta_auth.py             # OAuth endpoints
└── core/credentials.py          # Already exists (Nexus v7.7.1)
```

#### **1.2 Copy Services from ClinicForge:**
```bash
# From CRM Ventas root directory
cp ../clinicforge/orchestrator_service/services/meta_ads_service.py orchestrator_service/services/marketing/
cp ../clinicforge/orchestrator_service/services/marketing_service.py orchestrator_service/services/marketing/
cp ../clinicforge/orchestrator_service/services/automation_service.py orchestrator_service/services/marketing/
```

#### **1.3 Adapt Terminology in Services:**
```python
# File: marketing_service.py
# Global replacements:
# patients → leads
# appointments → opportunities
# dental → sales
# clinic → account
# acquisition_source → lead_source
# professional → seller/closer

# Example adaptation:
def calculate_roi_crm(tenant_id: int, time_range: str) -> Dict:
    """
    Adapted ROI formula for CRM Sales:
    1. Meta Ads attributed leads
    2. Opportunities generated
    3. Sales closed (revenue)
    4. Meta Ads spend
    5. ROI = (revenue - spend) / spend * 100
    """
```

#### **1.4 Dependencies:**
```bash
# Add to requirements.txt
echo "facebook-business==19.0.0" >> orchestrator_service/requirements.txt
echo "cryptography==42.0.5" >> orchestrator_service/requirements.txt
echo "redis==5.0.1" >> orchestrator_service/requirements.txt

# Install
pip install facebook-business cryptography redis
```

### **DAY 2: ENDPOINTS & ROUTES**

#### **2.1 Create Marketing Routes:**
```python
# File: orchestrator_service/routes/marketing.py
from fastapi import APIRouter, Depends
from typing import Optional

router = APIRouter()

# Required endpoints:
@router.get("/stats")                    # Dashboard metrics
@router.get("/stats/roi")               # ROI details
@router.get("/token-status")            # Meta connection status
@router.get("/meta-portfolios")         # Business Managers
@router.get("/meta-accounts")           # Ad accounts
@router.post("/connect")                # Connect Meta account
@router.get("/automation-logs")         # HSM automation logs
@router.get("/hsm/templates")           # WhatsApp templates
@router.get("/automation/rules")        # Automation rules
```

#### **2.2 Create Meta Auth Routes:**
```python
# File: orchestrator_service/routes/meta_auth.py
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

router = APIRouter()

@router.get("/url")                     # OAuth authorization URL
async def get_meta_auth_url(...):
    # Generate OAuth URL with state=tenant_{id}

@router.get("/callback")                # OAuth callback handler
async def meta_auth_callback(...):
    # Exchange code for token, save to credentials

@router.post("/disconnect")             # Disconnect Meta account
async def disconnect_meta(...):
    # Remove token from credentials
```

#### **2.3 Integrate in Main Application:**
```python
# File: orchestrator_service/main.py
from routes.marketing import router as marketing_router
from routes.meta_auth import router as meta_auth_router

app.include_router(marketing_router, prefix="/crm/marketing", tags=["Marketing"])
app.include_router(meta_auth_router, prefix="/crm/auth/meta", tags=["Meta OAuth"])
```

#### **2.4 Apply Security Measures:**
```python
# All endpoints must have:
@audit_access("action_name")            # Audit logging
@limiter.limit("100/minute")            # Rate limiting
user_data=Depends(verify_admin_token)   # Authentication
tenant_id=Depends(get_resolved_tenant_id) # Multi-tenant isolation
```

### **DAY 3: DATABASE MIGRATIONS**

#### **3.1 SQL Migration Script:**
```sql
-- File: migrations/meta_ads_migration.sql
BEGIN;

-- 1. Add fields to leads table
ALTER TABLE leads ADD COLUMN IF NOT EXISTS lead_source VARCHAR(50) DEFAULT 'ORGANIC';
ALTER TABLE leads ADD COLUMN IF NOT EXISTS meta_campaign_id VARCHAR(255);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS meta_ad_id VARCHAR(255);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS meta_ad_headline TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS meta_ad_body TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS external_ids JSONB DEFAULT '{}';

-- 2. Create marketing tables
CREATE TABLE IF NOT EXISTS meta_ads_campaigns (...);
CREATE TABLE IF NOT EXISTS meta_ads_insights (...);
CREATE TABLE IF NOT EXISTS meta_templates (...);
CREATE TABLE IF NOT EXISTS automation_rules (...);
CREATE TABLE IF NOT EXISTS automation_logs (...);

-- 3. Create indexes
CREATE INDEX IF NOT EXISTS idx_leads_lead_source ON leads(lead_source);
CREATE INDEX IF NOT EXISTS idx_leads_meta_campaign ON leads(meta_campaign_id);

COMMIT;
```

#### **3.2 Execute Migration:**
```bash
psql -h localhost -U postgres -d crmventas -f migrations/meta_ads_migration.sql

# Verify
psql -h localhost -U postgres -d crmventas -c "\dt meta_*"
psql -h localhost -U postgres -d crmventas -c "\df calculate_*"
```

#### **3.3 Backend Testing:**
```python
# File: test_marketing_backend.py
import pytest
from fastapi.testclient import TestClient

def test_marketing_stats_endpoint():
    """Test /crm/marketing/stats endpoint."""
    headers = {"Authorization": "Bearer test", "X-Admin-Token": "test"}
    response = client.get("/crm/marketing/stats", headers=headers)
    assert response.status_code in [200, 401]

def test_meta_auth_url():
    """Test /crm/auth/meta/url endpoint."""
    headers = {"Authorization": "Bearer test", "X-Admin-Token": "test"}
    response = client.get("/crm/auth/meta/url", headers=headers)
    assert response.status_code in [200, 401]
```

---

## 📅 SPRINT 2: FRONTEND & UI (3 DAYS)

### **DAY 4: COMPONENT MIGRATION**

#### **4.1 Frontend Directory Structure:**
```
frontend_react/
├── src/
│   ├── views/marketing/           # New directory
│   │   ├── MarketingHubView.tsx   # Main dashboard
│   │   └── MetaTemplatesView.tsx  # HSM automation
│   ├── components/marketing/      # New directory
│   │   ├── MarketingPerformanceCard.tsx
│   │   ├── AdContextCard.tsx
│   │   ├── MetaConnectionWizard.tsx
│   │   └── MetaTokenBanner.tsx
│   ├── api/marketing.ts          # API client
│   └── types/marketing.ts        # TypeScript interfaces
```

#### **4.2 Copy Components from ClinicForge:**
```bash
# From frontend_react directory
cp ../../clinicforge/frontend_react/src/views/MarketingHubView.tsx src/views/marketing/
cp ../../clinicforge/frontend_react/src/views/MetaTemplatesView.tsx src/views/marketing/
cp ../../clinicforge/frontend_react/src/components/MarketingPerformanceCard.tsx src/components/marketing/
cp ../../clinicforge/frontend_react/src/components/AdContextCard.tsx src/components/marketing/
cp ../../clinicforge/frontend_react/src/components/integrations/MetaConnectionWizard.tsx src/components/marketing/
cp ../../clinicforge/frontend_react/src/components/MetaTokenBanner.tsx src/components/marketing/
```

#### **4.3 Adapt Terminology in Frontend:**
```typescript
// File: MarketingHubView.tsx
// Global replacements:
// patients → leads
// appointments → opportunities
// dental revenue → sales revenue
// clinic → account

// Example:
const [stats, setStats] = useState<MarketingStats | null>(null);
// Change interface to use leads instead of patients
```

#### **4.4 Update API Calls:**
```typescript
// File: MarketingHubView.tsx
const loadMarketingData = async () => {
  try {
    // Change from: /admin/marketing/stats
    // Change to: /crm/marketing/stats
    const response = await api.get(`/crm/marketing/stats?time_range=${timeRange}`);
    setStats(response.data);
  } catch (error) {
    console.error('Error loading marketing data:', error);
  }
};
```

### **DAY 5: SIDEBAR INTEGRATION & ROUTING**

#### **5.1 Update Sidebar:**
```typescript
// File: src/components/Sidebar.tsx
import { Megaphone, Layout } from 'lucide-react';

// Add to menuItems array:
{
  id: 'marketing',
  labelKey: 'nav.marketing' as const,
  icon: <Megaphone size={20} />,
  path: '/crm/marketing',
  roles: ['ceo', 'admin', 'marketing'] as const
},
{
  id: 'hsm_automation',
  labelKey: 'nav.hsm_automation' as const,
  icon: <Layout size={20} />,
  path: '/crm/hsm',
  roles: ['ceo', 'admin'] as const
}
```

#### **5.2 Update App Routing:**
```typescript
// File: src/App.tsx
import MarketingHubView from './views/marketing/MarketingHubView';
import MetaTemplatesView from './views/marketing/MetaTemplatesView';

// Add routes inside Layout:
<Route path="crm/marketing" element={<MarketingHubView />} />
<Route path="crm/hsm" element={<MetaTemplatesView />} />
```

#### **5.3 Update i18n Translations:**
```typescript
// File: src/i18n/translations.ts
export const translations = {
  es: {
    nav: {
      marketing: 'Marketing Hub',
      hsm_automation: 'HSM Automation'
    },
    marketing: {
      leads: 'Leads',
      opportunities: 'Oportunidades',
      revenue: 'Ingresos',
      roi: 'ROI'
    }
  },
  en: {
    // English translations
  }
};
```

#### **5.4 Create API Client:**
```typescript
// File: src/api/marketing.ts
import api from './axios';

export const marketingApi = {
  getStats: (timeRange: string = '7d') => 
    api.get(`/crm/marketing/stats?time_range=${timeRange}`),
  
  getRoiDetails: () => 
    api.get('/crm/marketing/stats/roi'),
  
  getTokenStatus: () => 
    api.get('/crm/marketing/token-status'),
  
  getMetaAccounts: (portfolioId?: string) => 
    api.get('/crm/marketing/meta-accounts', { params: { portfolio_id: portfolioId } }),
  
  connectMetaAccount: (data: { account_id: string; account_name: string }) => 
    api.post('/crm/marketing/connect', data),
  
  getHSMTemplates: () => 
    api.get('/crm/marketing/hsm/templates'),
  
  getAutomationRules: () => 
    api.get('/crm/marketing/automation/rules'),
  
  getMetaAuthUrl: () => 
    api.get('/crm/auth/meta/url'),
  
  disconnectMeta: () => 
    api.post('/crm/auth/meta/disconnect')
};
```

#### **5.5 Create TypeScript Interfaces:**
```typescript
// File: src/types/marketing.ts
export interface MarketingStats {
  leads: number;
  leads_change: number;
  opportunities: number;
  opportunities_change: number;
  sales_revenue: number;
  revenue_change: number;
  marketing_spend: number;
  spend_change: number;
  roi_percentage: number;
  roi_change: number;
  cpa: number;
}

export interface CampaignStat {
  id: string;
  name: string;
  status: 'ACTIVE' | 'PAUSED' | 'DELETED';
  spend: number;
  leads: number;
  opportunities: number;
  revenue: number;
  roi: number;
  cpa: number;
}

export interface HSMTemplate {
  id: string;
  name: string;
  category: string;
  language: string;
  status: 'APPROVED' | 'PENDING' | 'REJECTED';
  components: any[];
}
```

### **DAY 6: TESTING & OPTIMIZATION**

#### **6.1 Component Testing:**
```typescript
// File: src/__tests__/MarketingPerformanceCard.test.tsx
import { render, screen } from '@testing-library/react';
import { MarketingPerformanceCard } from '../components/marketing/MarketingPerformanceCard';
import { Users } from 'lucide-react';

describe('MarketingPerformanceCard', () => {
  it('renders title and value correctly', () => {
    render(
      <MarketingPerformanceCard
        title="Leads"
        value={150}
        icon={<Users />}
      />
    );
    
    expect(screen.getByText('Leads')).toBeInTheDocument();
    expect(screen.getByText('150')).toBeInTheDocument();
  });
});
```

#### **6.2 View Testing:**
```typescript
// File: src/__tests__/MarketingHubView.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import { MarketingHubView } from '../views/marketing/MarketingHubView';
import { marketingApi } from '../api/marketing';

jest.mock('../api/marketing');

describe('MarketingHubView', () => {
  beforeEach(() => {
    (marketingApi.getStats as jest.Mock).mockResolvedValue({
      data: {
        leads: 150,
        opportunities: 45,
        sales_revenue: 25000,
        marketing_spend: 5000,
        roi_percentage: 400,
        cpa: 33.33
      }
    });
  });

  it('loads and displays marketing data', async () => {
    render(<MarketingHubView />);
    
    await waitFor(() => {
      expect(screen.getByText('Marketing Hub')).toBeInTheDocument();
      expect(screen.getByText('150')).toBeInTheDocument();
      expect(screen.getBy