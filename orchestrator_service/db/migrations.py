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
        ]


def create_migration_runner(pool):
    """Factory para crear MigrationRunner"""
    return MigrationRunner(pool)
