import asyncpg
import os
import json
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any

POSTGRES_DSN = os.getenv("POSTGRES_DSN")

class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

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

            # Parche 8: Pipeline de Ventas (Opportunities, Transactions & Clients)
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
        query = "INSERT INTO inbound_messages (provider, provider_message_id, event_id, from_number, payload, status, correlation_id) VALUES ($1, $2, $3, $4, $5, 'received', $6) ON CONFLICT (provider, provider_message_id) DO NOTHING RETURNING id"
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(query, provider, provider_message_id, event_id, from_number, json.dumps(payload), correlation_id)
            return result is not None

    async def append_chat_message(self, from_number: str, role: str, content: str, correlation_id: str, tenant_id: int = 1):
        query = "INSERT INTO chat_messages (from_number, role, content, correlation_id, tenant_id) VALUES ($1, $2, $3, $4, $5)"
        async with self.pool.acquire() as conn:
            await conn.execute(query, from_number, role, content, correlation_id, tenant_id)

    async def ensure_lead_exists(self, tenant_id: int, phone_number: str, customer_name: Optional[str] = None, source: str = "whatsapp_inbound", referral: Optional[dict] = None):
        parts = (customer_name or "").strip().split(None, 1)
        fn = parts[0] if parts else "Lead"
        ln = parts[1] if len(parts) > 1 else ""
        async with self.pool.acquire() as conn:
            query = "INSERT INTO leads (tenant_id, phone_number, first_name, last_name, source) VALUES ($1, $2, $3, $4, $5) ON CONFLICT (tenant_id, phone_number) DO UPDATE SET first_name = EXCLUDED.first_name, last_name = EXCLUDED.last_name, updated_at = NOW() RETURNING id"
            return await conn.fetchrow(query, tenant_id, phone_number, fn, ln, source)

    async def get_chat_history(self, from_number: str, limit: int = 15, tenant_id: Optional[int] = None) -> List[dict]:
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
