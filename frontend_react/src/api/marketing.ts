/**
 * Marketing API Client for CRM Ventas
 * Adapted from ClinicForge for CRM Sales context
 */

import api from './axios';

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
  meta_connected: boolean;
  connect_url?: string;
}

export interface CampaignStat {
  id: string;
  name: string;
  status: 'ACTIVE' | 'PAUSED' | 'DELETED' | 'ARCHIVED';
  spend: number;
  leads: number;
  opportunities: number;
  revenue: number;
  roi: number;
  cpa: number;
}

export interface RoiBreakdown {
  campaigns: CampaignStat[];
  time_period: string;
  total_spend: number;
  total_revenue: number;
  average_roi: number;
}

export interface MetaTokenStatus {
  connected: boolean;
  expires_at?: string;
  scopes?: string[];
  business_managers?: number;
  ad_accounts?: number;
  connect_url?: string;
}

export interface BusinessManager {
  id: string;
  name: string;
  ad_accounts_count: number;
}

export interface AdAccount {
  id: string;
  name: string;
  currency: string;
  timezone: string;
  status: string;
}

export interface HSMTemplate {
  id: string;
  name: string;
  category: string;
  language: string;
  status: 'APPROVED' | 'PENDING' | 'REJECTED' | 'PAUSED';
  components: any[];
}

export interface AutomationRule {
  id: string;
  name: string;
  trigger_type: string;
  is_active: boolean;
  trigger_count: number;
}

export interface CampaignDetails {
  id: string;
  name: string;
  objective: string;
  daily_budget: number;
  targeting: any;
  performance: {
    spend: number;
    leads: number;
    cpa: number;
  };
}

export interface CampaignInsights {
  id: string;
  name: string;
  insights: any[];
  time_range: string;
}

export const marketingApi = {
  // ==================== DASHBOARD ENDPOINTS ====================
  
  getStats: (timeRange: string = 'last_30d'): Promise<{ data: MarketingStats }> => 
    api.get(`/crm/marketing/stats?time_range=${timeRange}`),
  
  getRoiDetails: (timeRange: string = 'last_30d'): Promise<{ data: RoiBreakdown }> => 
    api.get(`/crm/marketing/stats/roi?time_range=${timeRange}`),
  
  getTokenStatus: (): Promise<{ data: MetaTokenStatus }> => 
    api.get('/crm/marketing/token-status'),
  
  // ==================== META ACCOUNT MANAGEMENT ====================
  
  getMetaPortfolios: (): Promise<{ data: BusinessManager[] }> => 
    api.get('/crm/marketing/meta-portfolios'),
  
  getMetaAccounts: (portfolioId?: string): Promise<{ data: AdAccount[] }> => 
    api.get('/crm/marketing/meta-accounts', { params: { portfolio_id: portfolioId } }),
  
  connectMetaAccount: (data: { account_id: string; account_name: string }): Promise<{ data: any }> => 
    api.post('/crm/marketing/connect', data),
  
  // ==================== HSM AUTOMATION ====================
  
  getHSMTemplates: (): Promise<{ data: HSMTemplate[] }> => 
    api.get('/crm/marketing/hsm/templates'),
  
  getAutomationRules: (): Promise<{ data: AutomationRule[] }> => 
    api.get('/crm/marketing/automation/rules'),
  
  updateAutomationRules: (rules: any[]): Promise<{ data: any }> => 
    api.post('/crm/marketing/automation/rules', { rules }),
  
  getAutomationLogs: (limit: number = 100, offset: number = 0): Promise<{ data: any[] }> => 
    api.get(`/crm/marketing/automation-logs?limit=${limit}&offset=${offset}`),
  
  // ==================== CAMPAIGN MANAGEMENT ====================
  
  getCampaigns: (status?: string, limit: number = 50, offset: number = 0): Promise<{ data: CampaignStat[] }> => 
    api.get('/crm/marketing/campaigns', { params: { status, limit, offset } }),
  
  getCampaignDetails: (campaignId: string): Promise<{ data: CampaignDetails }> => 
    api.get(`/crm/marketing/campaigns/${campaignId}`),
  
  getCampaignInsights: (campaignId: string, timeRange: string = 'last_30d'): Promise<{ data: CampaignInsights }> => 
    api.get(`/crm/marketing/campaigns/${campaignId}/insights?time_range=${timeRange}`),
  
  // ==================== META OAUTH ====================
  
  getMetaAuthUrl: (): Promise<{ data: { auth_url: string; state: string; expires_in: number } }> => 
    api.get('/crm/auth/meta/url'),
  
  disconnectMeta: (): Promise<{ data: any }> => 
    api.post('/crm/auth/meta/disconnect'),
  
  testMetaConnection: (): Promise<{ data: any }> => 
    api.get('/crm/auth/meta/test-connection'),
  
  debugMetaToken: (): Promise<{ data: any }> => 
    api.get('/crm/auth/meta/debug/token'),
};

// Helper function to format currency
export const formatCurrency = (amount: number, currency: string = 'USD'): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
};

// Helper function to format percentage
export const formatPercentage = (value: number): string => {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(1)}%`;
};

// Helper function to calculate ROI color
export const getRoiColor = (roi: number): string => {
  if (roi >= 300) return 'text-green-600';
  if (roi >= 100) return 'text-green-500';
  if (roi >= 0) return 'text-yellow-500';
  return 'text-red-500';
};

// Helper function to get time range options
export const timeRangeOptions = [
  { value: 'last_30d', label: 'Last 30 days' },
  { value: 'last_90d', label: 'Last 90 days' },
  { value: 'this_year', label: 'This year' },
  { value: 'yearly', label: 'Yearly' },
  { value: 'lifetime', label: 'Lifetime' },
];

// Types for TypeScript
export type { 
  MarketingStats, 
  CampaignStat, 
  RoiBreakdown, 
  MetaTokenStatus,
  BusinessManager,
  AdAccount,
  HSMTemplate,
  AutomationRule,
  CampaignDetails,
  CampaignInsights
};