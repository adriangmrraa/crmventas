"""
Scheduled Tasks Routes
Endpoints para gestionar tareas programadas en background
"""

from datetime import datetime
from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.security import get_current_user
from services.scheduled_tasks import scheduled_tasks_service

router = APIRouter(prefix="/scheduled-tasks", tags=["scheduled-tasks"])

# Models
class TaskStatusResponse(BaseModel):
    scheduler_running: bool
    total_tasks: int
    tasks: List[Dict]

class StartTasksResponse(BaseModel):
    success: bool
    message: str
    tasks_started: int

class StopTasksResponse(BaseModel):
    success: bool
    message: str

class RunTaskResponse(BaseModel):
    success: bool
    message: str
    result: Dict

# Endpoints
@router.get("/status", response_model=TaskStatusResponse)
async def get_task_status(
    current_user: dict = Depends(get_current_user)
):
    """
    Obtener estado de las tareas programadas
    """
    # Solo CEO/admin pueden ver el estado
    if current_user["role"] not in ["ceo", "admin"]:
        raise HTTPException(status_code=403, detail="Only CEO/admin can view task status")
    
    try:
        status = scheduled_tasks_service.get_task_status()
        return TaskStatusResponse(**status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting task status: {str(e)}")

@router.post("/start", response_model=StartTasksResponse)
async def start_scheduled_tasks(
    current_user: dict = Depends(get_current_user)
):
    """
    Iniciar todas las tareas programadas
    """
    if current_user["role"] not in ["ceo", "admin"]:
        raise HTTPException(status_code=403, detail="Only CEO/admin can start scheduled tasks")
    
    try:
        scheduled_tasks_service.start_all_tasks()
        
        status = scheduled_tasks_service.get_task_status()
        tasks_started = status.get("total_tasks", 0)
        
        return StartTasksResponse(
            success=True,
            message=f"Scheduled tasks started successfully",
            tasks_started=tasks_started
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting scheduled tasks: {str(e)}")

@router.post("/stop", response_model=StopTasksResponse)
async def stop_scheduled_tasks(
    current_user: dict = Depends(get_current_user)
):
    """
    Detener todas las tareas programadas
    """
    if current_user["role"] not in ["ceo", "admin"]:
        raise HTTPException(status_code=403, detail="Only CEO/admin can stop scheduled tasks")
    
    try:
        scheduled_tasks_service.stop_all_tasks()
        
        return StopTasksResponse(
            success=True,
            message="Scheduled tasks stopped successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping scheduled tasks: {str(e)}")

@router.post("/run/notification-checks", response_model=RunTaskResponse)
async def run_notification_checks(
    current_user: dict = Depends(get_current_user)
):
    """
    Ejecutar verificaciones de notificaciones manualmente
    """
    if current_user["role"] not in ["ceo", "admin"]:
        raise HTTPException(status_code=403, detail="Only CEO/admin can run notification checks")
    
    try:
        # Usar tenant_id del usuario actual
        tenant_id = current_user.get("tenant_id")
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User does not have a tenant assigned")
        
        from services.seller_notification_service import notification_service
        notifications = await notification_service.run_all_checks(tenant_id)
        
        return RunTaskResponse(
            success=True,
            message=f"Notification checks completed: {len(notifications)} notifications generated",
            result={"notifications_generated": len(notifications)}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running notification checks: {str(e)}")

@router.post("/run/metrics-refresh", response_model=RunTaskResponse)
async def run_metrics_refresh(
    current_user: dict = Depends(get_current_user)
):
    """
    Ejecutar refresh de métricas manualmente
    """
    if current_user["role"] not in ["ceo", "admin"]:
        raise HTTPException(status_code=403, detail="Only CEO/admin can run metrics refresh")
    
    try:
        tenant_id = current_user.get("tenant_id")
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User does not have a tenant assigned")
        
        from services.seller_metrics_service import seller_metrics_service
        result = await seller_metrics_service.refresh_all_metrics(tenant_id)
        
        return RunTaskResponse(
            success=result.get("success", False),
            message=f"Metrics refresh completed: {result.get('refreshed_count', 0)} sellers refreshed",
            result=result
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running metrics refresh: {str(e)}")

@router.post("/run/data-cleanup", response_model=RunTaskResponse)
async def run_data_cleanup(
    current_user: dict = Depends(get_current_user)
):
    """
    Ejecutar limpieza de datos manualmente
    """
    if current_user["role"] not in ["ceo", "admin"]:
        raise HTTPException(status_code=403, detail="Only CEO/admin can run data cleanup")
    
    try:
        from services.seller_notification_service import notification_service
        expired_count = await notification_service.delete_expired_notifications()
        
        return RunTaskResponse(
            success=True,
            message=f"Data cleanup completed: {expired_count} expired notifications deleted",
            result={"expired_notifications_deleted": expired_count}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running data cleanup: {str(e)}")

@router.get("/health")
async def get_scheduler_health():
    """
    Health check para el scheduler
    """
    try:
        status = scheduled_tasks_service.get_task_status()
        
        if status.get("error"):
            return {
                "status": "error",
                "message": status["error"],
                "scheduler_running": False
            }
        
        return {
            "status": "healthy" if status.get("scheduler_running", False) else "idle",
            "scheduler_running": status.get("scheduler_running", False),
            "total_tasks": status.get("total_tasks", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "scheduler_running": False
        }