"""
Health Check Routes
Endpoints para monitoreo del sistema y scheduled tasks
"""

from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from services.scheduled_tasks import scheduled_tasks_service
from db import get_db

router = APIRouter(prefix="/health", tags=["health"])

# Models
class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    environment: str
    database: Dict[str, Any]
    redis: Dict[str, Any]
    scheduled_tasks: Dict[str, Any]
    services: Dict[str, Any]

class TaskStatusResponse(BaseModel):
    scheduler_running: bool
    total_tasks: int
    tasks: list

# Endpoints
@router.get("/", response_model=HealthResponse)
async def health_check():
    """
    Health check completo del sistema
    """
    # Verificar base de datos
    db_status = {"status": "unknown", "connected": False}
    try:
        async with get_db() as db:
            # Ejecutar query simple para verificar conexión
            result = await db.execute("SELECT 1 as test")
            row = result.fetchone()
            db_status = {
                "status": "healthy" if row and row.test == 1 else "unhealthy",
                "connected": bool(row and row.test == 1)
            }
    except Exception as e:
        db_status = {
            "status": "error",
            "connected": False,
            "error": str(e)
        }
    
    # Verificar Redis (si está configurado)
    redis_status = {"status": "not_configured", "available": False}
    try:
        from services.seller_notification_service import notification_service
        if notification_service.redis_client:
            # Intentar ping a Redis
            ping_result = await notification_service.redis_client.ping()
            redis_status = {
                "status": "healthy" if ping_result else "unhealthy",
                "available": bool(ping_result)
            }
    except Exception as e:
        redis_status = {
            "status": "error",
            "available": False,
            "error": str(e)
        }
    
    # Obtener estado de scheduled tasks
    tasks_status = scheduled_tasks_service.get_task_status() if hasattr(scheduled_tasks_service, 'get_task_status') else {
        "scheduler_running": False,
        "total_tasks": 0,
        "tasks": []
    }
    
    # Verificar servicios críticos
    services_status = {
        "notification_service": "unknown",
        "metrics_service": "unknown",
        "socket_io": "unknown"
    }
    
    try:
        from services.seller_notification_service import notification_service
        services_status["notification_service"] = "available"
    except Exception:
        services_status["notification_service"] = "unavailable"
    
    try:
        from services.seller_metrics_service import seller_metrics_service
        services_status["metrics_service"] = "available"
    except Exception:
        services_status["metrics_service"] = "unavailable"
    
    try:
        from core.socket_notifications import register_notification_socket_handlers
        services_status["socket_io"] = "available"
    except Exception:
        services_status["socket_io"] = "unavailable"
    
    # Determinar estado general
    overall_status = "healthy"
    if db_status["status"] != "healthy":
        overall_status = "degraded"
    if not tasks_status.get("scheduler_running", False):
        overall_status = "degraded"
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow().isoformat(),
        version="7.6.0",
        environment="production",
        database=db_status,
        redis=redis_status,
        scheduled_tasks=tasks_status,
        services=services_status
    )

@router.get("/tasks", response_model=TaskStatusResponse)
async def get_task_status():
    """
    Obtener estado detallado de scheduled tasks
    """
    try:
        status = scheduled_tasks_service.get_task_status()
        return TaskStatusResponse(**status)
    except Exception as e:
        return TaskStatusResponse(
            scheduler_running=False,
            total_tasks=0,
            tasks=[{"error": str(e)}]
        )

@router.post("/tasks/start")
async def start_scheduled_tasks():
    """
    Iniciar scheduled tasks manualmente
    """
    try:
        scheduled_tasks_service.start_all_tasks()
        status = scheduled_tasks_service.get_task_status()
        
        return {
            "success": True,
            "message": "Scheduled tasks started",
            "tasks_started": status.get("total_tasks", 0),
            "scheduler_running": status.get("scheduler_running", False)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to start scheduled tasks"
        }

@router.post("/tasks/stop")
async def stop_scheduled_tasks():
    """
    Detener scheduled tasks manualmente
    """
    try:
        scheduled_tasks_service.stop_all_tasks()
        
        return {
            "success": True,
            "message": "Scheduled tasks stopped"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to stop scheduled tasks"
        }

@router.get("/tasks/run/notification-checks")
async def run_notification_checks_now():
    """
    Ejecutar verificaciones de notificaciones inmediatamente
    """
    try:
        from services.scheduled_tasks import scheduled_tasks_service
        
        # Ejecutar tarea manualmente
        result = await scheduled_tasks_service.run_notification_checks()
        
        return {
            "success": True,
            "message": "Notification checks executed",
            "result": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to run notification checks"
        }

@router.get("/tasks/run/metrics-refresh")
async def run_metrics_refresh_now():
    """
    Ejecutar refresh de métricas inmediatamente
    """
    try:
        from services.scheduled_tasks import scheduled_tasks_service
        
        result = await scheduled_tasks_service.refresh_seller_metrics()
        
        return {
            "success": True,
            "message": "Metrics refresh executed",
            "result": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to run metrics refresh"
        }

@router.get("/tasks/run/cleanup")
async def run_cleanup_now():
    """
    Ejecutar limpieza de datos inmediatamente
    """
    try:
        from services.scheduled_tasks import scheduled_tasks_service
        
        result = await scheduled_tasks_service.cleanup_expired_data()
        
        return {
            "success": True,
            "message": "Data cleanup executed",
            "result": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to run data cleanup"
        }

@router.get("/readiness")
async def readiness_probe():
    """
    Readiness probe para Kubernetes/load balancers
    Verifica que el servicio está listo para recibir tráfico
    """
    try:
        # Verificar conexión a base de datos
        async with get_db() as db:
            result = await db.execute("SELECT 1 as ready")
            row = result.fetchone()
            
            if not row or row.ready != 1:
                return {"status": "not_ready", "reason": "database_unavailable"}
        
        # Verificar que scheduled tasks están corriendo (si están habilitados)
        import os
        if os.getenv("ENABLE_SCHEDULED_TASKS", "true").lower() == "true":
            status = scheduled_tasks_service.get_task_status()
            if not status.get("scheduler_running", False):
                return {"status": "not_ready", "reason": "scheduler_not_running"}
        
        return {"status": "ready"}
        
    except Exception as e:
        return {"status": "not_ready", "reason": str(e)}

@router.get("/liveness")
async def liveness_probe():
    """
    Liveness probe para Kubernetes
    Verifica que el servicio está vivo
    """
    try:
        # Verificación simple de que la aplicación responde
        return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        return {"status": "dead", "error": str(e)}