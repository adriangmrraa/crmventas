from typing import List, Dict, Optional, Any
from uuid import UUID
import asyncpg
from datetime import datetime

class LeadHistoryService:
    """Servicio para consulta del audit trail y eventos de leads (Lead Status History)"""

    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool

    async def get_lead_timeline(self, tenant_id: int, lead_id: UUID, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Devuelve el timeline completo (Audit Trail) de cambios de estado para un lead, asegurando Tenant Isolation."""
        query = """
            SELECT h.id, h.from_status_code, h.to_status_code,
                   h.changed_by_user_id, h.changed_by_name,
                   h.comment, h.source, h.created_at, h.metadata,
                   s_from.name as from_status_name, s_from.color as from_status_color,
                   s_to.name as to_status_name, s_to.color as to_status_color
            FROM lead_status_history h
            LEFT JOIN lead_statuses s_from ON h.tenant_id = s_from.tenant_id AND h.from_status_code = s_from.code
            JOIN lead_statuses s_to ON h.tenant_id = s_to.tenant_id AND h.to_status_code = s_to.code
            WHERE h.tenant_id = $1 AND h.lead_id = $2
            ORDER BY h.created_at DESC
            LIMIT $3 OFFSET $4
        """
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, tenant_id, lead_id, limit, offset)
            return [dict(row) for row in rows]

    async def get_status_analytics(self, tenant_id: int, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Agrega análisis sencillos de los movimientos transaccionales de leads."""
        query = """
            SELECT to_status_code, COUNT(*) as transition_count
            FROM lead_status_history
            WHERE tenant_id = $1 AND created_at BETWEEN $2 AND $3
            GROUP BY to_status_code
            ORDER BY transition_count DESC
        """
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, tenant_id, start_date, end_date)
            return {"transitions_to": [dict(row) for row in rows]}
