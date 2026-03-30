"""
Query Modules - Base CRUD Operations
"""

from typing import List, Optional, Dict, Any
import uuid


class BaseQuery:
    """Base class for all query modules"""

    def __init__(self, pool):
        self.pool = pool

    async def _fetch(self, query: str, *args) -> List[dict]:
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def _fetchrow(self, query: str, *args) -> Optional[dict]:
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def _execute(self, query: str, *args) -> str:
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)


class LeadsQueries(BaseQuery):
    """Queries for leads table"""

    async def get_by_tenant(self, tenant_id: int, **filters) -> List[dict]:
        """Get all leads for a tenant"""
        query = "SELECT * FROM leads WHERE tenant_id = $1"
        params = [tenant_id]

        if filters.get("status"):
            query += f" AND status = ${len(params) + 1}"
            params.append(filters["status"])

        if filters.get("assigned_seller_id"):
            query += f" AND assigned_seller_id = ${len(params) + 1}"
            params.append(filters["assigned_seller_id"])

        query += " ORDER BY created_at DESC"
        return await self._fetch(query, *params)

    async def get_by_id(self, lead_id: uuid.UUID) -> Optional[dict]:
        """Get lead by ID"""
        return await self._fetchrow("SELECT * FROM leads WHERE id = $1", lead_id)

    async def get_by_phone(self, tenant_id: int, phone_number: str) -> Optional[dict]:
        """Get lead by phone number"""
        return await self._fetchrow(
            "SELECT * FROM leads WHERE tenant_id = $1 AND phone_number = $2",
            tenant_id,
            phone_number,
        )

    async def create(self, tenant_id: int, phone_number: str, **kwargs) -> dict:
        """Create a new lead"""
        return await self._fetchrow(
            """
            INSERT INTO leads (tenant_id, phone_number, first_name, last_name, email, status, source, tags, assigned_seller_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING *
        """,
            tenant_id,
            phone_number,
            kwargs.get("first_name"),
            kwargs.get("last_name"),
            kwargs.get("email"),
            kwargs.get("status", "new"),
            kwargs.get("source", "whatsapp_inbound"),
            kwargs.get("tags", "[]"),
            kwargs.get("assigned_seller_id"),
        )

    async def update(self, lead_id: uuid.UUID, **kwargs) -> Optional[dict]:
        """Update a lead"""
        if not kwargs:
            return await self.get_by_id(lead_id)

        set_clauses = []
        params = []

        for key, value in kwargs.items():
            params.append(value)
            set_clauses.append(f"{key} = ${len(params)}")

        params.append(lead_id)

        query = f"""
            UPDATE leads 
            SET {", ".join(set_clauses)}, updated_at = NOW() 
            WHERE id = ${len(params)} 
            RETURNING *
        """
        return await self._fetchrow(query, *params)

    async def delete(self, lead_id: uuid.UUID) -> bool:
        """Delete a lead"""
        result = await self._execute("DELETE FROM leads WHERE id = $1", lead_id)
        return "DELETE" in result


class UsersQueries(BaseQuery):
    """Queries for users table"""

    async def get_by_tenant(self, tenant_id: int) -> List[dict]:
        """Get all users for a tenant"""
        return await self._fetch(
            "SELECT * FROM users WHERE tenant_id = $1 AND status = 'active' ORDER BY email",
            tenant_id,
        )

    async def get_by_email(self, email: str) -> Optional[dict]:
        """Get user by email"""
        return await self._fetchrow("SELECT * FROM users WHERE email = $1", email)

    async def create(
        self, email: str, password_hash: str, role: str, tenant_id: int, **kwargs
    ) -> dict:
        """Create a new user"""
        return await self._fetchrow(
            """
            INSERT INTO users (email, password_hash, role, tenant_id, status, first_name, last_name, phone)
            VALUES ($1, $2, $3, $4, 'pending', $5, $6, $7)
            RETURNING *
        """,
            email,
            password_hash,
            role,
            tenant_id,
            kwargs.get("first_name"),
            kwargs.get("last_name"),
            kwargs.get("phone"),
        )

    async def update_status(self, user_id: uuid.UUID, status: str) -> Optional[dict]:
        """Update user status"""
        return await self._fetchrow(
            """
            UPDATE users SET status = $1, updated_at = NOW() WHERE id = $2 RETURNING *
        """,
            status,
            user_id,
        )


class TenantsQueries(BaseQuery):
    """Queries for tenants table"""

    async def get_all(self) -> List[dict]:
        """Get all tenants"""
        return await self._fetch("SELECT * FROM tenants ORDER BY id")

    async def get_by_id(self, tenant_id: int) -> Optional[dict]:
        """Get tenant by ID"""
        return await self._fetchrow("SELECT * FROM tenants WHERE id = $1", tenant_id)

    async def create(self, clinic_name: str, **kwargs) -> dict:
        """Create a new tenant"""
        return await self._fetchrow(
            """
            INSERT INTO tenants (clinic_name, bot_phone_number, config, niche_type)
            VALUES ($1, $2, $3, $4)
            RETURNING *
        """,
            clinic_name,
            kwargs.get("bot_phone_number", ""),
            kwargs.get("config", "{}"),
            kwargs.get("niche_type", "dental"),
        )


class ChatQueries(BaseQuery):
    """Queries for chat_messages table"""

    async def get_sessions(self, tenant_id: int, **filters) -> List[dict]:
        """Get chat sessions for a tenant"""
        query = """
            SELECT DISTINCT ON (phone_number)
                phone_number,
                MAX(created_at) as last_message_at,
                COUNT(*) as message_count,
                MAX(role) as last_role,
                MAX(content) as last_message
            FROM chat_messages
            WHERE tenant_id = $1
        """
        params = [tenant_id]

        if filters.get("assigned_seller_id"):
            query += f" AND assigned_seller_id = ${len(params) + 1}"
            params.append(filters["assigned_seller_id"])

        query += " GROUP BY phone_number ORDER BY last_message_at DESC"

        return await self._fetch(query, *params)

    async def get_messages(
        self, tenant_id: int, phone_number: str, limit: int = 100
    ) -> List[dict]:
        """Get messages for a chat session"""
        return await self._fetch(
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

    async def create_message(
        self, tenant_id: int, phone_number: str, role: str, content: str, **kwargs
    ) -> dict:
        """Create a new chat message"""
        return await self._fetchrow(
            """
            INSERT INTO chat_messages (tenant_id, phone_number, role, content, assigned_seller_id)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
        """,
            tenant_id,
            phone_number,
            role,
            content,
            kwargs.get("assigned_seller_id"),
        )


# Factory function to create query instances
def create_queries(pool):
    """Create query instances for a pool"""
    return {
        "leads": LeadsQueries(pool),
        "users": UsersQueries(pool),
        "tenants": TenantsQueries(pool),
        "chat": ChatQueries(pool),
    }
