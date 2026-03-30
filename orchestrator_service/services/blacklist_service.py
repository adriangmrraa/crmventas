import logging
from typing import Optional, List, Tuple
from db import db

logger = logging.getLogger(__name__)

class BlacklistService:
    async def is_blacklisted(self, tenant_id: int, value: str) -> Tuple[bool, Optional[str]]:
        """
        Calculates if a value (phone, email, etc) is blacklisted for a tenant.
        Returns (is_blacklisted, reason).
        """
        if not value:
            return False, None
            
        query = "SELECT reason FROM blacklist WHERE tenant_id = $1 AND value = $2"
        row = await db.fetchrow(query, tenant_id, value)
        if row:
            return True, row['reason']
        return False, None

    async def log_attempt(self, tenant_id: int, value: str, type: str, source: str, payload: dict = None):
        """Logs a blocked attempt from a blacklisted entity."""
        import json
        query = """
            INSERT INTO blacklist_attempts (tenant_id, value, type, source, payload)
            VALUES ($1, $2, $3, $4, $5)
        """
        await db.execute(query, tenant_id, value, type, source, json.dumps(payload or {}))

    async def add_to_blacklist(self, tenant_id: int, value: str, type: str, reason: str = None):
        """Adds a value to the blacklist."""
        query = """
            INSERT INTO blacklist (tenant_id, value, type, reason)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (tenant_id, value) DO UPDATE SET 
                reason = EXCLUDED.reason,
                created_at = NOW()
        """
        await db.execute(query, tenant_id, value, type, reason)

    async def remove_from_blacklist(self, tenant_id: int, value: str):
        """Removes a value from the blacklist."""
        query = "DELETE FROM blacklist WHERE tenant_id = $1 AND value = $2"
        await db.execute(query, tenant_id, value)

    async def list_blacklist(self, tenant_id: int) -> List[dict]:
        """Lists all blacklisted entities for a tenant."""
        query = "SELECT * FROM blacklist WHERE tenant_id = $1 ORDER BY created_at DESC"
        rows = await db.fetch(query, tenant_id)
        return [dict(r) for r in rows]

blacklist_service = BlacklistService()
