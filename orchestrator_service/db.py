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

            # asyncpg no soporta el esquema 'postgresql+asyncpg', solo 'postgresql' o 'postgres'
            dsn = POSTGRES_DSN.replace("postgresql+asyncpg://", "postgresql://")
            
            try:
                self.pool = await asyncpg.create_pool(dsn, init=self._init_connection)
            except Exception as e:
                print(f"❌ ERROR: Failed to create database pool: {e}")
                return
            
            # Auto-Migration: Ejecutar dentalogic_schema.sql si las tablas no existen
            await self._run_auto_migrations()
    
    async def _run_auto_migrations(self):
        """
        Sistema de Auto-Migración (Maintenance Robot / Schema Surgeon).
        Se asegura de que la base de datos esté siempre actualizada y saludable.
        """
        import logging
        logger = logging.getLogger("db")
        
        try:
            # 1. Auditoría de Salud: ¿Existe la base mínima?
            async with self.pool.acquire() as conn:
                schema_exists = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'tenants'
                    )
                """)
            
            # 2. Aplicar Base (Foundation) si es un Fresh Install
            if not schema_exists:
                logger.warning("⚠️ Base de datos vacía, aplicando Foundation...")
                await self._apply_foundation(logger)
            
            # 3. Evolución Continua (Pipeline de Cirugía)
            # Aquí agregamos parches específicos que deben correr siempre de forma segura
            await self._run_evolution_pipeline(logger)
            
            logger.info("✅ Base de datos verificada y actualizada (Maintenance Robot OK)")
            
        except Exception as e:
            import traceback
            logger.error(f"❌ Error en Maintenance Robot: {e}")
            logger.error(traceback.format_exc())

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

        # Limpiar comentarios y separar sentencias respetando $$
        clean_lines = [line.split('--')[0].rstrip() for line in schema_sql.splitlines()]
        clean_sql = "\n".join(clean_lines)
        
        statements = []
        current_stmt = []
        in_dollar = False
        for line in clean_sql.splitlines():
            if "$$" in line:
                in_dollar = not in_dollar if line.count("$$") % 2 != 0 else in_dollar
            current_stmt.append(line)
            if not in_dollar and ";" in line:
                full = "\n".join(current_stmt).strip()
                if full: statements.append(full)
                current_stmt = []
        
        if current_stmt:
            leftover = "\n".join(current_stmt).strip()
            if leftover: statements.append(leftover)

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for i, stmt in enumerate(statements):
                    await conn.execute(stmt)
        logger.info(f"✅ Foundation aplicada ({len(statements)} sentencias)")

    async def _run_evolution_pipeline(self, logger):
        """
        Pipeline de Cirugía: Parches acumulativos e independientes.
        Agrega aquí bloques DO $$ que aseguren la evolución del esquema.
        """
        patches = [
            # Parche 1: Asegurar tabla 'users' y columna 'user_id' en 'professionals'
            """
            DO $$ 
            BEGIN 
                -- Asegurar columna user_id en professionals
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='professionals' AND column_name='user_id') THEN
                    ALTER TABLE professionals ADD COLUMN user_id UUID REFERENCES users(id) ON DELETE SET NULL;
                END IF;
            END $$;
            """,
            # Parche 2: Auto-activación del primer CEO (Protocolo Omega Prime)
            """
            DO $$ 
            BEGIN 
                -- Solo activamos un CEO pendiente si NO hay ningún CEO activo
                IF NOT EXISTS (SELECT 1 FROM users WHERE role = 'ceo' AND status = 'active') THEN
                    UPDATE users SET status = 'active' 
                    WHERE role = 'ceo' AND status = 'pending';
                    
                    -- Aseguramos que su perfil profesional también esté activo (si existe)
                    UPDATE professionals SET is_active = TRUE 
                    WHERE email IN (SELECT email FROM users WHERE role = 'ceo' AND status = 'active');
                END IF;
            END $$;
            """,
            # Agrega más parches aquí en el futuro...
            # Parche 3: Permitir DNI y Apellido nulos para 'guests' (Chat Users)
            """
            DO $$ 
            BEGIN 
                -- Hacer dni nullable
                ALTER TABLE patients ALTER COLUMN dni DROP NOT NULL;
                
                -- Hacer last_name nullable
                ALTER TABLE patients ALTER COLUMN last_name DROP NOT NULL;
                
                -- El constraint de unique dni debe ignorar nulos (Postgres lo hace por defecto, pero revisamos index)
            EXCEPTION
                WHEN others THEN null; -- Ignorar si ya se aplicó o falla
            END $$;
            """,
            # Parche 4: Asegurar constraint unique (tenant_id, phone_number) en patients
            """
            DO $$ 
            BEGIN 
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'patients_tenant_id_phone_number_key'
                ) THEN
                    ALTER TABLE patients ADD CONSTRAINT patients_tenant_id_phone_number_key UNIQUE (tenant_id, phone_number);
                END IF;
            END $$;
            """,
            # Parche 5: Agregar urgencia a la tabla patients para tracking de leads
            """
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='patients' AND column_name='urgency_level') THEN
                    ALTER TABLE patients ADD COLUMN urgency_level VARCHAR(20) DEFAULT 'normal';
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='patients' AND column_name='urgency_reason') THEN
                    ALTER TABLE patients ADD COLUMN urgency_reason TEXT;
                END IF;
            END $$;
            """,
            # Parche 37: Add page_id to meta_tokens
            """
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='meta_tokens' AND column_name='page_id') THEN
                    ALTER TABLE meta_tokens ADD COLUMN page_id VARCHAR(255);
                    CREATE INDEX IF NOT EXISTS idx_meta_tokens_page_id ON meta_tokens(page_id);
                END IF;
            END $$;
            """,
            # Parche 38: Columnas de Atribución Extendida para Meta Ads
            """
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='leads' AND column_name='meta_adset_id') THEN
                    ALTER TABLE leads ADD COLUMN meta_adset_id VARCHAR(255);
                END IF;

                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='leads' AND column_name='meta_campaign_name') THEN
                    ALTER TABLE leads ADD COLUMN meta_campaign_name TEXT;
                END IF;

                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='leads' AND column_name='meta_adset_name') THEN
                    ALTER TABLE leads ADD COLUMN meta_adset_name TEXT;
                END IF;

                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='leads' AND column_name='meta_ad_name') THEN
                    ALTER TABLE leads ADD COLUMN meta_ad_name TEXT;
                END IF;
            END $$;
            """,
            # Parche 6: Evolucionar treatment_plan a JSONB en clinical_records
            """
            DO $$ 
            BEGIN 
                -- Si la columna existe y es de tipo text/varchar, la convertimos a JSONB
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='clinical_records' AND column_name='treatment_plan' 
                    AND data_type IN ('text', 'character varying')
                ) THEN
                    ALTER TABLE clinical_records ALTER COLUMN treatment_plan TYPE JSONB USING treatment_plan::jsonb;
                END IF;
                
                -- Si no existe, la creamos
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='clinical_records' AND column_name='treatment_plan') THEN
                    ALTER TABLE clinical_records ADD COLUMN treatment_plan JSONB DEFAULT '{}';
                END IF;
            END $$;
            """,
            # Parche 7: Asegurar nombres en tabla users para gestión unificada
            """
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='first_name') THEN
                    ALTER TABLE users ADD COLUMN first_name VARCHAR(100);
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='last_name') THEN
                    ALTER TABLE users ADD COLUMN last_name VARCHAR(100);
                END IF;
            END $$;
            
            -- Copiar datos existentes de professionals a users (opcional pero recomendado)
            UPDATE users u
            SET first_name = p.first_name, last_name = p.last_name
            FROM professionals p
            WHERE u.id = p.user_id AND u.first_name IS NULL;
            """,
            # Parche 8: Agregar google_calendar_id a la tabla de profesionales
            """
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='professionals' AND column_name='google_calendar_id') THEN
                    ALTER TABLE professionals ADD COLUMN google_calendar_id VARCHAR(255);
                END IF;
            END $$;
            """,
            # Parche 9: Agregar working_hours a la tabla profesionales
            """
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='professionals' AND column_name='working_hours') THEN
                    ALTER TABLE professionals ADD COLUMN working_hours JSONB DEFAULT '{}';
                END IF;
            END $$;
            """,
            # Parche 10: Inicializar working_hours para profesionales existentes
            """
            DO $$ 
            BEGIN 
                UPDATE professionals 
                SET working_hours = '{
                    "monday": {"enabled": true, "slots": [{"start": "09:00", "end": "18:00"}]},
                    "tuesday": {"enabled": true, "slots": [{"start": "09:00", "end": "18:00"}]},
                    "wednesday": {"enabled": true, "slots": [{"start": "09:00", "end": "18:00"}]},
                    "thursday": {"enabled": true, "slots": [{"start": "09:00", "end": "18:00"}]},
                    "friday": {"enabled": true, "slots": [{"start": "09:00", "end": "18:00"}]},
                    "saturday": {"enabled": true, "slots": [{"start": "09:00", "end": "18:00"}]},
                    "sunday": {"enabled": false, "slots": []}
                }'::jsonb
                WHERE working_hours = '{}'::jsonb OR working_hours IS NULL;
            END $$;
            """,
            # Parche 11: Columna config (JSONB) en tenants para calendar_provider y demás opciones
            """
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tenants' AND column_name='config') THEN
                    ALTER TABLE tenants ADD COLUMN config JSONB DEFAULT '{}';
                END IF;
                -- Asegurar que tenants existentes tengan calendar_provider por defecto
                UPDATE tenants SET config = jsonb_set(COALESCE(config, '{}'), '{calendar_provider}', '"local"')
                WHERE config IS NULL OR config->>'calendar_provider' IS NULL;
            END $$;
            """,
            # Parche 12: tenant_id en professionals (idempotente, no rompe datos existentes)
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'professionals' AND column_name = 'tenant_id') THEN
                    ALTER TABLE professionals ADD COLUMN tenant_id INTEGER DEFAULT 1;
                    UPDATE professionals SET tenant_id = 1 WHERE tenant_id IS NULL;
                    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'tenants') THEN
                        ALTER TABLE professionals ADD CONSTRAINT fk_professionals_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;
                    END IF;
                END IF;
            END $$;
            CREATE INDEX IF NOT EXISTS idx_professionals_tenant ON professionals(tenant_id);
            """,
            # Parche 12b: registration_id en professionals (matrícula; BD puede tener license_number)
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'professionals' AND column_name = 'registration_id') THEN
                    ALTER TABLE professionals ADD COLUMN registration_id VARCHAR(50);
                    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'professionals' AND column_name = 'license_number') THEN
                        UPDATE professionals SET registration_id = license_number WHERE license_number IS NOT NULL;
                    END IF;
                END IF;
            END $$;
            """,
            # Parche 12c: updated_at en professionals (algunos esquemas antiguos no lo tienen)
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'professionals' AND column_name = 'updated_at') THEN
                    ALTER TABLE professionals ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();
                    UPDATE professionals SET updated_at = NOW() WHERE updated_at IS NULL;
                END IF;
            END $$;
            """,
            # Parche 12d: phone_number en professionals (esquemas antiguos pueden no tenerla)
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'professionals' AND column_name = 'phone_number') THEN
                    ALTER TABLE professionals ADD COLUMN phone_number VARCHAR(20);
                END IF;
            END $$;
            """,
            # Parche 12e: specialty en professionals (esquemas antiguos pueden no tenerla)
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'professionals' AND column_name = 'specialty') THEN
                    ALTER TABLE professionals ADD COLUMN specialty VARCHAR(100);
                END IF;
            END $$;
            """,
            # Parche 13: tenant_id, source y google_calendar_event_id en appointments (idempotente)
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'appointments' AND column_name = 'tenant_id') THEN
                    ALTER TABLE appointments ADD COLUMN tenant_id INTEGER DEFAULT 1;
                    UPDATE appointments SET tenant_id = 1 WHERE tenant_id IS NULL;
                    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'tenants') THEN
                        ALTER TABLE appointments ADD CONSTRAINT fk_appointments_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;
                    END IF;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'appointments' AND column_name = 'source') THEN
                    ALTER TABLE appointments ADD COLUMN source VARCHAR(20) DEFAULT 'ai';
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'appointments' AND column_name = 'google_calendar_event_id') THEN
                    ALTER TABLE appointments ADD COLUMN google_calendar_event_id VARCHAR(255);
                END IF;
            END $$;
            CREATE INDEX IF NOT EXISTS idx_appointments_tenant ON appointments(tenant_id);
            CREATE INDEX IF NOT EXISTS idx_appointments_source ON appointments(source);
            """,
            # Parche 14: tenant_id en treatment_types (idempotente)
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'treatment_types' AND column_name = 'tenant_id') THEN
                    ALTER TABLE treatment_types ADD COLUMN tenant_id INTEGER DEFAULT 1;
                    UPDATE treatment_types SET tenant_id = 1 WHERE tenant_id IS NULL;
                    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'tenants') THEN
                        ALTER TABLE treatment_types ADD CONSTRAINT fk_treatment_types_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;
                    END IF;
                END IF;
            END $$;
            CREATE INDEX IF NOT EXISTS idx_treatment_types_tenant ON treatment_types(tenant_id);
            """,
            # Parche 15: tenant_id en chat_messages (conversaciones por clínica, buffer/override independientes)
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'chat_messages' AND column_name = 'tenant_id') THEN
                    ALTER TABLE chat_messages ADD COLUMN tenant_id INTEGER DEFAULT 1;
                    UPDATE chat_messages SET tenant_id = 1 WHERE tenant_id IS NULL;
                    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'tenants') THEN
                        ALTER TABLE chat_messages ADD CONSTRAINT fk_chat_messages_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;
                    END IF;
                END IF;
            END $$;
            CREATE INDEX IF NOT EXISTS idx_chat_messages_tenant_id ON chat_messages(tenant_id);
            CREATE INDEX IF NOT EXISTS idx_chat_messages_tenant_from_created ON chat_messages(tenant_id, from_number, created_at DESC);
            """,
            # Parche 16: Crear tabla leads (núcleo CRM agnóstico)
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'leads'
                ) THEN
                    CREATE TABLE leads (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                        first_name TEXT,
                        last_name TEXT,
                        phone_number TEXT NOT NULL,
                        email TEXT,
                        status TEXT DEFAULT 'new',
                        lead_score TEXT,
                        source TEXT,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    );
                END IF;

                -- Índice crítico para performance de WhatsApp y soberanía (tenant_id + phone_number)
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE c.relkind = 'i'
                      AND c.relname = 'idx_leads_tenant_phone'
                      AND n.nspname = 'public'
                ) THEN
                    CREATE INDEX idx_leads_tenant_phone ON leads(tenant_id, phone_number);
                END IF;
            END $$;
            """
            ,
            # Parche 16: Crear tabla leads, whatsapp_connections, templates, campaigns (CRM Sales Core)
            """
            DO $$
            BEGIN
                -- 1. leads (Sovereign replacement for patients)
                IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'leads') THEN
                    CREATE TABLE leads (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                        phone_number TEXT NOT NULL,
                        first_name TEXT,
                        last_name TEXT,
                        email TEXT,
                        status TEXT DEFAULT 'new', -- new, contacted, interested, negotiation, closed_won, closed_lost
                        lead_score TEXT,
                        source TEXT, -- meta_ads, website, referral
                        assigned_seller_id UUID REFERENCES users(id),
                        tags JSONB DEFAULT '[]',
                        meta_lead_id TEXT,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW(),
                        CONSTRAINT leads_tenant_phone_unique UNIQUE (tenant_id, phone_number)
                    );
                    CREATE INDEX idx_leads_tenant_phone ON leads(tenant_id, phone_number);
                    CREATE INDEX idx_leads_seller ON leads(tenant_id, assigned_seller_id);
                END IF;

                -- 2. whatsapp_connections (Meta API per tenant/seller)
                IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'whatsapp_connections') THEN
                    CREATE TABLE whatsapp_connections (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                        seller_id UUID REFERENCES users(id),
                        phonenumber_id TEXT NOT NULL,
                        waba_id TEXT NOT NULL,
                        access_token_vault_id TEXT NOT NULL,
                        status TEXT DEFAULT 'active',
                        friendly_name TEXT,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    );
                    CREATE INDEX idx_wa_conn_tenant ON whatsapp_connections(tenant_id);
                END IF;

                -- 3. templates (Synced from Meta)
                IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'templates') THEN
                    CREATE TABLE templates (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                        meta_template_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        language TEXT DEFAULT 'es',
                        category TEXT,
                        components JSONB NOT NULL,
                        status TEXT,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW(),
                        CONSTRAINT templates_tenant_meta_id_unique UNIQUE (tenant_id, meta_template_id)
                    );
                    CREATE INDEX idx_templates_tenant ON templates(tenant_id);
                END IF;

                -- 4. campaigns (Mass sending)
                IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'campaigns') THEN
                    CREATE TABLE campaigns (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                        name TEXT NOT NULL,
                        template_id UUID REFERENCES templates(id),
                        target_segment JSONB,
                        status TEXT DEFAULT 'draft',
                        stats JSONB DEFAULT '{}',
                        scheduled_at TIMESTAMPTZ,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    );
                    CREATE INDEX idx_campaigns_tenant ON campaigns(tenant_id);
                END IF;
            END $$;
            """,
            # Parche 17: Agregar columna niche_type a tenants
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tenants' AND column_name='niche_type') THEN
                    ALTER TABLE tenants ADD COLUMN niche_type TEXT DEFAULT 'crm_sales';
                END IF;
            END $$;
            """,
            # Parche 18: Columna stage_id en leads (API CRM)
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='leads' AND column_name='stage_id') THEN
                    ALTER TABLE leads ADD COLUMN stage_id UUID;
                END IF;
            END $$;
            """,
            # Parche 19: Roles setter y closer para CRM (vendedores)
            """
            DO $$
            DECLARE
                cname text;
            BEGIN
                SELECT conname INTO cname FROM pg_constraint WHERE conrelid = 'public.users'::regclass AND contype = 'c' AND pg_get_constraintdef(oid) LIKE '%role%' LIMIT 1;
                IF cname IS NOT NULL THEN
                    EXECUTE format('ALTER TABLE public.users DROP CONSTRAINT IF EXISTS %I', cname);
                END IF;
                ALTER TABLE public.users ADD CONSTRAINT users_role_check CHECK (role IN ('ceo', 'professional', 'secretary', 'setter', 'closer'));
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """,
            # Parche 20: Tabla clients (CRM - página Clientes, análoga a patients en dental)
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'clients') THEN
                    CREATE TABLE clients (
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
                    CREATE INDEX idx_clients_tenant ON clients(tenant_id);
                    CREATE INDEX idx_clients_tenant_phone ON clients(tenant_id, phone_number);
                    CREATE INDEX idx_clients_status ON clients(tenant_id, status);
                END IF;
            END $$;
            """,
            # Parche 21: Columna assigned_seller_id en leads (si la tabla existía sin ella)
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'leads')
                   AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'leads' AND column_name = 'assigned_seller_id') THEN
                    ALTER TABLE leads ADD COLUMN assigned_seller_id UUID REFERENCES users(id);
                    CREATE INDEX IF NOT EXISTS idx_leads_seller ON leads(tenant_id, assigned_seller_id);
                END IF;
            END $$;
            """,
            # Parche 22: Columna meta_lead_id en leads (ID de Meta Lead Ads si la tabla existía sin ella)
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'leads')
                   AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'leads' AND column_name = 'meta_lead_id') THEN
                    ALTER TABLE leads ADD COLUMN meta_lead_id TEXT;
                END IF;
            END $$;
            """,
            # Parche 23: Columna tags en leads (JSONB para etiquetas; tabla creada sin ella)
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'leads')
                   AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'leads' AND column_name = 'tags') THEN
                    ALTER TABLE leads ADD COLUMN tags JSONB DEFAULT '[]';
                END IF;
            END $$;
            """,
            # Parche 24: Tabla seller_agenda_events (agenda por vendedor en CRM Sales)
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'seller_agenda_events') THEN
                    CREATE TABLE seller_agenda_events (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                        seller_id INTEGER NOT NULL REFERENCES professionals(id) ON DELETE CASCADE,
                        title TEXT NOT NULL,
                        start_datetime TIMESTAMPTZ NOT NULL,
                        end_datetime TIMESTAMPTZ NOT NULL,
                        lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
                        client_id INTEGER REFERENCES clients(id) ON DELETE SET NULL,
                        notes TEXT,
                        source TEXT DEFAULT 'manual',
                        status TEXT DEFAULT 'scheduled',
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    );
                    CREATE INDEX idx_seller_agenda_tenant ON seller_agenda_events(tenant_id);
                    CREATE INDEX idx_seller_agenda_seller ON seller_agenda_events(tenant_id, seller_id);
                    CREATE INDEX idx_seller_agenda_range ON seller_agenda_events(tenant_id, start_datetime, end_datetime);
                END IF;
            END $$;
            """,
            # Parche 25: Human override en leads (chat: intervención humana 24h, paridad con Clínicas)
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'leads')
                   AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'leads' AND column_name = 'human_handoff_requested') THEN
                    ALTER TABLE leads ADD COLUMN human_handoff_requested BOOLEAN DEFAULT FALSE;
                END IF;
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'leads')
                   AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'leads' AND column_name = 'human_override_until') THEN
                    ALTER TABLE leads ADD COLUMN human_override_until TIMESTAMPTZ DEFAULT NULL;
                END IF;
            END $$;
            """,
            # Parche 26: Campos de prospección Apify + estado de outreach en leads (CRM Sales)
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'leads')
                   AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'leads' AND column_name = 'apify_title') THEN
                    ALTER TABLE leads ADD COLUMN apify_title TEXT;
                END IF;
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'leads')
                   AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'leads' AND column_name = 'apify_category_name') THEN
                    ALTER TABLE leads ADD COLUMN apify_category_name TEXT;
                END IF;
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'leads')
                   AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'leads' AND column_name = 'apify_address') THEN
                    ALTER TABLE leads ADD COLUMN apify_address TEXT;
                END IF;
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'leads')
                   AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'leads' AND column_name = 'apify_city') THEN
                    ALTER TABLE leads ADD COLUMN apify_city TEXT;
                END IF;
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'leads')
                   AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'leads' AND column_name = 'apify_state') THEN
                    ALTER TABLE leads ADD COLUMN apify_state TEXT;
                END IF;
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'leads')
                   AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'leads' AND column_name = 'apify_country_code') THEN
                    ALTER TABLE leads ADD COLUMN apify_country_code TEXT;
                END IF;
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'leads')
                   AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'leads' AND column_name = 'apify_website') THEN
                    ALTER TABLE leads ADD COLUMN apify_website TEXT;
                END IF;
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'leads')
                   AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'leads' AND column_name = 'apify_place_id') THEN
                    ALTER TABLE leads ADD COLUMN apify_place_id TEXT;
                END IF;
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'leads')
                   AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'leads' AND column_name = 'apify_total_score') THEN
                    ALTER TABLE leads ADD COLUMN apify_total_score DOUBLE PRECISION;
                END IF;
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'leads')
                   AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'leads' AND column_name = 'apify_reviews_count') THEN
                    ALTER TABLE leads ADD COLUMN apify_reviews_count INTEGER;
                END IF;
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'leads')
                   AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'leads' AND column_name = 'apify_scraped_at') THEN
                    ALTER TABLE leads ADD COLUMN apify_scraped_at TIMESTAMPTZ;
                END IF;
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'leads')
                   AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'leads' AND column_name = 'apify_raw') THEN
                    ALTER TABLE leads ADD COLUMN apify_raw JSONB DEFAULT '{}'::jsonb;
                END IF;
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'leads')
                   AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'leads' AND column_name = 'prospecting_niche') THEN
                    ALTER TABLE leads ADD COLUMN prospecting_niche TEXT;
                END IF;
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'leads')
                   AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'leads' AND column_name = 'prospecting_location_query') THEN
                    ALTER TABLE leads ADD COLUMN prospecting_location_query TEXT;
                END IF;
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'leads')
                   AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'leads' AND column_name = 'outreach_message_sent') THEN
                    ALTER TABLE leads ADD COLUMN outreach_message_sent BOOLEAN DEFAULT FALSE;
                END IF;
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'leads')
                   AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'leads' AND column_name = 'outreach_send_requested') THEN
                    ALTER TABLE leads ADD COLUMN outreach_send_requested BOOLEAN DEFAULT FALSE;
                END IF;
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'leads')
                   AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'leads' AND column_name = 'outreach_last_requested_at') THEN
                    ALTER TABLE leads ADD COLUMN outreach_last_requested_at TIMESTAMPTZ;
                END IF;
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'leads')
                   AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'leads' AND column_name = 'outreach_last_sent_at') THEN
                    ALTER TABLE leads ADD COLUMN outreach_last_sent_at TIMESTAMPTZ;
                END IF;
            END $$;
            """,
            # Parche 27: Asegurar constraint unique (tenant_id, phone_number) en leads
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'leads_tenant_phone_unique'
                ) THEN
                    ALTER TABLE leads ADD CONSTRAINT leads_tenant_phone_unique UNIQUE (tenant_id, phone_number);
                END IF;
            END $$;
            """,
            # Parche 28: Columna social_links para IG, FB, LinkedIn
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'leads')
                   AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'leads' AND column_name = 'social_links') THEN
                    ALTER TABLE leads ADD COLUMN social_links JSONB DEFAULT '{}'::jsonb;
                END IF;
            END $$;
            """,
            # Parche 29: Prospecting Phase 2 columns
            """
            ALTER TABLE leads
            ADD COLUMN IF NOT EXISTS outreach_message_content TEXT,
            ADD COLUMN IF NOT EXISTS apify_rating FLOAT,
            ADD COLUMN IF NOT EXISTS apify_reviews INTEGER;
            """,
            # Parche 30 (Nexus Security v7.6): Tabla de auditoría system_events completa
            """
            DO $$
            BEGIN
                CREATE TABLE IF NOT EXISTS system_events (
                    id BIGSERIAL PRIMARY KEY,
                    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
                    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                    event_type VARCHAR(100) NOT NULL,
                    description TEXT,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    severity TEXT DEFAULT 'info',
                    message TEXT,
                    payload JSONB DEFAULT '{}',
                    occurred_at TIMESTAMPTZ DEFAULT NOW()
                );
                
                -- Si la tabla se creó previamente sin las nuevas columnas, agregarlas
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'system_events' AND column_name = 'severity') THEN
                    ALTER TABLE system_events ADD COLUMN severity TEXT DEFAULT 'info';
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'system_events' AND column_name = 'message') THEN
                    ALTER TABLE system_events ADD COLUMN message TEXT;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'system_events' AND column_name = 'payload') THEN
                    ALTER TABLE system_events ADD COLUMN payload JSONB DEFAULT '{}';
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'system_events' AND column_name = 'occurred_at') THEN
                    ALTER TABLE system_events ADD COLUMN occurred_at TIMESTAMPTZ DEFAULT NOW();
                END IF;

                CREATE INDEX IF NOT EXISTS idx_system_events_tenant ON system_events(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_system_events_user ON system_events(user_id);
                CREATE INDEX IF NOT EXISTS idx_system_events_type ON system_events(event_type);
                CREATE INDEX IF NOT EXISTS idx_system_events_created ON system_events(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_system_events_occurred ON system_events(occurred_at DESC);
                CREATE INDEX IF NOT EXISTS idx_system_events_severity ON system_events(severity);
            END $$;
            """,
            # Parche 31 (Nexus Security v7.6): Columna category en credentials para clasificación
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'credentials') THEN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                                   WHERE table_name = 'credentials' AND column_name = 'category') THEN
                        ALTER TABLE credentials ADD COLUMN category VARCHAR(50) DEFAULT 'general';
                    END IF;
                ELSE
                    -- Crear tabla credentials si no existe (multi-tenant)
                    CREATE TABLE IF NOT EXISTS credentials (
                        id BIGSERIAL PRIMARY KEY,
                        tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
                        name VARCHAR(255) NOT NULL,
                        value TEXT,
                        category VARCHAR(50) DEFAULT 'general',
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW(),
                        UNIQUE(tenant_id, name)
                    );
                    CREATE INDEX IF NOT EXISTS idx_credentials_tenant ON credentials(tenant_id);
                    CREATE INDEX IF NOT EXISTS idx_credentials_name ON credentials(name);
                END IF;
            END $$;
            """,
            # Parche 32 (Nexus Security v7.6): Tabla sellers para CRM (idempotente)
            """
            DO $$
            BEGIN
                -- Crear tabla sellers si no existe
                CREATE TABLE IF NOT EXISTS sellers (
                    id BIGSERIAL PRIMARY KEY,
                    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                    first_name VARCHAR(100),
                    last_name VARCHAR(100),
                    email VARCHAR(255),
                    phone VARCHAR(50),
                    role VARCHAR(50) DEFAULT 'setter',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                -- Agregar tenant_id si no existe (para tablas sellers ya creadas sin esta columna)
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                               WHERE table_name = 'sellers' AND column_name = 'tenant_id') THEN
                    ALTER TABLE sellers ADD COLUMN tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE;
                END IF;
                -- Agregar UNIQUE(user_id) si no existe
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.table_constraints tc
                    JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
                    WHERE tc.table_name = 'sellers' AND tc.constraint_type = 'UNIQUE' AND ccu.column_name = 'user_id'
                ) THEN
                    BEGIN
                        ALTER TABLE sellers ADD CONSTRAINT sellers_user_id_key UNIQUE (user_id);
                    EXCEPTION WHEN duplicate_object THEN NULL;
                    END;
                END IF;
                -- Índices (idempotentes con IF NOT EXISTS)
                CREATE INDEX IF NOT EXISTS idx_sellers_tenant ON sellers(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_sellers_user ON sellers(user_id);
            END $$;
            """,
            # Parche 33: Tabla de Auditoría (system_events) - Desactivado por consolidación en Parche 30
            """
            DO $$
            BEGIN
                -- Este parche se integró en Parche 30 de manera segura.
                -- Solo mantenemos el índice GIN de payload por compatibilidad
                CREATE INDEX IF NOT EXISTS idx_system_events_payload ON system_events USING gin(payload);
            END $$;
            """,
            # Parche 34: Tabla Credentials (Encriptada) - Fix para multi-tenancy y seguridad
            """
            DO $$
            BEGIN
                CREATE TABLE IF NOT EXISTS credentials (
                    id SERIAL PRIMARY KEY,
                    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    value TEXT NOT NULL,
                    category TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE (tenant_id, name)
                );
                CREATE INDEX IF NOT EXISTS idx_credentials_tenant ON credentials(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_credentials_name ON credentials(name);
                CREATE INDEX IF NOT EXISTS idx_credentials_category ON credentials(category);
            END $$;
            """
            # Parche 35: tenant_id en system_events para filtrado multi-tenant nativo (v7.7.1)
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                             WHERE table_name='system_events' AND column_name='tenant_id') THEN
                    ALTER TABLE system_events ADD COLUMN tenant_id INTEGER REFERENCES tenants(id);
                END IF;
                IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_system_events_tenant_v2') THEN
                    CREATE INDEX idx_system_events_tenant_v2 ON system_events(tenant_id);
                END IF;
            END $$;
            """,
            # Parche 36: Normalizar source='whatsapp_inbound' para consistencia core (v7.7.2)
            """
            UPDATE leads SET source = 'whatsapp_inbound' WHERE source = 'whatsapp';
            """,
            # Parche 37: Columna page_id en meta_tokens (Marketing Hub)
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'meta_tokens') THEN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                   WHERE table_name = 'meta_tokens' AND column_name = 'page_id') THEN
                        ALTER TABLE meta_tokens ADD COLUMN page_id VARCHAR(255);
                        CREATE INDEX IF NOT EXISTS idx_meta_tokens_page_id ON meta_tokens(page_id);
                    END IF;
                END IF;
            END $$;
            """,
            # Parche 38: Tablas de Marketing Hub (Sync Meta Ads)
            """
            DO $$
            BEGIN
                -- meta_ads_campaigns
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
                
                -- meta_ads_insights
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

                -- meta_templates
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
            END $$;
            """,
            # Parche 39: Automatización y Reglas (CRM Marketing)
            """
            DO $$
            BEGIN
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
            END $$;
            """,
            # Parche 40: Pipeline de Ventas (Opportunities & Transactions)
            """
            DO $$
            BEGIN
                CREATE TABLE IF NOT EXISTS opportunities (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                    lead_id UUID REFERENCES leads(id) NOT NULL,
                    seller_id UUID REFERENCES users(id),
                    name TEXT NOT NULL,
                    description TEXT,
                    value DECIMAL(12,2) NOT NULL,
                    currency TEXT DEFAULT 'USD',
                    stage TEXT NOT NULL,
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
                    attribution_source TEXT,
                    meta_campaign_id VARCHAR(255),
                    meta_ad_id VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            END $$;
            """,
            # Parche 41: Asegurar 'created_at' y 'updated_at' en credentials
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'credentials') THEN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'credentials' AND column_name = 'created_at') THEN
                        ALTER TABLE credentials ADD COLUMN created_at TIMESTAMPTZ DEFAULT NOW();
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'credentials' AND column_name = 'updated_at') THEN
                        ALTER TABLE credentials ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();
                    END IF;
                END IF;
            END $$;
            """
        ]

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for i, patch in enumerate(patches):
                    try:
                        await conn.execute(patch)
                    except Exception as e:
                        logger.error(f"❌ Error aplicando parche evolutivo {i+1}: {e}")
                        # En evolución, a veces es mejor fallar rápido para no corromper
                        raise e

    async def disconnect(self):
        if self.pool:
            await self.pool.close()

    async def try_insert_inbound(self, provider: str, provider_message_id: str, event_id: str, from_number: str, payload: dict, correlation_id: str) -> bool:
        """Try to insert inbound message. Returns True if inserted, False if duplicate."""
        query = """
        INSERT INTO inbound_messages (provider, provider_message_id, event_id, from_number, payload, status, correlation_id)
        VALUES ($1, $2, $3, $4, $5, 'received', $6)
        ON CONFLICT (provider, provider_message_id) DO NOTHING
        RETURNING id
        """
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

    async def append_chat_message(self, from_number: str, role: str, content: str, correlation_id: str, tenant_id: int = 1):
        query = "INSERT INTO chat_messages (from_number, role, content, correlation_id, tenant_id) VALUES ($1, $2, $3, $4, $5)"
        async with self.pool.acquire() as conn:
            await conn.execute(query, from_number, role, content, correlation_id, tenant_id)

    async def ensure_patient_exists(self, phone_number: str, tenant_id: int, first_name: str = 'Visitante', status: str = 'guest'):
        """
        Ensures a patient record exists for the given phone number.
        If it exists as a 'guest', it can be updated to 'active' or update its name.
        """
        query = """
        INSERT INTO patients (tenant_id, phone_number, first_name, status, created_at)
        VALUES ($1, $2, $3, $4, NOW())
        ON CONFLICT (tenant_id, phone_number) 
        DO UPDATE SET 
            first_name = CASE 
                WHEN patients.status = 'guest' 
                     OR patients.first_name IS NULL 
                     OR patients.first_name IN ('Visitante', 'Paciente', 'Visitante ', 'Paciente ')
                THEN EXCLUDED.first_name 
                ELSE patients.first_name 
            END,
            status = CASE WHEN patients.status = 'guest' AND EXCLUDED.status = 'active' THEN 'active' ELSE patients.status END,
            updated_at = NOW() 
        RETURNING id, status
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, tenant_id, phone_number, first_name, status)

    async def ensure_lead_exists(
        self,
        tenant_id: int,
        phone_number: str,
        customer_name: Optional[str] = None,
        source: str = "whatsapp_inbound",
        referral: Optional[dict] = None,
    ):
        """
        Ensures a lead record exists for this tenant + phone (CRM Sales).
        customer_name: WhatsApp display name; split into first_name/last_name.
        If lead exists, updates name when customer_name is provided.
        Returns the lead row (id, etc.).
        """
        parts = (customer_name or "").strip().split(None, 1)
        first_name = parts[0] if parts else None
        last_name = parts[1] if len(parts) > 1 else None
        
        async with self.pool.acquire() as conn:
            existing = await conn.fetchrow(
                "SELECT id, first_name, last_name, lead_source FROM leads WHERE tenant_id = $1 AND phone_number = $2",
                tenant_id,
                phone_number,
            )
            
            # Atribución Meta Ads Logic (Spec Meta Attribution)
            # Siempre intentamos actualizar la atribución si viene referral (Last Click)
            attribution_update = {}
            if referral:
                ad_id = referral.get("ad_id")
                if ad_id:
                    attribution_update = {
                        "lead_source": "META_ADS",
                        "meta_ad_id": ad_id,
                        "meta_ad_name": referral.get("ad_name"),
                        "meta_adset_id": referral.get("adset_id"),
                        "meta_adset_name": referral.get("adset_name"),
                        "meta_campaign_id": referral.get("campaign_id"),
                        "meta_campaign_name": referral.get("campaign_name"),
                        "meta_ad_headline": referral.get("headline"),
                        "meta_ad_body": referral.get("body"),
                        "updated_at": datetime.now()
                    }

            if existing:
                # Use dict casting to avoid Pyre indexing issues with Record
                existing_dict = dict(existing)
                # Update base fields
                fn = first_name or existing_dict.get("first_name")
                ln = last_name if last_name is not None else existing_dict.get("last_name")
                
                # Merge attribution if needed
                update_fields = {
                    "first_name": fn,
                    "last_name": ln,
                    "updated_at": datetime.now()
                }
                if attribution_update:
                    update_fields.update(attribution_update)
                
                # Build dynamic query
                set_clauses = []
                values = []
                for i, (k, v) in enumerate(update_fields.items()):
                    set_clauses.append(f"{k} = ${i+1}")
                    values.append(v)
                values.append(existing_dict.get("id"))
                
                query = f"UPDATE leads SET {', '.join(set_clauses)} WHERE id = ${len(values)}"
                await conn.execute(query, *values)
                return {**existing_dict, **update_fields}

            # New Lead
            fn = first_name or "Lead"
            ln = last_name or ""
            
            # Prep default insert values
            insert_fields: Dict[str, Any] = {
                "tenant_id": tenant_id,
                "phone_number": phone_number,
                "first_name": fn,
                "last_name": ln,
                "status": "new",
                "source": source,
                "lead_source": "ORGANIC",
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            # Override with attribution if present
            if attribution_update:
                for k, v in attribution_update.items():
                    insert_fields[k] = v
            
            # Dynamic Insert
            cols = ", ".join(insert_fields.keys())
            placeholders = ", ".join([f"${i+1}" for i in range(len(insert_fields))])
            query = f"INSERT INTO leads ({cols}) VALUES ({placeholders}) RETURNING id, tenant_id, phone_number, first_name, last_name, status, source"
            
            row = await conn.fetchrow(query, *insert_fields.values())
            return row

    async def get_chat_history(self, from_number: str, limit: int = 15, tenant_id: Optional[int] = None) -> List[dict]:
        """Returns list of {'role': ..., 'content': ...} in chronological order. Opcional tenant_id para aislamiento por clínica."""
        if tenant_id is not None:
            query = "SELECT role, content FROM chat_messages WHERE from_number = $1 AND tenant_id = $2 ORDER BY created_at DESC LIMIT $3"
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, from_number, tenant_id, limit)
                return [dict(row) for row in reversed(rows)]
        query = "SELECT role, content FROM chat_messages WHERE from_number = $1 ORDER BY created_at DESC LIMIT $2"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, from_number, limit)
            return [dict(row) for row in reversed(rows)]

    # --- WRAPPER METHODS PARA TOOLS (acceso directo al pool) ---
    async def fetch(self, query: str, *args):
        """Wrapper para pool.fetch - usado por check_availability."""
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def fetchrow(self, query: str, *args):
        """Wrapper para pool.fetchrow - usado por book_appointment."""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetchval(self, query: str, *args):
        """Wrapper para pool.fetchval."""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)
    
    async def execute(self, query: str, *args):
        """Wrapper para pool.execute - usado por book_appointment."""
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

# Global instance
db = Database()
