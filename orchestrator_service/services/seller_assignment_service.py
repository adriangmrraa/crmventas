"""
Service for managing seller assignments to conversations and leads
"""
import logging
from typing import Optional, Dict, List, Any
from uuid import UUID
from datetime import datetime, timedelta
from db import db
from core.security import get_resolved_tenant_id
from services.seller_notification_service import seller_notification_service, Notification

logger = logging.getLogger(__name__)

class SellerAssignmentService:
    
    async def assign_conversation_to_seller(
        self,
        phone: str,
        seller_id: UUID,
        assigned_by: UUID,
        tenant_id: int,
        source: str = "manual"
    ) -> Dict:
        """
        Assign a conversation to a seller
        Returns: {"success": bool, "message": str, "assignment": dict}
        """
        try:
            # 1. Validate seller exists and is active
            seller = await db.fetchrow("""
                SELECT id, role, status FROM users 
                WHERE id = $1 AND tenant_id = $2 AND status = 'active'
            """, seller_id, tenant_id)
            
            if not seller:
                return {"success": False, "message": "Seller not found or inactive"}
            
            # 2. Check if conversation exists (get latest chat message for this phone)
            conversation = await db.fetchrow("""
                SELECT id, tenant_id, assigned_seller_id 
                FROM chat_messages 
                WHERE from_number = $1 AND tenant_id = $2
                ORDER BY created_at DESC 
                LIMIT 1
            """, phone, tenant_id)
            
            if not conversation:
                return {"success": False, "message": "No conversation found for this phone number"}
            
            # 3. Update all chat messages for this conversation with assignment
            await db.execute("""
                UPDATE chat_messages 
                SET assigned_seller_id = $1, 
                    assigned_at = NOW(), 
                    assigned_by = $2,
                    assignment_source = $3
                WHERE from_number = $4 AND tenant_id = $5
            """, seller_id, assigned_by, source, phone, tenant_id)
            
            # 4. Update lead assignment if exists
            await db.execute("""
                UPDATE leads 
                SET assigned_seller_id = $1,
                    initial_assignment_source = $2,
                    assignment_history = COALESCE(assignment_history, '[]') || jsonb_build_array(
                        jsonb_build_object(
                            'seller_id', $1::text,
                            'assigned_at', NOW()::text,
                            'assigned_by', $3::text,
                            'source', $2
                        )
                    )
                WHERE phone_number = $4 AND tenant_id = $5
            """, seller_id, source, str(assigned_by), phone, tenant_id)
            
            # 5. Notify seller and CEO
            await self._notify_assignment(phone, seller_id, seller.get('first_name', 'Vendedor'), tenant_id, source)
            
            # 6. Update seller metrics
            await self._update_seller_metrics(seller_id, tenant_id)
            
            # 7. Log assignment event
            await db.execute("""
                INSERT INTO system_events 
                (tenant_id, user_id, event_type, severity, message, payload)
                VALUES ($1, $2, 'seller_assignment', 'info', 
                        'Conversation assigned to seller',
                        jsonb_build_object(
                            'phone', $3,
                            'seller_id', $4::text,
                            'assigned_by', $5::text,
                            'source', $6
                        ))
            """, tenant_id, assigned_by, phone, str(seller_id), str(assigned_by), source)
            
            return {
                "success": True,
                "message": f"Conversation assigned to seller successfully",
                "assignment": {
                    "seller_id": str(seller_id),
                    "assigned_at": datetime.now().isoformat(),
                    "assigned_by": str(assigned_by),
                    "source": source,
                    "phone": phone
                }
            }
            
        except Exception as e:
            logger.error(f"Error assigning conversation to seller: {e}")
            return {"success": False, "message": f"Error: {str(e)}"}
    
    async def get_conversation_assignment(
        self,
        phone: str,
        tenant_id: int
    ) -> Optional[Dict]:
        """
        Get current assignment for a conversation
        """
        try:
            assignment = await db.fetchrow("""
                SELECT 
                    cm.assigned_seller_id,
                    cm.assigned_at,
                    cm.assigned_by,
                    cm.assignment_source,
                    u.first_name as seller_first_name,
                    u.last_name as seller_last_name,
                    u.role as seller_role,
                    assigned_by_user.first_name as assigned_by_first_name,
                    assigned_by_user.last_name as assigned_by_last_name
                FROM chat_messages cm
                LEFT JOIN users u ON cm.assigned_seller_id = u.id
                LEFT JOIN users assigned_by_user ON cm.assigned_by = assigned_by_user.id
                WHERE cm.from_number = $1 AND cm.tenant_id = $2
                AND cm.assigned_seller_id IS NOT NULL
                ORDER BY cm.assigned_at DESC
                LIMIT 1
            """, phone, tenant_id)
            
            if assignment:
                return dict(assignment)
            return None
            
        except Exception as e:
            logger.error(f"Error getting conversation assignment: {e}")
            return None
    
    async def get_available_sellers(
        self,
        tenant_id: int,
        role_filter: Optional[str] = None
    ) -> List[Dict]:
        """
        Get list of available sellers for assignment
        """
        try:
            query = """
                SELECT 
                    u.id,
                    u.first_name,
                    u.last_name,
                    u.role,
                    u.email,
                    COALESCE(sm.active_conversations, 0) as active_conversations,
                    COALESCE(sm.conversion_rate, 0) as conversion_rate
                FROM users u
                LEFT JOIN seller_metrics sm ON u.id = sm.seller_id 
                    AND sm.tenant_id = $1 
                    AND sm.metrics_period_start >= NOW() - INTERVAL '7 days'
                WHERE u.tenant_id = $1 
                AND u.status = 'active'
                AND u.role IN ('setter', 'closer', 'professional', 'ceo')
                -- Ensure they have a record in sellers table (B-01 requirement)
                AND EXISTS (SELECT 1 FROM sellers s WHERE s.user_id = u.id)
            """
            
            params = [tenant_id]
            
            if role_filter:
                query += " AND u.role = $2"
                params.append(role_filter)
            
            query += " ORDER BY u.role, u.first_name"
            
            sellers = await db.fetch(query, *params)
            return [dict(seller) for seller in sellers]
            
        except Exception as e:
            logger.error(f"Error getting available sellers: {e}")
            return []
    
    async def auto_assign_conversation(
        self,
        phone: str,
        tenant_id: int,
        lead_source: Optional[str] = None
    ) -> Dict:
        """
        Automatically assign conversation based on rules
        """
        try:
            # 1. Get active assignment rules for this tenant
            rules = await db.fetch("""
                SELECT * FROM assignment_rules 
                WHERE tenant_id = $1 AND is_active = TRUE
                ORDER BY priority ASC
            """, tenant_id)
            
            if not rules:
                # No rules, assign to CEO if exists
                ceo = await db.fetchrow("""
                    SELECT id FROM users 
                    WHERE tenant_id = $1 AND role = 'ceo' AND status = 'active'
                    LIMIT 1
                """, tenant_id)
                
                if ceo:
                    return await self.assign_conversation_to_seller(
                        phone, ceo['id'], UUID(int=0), tenant_id, "auto_ceo_fallback"
                    )
                return {"success": False, "message": "No assignment rules and no CEO found"}
            
            # 2. Apply rules in priority order
            for rule in rules:
                seller_id = await self._apply_assignment_rule(rule, tenant_id, lead_source)
                if seller_id:
                    return await self.assign_conversation_to_seller(
                        phone, seller_id, UUID(int=0), tenant_id, f"auto_{rule['rule_type']}"
                    )
            
            # 3. Fallback to round-robin among all active sellers
            sellers = await self.get_available_sellers(tenant_id)
            if sellers:
                # Simple round-robin: get seller with fewest active conversations
                sellers_sorted = sorted(sellers, key=lambda x: x.get('active_conversations', 0))
                return await self.assign_conversation_to_seller(
                    phone, sellers_sorted[0]['id'], UUID(int=0), tenant_id, "auto_round_robin"
                )
            
            return {"success": False, "message": "No available sellers for assignment"}
            
        except Exception as e:
            logger.error(f"Error in auto assignment: {e}")
            return {"success": False, "message": f"Auto assignment error: {str(e)}"}
    
    async def _apply_assignment_rule(
        self,
        rule: Dict,
        tenant_id: int,
        lead_source: Optional[str] = None
    ) -> Optional[UUID]:
        """
        Apply a specific assignment rule and return seller_id if match
        """
        try:
            rule_type = rule['rule_type']
            config = rule.get('config', {})
            
            # Check filters
            if not self._check_rule_filters(rule, lead_source):
                return None
            
            if rule_type == 'round_robin':
                return await self._round_robin_assignment(tenant_id, config)
            elif rule_type == 'performance':
                return await self._performance_based_assignment(tenant_id, config)
            elif rule_type == 'specialty':
                return await self._specialty_based_assignment(tenant_id, config, lead_source)
            elif rule_type == 'load_balance':
                return await self._load_balance_assignment(tenant_id, config)
            
            return None
            
        except Exception as e:
            logger.error(f"Error applying rule {rule.get('rule_name')}: {e}")
            return None
    
    async def _round_robin_assignment(
        self,
        tenant_id: int,
        config: Dict
    ) -> Optional[UUID]:
        """Round-robin assignment among available sellers"""
        sellers = await self.get_available_sellers(tenant_id)
        if not sellers:
            return None
        
        # Get seller with oldest assignment (or never assigned)
        seller_with_oldest = await db.fetchrow("""
            SELECT u.id, MAX(cm.assigned_at) as last_assigned
            FROM users u
            LEFT JOIN chat_messages cm ON u.id = cm.assigned_seller_id
            WHERE u.tenant_id = $1 
            AND u.status = 'active'
            AND u.role IN ('setter', 'closer', 'professional')
            GROUP BY u.id
            ORDER BY last_assigned NULLS FIRST
            LIMIT 1
        """, tenant_id)
        
        if seller_with_oldest:
            return seller_with_oldest['id']
        
        # Fallback to first seller
        return sellers[0]['id']
    
    async def _performance_based_assignment(
        self,
        tenant_id: int,
        config: Dict
    ) -> Optional[UUID]:
        """Assign to seller with best performance metrics"""
        seller = await db.fetchrow("""
            SELECT sm.seller_id
            FROM seller_metrics sm
            JOIN users u ON sm.seller_id = u.id
            WHERE sm.tenant_id = $1
            AND u.status = 'active'
            AND sm.metrics_period_start >= NOW() - INTERVAL '30 days'
            ORDER BY sm.conversion_rate DESC NULLS LAST,
                     sm.leads_converted DESC
            LIMIT 1
        """, tenant_id)
        
        return seller['seller_id'] if seller else None
    
    async def _specialty_based_assignment(
        self,
        tenant_id: int,
        config: Dict,
        lead_source: Optional[str]
    ) -> Optional[UUID]:
        """Assign based on seller specialty"""
        # Default: setters for new leads, closers for warm leads
        if lead_source == 'META_ADS' or not lead_source:
            # New leads go to setters
            seller = await db.fetchrow("""
                SELECT id FROM users 
                WHERE tenant_id = $1 
                AND role = 'setter'
                AND status = 'active'
                LIMIT 1
            """, tenant_id)
            return seller['id'] if seller else None
        else:
            # Other leads go to closers
            seller = await db.fetchrow("""
                SELECT id FROM users 
                WHERE tenant_id = $1 
                AND role = 'closer'
                AND status = 'active'
                LIMIT 1
            """, tenant_id)
            return seller['id'] if seller else None
    
    async def _load_balance_assignment(
        self,
        tenant_id: int,
        config: Dict
    ) -> Optional[UUID]:
        """Assign to seller with lightest load"""
        seller = await db.fetchrow("""
            SELECT u.id, COALESCE(sm.active_conversations, 0) as load
            FROM users u
            LEFT JOIN seller_metrics sm ON u.id = sm.seller_id 
                AND sm.tenant_id = $1
            WHERE u.tenant_id = $1 
            AND u.status = 'active'
            AND u.role IN ('setter', 'closer', 'professional')
            ORDER BY load ASC
            LIMIT 1
        """, tenant_id)
        
        return seller['id'] if seller else None
    
    def _check_rule_filters(
        self,
        rule: Dict,
        lead_source: Optional[str]
    ) -> bool:
        """Check if rule filters match the lead"""
        apply_to_source = rule.get('apply_to_lead_source')
        if apply_to_source and lead_source:
            if lead_source not in apply_to_source:
                return False
        
        # Add more filter checks as needed
        return True
    
    async def _update_seller_metrics(
        self,
        seller_id: UUID,
        tenant_id: int
    ):
        """Update seller metrics after assignment"""
        try:
            # Calculate active conversations
            active_convs = await db.fetchval("""
                SELECT COUNT(DISTINCT from_number)
                FROM chat_messages
                WHERE assigned_seller_id = $1 
                AND tenant_id = $2
                AND assigned_at >= NOW() - INTERVAL '24 hours'
            """, seller_id, tenant_id)
            
            # Update or insert metrics
            await db.execute("""
                INSERT INTO seller_metrics 
                (seller_id, tenant_id, active_conversations, metrics_period_start, metrics_period_end)
                VALUES ($1, $2, $3, DATE_TRUNC('day', NOW()), DATE_TRUNC('day', NOW()) + INTERVAL '1 day')
                ON CONFLICT (seller_id, tenant_id, metrics_period_start) 
                DO UPDATE SET 
                    active_conversations = EXCLUDED.active_conversations,
                    metrics_calculated_at = NOW()
            """, seller_id, tenant_id, active_convs)
            
        except Exception as e:
            logger.error(f"Error updating seller metrics: {e}")
    
    async def get_seller_conversations(
        self,
        seller_id: UUID,
        tenant_id: int,
        active_only: bool = True
    ) -> List[Dict]:
        """Get all conversations assigned to a seller"""
        try:
            query = """
                SELECT DISTINCT 
                    cm.from_number as phone,
                    MAX(cm.assigned_at) as last_assigned,
                    COUNT(cm.id) as message_count,
                    l.first_name,
                    l.last_name,
                    l.status as lead_status
                FROM chat_messages cm
                LEFT JOIN leads l ON cm.from_number = l.phone_number AND cm.tenant_id = l.tenant_id
                WHERE cm.assigned_seller_id = $1 
                AND cm.tenant_id = $2
            """
            
            if active_only:
                query += " AND cm.assigned_at >= NOW() - INTERVAL '7 days'"
            
            query += """
                GROUP BY cm.from_number, l.first_name, l.last_name, l.status
                ORDER BY MAX(cm.assigned_at) DESC
            """
            
            conversations = await db.fetch(query, seller_id, tenant_id)
            return [dict(conv) for conv in conversations]
            
        except Exception as e:
            logger.error(f"Error getting seller conversations: {e}")
            return []
    
    async def reassign_conversation(
        self,
        phone: str,
        new_seller_id: UUID,
        reassigned_by: UUID,
        tenant_id: int,
        reason: Optional[str] = None
    ) -> Dict:
        """Reassign conversation to a different seller"""
        try:
            # Get current assignment
            current = await self.get_conversation_assignment(phone, tenant_id)
            
            # Assign to new seller
            result = await self.assign_conversation_to_seller(
                phone, new_seller_id, reassigned_by, tenant_id, "reassignment"
            )
            
            if result['success'] and current and current.get('assigned_seller_id'):
                # Log reassignment event
                await db.execute("""
                    INSERT INTO system_events 
                    (tenant_id, user_id, event_type, severity, message, payload)
                    VALUES ($1, $2, 'seller_reassignment', 'info', 
                            'Conversation reassigned to different seller',
                            jsonb_build_object(
                                'phone', $3,
                                'from_seller_id', $4,
                                'to_seller_id', $5::text,
                                'reassigned_by', $6::text,
                                'reason', $7
                            ))
                """, tenant_id, reassigned_by, phone, 
                   str(current['assigned_seller_id']), str(new_seller_id), 
                   str(reassigned_by), reason or "")
            
            return result
            
        except Exception as e:
            logger.error(f"Error reassigning conversation: {e}")
            return {"success": False, "message": f"Error: {str(e)}"}

    async def _notify_assignment(self, phone: str, seller_id: UUID, seller_name: str, tenant_id: int, source: str):
        """
        Send notification to the assigned seller and a global copy to the CEO.
        """
        try:
            from datetime import datetime
            timestamp = datetime.utcnow().timestamp()
            
            # 1. Notification for the Seller
            seller_notif = Notification(
                id=f"assign_{phone}_{seller_id}_{timestamp}",
                tenant_id=tenant_id,
                type="assignment",
                title="🔔 Nuevo Lead Asignado",
                message=f"Se te ha asignado un nuevo lead ({phone}) vía {source}",
                priority="high",
                recipient_id=str(seller_id),
                related_entity_type="conversation",
                related_entity_id=phone,
                metadata={"phone": phone, "source": source}
            )
            
            # 2. Notification for the CEO (Global Visibility)
            ceo = await db.fetchrow("SELECT id FROM users WHERE tenant_id = $1 AND role = 'ceo' AND status = 'active' LIMIT 1", tenant_id)
            notifications = [seller_notif]
            
            if ceo and str(ceo['id']) != str(seller_id):
                ceo_notif = Notification(
                    id=f"assign_ceo_{phone}_{seller_id}_{timestamp}",
                    tenant_id=tenant_id,
                    type="assignment",
                    title="📢 Nueva Asignación (Global)",
                    message=f"Lead {phone} asignado a {seller_name}",
                    priority="medium",
                    recipient_id=str(ceo['id']),
                    related_entity_type="conversation",
                    related_entity_id=phone,
                    metadata={"phone": phone, "seller_id": str(seller_id), "seller_name": seller_name}
                )
                notifications.append(ceo_notif)
            
            # Save and Broadcast
            await seller_notification_service.save_notifications(notifications)
            await seller_notification_service.broadcast_notifications(notifications)
            
        except Exception as e:
            logger.error(f"Error triggering assignment notifications: {e}")

# Singleton instance
seller_assignment_service = SellerAssignmentService()