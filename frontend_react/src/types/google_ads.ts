/**
 * TypeScript types for Google Ads integration
 */

export interface GoogleAdsCampaign {
  id: string;
  name: string;
  status: GoogleAdsCampaignStatus;
  channel_type: GoogleAdsChannelType;
  start_date: string;
  end_date?: string;
  budget: number;
  budget_micros: number;
  impressions: number;
  clicks: number;
  cost: number;
  cost_micros: number;
  conversions: number;
  conversions_value: number;
  average_cpc: number;
  ctr: number;
  all_conversions: number;
  all_conversions_value: number;
  // Calculated fields
  roi?: number;
  leads?: number;
  opportunities?: number;
}

export type GoogleAdsCampaignStatus = 'ENABLED' | 'PAUSED' | 'REMOVED';

export type GoogleAdsChannelType = 
  | 'SEARCH' 
  | 'DISPLAY' 
  | 'SHOPPING' 
  | 'VIDEO' 
  | 'APP' 
  | 'LOCAL' 
  | 'SMART' 
  | 'PERFORMANCE_MAX' 
  | 'DISCOVERY' 
  | 'TRAVEL' 
  | 'UNKNOWN' 
  | 'UNSPECIFIED';

export interface GoogleAdsMetrics {
  impressions: number;
  clicks: number;
  cost: number;
  cost_micros: number;
  conversions: number;
  conversions_value: number;
  average_cpc: number;
  ctr: number;
  all_conversions: number;
  all_conversions_value: number;
  date_range: GoogleAdsDateRange;
  customer_id?: string;
  // Calculated fields
  roi?: number;
  leads?: number;
  opportunities?: number;
}

export type GoogleAdsDateRange = 
  | 'TODAY'
  | 'YESTERDAY'
  | 'LAST_7_DAYS'
  | 'LAST_14_DAYS'
  | 'LAST_30_DAYS'
  | 'LAST_BUSINESS_WEEK'
  | 'THIS_WEEK_SUN_TODAY'
  | 'THIS_WEEK_MON_TODAY'
  | 'LAST_WEEK_SUN_SAT'
  | 'LAST_WEEK_MON_SUN'
  | 'THIS_MONTH'
  | 'LAST_MONTH'
  | 'ALL_TIME'
  | 'CUSTOM_DATE';

export interface GoogleAdsConnectionStatus {
  connected: boolean;
  customer_ids: string[];
  user_email?: string;
  expires_at?: string;
  message?: string;
  test_customer?: string;
  test_metrics?: GoogleAdsMetrics;
}

export interface GoogleAdsTokenStatus {
  connected: boolean;
  token_exists: boolean;
  is_expired: boolean;
  expires_at?: string;
  has_refresh_token: boolean;
  user_email?: string;
  message?: string;
}

export interface GoogleAdsCustomerAccount {
  id: string;
  name: string;
  type: 'GOOGLE_ADS';
  currency?: string;
  time_zone?: string;
  test_account?: boolean;
}

export interface GoogleAdsSyncResult {
  success: boolean;
  message: string;
  synced_customers: number;
  total_campaigns: number;
  results?: Array<{
    customer_id: string;
    campaigns_count: number;
    metrics: GoogleAdsMetrics;
    error?: string;
  }>;
}

export interface GoogleAdsOAuthResponse {
  auth_url: string;
  state: string;
  expires_in: number;
  scopes: string[];
}

export interface GoogleAdsError {
  code: number;
  message: string;
  details?: any;
  domain?: string;
}

// Response wrapper for API calls
export interface GoogleAdsApiResponse<T> {
  success: boolean;
  data?: T;
  error?: GoogleAdsError;
  timestamp: string;
}

// Props for Google Ads components
export interface GoogleAdsPerformanceCardProps {
  metrics: GoogleAdsMetrics;
  loading?: boolean;
  timeRange?: string;
  customerId?: string;
}

export interface GoogleAdsCampaignTableProps {
  campaigns: GoogleAdsCampaign[];
  loading?: boolean;
  onCampaignClick?: (campaign: GoogleAdsCampaign) => void;
}

export interface GoogleAdsConnectionCardProps {
  connected: boolean;
  customerIds: string[];
  userEmail?: string;
  onConnect: () => void;
  onDisconnect: () => void;
  onRefresh?: () => void;
}

// Hook return types
export interface UseGoogleAdsReturn {
  campaigns: GoogleAdsCampaign[];
  metrics: GoogleAdsMetrics;
  connected: boolean;
  customerIds: string[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  connect: () => Promise<void>;
  disconnect: () => Promise<void>;
}

export interface UseGoogleAdsCampaignsReturn {
  campaigns: GoogleAdsCampaign[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export interface UseGoogleAdsMetricsReturn {
  metrics: GoogleAdsMetrics;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

// Utility types
export type GoogleAdsCurrency = 'USD' | 'EUR' | 'GBP' | 'ARS' | 'BRL' | 'MXN' | string;

export interface GoogleAdsBudget {
  amount_micros: number;
  delivery_method: 'STANDARD' | 'ACCELERATED';
  period: 'DAILY' | 'CUSTOM';
}

export interface GoogleAdsTargeting {
  locations: string[];
  languages: string[];
  devices: string[];
  demographics: {
    age_ranges: string[];
    genders: string[];
  };
  keywords?: string[];
  placements?: string[];
}