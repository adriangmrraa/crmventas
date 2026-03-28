import asyncpg
import os
import json
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any

from contextlib import asynccontextmanager

POSTGRES_DSN = os.getenv("POSTGRES_DSN")

class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    @asynccontextmanager
    async def get_connection(self):
        async with self.pool.acquire() as conn:
            yield conn

    async def _init_connection(self, conn):
        """Registra codecs para JSON/JSONB en cada conexión del pool para soporte nativo de tipos Python."""
        await conn.set_type_codec(
            'json',
            encoder=json.dumps,
            decoder=json.loads,
            schema='pg_catalog'
        )
        await conn.set_type_codec(
            'jsonb',
            encoder=json.dumps,
            decoder=json.loads,
            schema='pg_catalog'
        )

    async def connect(self):
        """Conecta al pool de PostgreSQL y ejecuta auto-migraciones."""
        if not self.pool:
            if not POSTGRES_DSN:
                print("❌ ERROR: POSTGRES_DSN environment variable is not set!")
                return

            dsn = POSTGRES_DSN.replace("postgresql+asyncpg://", "postgresql://")
            
            try:
                self.pool = await asyncpg.create_pool(dsn, init=self._init_connection)
            except Exception as e:
                print(f"❌ ERROR: Failed to create database pool: {e}")
                return
            
            await self._run_auto_migrations()
    
    async def _run_auto_migrations(self):
        """
        Sistema de Auto-Migración (Maintenance Robot / Schema Surgeon).
        Garantiza idempotencia y resiliencia en redimensionamientos de base de datos.
        """
        import logging
        logger = logging.getLogger("db")
        
        try:
            async with self.pool.acquire() as conn:
                critical_tables = ['tenants', 'users', 'leads']
                existing_tables = await conn.fetch("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = ANY($1)
                """, critical_tables)
                
                existing_table_names = [r['table_name'] for r in existing_tables]
                foundation_needed = len(existing_table_names) < len(critical_tables)
            
            if foundation_needed:
                logger.warning(f"⚠️ Esquema incompleto (encontrado: {existing_table_names}), aplicando Foundation...")
                await self._apply_foundation(logger)
            
            await self._run_evolution_pipeline(logger)
            logger.info("✅ Database optimized and synced (Maintenance Robot OK)")
            
        except Exception as e:
            import traceback
            logger.error(f"❌ Error in Maintenance Robot: {e}")
            logger.debug(traceback.format_exc())

    async def _apply_foundation(self, logger):
        """Ejecuta el esquema base dentalogic_schema.sql"""
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "..", "db", "init", "dentalogic_schema.sql"),
            os.path.join(os.path.dirname(__file__), "db", "init", "dentalogic_schema.sql"),
            "/app/db/init/dentalogic_schema.sql"
        ]
        
        schema_path = next((p for p in possible_paths if os.path.exists(p)), None)
        if not schema_path:
            logger.error("❌ Foundation schema not found!")
            return

        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        clean_lines = [line.split('--')[0].rstrip() for line in schema_sql.splitlines() if line.strip()]
        clean_sql = "\n".join(clean_lines)
        
        async with self.pool.acquire() as conn:
            try:
                await conn.execute(clean_sql)
                logger.info("✅ Foundation applied.")
            except Exception as e:
                logger.error(f"❌ Error applying Foundation: {e}")

    async def _run_evolution_pipeline(self, logger):
        """Pipeline de parches atómicos e idempotentes."""
        patches = [
            # Parche 1: Columna user_id en professionals
            "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='professionals' AND column_name='user_id') THEN ALTER TABLE professionals ADD COLUMN user_id UUID REFERENCES users(id) ON DELETE SET NULL; END IF; END $$;",
            
            # Parche 2: Asegurar tabla 'leads' (CRM Core)
            """
            DO $$ BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'leads') THEN
                    CREATE TABLE leads (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                        phone_number VARCHAR(50) NOT NULL,
                        first_name TEXT,
                        last_name TEXT,
                        status TEXT DEFAULT 'new',
                        source TEXT DEFAULT 'whatsapp_inbound',
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW(),
                        CONSTRAINT leads_tenant_phone_unique UNIQUE (tenant_id, phone_number)
                    );
                END IF;
            END $$;
            """,

            # Parche 3: Asegurar tabla 'credentials' y sus columnas críticas (Vault)
            """
            DO $$ BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'credentials') THEN
                    CREATE TABLE credentials (
                        id BIGSERIAL PRIMARY KEY,
                        tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
                        name VARCHAR(255) NOT NULL,
                        value TEXT NOT NULL,
                        category VARCHAR(50) DEFAULT 'general',
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW(),
                        UNIQUE(tenant_id, name)
                    );
                END IF;
                -- Asegurar columnas de timestamp si la tabla existía pero era antigua
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='credentials' AND column_name='created_at') THEN
                    ALTER TABLE credentials ADD COLUMN created_at TIMESTAMPTZ DEFAULT NOW();
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='credentials' AND column_name='updated_at') THEN
                    ALTER TABLE credentials ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();
                END IF;
            END $$;
            """,

            # Parche 4: Asegurar tabla 'meta_tokens'
            """
            DO $$ BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'meta_tokens') THEN
                    CREATE TABLE meta_tokens (
                        id SERIAL PRIMARY KEY,
                        tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                        access_token TEXT NOT NULL,
                        token_type VARCHAR(50),
                        page_id VARCHAR(255),
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW(),
                        UNIQUE(tenant_id, token_type)
                    );
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='meta_tokens' AND column_name='page_id') THEN
                    ALTER TABLE meta_tokens ADD COLUMN page_id VARCHAR(255);
                END IF;
            END $$;
            """,

            # Parche 5: Columnas extendidas en 'leads' y roles CRM
            """
            DO $$ BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='leads' AND column_name='email') THEN
                    ALTER TABLE leads ADD COLUMN email TEXT;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='leads' AND column_name='meta_lead_id') THEN
                    ALTER TABLE leads ADD COLUMN meta_lead_id TEXT;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='leads' AND column_name='assigned_seller_id') THEN
                    ALTER TABLE leads ADD COLUMN assigned_seller_id UUID REFERENCES users(id);
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='leads' AND column_name='stage_id') THEN
                    ALTER TABLE leads ADD COLUMN stage_id UUID;
                END IF;
                -- Roles de venta
                ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;
                ALTER TABLE users ADD CONSTRAINT users_role_check CHECK (role IN ('ceo', 'professional', 'secretary', 'setter', 'closer'));
            EXCEPTION WHEN others THEN NULL; END $$;
            """,

            # Parche 6: Tabla 'system_events' (Auditoría v7.7.3)
            """
            DO $$ BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'system_events') THEN
                    CREATE TABLE system_events (
                        id BIGSERIAL PRIMARY KEY,
                        tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
                        event_type VARCHAR(100) NOT NULL,
                        severity VARCHAR(20) DEFAULT 'info',
                        message TEXT,
                        payload JSONB DEFAULT '{}',
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    );
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='system_events' AND column_name='tenant_id') THEN
                    ALTER TABLE system_events ADD COLUMN tenant_id INTEGER REFERENCES tenants(id);
                END IF;
                CREATE INDEX IF NOT EXISTS idx_system_events_payload ON system_events USING gin(payload);
            END $$;
            """,

            # Parche 7: Tablas de Marketing Hub, Automatización y Leads Extended
            """
            DO $$ BEGIN
                CREATE TABLE IF NOT EXISTS meta_ads_campaigns (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
                    meta_campaign_id VARCHAR(255) NOT NULL,
                    name TEXT NOT NULL,
                    status TEXT,
                    spend DECIMAL(12,2) DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT unique_meta_campaign_per_tenant UNIQUE (tenant_id, meta_campaign_id)
                );
                CREATE TABLE IF NOT EXISTS automation_rules (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
                    name TEXT NOT NULL,
                    trigger_type TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                -- Prospecting fields in leads
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='leads' AND column_name='apify_title') THEN
                    ALTER TABLE leads ADD COLUMN apify_title TEXT, ADD COLUMN apify_category_name TEXT, ADD COLUMN apify_address TEXT;
                    ALTER TABLE leads ADD COLUMN apify_reviews_count INTEGER, ADD COLUMN apify_rating FLOAT;
                END IF;
            END $$;
            """,

            # Parche 8: Notifications 2.0 Schema
            """
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'notifications') THEN
                    CREATE TABLE notifications (
                        id VARCHAR(255) PRIMARY KEY,
                        tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
                        type VARCHAR(100) NOT NULL,
                        title VARCHAR(255) NOT NULL,
                        message TEXT NOT NULL,
                        priority VARCHAR(50) DEFAULT 'medium',
                        recipient_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
                        sender_id UUID REFERENCES users(id) ON DELETE SET NULL,
                        related_entity_type VARCHAR(100),
                        related_entity_id VARCHAR(255),
                        metadata JSONB,
                        read BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        expires_at TIMESTAMPTZ
                    );
                    CREATE INDEX idx_notifications_recipient_tenant ON notifications(recipient_id, tenant_id, created_at DESC);
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='notifications' AND column_name='tenant_id') THEN
                    ALTER TABLE notifications ADD COLUMN tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE;
                END IF;

                -- View for unread counts
                IF NOT EXISTS (SELECT 1 FROM information_schema.views WHERE table_name = 'unread_notifications_count') THEN
                    CREATE VIEW unread_notifications_count AS
                    SELECT 
                        recipient_id as user_id,
                        COUNT(*) as count,
                        COUNT(*) FILTER (WHERE priority = 'critical') as critical_count,
                        COUNT(*) FILTER (WHERE priority = 'high') as high_count,
                        COUNT(*) FILTER (WHERE priority = 'medium') as medium_count,
                        COUNT(*) FILTER (WHERE priority = 'low') as low_count
                    FROM notifications
                    WHERE read = FALSE
                    GROUP BY recipient_id;
                END IF;
            END $$;
            """,
            # Parche 9: Pipeline de Ventas (Opportunities, Transactions & Clients)
            """
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'clients') THEN
                    CREATE TABLE clients (
                        id SERIAL PRIMARY KEY,
                        tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
                        phone_number VARCHAR(50) NOT NULL,
                        first_name VARCHAR(100),
                        last_name VARCHAR(100),
                        status VARCHAR(50) DEFAULT 'active',
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        CONSTRAINT clients_tenant_phone_unique UNIQUE (tenant_id, phone_number)
                    );
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'opportunities') THEN
                    CREATE TABLE opportunities (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                        lead_id UUID REFERENCES leads(id) NOT NULL,
                        seller_id UUID REFERENCES users(id),
                        name TEXT NOT NULL,
                        value DECIMAL(12,2) NOT NULL,
                        stage TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sales_transactions') THEN
                    CREATE TABLE sales_transactions (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                        opportunity_id UUID REFERENCES opportunities(id),
                        amount DECIMAL(12,2) NOT NULL,
                        transaction_date DATE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'seller_agenda_events') THEN
                    CREATE TABLE seller_agenda_events (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                        seller_id INTEGER NOT NULL REFERENCES professionals(id) ON DELETE CASCADE,
                        title TEXT NOT NULL,
                        start_datetime TIMESTAMPTZ NOT NULL,
                        end_datetime TIMESTAMPTZ NOT NULL,
                        lead_id UUID REFERENCES leads(id),
                        status TEXT DEFAULT 'scheduled'
                    );
                END IF;
            END $$;
            """,

            # Parche 9: Auto-activación del primer CEO (Nexus Onboarding)
            """
            DO $$ 
            BEGIN 
                -- Si no hay ningún CEO activo, activamos todos los CEOs pendientes
                IF NOT EXISTS (SELECT 1 FROM users WHERE role = 'ceo' AND status = 'active') THEN
                    UPDATE users SET status = 'active' WHERE role = 'ceo' AND status = 'pending';
                    -- Sincronizar con profesionales si existe el registro correspondiente
                    UPDATE professionals SET is_active = TRUE 
                    WHERE email IN (SELECT email FROM users WHERE role = 'ceo' AND status = 'active');
                END IF;
            END $$;
            """,

            # Parche 10: Asegurar tenant_id en users y constraints finales
            """
            DO $$ BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='tenant_id') THEN
                    ALTER TABLE users ADD COLUMN tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE;
                END IF;
            EXCEPTION WHEN others THEN NULL; END $$;
            """,

            # Parche 11: Sistema de Asignación de Vendedores (CEO Control)
            """
            DO $$ BEGIN 
                -- 1. Add seller assignment columns to chat_messages
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='chat_messages' AND column_name='assigned_seller_id') THEN
                    ALTER TABLE chat_messages 
                    ADD COLUMN assigned_seller_id UUID REFERENCES users(id),
                    ADD COLUMN assigned_at TIMESTAMPTZ,
                    ADD COLUMN assigned_by UUID REFERENCES users(id),
                    ADD COLUMN assignment_source TEXT DEFAULT 'manual';
                END IF;
                
                -- 2. Create seller_metrics table for performance tracking
                IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'seller_metrics') THEN
                    CREATE TABLE seller_metrics (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        seller_id UUID NOT NULL REFERENCES users(id),
                        tenant_id INTEGER NOT NULL REFERENCES tenants(id),
                        
                        -- Conversaciones
                        total_conversations INTEGER DEFAULT 0,
                        active_conversations INTEGER DEFAULT 0,
                        conversations_assigned_today INTEGER DEFAULT 0,
                        
                        -- Mensajes
                        total_messages_sent INTEGER DEFAULT 0,
                        total_messages_received INTEGER DEFAULT 0,
                        avg_response_time_seconds INTEGER,
                        
                        -- Leads
                        leads_assigned INTEGER DEFAULT 0,
                        leads_converted INTEGER DEFAULT 0,
                        conversion_rate DECIMAL(5,2),
                        
                        -- Prospección
                        prospects_generated INTEGER DEFAULT 0,
                        prospects_converted INTEGER DEFAULT 0,
                        
                        -- Tiempo
                        total_chat_minutes INTEGER DEFAULT 0,
                        avg_session_duration_minutes INTEGER,
                        
                        -- Metadata
                        last_activity_at TIMESTAMPTZ,
                        metrics_calculated_at TIMESTAMPTZ DEFAULT NOW(),
                        metrics_period_start TIMESTAMPTZ,
                        metrics_period_end TIMESTAMPTZ,
                        
                        -- Constraints
                        UNIQUE(seller_id, tenant_id, metrics_period_start),
                        CHECK (conversion_rate >= 0 AND conversion_rate <= 100)
                    );
                END IF;
                
                -- 3. Create assignment_rules table for auto-assignment configuration
                IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'assignment_rules') THEN
                    CREATE TABLE assignment_rules (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        tenant_id INTEGER NOT NULL REFERENCES tenants(id),
                        
                        -- Regla
                        rule_name TEXT NOT NULL,
                        rule_type TEXT NOT NULL CHECK (rule_type IN ('round_robin', 'performance', 'specialty', 'load_balance')),
                        is_active BOOLEAN DEFAULT TRUE,
                        priority INTEGER DEFAULT 0,
                        
                        -- Configuración
                        config JSONB NOT NULL DEFAULT '{}',
                        
                        -- Filtros
                        apply_to_lead_source TEXT[],
                        apply_to_lead_status TEXT[],
                        apply_to_seller_roles TEXT[],
                        
                        -- Límites
                        max_conversations_per_seller INTEGER,
                        min_response_time_seconds INTEGER,
                        
                        -- Metadata
                        description TEXT,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW(),
                        
                        UNIQUE(tenant_id, rule_name)
                    );
                END IF;
                
                -- 4. Add assignment tracking to leads table
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='leads' AND column_name='initial_assignment_source') THEN
                    ALTER TABLE leads 
                    ADD COLUMN initial_assignment_source TEXT,
                    ADD COLUMN assignment_history JSONB DEFAULT '[]';
                END IF;
                
                -- 5. Create indexes for performance
                CREATE INDEX IF NOT EXISTS idx_chat_messages_assigned_seller 
                ON chat_messages(assigned_seller_id);
                
                CREATE INDEX IF NOT EXISTS idx_chat_messages_assignment_source 
                ON chat_messages(assignment_source);
                
                CREATE INDEX IF NOT EXISTS idx_seller_metrics_tenant 
                ON seller_metrics(tenant_id);
                
                CREATE INDEX IF NOT EXISTS idx_seller_metrics_seller 
                ON seller_metrics(seller_id);
                
                CREATE INDEX IF NOT EXISTS idx_seller_metrics_period 
                ON seller_metrics(metrics_period_start DESC);
                
                -- 6. Insert default round-robin rule for each tenant
                INSERT INTO assignment_rules 
                (tenant_id, rule_name, rule_type, config, description, priority)
                SELECT id, 'Round Robin Default', 'round_robin', 
                       '{"enabled": true, "exclude_inactive": true}', 
                       'Default round-robin assignment for new conversations',
                       0
                FROM tenants
                ON CONFLICT (tenant_id, rule_name) DO NOTHING;
                
            EXCEPTION WHEN others THEN 
                RAISE NOTICE 'Parche 11: Error en sistema de asignación de vendedores: %', SQLERRM;
            END $$;
            """,
            # Parche 12: Asegurar tabla 'sellers' y columna 'phone_number' (Nexus CRM)
            """
            DO $$ BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sellers') THEN
                    CREATE TABLE sellers (
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
                END IF;
                -- Asegurar columna phone_number si la tabla existía pero era antigua
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='sellers' AND column_name='phone_number') THEN
                    ALTER TABLE sellers ADD COLUMN phone_number VARCHAR(50);
                END IF;
            END $$;
            """,
            # Parche 13: Asegurar columnas críticas en 'sellers' (Error 500 Fix)
            """
            DO $$ BEGIN 
                -- Asegurar created_at
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='sellers' AND column_name='created_at') THEN
                    ALTER TABLE sellers ADD COLUMN created_at TIMESTAMPTZ DEFAULT NOW();
                END IF;
                -- Asegurar updated_at
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='sellers' AND column_name='updated_at') THEN
                    ALTER TABLE sellers ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();
                END IF;
                -- Asegurar phone_number (doble verificación)
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='sellers' AND column_name='phone_number') THEN
                    ALTER TABLE sellers ADD COLUMN phone_number VARCHAR(50);
                END IF;
            END $$;
            """,
            # Parche 14: Backfill 'sellers' table for existing active users with relevant roles
            """
            DO $$ BEGIN 
                INSERT INTO sellers (user_id, tenant_id, first_name, last_name, email, is_active, created_at, updated_at)
                SELECT id, tenant_id, first_name, last_name, email, TRUE, NOW(), NOW()
                FROM users 
                WHERE status = 'active' 
                AND role IN ('setter', 'closer', 'professional', 'ceo')
                ON CONFLICT (user_id) DO NOTHING;
            END $$;
            """,

            # Parche 15: Lead Scoring — score column + breakdown JSONB
            """
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='leads' AND column_name='score') THEN
                    ALTER TABLE leads ADD COLUMN score INTEGER DEFAULT 0;
                    ALTER TABLE leads ADD COLUMN score_breakdown JSONB DEFAULT '{}';
                    ALTER TABLE leads ADD COLUMN score_updated_at TIMESTAMPTZ;
                    CREATE INDEX IF NOT EXISTS idx_leads_score ON leads (tenant_id, score DESC);
                    RAISE NOTICE 'Parche 15: Lead scoring columns added';
                END IF;
            EXCEPTION WHEN OTHERS THEN
                RAISE NOTICE 'Parche 15: Error: %', SQLERRM;
            END $$;
            """,

            # Parche 16: Task Management + lead import tracking
            """
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'lead_tasks') THEN
                    CREATE TABLE lead_tasks (
                        id SERIAL PRIMARY KEY,
                        tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                        lead_id UUID REFERENCES leads(id) ON DELETE CASCADE,
                        seller_id INTEGER REFERENCES sellers(id) ON DELETE SET NULL,
                        title TEXT NOT NULL,
                        description TEXT,
                        due_date TIMESTAMPTZ,
                        status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed')),
                        priority TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
                        completed_at TIMESTAMPTZ,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    );
                    CREATE INDEX idx_lead_tasks_tenant ON lead_tasks (tenant_id);
                    CREATE INDEX idx_lead_tasks_lead ON lead_tasks (lead_id);
                    CREATE INDEX idx_lead_tasks_pending ON lead_tasks (tenant_id, status) WHERE status != 'completed';
                    RAISE NOTICE 'Parche 16: lead_tasks table created';
                END IF;

                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='leads' AND column_name='company') THEN
                    ALTER TABLE leads ADD COLUMN company TEXT;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='leads' AND column_name='estimated_value') THEN
                    ALTER TABLE leads ADD COLUMN estimated_value DECIMAL(12,2) DEFAULT 0;
                END IF;
            EXCEPTION WHEN OTHERS THEN
                RAISE NOTICE 'Parche 16: Error: %', SQLERRM;
            END $$;
            """,

            # Parche 17: Lead Tags — JSONB array for AI auto-tagging (DEV-19)
            """
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='leads' AND column_name='tags') THEN
                    ALTER TABLE leads ADD COLUMN tags JSONB DEFAULT '[]';
                    CREATE INDEX IF NOT EXISTS idx_leads_tags ON leads USING gin(tags);
                    RAISE NOTICE 'Parche 17: Lead tags column added';
                END IF;
                -- Tag audit log
                IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'lead_tag_log') THEN
                    CREATE TABLE lead_tag_log (
                        id BIGSERIAL PRIMARY KEY,
                        tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                        lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
                        tags_added TEXT[] NOT NULL DEFAULT '{}',
                        reason TEXT,
                        source TEXT DEFAULT 'ai_agent',
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    );
                    CREATE INDEX idx_lead_tag_log_lead ON lead_tag_log (lead_id);
                    CREATE INDEX idx_lead_tag_log_tenant ON lead_tag_log (tenant_id, created_at DESC);
                    RAISE NOTICE 'Parche 17: lead_tag_log table created';
                END IF;
            EXCEPTION WHEN OTHERS THEN
                RAISE NOTICE 'Parche 17: Error: %', SQLERRM;
            END $$;
            """,

            # Parche 19: Lead Notes — handoff, internal notes, follow-ups (DEV-21)
            """
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'lead_notes') THEN
                    CREATE TABLE lead_notes (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                        lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
                        author_id UUID REFERENCES users(id) ON DELETE SET NULL,
                        note_type VARCHAR(50) NOT NULL DEFAULT 'internal'
                            CHECK (note_type IN ('handoff', 'post_call', 'internal', 'follow_up')),
                        content TEXT NOT NULL,
                        structured_data JSONB DEFAULT '{}',
                        visibility VARCHAR(50) NOT NULL DEFAULT 'all'
                            CHECK (visibility IN ('setter_closer', 'all', 'private')),
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    );
                    CREATE INDEX idx_lead_notes_lead ON lead_notes (lead_id, created_at DESC);
                    CREATE INDEX idx_lead_notes_tenant ON lead_notes (tenant_id, created_at DESC);
                    CREATE INDEX idx_lead_notes_author ON lead_notes (author_id);
                    CREATE INDEX idx_lead_notes_type ON lead_notes (tenant_id, note_type);
                    RAISE NOTICE 'Parche 19: lead_notes table created';
                END IF;
            EXCEPTION WHEN OTHERS THEN
                RAISE NOTICE 'Parche 19: Error: %', SQLERRM;
            END $$;
            """,

            # Parche 18: Lead Tags catalog — predefined tags with color/icon/category
            """
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'lead_tags') THEN
                    CREATE TABLE lead_tags (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                        name VARCHAR(100) NOT NULL,
                        color VARCHAR(7) NOT NULL DEFAULT '#6B7280',
                        icon VARCHAR(50),
                        category VARCHAR(100),
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        CONSTRAINT lead_tags_tenant_name_unique UNIQUE (tenant_id, name)
                    );
                    CREATE INDEX idx_lead_tags_tenant ON lead_tags(tenant_id, is_active);
                    RAISE NOTICE 'Parche 18: lead_tags catalog table created';
                END IF;
                -- Ensure GIN index exists on leads.tags for fast containment queries
                CREATE INDEX IF NOT EXISTS idx_leads_tags_gin ON leads USING gin(tags);
            EXCEPTION WHEN OTHERS THEN
                RAISE NOTICE 'Parche 18: Error: %', SQLERRM;
            END $$;
            """,

            # Parche 20: Lead Notes — soft-delete + updated_at for setter<->closer channel (DEV-23)
            """
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='lead_notes' AND column_name='is_deleted') THEN
                    ALTER TABLE lead_notes ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='lead_notes' AND column_name='deleted_at') THEN
                    ALTER TABLE lead_notes ADD COLUMN deleted_at TIMESTAMPTZ;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='lead_notes' AND column_name='deleted_by') THEN
                    ALTER TABLE lead_notes ADD COLUMN deleted_by UUID REFERENCES users(id) ON DELETE SET NULL;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='lead_notes' AND column_name='updated_at') THEN
                    ALTER TABLE lead_notes ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();
                END IF;
                CREATE INDEX IF NOT EXISTS idx_lead_notes_active ON lead_notes (lead_id, is_deleted) WHERE is_deleted = FALSE;
                RAISE NOTICE 'Parche 20: lead_notes soft-delete columns added (DEV-23)';
            EXCEPTION WHEN OTHERS THEN
                RAISE NOTICE 'Parche 20: Error: %', SQLERRM;
            END $$;
            """,

            # Parche 21: Lead Statuses + Transitions + History (DEV-27)
            """
            DO $$ BEGIN
                -- 1. Lead Statuses table
                IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'lead_statuses') THEN
                    CREATE TABLE lead_statuses (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                        name VARCHAR(100) NOT NULL,
                        code VARCHAR(50) NOT NULL,
                        description TEXT,
                        color VARCHAR(7) NOT NULL DEFAULT '#6B7280',
                        icon VARCHAR(50) DEFAULT 'circle',
                        badge_style VARCHAR(50) DEFAULT 'default',
                        category VARCHAR(50) DEFAULT 'active',
                        is_active BOOLEAN DEFAULT TRUE,
                        is_initial BOOLEAN DEFAULT FALSE,
                        is_final BOOLEAN DEFAULT FALSE,
                        requires_comment BOOLEAN DEFAULT FALSE,
                        sort_order INTEGER DEFAULT 0,
                        metadata JSONB DEFAULT '{}',
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW(),
                        CONSTRAINT lead_statuses_tenant_code_unique UNIQUE (tenant_id, code)
                    );
                    CREATE INDEX idx_lead_statuses_tenant ON lead_statuses (tenant_id, is_active, sort_order);
                    RAISE NOTICE 'Parche 21: lead_statuses table created';
                END IF;

                -- 2. Lead Status Transitions table
                IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'lead_status_transitions') THEN
                    CREATE TABLE lead_status_transitions (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                        from_status_code VARCHAR(50),
                        to_status_code VARCHAR(50) NOT NULL,
                        label TEXT,
                        description TEXT,
                        icon VARCHAR(50),
                        button_style VARCHAR(50) DEFAULT 'default',
                        is_allowed BOOLEAN DEFAULT TRUE,
                        requires_approval BOOLEAN DEFAULT FALSE,
                        approval_role VARCHAR(50),
                        sort_order INTEGER DEFAULT 0,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    );
                    CREATE INDEX idx_lead_status_transitions_tenant ON lead_status_transitions (tenant_id, from_status_code);
                    RAISE NOTICE 'Parche 21: lead_status_transitions table created';
                END IF;

                -- 3. Lead Status History table
                IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'lead_status_history') THEN
                    CREATE TABLE lead_status_history (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
                        tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                        from_status_code VARCHAR(50),
                        to_status_code VARCHAR(50) NOT NULL,
                        changed_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                        changed_by_name TEXT,
                        changed_by_role TEXT,
                        comment TEXT,
                        source TEXT DEFAULT 'manual',
                        metadata JSONB DEFAULT '{}',
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    );
                    CREATE INDEX idx_lead_status_history_lead ON lead_status_history (lead_id, created_at DESC);
                    CREATE INDEX idx_lead_status_history_tenant ON lead_status_history (tenant_id, created_at DESC);
                    RAISE NOTICE 'Parche 21: lead_status_history table created';
                END IF;

                -- 4. Seed default statuses for all tenants that don't have any yet
                INSERT INTO lead_statuses (tenant_id, name, code, description, color, icon, badge_style, category, is_active, is_initial, is_final, sort_order)
                SELECT t.id, s.name, s.code, s.description, s.color, s.icon, s.badge_style, s.category, TRUE, s.is_initial, s.is_final, s.sort_order
                FROM tenants t
                CROSS JOIN (VALUES
                    ('Nuevo',             'nuevo',            'Lead recién ingresado',           '#3B82F6', 'user-plus',    'info',    'initial', TRUE,  FALSE, 1),
                    ('Contactado',        'contactado',       'Se estableció contacto',          '#8B5CF6', 'phone',        'purple',  'active',  FALSE, FALSE, 2),
                    ('Calificado',        'calificado',       'Lead calificado con potencial',   '#F59E0B', 'star',         'warning', 'active',  FALSE, FALSE, 3),
                    ('Negociación',       'negociacion',      'En proceso de negociación',       '#EC4899', 'handshake',    'pink',    'active',  FALSE, FALSE, 4),
                    ('Cerrado Ganado',    'cerrado_ganado',   'Venta concretada',                '#10B981', 'check-circle', 'success', 'final',   FALSE, TRUE,  5),
                    ('Cerrado Perdido',   'cerrado_perdido',  'Oportunidad perdida',             '#EF4444', 'x-circle',     'danger',  'final',   FALSE, TRUE,  6)
                ) AS s(name, code, description, color, icon, badge_style, category, is_initial, is_final, sort_order)
                WHERE NOT EXISTS (
                    SELECT 1 FROM lead_statuses ls WHERE ls.tenant_id = t.id
                )
                ON CONFLICT (tenant_id, code) DO NOTHING;

                -- 5. Seed default transitions for all tenants that don't have any yet
                INSERT INTO lead_status_transitions (tenant_id, from_status_code, to_status_code, label, icon, button_style, is_allowed)
                SELECT t.id, tr.from_code, tr.to_code, tr.label, tr.icon, tr.btn_style, TRUE
                FROM tenants t
                CROSS JOIN (VALUES
                    ('nuevo',           'contactado',       'Contactar',          'phone',        'purple'),
                    ('nuevo',           'cerrado_perdido',  'Descartar',          'x-circle',     'danger'),
                    ('contactado',      'calificado',       'Calificar',          'star',         'warning'),
                    ('contactado',      'cerrado_perdido',  'Descartar',          'x-circle',     'danger'),
                    ('calificado',      'negociacion',      'Negociar',           'handshake',    'pink'),
                    ('calificado',      'cerrado_perdido',  'Descartar',          'x-circle',     'danger'),
                    ('negociacion',     'cerrado_ganado',   'Cerrar Ganado',      'check-circle', 'success'),
                    ('negociacion',     'cerrado_perdido',  'Cerrar Perdido',     'x-circle',     'danger'),
                    ('cerrado_perdido', 'nuevo',            'Reactivar',          'refresh-cw',   'info')
                ) AS tr(from_code, to_code, label, icon, btn_style)
                WHERE NOT EXISTS (
                    SELECT 1 FROM lead_status_transitions lst WHERE lst.tenant_id = t.id
                )
                ON CONFLICT DO NOTHING;

                -- 6. Add status_changed_at and status_changed_by to leads if missing
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='leads' AND column_name='status_changed_at') THEN
                    ALTER TABLE leads ADD COLUMN status_changed_at TIMESTAMPTZ;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='leads' AND column_name='status_changed_by') THEN
                    ALTER TABLE leads ADD COLUMN status_changed_by UUID REFERENCES users(id) ON DELETE SET NULL;
                END IF;

                RAISE NOTICE 'Parche 21: Lead statuses pipeline complete (DEV-27)';
            EXCEPTION WHEN OTHERS THEN
                RAISE NOTICE 'Parche 21: Error: %', SQLERRM;
            END $$;
            """,

            # Parche 22: Add missing columns to lead_status_history (DEV-28)
            """
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='lead_status_history' AND column_name='source') THEN
                    ALTER TABLE lead_status_history ADD COLUMN source TEXT DEFAULT 'manual';
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='lead_status_history' AND column_name='changed_by_role') THEN
                    ALTER TABLE lead_status_history ADD COLUMN changed_by_role TEXT;
                END IF;
                RAISE NOTICE 'Parche 22: lead_status_history missing columns added (DEV-28)';
            EXCEPTION WHEN OTHERS THEN
                RAISE NOTICE 'Parche 22: Error: %', SQLERRM;
            END $$;
            """,

            # Parche 23: Seed standard lead tags for all tenants (DEV-33)
            """
            DO $$
            DECLARE
                t_id INTEGER;
            BEGIN
                FOR t_id IN SELECT id FROM tenants LOOP
                    INSERT INTO lead_tags (tenant_id, name, color, icon, category, is_active)
                    VALUES
                        (t_id, 'caliente',            '#EF4444', 'flame',        'temperatura',  TRUE),
                        (t_id, 'tibio',               '#F59E0B', 'thermometer',  'temperatura',  TRUE),
                        (t_id, 'frio',                '#3B82F6', 'snowflake',    'temperatura',  TRUE),
                        (t_id, 'llamada_pactada',     '#06B6D4', 'phone',        'seguimiento',  TRUE),
                        (t_id, 'sin_respuesta',       '#6B7280', 'phone-off',    'seguimiento',  TRUE),
                        (t_id, 'precio_sensible',     '#F97316', 'dollar-sign',  'objecion',     TRUE),
                        (t_id, 'urgente',             '#DC2626', 'alert-circle', 'prioridad',    TRUE),
                        (t_id, 'requiere_seguimiento','#EC4899', 'clock',        'seguimiento',  TRUE),
                        (t_id, 'cerrado',             '#22C55E', 'check-circle', 'resultado',    TRUE),
                        (t_id, 'descartado',          '#71717A', 'x-circle',     'resultado',    TRUE),
                        (t_id, 'derivado_por_ia',     '#8B5CF6', 'cpu',          'ia',           TRUE),
                        (t_id, 'handoff_solicitado',  '#FBBF24', 'user-plus',    'ia',           TRUE),
                        (t_id, 'comparando_opciones', '#14B8A6', 'git-branch',   'objecion',     TRUE)
                    ON CONFLICT (tenant_id, name) DO NOTHING;
                END LOOP;
                RAISE NOTICE 'Parche 23: Standard lead tags seeded for all tenants (DEV-33)';
            EXCEPTION WHEN OTHERS THEN
                RAISE NOTICE 'Parche 23: Error: %', SQLERRM;
            END $$;
            """,

            # Parche 24: Full 9-status pipeline + transitions (DEV-32)
            """
            DO $$ BEGIN
                -- 1. Upsert all 9 statuses for every tenant (idempotent)
                INSERT INTO lead_statuses (tenant_id, name, code, description, color, icon, badge_style, category, is_active, is_initial, is_final, sort_order)
                SELECT t.id, s.name, s.code, s.description, s.color, s.icon, s.badge_style, s.category, TRUE, s.is_initial, s.is_final, s.sort_order
                FROM tenants t
                CROSS JOIN (VALUES
                    ('Nuevo',                 'nuevo',                 'Lead recién ingresado',               '#3B82F6', 'user-plus',    'info',    'initial',  TRUE,  FALSE, 1),
                    ('Contactado',            'contactado',            'Se estableció contacto',              '#8B5CF6', 'phone',        'purple',  'active',   FALSE, FALSE, 2),
                    ('Calificado',            'calificado',            'Lead calificado con potencial',       '#F59E0B', 'star',         'warning', 'active',   FALSE, FALSE, 3),
                    ('Llamada Agendada',      'llamada_agendada',      'Llamada de seguimiento agendada',     '#06B6D4', 'calendar',     'cyan',    'active',   FALSE, FALSE, 4),
                    ('En Negociación',        'negociacion',           'En proceso de negociación',           '#F97316', 'handshake',    'orange',  'active',   FALSE, FALSE, 5),
                    ('Cerrado Ganado',        'cerrado_ganado',        'Venta concretada',                    '#22C55E', 'check-circle', 'success', 'final',    FALSE, TRUE,  6),
                    ('Cerrado Perdido',       'cerrado_perdido',       'Oportunidad perdida',                 '#EF4444', 'x-circle',     'danger',  'final',    FALSE, TRUE,  7),
                    ('Sin Respuesta',         'sin_respuesta',         'No se obtuvo respuesta del lead',     '#6B7280', 'phone-missed', 'gray',    'inactive', FALSE, FALSE, 8),
                    ('Seguimiento Pendiente', 'seguimiento_pendiente', 'Requiere seguimiento posterior',      '#EC4899', 'clock',        'pink',    'active',   FALSE, FALSE, 9)
                ) AS s(name, code, description, color, icon, badge_style, category, is_initial, is_final, sort_order)
                ON CONFLICT (tenant_id, code) DO UPDATE SET
                    name        = EXCLUDED.name,
                    color       = EXCLUDED.color,
                    icon        = EXCLUDED.icon,
                    badge_style = EXCLUDED.badge_style,
                    category    = EXCLUDED.category,
                    is_initial  = EXCLUDED.is_initial,
                    is_final    = EXCLUDED.is_final,
                    sort_order  = EXCLUDED.sort_order,
                    description = EXCLUDED.description,
                    updated_at  = NOW();

                -- 2. Ensure unique constraint exists on transitions for upsert
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'lead_status_transitions_unique'
                ) THEN
                    ALTER TABLE lead_status_transitions
                        ADD CONSTRAINT lead_status_transitions_unique UNIQUE (tenant_id, from_status_code, to_status_code);
                END IF;

                -- 3. Upsert all valid transitions for every tenant
                INSERT INTO lead_status_transitions (tenant_id, from_status_code, to_status_code, label, icon, button_style, is_allowed, sort_order)
                SELECT t.id, tr.from_code, tr.to_code, tr.label, tr.icon, tr.btn_style, TRUE, tr.srt
                FROM tenants t
                CROSS JOIN (VALUES
                    -- From: nuevo
                    ('nuevo',                 'contactado',            'Contactar',              'phone',        'purple',  1),
                    ('nuevo',                 'sin_respuesta',         'Sin Respuesta',          'phone-missed', 'gray',    2),
                    ('nuevo',                 'cerrado_perdido',       'Descartar',              'x-circle',     'danger',  3),
                    -- From: contactado
                    ('contactado',            'calificado',            'Calificar',              'star',         'warning', 1),
                    ('contactado',            'llamada_agendada',      'Agendar Llamada',        'calendar',     'cyan',    2),
                    ('contactado',            'sin_respuesta',         'Sin Respuesta',          'phone-missed', 'gray',    3),
                    ('contactado',            'cerrado_perdido',       'Descartar',              'x-circle',     'danger',  4),
                    -- From: calificado
                    ('calificado',            'llamada_agendada',      'Agendar Llamada',        'calendar',     'cyan',    1),
                    ('calificado',            'negociacion',           'Negociar',               'handshake',    'orange',  2),
                    ('calificado',            'cerrado_perdido',       'Descartar',              'x-circle',     'danger',  3),
                    -- From: llamada_agendada
                    ('llamada_agendada',      'negociacion',           'Negociar',               'handshake',    'orange',  1),
                    ('llamada_agendada',      'calificado',            'Recalificar',            'star',         'warning', 2),
                    ('llamada_agendada',      'sin_respuesta',         'Sin Respuesta',          'phone-missed', 'gray',    3),
                    ('llamada_agendada',      'seguimiento_pendiente', 'Seguimiento Pendiente',  'clock',        'pink',    4),
                    ('llamada_agendada',      'cerrado_perdido',       'Descartar',              'x-circle',     'danger',  5),
                    -- From: negociacion
                    ('negociacion',           'cerrado_ganado',        'Cerrar Ganado',          'check-circle', 'success', 1),
                    ('negociacion',           'cerrado_perdido',       'Cerrar Perdido',         'x-circle',     'danger',  2),
                    ('negociacion',           'seguimiento_pendiente', 'Seguimiento Pendiente',  'clock',        'pink',    3),
                    -- From: sin_respuesta
                    ('sin_respuesta',         'contactado',            'Reintentar Contacto',    'phone',        'purple',  1),
                    ('sin_respuesta',         'seguimiento_pendiente', 'Seguimiento Pendiente',  'clock',        'pink',    2),
                    ('sin_respuesta',         'cerrado_perdido',       'Descartar',              'x-circle',     'danger',  3),
                    -- From: seguimiento_pendiente
                    ('seguimiento_pendiente', 'contactado',            'Contactar',              'phone',        'purple',  1),
                    ('seguimiento_pendiente', 'llamada_agendada',      'Agendar Llamada',        'calendar',     'cyan',    2),
                    ('seguimiento_pendiente', 'negociacion',           'Negociar',               'handshake',    'orange',  3),
                    ('seguimiento_pendiente', 'cerrado_perdido',       'Descartar',              'x-circle',     'danger',  4),
                    -- From: cerrado_perdido (reactivation)
                    ('cerrado_perdido',       'nuevo',                 'Reactivar',              'refresh-cw',   'info',    1),
                    -- From: cerrado_ganado (post-sale follow-up)
                    ('cerrado_ganado',        'seguimiento_pendiente', 'Seguimiento Post-Venta', 'clock',        'pink',    1)
                ) AS tr(from_code, to_code, label, icon, btn_style, srt)
                ON CONFLICT ON CONSTRAINT lead_status_transitions_unique DO UPDATE SET
                    label        = EXCLUDED.label,
                    icon         = EXCLUDED.icon,
                    button_style = EXCLUDED.button_style,
                    is_allowed   = TRUE,
                    sort_order   = EXCLUDED.sort_order;

                RAISE NOTICE 'Parche 24: Full 9-status pipeline with transitions loaded (DEV-32)';
            EXCEPTION WHEN OTHERS THEN
                RAISE NOTICE 'Parche 24: Error: %', SQLERRM;
            END $$;
            """,

            # Parche 25.5: AI Agent Config columns on tenants (DEV-36)
            """
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tenants' AND column_name='ai_system_prompt') THEN
                    ALTER TABLE tenants ADD COLUMN ai_system_prompt TEXT;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tenants' AND column_name='ai_agent_name') THEN
                    ALTER TABLE tenants ADD COLUMN ai_agent_name TEXT;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tenants' AND column_name='ai_tone') THEN
                    ALTER TABLE tenants ADD COLUMN ai_tone TEXT DEFAULT 'profesional_argentino';
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tenants' AND column_name='ai_services_description') THEN
                    ALTER TABLE tenants ADD COLUMN ai_services_description TEXT;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tenants' AND column_name='ai_qualification_questions') THEN
                    ALTER TABLE tenants ADD COLUMN ai_qualification_questions JSONB DEFAULT '[]';
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tenants' AND column_name='ai_objection_responses') THEN
                    ALTER TABLE tenants ADD COLUMN ai_objection_responses JSONB DEFAULT '[]';
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tenants' AND column_name='ai_company_description') THEN
                    ALTER TABLE tenants ADD COLUMN ai_company_description TEXT;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tenants' AND column_name='business_hours') THEN
                    ALTER TABLE tenants ADD COLUMN business_hours JSONB DEFAULT '{"weekdays": "09:00-18:00", "saturday": "09:00-13:00", "sunday": "closed"}';
                END IF;
                RAISE NOTICE 'Parche 25.5: AI Agent Config columns added to tenants (DEV-36)';
            EXCEPTION WHEN OTHERS THEN
                RAISE NOTICE 'Parche 25.5: Error: %', SQLERRM;
            END $$;
            """,

            # Parche 25: meta_templates + automation_logs (DEV-31 HSM Templates)
            """
            DO $$ BEGIN
                -- meta_templates: HSM templates from Meta / local
                IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'meta_templates') THEN
                    CREATE TABLE meta_templates (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
                        meta_template_id VARCHAR(255) NOT NULL,
                        waba_id VARCHAR(255) NOT NULL DEFAULT 'pending',
                        name TEXT NOT NULL,
                        category TEXT NOT NULL,
                        language TEXT DEFAULT 'es',
                        status TEXT DEFAULT 'PENDING_APPROVAL',
                        components JSONB NOT NULL DEFAULT '[]',
                        example JSONB,
                        sent_count INTEGER DEFAULT 0,
                        delivered_count INTEGER DEFAULT 0,
                        read_count INTEGER DEFAULT 0,
                        replied_count INTEGER DEFAULT 0,
                        last_synced_at TIMESTAMP,
                        sync_status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT unique_meta_template_per_tenant UNIQUE (tenant_id, meta_template_id)
                    );
                    CREATE INDEX IF NOT EXISTS idx_meta_templates_tenant ON meta_templates(tenant_id);
                    CREATE INDEX IF NOT EXISTS idx_meta_templates_status ON meta_templates(tenant_id, status);
                    CREATE INDEX IF NOT EXISTS idx_meta_templates_category ON meta_templates(tenant_id, category);
                    RAISE NOTICE 'Parche 25: meta_templates table created (DEV-31)';
                END IF;

                -- automation_logs: ensure it has patient_id, target_id, meta, error_details columns
                IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'automation_logs') THEN
                    CREATE TABLE automation_logs (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
                        patient_id UUID,
                        trigger_type TEXT NOT NULL,
                        target_id TEXT,
                        status TEXT NOT NULL DEFAULT 'pending',
                        error_details TEXT,
                        meta JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE INDEX IF NOT EXISTS idx_automation_logs_tenant ON automation_logs(tenant_id);
                    CREATE INDEX IF NOT EXISTS idx_automation_logs_status ON automation_logs(tenant_id, status);
                    RAISE NOTICE 'Parche 25: automation_logs table created (DEV-31)';
                ELSE
                    -- Ensure columns exist for the send_hsm helper
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='automation_logs' AND column_name='patient_id') THEN
                        ALTER TABLE automation_logs ADD COLUMN patient_id UUID;
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='automation_logs' AND column_name='target_id') THEN
                        ALTER TABLE automation_logs ADD COLUMN target_id TEXT;
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='automation_logs' AND column_name='error_details') THEN
                        ALTER TABLE automation_logs ADD COLUMN error_details TEXT;
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='automation_logs' AND column_name='meta') THEN
                        ALTER TABLE automation_logs ADD COLUMN meta JSONB;
                    END IF;
                END IF;
            EXCEPTION WHEN others THEN
                RAISE NOTICE 'Parche 25: Error: %', SQLERRM;
            END $$;
            """,

            # Parche 26: Tenant Company Profile — business config fields (DEV-35)
            """
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tenants' AND column_name='logo_url') THEN
                    ALTER TABLE tenants ADD COLUMN logo_url TEXT;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tenants' AND column_name='contact_email') THEN
                    ALTER TABLE tenants ADD COLUMN contact_email TEXT;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tenants' AND column_name='contact_phone') THEN
                    ALTER TABLE tenants ADD COLUMN contact_phone TEXT;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tenants' AND column_name='whatsapp_number') THEN
                    ALTER TABLE tenants ADD COLUMN whatsapp_number TEXT;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tenants' AND column_name='timezone') THEN
                    ALTER TABLE tenants ADD COLUMN timezone TEXT DEFAULT 'America/Argentina/Buenos_Aires';
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tenants' AND column_name='currency') THEN
                    ALTER TABLE tenants ADD COLUMN currency VARCHAR(10) DEFAULT 'ARS';
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tenants' AND column_name='business_hours_start') THEN
                    ALTER TABLE tenants ADD COLUMN business_hours_start VARCHAR(5) DEFAULT '09:00';
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tenants' AND column_name='business_hours_end') THEN
                    ALTER TABLE tenants ADD COLUMN business_hours_end VARCHAR(5) DEFAULT '18:00';
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tenants' AND column_name='ai_agent_name') THEN
                    ALTER TABLE tenants ADD COLUMN ai_agent_name TEXT DEFAULT 'Asistente';
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tenants' AND column_name='ai_agent_active') THEN
                    ALTER TABLE tenants ADD COLUMN ai_agent_active BOOLEAN DEFAULT TRUE;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tenants' AND column_name='website') THEN
                    ALTER TABLE tenants ADD COLUMN website TEXT;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tenants' AND column_name='address') THEN
                    ALTER TABLE tenants ADD COLUMN address TEXT;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tenants' AND column_name='industry') THEN
                    ALTER TABLE tenants ADD COLUMN industry TEXT;
                END IF;
                RAISE NOTICE 'Parche 26: Tenant company profile columns added (DEV-35)';
            EXCEPTION WHEN OTHERS THEN
                RAISE NOTICE 'Parche 26: Error: %', SQLERRM;
            END $$;
            """,

            # Parche 27: Channel Bindings + Business Assets + chat_messages platform columns (Multi-Channel Routing)
            """
            DO $$ BEGIN
                -- channel_bindings table
                CREATE TABLE IF NOT EXISTS channel_bindings (
                    id SERIAL PRIMARY KEY,
                    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                    provider VARCHAR(50) NOT NULL,
                    channel_type VARCHAR(50) NOT NULL,
                    channel_id VARCHAR(255) NOT NULL,
                    label VARCHAR(255),
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    CONSTRAINT channel_bindings_provider_channel_unique UNIQUE (provider, channel_id)
                );
                CREATE INDEX IF NOT EXISTS idx_channel_bindings_tenant ON channel_bindings (tenant_id, is_active);
                CREATE INDEX IF NOT EXISTS idx_channel_bindings_lookup ON channel_bindings (provider, channel_id, is_active);

                -- business_assets table
                CREATE TABLE IF NOT EXISTS business_assets (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                    asset_type VARCHAR(50) NOT NULL,
                    external_id VARCHAR(255) NOT NULL,
                    name VARCHAR(255),
                    metadata JSONB DEFAULT '{}',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    CONSTRAINT business_assets_tenant_type_extid_unique UNIQUE (tenant_id, asset_type, external_id)
                );
                CREATE INDEX IF NOT EXISTS idx_business_assets_tenant ON business_assets (tenant_id, is_active);

                -- chat_messages: platform columns
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='chat_messages' AND column_name='platform') THEN
                    ALTER TABLE chat_messages ADD COLUMN platform VARCHAR(20);
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='chat_messages' AND column_name='platform_message_id') THEN
                    ALTER TABLE chat_messages ADD COLUMN platform_message_id TEXT;
                END IF;
                CREATE INDEX IF NOT EXISTS idx_chat_messages_platform ON chat_messages (platform);

                RAISE NOTICE 'Parche 27: Channel bindings, business assets, and chat_messages platform columns added';
            EXCEPTION WHEN OTHERS THEN
                RAISE NOTICE 'Parche 27: Error: %', SQLERRM;
            END $$;
            """,

            # Parche 28: Multi-Channel Lead Identity — instagram_psid, facebook_psid, channel_source on leads + chat_messages
            """
            DO $$ BEGIN
                -- leads: instagram_psid
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='leads' AND column_name='instagram_psid') THEN
                    ALTER TABLE leads ADD COLUMN instagram_psid VARCHAR(100);
                END IF;
                -- leads: facebook_psid
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='leads' AND column_name='facebook_psid') THEN
                    ALTER TABLE leads ADD COLUMN facebook_psid VARCHAR(100);
                END IF;
                -- leads: channel_source (first contact channel)
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='leads' AND column_name='channel_source') THEN
                    ALTER TABLE leads ADD COLUMN channel_source VARCHAR(20) DEFAULT 'whatsapp';
                END IF;

                -- Indexes for PSID lookups
                CREATE INDEX IF NOT EXISTS idx_leads_instagram_psid ON leads (tenant_id, instagram_psid) WHERE instagram_psid IS NOT NULL;
                CREATE INDEX IF NOT EXISTS idx_leads_facebook_psid ON leads (tenant_id, facebook_psid) WHERE facebook_psid IS NOT NULL;

                -- chat_messages: channel_source column (redundant with platform but explicit for queries)
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='chat_messages' AND column_name='channel_source') THEN
                    ALTER TABLE chat_messages ADD COLUMN channel_source VARCHAR(20) DEFAULT 'whatsapp';
                END IF;
                -- chat_messages: external_user_id (phone or PSID, for unified queries)
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='chat_messages' AND column_name='external_user_id') THEN
                    ALTER TABLE chat_messages ADD COLUMN external_user_id VARCHAR(100);
                END IF;
                CREATE INDEX IF NOT EXISTS idx_chat_messages_channel_user ON chat_messages (tenant_id, channel_source, external_user_id);

                RAISE NOTICE 'Parche 28: Multi-channel lead identity columns added';
            EXCEPTION WHEN OTHERS THEN
                RAISE NOTICE 'Parche 28: Error: %', SQLERRM;
            END $$;
            """,

            # Parche 29: Message delivery status tracking (Meta messaging webhooks)
            """
            DO $$ BEGIN
                -- chat_messages: delivery status columns
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='chat_messages' AND column_name='delivery_status') THEN
                    ALTER TABLE chat_messages ADD COLUMN delivery_status VARCHAR(20);
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='chat_messages' AND column_name='delivery_timestamp') THEN
                    ALTER TABLE chat_messages ADD COLUMN delivery_timestamp TIMESTAMPTZ;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='chat_messages' AND column_name='updated_at') THEN
                    ALTER TABLE chat_messages ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();
                END IF;
                CREATE INDEX IF NOT EXISTS idx_chat_messages_delivery ON chat_messages (delivery_status) WHERE delivery_status IS NOT NULL;

                -- message_status_log table for tracking delivery/read receipts
                CREATE TABLE IF NOT EXISTS message_status_log (
                    id SERIAL PRIMARY KEY,
                    provider_message_id TEXT NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    recipient VARCHAR(100),
                    timestamp TIMESTAMPTZ,
                    errors JSONB,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    CONSTRAINT message_status_log_unique UNIQUE (provider_message_id, status)
                );
                CREATE INDEX IF NOT EXISTS idx_message_status_log_msg ON message_status_log (provider_message_id);

                RAISE NOTICE 'Parche 29: Message delivery status tracking columns added';
            EXCEPTION WHEN OTHERS THEN
                RAISE NOTICE 'Parche 29: Error: %', SQLERRM;
            END $$;
            """,

            # Parche 30: Activity Events — Team Activity Panel (DEV-39)
            """
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'activity_events') THEN
                    CREATE TABLE activity_events (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                        actor_id UUID NOT NULL REFERENCES users(id),
                        event_type VARCHAR(50) NOT NULL,
                        entity_type VARCHAR(30) NOT NULL,
                        entity_id VARCHAR(100) NOT NULL,
                        metadata JSONB DEFAULT '{}',
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    CREATE INDEX idx_activity_events_tenant_created ON activity_events (tenant_id, created_at DESC);
                    CREATE INDEX idx_activity_events_actor ON activity_events (actor_id, created_at DESC);
                    CREATE INDEX idx_activity_events_entity ON activity_events (entity_type, entity_id);
                    RAISE NOTICE 'Parche 30: activity_events table created (DEV-39)';
                END IF;
            EXCEPTION WHEN OTHERS THEN
                RAISE NOTICE 'Parche 30: Error: %', SQLERRM;
            END $$;
            """,

            # Parche 31: SLA Rules (DEV-42)
            """
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sla_rules') THEN
                    CREATE TABLE sla_rules (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                        name TEXT NOT NULL,
                        description TEXT,
                        trigger_type VARCHAR(50) NOT NULL,
                        threshold_minutes INTEGER NOT NULL,
                        applies_to_statuses TEXT[],
                        applies_to_roles TEXT[],
                        escalate_to_ceo BOOLEAN DEFAULT true,
                        escalate_after_minutes INTEGER DEFAULT 30,
                        is_active BOOLEAN DEFAULT true,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    );
                    CREATE INDEX idx_sla_rules_tenant_active ON sla_rules (tenant_id, is_active);
                    RAISE NOTICE 'Parche 31: sla_rules table created (DEV-42)';
                END IF;
            EXCEPTION WHEN OTHERS THEN
                RAISE NOTICE 'Parche 31: Error: %', SQLERRM;
            END $$;
            """,

            # Parche 32: Note Mentions (DEV-43)
            """
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'note_mentions') THEN
                    CREATE TABLE note_mentions (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        note_id UUID NOT NULL REFERENCES lead_notes(id) ON DELETE CASCADE,
                        mentioned_user_id UUID NOT NULL REFERENCES users(id),
                        tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    );
                    CREATE INDEX idx_note_mentions_user ON note_mentions (mentioned_user_id, created_at DESC);
                    CREATE INDEX idx_note_mentions_note ON note_mentions (note_id);
                    RAISE NOTICE 'Parche 32: note_mentions table created (DEV-43)';
                END IF;
            EXCEPTION WHEN OTHERS THEN
                RAISE NOTICE 'Parche 32: Error: %', SQLERRM;
            END $$;
            """
        ]

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for i, patch in enumerate(patches):
                    try:
                        await conn.execute(patch)
                    except Exception as e:
                        logger.error(f"❌ Evolution Patch {i+1} failed: {e}")
                        raise e

    async def disconnect(self):
        if self.pool:
            await self.pool.close()

    async def try_insert_inbound(self, provider: str, provider_message_id: str, event_id: str, from_number: str, payload: dict, correlation_id: str) -> bool:
        """Try to insert inbound message. Returns True if inserted, False if duplicate."""
        query = "INSERT INTO inbound_messages (provider, provider_message_id, event_id, from_number, payload, status, correlation_id) VALUES ($1, $2, $3, $4, $5, 'received', $6) ON CONFLICT (provider, provider_message_id) DO NOTHING RETURNING id"
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(query, provider, provider_message_id, event_id, from_number, json.dumps(payload), correlation_id)
            return result is not None

    async def mark_inbound_processing(self, provider: str, provider_message_id: str):
        query = "UPDATE inbound_messages SET status = 'processing' WHERE provider = $1 AND provider_message_id = $2"
        async with self.pool.acquire() as conn:
            await conn.execute(query, provider, provider_message_id)

    async def mark_inbound_done(self, provider: str, provider_message_id: str):
        query = "UPDATE inbound_messages SET status = 'done', processed_at = NOW() WHERE provider = $1 AND provider_message_id = $2"
        async with self.pool.acquire() as conn:
            await conn.execute(query, provider, provider_message_id)

    async def mark_inbound_failed(self, provider: str, provider_message_id: str, error: str):
        query = "UPDATE inbound_messages SET status = 'failed', processed_at = NOW(), error = $3 WHERE provider = $1 AND provider_message_id = $2"
        async with self.pool.acquire() as conn:
            await conn.execute(query, provider, provider_message_id, error)

    async def append_chat_message(
        self, from_number: str, role: str, content: str, correlation_id: str, tenant_id: int = 1,
        platform: Optional[str] = None, platform_message_id: Optional[str] = None,
        channel_source: Optional[str] = None, external_user_id: Optional[str] = None
    ):
        """Append a chat message and trigger notifications for leads.

        Multi-channel support:
          - platform: 'whatsapp' | 'instagram' | 'facebook'
          - platform_message_id: provider-level message ID for dedup
          - channel_source: same as platform (explicit channel tag)
          - external_user_id: phone number (whatsapp) or PSID (ig/fb)
        """
        # Derive defaults for backward-compat: if caller didn't pass channel info, assume whatsapp
        _platform = platform or channel_source or "whatsapp"
        _channel_source = channel_source or platform or "whatsapp"
        _external_user_id = external_user_id or from_number

        async with self.pool.acquire() as conn:
            # 1. Insert message (with multi-channel columns)
            query = """INSERT INTO chat_messages
                (from_number, role, content, correlation_id, tenant_id,
                 platform, platform_message_id, channel_source, external_user_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)"""
            await conn.execute(
                query, from_number, role, content, correlation_id, tenant_id,
                _platform, platform_message_id, _channel_source, _external_user_id
            )
            
            # 2. Trigger Notification if it's a message FROM the USER (lead)
            if role == "user":
                try:
                    # Get assigned seller and lead info
                    row = await conn.fetchrow("""
                        SELECT assigned_seller_id, first_name, last_name 
                        FROM chat_messages cm
                        LEFT JOIN leads l ON cm.from_number = l.phone_number AND cm.tenant_id = l.tenant_id
                        WHERE cm.from_number = $1 AND cm.tenant_id = $2
                        AND cm.assigned_seller_id IS NOT NULL
                        ORDER BY cm.created_at DESC LIMIT 1
                    """, from_number, tenant_id)
                    
                    if row:
                        from services.seller_notification_service import seller_notification_service, Notification
                        import datetime
                        timestamp = datetime.datetime.utcnow().timestamp()
                        lead_name = f"{row['first_name'] or ''} {row['last_name'] or ''}".strip() or from_number
                        
                        # Notification for Seller
                        notif_seller = Notification(
                            id=f"msg_{from_number}_{timestamp}",
                            tenant_id=tenant_id,
                            type="unanswered",
                            title="💬 Nuevo mensaje de Lead",
                            message=f"{lead_name}: {content[:50]}...",
                            priority="high",
                            recipient_id=str(row['assigned_seller_id']),
                            related_entity_type="conversation",
                            related_entity_id=from_number,
                            metadata={"phone": from_number, "preview": content[:100]}
                        )
                        
                        # Notification for CEO
                        ceo = await conn.fetchrow("SELECT id FROM users WHERE tenant_id = $1 AND role = 'ceo' AND status = 'active' LIMIT 1", tenant_id)
                        notifications = [notif_seller]
                        
                        if ceo and str(ceo['id']) != str(row['assigned_seller_id']):
                            notif_ceo = Notification(
                                id=f"msg_ceo_{from_number}_{timestamp}",
                                tenant_id=tenant_id,
                                type="unanswered",
                                title="📢 Actividad Lead (Global)",
                                message=f"{lead_name} envió un mensaje. Asignado a: (Seller ID: {row['assigned_seller_id']})",
                                priority="medium",
                                recipient_id=str(ceo['id']),
                                related_entity_type="conversation",
                                related_entity_id=from_number,
                                metadata={"phone": from_number, "seller_id": str(row['assigned_seller_id'])}
                            )
                            notifications.append(notif_ceo)
                            
                        await seller_notification_service.save_notifications(notifications)
                        await seller_notification_service.broadcast_notifications(notifications)
                except Exception as e:
                    logger.error(f"Error triggering message notification: {e}")

    async def ensure_lead_exists(
        self,
        tenant_id: int,
        phone_number: str,
        customer_name: Optional[str] = None,
        source: str = "whatsapp_inbound",
        referral: Optional[dict] = None,
        channel_source: Optional[str] = None,
        external_user_id: Optional[str] = None
    ):
        """
        Ensures a lead record exists (CRM Sales).
        customer_name: WhatsApp display name; split into first_name/last_name.
        Handles Meta Ads attribution if referral is present.

        Multi-channel support:
          - channel_source: 'whatsapp' | 'instagram' | 'facebook'
          - external_user_id: phone number (whatsapp) or PSID (instagram/facebook)
        For WhatsApp the lookup is by phone_number (backward-compat).
        For Instagram/Facebook the lookup is by PSID column.
        """
        _channel = channel_source or "whatsapp"
        _ext_id = external_user_id or phone_number

        parts = (customer_name or "").strip().split(None, 1)
        first_name = parts[0] if parts else "Lead"
        last_name = parts[1] if len(parts) > 1 else ""

        async with self.pool.acquire() as conn:
            # 1. Check for existing lead — lookup strategy depends on channel
            existing = None
            if _channel == "instagram":
                existing = await conn.fetchrow(
                    "SELECT id, first_name, last_name, lead_source FROM leads WHERE tenant_id = $1 AND instagram_psid = $2",
                    tenant_id, _ext_id
                )
            elif _channel == "facebook":
                existing = await conn.fetchrow(
                    "SELECT id, first_name, last_name, lead_source FROM leads WHERE tenant_id = $1 AND facebook_psid = $2",
                    tenant_id, _ext_id
                )

            # Fallback / WhatsApp: lookup by phone_number (also catches IG/FB leads that already have a phone)
            if not existing and phone_number:
                existing = await conn.fetchrow(
                    "SELECT id, first_name, last_name, lead_source FROM leads WHERE tenant_id = $1 AND phone_number = $2",
                    tenant_id, phone_number
                )

            # 2. Build attribution fields if referral present (Spec Multi-Attribution)
            attribution_data = {}
            if referral:
                ad_id = referral.get("ad_id")
                if ad_id:
                    attribution_data = {
                        "lead_source": "META_ADS",
                        "meta_ad_id": ad_id,
                        "meta_campaign_id": referral.get("campaign_id")
                    }

            # 3. Build channel-specific PSID fields
            psid_fields = {}
            if _channel == "instagram" and _ext_id:
                psid_fields["instagram_psid"] = _ext_id
            elif _channel == "facebook" and _ext_id:
                psid_fields["facebook_psid"] = _ext_id

            if existing:
                # Update existing lead
                update_fields = {
                    "first_name": first_name if first_name != "Lead" else existing["first_name"],
                    "last_name": last_name if last_name else existing["last_name"],
                    "updated_at": datetime.now()
                }
                if attribution_data:
                    update_fields.update(attribution_data)
                # Merge PSID fields (add IG/FB PSID to existing lead even if it was created via WhatsApp)
                if psid_fields:
                    update_fields.update(psid_fields)
                # Store channel_source if not already set
                update_fields["channel_source"] = _channel

                set_clauses = [f"{k} = ${i+1}" for i, k in enumerate(update_fields.keys())]
                query = f"UPDATE leads SET {', '.join(set_clauses)} WHERE id = ${len(update_fields)+1}"
                await conn.execute(query, *update_fields.values(), existing["id"])
                return {**dict(existing), **update_fields}

            # 4. Create new lead
            insert_fields = {
                "tenant_id": tenant_id,
                "phone_number": phone_number or "",
                "first_name": first_name,
                "last_name": last_name,
                "source": source,
                "lead_source": attribution_data.get("lead_source", "ORGANIC"),
                "channel_source": _channel
            }
            if attribution_data:
                insert_fields.update(attribution_data)
            if psid_fields:
                insert_fields.update(psid_fields)

            cols = ", ".join(insert_fields.keys())
            placeholders = ", ".join([f"${i+1}" for i in range(len(insert_fields))])
            query = f"INSERT INTO leads ({cols}) VALUES ({placeholders}) RETURNING id, tenant_id, phone_number, first_name, last_name, status, source, lead_source"
            return await conn.fetchrow(query, *insert_fields.values())

    async def get_chat_history(
        self, from_number: str, limit: int = 15, tenant_id: Optional[int] = None,
        channel_source: Optional[str] = None, external_user_id: Optional[str] = None
    ) -> List[dict]:
        """Fetch recent chat messages for a conversation.

        Multi-channel: when channel_source + external_user_id are provided,
        uses the indexed (tenant_id, channel_source, external_user_id) path.
        Falls back to from_number lookup for backward-compat.
        """
        _channel = channel_source or "whatsapp"
        _ext_id = external_user_id or from_number

        # Prefer channel+ext_id lookup when tenant is known (indexed path)
        if tenant_id is not None and (_channel != "whatsapp" or external_user_id):
            query = """SELECT role, content FROM chat_messages
                       WHERE tenant_id = $1 AND channel_source = $2 AND external_user_id = $3
                       ORDER BY created_at DESC LIMIT $4"""
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, tenant_id, _channel, _ext_id, limit)
                return [dict(row) for row in reversed(rows)]

        # Legacy path: lookup by from_number (WhatsApp default)
        if tenant_id is not None:
            query = "SELECT role, content FROM chat_messages WHERE from_number = $1 AND tenant_id = $2 ORDER BY created_at DESC LIMIT $3"
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, from_number, tenant_id, limit)
                return [dict(row) for row in reversed(rows)]
        query = "SELECT role, content FROM chat_messages WHERE from_number = $1 ORDER BY created_at DESC LIMIT $2"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, from_number, limit)
            return [dict(row) for row in reversed(rows)]

    async def fetch(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def fetchrow(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetchval(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)
    
    async def execute(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

db = Database()

# SQLAlchemy AsyncSession for routes that require it (like notifications)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

if POSTGRES_DSN:
    engine = create_async_engine(POSTGRES_DSN, echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

@asynccontextmanager
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
