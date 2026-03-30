"""
Database Module - Backward Compatibility Layer
=============================================
This module provides backward compatibility for the old db.py interface
while the internal structure is being refactored.

New structure:
- db/pool.py: Pool management
- db/migrations.py: Auto-migrations (Maintenance Robot)
- db/queries/: Query modules by domain
- db/models.py: SQLAlchemy models

All exports are re-exported from here for backward compatibility.
"""

import os
import json
import asyncpg
from typing import Optional, List, Tuple, Dict, Any
from contextlib import asynccontextmanager

from .pool import pool_manager, DatabasePool
from .migrations import create_migration_runner, MigrationRunner


class Database:
    """
    Main Database class - maintains backward compatibility
    Delegates to pool.py and migrations.py internally
    """

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    @asynccontextmanager
    async def get_connection(self):
        """Legacy interface - use pool.acquire() directly"""
        async with self.pool.acquire() as conn:
            yield conn

    async def _init_connection(self, conn):
        """Registra codecs para JSON/JSONB"""
        await conn.set_type_codec(
            "json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
        )
        await conn.set_type_codec(
            "jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
        )

    async def connect(self):
        """Conecta al pool y ejecuta auto-migraciones"""
        if not self.pool:
            from .pool import POSTGRES_DSN

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
        """Ejecuta el sistema de auto-migración"""
        import logging

        logger = logging.getLogger("db")

        try:
            migration_runner = create_migration_runner(self.pool)
            await migration_runner.run_all()
            logger.info("✅ Database optimized and synced (Maintenance Robot OK)")
        except Exception as e:
            import traceback

            logger.error(f"❌ Error in Maintenance Robot: {e}")
            logger.debug(traceback.format_exc())

    async def _apply_foundation(self, logger):
        """Legacy: foundation schema application"""
        migration_runner = create_migration_runner(self.pool)
        await migration_runner._apply_foundation()

    async def _run_evolution_pipeline(self, logger):
        """Legacy: evolution pipeline"""
        migration_runner = create_migration_runner(self.pool)
        await migration_runner._run_evolution_pipeline()

    async def disconnect(self):
        """Desconecta el pool"""
        if self.pool:
            await self.pool.close()


# Backward compatibility: single instance
db = Database()


# ============================================================================
# Re-export everything from the old db.py interface
# These are used throughout the codebase
# ============================================================================


async def fetch(query: str, *args) -> List[dict]:
    """Execute query and return all rows"""
    async with db.pool.acquire() as conn:
        return await conn.fetch(query, *args)


async def fetchrow(query: str, *args) -> Optional[dict]:
    """Execute query and return first row"""
    async with db.pool.acquire() as conn:
        return await conn.fetchrow(query, *args)


async def execute(query: str, *args) -> str:
    """Execute query and return status"""
    async with db.pool.acquire() as conn:
        return await conn.execute(query, *args)


async def execute_many(query: str, *args) -> None:
    """Execute query multiple times"""
    async with db.pool.acquire() as conn:
        return await conn.executemany(query, *args)


# Additional utility functions that were in the original db.py


async def tenants_get_all() -> List[dict]:
    """Get all tenants"""
    return await fetch("SELECT * FROM tenants ORDER BY id")


async def tenants_get_by_id(tenant_id: int) -> Optional[dict]:
    """Get tenant by ID"""
    return await fetchrow("SELECT * FROM tenants WHERE id = $1", tenant_id)


async def users_get_by_tenant(tenant_id: int) -> List[dict]:
    """Get all users for a tenant"""
    return await fetch(
        "SELECT * FROM users WHERE tenant_id = $1 AND status = 'active' ORDER BY email",
        tenant_id,
    )


async def users_get_by_email(email: str) -> Optional[dict]:
    """Get user by email"""
    return await fetchrow("SELECT * FROM users WHERE email = $1", email)


async def users_create(
    email: str, password_hash: str, role: str, tenant_id: int, **kwargs
) -> dict:
    """Create a new user"""
    return await fetchrow(
        """
        INSERT INTO users (email, password_hash, role, tenant_id, status, **kwargs)
        VALUES ($1, $2, $3, $4, 'pending', $5)
        RETURNING *
    """,
        email,
        password_hash,
        role,
        tenant_id,
        json.dumps(kwargs) if kwargs else None,
    )


async def leads_get_by_tenant(tenant_id: int, **filters) -> List[dict]:
    """Get leads for a tenant with optional filters"""
    query = "SELECT * FROM leads WHERE tenant_id = $1"
    params = [tenant_id]

    if filters.get("status"):
        query += f" AND status = ${len(params) + 1}"
        params.append(filters["status"])

    if filters.get("assigned_seller_id"):
        query += f" AND assigned_seller_id = ${len(params) + 1}"
        params.append(filters["assigned_seller_id"])

    query += " ORDER BY created_at DESC"

    return await fetch(query, *params)


async def leads_create(tenant_id: int, phone_number: str, **kwargs) -> dict:
    """Create a new lead"""
    return await fetchrow(
        """
        INSERT INTO leads (tenant_id, phone_number, **kwargs)
        VALUES ($1, $2, $3)
        RETURNING *
    """,
        tenant_id,
        phone_number,
        json.dumps(kwargs) if kwargs else None,
    )


async def leads_update(lead_id: uuid.UUID, **kwargs) -> Optional[dict]:
    """Update a lead"""
    set_clauses = []
    params = []

    for key, value in kwargs.items():
        params.append(value)
        set_clauses.append(f"{key} = ${len(params)}")

    if not set_clauses:
        return await fetchrow("SELECT * FROM leads WHERE id = $1", lead_id)

    params.append(lead_id)

    query = f"UPDATE leads SET {', '.join(set_clauses)}, updated_at = NOW() WHERE id = ${len(params)} RETURNING *"
    return await fetchrow(query, *params)


async def chat_get_sessions(tenant_id: int, **filters) -> List[dict]:
    """Get chat sessions for a tenant"""
    query = """
        SELECT DISTINCT ON (phone_number)
            phone_number,
            MAX(created_at) as last_message_at,
            COUNT(*) as message_count
        FROM chat_messages
        WHERE tenant_id = $1
    """
    params = [tenant_id]

    if filters.get("assigned_seller_id"):
        query += f" AND assigned_seller_id = ${len(params) + 1}"
        params.append(filters["assigned_seller_id"])

    query += " GROUP BY phone_number ORDER BY last_message_at DESC"

    return await fetch(query, *params)


async def chat_get_messages(
    tenant_id: int, phone_number: str, limit: int = 100
) -> List[dict]:
    """Get messages for a chat session"""
    return await fetch(
        """
        SELECT * FROM chat_messages 
        WHERE tenant_id = $1 AND phone_number = $2
        ORDER BY created_at DESC 
        LIMIT $3
    """,
        tenant_id,
        phone_number,
        limit,
    )


# Import uuid for lead updates
import uuid
