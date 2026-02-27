-- ==================================================================================
-- DENTALOGIC & CRM VENTAS - SCHEMA UNIFICADO (MASTER)
-- ==================================================================================
-- Sistema de gestión dental y CRM Sales con IA
-- Versión: 2.0 (Nexus Evolution - Feb 2026)
-- ==================================================================================

-- ==================== CORE TABLES - MESSAGES & CHAT ====================

-- Table for inbound messages (dedupe/idempotency from WhatsApp)
CREATE TABLE IF NOT EXISTS inbound_messages (
    id BIGSERIAL PRIMARY KEY,
    provider TEXT NOT NULL,
    provider_message_id TEXT NOT NULL,
    event_id TEXT NULL,
    from_number TEXT NOT NULL,
    payload JSONB NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('received', 'processing', 'done', 'failed')),
    received_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ NULL,
    error TEXT NULL,
    correlation_id TEXT NULL,
    UNIQUE (provider, provider_message_id)
);

CREATE INDEX IF NOT EXISTS idx_inbound_messages_from_number_received_at ON inbound_messages (from_number, received_at DESC);
CREATE INDEX IF NOT EXISTS idx_inbound_messages_status ON inbound_messages (status);

-- Table for chat messages (source-of-truth)
CREATE TABLE IF NOT EXISTS chat_messages (
    id BIGSERIAL PRIMARY KEY,
    tenant_id INTEGER DEFAULT 1, -- Multi-tenant support
    from_number TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    correlation_id TEXT NULL
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_tenant_from_created ON chat_messages (tenant_id, from_number, created_at DESC);

-- ==================== TENANT & CONFIGURATION ====================

-- Tabla de configuración de la clínica/negocio (multi-tenant ready)
CREATE TABLE IF NOT EXISTS tenants (
    id SERIAL PRIMARY KEY,
    clinic_name TEXT NOT NULL DEFAULT 'Organización Nexus',
    bot_phone_number TEXT UNIQUE NOT NULL,
    owner_email TEXT,
    clinic_location TEXT,
    clinic_website TEXT,
    system_prompt_template TEXT, -- Prompt del agente IA
    
    -- Configuración Avanzada
    config JSONB DEFAULT '{}', -- {calendar_provider: 'local'|'google', etc.}
    niche_type TEXT DEFAULT 'crm_sales', -- dental, crm_sales, real_estate
    
    -- Usage Stats
    total_tokens_used BIGINT DEFAULT 0,
    total_tool_calls BIGINT DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Credentials Table (Secrets Management / The Vault)
CREATE TABLE IF NOT EXISTS credentials (
    id BIGSERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    value TEXT NOT NULL,
    category VARCHAR(50) DEFAULT 'general',
    scope TEXT DEFAULT 'global',
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, name)
);

CREATE INDEX IF NOT EXISTS idx_credentials_tenant_name ON credentials(tenant_id, name);

-- System Events (Audit Trail - Nexus Security v7.7)
CREATE TABLE IF NOT EXISTS system_events (
    id BIGSERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID, -- Reference to users.id
    event_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) DEFAULT 'info' CHECK (severity IN ('info', 'warning', 'critical')),
    message TEXT,
    payload JSONB DEFAULT '{}',
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_system_events_tenant ON system_events(tenant_id);
CREATE INDEX IF NOT EXISTS idx_system_events_type ON system_events(event_type);
CREATE INDEX IF NOT EXISTS idx_system_events_created ON system_events(created_at DESC);

-- Insert Default Tenant
INSERT INTO tenants (clinic_name, bot_phone_number, clinic_location, niche_type) 
VALUES ('CRM Ventas Demo', '5491100000000', 'Argentina', 'crm_sales') 
ON CONFLICT (bot_phone_number) DO NOTHING;

-- ==================== USERS & PROFESSIONALS (RBAC) ====================

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('ceo', 'professional', 'secretary', 'setter', 'closer')),
    status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'suspended')),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    professional_id INTEGER NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);

CREATE TABLE IF NOT EXISTS professionals (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    phone_number VARCHAR(20),
    specialty VARCHAR(100),
    registration_id VARCHAR(50), -- Matrícula / DNI
    
    is_active BOOLEAN DEFAULT TRUE,
    google_calendar_id VARCHAR(255),
    working_hours JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_professionals_tenant ON professionals(tenant_id);
CREATE INDEX IF NOT EXISTS idx_professionals_user_id ON professionals(user_id);

CREATE TABLE IF NOT EXISTS sellers (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255),
    phone_number VARCHAR(50),
    
    is_active BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id)
);

CREATE INDEX IF NOT EXISTS idx_sellers_tenant ON sellers(tenant_id);
CREATE INDEX IF NOT EXISTS idx_sellers_user_id ON sellers(user_id);

-- ==================== CLIENTS & LEADS (CRM CORE) ====================

-- Table for Leads (Consolidated Marketing Inbound)
CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    -- Contact Information
    phone_number VARCHAR(50) NOT NULL,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    
    -- Identity & Social
    dni VARCHAR(15),
    social_links JSONB DEFAULT '{}', -- {instagram, facebook, linkedin}
    
    -- Pipeline & Status
    status TEXT DEFAULT 'new', -- new, contacted, interested, negotiation, closed_won, closed_lost
    lead_score TEXT,
    stage_id UUID,
    
    -- Marketing Attribution (Last Click)
    source TEXT DEFAULT 'whatsapp_inbound',
    lead_source VARCHAR(50) DEFAULT 'ORGANIC', -- ORGANIC, META_ADS, REFERRAL, APIFY
    meta_campaign_id VARCHAR(255),
    meta_ad_id VARCHAR(255),
    meta_ad_headline TEXT,
    meta_ad_body TEXT,
    meta_lead_id TEXT,
    external_ids JSONB DEFAULT '{}',
    
    -- Assignment
    assigned_seller_id UUID REFERENCES users(id),
    
    -- Apify & Prospecting Data
    apify_title TEXT,
    apify_category_name TEXT,
    apify_address TEXT,
    apify_city TEXT,
    apify_state TEXT,
    apify_country_code TEXT,
    apify_website TEXT,
    apify_place_id TEXT,
    apify_total_score DOUBLE PRECISION,
    apify_reviews_count INTEGER,
    apify_scraped_at TIMESTAMPTZ,
    apify_raw JSONB DEFAULT '{}',
    apify_rating FLOAT,
    apify_reviews INTEGER,
    prospecting_niche TEXT,
    prospecting_location_query TEXT,
    
    -- Outreach Controls
    outreach_message_sent BOOLEAN DEFAULT FALSE,
    outreach_send_requested BOOLEAN DEFAULT FALSE,
    outreach_last_requested_at TIMESTAMPTZ,
    outreach_last_sent_at TIMESTAMPTZ,
    outreach_message_content TEXT,
    
    -- Chat Management
    human_handoff_requested BOOLEAN DEFAULT FALSE,
    human_override_until TIMESTAMPTZ DEFAULT NULL,
    
    -- Metadata
    tags JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT leads_tenant_phone_unique UNIQUE (tenant_id, phone_number)
);

CREATE INDEX IF NOT EXISTS idx_leads_tenant_phone ON leads(tenant_id, phone_number);
CREATE INDEX IF NOT EXISTS idx_leads_lead_source ON leads(tenant_id, lead_source);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(tenant_id, status);

-- Table for Clients (Converted Leads / Permanent Customers)
CREATE TABLE IF NOT EXISTS clients (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    phone_number VARCHAR(50) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active',
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT clients_tenant_phone_unique UNIQUE (tenant_id, phone_number)
);

-- ==================== SALES PIPELINE & TRANSACTIONS ====================

CREATE TABLE IF NOT EXISTS opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    lead_id UUID REFERENCES leads(id) NOT NULL,
    seller_id UUID REFERENCES users(id),
    
    name TEXT NOT NULL,
    description TEXT,
    value DECIMAL(12,2) NOT NULL,
    currency TEXT DEFAULT 'USD',
    stage TEXT NOT NULL, -- prospecting, qualification, proposal, negotiation, closed_won, closed_lost
    probability DECIMAL(5,2) DEFAULT 0,
    expected_close_date DATE,
    
    closed_at TIMESTAMP,
    close_reason TEXT,
    
    tags JSONB DEFAULT '[]',
    custom_fields JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sales_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    opportunity_id UUID REFERENCES opportunities(id),
    lead_id UUID REFERENCES leads(id),
    
    amount DECIMAL(12,2) NOT NULL,
    currency TEXT DEFAULT 'USD',
    transaction_date DATE NOT NULL,
    description TEXT,
    payment_method TEXT,
    payment_status TEXT DEFAULT 'pending',
    
    attribution_source TEXT, -- meta_ads, organic, referral
    meta_campaign_id VARCHAR(255),
    meta_ad_id VARCHAR(255),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==================== META ADS MARKETING HUB ====================

-- Meta OAuth Tokens per Tenant
CREATE TABLE IF NOT EXISTS meta_tokens (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    access_token TEXT NOT NULL,
    token_type VARCHAR(50),
    expires_at TIMESTAMP,
    meta_user_id VARCHAR(100),
    business_manager_id VARCHAR(100),
    page_id VARCHAR(255), -- ID of the main FB Page for webhooks
    scopes JSONB DEFAULT '[]',
    business_managers JSONB DEFAULT '[]',
    last_used_by UUID,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tenant_id, token_type)
);

CREATE INDEX IF NOT EXISTS idx_meta_tokens_page_id ON meta_tokens(page_id);

-- Meta Ads Campaigns (Sync from API)
CREATE TABLE IF NOT EXISTS meta_ads_campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    meta_campaign_id VARCHAR(255) NOT NULL,
    meta_account_id VARCHAR(255) NOT NULL,
    name TEXT NOT NULL,
    objective TEXT,
    status TEXT,
    daily_budget DECIMAL(12,2),
    lifetime_budget DECIMAL(12,2),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    spend DECIMAL(12,2) DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    leads_count INTEGER DEFAULT 0,
    roi_percentage DECIMAL(5,2) DEFAULT 0,
    last_synced_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_meta_campaign_per_tenant UNIQUE (tenant_id, meta_campaign_id)
);

CREATE TABLE IF NOT EXISTS meta_ads_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    meta_campaign_id VARCHAR(255) NOT NULL,
    date DATE NOT NULL,
    spend DECIMAL(12,2) DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    leads INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_insight_per_day UNIQUE (tenant_id, meta_campaign_id, date)
);

-- Meta HSM Templates
CREATE TABLE IF NOT EXISTS meta_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    meta_template_id VARCHAR(255) NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    language TEXT DEFAULT 'es',
    status TEXT,
    components JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_meta_template_per_tenant UNIQUE (tenant_id, meta_template_id)
);

-- Automation & Rules
CREATE TABLE IF NOT EXISTS automation_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    name TEXT NOT NULL,
    trigger_type TEXT NOT NULL,
    trigger_conditions JSONB NOT NULL,
    action_type TEXT NOT NULL,
    action_config JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS automation_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    rule_id UUID REFERENCES automation_rules(id),
    trigger_type TEXT NOT NULL,
    status TEXT NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==================== DENTAL LEGACY (Compatibility) ====================

-- Table for Patients (Maps to Leads in CRM niche)
CREATE TABLE IF NOT EXISTS patients (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    phone_number VARCHAR(20) NOT NULL,
    dni VARCHAR(15),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100),
    status VARCHAR(20) DEFAULT 'active',
    human_handoff_requested BOOLEAN DEFAULT FALSE,
    human_override_until TIMESTAMPTZ DEFAULT NULL,
    urgency_level VARCHAR(20) DEFAULT 'normal',
    urgency_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (tenant_id, phone_number)
);

CREATE TABLE IF NOT EXISTS clinical_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    record_date DATE NOT NULL DEFAULT CURRENT_DATE,
    professional_id INTEGER REFERENCES professionals(id),
    diagnosis TEXT,
    treatments JSONB DEFAULT '[]',
    treatment_plan JSONB DEFAULT '{}',
    clinical_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    appointment_datetime TIMESTAMPTZ NOT NULL,
    duration_minutes INTEGER DEFAULT 60,
    professional_id INTEGER REFERENCES professionals(id),
    appointment_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'scheduled',
    source VARCHAR(20) DEFAULT 'ai',
    google_calendar_event_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==================== SETTINGS & HELPERS ====================

CREATE TABLE IF NOT EXISTS treatment_types (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    default_duration_minutes INTEGER NOT NULL DEFAULT 30,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, code)
);

-- ==================================================================================
-- SCHEMA COMPLETE
-- ==================================================================================
