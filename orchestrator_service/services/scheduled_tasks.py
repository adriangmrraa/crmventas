"""
Scheduled Tasks Service
Background jobs para ejecutar tareas periódicas
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from .seller_notification_service import notification_service
from .seller_metrics_service import seller_metrics_service
from db import get_db
from config import settings

logger = logging.getLogger(__name__)

class ScheduledTasksService:
    """Servicio para tareas programadas en background"""
    
    def __init__(self):
        self.scheduler = None
        self._init_scheduler()
    
    def _init_scheduler(self):
        """Inicializar scheduler"""
        try:
            self.scheduler = AsyncIOScheduler()
            logger.info("Scheduler initialized")
        except Exception as e:
            logger.error(f"Error initializing scheduler: {e}")
            self.scheduler = None
    
    async def run_notification_checks(self):
        """Ejecutar verificaciones de notificaciones para todos los tenants"""
        logger.info("Running scheduled notification checks")
        
        try:
            async with get_db() as db:
                # Obtener todos los tenants activos
                result = await db.execute(
                    "SELECT id FROM tenants WHERE status = 'active'"
                )
                tenants = result.fetchall()
                
                tasks = []
                for tenant in tenants:
                    task = notification_service.run_all_checks(tenant.id)
                    tasks.append(task)
                
                # Ejecutar en paralelo
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    total_notifications = 0
                    for i, result in enumerate(results):
                        if isinstance(result, Exception):
                            logger.error(f"Error running checks for tenant {tenants[i].id}: {result}")
                        elif isinstance(result, list):
                            total_notifications += len(result)
                    
                    logger.info(f"Scheduled notification checks completed: {total_notifications} notifications generated across {len(tenants)} tenants")
                else:
                    logger.info("No active tenants found for notification checks")
                    
        except Exception as e:
            logger.error(f"Error in scheduled notification checks: {e}")
    
    async def refresh_seller_metrics(self):
        """Refrescar métricas de vendedores para todos los tenants"""
        logger.info("Running scheduled seller metrics refresh")
        
        try:
            async with get_db() as db:
                # Obtener todos los tenants activos
                result = await db.execute(
                    "SELECT id FROM tenants WHERE status = 'active'"
                )
                tenants = result.fetchall()
                
                tasks = []
                for tenant in tenants:
                    task = seller_metrics_service.refresh_all_metrics(tenant.id)
                    tasks.append(task)
                
                # Ejecutar en paralelo
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    success_count = 0
                    error_count = 0
                    for i, result in enumerate(results):
                        if isinstance(result, Exception):
                            logger.error(f"Error refreshing metrics for tenant {tenants[i].id}: {result}")
                            error_count += 1
                        else:
                            success_count += 1
                    
                    logger.info(f"Scheduled metrics refresh completed: {success_count} successful, {error_count} errors")
                else:
                    logger.info("No active tenants found for metrics refresh")
                    
        except Exception as e:
            logger.error(f"Error in scheduled metrics refresh: {e}")
    
    async def cleanup_expired_data(self):
        """Limpiar datos expirados"""
        logger.info("Running scheduled data cleanup")
        
        try:
            async with get_db() as db:
                # 1. Eliminar notificaciones expiradas
                expired_notifications = await notification_service.delete_expired_notifications()
                
                # 2. Limpiar cache Redis viejo (si está configurado)
                # 3. Archivar métricas antiguas (más de 30 días)
                result = await db.execute("""
                    DELETE FROM seller_metrics 
                    WHERE period != 'today' 
                    AND updated_at < NOW() - INTERVAL '30 days'
                    RETURNING COUNT(*) as count
                """)
                row = result.fetchone()
                archived_metrics = row.count if row else 0
                
                # 4. Limpiar sesiones de chat inactivas
                result = await db.execute("""
                    DELETE FROM chat_sessions 
                    WHERE last_activity < NOW() - INTERVAL '7 days'
                    AND status = 'inactive'
                    RETURNING COUNT(*) as count
                """)
                row = result.fetchone()
                cleaned_sessions = row.count if row else 0
                
                await db.commit()
                
                logger.info(f"Data cleanup completed: {expired_notifications} expired notifications, {archived_metrics} archived metrics, {cleaned_sessions} cleaned sessions")
                
        except Exception as e:
            logger.error(f"Error in scheduled data cleanup: {e}")
    
    async def generate_daily_reports(self):
        """Generar reportes diarios para CEO"""
        logger.info("Running scheduled daily reports generation")
        
        try:
            async with get_db() as db:
                # Obtener todos los tenants con CEO
                result = await db.execute("""
                    SELECT DISTINCT t.id as tenant_id, u.id as ceo_id, u.email as ceo_email
                    FROM tenants t
                    JOIN users u ON t.id = u.tenant_id
                    WHERE u.role = 'ceo' 
                        AND u.status = 'active'
                        AND t.status = 'active'
                """)
                ceo_tenants = result.fetchall()
                
                for tenant in ceo_tenants:
                    try:
                        # Generar reporte de métricas del día
                        daily_metrics = await seller_metrics_service.get_daily_summary(tenant.tenant_id)
                        
                        # Crear notificación de reporte diario
                        notification = await notification_service.create_daily_report_notification(
                            tenant_id=tenant.tenant_id,
                            ceo_id=tenant.ceo_id,
                            metrics=daily_metrics
                        )
                        
                        logger.info(f"Daily report generated for tenant {tenant.tenant_id}, CEO: {tenant.ceo_email}")
                        
                    except Exception as e:
                        logger.error(f"Error generating daily report for tenant {tenant.tenant_id}: {e}")
                
                logger.info(f"Daily reports generation completed for {len(ceo_tenants)} tenants")
                
        except Exception as e:
            logger.error(f"Error in scheduled daily reports: {e}")
    
    def start_all_tasks(self):
        """Iniciar todas las tareas programadas"""
        if not self.scheduler:
            logger.error("Scheduler not initialized, cannot start tasks")
            return
        
        try:
            # 1. Verificaciones de notificaciones cada 5 minutos
            self.scheduler.add_job(
                self.run_notification_checks,
                IntervalTrigger(minutes=5),
                id='notification_checks',
                name='Notification Checks',
                replace_existing=True
            )
            
            # 2. Refresh de métricas cada 15 minutos
            self.scheduler.add_job(
                self.refresh_seller_metrics,
                IntervalTrigger(minutes=15),
                id='metrics_refresh',
                name='Seller Metrics Refresh',
                replace_existing=True
            )
            
            # 3. Limpieza de datos cada hora
            self.scheduler.add_job(
                self.cleanup_expired_data,
                IntervalTrigger(hours=1),
                id='data_cleanup',
                name='Data Cleanup',
                replace_existing=True
            )
            
            # 4. Reportes diarios a las 8:00 AM
            self.scheduler.add_job(
                self.generate_daily_reports,
                CronTrigger(hour=8, minute=0),
                id='daily_reports',
                name='Daily Reports',
                replace_existing=True
            )
            
            # Iniciar scheduler
            self.scheduler.start()
            logger.info("All scheduled tasks started")
            
            # Log de jobs programados
            jobs = self.scheduler.get_jobs()
            logger.info(f"Scheduled {len(jobs)} tasks:")
            for job in jobs:
                logger.info(f"  - {job.name}: {job.trigger}")
                
        except Exception as e:
            logger.error(f"Error starting scheduled tasks: {e}")
    
    def stop_all_tasks(self):
        """Detener todas las tareas programadas"""
        if self.scheduler:
            self.scheduler.shutdown()
            logger.info("All scheduled tasks stopped")
    
    def get_task_status(self) -> Dict:
        """Obtener estado de todas las tareas programadas"""
        if not self.scheduler:
            return {"error": "Scheduler not initialized"}
        
        jobs = self.scheduler.get_jobs()
        status = {
            "scheduler_running": self.scheduler.running,
            "total_tasks": len(jobs),
            "tasks": []
        }
        
        for job in jobs:
            status["tasks"].append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "last_run": job.last_run_time.isoformat() if job.last_run_time else None,
                "trigger": str(job.trigger)
            })
        
        return status

# Instancia global del servicio
scheduled_tasks_service = ScheduledTasksService()