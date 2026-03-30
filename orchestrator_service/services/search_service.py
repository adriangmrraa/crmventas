import logging
from typing import List, dict
from db import db

logger = logging.getLogger(__name__)

class SearchService:
    async def global_search(self, tenant_id: int, query: str, limit: int = 20):
        """
        Performs a full-text search across Leads, Notes, and Messages.
        Uses PostgreSQL FTS (indexes created in Patch 38).
        """
        if not query or len(query) < 2:
            return {"leads": [], "notes": [], "messages": []}
            
        # Clean query for Postgres
        query_parts = query.split()
        fts_query = " & ".join([f"{p}:*" for p in query_parts]) # Prefix search
        
        # 1. Search Leads
        leads_query = """
            SELECT id, first_name, last_name, email, phone_number, status, 
                   ts_rank_cd(to_tsvector('spanish', coalesce(first_name, '') || ' ' || coalesce(last_name, '') || ' ' || coalesce(email, '') || ' ' || coalesce(phone_number, '')), to_tsquery('spanish', $2)) as rank
            FROM leads
            WHERE tenant_id = $1 AND to_tsvector('spanish', coalesce(first_name, '') || ' ' || coalesce(last_name, '') || ' ' || coalesce(email, '') || ' ' || coalesce(phone_number, '')) @@ to_tsquery('spanish', $2)
            ORDER BY rank DESC
            LIMIT $3
        """
        lead_rows = await db.fetch(leads_query, tenant_id, fts_query, limit)
        
        # 2. Search Notes
        notes_query = """
            SELECT ln.id, ln.lead_id, ln.content, ln.note_type, l.first_name, l.last_name, 
                   ts_rank_cd(to_tsvector('spanish', coalesce(ln.content, '')), to_tsquery('spanish', $2)) as rank
            FROM lead_notes ln
            JOIN leads l ON ln.lead_id = l.id
            WHERE ln.tenant_id = $1 AND to_tsvector('spanish', coalesce(ln.content, '')) @@ to_tsquery('spanish', $2)
            ORDER BY rank DESC
            LIMIT $3
        """
        note_rows = await db.fetch(notes_query, tenant_id, fts_query, limit)
        
        # 3. Search Chat Messages
        messages_query = """
            SELECT cm.id, cm.from_number, cm.content, cm.role, l.first_name, l.last_name, 
                   ts_rank_cd(to_tsvector('spanish', coalesce(cm.content, '')), to_tsquery('spanish', $2)) as rank
            FROM chat_messages cm
            LEFT JOIN leads l ON (cm.from_number = l.phone_number AND cm.tenant_id = l.tenant_id)
            WHERE cm.tenant_id = $1 AND to_tsvector('spanish', coalesce(cm.content, '')) @@ to_tsquery('spanish', $2)
            ORDER BY rank DESC
            LIMIT $3
        """
        message_rows = await db.fetch(messages_query, tenant_id, fts_query, limit)

        return {
            "leads": [dict(r) for r in lead_rows],
            "notes": [dict(r) for r in note_rows],
            "messages": [dict(r) for r in message_rows]
        }

search_service = SearchService()
