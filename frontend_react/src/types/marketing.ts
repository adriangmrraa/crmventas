/**
 * TypeScript interfaces for Marketing module
 * CRM Ventas - Adapted from ClinicForge
 */

// ==================== CORE TYPES ====================

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

// ==================== META INTEGRATION TYPES ====================

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

export interface MetaConnectionResult {
  connected: boolean;
  account_id: string;
  account_name: string;
  message: string;
}

// ==================== HSM AUTOMATION TYPES ====================

export interface HSMTemplate {
  id: string;
  name: string;
  category: 'MARKETING' | 'UTILITY' | 'AUTHENTICATION';
  language: string;
  status: 'APPROVED' | 'PENDING' | 'REJECTED' | 'PAUSED';
  components: {
    header?: any;
    body: any;
    footer?: any;
    buttons?: any[];
  };
  example?: any;
}

export interface AutomationRule {
  id: string;
  name: string;
  trigger_type: 'lead_created' | 'lead_status_changed' | 'opportunity_created';
  trigger_conditions: Record<string, any>;
  action_type: 'send_hsm' | 'assign_seller' | 'update_field';
  action_config: Record<string, any>;
  is_active: boolean;
  last_triggered_at?: string;
  trigger_count: number;
  success_count: number;
  error_count: number;
}

export interface AutomationLog {
  id: string;
  rule_id: string;
  trigger_type: string;
  trigger_data: Record<string, any>;
  action_type: string;
  action_config: Record<string, any>;
  action_result?: Record<string, any>;
  status: 'success' | 'error' | 'skipped';
  error_message?: string;
  execution_time_ms?: number;
  created_at: string;
}

// ==================== CAMPAIGN TYPES ====================

export interface CampaignDetails {
  id: string;
  name: string;
  objective: 'LEADS' | 'MESSAGES' | 'CONVERSIONS' | 'REACH';
  status: 'ACTIVE' | 'PAUSED' | 'DELETED' | 'ARCHIVED';
  daily_budget?: number;
  lifetime_budget?: number;
  start_time?: string;
  end_time?: string;
  targeting: Record<string, any>;
  performance: {
    spend: number;
    impressions: number;
    clicks: number;
    leads: number;
    opportunities: number;
    revenue: number;
    roi_percentage: number;
    cpa: number;
    cpc: number;
    cpm: number;
    ctr: number;
  };
}

export interface CampaignInsights {
  id: string;
  name: string;
  insights: Array<{
    date: string;
    spend: number;
    impressions: number;
    clicks: number;
    leads: number;
    opportunities: number;
    revenue: number;
    cpa: number;
    cpc: number;
    cpm: number;
    ctr: number;
  }>;
  time_range: string;
  attribution_window: string;
}

// ==================== API RESPONSE TYPES ====================

export interface ApiResponse<T = any> {
  success: boolean;
  data: T;
  timestamp: string;
  error?: string;
  error_reason?: string;
  error_description?: string;
}

export interface PaginatedResponse<T = any> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
}

// ==================== UI COMPONENT PROPS ====================

export interface MarketingPerformanceCardProps {
  title: string;
  value: number | string;
  change?: number;
  icon: React.ReactNode;
  format?: 'number' | 'currency' | 'percentage';
  currency?: string;
  loading?: boolean;
}

export interface MetaConnectionWizardProps {
  isOpen: boolean;
  onClose: () => void;
  onConnected?: (result: MetaConnectionResult) => void;
}

export interface MetaTokenBannerProps {
  status: MetaTokenStatus;
  onReconnect?: () => void;
  onDisconnect?: () => void;
}

// ==================== FORM TYPES ====================

export interface ConnectMetaFormData {
  account_id: string;
  account_name: string;
}

// ==================== OAUTH TYPES ====================

export interface AuthUrl {
  auth_url: string;
  state: string;
  expires_in: number;
}

export interface AutomationRuleFormData {
  name: string;
  trigger_type: string;
  trigger_conditions: Record<string, any>;
  action_type: string;
  action_config: Record<string, any>;
  is_active: boolean;
}

// ==================== ENUM TYPES ====================

export enum TimeRange {
  LAST_30D = 'last_30d',
  LAST_90D = 'last_90d',
  THIS_YEAR = 'this_year',
  YEARLY = 'yearly',
  LIFETIME = 'lifetime',
}

export enum CampaignStatus {
  ACTIVE = 'ACTIVE',
  PAUSED = 'PAUSED',
  DELETED = 'DELETED',
  ARCHIVED = 'ARCHIVED',
}

export enum TemplateStatus {
  APPROVED = 'APPROVED',
  PENDING = 'PENDING',
  REJECTED = 'REJECTED',
  PAUSED = 'PAUSED',
}

export enum AutomationStatus {
  SUCCESS = 'success',
  ERROR = 'error',
  SKIPPED = 'skipped',
}

// ==================== HELPER TYPES ====================

export type Nullable<T> = T | null;
export type Optional<T> = T | undefined;
export type Dictionary<T = any> = Record<string, T>;