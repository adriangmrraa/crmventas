-- Migration Patch 008: CRM Sales Data Model
-- Creates tables for CRM niche: leads, whatsapp_connections, templates, campaigns
-- All tables include tenant_id for multi-tenancy sovereignty

-- ============================================
-- 1. LEADS (Replaces patients for CRM niche)
-- ============================================
CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    
    -- Contact Data
    phone_number TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    
    -- Pipeline Status
    status TEXT DEFAULT 'new', -- new, contacted, interested, negotiation, closed_won, closed_lost
    stage_id UUID, -- Future: customizable pipelines
    
    -- Assignment
    assigned_seller_id INTEGER REFERENCES users(id), -- Assigned seller
    
    -- Metadata
    source TEXT, -- 'meta_ads', 'website', 'referral'
    meta_lead_id TEXT, -- ID if from Meta Lead Ads
    tags JSONB DEFAULT '[]',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_lead_per_tenant UNIQUE (tenant_id, phone_number)
);

CREATE INDEX IF NOT EXISTS idx_leads_tenant_phone ON leads(tenant_id, phone_number);
CREATE INDEX IF NOT EXISTS idx_leads_seller ON leads(tenant_id, assigned_seller_id);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(tenant_id, status);

-- ============================================
-- 2. WHATSAPP_CONNECTIONS (Meta API credentials)
-- ============================================
CREATE TABLE IF NOT EXISTS whatsapp_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    seller_id INTEGER REFERENCES users(id), -- Optional: personal seller connection
    
    phonenumber_id TEXT NOT NULL,
    waba_id TEXT NOT NULL,
    access_token_vault_id TEXT NOT NULL, -- Reference to Vault (encrypted)
    
    status TEXT DEFAULT 'active', -- active, disconnected, expired
    friendly_name TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_whatsapp_conn_tenant ON whatsapp_connections(tenant_id);
CREATE INDEX IF NOT EXISTS idx_whatsapp_conn_seller ON whatsapp_connections(seller_id);

-- ============================================
-- 3. TEMPLATES (WhatsApp approved templates)
-- ============================================
CREATE TABLE IF NOT EXISTS templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    
    meta_template_id TEXT NOT NULL,
    name TEXT NOT NULL,
    language TEXT DEFAULT 'es',
    category TEXT, -- MARKETING, UTILITY, AUTHENTICATION
    
    components JSONB NOT NULL, -- Structure: header, body, footer, buttons
    status TEXT, -- APPROVED, REJECTED, PAUSED, PENDING
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_template_per_tenant UNIQUE (tenant_id, meta_template_id)
);

CREATE INDEX IF NOT EXISTS idx_templates_tenant ON templates(tenant_id);
CREATE INDEX IF NOT EXISTS idx_templates_status ON templates(tenant_id, status);

-- ============================================
-- 4. CAMPAIGNS (Mass sending campaigns)
-- ============================================
CREATE TABLE IF NOT EXISTS campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    
    name TEXT NOT NULL,
    template_id UUID REFERENCES templates(id),
    target_segment JSONB, -- Filters for leads (e.g., tags=['interested'])
    
    status TEXT DEFAULT 'draft', -- draft, scheduled, sending, completed, failed
    stats JSONB DEFAULT '{}', -- {sent: 100, delivered: 90, read: 50, replied: 10}
    
    scheduled_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_campaigns_tenant ON campaigns(tenant_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_campaigns_template ON campaigns(template_id);

-- ============================================
-- Migration Complete
-- ============================================
