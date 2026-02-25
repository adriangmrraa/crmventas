# 🎨 META ADS FRONTEND IMPLEMENTATION - CRM VENTAS

## 📊 RESUMEN TÉCNICO

**Objetivo:** Implementar frontend completo para Meta Ads Marketing Hub y HSM Automation en CRM Ventas, migrando y adaptando componentes de ClinicForge.

**Componentes ClinicForge:**
- `frontend_react/src/views/MarketingHubView.tsx`
- `frontend_react/src/views/MetaTemplatesView.tsx`
- `frontend_react/src/components/MarketingPerformanceCard.tsx`
- `frontend_react/src/components/AdContextCard.tsx`
- `frontend_react/src/components/integrations/MetaConnectionWizard.tsx`
- `frontend_react/src/components/MetaTokenBanner.tsx`

---

## 🏗️ ARQUITECTURA FRONTEND

### **1. VISTAS PRINCIPALES**

#### **1.1. MarketingHubView.tsx - Dashboard Marketing**
```typescript
// Ubicación: frontend_react/src/views/marketing/MarketingHubView.tsx
// Responsabilidad: Dashboard principal de marketing con KPIs y tablas

interface MarketingHubViewProps {
  // Props opcionales si es necesario
}

const MarketingHubView: React.FC<MarketingHubViewProps> = () => {
  // Estado para datos del dashboard
  const [stats, setStats] = useState<MarketingStats | null>(null);
  const [campaigns, setCampaigns] = useState<CampaignStat[]>([]);
  const [timeRange, setTimeRange] = useState<string>('7d');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Cargar datos al montar componente
  useEffect(() => {
    loadMarketingData();
  }, [timeRange]);

  const loadMarketingData = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/crm/marketing/stats?time_range=${timeRange}`);
      setStats(response.data.summary);
      setCampaigns(response.data.campaigns);
    } catch (err) {
      setError('Error cargando datos de marketing');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6">
      {/* Header con título y filtros */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Marketing Hub</h1>
        <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
      </div>

      {/* Banner de conexión Meta (si no está conectado) */}
      <MetaTokenBanner onConnect={() => setShowWizard(true)} />

      {/* KPIs principales */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <MarketingPerformanceCard
            title="Leads"
            value={stats.leads}
            change={stats.leads_change}
            icon={<Users />}
          />
          <MarketingPerformanceCard
            title="Oportunidades"
            value={stats.opportunities}
            change={stats.opportunities_change}
            icon={<Target />}
          />
          <MarketingPerformanceCard
            title="Ingresos"
            value={formatCurrency(stats.sales_revenue)}
            change={stats.revenue_change}
            icon={<DollarSign />}
          />
          <MarketingPerformanceCard
            title="ROI"
            value={`${stats.roi_percentage.toFixed(1)}%`}
            change={stats.roi_change}
            icon={<TrendingUp />}
            variant={stats.roi_percentage >= 0 ? 'success' : 'danger'}
          />
        </div>
      )}

      {/* Tabla de campañas */}
      <CampaignsTable campaigns={campaigns} loading={loading} />

      {/* Gráficos (opcional) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        <SpendOverTimeChart data={stats?.spend_over_time} />
        <LeadsByCampaignChart data={campaigns} />
      </div>

      {/* Wizard de conexión (modal) */}
      {showWizard && (
        <MetaConnectionWizard
          onClose={() => setShowWizard(false)}
          onSuccess={() => {
            setShowWizard(false);
            loadMarketingData(); // Recargar datos
          }}
        />
      )}
    </div>
  );
};
```

#### **1.2. MetaTemplatesView.tsx - HSM Automation**
```typescript
// Ubicación: frontend_react/src/views/marketing/MetaTemplatesView.tsx
// Responsabilidad: Gestión de templates HSM y automatización

const MetaTemplatesView: React.FC = () => {
  const [templates, setTemplates] = useState<HSMTemplate[]>([]);
  const [automationRules, setAutomationRules] = useState<AutomationRule[]>([]);
  const [logs, setLogs] = useState<AutomationLog[]>([]);
  const [activeTab, setActiveTab] = useState<'templates' | 'rules' | 'logs'>('templates');

  // Cargar templates aprobados
  const loadTemplates = async () => {
    const response = await api.get('/crm/marketing/hsm/templates');
    setTemplates(response.data);
  };

  // Cargar reglas de automatización
  const loadAutomationRules = async () => {
    const response = await api.get('/crm/marketing/automation/rules');
    setAutomationRules(response.data);
  };

  // Cargar logs
  const loadLogs = async () => {
    const response = await api.get('/crm/marketing/automation/logs');
    setLogs(response.data);
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">HSM Automation</h1>

      {/* Tabs de navegación */}
      <div className="border-b mb-6">
        <nav className="-mb-px flex space-x-8">
          <button
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'templates'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
            onClick={() => setActiveTab('templates')}
          >
            Templates ({templates.length})
          </button>
          <button
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'rules'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
            onClick={() => setActiveTab('rules')}
          >
            Reglas ({automationRules.length})
          </button>
          <button
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'logs'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
            onClick={() => setActiveTab('logs')}
          >
            Logs ({logs.length})
          </button>
        </nav>
      </div>

      {/* Contenido según tab activo */}
      {activeTab === 'templates' && (
        <TemplatesList
          templates={templates}
          onRefresh={loadTemplates}
          onCreateTemplate={() => {/* abrir modal */}}
        />
      )}

      {activeTab === 'rules' && (
        <AutomationRules
          rules={automationRules}
          onRefresh={loadAutomationRules}
          onToggleRule={async (ruleId, enabled) => {
            await api.patch(`/crm/marketing/automation/rules/${ruleId}`, { enabled });
            loadAutomationRules();
          }}
        />
      )}

      {activeTab === 'logs' && (
        <AutomationLogs
          logs={logs}
          onRefresh={loadLogs}
          onFilterChange={(filters) => {
            // Aplicar filtros
          }}
        />
      )}
    </div>
  );
};
```

### **2. COMPONENTES REUSABLES**

#### **2.1. MarketingPerformanceCard.tsx**
```typescript
// Ubicación: frontend_react/src/components/marketing/MarketingPerformanceCard.tsx

interface MarketingPerformanceCardProps {
  title: string;
  value: string | number;
  change?: number; // Porcentaje de cambio
  icon: React.ReactNode;
  variant?: 'default' | 'success' | 'danger' | 'warning';
  description?: string;
}

const MarketingPerformanceCard: React.FC<MarketingPerformanceCardProps> = ({
  title,
  value,
  change,
  icon,
  variant = 'default',
  description
}) => {
  const variantClasses = {
    default: 'bg-white border-gray-200',
    success: 'bg-green-50 border-green-200',
    danger: 'bg-red-50 border-red-200',
    warning: 'bg-yellow-50 border-yellow-200'
  };

  const changeColor = change && change >= 0 ? 'text-green-600' : 'text-red-600';
  const changeIcon = change && change >= 0 ? <TrendingUp size={16} /> : <TrendingDown size={16} />;

  return (
    <div className={`border rounded-lg p-4 ${variantClasses[variant]}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          <div className="p-2 bg-gray-100 rounded-lg">
            {icon}
          </div>
          <span className="text-sm font-medium text-gray-600">{title}</span>
        </div>
        {change !== undefined && (
          <div className={`flex items-center text-sm ${changeColor}`}>
            {changeIcon}
            <span className="ml-1">{Math.abs(change)}%</span>
          </div>
        )}
      </div>
      <div className="text-2xl font-bold">{value}</div>
      {description && (
        <div className="text-xs text-gray-500 mt-1">{description}</div>
      )}
    </div>
  );
};
```

#### **2.2. CampaignsTable.tsx**
```typescript
// Ubicación: frontend_react/src/components/marketing/CampaignsTable.tsx

interface CampaignStat {
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

interface CampaignsTableProps {
  campaigns: CampaignStat[];
  loading: boolean;
  onCampaignClick?: (campaign: CampaignStat) => void;
}

const CampaignsTable: React.FC<CampaignsTableProps> = ({
  campaigns,
  loading,
  onCampaignClick
}) => {
  const columns: ColumnDef<CampaignStat>[] = [
    {
      accessorKey: 'name',
      header: 'Campaña',
      cell: ({ row }) => (
        <div className="flex items-center">
          <div className={`w-2 h-2 rounded-full mr-2 ${
            row.original.status === 'ACTIVE' ? 'bg-green-500' :
            row.original.status === 'PAUSED' ? 'bg-yellow-500' : 'bg-gray-500'
          }`} />
          <span className="font-medium">{row.original.name}</span>
        </div>
      )
    },
    {
      accessorKey: 'spend',
      header: 'Inversión',
      cell: ({ row }) => formatCurrency(row.original.spend)
    },
    {
      accessorKey: 'leads',
      header: 'Leads',
      cell: ({ row }) => row.original.leads.toLocaleString()
    },
    {
      accessorKey: 'opportunities',
      header: 'Oportunidades',
      cell: ({ row }) => row.original.opportunities.toLocaleString()
    },
    {
      accessorKey: 'revenue',
      header: 'Ingresos',
      cell: ({ row }) => formatCurrency(row.original.revenue)
    },
    {
      accessorKey: 'roi',
      header: 'ROI',
      cell: ({ row }) => (
        <span className={`font-medium ${
          row.original.roi >= 0 ? 'text-green-600' : 'text-red-600'
        }`}>
          {row.original.roi.toFixed(1)}%
        </span>
      )
    },
    {
      accessorKey: 'cpa',
      header: 'CPA',
      cell: ({ row }) => formatCurrency(row.original.cpa)
    }
  ];

  if (loading) {
    return (
      <div className="border rounded-lg p-8 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (campaigns.length === 0) {
    return (
      <div className="border rounded-lg p-8 text-center">
        <BarChart3 className="h-12 w-12 mx-auto text-gray-400 mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">Sin datos de campañas</h3>
        <p className="text-gray-500 mb-4">
          Conecta tu cuenta de Meta Ads para ver el rendimiento de tus campañas.
        </p>
        <Button>
          <Link href="/crm/marketing?connect=true">Conectar Meta Ads</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="border rounded-lg overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow>
            {columns.map((column) => (
              <TableHead key={column.accessorKey as string}>
                {column.header as string}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {campaigns.map((campaign) => (
            <TableRow
              key={campaign.id}
              className="cursor-pointer hover:bg-gray-50"
              onClick={() => onCampaignClick?.(campaign)}
            >
              {columns.map((column) => (
                <TableCell key={column.accessorKey as string}>
                  {column.cell?.({ row: { original: campaign } } as any) || 
                   (campaign as any)[column.accessorKey as string]}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
};
```

#### **2.3. MetaConnectionWizard.tsx**
```typescript
// Ubicación: frontend_react/src/components/marketing/MetaConnectionWizard.tsx

interface MetaConnectionWizardProps {
  onClose: () => void;
  onSuccess: () => void;
}

const MetaConnectionWizard: React.FC<MetaConnectionWizardProps> = ({
  onClose,
  onSuccess
}) => {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [loading, setLoading] = useState(false);
  const [authUrl, setAuthUrl] = useState<string | null>(null);
  const [selectedAccount, setSelectedAccount] = useState<any>(null);
  const [accounts, setAccounts] = useState<any[]>([]);

  // Paso 1: Obtener URL OAuth
  const getAuthUrl = async () => {
    setLoading(true);
    try {
      const response = await api.get('/crm/auth/meta/url');
      setAuthUrl(response.data.url);
      setStep(2);
    } catch (error) {
      console.error('Error obteniendo URL OAuth:', error);
    } finally {
      setLoading(false);
    }
  };

  // Paso 2: Después de OAuth, seleccionar cuenta
  const loadAccounts = async () => {
    setLoading(true);
    try {
      const response = await api.get('/crm/marketing/meta-accounts');
      setAccounts(response.data.accounts);
      setStep(3);
    } catch (error) {
      console.error('Error cargando cuentas:', error);
    } finally {
      setLoading(false);
    }
  };

  // Paso 3: Conectar cuenta seleccionada
  const connectAccount = async () => {
    if (!selectedAccount) return;
    
    setLoading(true);
    try {
      await api.post('/crm/marketing/connect', {
        account_id: selectedAccount.id,
        account_name: selectedAccount.name
      });
      onSuccess();
      onClose();
    } catch (error) {
      console.error('Error conectando cuenta:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal isOpen={true} onClose={onClose} title="Conectar Meta Ads">
      <div className="space-y-6">
        {step === 1 && (
          <>
            <div className="text-center">
              <Facebook className="h-12 w-12 text-blue-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium">Conectar con Meta Ads</h3>
              <p className="text-gray-500 mt-2">
                Conecta tu cuenta de Meta Ads para ver el rendimiento de tus campañas
                y configurar automatizaciones.
              </p>
            </div>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h4 className="font-medium text-blue-800 mb-2">Permisos requeridos:</h4>
              <ul className="text-sm text-blue-700 space-y-1">
                <li>• ads_management - Gestionar anuncios</li>
                <li>• business_management - Acceder a Business Manager</li>
                <li>• whatsapp_business_management - HSM Automation</li>
              </ul>
            </div>
            <Button onClick={getAuthUrl} disabled={loading} className="w-full">
              {loading ? 'Cargando...' : 'Continuar con Meta'}
            </Button>
          </>
        )}

        {step === 2 && authUrl && (
          <>
            <div className="text-center">
              <ExternalLink className="h-12 w-12 text-green-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium">Autorizar aplicación</h3>
              <p className="text-gray-500 mt-2">
                Serás redirigido a Meta para autorizar la conexión. 
                Una vez autorizado, volverás automáticamente a esta página.
              </p>
            </div>
            <div className="text-center">
              <a
                href={authUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                <Facebook className="mr-2 h-5 w-5" />
                Autorizar en Meta
              </a>
              <p className="text-sm text-gray-500 mt-4">
                ¿Ya autorizaste? <button onClick={loadAccounts} className="text-blue-600 hover:underline">Continuar</button>
              </p>
            </div>
          </>
        )}

        {step === 3 && (
          <>
            <div className="text-center">
              <Building2 className="h-12 w-12 text-purple-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium">Seleccionar cuenta</h3>
              <p className="text-gray-500 mt-2">
                Selecciona la cuenta de anuncios que deseas conectar.
              </p>
            </div>
            <div className="space-y-3 max-h-60 overflow-y-auto">
              {accounts.map((account) => (
                <div
                  key={account.id}
                  className={`border rounded-lg p-3 cursor-pointer hover:border-blue-500 ${
                    selectedAccount?.id === account.id ? 'border-blue-500 bg-blue-50' : ''
                  }`}
                  onClick={() => setSelectedAccount(account)}
                >
                  <div className="font-medium">{account.name}</div>
                  <div className="text-sm text-gray-500">ID: {account.id}</div>
                  <div className="text-sm text-gray-500">Tipo: {account.type}</div>
                </div>
              ))}
            </div>
            <Button
              onClick={connectAccount}
              disabled={!selectedAccount || loading}
              className="w-full"
            >
              {loading ? 'Conectando...' : 'Conectar cuenta'}
            </Button>
          </>
        )}
      </div>
    </Modal>
  );
};
```

### **3. INTEGRACIÓN EN SIDEBAR CRM**

#### **3.1. Actualizar Sidebar.tsx:**
```typescript
// Ubicación: frontend_react/src/components/Sidebar.tsx
import { Megaphone, Layout } from 'lucide-react';

// Agregar al array menuItems:
const menuItems = [
  // ... items existentes (dashboard, leads, clients, etc.)
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
];

// Actualizar traducciones en i18n:
const translations = {
  es: {
    nav: {
      marketing: 'Marketing Hub',
      hsm_automation: 'HSM Automation'
    }
  },
  en: {
    nav: {
      marketing: 'Marketing Hub',
      hsm_automation: 'HSM Automation'
    }
  }
};
```

#### **3.2. Actualizar App.tsx (Routing):**
```typescript
// Ubicación: frontend_react/src/App.tsx
import MarketingHubView from './views/marketing/MarketingHubView';
import MetaTemplatesView from './views/marketing/MetaTemplatesView';

// Agregar rutas dentro del Layout:
<Route path="crm/marketing" element={<MarketingHubView />} />
<Route path="crm/hsm" element={<MetaTemplatesView />} />
```

### **4. API CLIENT PARA MARKETING**

#### **4.1. marketingApi.ts:**
```typescript
// Ubicación: frontend_react/src/api/marketing.ts
import api from './axios';

export const marketingApi = {
  // Dashboard stats
  getStats: (timeRange: string = '7d') => 
    api.get(`/crm/marketing/stats?time_range=${timeRange}`),
  
  // ROI details
  getRoiDetails: () => 
    api.get('/crm/marketing/stats/roi'),
  
  // Token status
  getTokenStatus: () => 
    api.get('/crm/marketing/token-status'),
  
  // Meta accounts
  getMetaAccounts: (portfolioId?: string) => 
    api.get('/crm/marketing/meta-accounts', { params: { portfolio_id: portfolioId } }),
  
  // Connect Meta account
  connectMetaAccount: (data: { account_id: string; account_name: string }) => 
    api.post('/crm/marketing/connect', data),
  
  // HSM Templates
  getHSMTemplates: () => 
    api.get('/crm/marketing/hsm/templates'),
  
  createHSMTemplate: (data: any) => 
    api.post('/crm/marketing/hsm/templates', data),
  
  // Automation rules
  getAutomationRules: () => 
    api.get('/crm/marketing/automation/rules'),
  
  updateAutomationRule: (ruleId: string, data: { enabled: boolean }) => 
    api.patch(`/crm/marketing/automation/rules/${ruleId}`, data),
  
  // Automation logs
  getAutomationLogs: (params?: { limit?: number; offset?: number; status?: string }) => 
    api.get('/crm/marketing/automation/logs', { params }),
  
  // OAuth URLs
  getMetaAuthUrl: () => 
    api.get('/crm/auth/meta/url'),
  
  disconnectMeta: () => 
    api.post('/crm/auth/meta/disconnect')
};
```

### **5. TYPES E INTERFACES**

#### **5.1. marketingTypes.ts:**
```typescript
// Ubicación: frontend_react/src/types/marketing.ts

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
  summary: {
    total_leads: number;
    total_opportunities: number;
    total_revenue: number;
    total_spend: number;
    overall_roi: number;
    overall_cpa: number;
  };
  spend_over_time: Array<{
    date: string;
    spend: number;
    leads: number;
  }>;
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
  start_date: string;
  end_date?: string;
  objective: string;
}

export interface HSMTemplate {
  id: string;
  name: string;
  category: string;
  language: string;
  status: 'APPROVED' | 'PENDING' | 'REJECTED';
  components: Array<{
    type: 'HEADER' | 'BODY' | 'FOOTER' | 'BUTTONS';
    text?: string;
    format?: 'TEXT' | 'IMAGE' | 'VIDEO' | 'DOCUMENT';
    buttons?: Array<{
      type: 'QUICK_REPLY' | 'URL';
      text: string;
      url?: string;
    }>;
  }>;
  created_at: string;
  updated_at: string;
}

export interface AutomationRule {
  id: string;
  name: string;
  description: string;
  trigger_type: 'lead_followup' | 'opportunity_reminder' | 'post_sale_feedback' | 'abandoned_cart';
  condition: string;
  template_id: string;
  template_name: string;
  enabled: boolean;
  last_triggered?: string;
  trigger_count: number;
}

export interface AutomationLog {
  id: string;
  rule_id: string;
  rule_name: string;
  lead_id: string;
  lead_name: string;
  phone: string;
  template_id: string;
  template_name: string;
  status: 'SENT' | 'DELIVERED' | 'READ' | 'FAILED';
  error_message?: string;
  sent_at: string;
  delivered_at?: string;
  read_at?: string;
}

export interface MetaAccount {
  id: string;
  name: string;
  type: 'BUSINESS' | 'AD_ACCOUNT';
  currency: string;
  timezone: string;
  status: 'ACTIVE' | 'DISABLED' | 'PENDING_REVIEW';
  spend_cap?: number;
  amount_spent?: number;
}
```

### **6. MIGRACIÓN PASO A PASO**

#### **Paso 1: Crear estructura de directorios**
```bash
# Desde directorio frontend_react
mkdir -p src/views/marketing
mkdir -p src/components/marketing
mkdir -p src/api
mkdir -p src/types
```

#### **Paso 2: Copiar componentes de ClinicForge**
```bash
# Copiar vistas
cp ../clinicforge/frontend_react/src/views/MarketingHubView.tsx src/views/marketing/
cp ../clinicforge/frontend_react/src/views/MetaTemplatesView.tsx src/views/marketing/

# Copiar componentes
cp ../clinicforge/frontend_react/src/components/MarketingPerformanceCard.tsx src/components/marketing/
cp ../clinicforge/frontend_react/src/components/AdContextCard.tsx src/components/marketing/
cp ../clinicforge/frontend_react/src/components/integrations/MetaConnectionWizard.tsx src/components/marketing/
cp ../clinicforge/frontend_react/src/components/MetaTokenBanner.tsx src/components/marketing/
```

#### **Paso 3: Adaptar terminología**
```typescript
// En todos los componentes, reemplazar:
// patients → leads
// appointments → opportunities
// dental → sales
// clinic → account
// acquisition_source → lead_source
```

#### **Paso 4: Actualizar API calls**
```typescript
// Cambiar endpoints:
// /admin/marketing/ → /crm/marketing/
// /auth/meta/ → /crm/auth/meta/
```

#### **Paso 5: Integrar en Sidebar y Routing**
```typescript
// 1. Actualizar Sidebar.tsx con nuevos items
// 2. Agregar rutas en App.tsx
// 3. Actualizar traducciones i18n
```

#### **Paso 6: Crear API client y types**
```typescript
// 1. Crear src/api/marketing.ts
// 2. Crear src/types/marketing.ts
// 3. Actualizar imports en componentes
```

### **7. TESTING FRONTEND**

#### **7.1. Unit Testing Components:**
```typescript
// tests/components/MarketingPerformanceCard.test.tsx
import { render, screen } from '@testing-library/react';
import { MarketingPerformanceCard } from '../../src/components/marketing/MarketingPerformanceCard';
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

  it('shows positive change with green color', () => {
    render(
      <MarketingPerformanceCard
        title="ROI"
        value="25%"
        change={15}
        icon={<TrendingUp />}
      />
    );
    
    const changeElement = screen.getByText('15%');
    expect(changeElement).toHaveClass('text-green-600');
  });
});
```

#### **7.2. Integration Testing Views:**
```typescript
// tests/views/MarketingHubView.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import { MarketingHubView } from '../../src/views/marketing/MarketingHubView';
import { marketingApi } from '../../src/api/marketing';

jest.mock('../../src/api/marketing');

describe('MarketingHubView', () => {
  beforeEach(() => {
    (marketingApi.getStats as jest.Mock).mockResolvedValue({
      data: {
        summary: {
          leads: 150,
          opportunities: 45,
          sales_revenue: 25000,
          marketing_spend: 5000,
          overall_roi: 400,
          overall_cpa: 33.33
        },
        campaigns: []
      }
    });
  });

  it('loads and displays marketing data', async () => {
    render(<MarketingHubView />);
    
    // Verificar loading state
    expect(screen.getByRole('status')).toBeInTheDocument();
    
    // Esperar a que carguen los datos
    await waitFor(() => {
      expect(screen.getByText('Marketing Hub')).toBeInTheDocument();
      expect(screen.getByText('150')).toBeInTheDocument(); // Leads
      expect(screen.getByText('$25,000')).toBeInTheDocument(); // Revenue
    });
  });
});
```

#### **7.3. E2E Testing con Cypress:**
```typescript
// cypress/e2e/marketing.cy.ts
describe('Marketing Hub E2E', () => {
  beforeEach(() => {
    cy.login('ceo@example.com', 'password');
    cy.visit('/crm/marketing');
  });

  it('displays marketing dashboard', () => {
    cy.contains('Marketing Hub').should('be.visible');
    cy.contains('Leads').should('be.visible');
    cy.contains('Oportunidades').should('be.visible');
    cy.contains('ROI').should('be.visible');
  });

  it('connects Meta account successfully', () => {
    cy.contains('Conectar Meta Ads').click();
    cy.contains('Continuar con Meta').click();
    // Simular flujo OAuth
    // ...
    cy.contains('Cuenta conectada exitosamente').should('be.visible');
  });

  it('filters campaigns by time range', () => {
    cy.get('[data-testid="time-range-selector"]').select('30d');
    cy.contains('Cargando...').should('be.visible');
    cy.contains('Cargando...').should('not.exist');
  });
});
```

### **8. OPTIMIZACIONES DE PERFORMANCE**

#### **8.1. Lazy Loading de Vistas:**
```typescript
// En App.tsx
const MarketingHubView = lazy(() => import('./views/marketing/MarketingHubView'));
const MetaTemplatesView = lazy(() => import('./views/marketing/MetaTemplatesView'));

// En las rutas:
<Route 
  path="crm/marketing" 
  element={
    <Suspense fallback={<LoadingSpinner />}>
      <MarketingHubView />
    </Suspense>
  } 
/>
```

#### **8.2. Data Caching con React Query:**
```typescript
// Usar React Query para caching de datos de marketing
import { useQuery } from '@tanstack/react-query';

const MarketingHubView = () => {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['marketing-stats', timeRange],
    queryFn: () => marketingApi.getStats(timeRange).then(res => res.data),
    staleTime: 5 * 60 * 1000, // 5 minutos
    cacheTime: 10 * 60 * 1000, // 10 minutos
  });

  // ... resto del componente
};
```

#### **8.3. Virtualización de Tablas:**
```typescript
// Para tablas con muchos datos (ej: 1000+ campañas)
import { FixedSizeList as List } from 'react-window';

const VirtualizedCampaignsTable = ({ campaigns }) => {
  const Row = ({ index, style }) => (
    <div style={style}>
      <CampaignRow campaign={campaigns[index]} />
    </div>
  );

  return (
