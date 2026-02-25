# 🗄️ META ADS DATABASE IMPLEMENTATION - CRM VENTAS

## 📊 RESUMEN TÉCNICO

**Objetivo:** Implementar esquema de base de datos completo para Meta Ads Marketing Hub y HSM Automation en CRM Ventas, migrando y adaptando las estructuras de ClinicForge.

**Migraciones ClinicForge:**
- Parche 19: Campos de atribución en `patients` table
- Parche 20: Soporte de identidad multi-plataforma (JSONB)
- Parche 21: Motor de automatización & expiración Meta
- Parche 30-35: Sistema de auditoría y credenciales

---

## 🏗️ ESQUEMA DE BASE DE DATOS

### **1. MIGRACIONES NECESARIAS**

#### **1.1. Migración 1: Campos de Atribución en Leads**
```sql
-- Agregar campos de atribución Meta Ads a tabla leads
DO $$
BEGIN
    -- Campo lead_source (reemplaza acquisition_source de ClinicForge)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'leads'
        AND column_name = 'lead_source'
    ) THEN
        ALTER TABLE leads ADD COLUMN lead_source VARCHAR(50) DEFAULT 'ORGANIC';
    END IF;

    -- Meta Campaign ID
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'leads'
        AND column_name = 'meta_campaign_id'
    ) THEN
        ALTER TABLE leads ADD COLUMN meta_campaign_id VARCHAR(255);
    END IF;

    -- Meta Ad ID
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'leads'
        AND column_name = 'meta_ad_id'
    ) THEN
        ALTER TABLE leads ADD COLUMN meta_ad_id VARCHAR(255);
    END IF;

    -- Meta Ad Headline
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'leads'
        AND column_name = 'meta_ad_headline'
    ) THEN
        ALTER TABLE leads ADD COLUMN meta_ad_headline TEXT;
    END IF;

    -- Meta Ad Body
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'leads'
        AND column_name = 'meta_ad_body'
    ) THEN
        ALTER TABLE leads ADD COLUMN meta_ad_body TEXT;
    END IF;

    -- External IDs (JSONB para identidad multi-plataforma)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'leads'
        AND column_name = 'external_ids'
    ) THEN
        ALTER TABLE leads ADD COLUMN external_ids JSONB DEFAULT '{}';
    END IF;
END $$;

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_leads_lead_source ON leads(lead_source);
CREATE INDEX IF NOT EXISTS idx_leads_meta_campaign_id ON leads(meta_campaign_id) WHERE meta_campaign_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_leads_meta_ad_id ON leads(meta_ad_id) WHERE meta_ad_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_leads_external_ids ON leads USING GIN (external_ids);
```

#### **1.2. Migración 2: Tabla de Campañas Meta Ads**
```sql
-- Tabla para almacenar campañas de Meta Ads
CREATE TABLE IF NOT EXISTS meta_ads_campaigns (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    campaign_id VARCHAR(255) NOT NULL,  -- ID de Meta
    name TEXT NOT NULL,
    objective VARCHAR(100),  -- TRAFFIC, CONVERSIONS, etc.
    status VARCHAR(50),  -- ACTIVE, PAUSED, DELETED
    daily_budget DECIMAL(10,2),
    lifetime_budget DECIMAL(10,2),
    start_time TIMESTAMPTZ,
    stop_time TIMESTAMPTZ,
    created_time TIMESTAMPTZ,
    updated_time TIMESTAMPTZ,
    account_id VARCHAR(255),
    account_name TEXT,
    -- Metadata adicional
    meta_data JSONB DEFAULT '{}',
    last_synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    UNIQUE (tenant_id, campaign_id)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_meta_ads_campaigns_tenant ON meta_ads_campaigns(tenant_id);
CREATE INDEX IF NOT EXISTS idx_meta_ads_campaigns_status ON meta_ads_campaigns(status);
CREATE INDEX IF NOT EXISTS idx_meta_ads_campaigns_account ON meta_ads_campaigns(account_id);
CREATE INDEX IF NOT EXISTS idx_meta_ads_campaigns_created ON meta_ads_campaigns(created_time DESC);
```

#### **1.3. Migración 3: Tabla de Insights (Métricas)**
```sql
-- Tabla para métricas diarias de campañas/ads
CREATE TABLE IF NOT EXISTS meta_ads_insights (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    campaign_id VARCHAR(255) NOT NULL,
    ad_id VARCHAR(255),
    date DATE NOT NULL,
    
    -- Métricas básicas
    impressions BIGINT DEFAULT 0,
    clicks BIGINT DEFAULT 0,
    spend DECIMAL(10,2) DEFAULT 0,
    
    -- Métricas CRM (atribución)
    leads_count INTEGER DEFAULT 0,
    opportunities_count INTEGER DEFAULT 0,
    sales_count INTEGER DEFAULT 0,
    revenue DECIMAL(10,2) DEFAULT 0,
    
    -- Métricas calculadas
    ctr DECIMAL(5,4) DEFAULT 0,  -- Click-through rate
    cpc DECIMAL(10,2) DEFAULT 0,  -- Cost per click
    cpa DECIMAL(10,2) DEFAULT 0,  -- Cost per acquisition (lead)
    roas DECIMAL(5,2) DEFAULT 0,  -- Return on ad spend
    
    -- Metadata
    breakdown JSONB DEFAULT '{}',  -- Desglose por edad, género, etc.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    UNIQUE (tenant_id, campaign_id, ad_id, date),
    FOREIGN KEY (tenant_id, campaign_id) 
        REFERENCES meta_ads_campaigns(tenant_id, campaign_id) 
        ON DELETE CASCADE
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_meta_ads_insights_tenant ON meta_ads_insights(tenant_id);
CREATE INDEX IF NOT EXISTS idx_meta_ads_insights_campaign ON meta_ads_insights(campaign_id);
CREATE INDEX IF NOT EXISTS idx_meta_ads_insights_date ON meta_ads_insights(date DESC);
CREATE INDEX IF NOT EXISTS idx_meta_ads_insights_ad ON meta_ads_insights(ad_id) WHERE ad_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_meta_ads_insights_tenant_date ON meta_ads_campaigns(tenant_id, date);
```

#### **1.4. Migración 4: Tabla de HSM Templates**
```sql
-- Tabla para templates de WhatsApp HSM
CREATE TABLE IF NOT EXISTS meta_templates (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    template_id VARCHAR(255) NOT NULL,  -- ID de Meta
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,  -- MARKETING, UTILITY, etc.
    language VARCHAR(10) NOT NULL,  -- es, en, etc.
    status VARCHAR(50) NOT NULL,  -- APPROVED, PENDING, REJECTED
    components JSONB NOT NULL,  -- Estructura del template
    example JSONB,  -- Ejemplo de uso
    quality_rating VARCHAR(50),  -- GREEN, YELLOW, RED
    rejected_reason TEXT,
    created_time TIMESTAMPTZ,  -- Cuando se creó en Meta
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    UNIQUE (tenant_id, template_id)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_meta_templates_tenant ON meta_templates(tenant_id);
CREATE INDEX IF NOT EXISTS idx_meta_templates_status ON meta_templates(status);
CREATE INDEX IF NOT EXISTS idx_meta_templates_category ON meta_templates(category);
CREATE INDEX IF NOT EXISTS idx_meta_templates_language ON meta_templates(language);
```

#### **1.5. Migración 5: Tabla de Automation Rules**
```sql
-- Tabla para reglas de automatización HSM
CREATE TABLE IF NOT EXISTS automation_rules (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    trigger_type VARCHAR(50) NOT NULL,  -- lead_followup, opportunity_reminder, etc.
    condition JSONB NOT NULL,  -- Condición en formato estructurado
    template_id VARCHAR(255) NOT NULL REFERENCES meta_templates(template_id),
    enabled BOOLEAN DEFAULT TRUE,
    delay_hours INTEGER DEFAULT 0,  -- Retraso después del trigger
    time_window_start TIME,  -- Ventana horaria inicio
    time_window_end TIME,    -- Ventana horaria fin
    max_executions_per_day INTEGER DEFAULT 1,
    last_triggered_at TIMESTAMPTZ,
    trigger_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    UNIQUE (tenant_id, name)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_automation_rules_tenant ON automation_rules(tenant_id);
CREATE INDEX IF NOT EXISTS idx_automation_rules_trigger_type ON automation_rules(trigger_type);
CREATE INDEX IF NOT EXISTS idx_automation_rules_enabled ON automation_rules(enabled) WHERE enabled = TRUE;
CREATE INDEX IF NOT EXISTS idx_automation_rules_template ON automation_rules(template_id);
```

#### **1.6. Migración 6: Tabla de Automation Logs**
```sql
-- Tabla para logs de ejecución de automatización
CREATE TABLE IF NOT EXISTS automation_logs (
    id BIGSERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    rule_id INTEGER REFERENCES automation_rules(id) ON DELETE SET NULL,
    lead_id INTEGER REFERENCES leads(id) ON DELETE SET NULL,
    template_id VARCHAR(255),
    phone VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,  -- PENDING, SENT, DELIVERED, READ, FAILED
    message_id VARCHAR(255),  -- ID del mensaje en WhatsApp
    parameters JSONB,  -- Parámetros usados en el template
    error_message TEXT,
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Índices
    INDEX idx_automation_logs_tenant (tenant_id),
    INDEX idx_automation_logs_rule (rule_id),
    INDEX idx_automation_logs_lead (lead_id),
    INDEX idx_automation_logs_status (status),
    INDEX idx_automation_logs_created (created_at DESC)
);
```

#### **1.7. Migración 7: Tabla de Credenciales (Ya existe en Nexus v7.7)**
```sql
-- Verificar si ya existe (creada en seguridad Nexus v7.7)
CREATE TABLE IF NOT EXISTS credentials (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name TEXT NOT NULL,  -- Ej: 'META_USER_LONG_TOKEN', 'META_APP_ACCESS_TOKEN'
    value TEXT NOT NULL,  -- Encriptado con Fernet
    category VARCHAR(50) DEFAULT 'general',  -- 'meta_ads', 'whatsapp', 'openai'
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE (tenant_id, name)
);

-- Índices (si no existen)
CREATE INDEX IF NOT EXISTS idx_credentials_tenant ON credentials(tenant_id);
CREATE INDEX IF NOT EXISTS idx_credentials_name ON credentials(name);
CREATE INDEX IF NOT EXISTS idx_credentials_category ON credentials(category);
```

### **2. RELACIONES ENTRE TABLAS**

#### **2.1. Diagrama de Relaciones:**
```
tenants
    ├── leads
    │   ├── meta_ads_campaigns (via meta_campaign_id)
    │   └── automation_logs
    │
    ├── meta_ads_campaigns
    │   └── meta_ads_insights
    │
    ├── meta_templates
    │   └── automation_rules
    │       └── automation_logs
    │
    └── credentials
```

#### **2.2. Foreign Keys:**
```sql
-- Agregar FK de leads a meta_ads_campaigns (opcional)
ALTER TABLE leads ADD CONSTRAINT fk_leads_meta_campaign 
    FOREIGN KEY (tenant_id, meta_campaign_id) 
    REFERENCES meta_ads_campaigns(tenant_id, campaign_id)
    ON DELETE SET NULL;

-- Agregar FK de automation_rules a meta_templates
ALTER TABLE automation_rules ADD CONSTRAINT fk_automation_rules_template
    FOREIGN KEY (template_id) 
    REFERENCES meta_templates(template_id)
    ON DELETE RESTRICT;
```

### **3. VISTAS Y FUNCIONES**

#### **3.1. Vista: Marketing Dashboard Stats**
```sql
-- Vista para dashboard de marketing
CREATE OR REPLACE VIEW marketing_dashboard_stats AS
SELECT 
    l.tenant_id,
    DATE_TRUNC('day', l.created_at) as date,
    COUNT(*) as total_leads,
    COUNT(CASE WHEN l.lead_source = 'META_ADS' THEN 1 END) as meta_leads,
    COUNT(CASE WHEN l.lead_source != 'META_ADS' THEN 1 END) as other_leads,
    COUNT(DISTINCT o.id) as opportunities,
    COALESCE(SUM(CASE WHEN t.status = 'completed' THEN t.amount ELSE 0 END), 0) as revenue,
    COALESCE(SUM(i.spend), 0) as marketing_spend
FROM leads l
LEFT JOIN opportunities o ON o.lead_id = l.id
LEFT JOIN sales_transactions t ON t.lead_id = l.id AND t.status = 'completed'
LEFT JOIN meta_ads_insights i ON i.campaign_id = l.meta_campaign_id 
    AND i.date = DATE(l.created_at)
    AND i.tenant_id = l.tenant_id
GROUP BY l.tenant_id, DATE_TRUNC('day', l.created_at);
```

#### **3.2. Función: Calcular ROI por Campaña**
```sql
-- Función para calcular ROI por campaña
CREATE OR REPLACE FUNCTION calculate_campaign_roi(
    p_tenant_id INTEGER,
    p_campaign_id VARCHAR,
    p_start_date DATE,
    p_end_date DATE
) RETURNS TABLE (
    campaign_id VARCHAR,
    campaign_name TEXT,
    total_spend DECIMAL,
    total_leads INTEGER,
    total_opportunities INTEGER,
    total_revenue DECIMAL,
    cpa DECIMAL,
    roas DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.campaign_id,
        c.name as campaign_name,
        COALESCE(SUM(i.spend), 0) as total_spend,
        COUNT(DISTINCT l.id) as total_leads,
        COUNT(DISTINCT o.id) as total_opportunities,
        COALESCE(SUM(t.amount), 0) as total_revenue,
        CASE 
            WHEN COUNT(DISTINCT l.id) > 0 THEN COALESCE(SUM(i.spend), 0) / COUNT(DISTINCT l.id)
            ELSE 0 
        END as cpa,
        CASE 
            WHEN COALESCE(SUM(i.spend), 0) > 0 THEN COALESCE(SUM(t.amount), 0) / COALESCE(SUM(i.spend), 0)
            ELSE 0 
        END as roas
    FROM meta_ads_campaigns c
    LEFT JOIN meta_ads_insights i ON i.campaign_id = c.campaign_id 
        AND i.tenant_id = c.tenant_id
        AND i.date BETWEEN p_start_date AND p_end_date
    LEFT JOIN leads l ON l.meta_campaign_id = c.campaign_id 
        AND l.tenant_id = c.tenant_id
        AND l.created_at::DATE BETWEEN p_start_date AND p_end_date
    LEFT JOIN opportunities o ON o.lead_id = l.id
    LEFT JOIN sales_transactions t ON t.lead_id = l.id 
        AND t.status = 'completed'
    WHERE c.tenant_id = p_tenant_id 
        AND c.campaign_id = p_campaign_id
    GROUP BY c.campaign_id, c.name;
END;
$$ LANGUAGE plpgsql;
```

#### **3.3. Función: Obtener Stats de Automatización**
```sql
-- Función para stats de automatización
CREATE OR REPLACE FUNCTION get_automation_stats(
    p_tenant_id INTEGER,
    p_start_date DATE,
    p_end_date DATE
) RETURNS TABLE (
    total_rules INTEGER,
    active_rules INTEGER,
    total_executions BIGINT,
    success_rate DECIMAL,
    most_used_template VARCHAR,
    leads_touched INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(DISTINCT r.id) as total_rules,
        COUNT(DISTINCT CASE WHEN r.enabled THEN r.id END) as active_rules,
        COUNT(DISTINCT l.id) as total_executions,
        CASE 
            WHEN COUNT(DISTINCT l.id) > 0 THEN 
                COUNT(DISTINCT CASE WHEN l.status IN ('SENT', 'DELIVERED', 'READ') THEN l.id END)::DECIMAL / COUNT(DISTINCT l.id) * 100
            ELSE 0 
        END as success_rate,
        (SELECT t.name FROM meta_templates t 
         JOIN automation_logs al ON al.template_id = t.template_id
         WHERE al.tenant_id = p_tenant_id
           AND al.created_at::DATE BETWEEN p_start_date AND p_end_date
         GROUP BY t.name ORDER BY COUNT(*) DESC LIMIT 1) as most_used_template,
        COUNT(DISTINCT l.lead_id) as leads_touched
    FROM automation_rules r
    LEFT JOIN automation_logs l ON l.rule_id = r.id
        AND l.created_at::DATE BETWEEN p_start_date AND p_end_date
    WHERE r.tenant_id = p_tenant_id;
END;
$$ LANGUAGE plpgsql;
```

### **4. TRIGGERS Y EVENTOS**

#### **4.1. Trigger: Actualizar updated_at automáticamente**
```sql
-- Trigger para actualizar updated_at en todas las tablas
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Aplicar trigger a meta_ads_campaigns
CREATE TRIGGER update_meta_ads_campaigns_updated_at
    BEFORE UPDATE ON meta_ads_campaigns
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Aplicar trigger a meta_ads_insights
CREATE TRIGGER update_meta_ads_insights_updated_at
    BEFORE UPDATE ON meta_ads_insights
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Aplicar trigger a meta_templates
CREATE TRIGGER update_meta_templates_updated_at
    BEFORE UPDATE ON meta_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Aplicar trigger a automation_rules
CREATE TRIGGER update_automation_rules_updated_at
    BEFORE UPDATE ON automation_rules
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

#### **4.2. Trigger: Incrementar contador en automation_rules**
```sql
-- Trigger para incrementar trigger_count cuando se ejecuta una regla
CREATE OR REPLACE FUNCTION increment_rule_trigger_count()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE automation_rules 
    SET trigger_count = trigger_count + 1,
        last_triggered_at = NOW(),
        success_count = success_count + CASE WHEN NEW.status IN ('SENT', 'DELIVERED', 'READ') THEN 1 ELSE 0 END,
        failure_count = failure_count + CASE WHEN NEW.status = 'FAILED' THEN 1 ELSE 0 END
    WHERE id = NEW.rule_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER increment_rule_counter
    AFTER INSERT ON automation_logs
    FOR EACH ROW
    EXECUTE FUNCTION increment_rule_trigger_count();
```

#### **4.3. Trigger: Validar límite diario de ejecuciones**
```sql
-- Trigger para validar límite diario de ejecuciones por regla
CREATE OR REPLACE FUNCTION validate_daily_execution_limit()
RETURNS TRIGGER AS $$
DECLARE
    daily_limit INTEGER;
    today_executions INTEGER;
BEGIN
    -- Obtener límite diario de la regla
    SELECT max_executions_per_day INTO daily_limit
    FROM automation_rules 
    WHERE id = NEW.rule_id;
    
    -- Contar ejecuciones hoy
    SELECT COUNT(*) INTO today_executions
    FROM automation_logs 
    WHERE rule_id = NEW.rule_id
      AND created_at::DATE = CURRENT_DATE;
    
    -- Validar límite
    IF today_executions >= daily_limit THEN
        RAISE EXCEPTION 'Límite diario de ejecuciones alcanzado para esta regla (%)', daily_limit;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER check_daily_execution_limit
    BEFORE INSERT ON automation_logs
    FOR EACH ROW
    EXECUTE FUNCTION validate_daily_execution_limit();
```

### **5. MIGRACIÓN PASO A PASO**

#### **Paso 1: Preparar Script de Migración**
```sql
-- save_as: migrations/meta_ads_migration.sql
BEGIN;

-- 1. Agregar campos a leads
DO $$ ... $$; -- (código de la sección 1.1)

-- 2. Crear tabla meta_ads_campaigns
CREATE TABLE IF NOT EXISTS meta_ads_campaigns (...);

-- 3. Crear tabla meta_ads_insights
CREATE TABLE IF NOT EXISTS meta_ads_insights (...);

-- 4. Crear tabla meta_templates
CREATE TABLE IF NOT EXISTS meta_templates (...);

-- 5. Crear tabla automation_rules
CREATE TABLE IF NOT EXISTS automation_rules (...);

-- 6. Crear tabla automation_logs
CREATE TABLE IF NOT EXISTS automation_logs (...);

-- 7. Crear índices
CREATE INDEX IF NOT EXISTS ...;

-- 8. Crear vistas
CREATE OR REPLACE VIEW marketing_dashboard_stats AS ...;

-- 9. Crear funciones
CREATE OR REPLACE FUNCTION calculate_campaign_roi(...) ...;

-- 10. Crear triggers
CREATE OR REPLACE FUNCTION update_updated_at_column() ...;

COMMIT;
```

#### **Paso 2: Ejecutar Migración en Producción**
```bash
# Conectar a base de datos CRM Ventas
psql -h localhost -U postgres -d crmventas -f migrations/meta_ads_migration.sql

# Verificar migración
psql -h localhost -U postgres -d crmventas -c "\dt meta_*"
psql -h localhost -U postgres -d crmventas -c "\df calculate_*"
```

#### **Paso 3: Verificar Integridad de Datos**
```sql
-- Verificar que todas las tablas se crearon correctamente
SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public'
  AND table_name LIKE 'meta_%'
  OR table_name LIKE 'automation_%'
ORDER BY table_name;

-- Verificar foreign keys
SELECT
    tc.table_name, 
    kcu.column_name, 
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name 
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND (tc.table_name LIKE 'meta_%' OR tc.table_name LIKE 'automation_%');
```

#### **Paso 4: Migrar Datos Existentes (si aplica)**
```sql
-- Si hay datos de marketing existentes en otra tabla
INSERT INTO meta_ads_campaigns (tenant_id, campaign_id, name, status, ...)
SELECT 
    tenant_id,
    campaign_id,
    campaign_name,
    status,
    ...
FROM legacy_marketing_campaigns
ON CONFLICT (tenant_id, campaign_id) DO NOTHING;

-- Actualizar leads con lead_source si vienen de campañas existentes
UPDATE leads l
SET lead_source = 'META_ADS',
    meta_campaign_id = c.campaign_id
FROM legacy_campaign_conversions c
WHERE l.id = c.lead_id
  AND l.lead_source IS NULL;
```

### **6. OPTIMIZACIONES DE PERFORMANCE**

#### **6.1. Particionamiento por Tenant y Fecha**
```sql
-- Particionar meta_ads_insights por tenant_id y date
CREATE TABLE meta_ads_insights_partitioned (
    LIKE meta_ads_insights INCLUDING ALL
) PARTITION BY LIST (tenant_id);

-- Crear particiones por tenant (ejemplo para tenant 1)
CREATE TABLE meta_ads_insights_tenant_1 
PARTITION OF meta_ads_insights_partitioned
FOR VALUES IN (1);

-- Crear subparticiones por fecha dentro de cada tenant
CREATE TABLE meta_ads_insights_tenant_1_2026_02 
PARTITION OF meta_ads_insights_tenant_1
FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
```

#### **6.2. Índices Compuestos para Queries Comunes**
```sql
-- Índice para queries de dashboard por tenant y fecha
CREATE INDEX IF NOT EXISTS idx_insights_tenant_date_campaign 
ON meta_ads_insights (tenant_id, date DESC, campaign_id);

-- Índice para queries de leads por fuente y fecha
CREATE INDEX IF NOT EXISTS idx_leads_tenant_source_date 
ON leads (tenant_id, lead_source, created_at DESC);

-- Índice para queries de automation por estado y fecha
CREATE INDEX IF NOT EXISTS idx_automation_logs_tenant_status_date 
ON automation_logs (tenant_id, status, created_at DESC);
```

#### **6.3. Materialized Views para Datos Agregados**
```sql
-- Vista materializada para stats diarios (refrescar cada hora)
CREATE MATERIALIZED VIEW marketing_daily_stats AS
SELECT 
    tenant_id,
    date,
    SUM(spend) as total_spend,
    SUM(leads_count) as total_leads,
    SUM(opportunities_count) as total_opportunities,
    SUM(revenue) as total_revenue
FROM meta_ads_insights
GROUP BY tenant_id, date
WITH DATA;

CREATE UNIQUE INDEX idx_marketing_daily_stats_unique 
ON marketing_daily_stats (tenant_id, date);

-- Refrescar vista materializada
REFRESH MATERIALIZED VIEW CONCURRENTLY marketing_daily_stats;
```

### **7. BACKUP Y RECOVERY**

#### **7.1. Script de Backup Específico para Marketing**
```bash
#!/bin/bash
# save_as: backup_marketing_data.sh

BACKUP_DIR="/backups/marketing"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup de tablas de marketing
pg_dump -h localhost -U postgres -d crmventas \
  -t 'meta_*' \
  -t 'automation_*' \
  -t 'leads' \
  -F c -f "$BACKUP_DIR/marketing_$DATE.dump"

# Backup de datos de la última semana (para recovery rápido)
pg_dump -h localhost -U postgres -d crmventas \
  --data-only \
  -t 'meta_ads_insights' \
  -t 'automation_logs' \
  --where="created_at > NOW() - INTERVAL '7 days'" \
  -f "$BACKUP_DIR/marketing_recent_$DATE.sql"

echo "Backup completado: $BACKUP_DIR/marketing_$DATE.dump"
```

#### **7.2. Script de Recovery**
```bash
#!/bin/bash
# save_as: restore_marketing_data.sh

BACKUP_FILE="$1"

if [ -z "$BACKUP_FILE" ]; then
    echo "Uso: $0 <archivo_backup>"
    exit 1
fi

# Restaurar backup
pg_restore -h localhost -U postgres -d crmventas \
  --clean --if-exists \
  "$BACKUP_FILE"

echo "Restauración completada desde: $BACKUP_FILE"
```

### **8. MONITORING Y MAINTENANCE**

#### **8.1. Queries de Monitoring**
```sql
-- Tamaño de tablas de marketing
SELECT 
    table_name,
    pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) as total_size,
    pg_size_pretty(pg_relation_size(quote_ident(table_name))) as table_size,
    pg_size_pretty(pg_total_relation_size(quote_ident(table_name)) - pg_relation_size(quote_ident(table_name))) as index_size
FROM information_schema.tables
WHERE table_schema = 'public'
  AND (table_name LIKE 'meta_%' OR table_name LIKE 'automation_%')
ORDER BY pg_total_relation_size(quote_ident(table_name)) DESC;

-- Crecimiento de datos (últimos 30 días)
SELECT 
    date,
    COUNT(*) as new_records,
    SUM(pg_column_size(t.*)) as size_bytes
FROM (
    SELECT created_at::DATE as date, * FROM meta_ads_insights
    UNION ALL
    SELECT created_at::DATE as date, * FROM automation_logs
) t
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY date
ORDER BY date DESC;

-- Performance de índices
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE tablename LIKE 'meta_%' OR tablename LIKE 'automation_%'
ORDER BY idx_scan DESC;
```

#### **8.2. Maintenance Programado**
```sql
-- Vacuum y analyze periódico
VACUUM ANALYZE meta_ads_insights;
VACUUM ANALYZE automation_logs;

-- Reindexar tablas grandes mensualmente
REINDEX TABLE CONCURRENTLY meta_ads_insights;
REINDEX TABLE CONCURRENTLY automation_logs;

-- Limpiar logs antiguos (mantener 90 días)
DELETE FROM automation_logs 
WHERE created_at < NOW() - INTERVAL '90 days'
  AND status IN ('DELIVERED', 'READ');

-- Archivar datos históricos (más de 1 año)
CREATE TABLE IF NOT EXISTS meta_ads_insights_archive (
    LIKE meta_ads_insights INCLUDING ALL
);

INSERT INTO meta_ads_insights_archive
SELECT * FROM meta_ads_insights
WHERE date < NOW() - INTERVAL '1 year';

DELETE FROM meta_ads_insights
WHERE date < NOW() - INTERVAL '1 year';
```

### **9. SEGURIDAD DE DATOS**

#### **9.1. Row Level Security (RLS)**
```sql
-- Habilitar RLS en tablas sensibles
ALTER TABLE meta_ads_campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE meta_ads_insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE automation_rules ENABLE ROW LEVEL SECURITY;

-- Política: Usuarios solo ven datos de su tenant
CREATE POLICY tenant_isolation_policy ON meta_ads_campaigns
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id')::integer);

CREATE POLICY tenant_isolation_policy ON meta_ads_insights
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id')::integer);

CREATE POLICY tenant_isolation_policy ON automation_rules
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id')::integer);
```

#### **9.2. Encriptación de Datos Sensibles**
```sql
-- Usar pgcrypto para encriptar datos sensibles
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Función para encriptar/desencriptar con clave por tenant
CREATE OR REPLACE FUNCTION encrypt_meta_data(
    data TEXT,
    tenant_id INTEGER
) RETURNS BYTEA AS $$
BEGIN
    RETURN pgp_sym_encrypt(
        data,
        -- Clave derivada de tenant_id + secret master
        encode(digest(tenant_id::text || 'META_SECRET_KEY', 'sha256'), 'hex')
    );
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION decrypt_meta_data(
    encrypted_data BYTEA,
    tenant_id INTEGER
) RETURNS TEXT AS $$
BEGIN
    RETURN pgp_sym_decrypt(
        encrypted_data,
        encode(digest(tenant_id::text || 'META_SECRET_KEY', 'sha256'), 'hex')
    );
END;
$$ LANGUAGE plpgsql;
```

### **10. IMPLEMENTACIÓN EN PRODUCCIÓN**

#### **10.1. Checklist Pre-Deploy:**
- [ ] Script de migración probado en staging
- [ ] Backup completo de base de datos
- [ ] Verificación de espacio en disco
- [ ] Notificación a usuarios (maintenance window)
- [ ] Rollback plan definido

#### **10.2. Procedimiento de Deploy:**
```bash
# 1. Notificar inicio de maintenance
# 2. Tomar backup completo
pg_dump -h localhost -U postgres -d crmventas -F c -f /backups