-- Migration Patch 009: Meta Ads Marketing Tables
-- Creates tables for Meta Ads integration and marketing analytics
-- All tables include tenant_id for multi-tenancy sovereignty

BEGIN;

-- ============================================
-- 1. Add marketing fields to existing leads table
-- ============================================
ALTER TABLE leads ADD COLUMN IF NOT EXISTS lead_source VARCHAR(50) DEFAULT 'ORGANIC';
ALTER TABLE leads ADD COLUMN IF NOT EXISTS meta_campaign_id VARCHAR(255);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS meta_ad_id VARCHAR(255);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS meta_ad_headline TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS meta_ad_body TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS external_ids JSONB DEFAULT '{}';

-- Indexes for marketing queries
CREATE INDEX IF NOT EXISTS idx_leads_lead_source ON leads(tenant_id, lead_source);
CREATE INDEX IF NOT EXISTS idx_leads_meta_campaign ON leads(tenant_id, meta_campaign_id);
CREATE INDEX IF NOT EXISTS idx_leads_meta_ad ON leads(tenant_id, meta_ad_id);

-- ============================================
-- 2. META_ADS_CAMPAIGNS (Sync from Meta API)
-- ============================================
CREATE TABLE IF NOT EXISTS meta_ads_campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    
    -- Meta API IDs
    meta_campaign_id VARCHAR(255) NOT NULL,
    meta_account_id VARCHAR(255) NOT NULL,
    meta_business_manager_id VARCHAR(255),
    
    -- Campaign Info
    name TEXT NOT NULL,
    objective TEXT, -- 'LEADS', 'MESSAGES', 'CONVERSIONS', 'REACH'
    status TEXT, -- 'ACTIVE', 'PAUSED', 'DELETED', 'ARCHIVED'
    
    -- Budget & Schedule
    daily_budget DECIMAL(12,2),
    lifetime_budget DECIMAL(12,2),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    
    -- Targeting
    targeting JSONB DEFAULT '{}',
    
    -- Performance Metrics (cached)
    spend DECIMAL(12,2) DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    leads INTEGER DEFAULT 0,
    opportunities INTEGER DEFAULT 0,
    revenue DECIMAL(12,2) DEFAULT 0,
    roi_percentage DECIMAL(5,2) DEFAULT 0,
    
    -- Sync Info
    last_synced_at TIMESTAMP,
    sync_status TEXT DEFAULT 'pending', -- pending, success, error
    sync_error TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_meta_campaign_per_tenant UNIQUE (tenant_id, meta_campaign_id)
);

CREATE INDEX IF NOT EXISTS idx_meta_campaigns_tenant ON meta_ads_campaigns(tenant_id);
CREATE INDEX IF NOT EXISTS idx_meta_campaigns_status ON meta_ads_campaigns(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_meta_campaigns_account ON meta_ads_campaigns(tenant_id, meta_account_id);

-- ============================================
-- 3. META_ADS_INSIGHTS (Daily performance data)
-- ============================================
CREATE TABLE IF NOT EXISTS meta_ads_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    
    -- Foreign Keys
    meta_campaign_id VARCHAR(255) NOT NULL,
    campaign_id UUID REFERENCES meta_ads_campaigns(id),
    
    -- Date Range
    date DATE NOT NULL,
    date_start TIMESTAMP,
    date_stop TIMESTAMP,
    
    -- Performance Metrics
    spend DECIMAL(12,2) DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    cpc DECIMAL(10,2),
    cpm DECIMAL(10,2),
    ctr DECIMAL(5,2),
    
    -- Conversion Metrics (if available)
    leads INTEGER DEFAULT 0,
    cost_per_lead DECIMAL(10,2),
    opportunities INTEGER DEFAULT 0,
    cost_per_opportunity DECIMAL(10,2),
    
    -- Attribution
    attribution_window TEXT, -- '1d_click', '7d_click', '1d_view', '28d_click'
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_insight_per_day UNIQUE (tenant_id, meta_campaign_id, date, attribution_window)
);

CREATE INDEX IF NOT EXISTS idx_meta_insights_tenant ON meta_ads_insights(tenant_id);
CREATE INDEX IF NOT EXISTS idx_meta_insights_campaign ON meta_ads_insights(tenant_id, meta_campaign_id);
CREATE INDEX IF NOT EXISTS idx_meta_insights_date ON meta_ads_insights(tenant_id, date);

-- ============================================
-- 4. META_TEMPLATES (HSM Templates from Meta)
-- ============================================
CREATE TABLE IF NOT EXISTS meta_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    
    -- Meta API IDs
    meta_template_id VARCHAR(255) NOT NULL,
    waba_id VARCHAR(255) NOT NULL,
    
    -- Template Info
    name TEXT NOT NULL,
    category TEXT NOT NULL, -- 'MARKETING', 'UTILITY', 'AUTHENTICATION'
    language TEXT DEFAULT 'es',
    status TEXT, -- 'APPROVED', 'PENDING', 'REJECTED', 'PAUSED'
    
    -- Components
    components JSONB NOT NULL, -- header, body, footer, buttons
    example JSONB, -- example message structure
    
    -- Usage Stats
    sent_count INTEGER DEFAULT 0,
    delivered_count INTEGER DEFAULT 0,
    read_count INTEGER DEFAULT 0,
    replied_count INTEGER DEFAULT 0,
    
    -- Sync Info
    last_synced_at TIMESTAMP,
    sync_status TEXT DEFAULT 'pending',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_meta_template_per_tenant UNIQUE (tenant_id, meta_template_id)
);

CREATE INDEX IF NOT EXISTS idx_meta_templates_tenant ON meta_templates(tenant_id);
CREATE INDEX IF NOT EXISTS idx_meta_templates_status ON meta_templates(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_meta_templates_category ON meta_templates(tenant_id, category);

-- ============================================
-- 5. AUTOMATION_RULES (HSM Automation Rules)
-- ============================================
CREATE TABLE IF NOT EXISTS automation_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    
    -- Rule Configuration
    name TEXT NOT NULL,
    trigger_type TEXT NOT NULL, -- 'lead_created', 'lead_status_changed', 'opportunity_created'
    trigger_conditions JSONB NOT NULL, -- {status: 'new', source: 'meta_ads'}
    
    -- Action Configuration
    action_type TEXT NOT NULL, -- 'send_hsm', 'assign_seller', 'update_field'
    action_config JSONB NOT NULL, -- {template_id: '...', delay_hours: 24}
    
    -- Execution
    is_active BOOLEAN DEFAULT TRUE,
    last_triggered_at TIMESTAMP,
    trigger_count INTEGER DEFAULT 0,
    
    -- Stats
    success_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_automation_rules_tenant ON automation_rules(tenant_id);
CREATE INDEX IF NOT EXISTS idx_automation_rules_active ON automation_rules(tenant_id, is_active);
CREATE INDEX IF NOT EXISTS idx_automation_rules_trigger ON automation_rules(tenant_id, trigger_type);

-- ============================================
-- 6. AUTOMATION_LOGS (Rule Execution Logs)
-- ============================================
CREATE TABLE IF NOT EXISTS automation_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    
    -- Execution Context
    rule_id UUID REFERENCES automation_rules(id),
    trigger_type TEXT NOT NULL,
    trigger_data JSONB NOT NULL, -- Data that triggered the rule
    
    -- Action Details
    action_type TEXT NOT NULL,
    action_config JSONB NOT NULL,
    action_result JSONB, -- Result of the action
    
    -- Status
    status TEXT NOT NULL, -- 'success', 'error', 'skipped'
    error_message TEXT,
    
    -- Performance
    execution_time_ms INTEGER,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_automation_logs_tenant ON automation_logs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_automation_logs_rule ON automation_logs(tenant_id, rule_id);
CREATE INDEX IF NOT EXISTS idx_automation_logs_status ON automation_logs(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_automation_logs_created ON automation_logs(tenant_id, created_at);

-- ============================================
-- 7. OPPORTUNITIES TABLE (Sales Pipeline)
-- ============================================
CREATE TABLE IF NOT EXISTS opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    
    -- Relationship
    lead_id UUID REFERENCES leads(id) NOT NULL,
    seller_id INTEGER REFERENCES users(id),
    
    -- Opportunity Details
    name TEXT NOT NULL,
    description TEXT,
    value DECIMAL(12,2) NOT NULL,
    currency TEXT DEFAULT 'USD',
    
    -- Pipeline Status
    stage TEXT NOT NULL, -- 'prospecting', 'qualification', 'proposal', 'negotiation', 'closed_won', 'closed_lost'
    probability DECIMAL(5,2) DEFAULT 0, -- 0-100%
    expected_close_date DATE,
    
    -- Win/Loss Details
    closed_at TIMESTAMP,
    close_reason TEXT,
    lost_reason TEXT,
    
    -- Metadata
    tags JSONB DEFAULT '[]',
    custom_fields JSONB DEFAULT '{}',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_opportunities_tenant ON opportunities(tenant_id);
CREATE INDEX IF NOT EXISTS idx_opportunities_lead ON opportunities(tenant_id, lead_id);
CREATE INDEX IF NOT EXISTS idx_opportunities_seller ON opportunities(tenant_id, seller_id);
CREATE INDEX IF NOT EXISTS idx_opportunities_stage ON opportunities(tenant_id, stage);
CREATE INDEX IF NOT EXISTS idx_opportunities_expected_close ON opportunities(tenant_id, expected_close_date);

-- ============================================
-- 8. SALES_TRANSACTIONS (Revenue Tracking)
-- ============================================
CREATE TABLE IF NOT EXISTS sales_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    
    -- Relationship
    opportunity_id UUID REFERENCES opportunities(id),
    lead_id UUID REFERENCES leads(id),
    
    -- Transaction Details
    amount DECIMAL(12,2) NOT NULL,
    currency TEXT DEFAULT 'USD',
    transaction_date DATE NOT NULL,
    description TEXT,
    
    -- Payment Info
    payment_method TEXT, -- 'credit_card', 'bank_transfer', 'cash', 'other'
    payment_status TEXT DEFAULT 'pending', -- 'pending', 'completed', 'failed', 'refunded'
    payment_reference TEXT,
    
    -- Attribution
    attribution_source TEXT, -- 'meta_ads', 'organic', 'referral'
    meta_campaign_id VARCHAR(255),
    meta_ad_id VARCHAR(255),
    
    -- Metadata
    invoice_number TEXT,
    notes TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sales_transactions_tenant ON sales_transactions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_sales_transactions_opportunity ON sales_transactions(tenant_id, opportunity_id);
CREATE INDEX IF NOT EXISTS idx_sales_transactions_lead ON sales_transactions(tenant_id, lead_id);
CREATE INDEX IF NOT EXISTS idx_sales_transactions_date ON sales_transactions(tenant_id, transaction_date);
CREATE INDEX IF NOT EXISTS idx_sales_transactions_source ON sales_transactions(tenant_id, attribution_source);

-- ============================================
-- 9. Helper Functions for ROI Calculations
-- ============================================
CREATE OR REPLACE FUNCTION calculate_campaign_roi(
    p_tenant_id INTEGER,
    p_campaign_id VARCHAR(255),
    p_start_date DATE,
    p_end_date DATE
) RETURNS TABLE (
    campaign_id VARCHAR(255),
    campaign_name TEXT,
    total_spend DECIMAL(12,2),
    total_revenue DECIMAL(12,2),
    leads_count INTEGER,
    opportunities_count INTEGER,
    roi_percentage DECIMAL(5,2)
) AS $$
BEGIN
    RETURN QUERY
    WITH campaign_spend AS (
        SELECT 
            mac.meta_campaign_id,
            mac.name,
            COALESCE(SUM(mai.spend), 0) as total_spend
        FROM meta_ads_campaigns mac
        LEFT JOIN meta_ads_insights mai ON mac.meta_campaign_id = mai.meta_campaign_id 
            AND mai.tenant_id = p_tenant_id
            AND mai.date BETWEEN p_start_date AND p_end_date
        WHERE mac.tenant_id = p_tenant_id 
            AND mac.meta_campaign_id = p_campaign_id
        GROUP BY mac.meta_campaign_id, mac.name
    ),
    campaign_revenue AS (
        SELECT 
            l.meta_campaign_id,
            COUNT(DISTINCT l.id) as leads_count,
            COUNT(DISTINCT o.id) as opportunities_count,
            COALESCE(SUM(st.amount), 0) as total_revenue
        FROM leads l
        LEFT JOIN opportunities o ON l.id = o.lead_id AND o.tenant_id = p_tenant_id
        LEFT JOIN sales_transactions st ON o.id = st.opportunity_id AND st.tenant_id = p_tenant_id
            AND st.transaction_date BETWEEN p_start_date AND p_end_date
            AND st.payment_status = 'completed'
        WHERE l.tenant_id = p_tenant_id 
            AND l.meta_campaign_id = p_campaign_id
            AND l.created_at BETWEEN p_start_date AND p_end_date
        GROUP BY l.meta_campaign_id
    )
    SELECT 
        cs.meta_campaign_id,
        cs.name,
        cs.total_spend,
        COALESCE(cr.total_revenue, 0),
        COALESCE(cr.leads_count, 0),
        COALESCE(cr.opportunities_count, 0),
        CASE 
            WHEN cs.total_spend > 0 THEN 
                ((COALESCE(cr.total_revenue, 0) - cs.total_spend) / cs.total_spend) * 100
            ELSE 0
        END as roi_percentage
    FROM campaign_spend cs
    LEFT JOIN campaign_revenue cr ON cs.meta_campaign_id = cr.meta_campaign_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Migration Complete
-- ============================================
COMMIT;

-- ============================================
-- Verification Queries
-- ============================================
/*
-- Verify tables were created
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN (
    'meta_ads_campaigns', 
    'meta_ads_insights', 
    'meta_templates', 
    'automation_rules', 
    'automation_logs',
    'opportunities',
    'sales_transactions'
)
ORDER BY table_name;

-- Verify leads table has new columns
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'leads' 
AND column_name IN ('lead_source', 'meta_campaign_id', 'meta_ad_id', 'meta_ad_headline', 'meta_ad_body', 'external_ids');

-- Test ROI function
SELECT * FROM calculate_campaign_roi(1, 'test_campaign_id', '2024-01-01', '2024-12-31');
*/