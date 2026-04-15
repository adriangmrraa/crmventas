"""
Database Migrations (Maintenance Robot)
Responsable: Auto-migraciones idempotentes del esquema
"""

import os
import logging
from typing import List

logger = logging.getLogger("db.migrations")


class MigrationRunner:
    """Ejecuta migraciones idempotentes al iniciar"""

    def __init__(self, pool):
        self.pool = pool

    async def run_all(self):
        """Ejecuta todas las migraciones"""
        critical_tables = ["tenants", "users", "leads"]

        async with self.pool.acquire() as conn:
            existing_tables = await conn.fetch(
                """
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = ANY($1)
            """,
                critical_tables,
            )

            existing_table_names = [r["table_name"] for r in existing_tables]
            foundation_needed = len(existing_table_names) < len(critical_tables)

        if foundation_needed:
            logger.warning(f"⚠️ Esquema incompleto, aplicando Foundation...")
            await self._apply_foundation()

        await self._run_evolution_pipeline()
        logger.info("✅ Database optimized and synced")

    async def _apply_foundation(self):
        """Ejecuta el esquema base dentalogic_schema.sql"""
        possible_paths = [
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "db",
                "init",
                "dentalogic_schema.sql",
            ),
            os.path.join(
                os.path.dirname(__file__), "..", "db", "init", "dentalogic_schema.sql"
            ),
            "/app/db/init/dentalogic_schema.sql",
        ]

        schema_path = next((p for p in possible_paths if os.path.exists(p)), None)
        if not schema_path:
            logger.error("❌ Foundation schema not found!")
            return

        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        clean_lines = [
            line.split("--")[0].rstrip()
            for line in schema_sql.splitlines()
            if line.strip()
        ]
        clean_sql = "\n".join(clean_lines)

        async with self.pool.acquire() as conn:
            try:
                await conn.execute(clean_sql)
                logger.info("✅ Foundation applied.")
            except Exception as e:
                logger.error(f"❌ Error applying Foundation: {e}")

    async def _run_evolution_pipeline(self):
        """Pipeline de parches atómicos e idempotentes"""
        patches = self._get_patches()

        async with self.pool.acquire() as conn:
            for patch in patches:
                try:
                    await conn.execute(patch)
                except Exception as e:
                    logger.debug(f"Patch execution: {e}")

    def _get_patches(self) -> List[str]:
        """Retorna lista de parches idempotentes"""
        return [
            # Parche 1: Columna user_id en professionals
            """DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='professionals' AND column_name='user_id') THEN ALTER TABLE professionals ADD COLUMN user_id UUID REFERENCES users(id) ON DELETE SET NULL; END IF; END $$;""",
            # Parche 2: Tabla leads (CRM Core)
            """DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'leads') THEN CREATE TABLE leads (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE, phone_number VARCHAR(50) NOT NULL, first_name TEXT, last_name TEXT, status TEXT DEFAULT 'new', source TEXT DEFAULT 'whatsapp_inbound', created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW(), CONSTRAINT leads_tenant_phone_unique UNIQUE (tenant_id, phone_number)); END IF; END $$;""",
            # Parche 3: Tabla credentials
            """DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'credentials') THEN CREATE TABLE credentials (id BIGSERIAL PRIMARY KEY, tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE, name VARCHAR(255) NOT NULL, value TEXT NOT NULL, category VARCHAR(50) DEFAULT 'general', created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW(), UNIQUE(tenant_id, name)); END IF; END $$;""",
            # Parche 4: Tabla meta_tokens
            """DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'meta_tokens') THEN CREATE TABLE meta_tokens (id SERIAL PRIMARY KEY, tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE, access_token TEXT NOT NULL, token_type VARCHAR(50), page_id VARCHAR(255), created_at TIMESTAMP DEFAULT NOW(), updated_at TIMESTAMP DEFAULT NOW(), UNIQUE(tenant_id, token_type)); END IF; END $$;""",
            # Parche 5: lead_statuses
            """DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'lead_statuses') THEN CREATE TABLE lead_statuses (id SERIAL PRIMARY KEY, tenant_id INTEGER NOT NULL REFERENCES tenants(id), name VARCHAR(100) NOT NULL, code VARCHAR(50) NOT NULL, category VARCHAR(50), color VARCHAR(20), icon VARCHAR(50), is_initial BOOLEAN DEFAULT FALSE, is_final BOOLEAN DEFAULT FALSE, sort_order INTEGER DEFAULT 0, created_at TIMESTAMPTZ DEFAULT NOW()); END IF; END $$;""",
            # Parche 6: sellers table
            """DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sellers') THEN CREATE TABLE sellers (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID REFERENCES users(id), tenant_id INTEGER NOT NULL REFERENCES tenants(id), first_name VARCHAR(100), last_name VARCHAR(100), email VARCHAR(255), phone VARCHAR(50), is_active BOOLEAN DEFAULT TRUE, created_at TIMESTAMPTZ DEFAULT NOW()); END IF; END $$;""",
            # Parche 7: Make bot_phone_number nullable (CEO registration fix)
            """DO $$ BEGIN ALTER TABLE tenants ALTER COLUMN bot_phone_number DROP NOT NULL; EXCEPTION WHEN OTHERS THEN NULL; END $$;""",
            # Parche 8: Drive folders (SPEC-01)
            """DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'drive_folders') THEN CREATE TABLE drive_folders (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE, client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE, nombre VARCHAR(255) NOT NULL, parent_id UUID REFERENCES drive_folders(id) ON DELETE CASCADE, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()); CREATE INDEX idx_drive_folders_tenant ON drive_folders(tenant_id); CREATE INDEX idx_drive_folders_client ON drive_folders(client_id); CREATE INDEX idx_drive_folders_parent ON drive_folders(parent_id); END IF; END $$;""",
            # Parche 9: Drive files (SPEC-01)
            """DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'drive_files') THEN CREATE TABLE drive_files (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE, client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE, folder_id UUID NOT NULL REFERENCES drive_folders(id) ON DELETE CASCADE, nombre VARCHAR(255) NOT NULL, storage_path VARCHAR(1024) NOT NULL, mime_type VARCHAR(127) NOT NULL, size_bytes BIGINT NOT NULL CHECK (size_bytes > 0), uploaded_by INTEGER REFERENCES users(id) ON DELETE SET NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()); CREATE INDEX idx_drive_files_tenant ON drive_files(tenant_id); CREATE INDEX idx_drive_files_client ON drive_files(client_id); CREATE INDEX idx_drive_files_folder ON drive_files(folder_id); END IF; END $$;""",
            # Parche 10: Plantillas de mensajes (SPEC-02)
            """DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'plantillas') THEN CREATE TABLE plantillas (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE, nombre TEXT NOT NULL, categoria TEXT NOT NULL DEFAULT 'whatsapp' CHECK (categoria IN ('whatsapp', 'email', 'seguimiento', 'prospeccion', 'cierre')), contenido TEXT NOT NULL CHECK (char_length(contenido) <= 4000), variables TEXT[] NOT NULL DEFAULT '{}', uso_count INTEGER NOT NULL DEFAULT 0, created_by INTEGER REFERENCES users(id) ON DELETE SET NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()); CREATE INDEX idx_plantillas_tenant_id ON plantillas(tenant_id); CREATE INDEX idx_plantillas_tenant_categoria ON plantillas(tenant_id, categoria); CREATE INDEX idx_plantillas_tenant_uso ON plantillas(tenant_id, uso_count DESC); CREATE UNIQUE INDEX idx_plantillas_tenant_nombre ON plantillas(tenant_id, nombre); END IF; END $$;""",
            # Parche 11: Internal Chat messages (SPEC-04)
            """DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'chat_mensajes') THEN CREATE TABLE chat_mensajes (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE, canal_id TEXT NOT NULL, autor_id VARCHAR(255) NOT NULL, autor_nombre TEXT NOT NULL, autor_rol TEXT NOT NULL, contenido TEXT NOT NULL CHECK (char_length(contenido) <= 2000), tipo TEXT NOT NULL DEFAULT 'mensaje' CHECK (tipo IN ('mensaje', 'notificacion_tarea', 'notificacion_llamada')), metadata JSONB, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()); CREATE INDEX idx_chat_mensajes_tenant_canal ON chat_mensajes(tenant_id, canal_id, created_at DESC); END IF; END $$;""",
            # Parche 12: Internal Chat conversations (SPEC-04)
            """DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'chat_conversaciones') THEN CREATE TABLE chat_conversaciones (canal_id TEXT NOT NULL, tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE, tipo TEXT NOT NULL CHECK (tipo IN ('canal', 'dm')), participantes VARCHAR(255)[] NOT NULL DEFAULT '{}', ultima_actividad TIMESTAMPTZ NOT NULL DEFAULT NOW(), created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), PRIMARY KEY (canal_id, tenant_id)); CREATE INDEX idx_chat_conv_tenant_tipo ON chat_conversaciones(tenant_id, tipo, ultima_actividad DESC); END IF; END $$;""",
            # Parche 13: Internal Chat DM unread counters (SPEC-04)
            """DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'chat_dm_no_leidos') THEN CREATE TABLE chat_dm_no_leidos (tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE, user_id VARCHAR(255) NOT NULL, canal_id TEXT NOT NULL, count INTEGER NOT NULL DEFAULT 0, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), PRIMARY KEY (tenant_id, user_id, canal_id)); END IF; END $$;""",
            # Parche 14: Trigger touch_chat_conversacion (SPEC-04)
            """DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'touch_chat_conversacion') THEN CREATE FUNCTION touch_chat_conversacion() RETURNS TRIGGER AS $fn$ BEGIN INSERT INTO chat_conversaciones (canal_id, tenant_id, tipo, ultima_actividad) VALUES (NEW.canal_id, NEW.tenant_id, CASE WHEN NEW.canal_id LIKE 'dm_%' THEN 'dm' ELSE 'canal' END, NEW.created_at) ON CONFLICT (canal_id, tenant_id) DO UPDATE SET ultima_actividad = EXCLUDED.ultima_actividad; RETURN NEW; END; $fn$ LANGUAGE plpgsql; CREATE TRIGGER trg_touch_chat_conv AFTER INSERT ON chat_mensajes FOR EACH ROW EXECUTE FUNCTION touch_chat_conversacion(); END IF; END $$;""",
            # Parche 15: Daily checkins (SPEC-05)
            """DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'daily_checkins') THEN CREATE TABLE daily_checkins (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE, seller_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, fecha DATE NOT NULL DEFAULT CURRENT_DATE, llamadas_planeadas INTEGER NOT NULL CHECK (llamadas_planeadas > 0), checkin_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), llamadas_logradas INTEGER, contactos_logrados INTEGER, notas TEXT, checkout_at TIMESTAMPTZ, estado TEXT NOT NULL DEFAULT 'active' CHECK (estado IN ('active','completed','auto_closed')), cumplimiento_pct DECIMAL(5,2), created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW(), UNIQUE (tenant_id, seller_id, fecha)); CREATE INDEX idx_daily_checkins_tenant_fecha ON daily_checkins(tenant_id, fecha DESC); CREATE INDEX idx_daily_checkins_seller_fecha ON daily_checkins(seller_id, fecha DESC); END IF; END $$;""",
            # Parche 16: Vendor tasks (SPEC-06)
            """DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'vendor_tasks') THEN CREATE TABLE vendor_tasks (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE, vendor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, created_by INTEGER NOT NULL REFERENCES users(id), contenido TEXT NOT NULL CHECK (char_length(contenido) BETWEEN 1 AND 2000), es_tarea BOOLEAN NOT NULL DEFAULT FALSE, fecha_limite TIMESTAMPTZ, completada BOOLEAN NOT NULL DEFAULT FALSE, completada_at TIMESTAMPTZ, created_at TIMESTAMPTZ DEFAULT NOW()); CREATE INDEX idx_vendor_tasks_tenant_vendor ON vendor_tasks(tenant_id, vendor_id); END IF; END $$;""",
            # Parche 17: Manuales / Knowledge Base (SPEC-03)
            """DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'manuales') THEN CREATE TABLE manuales (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE, titulo TEXT NOT NULL CHECK (char_length(trim(titulo)) > 0), contenido TEXT NOT NULL CHECK (char_length(trim(contenido)) > 0), categoria TEXT NOT NULL DEFAULT 'general' CHECK (categoria IN ('general','guion_ventas','objeciones','producto','proceso','onboarding')), autor TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()); CREATE INDEX idx_manuales_tenant_cat ON manuales(tenant_id, categoria); CREATE INDEX idx_manuales_tenant_updated ON manuales(tenant_id, updated_at DESC); END IF; END $$;""",
            # Parche 18: Lead Forms (F-02)
            """DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'lead_forms') THEN CREATE TABLE lead_forms (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE, name TEXT NOT NULL, slug TEXT NOT NULL UNIQUE, fields JSONB NOT NULL DEFAULT '[]', thank_you_message TEXT DEFAULT '', redirect_url TEXT DEFAULT '', active BOOLEAN NOT NULL DEFAULT TRUE, created_by INTEGER REFERENCES users(id) ON DELETE SET NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()); CREATE INDEX idx_lead_forms_tenant ON lead_forms(tenant_id); CREATE INDEX idx_lead_forms_slug ON lead_forms(slug); END IF; END $$;""",
            # Parche 19: Lead Form Submissions (F-02)
            """DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'lead_form_submissions') THEN CREATE TABLE lead_form_submissions (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), form_id UUID NOT NULL REFERENCES lead_forms(id) ON DELETE CASCADE, lead_id UUID, data JSONB NOT NULL DEFAULT '{}', ip_address TEXT, submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()); CREATE INDEX idx_lead_form_submissions_form ON lead_form_submissions(form_id); END IF; END $$;""",
        ]


def create_migration_runner(pool):
    """Factory para crear MigrationRunner"""
    return MigrationRunner(pool)
