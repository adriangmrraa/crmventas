from typing import Dict, Any
from db import db
import logging

logger = logging.getLogger("dental_context")

async def get_dental_context(tenant_id: int) -> Dict[str, Any]:
    """
    Fetches dental-specific context data for prompt rendering.
    
    Args:
        tenant_id: The tenant identifier
        
    Returns:
        Dictionary containing:
        - clinic_name: Name of the clinic
        - bot_phone_number: WhatsApp phone number
        - treatment_list: Comma-separated list of treatments (future enhancement)
        - working_hours: Operating hours (future enhancement)
    """
    try:
        # Fetch tenant information
        tenant_info = await db.pool.fetchrow(
            "SELECT clinic_name, bot_phone_number, config FROM tenants WHERE id = $1",
            tenant_id
        )
        
        if not tenant_info:
            logger.warning(f"Tenant {tenant_id} not found, using defaults")
            return {
                "clinic_name": "Clínica Dental",
                "bot_phone_number": "Unknown"
            }
        
        # TODO: Future enhancement - fetch active treatments
        # treatments = await db.fetch("SELECT name FROM treatments WHERE tenant_id = $1 AND active = true", tenant_id)
        # treatment_list = ", ".join([t['name'] for t in treatments])
        
        return {
            "clinic_name": tenant_info['clinic_name'] or "Clínica Dental",
            "bot_phone_number": tenant_info['bot_phone_number'] or "Unknown",
            # "treatment_list": treatment_list,
            # "working_hours": tenant_info.get('config', {}).get('working_hours', {})
        }
        
    except Exception as e:
        logger.error(f"Error fetching dental context for tenant {tenant_id}: {e}")
        # Return safe defaults
        return {
            "clinic_name": "Clínica Dental",
            "bot_phone_number": "Unknown"
        }
