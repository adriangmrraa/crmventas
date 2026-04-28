import logging
from typing import Optional, List, Tuple
from db import db
from services.deduplication_service import normalize_phone

logger = logging.getLogger(__name__)

PREDEFINED_REASONS = [
    "lead_descartado",
    "ex_cliente",
    "spam",
    "numero_invalido",
    "no_contactar",
]


class BlacklistService:
    async def is_blacklisted(self, tenant_id: int, value: str) -> Tuple[bool, Optional[str]]:
        """
        Checks if a value (phone, email, etc) is blacklisted for a tenant.
        Returns (is_blacklisted, reason). Exact match only.
        """
        if not value:
            return False, None

        query = "SELECT reason FROM blacklist WHERE tenant_id = $1 AND value = $2"
        row = await db.fetchrow(query, tenant_id, value)
        if row:
            return True, row['reason']
        return False, None

    async def is_blacklisted_normalized(
        self,
        tenant_id: int,
        phone: Optional[str] = None,
        email: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        G1: Checks phone (raw + E.164 normalized) and email against blacklist.
        Returns (is_blacklisted, reason) — True on first match found.
        """
        checks: List[str] = []

        if phone:
            raw_phone = phone.strip()
            norm_phone = normalize_phone(raw_phone)
            checks.append(raw_phone)
            if norm_phone and norm_phone != raw_phone:
                checks.append(norm_phone)

        if email:
            norm_email = email.strip().lower()
            checks.append(norm_email)

        if not checks:
            return False, None

        # Build parameterized query for all variants at once
        placeholders = ", ".join(f"${i + 2}" for i in range(len(checks)))
        query = f"SELECT value, reason FROM blacklist WHERE tenant_id = $1 AND value IN ({placeholders}) LIMIT 1"
        row = await db.fetchrow(query, tenant_id, *checks)
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
                type = EXCLUDED.type,
                created_at = NOW()
        """
        await db.execute(query, tenant_id, value, type, reason)

    async def remove_from_blacklist(self, tenant_id: int, value: str):
        """Removes a value from the blacklist."""
        query = "DELETE FROM blacklist WHERE tenant_id = $1 AND value = $2"
        await db.execute(query, tenant_id, value)

    async def list_blacklist(self, tenant_id: int) -> List[dict]:
        """Lists all blacklisted entities for a tenant."""
        query = "SELECT id, tenant_id, value, type, reason, created_at FROM blacklist WHERE tenant_id = $1 ORDER BY created_at DESC"
        rows = await db.fetch(query, tenant_id)
        return [dict(r) for r in rows]

    async def list_attempts(self, tenant_id: int, limit: int = 50, offset: int = 0) -> List[dict]:
        """G4: Lists blacklist attempts with pagination."""
        query = """
            SELECT id, tenant_id, value, type, source, payload, created_at
            FROM blacklist_attempts
            WHERE tenant_id = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
        """
        rows = await db.fetch(query, tenant_id, limit, offset)
        return [dict(r) for r in rows]

    async def get_attempts_count(self, tenant_id: int) -> int:
        """Returns total count of blacklist attempts for a tenant."""
        return await db.fetchval(
            "SELECT COUNT(*) FROM blacklist_attempts WHERE tenant_id = $1",
            tenant_id
        ) or 0

    async def block_lead(
        self,
        tenant_id: int,
        lead_id: str,
        reason: str,
    ) -> dict:
        """
        G5: Blocks a lead:
        1. Reads lead phone + email
        2. Adds both to blacklist
        3. Updates lead status to 'blocked'
        Returns dict with blocked values.
        """
        row = await db.fetchrow(
            "SELECT id, phone_number, email FROM leads WHERE tenant_id = $1 AND id = $2",
            tenant_id, lead_id
        )
        if not row:
            raise ValueError(f"Lead {lead_id} not found for tenant {tenant_id}")

        phone = row["phone_number"]
        email = row["email"]
        blocked = []

        if phone:
            await self.add_to_blacklist(tenant_id, phone, "phone", reason)
            norm = normalize_phone(phone)
            if norm and norm != phone:
                await self.add_to_blacklist(tenant_id, norm, "phone", reason)
            blocked.append({"type": "phone", "value": phone})

        if email:
            norm_email = email.strip().lower()
            await self.add_to_blacklist(tenant_id, norm_email, "email", reason)
            blocked.append({"type": "email", "value": norm_email})

        await db.execute(
            "UPDATE leads SET status = 'blocked', updated_at = NOW() WHERE tenant_id = $1 AND id = $2",
            tenant_id, lead_id
        )

        return {"lead_id": lead_id, "blocked": blocked, "reason": reason}

    async def add_bulk(self, tenant_id: int, items: list) -> dict:
        """Bulk add entries to blacklist. Each item: {value, type, reason}."""
        added = 0
        errors = []
        for item in items:
            try:
                await self.add_to_blacklist(
                    tenant_id,
                    item["value"],
                    item.get("type", "phone"),
                    item.get("reason"),
                )
                added += 1
            except Exception as e:
                errors.append({"value": item.get("value"), "error": str(e)})
        return {"added": added, "errors": errors}


blacklist_service = BlacklistService()
