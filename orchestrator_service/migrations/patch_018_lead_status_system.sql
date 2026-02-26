BEGIN;

-- 1. Crear tabla lead_statuses
CREATE TABLE IF NOT EXISTS lead_statuses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    code TEXT NOT NULL,
    description TEXT,
    category TEXT,
    color VARCHAR(7) DEFAULT '#6B7280',
    icon VARCHAR(50) DEFAULT 'circle',
    badge_style TEXT DEFAULT 'default',
    is_active BOOLEAN DEFAULT TRUE,
    is_initial BOOLEAN DEFAULT FALSE,
    is_final BOOLEAN DEFAULT FALSE,
    requires_comment BOOLEAN DEFAULT FALSE,
    sort_order INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, code),
    CHECK (color ~ '^#[0-9A-Fa-f]{6}$'),
    CHECK (code ~ '^[a-z_]+$')
);

CREATE INDEX IF NOT EXISTS idx_lead_statuses_tenant ON lead_statuses(tenant_id);
CREATE INDEX IF NOT EXISTS idx_lead_statuses_active ON lead_statuses(tenant_id, is_active);
CREATE INDEX IF NOT EXISTS idx_lead_statuses_initial ON lead_statuses(tenant_id, is_initial);
CREATE INDEX IF NOT EXISTS idx_lead_statuses_final ON lead_statuses(tenant_id, is_final);

-- 2. Crear tabla lead_status_transitions
CREATE TABLE IF NOT EXISTS lead_status_transitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    from_status_code TEXT,
    to_status_code TEXT NOT NULL,
    is_allowed BOOLEAN DEFAULT TRUE,
    requires_approval BOOLEAN DEFAULT FALSE,
    approval_role TEXT,
    max_daily_transitions INTEGER,
    label TEXT,
    description TEXT,
    icon VARCHAR(50),
    button_style TEXT DEFAULT 'default',
    validation_rules JSONB DEFAULT '{}',
    pre_conditions JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id, from_status_code) REFERENCES lead_statuses(tenant_id, code) ON DELETE CASCADE,
    FOREIGN KEY (tenant_id, to_status_code) REFERENCES lead_statuses(tenant_id, code) ON DELETE CASCADE,
    UNIQUE(tenant_id, from_status_code, to_status_code)
);

CREATE INDEX IF NOT EXISTS idx_transitions_from ON lead_status_transitions(tenant_id, from_status_code);
CREATE INDEX IF NOT EXISTS idx_transitions_to ON lead_status_transitions(tenant_id, to_status_code);
CREATE INDEX IF NOT EXISTS idx_transitions_allowed ON lead_status_transitions(tenant_id, is_allowed);

-- 3. Crear tabla lead_status_history
CREATE TABLE IF NOT EXISTS lead_status_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    from_status_code TEXT,
    to_status_code TEXT NOT NULL,
    changed_by_user_id UUID REFERENCES users(id),
    changed_by_name TEXT,
    changed_by_role TEXT,
    changed_by_ip INET,
    changed_by_user_agent TEXT,
    comment TEXT,
    reason_code TEXT,
    source TEXT DEFAULT 'manual',
    metadata JSONB DEFAULT '{}',
    session_id UUID,
    request_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_history_lead_tenant ON lead_status_history(lead_id, tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_history_tenant_date ON lead_status_history(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_history_user ON lead_status_history(changed_by_user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_history_status ON lead_status_history(to_status_code, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_history_source ON lead_status_history(source, created_at DESC);

-- 4. Crear tabla lead_status_triggers
CREATE TABLE IF NOT EXISTS lead_status_triggers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    trigger_name TEXT NOT NULL,
    from_status_code TEXT,
    to_status_code TEXT NOT NULL,
    action_type TEXT NOT NULL,
    action_config JSONB NOT NULL,
    execution_mode TEXT DEFAULT 'immediate',
    delay_minutes INTEGER DEFAULT 0,
    scheduled_time TIME,
    timezone TEXT DEFAULT 'UTC',
    conditions JSONB DEFAULT '{}',
    filters JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    max_executions INTEGER,
    error_handling TEXT DEFAULT 'retry',
    retry_count INTEGER DEFAULT 3,
    retry_delay_minutes INTEGER DEFAULT 5,
    description TEXT,
    tags TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_executed_at TIMESTAMP,
    execution_count INTEGER DEFAULT 0,
    FOREIGN KEY (tenant_id, from_status_code) REFERENCES lead_statuses(tenant_id, code) ON DELETE CASCADE,
    FOREIGN KEY (tenant_id, to_status_code) REFERENCES lead_statuses(tenant_id, code) ON DELETE CASCADE,
    CHECK (action_type IN ('email', 'whatsapp', 'task', 'webhook', 'api_call', 'notification')),
    CHECK (execution_mode IN ('immediate', 'delayed', 'scheduled'))
);

CREATE INDEX IF NOT EXISTS idx_triggers_active ON lead_status_triggers(tenant_id, is_active, to_status_code);
CREATE INDEX IF NOT EXISTS idx_triggers_type ON lead_status_triggers(tenant_id, action_type);
CREATE INDEX IF NOT EXISTS idx_triggers_execution ON lead_status_triggers(tenant_id, execution_mode, scheduled_time);

-- 5. Crear tabla lead_status_trigger_logs
CREATE TABLE IF NOT EXISTS lead_status_trigger_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trigger_id UUID REFERENCES lead_status_triggers(id) ON DELETE CASCADE,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    from_status_code TEXT,
    to_status_code TEXT NOT NULL,
    execution_status TEXT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    execution_duration_ms INTEGER,
    result_data JSONB DEFAULT '{}',
    error_message TEXT,
    error_stack TEXT,
    retry_count INTEGER DEFAULT 0,
    worker_id TEXT,
    attempt_number INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_trigger_logs_status ON lead_status_trigger_logs(execution_status, created_at);
CREATE INDEX IF NOT EXISTS idx_trigger_logs_trigger ON lead_status_trigger_logs(trigger_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_trigger_logs_lead ON lead_status_trigger_logs(lead_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_trigger_logs_tenant ON lead_status_trigger_logs(tenant_id, created_at DESC);

-- 6. Modificar tabla leads (Añadir constraints se hará en post-migración de datos para evitar bloqueos/errores)
ALTER TABLE leads ADD COLUMN IF NOT EXISTS status_changed_at TIMESTAMP;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS status_changed_by UUID REFERENCES users(id);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS days_in_current_status INTEGER GENERATED ALWAYS AS (
    EXTRACT(DAY FROM (COALESCE(status_changed_at, created_at) - CURRENT_TIMESTAMP))
) STORED;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS status_metadata JSONB DEFAULT '{}';

COMMIT;
