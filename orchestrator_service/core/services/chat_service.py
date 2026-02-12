from db import db
from typing import List, Dict, Any

class ChatService:
    @staticmethod
    async def get_chat_sessions(tenant_id: int) -> List[Dict[str, Any]]:
        """
        Retrieves chat sessions for a tenant, resolving contact details 
        from the appropriate niche table (patients or leads).
        """
        # Determine niche
        niche_type = await db.fetchval("SELECT niche_type FROM tenants WHERE id = $1", tenant_id)
        if not niche_type:
            niche_type = 'dental'

        if niche_type == 'dental':
            return await ChatService._get_dental_sessions(tenant_id)
        elif niche_type == 'crm_sales':
            return await ChatService._get_crm_sessions(tenant_id)
        else:
            return []

    @staticmethod
    async def _get_dental_sessions(tenant_id: int):
        # Note: We want sessions regardless of who spoke last, but usually grouped by contact.
        # The original query used DISTINCT ON phone_number from patients.
        rows = await db.pool.fetch("""
            SELECT DISTINCT ON (p.phone_number) 
                p.phone_number, 
                p.id as contact_id, 
                TRIM(REGEXP_REPLACE(p.first_name || ' ' || COALESCE(p.last_name, ''), '\s+', ' ', 'g')) as contact_name, 
                'patient' as contact_type,
                cm.content as last_message, 
                cm.created_at as last_message_time
            FROM patients p 
            LEFT JOIN chat_messages cm ON cm.from_number = p.phone_number AND cm.tenant_id = $1
            WHERE p.tenant_id = $1 
            ORDER BY p.phone_number, cm.created_at DESC NULLS LAST
        """, tenant_id)
        return [dict(r) | {"last_message_time": str(r['last_message_time']) if r['last_message_time'] else None} for r in rows]

    @staticmethod
    async def _get_crm_sessions(tenant_id: int):
        rows = await db.pool.fetch("""
            SELECT DISTINCT ON (l.phone_number) 
                l.phone_number, 
                l.id as contact_id, 
                TRIM(REGEXP_REPLACE(l.first_name || ' ' || COALESCE(l.last_name, ''), '\s+', ' ', 'g')) as contact_name,
                'lead' as contact_type,
                cm.content as last_message, 
                cm.created_at as last_message_time
            FROM leads l 
            LEFT JOIN chat_messages cm ON cm.from_number = l.phone_number AND cm.tenant_id = $1
            WHERE l.tenant_id = $1 
            ORDER BY l.phone_number, cm.created_at DESC NULLS LAST
        """, tenant_id)
        return [dict(r) | {"last_message_time": str(r['last_message_time']) if r['last_message_time'] else None} for r in rows]
