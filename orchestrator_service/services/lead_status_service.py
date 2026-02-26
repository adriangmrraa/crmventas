from typing import List, Dict, Optional, Any
from uuid import UUID
import asyncpg
from datetime import datetime
from pydantic import ValidationError

class LeadStatusService:
    """Servicio principal para la gestión de estados y validación de transiciones de Leads"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool

    async def get_statuses(self, tenant_id: int, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """Obtiene estados para un tenant (Tenant Isolation)"""
        active_filter = "" if include_inactive else "AND is_active = true"
        query = f"""
            SELECT id, name, code, description, color, icon, 
                   is_active, is_initial, is_final, sort_order,
                   requires_comment, category, badge_style, metadata
            FROM lead_statuses
            WHERE tenant_id = $1 {active_filter}
            ORDER BY sort_order, name
        """
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, tenant_id)
            return [dict(row) for row in rows]

    async def get_available_transitions(self, tenant_id: int, current_status: Optional[str]) -> List[Dict[str, Any]]:
        """Obtiene las transiciones de estados permitidas desde un estado específico"""
        query = """
            SELECT t.id, t.from_status_code, t.to_status_code,
                   t.label, t.description, t.icon, t.button_style,
                   t.requires_approval, t.approval_role,
                   s_to.name as to_status_name,
                   s_to.color as to_status_color,
                   s_to.icon as to_status_icon
            FROM lead_status_transitions t
            JOIN lead_statuses s_to ON t.tenant_id = s_to.tenant_id 
                AND t.to_status_code = s_to.code
            WHERE t.tenant_id = $1 
                AND t.is_allowed = true
                AND (t.from_status_code = $2 OR t.from_status_code IS NULL)
                AND s_to.is_active = true
            ORDER BY t.from_status_code NULLS LAST, t.label
        """
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, tenant_id, current_status)
            return [dict(row) for row in rows]

    async def validate_transition(self, tenant_id: int, from_status: Optional[str], to_status: str) -> bool:
        """Valida que una transición sea permitida en el modelo base de datos."""
        query = """
            SELECT 1 FROM lead_status_transitions 
            WHERE tenant_id = $1 
            AND (from_status_code = $2 OR from_status_code IS NULL)
            AND to_status_code = $3 
            AND is_allowed = true
        """
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchval(query, tenant_id, from_status, to_status)
            return bool(row)
            
    async def get_status_details(self, tenant_id: int, status_code: str) -> Optional[Dict[str, Any]]:
        """Devuelve los detalles de un estado en específico para chequear condiciones como requests_comment."""
        query = """
            SELECT * FROM lead_statuses WHERE tenant_id = $1 AND code = $2
        """
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, tenant_id, status_code)
            return dict(row) if row else None

    async def change_lead_status(self, lead_id: UUID, tenant_id: int, new_status: str, 
                                 user_id: Optional[UUID], user_name: Optional[str] = None, 
                                 comment: Optional[str] = None, metadata: Optional[Dict] = None,
                                 conn: Optional[asyncpg.Connection] = None) -> Dict[str, Any]:
        """Cambia el estado de un lead con todas las validaciones asertivas y tracking."""
        
        async def _execute_change(connection: asyncpg.Connection):
            # 1. Obtener lead actual (y asegurar Tenant Isolation)
            lead = await connection.fetchrow(
                "SELECT id, status FROM leads WHERE id = $1 AND tenant_id = $2 FOR UPDATE",
                lead_id, tenant_id
            )
            
            if not lead:
                raise ValueError("Lead not found or does not belong to your tenant.")
                
            current_status = lead['status']
            
            if current_status == new_status:
                return {"success": True, "message": "Lead is already in that status."}
                
            # 2. Validar transición y detalle destino
            if not await self.validate_transition(tenant_id, current_status, new_status):
                raise ValueError(f"Transition from '{current_status}' to '{new_status}' is not allowed in this workflow.")
                
            status_params = await self.get_status_details(tenant_id, new_status)
            if not status_params:
                raise ValueError(f"Target status '{new_status}' does not exist or is inactive.")
            
            if status_params.get('requires_comment', False) and not comment:
                raise ValueError(f"Status '{status_params['name']}' requires a comment rationale.")
                
            # 3. Actualizar tabla leads
            await connection.execute("""
                UPDATE leads 
                SET status = $1, 
                    status_changed_at = CURRENT_TIMESTAMP,
                    status_changed_by = $2,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = $3 AND tenant_id = $4
            """, new_status, user_id, lead_id, tenant_id)
            
            # 4. Registrar en el historial de eventos
            await connection.execute("""
                INSERT INTO lead_status_history 
                (lead_id, tenant_id, from_status_code, to_status_code, changed_by_user_id, changed_by_name, comment, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, lead_id, tenant_id, current_status, new_status, user_id, user_name, comment, '{}')
            
            # 5. Fase 5 Automatizaciones: Despachar Action Triggers
            # Import aquí para evitar dependencias cruzadas costosas al startup si LeadAutomationService crece
            from services.lead_automation_service import LeadAutomationService
            automation_service = LeadAutomationService(self.db_pool)
            
            # Lanzarlo via asyncio.create_task garantiza "Fire and Forget"
            import asyncio
            asyncio.create_task(
                automation_service.process_event(
                    tenant_id=tenant_id, 
                    lead_id=lead_id, 
                    new_status=new_status, 
                    previous_status=current_status
                )
            )
            
            return {
                "success": True,
                "lead_id": str(lead_id),
                "from_status": current_status,
                "to_status": new_status
            }
            
        if conn:
            return await _execute_change(conn)
        else:
            async with self.db_pool.acquire() as connection:
                async with connection.transaction():
                    return await _execute_change(connection)

    async def bulk_change_lead_status(self, lead_ids: List[UUID], tenant_id: int, new_status: str,
                                      user_id: Optional[UUID], user_name: Optional[str] = None,
                                      comment: Optional[str] = None) -> Dict[str, Any]:
        """Aplica un cambio global usando Advisory Locks (Prevención de Race Conditions)"""
        results = {"successful": 0, "failed": 0, "errors": []}
        
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                # Advisory Lock for concurrency shielding
                lock_key = hash(f"tenant:{tenant_id}")
                await conn.execute("SELECT pg_advisory_xact_lock($1)", lock_key)
                
                # Check target status validness upfront
                status_params = await self.get_status_details(tenant_id, new_status)
                if not status_params:
                     raise ValueError("Target status does not exist or is inactive.")
                     
                for lead_id in sorted(lead_ids):
                    try:
                        await self.change_lead_status(
                            lead_id=lead_id, tenant_id=tenant_id, new_status=new_status,
                            user_id=user_id, user_name=user_name, comment=comment, conn=conn
                        )
                        results["successful"] += 1
                    except Exception as e:
                        results["failed"] += 1
                        results["errors"].append({"id": str(lead_id), "error": str(e)})

        return results
