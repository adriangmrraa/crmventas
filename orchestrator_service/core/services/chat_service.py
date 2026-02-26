from datetime import datetime
from db import db
from typing import List, Dict, Any

from core.utils import ARG_TZ


class ChatService:
    @staticmethod
    async def get_chat_sessions(tenant_id: int) -> List[Dict[str, Any]]:
        """Chat sessions for tenant; CRM single-niche uses leads."""
        niche_type = await db.fetchval("SELECT COALESCE(niche_type, 'crm_sales') FROM tenants WHERE id = $1", tenant_id) or "crm_sales"
        if niche_type == "crm_sales":
            return await ChatService._get_crm_sessions(tenant_id)
        return []

    @staticmethod
    async def _get_crm_sessions(tenant_id: int) -> List[Dict[str, Any]]:
        rows = await db.pool.fetch("""
            SELECT DISTINCT ON (l.phone_number)
                l.phone_number,
                l.id as contact_id,
                TRIM(REGEXP_REPLACE(COALESCE(l.first_name,'') || ' ' || COALESCE(l.last_name,''), '\s+', ' ', 'g')) as contact_name,
                'lead' as contact_type,
                cm.content as last_message,
                cm.created_at as last_message_time,
                l.human_handoff_requested,
                l.human_override_until,
                $1::int as tenant_id
            FROM leads l
            JOIN chat_messages cm ON cm.from_number = l.phone_number AND cm.tenant_id = $1
            WHERE l.tenant_id = $1
            ORDER BY l.phone_number, cm.created_at DESC NULLS LAST
        """, tenant_id)
        now = datetime.now(ARG_TZ)
        out = []
        for r in rows:
            until = r.get("human_override_until")
            if until is not None and hasattr(until, "tzinfo") and until.tzinfo is None:
                until = until.replace(tzinfo=ARG_TZ) if hasattr(until, "replace") else until
            is_silenced = bool(r.get("human_handoff_requested")) and until is not None and (until > now if hasattr(until, "__gt__") else True)
            status = "silenced" if is_silenced else "active"
            out.append({
                "phone_number": r["phone_number"],
                "contact_id": str(r["contact_id"]) if r.get("contact_id") else None,
                "contact_name": (r["contact_name"] or "").strip() or "Lead",
                # Frontend (ChatsView.tsx) expects patient_name/patient_id
                "patient_id": str(r["contact_id"]) if r.get("contact_id") else None,
                "patient_name": (r["contact_name"] or "").strip() or "Lead",
                "contact_type": "lead",
                "last_message": r.get("last_message"),
                "last_message_time": str(r["last_message_time"]) if r.get("last_message_time") else None,
                "tenant_id": tenant_id,
                "status": status,
                "human_override_until": until.isoformat() if until and hasattr(until, "isoformat") else (str(until) if until else None),
            })
        return out
