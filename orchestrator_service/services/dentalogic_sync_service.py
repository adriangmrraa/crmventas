import os
import httpx
import logging
from db import db

logger = logging.getLogger("dentalogic_sync_service")

DENTALOGIC_API_URL = os.getenv("DENTALOGIC_API_URL", "http://localhost:8001")
BRIDGE_API_TOKEN = os.getenv("BRIDGE_API_TOKEN", "super-secret-bridge-token-2026")
DEFAULT_TENANT_ID = int(os.getenv("DENTALOGIC_SYNC_TENANT_ID", "1"))

class DentalogicSyncService:
    async def sync_leads(self):
        """
        Consulta la Bridge API de Dentalogic para obtener nuevos leads (alta intención)
        y los integra en la base de datos de CRM VENTAS.
        """
        logger.info("Iniciando sincronización con Dentalogic Bridge API...")
        try:
            headers = {"X-Bridge-Token": BRIDGE_API_TOKEN}
            url = f"{DENTALOGIC_API_URL}/api/bridge/v1/leads?min_score=5.0&status=new"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=10.0)
                if response.status_code != 200:
                    logger.error(f"Error consultando Dentalogic: {response.text}")
                    return {"status": "error", "message": "Failed to fetch leads"}
                
                data = response.json()
                leads = data.get("leads", [])
                logger.info(f"Se encontraron {len(leads)} leads en Dentalogic para sincronizar.")
                
                synced_count = 0
                for lead in leads:
                    demo_id = lead["id"]
                    phone = lead["phone_number"]
                    email = lead.get("email")
                    
                    # Ignorar si el phone es un visitor ID autogenerado temporal 
                    if phone.startswith("visitor_"):
                        logger.debug(f"Saltando lead anónimo {demo_id}")
                        continue
                        
                    # Insertarlo en CRM VENTAS
                    crm_lead = await db.ensure_lead_exists(
                        tenant_id=DEFAULT_TENANT_ID,
                        phone_number=phone,
                        customer_name="Dentalogic Lead",
                        source="dentalogic_demo"
                    )
                    
                    # Actualizar email o score
                    if email:
                        await db.execute("UPDATE leads SET email = $1 WHERE id = $2", email, crm_lead["id"])
                        
                    # Marcarlo como sincronizado en Dentalogic
                    sync_url = f"{DENTALOGIC_API_URL}/api/bridge/v1/leads/{demo_id}/sync"
                    await client.put(sync_url, headers=headers, timeout=5.0)
                    
                    synced_count += 1
                    
                logger.info(f"Sincronización finalizada. Leads procesados: {synced_count}")
                return {"status": "ok", "synced_count": synced_count}
                
        except Exception as e:
            logger.error(f"Excepción en sync_leads: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

dentalogic_sync_service = DentalogicSyncService()
