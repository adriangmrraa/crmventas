"""
Database Pool Management
Responsable: Conexiones al pool de PostgreSQL
"""

import asyncpg
import os
import json
from typing import Optional
from contextlib import asynccontextmanager

POSTGRES_DSN = os.getenv("POSTGRES_DSN")


class DatabasePool:
    """Manejo del pool de conexiones AsyncPG"""

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    @asynccontextmanager
    async def acquire(self):
        """Adquirir una conexión del pool"""
        async with self.pool.acquire() as conn:
            yield conn

    async def init_connection(self, conn):
        """Registra codecs para JSON/JSONB en cada conexión"""
        await conn.set_type_codec(
            "json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
        )
        await conn.set_type_codec(
            "jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
        )

    async def create_pool(self):
        """Crea el pool de conexiones"""
        if not POSTGRES_DSN:
            raise ValueError("POSTGRES_DSN environment variable is not set!")

        dsn = POSTGRES_DSN.replace("postgresql+asyncpg://", "postgresql://")
        self.pool = await asyncpg.create_pool(dsn, init=self.init_connection)
        return self.pool

    async def close_pool(self):
        """Cierra el pool de conexiones"""
        if self.pool:
            await self.pool.close()


# Singleton instance
pool_manager = DatabasePool()
