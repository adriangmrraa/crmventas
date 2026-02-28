"""
Seller Notification Service
Sistema de notificaciones avanzado para vendedores y CEO
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# Setup logger first
logger = logging.getLogger(__name__)

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, using in-memory fallback")

from sqlalchemy import text

from db import get_db
from config import settings

@dataclass
class Notification:
    """Estructura de una notificación"""
    id: str
    tenant_id: int
    type: str  # 'unanswered', 'hot_lead', 'followup', 'assignment', 'metric_alert'
    title: str
    message: str
    priority: str  # 'low', 'medium', 'high', 'critical'
    recipient_id: str  # User ID que recibe la notificación
    sender_id: Optional[str] = None  # User ID que envía (opcional)
    related_entity_type: Optional[str] = None  # 'conversation', 'lead', 'client'
    related_entity_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    read: bool = False
    created_at: datetime = None
    expires_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.expires_at is None and self.priority in ['low', 'medium']:
            self.expires_at = self.created_at + timedelta(days=7)

class SellerNotificationService:
    """Servicio de notificaciones para sistema de vendedores"""
    
    def __init__(self):
        self.redis_client = None
        self._init_redis()
    
    def _init_redis(self):
        """Inicializar conexión Redis para cache y pub/sub"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis module not available, using in-memory fallback")
            self.redis_client = None
            return
            
        try:
            if getattr(settings, 'REDIS_URL', None):
                self.redis_client = redis.Redis.from_url(
                    settings.REDIS_URL,
                    password=getattr(settings, 'REDIS_PASSWORD', None),
                    decode_responses=True
                )
                logger.info("Redis client initialized from REDIS_URL")
            else:
                logger.warning("No REDIS_URL found in settings, using in-memory fallback")
                self.redis_client = None
        except Exception as e:
            logger.warning(f"Could not connect to Redis: {e}. Using in-memory cache.")
            self.redis_client = None
    
    async def check_unanswered_conversations(self, tenant_id: int) -> List[Notification]:
        """
        Detectar conversaciones sin respuesta por más de 1 hora
        """
        notifications = []
        
        try:
            async with get_db() as db:
                # Buscar conversaciones activas sin respuesta > 1h
                query = text("""
                    SELECT 
                        cm.id as conversation_id,
                        cm.from_number,
                        cm.assigned_seller_id,
                        u.email as seller_email,
                        u.first_name as seller_name,
                        MAX(cm.created_at) as last_message_time,
                        COUNT(cm2.id) as unread_count
                    FROM chat_messages cm
                    LEFT JOIN users u ON cm.assigned_seller_id = u.id
                    LEFT JOIN chat_messages cm2 ON cm2.conversation_id = cm.conversation_id 
                        AND cm2.role = 'user' 
                        AND cm2.read = false
                    WHERE cm.tenant_id = :tenant_id
                        AND cm.assigned_seller_id IS NOT NULL
                        AND cm.created_at > NOW() - INTERVAL '24 hours'
                    GROUP BY cm.conversation_id, cm.from_number, cm.assigned_seller_id, u.email, u.first_name
                    HAVING MAX(cm.created_at) < NOW() - INTERVAL '1 hour'
                        AND COUNT(cm2.id) > 0
                    ORDER BY last_message_time ASC
                    LIMIT 50
                """)
                
                result = await db.execute(query, {"tenant_id": tenant_id})
                rows = result.fetchall()
                
                for row in rows:
                    notification = Notification(
                        id=f"unanswered_{row.conversation_id}_{datetime.utcnow().timestamp()}",
                        tenant_id=tenant_id,
                        type="unanswered",
                        title="Conversación sin respuesta",
                        message=f"La conversación con {row.from_number} no tiene respuesta desde hace más de 1 hora",
                        priority="high",
                        recipient_id=row.assigned_seller_id,
                        related_entity_type="conversation",
                        related_entity_id=row.conversation_id,
                        metadata={
                            "phone": row.from_number,
                            "seller_name": row.seller_name,
                            "unread_count": row.unread_count,
                            "last_message_time": row.last_message_time.isoformat() if row.last_message_time else None
                        }
                    )
                    notifications.append(notification)
                    
                    # Si pasa más de 4 horas, notificar también al CEO
                    if row.last_message_time and datetime.utcnow() - row.last_message_time > timedelta(hours=4):
                        # Buscar CEO del tenant
                        ceo_query = text("""
                            SELECT id, email FROM users 
                            WHERE tenant_id = :tenant_id AND role = 'ceo' AND status = 'active'
                            LIMIT 1
                        """)
                        ceo_result = await db.execute(ceo_query, {"tenant_id": tenant_id})
                        ceo = ceo_result.fetchone()
                        
                        if ceo:
                            ceo_notification = Notification(
                                id=f"unanswered_ceo_{row.conversation_id}_{datetime.utcnow().timestamp()}",
                                tenant_id=tenant_id,
                                type="unanswered",
                                title="Conversación crítica sin respuesta",
                                message=f"Conversación con {row.from_number} sin respuesta por más de 4 horas. Vendedor: {row.seller_name or 'Desconocido'}",
                                priority="critical",
                                recipient_id=ceo.id,
                                sender_id=row.assigned_seller_id,
                                related_entity_type="conversation",
                                related_entity_id=row.conversation_id,
                                metadata={
                                    "phone": row.from_number,
                                    "seller_id": row.assigned_seller_id,
                                    "seller_name": row.seller_name,
                                    "hours_without_response": 4,
                                    "last_message_time": row.last_message_time.isoformat() if row.last_message_time else None
                                }
                            )
                            notifications.append(ceo_notification)
                
                logger.info(f"Found {len(notifications)} unanswered conversations for tenant {tenant_id}")
                
        except Exception as e:
            logger.error(f"Error checking unanswered conversations: {e}")
        
        return notifications
    
    async def detect_hot_leads(self, tenant_id: int) -> List[Notification]:
        """
        Detectar leads calientes (alta probabilidad de conversión)
        """
        notifications = []
        
        try:
            async with get_db() as db:
                # Buscar leads con alta engagement reciente
                query = text("""
                    WITH lead_engagement AS (
                        SELECT 
                            l.id as lead_id,
                            l.first_name,
                            l.last_name,
                            l.phone_number,
                            l.lead_source,
                            l.status,
                            l.assigned_seller_id,
                            l.created_at,
                            COUNT(cm.id) as message_count,
                            MAX(cm.created_at) as last_interaction,
                            CASE 
                                WHEN l.lead_source = 'META_ADS' THEN 1.5
                                WHEN l.lead_source = 'REFERRAL' THEN 1.3
                                ELSE 1.0
                            END as source_multiplier,
                            CASE 
                                WHEN l.status IN ('nuevo', 'contactado', 'calificado') THEN 1.2
                                ELSE 1.0
                            END as status_multiplier
                        FROM leads l
                        LEFT JOIN chat_messages cm ON cm.from_number = l.phone_number 
                            AND cm.tenant_id = l.tenant_id
                            AND cm.created_at > NOW() - INTERVAL '24 hours'
                        WHERE l.tenant_id = :tenant_id
                            AND l.status NOT IN ('cerrado_ganado', 'cerrado_perdido', 'descartado')
                            AND l.created_at > NOW() - INTERVAL '7 days'
                        GROUP BY l.id, l.first_name, l.last_name, l.phone_number, 
                                 l.lead_source, l.status, l.assigned_seller_id, l.created_at
                    ),
                    hot_leads AS (
                        SELECT *,
                            (message_count * source_multiplier * status_multiplier) as hot_score
                        FROM lead_engagement
                        WHERE message_count >= 3
                            AND last_interaction > NOW() - INTERVAL '2 hours'
                        ORDER BY hot_score DESC
                        LIMIT 20
                    )
                    SELECT * FROM hot_leads WHERE hot_score >= 4.0
                """)
                
                result = await db.execute(query, {"tenant_id": tenant_id})
                rows = result.fetchall()
                
                for row in rows:
                    lead_name = f"{row.first_name or ''} {row.last_name or ''}".strip() or row.phone_number
                    
                    # Notificar al vendedor asignado
                    if row.assigned_seller_id:
                        notification = Notification(
                            id=f"hot_lead_{row.lead_id}_{datetime.utcnow().timestamp()}",
                            tenant_id=tenant_id,
                            type="hot_lead",
                            title="🔥 Lead Caliente",
                            message=f"{lead_name} muestra alto interés ({row.message_count} mensajes en 24h)",
                            priority="high",
                            recipient_id=row.assigned_seller_id,
                            related_entity_type="lead",
                            related_entity_id=row.lead_id,
                            metadata={
                                "lead_name": lead_name,
                                "phone": row.phone_number,
                                "lead_source": row.lead_source,
                                "message_count": row.message_count,
                                "hot_score": float(row.hot_score),
                                "last_interaction": row.last_interaction.isoformat() if row.last_interaction else None
                            }
                        )
                        notifications.append(notification)
                    
                    # También notificar al CEO para leads muy calientes
                    if float(row.hot_score) >= 8.0:
                        ceo_query = text("""
                            SELECT id, email FROM users 
                            WHERE tenant_id = :tenant_id AND role = 'ceo' AND status = 'active'
                            LIMIT 1
                        """)
                        ceo_result = await db.execute(ceo_query, {"tenant_id": tenant_id})
                        ceo = ceo_result.fetchone()
                        
                        if ceo:
                            ceo_notification = Notification(
                                id=f"hot_lead_ceo_{row.lead_id}_{datetime.utcnow().timestamp()}",
                                tenant_id=tenant_id,
                                type="hot_lead",
                                title="🔥🔥 Lead Muy Caliente",
                                message=f"{lead_name} ({row.phone_number}) - Score: {row.hot_score:.1f}",
                                priority="critical",
                                recipient_id=ceo.id,
                                related_entity_type="lead",
                                related_entity_id=row.lead_id,
                                metadata={
                                    "lead_name": lead_name,
                                    "phone": row.phone_number,
                                    "lead_source": row.lead_source,
                                    "message_count": row.message_count,
                                    "hot_score": float(row.hot_score),
                                    "assigned_seller_id": row.assigned_seller_id
                                }
                            )
                            notifications.append(ceo_notification)
                
                logger.info(f"Found {len(notifications)} hot leads for tenant {tenant_id}")
                
        except Exception as e:
            logger.error(f"Error detecting hot leads: {e}")
        
        return notifications
    
    async def check_followup_reminders(self, tenant_id: int) -> List[Notification]:
        """
        Verificar conversaciones que necesitan follow-up
        """
        notifications = []
        
        try:
            async with get_db() as db:
                # Buscar conversaciones que necesitan follow-up
                # Basado en última interacción y etapa del lead
                query = text("""
                    WITH conversation_metrics AS (
                        SELECT 
                            cm.conversation_id,
                            cm.from_number,
                            cm.assigned_seller_id,
                            MAX(cm.created_at) as last_interaction,
                            COUNT(DISTINCT DATE(cm.created_at)) as interaction_days,
                            BOOL_OR(l.id IS NOT NULL) as has_lead,
                            MAX(l.status) as lead_status,
                            MAX(l.created_at) as lead_created_at
                        FROM chat_messages cm
                        LEFT JOIN leads l ON l.phone_number = cm.from_number 
                            AND l.tenant_id = cm.tenant_id
                        WHERE cm.tenant_id = :tenant_id
                            AND cm.created_at > NOW() - INTERVAL '30 days'
                            AND cm.assigned_seller_id IS NOT NULL
                        GROUP BY cm.conversation_id, cm.from_number, cm.assigned_seller_id
                    ),
                    followup_candidates AS (
                        SELECT *,
                            CASE 
                                WHEN has_lead AND lead_status IN ('contactado', 'calificado') 
                                    AND last_interaction < NOW() - INTERVAL '2 days' THEN 'high'
                                WHEN has_lead AND lead_status = 'nuevo'
                                    AND last_interaction < NOW() - INTERVAL '1 day' THEN 'medium'
                                WHEN NOT has_lead 
                                    AND last_interaction < NOW() - INTERVAL '3 days' THEN 'low'
                                ELSE NULL
                            END as followup_priority
                        FROM conversation_metrics
                        WHERE last_interaction < NOW() - INTERVAL '1 day'
                    )
                    SELECT * FROM followup_candidates 
                    WHERE followup_priority IS NOT NULL
                    ORDER BY last_interaction ASC
                    LIMIT 50
                """)
                
                result = await db.execute(query, {"tenant_id": tenant_id})
                rows = result.fetchall()
                
                for row in rows:
                    days_since = (datetime.utcnow() - row.last_interaction).days
                    
                    notification = Notification(
                        id=f"followup_{row.conversation_id}_{datetime.utcnow().timestamp()}",
                        tenant_id=tenant_id,
                        type="followup",
                        title="📅 Recordatorio de Follow-up",
                        message=f"Conversación con {row.from_number} - {days_since} día(s) sin contacto",
                        priority=row.followup_priority or "medium",
                        recipient_id=row.assigned_seller_id,
                        related_entity_type="conversation",
                        related_entity_id=row.conversation_id,
                        metadata={
                            "phone": row.from_number,
                            "days_since_last_contact": days_since,
                            "has_lead": row.has_lead,
                            "lead_status": row.lead_status,
                            "interaction_days": row.interaction_days
                        }
                    )
                    notifications.append(notification)
                
                logger.info(f"Found {len(notifications)} follow-up reminders for tenant {tenant_id}")
                
        except Exception as e:
            logger.error(f"Error checking follow-up reminders: {e}")
        
        return notifications
    
    async def check_performance_alerts(self, tenant_id: int) -> List[Notification]:
        """
        Alertas basadas en métricas de performance
        """
        notifications = []
        
        try:
            async with get_db() as db:
                # Buscar vendedores con métricas bajas
                query = text("""
                    SELECT 
                        sm.seller_id,
                        u.first_name,
                        u.last_name,
                        u.email,
                        sm.response_time_avg,
                        sm.conversion_rate,
                        sm.active_conversations,
                        sm.updated_at
                    FROM seller_metrics sm
                    JOIN users u ON sm.seller_id = u.id
                    WHERE sm.tenant_id = :tenant_id
                        AND sm.period = 'today'
                        AND sm.updated_at > NOW() - INTERVAL '2 hours'
                    ORDER BY sm.updated_at DESC
                """)
                
                result = await db.execute(query, {"tenant_id": tenant_id})
                rows = result.fetchall()
                
                for row in rows:
                    alerts = []
                    
                    # Check response time
                    if row.response_time_avg and row.response_time_avg > 30:  # > 30 minutos
                        alerts.append(f"Tiempo de respuesta alto: {row.response_time_avg:.1f} min")
                    
                    # Check conversion rate
                    if row.conversion_rate and row.conversion_rate < 0.1:  # < 10%
                        alerts.append(f"Tasa de conversión baja: {row.conversion_rate*100:.1f}%")
                    
                    # Check activity
                    if row.active_conversations and row.active_conversations < 3:
                        alerts.append(f"Conversaciones activas bajas: {row.active_conversations}")
                    
                    if alerts:
                        seller_name = f"{row.first_name or ''} {row.last_name or ''}".strip() or row.email
                        
                        # Notificar al vendedor
                        notification = Notification(
                            id=f"performance_{row.seller_id}_{datetime.utcnow().timestamp()}",
                            tenant_id=tenant_id,
                            type="performance_alert",
                            title="📊 Alerta de Performance",
                            message=f"Áreas a mejorar: {', '.join(alerts)}",
                            priority="medium",
                            recipient_id=row.seller_id,
                            metadata={
                                "seller_name": seller_name,
                                "alerts": alerts,
                                "response_time": float(row.response_time_avg) if row.response_time_avg else None,
                                "conversion_rate": float(row.conversion_rate) if row.conversion_rate else None,
                                "active_conversations": row.active_conversations
                            }
                        )
                        notifications.append(notification)
                        
                        # Notificar al CEO para alertas críticas
                        if row.response_time_avg and row.response_time_avg > 60:  # > 1 hora
                            ceo_query = text("""
                                SELECT id, email FROM users 
                                WHERE tenant_id = :tenant_id AND role = 'ceo' AND status = 'active'
                                LIMIT 1
                            """)
                            ceo_result = await db.execute(ceo_query, {"tenant_id": tenant_id})
                            ceo = ceo_result.fetchone()
                            
                            if ceo:
                                ceo_notification = Notification(
                                    id=f"performance_ceo_{row.seller_id}_{datetime.utcnow().timestamp()}",
                                    tenant_id=tenant_id,
                                    type="performance_alert",
                                    title="🚨 Performance Crítica",
                                    message=f"{seller_name}: Tiempo de respuesta > 1 hora ({row.response_time_avg:.1f} min)",
                                    priority="critical",
                                    recipient_id=ceo.id,
                                    sender_id=row.seller_id,
                                    metadata={
                                        "seller_name": seller_name,
                                        "seller_id": row.seller_id,
                                        "response_time": float(row.response_time_avg),
                                        "metric": "response_time",
                                        "threshold": 60
                                    }
                                )
                                notifications.append(ceo_notification)
                
                logger.info(f"Found {len(notifications)} performance alerts for tenant {tenant_id}")
                
        except Exception as e:
            logger.error(f"Error checking performance alerts: {e}")
        
        return notifications
    
    async def run_all_checks(self, tenant_id: int) -> List[Notification]:
        """
        Ejecutar todas las verificaciones de notificaciones
        """
        all_notifications = []
        
        try:
            # Ejecutar checks en paralelo
            tasks = [
                self.check_unanswered_conversations(tenant_id),
                self.detect_hot_leads(tenant_id),
                self.check_followup_reminders(tenant_id),
                self.check_performance_alerts(tenant_id)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Error in notification check: {result}")
                elif isinstance(result, list):
                    all_notifications.extend(result)
            
            # Guardar notificaciones en base de datos
            if all_notifications:
                await self.save_notifications(all_notifications)
                
                # Enviar notificaciones en tiempo real via Redis/Socket.IO
                await self.broadcast_notifications(all_notifications)
            
            logger.info(f"Generated {len(all_notifications)} total notifications for tenant {tenant_id}")
            
        except Exception as e:
            logger.error(f"Error running notification checks: {e}")
        
        return all_notifications
    
    async def save_notifications(self, notifications: List[Notification]):
        """
        Guardar notificaciones en base de datos con límite de 1000 por usuario
        """
        if not notifications:
            return
        
        try:
            async with get_db() as db:
                for notification in notifications:
                    # Insertar en tabla de notificaciones
                    query = text("""
                        INSERT INTO notifications (
                            id, tenant_id, type, title, message, priority, recipient_id, sender_id,
                            related_entity_type, related_entity_id, metadata, read,
                            created_at, expires_at
                        ) VALUES (
                            :id, :tenant_id, :type, :title, :message, :priority, :recipient_id, :sender_id,
                            :related_entity_type, :related_entity_id, :metadata, :read,
                            :created_at, :expires_at
                        )
                        ON CONFLICT (id) DO UPDATE SET
                            read = EXCLUDED.read,
                            expires_at = EXCLUDED.expires_at
                    """)
                    
                    await db.execute(query, {
                        "id": notification.id,
                        "tenant_id": notification.tenant_id,
                        "type": notification.type,
                        "title": notification.title,
                        "message": notification.message,
                        "priority": notification.priority,
                        "recipient_id": notification.recipient_id,
                        "sender_id": notification.sender_id,
                        "related_entity_type": notification.related_entity_type,
                        "related_entity_id": notification.related_entity_id,
                        "metadata": json.dumps(notification.metadata) if notification.metadata else None,
                        "read": notification.read,
                        "created_at": notification.created_at,
                        "expires_at": notification.expires_at
                    })

                    # Enforce 1000 message limit (FIFO)
                    limit_query = text("""
                        DELETE FROM notifications
                        WHERE id IN (
                            SELECT id FROM notifications
                            WHERE recipient_id = :user_id
                            ORDER BY created_at DESC
                            OFFSET 1000
                        )
                    """)
                    await db.execute(limit_query, {"user_id": notification.recipient_id})
                
                await db.commit()
                logger.info(f"Saved {len(notifications)} notifications to database (FIFO check applied)")
                
        except Exception as e:
            logger.error(f"Error saving notifications: {e}")
    
    async def broadcast_notifications(self, notifications: List[Notification]):
        """
        Enviar notificaciones en tiempo real via Redis pub/sub
        """
        if not notifications or not self.redis_client:
            return
        
        try:
            # Agrupar notificaciones por recipient
            notifications_by_recipient = {}
            for notification in notifications:
                if notification.recipient_id not in notifications_by_recipient:
                    notifications_by_recipient[notification.recipient_id] = []
                notifications_by_recipient[notification.recipient_id].append(notification)
            
            # Enviar a cada recipient
            for recipient_id, recipient_notifications in notifications_by_recipient.items():
                channel = f"notifications:{recipient_id}"
                message = {
                    "type": "new_notifications",
                    "count": len(recipient_notifications),
                    "notifications": [
                        {
                            "id": n.id,
                            "type": n.type,
                            "title": n.title,
                            "message": n.message,
                            "priority": n.priority,
                            "created_at": n.created_at.isoformat()
                        }
                        for n in recipient_notifications[:5]  # Limitar para no saturar
                    ]
                }
                
                await self.redis_client.publish(channel, json.dumps(message))
                logger.debug(f"Published notifications to channel {channel}")
            
            logger.info(f"Broadcasted notifications to {len(notifications_by_recipient)} recipients")
            
        except Exception as e:
            logger.error(f"Error broadcasting notifications: {e}")
    
    async def get_user_notifications(
        self, 
        user_id: str, 
        role: str = 'setter',
        tenant_id: int = 1,
        limit: int = 50, 
        offset: int = 0,
        unread_only: bool = False,
        filter_seller_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Obtener notificaciones para un usuario con soporte para CEO global view y paginación
        """
        try:
            async with get_db() as db:
                # Si es CEO, puede ver todas las notificaciones del tenant
                if role == 'ceo':
                    where_clause = "WHERE tenant_id = :tenant_id"
                    params = {"tenant_id": tenant_id, "limit": limit, "offset": offset}
                    
                    if filter_seller_id:
                        where_clause += " AND recipient_id = :filter_seller_id"
                        params["filter_seller_id"] = filter_seller_id
                else:
                    where_clause = "WHERE recipient_id = :user_id"
                    params = {"user_id": user_id, "limit": limit, "offset": offset}
                
                if unread_only:
                    where_clause += " AND read = false"
                
                query = text(f"""
                    SELECT 
                        id, type, title, message, priority, recipient_id, sender_id,
                        related_entity_type, related_entity_id, metadata, read,
                        created_at, expires_at
                    FROM notifications
                    {where_clause}
                    ORDER BY 
                        CASE priority
                            WHEN 'critical' THEN 1
                            WHEN 'high' THEN 2
                            WHEN 'medium' THEN 3
                            WHEN 'low' THEN 4
                        END,
                        created_at DESC
                    LIMIT :limit OFFSET :offset
                """)
                
                result = await db.execute(query, params)
                rows = result.fetchall()
                
                notifications = []
                for row in rows:
                    notifications.append({
                        "id": row.id,
                        "type": row.type,
                        "title": row.title,
                        "message": row.message,
                        "priority": row.priority,
                        "recipient_id": row.recipient_id,
                        "sender_id": row.sender_id,
                        "related_entity_type": row.related_entity_type,
                        "related_entity_id": row.related_entity_id,
                        "metadata": json.loads(row.metadata) if row.metadata else {},
                        "read": row.read,
                        "created_at": row.created_at.isoformat() if row.created_at else None,
                        "expires_at": row.expires_at.isoformat() if row.expires_at else None
                    })
                
                return notifications
                
        except Exception as e:
            logger.error(f"Error getting user notifications: {e}")
            return []
    
    async def mark_as_read(self, notification_id: str, user_id: str) -> bool:
        """
        Marcar notificación como leída
        """
        try:
            async with get_db() as db:
                query = text("""
                    UPDATE notifications 
                    SET read = true 
                    WHERE id = :notification_id 
                        AND recipient_id = :user_id
                    RETURNING id
                """)
                
                result = await db.execute(query, {
                    "notification_id": notification_id,
                    "user_id": user_id
                })
                
                await db.commit()
                updated = result.fetchone() is not None
                
                if updated:
                    logger.info(f"Marked notification {notification_id} as read for user {user_id}")
                    
                    # Notificar via Redis que se marcó como leída
                    if self.redis_client:
                        channel = f"notifications:{user_id}"
                        message = {
                            "type": "notification_read",
                            "notification_id": notification_id
                        }
                        await self.redis_client.publish(channel, json.dumps(message))
                
                return updated
                
        except Exception as e:
            logger.error(f"Error marking notification as read: {e}")
            return False
    
    async def mark_all_as_read(self, user_id: str) -> int:
        """
        Marcar todas las notificaciones de un usuario como leídas
        """
        try:
            async with get_db() as db:
                query = text("""
                    UPDATE notifications 
                    SET read = true 
                    WHERE recipient_id = :user_id 
                        AND read = false
                    RETURNING COUNT(*) as count
                """)
                
                result = await db.execute(query, {"user_id": user_id})
                await db.commit()
                
                row = result.fetchone()
                count = row.count if row else 0
                
                if count > 0:
                    logger.info(f"Marked {count} notifications as read for user {user_id}")
                    
                    # Notificar via Redis
                    if self.redis_client:
                        channel = f"notifications:{user_id}"
                        message = {
                            "type": "all_notifications_read",
                            "count": count
                        }
                        await self.redis_client.publish(channel, json.dumps(message))
                
                return count
                
        except Exception as e:
            logger.error(f"Error marking all notifications as read: {e}")
            return 0
    
    async def delete_expired_notifications(self) -> int:
        """
        Eliminar notificaciones expiradas
        """
        try:
            async with get_db() as db:
                query = text("""
                    DELETE FROM notifications 
                    WHERE expires_at IS NOT NULL 
                        AND expires_at < NOW()
                    RETURNING COUNT(*) as count
                """)
                
                result = await db.execute(query)
                await db.commit()
                
                row = result.fetchone()
                count = row.count if row else 0
                
                if count > 0:
                    logger.info(f"Deleted {count} expired notifications")
                
                return count
                
        except Exception as e:
            logger.error(f"Error deleting expired notifications: {e}")
            return 0
    
    async def create_daily_report_notification(self, tenant_id: int, ceo_id: str, metrics: Dict) -> Optional[Notification]:
        """
        Crear notificación de reporte diario para CEO
        """
        try:
            # Obtener resumen del día
            async with get_db() as db:
                query = text("""
                    SELECT 
                        COUNT(DISTINCT cm.conversation_id) as total_conversations,
                        COUNT(DISTINCT CASE WHEN cm.created_at > NOW() - INTERVAL '24 hours' THEN cm.conversation_id END) as today_conversations,
                        COUNT(DISTINCT l.id) as new_leads,
                        COUNT(DISTINCT CASE WHEN l.status = 'cerrado_ganado' THEN l.id END) as won_leads,
                        COALESCE(AVG(sm.response_time_avg), 0) as avg_response_time
                    FROM chat_messages cm
                    LEFT JOIN leads l ON l.tenant_id = cm.tenant_id 
                        AND l.created_at > NOW() - INTERVAL '24 hours'
                    LEFT JOIN seller_metrics sm ON sm.tenant_id = cm.tenant_id 
                        AND sm.period = 'today'
                    WHERE cm.tenant_id = :tenant_id
                        AND cm.created_at > NOW() - INTERVAL '24 hours'
                """)
                
                result = await db.execute(query, {"tenant_id": tenant_id})
                row = result.fetchone()
                
                if row:
                    message = f"📊 Reporte Diario: {row.today_conversations} conversaciones hoy, {row.new_leads} nuevos leads, {row.won_leads} ganados. Tiempo respuesta: {row.avg_response_time:.1f} min"
                    
                    notification = Notification(
                        id=f"daily_report_{tenant_id}_{datetime.utcnow().strftime('%Y%m%d')}",
                        tenant_id=tenant_id,
                        type="metric_alert",
                        title="📈 Reporte Diario CEO",
                        message=message,
                        priority="medium",
                        recipient_id=ceo_id,
                        metadata={
                            "tenant_id": tenant_id,
                            "date": datetime.utcnow().strftime('%Y-%m-%d'),
                            "today_conversations": row.today_conversations,
                            "new_leads": row.new_leads,
                            "won_leads": row.won_leads,
                            "avg_response_time": float(row.avg_response_time),
                            "total_conversations": row.total_conversations
                        }
                    )
                    
                    # Guardar notificación
                    await self.save_notifications([notification])
                    
                    return notification
                    
        except Exception as e:
            logger.error(f"Error creating daily report notification: {e}")
        
        return None

# Instancia global del servicio
notification_service = SellerNotificationService()