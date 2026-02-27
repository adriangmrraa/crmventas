"""
Metrics Cache Service - Optimized real-time metrics with Redis caching
"""
import logging
import json
import asyncio
from typing import Dict, List, Optional, Any
from uuid import UUID
from datetime import datetime, timedelta
import redis.asyncio as redis
from db import db

logger = logging.getLogger(__name__)

class MetricsCacheService:
    """
    Service for caching and optimizing seller metrics calculations
    Uses Redis for fast access and reduces database load
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or "redis://localhost:6379"
        self.redis_client = None
        self.cache_ttl = 300  # 5 minutes cache TTL
        self.metrics_lock = asyncio.Lock()
    
    async def get_redis_client(self):
        """Get or create Redis client"""
        if self.redis_client is None:
            try:
                self.redis_client = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                await self.redis_client.ping()
                logger.info("✅ Redis client connected successfully")
            except Exception as e:
                logger.error(f"❌ Failed to connect to Redis: {e}")
                self.redis_client = None
        return self.redis_client
    
    async def get_cached_metrics(self, seller_id: UUID, tenant_id: int) -> Optional[Dict]:
        """Get metrics from Redis cache"""
        try:
            redis_client = await self.get_redis_client()
            if not redis_client:
                return None
            
            cache_key = f"metrics:seller:{seller_id}:tenant:{tenant_id}"
            cached_data = await redis_client.get(cache_key)
            
            if cached_data:
                metrics = json.loads(cached_data)
                # Check if cache is still valid (not too old)
                cached_at = datetime.fromisoformat(metrics.get('cached_at', '2000-01-01'))
                if datetime.now() - cached_at < timedelta(seconds=self.cache_ttl):
                    logger.debug(f"✅ Cache hit for seller {seller_id}")
                    return metrics
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached metrics: {e}")
            return None
    
    async def set_cached_metrics(self, seller_id: UUID, tenant_id: int, metrics: Dict):
        """Store metrics in Redis cache"""
        try:
            redis_client = await self.get_redis_client()
            if not redis_client:
                return
            
            cache_key = f"metrics:seller:{seller_id}:tenant:{tenant_id}"
            metrics['cached_at'] = datetime.now().isoformat()
            
            await redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(metrics, default=str)
            )
            logger.debug(f"✅ Cache set for seller {seller_id}")
            
        except Exception as e:
            logger.error(f"Error setting cached metrics: {e}")
    
    async def invalidate_metrics_cache(self, seller_id: UUID, tenant_id: int):
        """Invalidate cache for specific seller"""
        try:
            redis_client = await self.get_redis_client()
            if not redis_client:
                return
            
            cache_key = f"metrics:seller:{seller_id}:tenant:{tenant_id}"
            await redis_client.delete(cache_key)
            logger.debug(f"✅ Cache invalidated for seller {seller_id}")
            
        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")
    
    async def get_realtime_conversation_metrics(self, seller_id: UUID, tenant_id: int) -> Dict:
        """
        Get real-time conversation metrics with caching
        Optimized for frequent access
        """
        cache_key = f"realtime:conv:{seller_id}:tenant:{tenant_id}"
        
        try:
            # Try cache first
            cached = await self.get_cached_metrics(seller_id, tenant_id)
            if cached and 'realtime_conversations' in cached:
                return cached['realtime_conversations']
            
            async with self.metrics_lock:
                # Calculate fresh metrics
                metrics = await self._calculate_realtime_conversation_metrics(seller_id, tenant_id)
                
                # Update cache
                await self.set_cached_metrics(seller_id, tenant_id, {
                    'realtime_conversations': metrics,
                    'calculated_at': datetime.now().isoformat()
                })
                
                return metrics
                
        except Exception as e:
            logger.error(f"Error getting realtime conversation metrics: {e}")
            return await self._calculate_realtime_conversation_metrics(seller_id, tenant_id)
    
    async def _calculate_realtime_conversation_metrics(self, seller_id: UUID, tenant_id: int) -> Dict:
        """Calculate real-time conversation metrics (optimized query)"""
        try:
            # Get active conversations (last 24 hours)
            active_convs = await db.fetchval("""
                SELECT COUNT(DISTINCT from_number)
                FROM chat_messages
                WHERE assigned_seller_id = $1
                AND tenant_id = $2
                AND assigned_at >= NOW() - INTERVAL '24 hours'
            """, seller_id, tenant_id) or 0
            
            # Get today's assignments
            today_assignments = await db.fetchval("""
                SELECT COUNT(DISTINCT from_number)
                FROM chat_messages
                WHERE assigned_seller_id = $1
                AND tenant_id = $2
                AND assigned_at::date = CURRENT_DATE
            """, seller_id, tenant_id) or 0
            
            # Get unread messages
            unread_messages = await db.fetchval("""
                SELECT COUNT(*)
                FROM chat_messages cm
                WHERE cm.assigned_seller_id = $1
                AND cm.tenant_id = $2
                AND cm.role = 'user'
                AND cm.created_at >= NOW() - INTERVAL '24 hours'
                AND NOT EXISTS (
                    SELECT 1 FROM message_reads mr 
                    WHERE mr.message_id = cm.id 
                    AND mr.user_id = $1
                )
            """, seller_id, tenant_id) or 0
            
            # Get response time for last 10 conversations
            response_times = await db.fetch("""
                WITH seller_responses AS (
                    SELECT 
                        from_number,
                        MIN(created_at) as first_response
                    FROM chat_messages
                    WHERE assigned_seller_id = $1
                    AND tenant_id = $2
                    AND role = 'assistant'
                    AND created_at >= NOW() - INTERVAL '24 hours'
                    GROUP BY from_number
                ),
                user_messages AS (
                    SELECT 
                        from_number,
                        MIN(created_at) as first_message
                    FROM chat_messages
                    WHERE assigned_seller_id = $1
                    AND tenant_id = $2
                    AND role = 'user'
                    AND created_at >= NOW() - INTERVAL '24 hours'
                    GROUP BY from_number
                )
                SELECT 
                    EXTRACT(EPOCH FROM (sr.first_response - um.first_message)) as response_seconds
                FROM seller_responses sr
                JOIN user_messages um ON sr.from_number = um.from_number
                WHERE sr.first_response > um.first_message
                ORDER BY sr.first_response DESC
                LIMIT 10
            """, seller_id, tenant_id)
            
            avg_response_seconds = 0
            if response_times:
                times = [rt['response_seconds'] for rt in response_times if rt['response_seconds']]
                if times:
                    avg_response_seconds = sum(times) / len(times)
            
            return {
                "active_conversations": int(active_convs),
                "today_assignments": int(today_assignments),
                "unread_messages": int(unread_messages),
                "avg_response_seconds": round(avg_response_seconds, 1),
                "calculated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating realtime metrics: {e}")
            return {
                "active_conversations": 0,
                "today_assignments": 0,
                "unread_messages": 0,
                "avg_response_seconds": 0,
                "calculated_at": datetime.now().isoformat(),
                "error": str(e)
            }
    
    async def get_performance_trends(self, seller_id: UUID, tenant_id: int, days: int = 7) -> Dict:
        """Get performance trends over time"""
        try:
            trends = await db.fetch("""
                SELECT 
                    DATE(metrics_period_start) as date,
                    total_conversations,
                    leads_converted,
                    conversion_rate,
                    avg_response_time_seconds
                FROM seller_metrics
                WHERE seller_id = $1
                AND tenant_id = $2
                AND metrics_period_start >= NOW() - INTERVAL '$3 days'
                ORDER BY metrics_period_start ASC
            """, seller_id, tenant_id, days)
            
            return {
                "trends": [dict(trend) for trend in trends],
                "period_days": days,
                "seller_id": str(seller_id)
            }
            
        except Exception as e:
            logger.error(f"Error getting performance trends: {e}")
            return {"trends": [], "period_days": days, "error": str(e)}
    
    async def update_metrics_on_message(self, seller_id: UUID, tenant_id: int, message_type: str):
        """
        Update metrics in real-time when a message is sent/received
        Optimized for high frequency updates
        """
        try:
            # Invalidate cache to force recalculation
            await self.invalidate_metrics_cache(seller_id, tenant_id)
            
            # Update real-time counters in Redis for immediate access
            redis_client = await self.get_redis_client()
            if redis_client:
                today = datetime.now().strftime("%Y-%m-%d")
                
                if message_type == 'sent':
                    await redis_client.hincrby(
                        f"daily:metrics:{seller_id}:{tenant_id}:{today}",
                        "messages_sent",
                        1
                    )
                elif message_type == 'received':
                    await redis_client.hincrby(
                        f"daily:metrics:{seller_id}:{tenant_id}:{today}",
                        "messages_received",
                        1
                    )
                
                # Update last activity timestamp
                await redis_client.hset(
                    f"daily:metrics:{seller_id}:{tenant_id}:{today}",
                    "last_activity",
                    datetime.now().isoformat()
                )
            
            logger.debug(f"✅ Metrics updated for seller {seller_id} - {message_type}")
            
        except Exception as e:
            logger.error(f"Error updating metrics on message: {e}")
    
    async def get_daily_metrics_summary(self, tenant_id: int, date: Optional[str] = None) -> Dict:
        """Get daily metrics summary for all sellers (CEO dashboard)"""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        try:
            # Try Redis cache first
            redis_client = await self.get_redis_client()
            if redis_client:
                cache_key = f"daily:summary:tenant:{tenant_id}:{date}"
                cached = await redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            
            # Calculate fresh summary
            summary = await self._calculate_daily_summary(tenant_id, date)
            
            # Cache for 1 hour
            if redis_client:
                await redis_client.setex(
                    cache_key,
                    3600,  # 1 hour
                    json.dumps(summary, default=str)
                )
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting daily metrics summary: {e}")
            return await self._calculate_daily_summary(tenant_id, date)
    
    async def _calculate_daily_summary(self, tenant_id: int, date: str) -> Dict:
        """Calculate daily metrics summary for CEO dashboard"""
        try:
            # Get total conversations today
            total_convs_today = await db.fetchval("""
                SELECT COUNT(DISTINCT from_number)
                FROM chat_messages
                WHERE tenant_id = $1
                AND assigned_at::date = $2::date
                AND assigned_seller_id IS NOT NULL
            """, tenant_id, date) or 0
            
            # Get unassigned conversations today
            unassigned_convs_today = await db.fetchval("""
                SELECT COUNT(DISTINCT from_number)
                FROM chat_messages
                WHERE tenant_id = $1
                AND created_at::date = $2::date
                AND assigned_seller_id IS NULL
            """, tenant_id, date) or 0
            
            # Get active sellers today
            active_sellers_today = await db.fetchval("""
                SELECT COUNT(DISTINCT assigned_seller_id)
                FROM chat_messages
                WHERE tenant_id = $1
                AND assigned_at::date = $2::date
                AND assigned_seller_id IS NOT NULL
            """, tenant_id, date) or 0
            
            # Get conversions today
            conversions_today = await db.fetchval("""
                SELECT COUNT(*)
                FROM leads
                WHERE tenant_id = $1
                AND status IN ('converted', 'closed_won')
                AND updated_at::date = $2::date
            """, tenant_id, date) or 0
            
            # Get top performers today
            top_performers = await db.fetch("""
                SELECT 
                    u.id as seller_id,
                    u.first_name,
                    u.last_name,
                    u.role,
                    COUNT(DISTINCT cm.from_number) as conversations_today,
                    COUNT(DISTINCT CASE WHEN l.status IN ('converted', 'closed_won') THEN l.id END) as conversions_today
                FROM users u
                LEFT JOIN chat_messages cm ON u.id = cm.assigned_seller_id
                    AND cm.tenant_id = $1
                    AND cm.assigned_at::date = $2::date
                LEFT JOIN leads l ON u.id = l.assigned_seller_id
                    AND l.tenant_id = $1
                    AND l.updated_at::date = $2::date
                WHERE u.tenant_id = $1
                AND u.status = 'active'
                AND u.role IN ('setter', 'closer', 'professional', 'ceo')
                GROUP BY u.id, u.first_name, u.last_name, u.role
                ORDER BY conversations_today DESC, conversions_today DESC
                LIMIT 5
            """, tenant_id, date)
            
            return {
                "date": date,
                "total_conversations_today": int(total_convs_today),
                "unassigned_conversations_today": int(unassigned_convs_today),
                "active_sellers_today": int(active_sellers_today),
                "conversions_today": int(conversions_today),
                "top_performers": [dict(performer) for performer in top_performers],
                "calculated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating daily summary: {e}")
            return {
                "date": date,
                "total_conversations_today": 0,
                "unassigned_conversations_today": 0,
                "active_sellers_today": 0,
                "conversions_today": 0,
                "top_performers": [],
                "calculated_at": datetime.now().isoformat(),
                "error": str(e)
            }
    
    async def get_system_health_metrics(self) -> Dict:
        """Get system health metrics for monitoring"""
        try:
            # Database health
            db_health = await db.fetchval("SELECT 1") == 1
            
            # Redis health
            redis_health = False
            redis_client = await self.get_redis_client()
            if redis_client:
                try:
                    await redis_client.ping()
                    redis_health = True
                except:
                    redis_health = False
            
            # Metrics calculation health
            metrics_health = await db.fetchval("""
                SELECT COUNT(*) > 0 
                FROM seller_metrics 
                WHERE metrics_calculated_at >= NOW() - INTERVAL '1 hour'
            """) or False
            
            return {
                "database": db_health,
                "redis": redis_health,
                "metrics_calculation": bool(metrics_health),
                "timestamp": datetime.now().isoformat(),
                "cache_hit_rate": await self._calculate_cache_hit_rate() if redis_health else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting system health metrics: {e}")
            return {
                "database": False,
                "redis": False,
                "metrics_calculation": False,
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    async def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate (simplified)"""
        try:
            redis_client = await self.get_redis_client()
            if not redis_client:
                return 0.0
            
            # This is a simplified calculation
            # In production, you'd want more sophisticated tracking
            info = await redis_client.info('stats')
            hits = info.get('keyspace_hits', 0)
            misses = info.get('keyspace_misses', 0)
            total = hits + misses
            
            if total > 0:
                return round((hits / total) * 100, 2)
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating cache hit rate: {e}")
            return 0.0
    
    async def cleanup_old_cache(self, days: int = 7):
        """Cleanup old cache entries"""
        try:
            redis_client = await self.get_redis_client()
            if not redis_client:
                return
            
            # This is a simplified cleanup
            # In production, use Redis TTL or scheduled cleanup
            pattern = "metrics:seller:*"
            keys = await redis_client.keys(pattern)
            
            old_keys = []
            for key in keys:
                ttl = await redis_client.ttl(key)
                if ttl < 0:  # No TTL or expired
                    old_keys.append(key)
            
            if old_keys:
                await redis_client.delete(*old_keys)
                logger.info(f"✅ Cleaned up {len(old_keys)} old cache entries")
            
        except Exception as e:
            logger.error(f"Error cleaning up old cache: {e}")
    
    async def get_metrics_insights(self, seller_id: UUID, tenant_id: int) -> Dict:
        """Get AI-powered insights from metrics"""
        try:
            # Get recent metrics
            recent_metrics = await db.fetchrow("""
                SELECT *
                FROM seller_metrics
                WHERE seller_id = $1
                AND tenant_id = $2
                ORDER BY metrics_period_start DESC
                LIMIT 1
            """, seller_id, tenant_id)
            
            if not recent_metrics:
                return {"insights": [], "seller_id": str(seller_id)}
            
            metrics = dict(recent_metrics)
            insights = []
            
            # Generate insights based on metrics
            if metrics.get('avg_response_time_seconds', 0) > 600:  # > 10 minutes
                insights.append({
                    "type": "warning",
                    "title": "Tiempo de respuesta alto",
                    "message": f"Tiempo promedio de respuesta: {metrics['avg_response_time_seconds']}s. Objetivo: <300s",
                    "suggestion": "Revisar notificaciones y priorizar respuestas rápidas"
                })
            
            if metrics.get('conversion_rate', 0) < 10:  # < 10% conversion
                insights.append({
                    "type": "improvement",
                    "title": "Tasa de conversión baja",
                    "message": f"Tasa de conversión: {metrics['conversion_rate']}%. Objetivo: >20%",
                    "suggestion": "Focalizar en leads calificados y mejorar técnicas de cierre"
                })
            
            if metrics.get('active_conversations', 0) < 3:
                insights.append({
                    "type": "opportunity",
                    "title": "Baja actividad de conversaciones",
                    "message": f"Conversaciones activas: {metrics['active_conversations']}. Objetivo: 5+",
                    "suggestion": "Tomar más conversaciones asignadas y aumentar engagement"
                })
            
            if metrics.get('leads_converted', 0) > 0 and metrics.get('leads_assigned', 0) > 0:
                conversion_rate = (metrics['leads_converted'] / metrics['leads_assigned']) * 100
                if conversion_rate > 30:
                    insights.append({
                        "type": "success",
                        "title": "Alta efectividad en conversiones",
                        "message": f"Excelente tasa de conversión: {conversion_rate:.1f}%",
                        "suggestion": "Mantener estrategias actuales y mentorar a otros vendedores"
                    })
            
            return {
                "insights": insights,
                "seller_id": str(seller_id),
                "period": metrics.get('metrics_period_start'),
                "metrics_analyzed": len(insights) > 0
            }
            
        except Exception as e:
            logger.error(f"Error getting metrics insights: {e}")
            return {"insights": [], "seller_id": str(seller_id), "error": str(e)}

# Singleton instance
metrics_cache_service = MetricsCacheService()