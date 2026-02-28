"""
Notification Routes
Endpoints API para el sistema de notificaciones
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from datetime import datetime
from sqlalchemy import text

from core.security import get_current_user
from services.seller_notification_service import notification_service
from db import get_db

router = APIRouter(prefix="/admin/core/notifications", tags=["notifications"])

# Models
class NotificationResponse(BaseModel):
    id: str
    type: str
    title: str
    message: str
    priority: str
    recipient_id: str
    sender_id: Optional[str] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    metadata: dict = Field(default_factory=dict)
    read: bool
    created_at: str
    expires_at: Optional[str] = None
    sender_name: Optional[str] = None
    sender_email: Optional[str] = None

class NotificationCountResponse(BaseModel):
    total: int
    critical: int
    high: int
    medium: int
    low: int

class MarkAsReadRequest(BaseModel):
    notification_id: str

class NotificationSettings(BaseModel):
    email_notifications: bool = True
    push_notifications: bool = True
    desktop_notifications: bool = True
    mute_until: Optional[datetime] = None
    muted_types: List[str] = Field(default_factory=list)

class RunChecksResponse(BaseModel):
    generated: int
    notifications: List[NotificationResponse]

# Endpoints
@router.get("/", response_model=List[NotificationResponse])
async def get_notifications(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    unread_only: bool = False,
    seller_id: Optional[str] = None,
    db=Depends(get_db)
):
    """
    Obtener notificaciones del usuario actual (o de otro vendedor si es CEO)
    """
    try:
        notifications = await notification_service.get_user_notifications(
            user_id=current_user["id"],
            role=current_user.get("role", "setter"),
            tenant_id=current_user.get("tenant_id", 1),
            limit=limit,
            offset=offset,
            unread_only=unread_only,
            filter_seller_id=seller_id
        )
        return notifications
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting notifications: {str(e)}")

@router.get("/count", response_model=NotificationCountResponse)
async def get_notification_count(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Obtener conteo de notificaciones no leídas (aislado por tenant_id)
    """
    try:
        # Usamos el tenant_id del usuario para el conteo si es que la vista no lo filtra
        # Pero la vista 'unread_notifications_count' agrupa por recipient_id, que es único globalmente (UUID)
        async with db.begin():
            result = await db.execute(
                text("SELECT * FROM unread_notifications_count WHERE user_id = :user_id"),
                {"user_id": current_user["id"]}
            )
            row = result.fetchone()
            
            if row:
                return NotificationCountResponse(
                    total=row.count,
                    critical=row.critical_count,
                    high=row.high_count,
                    medium=row.medium_count,
                    low=row.low_count
                )
            return NotificationCountResponse(total=0, critical=0, high=0, medium=0, low=0)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting notification count: {str(e)}")

@router.post("/read", response_model=bool)
async def mark_as_read(
    request: MarkAsReadRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Marcar una notificación como leída
    """
    try:
        success = await notification_service.mark_as_read(
            notification_id=request.notification_id,
            user_id=current_user["id"]
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Notification not found or not authorized")
        
        return True
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error marking notification as read: {str(e)}")

@router.post("/read-all", response_model=int)
async def mark_all_as_read(
    current_user: dict = Depends(get_current_user)
):
    """
    Marcar todas las notificaciones como leídas
    """
    try:
        count = await notification_service.mark_all_as_read(
            user_id=current_user["id"]
        )
        return count
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error marking all notifications as read: {str(e)}")

@router.get("/settings", response_model=NotificationSettings)
async def get_notification_settings(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Obtener configuración de notificaciones del usuario
    """
    try:
        async with db as database:
            result = await database.execute(
                """
                SELECT email_notifications, push_notifications, desktop_notifications,
                       mute_until, muted_types
                FROM notification_settings
                WHERE user_id = :user_id
                """,
                {"user_id": current_user["id"]}
            )
            row = result.fetchone()
            
            if row:
                return NotificationSettings(
                    email_notifications=row.email_notifications,
                    push_notifications=row.push_notifications,
                    desktop_notifications=row.desktop_notifications,
                    mute_until=row.mute_until,
                    muted_types=row.muted_types or []
                )
            else:
                # Crear configuración por defecto si no existe
                return NotificationSettings()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting notification settings: {str(e)}")

@router.put("/settings", response_model=NotificationSettings)
async def update_notification_settings(
    settings: NotificationSettings,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Actualizar configuración de notificaciones
    """
    try:
        async with db as database:
            await database.execute(
                """
                INSERT INTO notification_settings (
                    user_id, email_notifications, push_notifications, 
                    desktop_notifications, mute_until, muted_types
                ) VALUES (
                    :user_id, :email_notifications, :push_notifications,
                    :desktop_notifications, :mute_until, :muted_types
                )
                ON CONFLICT (user_id) DO UPDATE SET
                    email_notifications = EXCLUDED.email_notifications,
                    push_notifications = EXCLUDED.push_notifications,
                    desktop_notifications = EXCLUDED.desktop_notifications,
                    mute_until = EXCLUDED.mute_until,
                    muted_types = EXCLUDED.muted_types,
                    updated_at = NOW()
                """,
                {
                    "user_id": current_user["id"],
                    "email_notifications": settings.email_notifications,
                    "push_notifications": settings.push_notifications,
                    "desktop_notifications": settings.desktop_notifications,
                    "mute_until": settings.mute_until,
                    "muted_types": settings.muted_types
                }
            )
            await database.commit()
            
            return settings
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating notification settings: {str(e)}")

@router.post("/run-checks", response_model=RunChecksResponse)
async def run_notification_checks(
    current_user: dict = Depends(get_current_user),
    tenant_id: Optional[int] = Query(None)
):
    """
    Ejecutar verificaciones de notificaciones (solo para admin/CEO)
    """
    # Verificar permisos
    if current_user["role"] not in ["ceo", "admin"]:
        raise HTTPException(status_code=403, detail="Only CEO/admin can run notification checks")
    
    try:
        # Usar tenant_id del usuario si no se especifica
        target_tenant_id = tenant_id or current_user.get("tenant_id")
        if not target_tenant_id:
            raise HTTPException(status_code=400, detail="Tenant ID is required")
        
        # Ejecutar verificaciones
        notifications = await notification_service.run_all_checks(
            tenant_id=target_tenant_id
        )
        
        # Convertir a response
        notification_responses = []
        for notification in notifications:
            notification_responses.append(
                NotificationResponse(
                    id=notification.id,
                    type=notification.type,
                    title=notification.title,
                    message=notification.message,
                    priority=notification.priority,
                    recipient_id=notification.recipient_id,
                    sender_id=notification.sender_id,
                    related_entity_type=notification.related_entity_type,
                    related_entity_id=notification.related_entity_id,
                    metadata=notification.metadata or {},
                    read=notification.read,
                    created_at=notification.created_at.isoformat() if notification.created_at else None,
                    expires_at=notification.expires_at.isoformat() if notification.expires_at else None
                )
            )
        
        return RunChecksResponse(
            generated=len(notifications),
            notifications=notification_responses[:10]  # Limitar respuesta
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running notification checks: {str(e)}")

@router.delete("/expired", response_model=int)
async def delete_expired_notifications(
    current_user: dict = Depends(get_current_user)
):
    """
    Eliminar notificaciones expiradas (solo para admin/CEO)
    """
    if current_user["role"] not in ["ceo", "admin"]:
        raise HTTPException(status_code=403, detail="Only CEO/admin can delete expired notifications")
    
    try:
        count = await notification_service.delete_expired_notifications()
        return count
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting expired notifications: {str(e)}")

@router.get("/types")
async def get_notification_types():
    """
    Obtener tipos de notificaciones disponibles
    """
    return {
        "types": [
            {
                "id": "unanswered",
                "name": "Conversaciones sin respuesta",
                "description": "Alertas cuando una conversación no tiene respuesta por más de 1 hora",
                "default_priority": "high"
            },
            {
                "id": "hot_lead",
                "name": "Leads calientes",
                "description": "Notificaciones para leads con alta probabilidad de conversión",
                "default_priority": "high"
            },
            {
                "id": "followup",
                "name": "Recordatorios de follow-up",
                "description": "Recordatorios para contactar leads que necesitan seguimiento",
                "default_priority": "medium"
            },
            {
                "id": "performance_alert",
                "name": "Alertas de performance",
                "description": "Alertas cuando métricas de vendedores están por debajo de objetivos",
                "default_priority": "medium"
            },
            {
                "id": "assignment",
                "name": "Asignaciones",
                "description": "Notificaciones cuando se asigna una conversación o lead",
                "default_priority": "low"
            },
            {
                "id": "metric_alert",
                "name": "Alertas de métricas",
                "description": "Alertas cuando métricas del equipo alcanzan objetivos o requieren atención",
                "default_priority": "medium"
            }
        ]
    }