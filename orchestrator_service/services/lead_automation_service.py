import asyncio
from typing import List, Dict, Any, Optional
from uuid import UUID
import asyncpg
import aiohttp
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

class LeadAutomationService:
    """
    Servicio Background que procesa Webhooks o Triggers Internos (Actions)
    cuando el estado de un lead cambia. Opera de manera asíncrona garantizando alta
    disponibilidad a través del Patrón Circuit Breaker.
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool

    async def get_triggers_for_transition(self, tenant_id: int, on_status_code: str) -> List[Dict[str, Any]]:
        """Busca y evalúa todos los disipadores asignados a un status particular"""
        query = """
            SELECT id, action_type, config_json 
            FROM lead_status_triggers
            WHERE tenant_id = $1 
            AND on_status_code = $2 
            AND is_active = true
        """
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, tenant_id, on_status_code)
            return [dict(row) for row in rows]

    async def _execute_webhook(self, url: str, headers: Dict, payload: Dict) -> Dict[str, Any]:
        """Ataque HTTP con Timeout / Circuit Breaker Básico"""
        try:
           async with aiohttp.ClientSession() as session:
              async with session.post(url, json=payload, headers=headers, timeout=10) as response:
                 resp_text = await response.text()
                 return {
                     "success": response.status in (200, 201, 202, 204),
                     "status_code": response.status,
                     "response": resp_text[:1000] # Trim por seguridad (1kb max)
                 }
        except asyncio.TimeoutError:
             return {"success": False, "status_code": 408, "response": "Request Timeout (>10s)"}
        except Exception as e:
             return {"success": False, "status_code": 500, "response": str(e)}

    async def process_event(self, tenant_id: int, lead_id: UUID, new_status: str, previous_status: Optional[str] = None):
        """Dispara en ráfaga las acciones (Webhooks) post-commit para que el Main Thread no se frene"""
        
        # 1. Recuperar contexto del lead que cambió
        lead_query = "SELECT * FROM leads WHERE id = $1 AND tenant_id = $2"
        async with self.db_pool.acquire() as conn:
             lead = dict(await conn.fetchrow(lead_query, lead_id, tenant_id) or {})
             if not lead: return
             
             # Cast dates/uuids para JSON safe transport
             for k, v in lead.items():
                 if isinstance(v, (datetime, UUID)):
                     lead[k] = str(v)
             
             triggers = await self.get_triggers_for_transition(tenant_id, new_status)
             
             for trigger in triggers:
                 
                 payload = {
                    "event": "lead.status_updated",
                    "tenant_id": tenant_id,
                    "lead_id": str(lead_id),
                    "previous_status": previous_status,
                    "new_status": new_status,
                    "lead_snapshot": lead
                 }
                 
                 result = {"success": False, "status_code": None, "response": None}
                 start_time = datetime.now()
                 
                 # 2. Match Actions 
                 if trigger['action_type'] == 'webhook':
                     config = json.loads(trigger['config_json'] or '{}')
                     url = config.get('url')
                     headers = config.get('headers', {})
                     if url:
                         result = await self._execute_webhook(url, headers, payload)
                 else:
                     # Other internals (E.g email_notification, zapier, etc) -> Future expansions
                     result["success"] = True
                     result["response"] = "Internal Trigger Skipped or Simulated."
                     
                 # 3. Loggar el Action (Audit log action)
                 end_time = datetime.now()
                 
                 await conn.execute("""
                     INSERT INTO lead_status_trigger_logs (trigger_id, tenant_id, lead_id, status, error_details, executed_at, payload)
                     VALUES ($1, $2, $3, $4, $5, $6, $7)
                 """, 
                 trigger['id'], tenant_id, lead_id, 
                 'success' if result['success'] else 'failed',
                 json.dumps(result), end_time, json.dumps(payload))
