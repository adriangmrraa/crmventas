/**
 * Google Ads API Client for CRM Ventas
 */

import api from './axios';

export interface GoogleAdsCampaign {
  id: string;
  name: string;
  status: 'ENABLED' | 'PAUSED' | 'REMOVED';
  channel_type: string;
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
}

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
  date_range: string;
  customer_id?: string;
}

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

/**
 * Get Google Ads OAuth URL for connecting account
 */
export async function getGoogleAdsAuthUrl(): Promise<{ auth_url: string; state: string; expires_in: number }> {
  const response = await api.get('/crm/auth/google/ads/url');
  return response.data?.data || response.data;
}

/**
 * Test Google Ads connection
 */
export async function testGoogleAdsConnection(): Promise<GoogleAdsConnectionStatus> {
  const response = await api.get('/crm/auth/google/ads/test-connection');
  return response.data?.data || response.data;
}

/**
 * Get Google Ads token status
 */
export async function getGoogleAdsTokenStatus(): Promise<GoogleAdsTokenStatus> {
  const response = await api.get('/crm/auth/google/ads/debug/token');
  return response.data?.data || response.data;
}

/**
 * Refresh Google Ads token manually
 */
export async function refreshGoogleAdsToken(): Promise<{ refreshed: boolean; message: string }> {
  const response = await api.post('/crm/auth/google/ads/refresh');
  return response.data?.data || response.data;
}

/**
 * Disconnect Google Ads account
 */
export async function disconnectGoogleAdsAccount(): Promise<{ disconnected: boolean; message: string }> {
  const response = await api.post('/crm/auth/google/ads/disconnect');
  return response.data?.data || response.data;
}

/**
 * Get Google Ads campaigns for a customer
 */
export async function getGoogleAdsCampaigns(customerId: string): Promise<GoogleAdsCampaign[]> {
  const response = await api.get(`/crm/marketing/google/campaigns?customer_id=${customerId}`);
  return response.data?.data || response.data || [];
}

/**
 * Get Google Ads metrics for a customer
 */
export async function getGoogleAdsMetrics(customerId: string, dateRange: string = 'LAST_30_DAYS'): Promise<GoogleAdsMetrics> {
  const response = await api.get(`/crm/marketing/google/metrics?customer_id=${customerId}&date_range=${dateRange}`);
  return response.data?.data || response.data || getEmptyGoogleAdsMetrics();
}

/**
 * Get accessible Google Ads customers
 */
export async function getAccessibleGoogleAdsCustomers(): Promise<string[]> {
  const response = await api.get('/crm/marketing/google/customers');
  return response.data?.data || response.data || [];
}

/**
 * Sync Google Ads data (background job)
 */
export async function syncGoogleAdsData(): Promise<{ success: boolean; message: string; synced_customers: number; total_campaigns: number }> {
  const response = await api.post('/crm/marketing/google/sync');
  return response.data?.data || response.data;
}

/**
 * Get Google Ads stats (combined campaigns + metrics)
 */
export async function getGoogleAdsStats(customerId?: string, dateRange: string = 'LAST_30_DAYS'): Promise<{
  campaigns: GoogleAdsCampaign[];
  metrics: GoogleAdsMetrics;
  connected: boolean;
  customer_ids: string[];
}> {
  try {
    // Get connection status first
    const connection = await testGoogleAdsConnection();
    
    if (!connection.connected || connection.customer_ids.length === 0) {
      return {
        campaigns: [],
        metrics: getEmptyGoogleAdsMetrics(),
        connected: false,
        customer_ids: []
      };
    }

    // Use first customer if not specified
    const targetCustomerId = customerId || connection.customer_ids[0];
    
    // Get campaigns and metrics in parallel
    const [campaigns, metrics] = await Promise.all([
      getGoogleAdsCampaigns(targetCustomerId),
      getGoogleAdsMetrics(targetCustomerId, dateRange)
    ]);

    return {
      campaigns,
      metrics,
      connected: true,
      customer_ids: connection.customer_ids
    };
  } catch (error) {
    console.error('Error getting Google Ads stats:', error);
    return {
      campaigns: [],
      metrics: getEmptyGoogleAdsMetrics(),
      connected: false,
      customer_ids: []
    };
  }
}

/**
 * Get empty Google Ads metrics for error handling
 */
export function getEmptyGoogleAdsMetrics(): GoogleAdsMetrics {
  return {
    impressions: 0,
    clicks: 0,
    cost: 0,
    cost_micros: 0,
    conversions: 0,
    conversions_value: 0,
    average_cpc: 0,
    ctr: 0,
    all_conversions: 0,
    all_conversions_value: 0,
    date_range: 'LAST_30_DAYS'
  };
}

/**
 * Format currency for Google Ads (micros to dollars)
 */
export function formatGoogleAdsCurrency(micros: number): string {
  return `$${(micros / 1000000).toFixed(2)}`;
}

/**
 * Calculate ROI for Google Ads campaign
 */
export function calculateGoogleAdsROI(cost: number, conversionsValue: number): number {
  if (cost === 0) return 0;
  return (conversionsValue - cost) / cost;
}

/**
 * Get status color for Google Ads campaign
 */
export function getGoogleAdsStatusColor(status: string): string {
  switch (status) {
    case 'ENABLED':
      return 'text-green-600 bg-green-50 border-green-100';
    case 'PAUSED':
      return 'text-amber-600 bg-amber-50 border-amber-100';
    case 'REMOVED':
      return 'text-gray-600 bg-gray-50 border-gray-100';
    default:
      return 'text-gray-600 bg-gray-50 border-gray-100';
  }
}

/**
 * Get status text for Google Ads campaign
 */
export function getGoogleAdsStatusText(status: string): string {
  switch (status) {
    case 'ENABLED':
      return 'Active';
    case 'PAUSED':
      return 'Paused';
    case 'REMOVED':
      return 'Removed';
    default:
      return status;
  }
}