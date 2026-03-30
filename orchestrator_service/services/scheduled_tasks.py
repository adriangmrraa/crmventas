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
    
    async def run_reactivation_checks(self):
        """DEV-47: Buscar leads inactivos para iniciar secuencias de reactivación"""
        logger.info("Running scheduled reactivation checks")
        try:
            from services.reactivation_service import check_and_trigger_sequences
            async with get_db() as db_session:
                # Obtener todos los tenants activos
                result = await db_session.execute("SELECT id FROM tenants WHERE status = 'active'")
                tenants = result.fetchall()
                
                for tenant in tenants:
                    # check_and_trigger_sequences usa el pool de db.py, no el session de SQLAlchemy por ahora
                    # pero pasamos el tenant_id
                    from db import db as pg_db
                    await check_and_trigger_sequences(tenant.id, pg_db.pool)
            logger.info("Reactivation checks completed")
        except Exception as e:
            logger.error(f"Error in scheduled reactivation checks: {e}")

    async def run_pending_reactivations(self):
        """DEV-47: Ejecutar pasos de reactivación pendientes (envío de mensajes)"""
        logger.info("Running scheduled pending reactivations execution")
        try:
            from services.reactivation_service import execute_pending_steps
            async with get_db() as db_session:
                result = await db_session.execute("SELECT id FROM tenants WHERE status = 'active'")
                tenants = result.fetchall()
                
                for tenant in tenants:
                    from db import db as pg_db
                    await execute_pending_steps(tenant.id, pg_db.pool)
            logger.info("Pending reactivations execution completed")
        except Exception as e:
            logger.error(f"Error in scheduled pending reactivations: {e}")

    async def run_deduplication_checks(self):
        """DEV-50: Buscar candidatos duplicados para todos los leads activos"""
        logger.info("Running scheduled deduplication checks")
        try:
            from services.deduplication_service import find_duplicates_for_lead, create_duplicate_candidates
            from db import db as pg_db
            
            async with get_db() as db_session:
                result = await db_session.execute("SELECT id FROM tenants WHERE status = 'active'")
                tenants = result.fetchall()
                
                for tenant in tenants:
                    # Buscar leads actualizados recientemente (últimas 3 horas) para no procesar todo siempre
                    leads = await pg_db.pool.fetch(
                        "SELECT id, phone_number, email, first_name, last_name FROM leads WHERE tenant_id = $1 AND updated_at > NOW() - INTERVAL '3 hours'",
                        tenant.id
                    )
                    for lead in leads:
                        duplicates = await find_duplicates_for_lead(
                            tenant.id, str(lead['id']), lead['phone_number'], 
                            lead['email'], lead['first_name'], lead['last_name'], pg_db.pool
                        )
                        if duplicates:
                            await create_duplicate_candidates(tenant.id, str(lead['id']), duplicates, pg_db.pool)
            logger.info("Deduplication checks completed")
        except Exception as e:
            logger.error(f"Error in scheduled deduplication checks: {e}")

    async def sync_dentalogic_leads(self):
        """Sincronizar leads de alta intención desde Dentalogic"""
        logger.info("Running scheduled Dentalogic leads sync")
        try:
            from .dentalogic_sync_service import dentalogic_sync_service
            await dentalogic_sync_service.sync_leads()
            logger.info("Dentalogic leads sync completed")
        except Exception as e:
            logger.error(f"Error in Dentalogic leads sync: {e}")
            
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
            
            # 5. Sync con Dentalogic (Frecuencia: 5 minutos)
            self.scheduler.add_job(
                self.sync_dentalogic_leads,
                IntervalTrigger(minutes=5),
                id='dentalogic_sync',
                name='Dentalogic Leads Sync',
                replace_existing=True
            )

            # 6. Reactivation Checks (Frecuencia: 30 minutos)
            self.scheduler.add_job(
                self.run_reactivation_checks,
                IntervalTrigger(minutes=30),
                id='reactivation_checks',
                name='Lead Reactivation Checks',
                replace_existing=True
            )

            # 7. Pending Reactivations (Frecuencia: 15 minutos)
            self.scheduler.add_job(
                self.run_pending_reactivations,
                IntervalTrigger(minutes=15),
                id='pending_reactivations',
                name='Execute Pending Reactivations',
                replace_existing=True
            )

            # 8. Deduplication Checks (Frecuencia: 2 horas)
            self.scheduler.add_job(
                self.run_deduplication_checks,
                IntervalTrigger(hours=2),
                id='deduplication_checks',
                name='Lead Deduplication Checks',
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