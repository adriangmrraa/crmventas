"""
Socket.IO Integration for Notifications
Real-time notification delivery via WebSockets
"""

import logging
import sys
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)

from .socket_manager import sio

# Importación de notification_service - manejar diferentes contextos
notification_service = None

try:
    # Try absolute import first (when running from orchestrator_service root)
    from services.seller_notification_service import notification_service as ns
    notification_service = ns
    logger.info("✅ Notification service imported via absolute path")
except ImportError:
    try:
        # Try relative import (when running from core/ directory)
        from services.seller_notification_service import notification_service as ns
        notification_service = ns
        logger.info("✅ Notification service imported via relative path")
    except ImportError:
        try:
            # Last resort - import with full path
            services_path = os.path.join(os.path.dirname(__file__), '..', 'services')
            if services_path not in sys.path:
                sys.path.insert(0, services_path)
            from seller_notification_service import notification_service as ns
            notification_service = ns
            logger.info("✅ Notification service imported via sys.path manipulation")
        except ImportError:
            # If all imports fail, create a dummy service
            logger.warning("⚠️ Could not import notification_service, using dummy implementation")
            class DummyNotificationService:
                async def create_notification(self, *args, **kwargs):
                    return {"id": "dummy", "success": False}
                
                async def mark_as_read(self, notification_id, user_id):
                    return True
                
                async def get_unread_count(self, user_id):
                    return 0
            
            notification_service = DummyNotificationService()
            logger.info("✅ Dummy notification service created")

def register_notification_socket_handlers():
    """Registrar handlers de Socket.IO para notificaciones"""
    
    @sio.on('connect')
    async def handle_connect(sid, environ):
        """Manejar conexión de cliente"""
        logger.info(f"Client connected: {sid}")
        
        # Enviar estado inicial
        await sio.emit('notification_connected', {
            'status': 'connected',
            'message': 'Notification socket connected'
        }, room=sid)
    
    @sio.on('disconnect')
    async def handle_disconnect(sid):
        """Manejar desconexión de cliente"""
        logger.info(f"Client disconnected: {sid}")
    
    @sio.on('subscribe_notifications')
    async def handle_subscribe_notifications(sid, data):
        """Suscribir usuario a sus notificaciones"""
        try:
            user_id = data.get('user_id')
            if not user_id:
                logger.error(f"No user_id provided in subscribe_notifications: {data}")
                return
            
            # Unir al usuario a su room personal
            await sio.enter_room(sid, f"notifications:{user_id}")
            
            logger.info(f"User {user_id} subscribed to notifications")
            
            # Enviar confirmación
            await sio.emit('notification_subscribed', {
                'user_id': user_id,
                'status': 'subscribed'
            }, room=sid)
            
        except Exception as e:
            logger.error(f"Error in subscribe_notifications: {e}")
    
    @sio.on('unsubscribe_notifications')
    async def handle_unsubscribe_notifications(sid, data):
        """Desuscribir usuario de notificaciones"""
        try:
            user_id = data.get('user_id')
            if user_id:
                await sio.leave_room(sid, f"notifications:{user_id}")
                logger.info(f"User {user_id} unsubscribed from notifications")
        except Exception as e:
            logger.error(f"Error in unsubscribe_notifications: {e}")
    
    @sio.on('mark_notification_read')
    async def handle_mark_notification_read(sid, data):
        """Marcar notificación como leída via socket"""
        try:
            notification_id = data.get('notification_id')
            user_id = data.get('user_id')
            
            if not notification_id or not user_id:
                logger.error(f"Missing data in mark_notification_read: {data}")
                return
            
            # Marcar como leída en el servicio
            success = await notification_service.mark_as_read(notification_id, user_id)
            
            if success:
                # Notificar al usuario que se marcó como leída
                await sio.emit('notification_marked_read', {
                    'notification_id': notification_id,
                    'success': True
                }, room=sid)
                
                # Actualizar count para todos los suscriptores de este usuario
                await emit_notification_count_update(user_id)
            
        except Exception as e:
            logger.error(f"Error in mark_notification_read: {e}")
    
    @sio.on('get_notification_count')
    async def handle_get_notification_count(sid, data):
        """Obtener count de notificaciones via socket"""
        try:
            user_id = data.get('user_id')
            if not user_id:
                return
            
            # Obtener count desde Redis o DB
            from db import get_db
            async with get_db() as db:
                result = await db.execute(
                    "SELECT * FROM unread_notifications_count WHERE user_id = :user_id",
                    {"user_id": user_id}
                )
                row = result.fetchone()
                
                if row:
                    count_data = {
                        'total': row.count,
                        'critical': row.critical_count,
                        'high': row.high_count,
                        'medium': row.medium_count,
                        'low': row.low_count
                    }
                else:
                    count_data = {
                        'total': 0,
                        'critical': 0,
                        'high': 0,
                        'medium': 0,
                        'low': 0
                    }
            
            # Enviar count al cliente
            await sio.emit('notification_count_update', count_data, room=sid)
            
        except Exception as e:
            logger.error(f"Error in get_notification_count: {e}")
    
    logger.info("✅ Notification socket handlers registered")

async def emit_notification_count_update(user_id: str):
    """Emitir actualización de count de notificaciones"""
    try:
        # Obtener count actualizado
        from db import get_db
        async with get_db() as db:
            result = await db.execute(
                "SELECT * FROM unread_notifications_count WHERE user_id = :user_id",
                {"user_id": user_id}
            )
            row = result.fetchone()
            
            if row:
                count_data = {
                    'total': row.count,
                    'critical': row.critical_count,
                    'high': row.high_count,
                    'medium': row.medium_count,
                    'low': row.low_count
                }
            else:
                count_data = {
                    'total': 0,
                    'critical': 0,
                    'high': 0,
                    'medium': 0,
                    'low': 0
                }
        
        # Emitir a todos en el room del usuario
        await sio.emit('notification_count_update', count_data, room=f"notifications:{user_id}")
        
    except Exception as e:
        logger.error(f"Error emitting notification count update: {e}")

async def emit_new_notification(notification_data: Dict[str, Any]):
    """Emitir nueva notificación en tiempo real"""
    try:
        user_id = notification_data.get('recipient_id')
        if not user_id:
            return
        
        # Preparar datos para el frontend
        frontend_notification = {
            'id': notification_data.get('id'),
            'type': notification_data.get('type'),
            'title': notification_data.get('title'),
            'message': notification_data.get('message'),
            'priority': notification_data.get('priority'),
            'created_at': notification_data.get('created_at'),
            'related_entity_type': notification_data.get('related_entity_type'),
            'related_entity_id': notification_data.get('related_entity_id')
        }
        
        # Emitir al usuario específico
        await sio.emit('new_notification', frontend_notification, room=f"notifications:{user_id}")
        
        # También actualizar el count
        await emit_notification_count_update(user_id)
        
        logger.info(f"Emitted new notification to user {user_id}: {notification_data.get('title')}")
        
    except Exception as e:
        logger.error(f"Error emitting new notification: {e}")

# Registrar handlers al importar
register_notification_socket_handlers()