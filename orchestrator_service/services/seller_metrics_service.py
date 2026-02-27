"""
Service for calculating and managing seller performance metrics
"""
import logging
from typing import Dict, List, Optional, Tuple
from uuid import UUID
from datetime import datetime, timedelta
from db import db

logger = logging.getLogger(__name__)

class SellerMetricsService:
    
    async def calculate_seller_metrics(
        self,
        seller_id: UUID,
        tenant_id: int,
        period_days: int = 7
    ) -> Dict:
        """
        Calculate comprehensive metrics for a seller
        Returns: {"success": bool, "metrics": dict, "period": dict}
        """
        try:
            period_start = datetime.now() - timedelta(days=period_days)
            period_end = datetime.now()
            
            # 1. Conversation metrics
            conv_metrics = await self._calculate_conversation_metrics(
                seller_id, tenant_id, period_start, period_end
            )
            
            # 2. Message metrics
            msg_metrics = await self._calculate_message_metrics(
                seller_id, tenant_id, period_start, period_end
            )
            
            # 3. Lead conversion metrics
            lead_metrics = await self._calculate_lead_metrics(
                seller_id, tenant_id, period_start, period_end
            )
            
            # 4. Response time metrics
            response_metrics = await self._calculate_response_metrics(
                seller_id, tenant_id, period_start, period_end
            )
            
            # 5. Activity metrics
            activity_metrics = await self._calculate_activity_metrics(
                seller_id, tenant_id, period_start, period_end
            )
            
            # Combine all metrics
            metrics = {
                **conv_metrics,
                **msg_metrics,
                **lead_metrics,
                **response_metrics,
                **activity_metrics,
                "seller_id": str(seller_id),
                "tenant_id": tenant_id,
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "calculated_at": datetime.now().isoformat()
            }
            
            # 6. Save to database
            await self._save_metrics_to_db(seller_id, tenant_id, metrics, period_start, period_end)
            
            return {
                "success": True,
                "metrics": metrics,
                "period": {
                    "start": period_start.isoformat(),
                    "end": period_end.isoformat(),
                    "days": period_days
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating seller metrics: {e}")
            return {"success": False, "message": f"Error: {str(e)}"}
    
    async def _calculate_conversation_metrics(
        self,
        seller_id: UUID,
        tenant_id: int,
        period_start: datetime,
        period_end: datetime
    ) -> Dict:
        """Calculate conversation-related metrics"""
        try:
            # Total conversations assigned in period
            total_convs = await db.fetchval("""
                SELECT COUNT(DISTINCT from_number)
                FROM chat_messages
                WHERE assigned_seller_id = $1
                AND tenant_id = $2
                AND assigned_at BETWEEN $3 AND $4
            """, seller_id, tenant_id, period_start, period_end) or 0
            
            # Active conversations (assigned in last 24h)
            active_convs = await db.fetchval("""
                SELECT COUNT(DISTINCT from_number)
                FROM chat_messages
                WHERE assigned_seller_id = $1
                AND tenant_id = $2
                AND assigned_at >= NOW() - INTERVAL '24 hours'
            """, seller_id, tenant_id) or 0
            
            # Conversations assigned today
            convs_today = await db.fetchval("""
                SELECT COUNT(DISTINCT from_number)
                FROM chat_messages
                WHERE assigned_seller_id = $1
                AND tenant_id = $2
                AND assigned_at::date = CURRENT_DATE
            """, seller_id, tenant_id) or 0
            
            # Average conversation duration
            avg_duration = await db.fetchval("""
                SELECT AVG(EXTRACT(EPOCH FROM (MAX(created_at) - MIN(created_at)))) / 60
                FROM chat_messages
                WHERE assigned_seller_id = $1
                AND tenant_id = $2
                AND assigned_at BETWEEN $3 AND $4
                GROUP BY from_number
            """, seller_id, tenant_id, period_start, period_end) or 0
            
            return {
                "total_conversations": int(total_convs),
                "active_conversations": int(active_convs),
                "conversations_assigned_today": int(convs_today),
                "avg_conversation_duration_minutes": round(float(avg_duration), 1)
            }
            
        except Exception as e:
            logger.error(f"Error calculating conversation metrics: {e}")
            return {
                "total_conversations": 0,
                "active_conversations": 0,
                "conversations_assigned_today": 0,
                "avg_conversation_duration_minutes": 0
            }
    
    async def _calculate_message_metrics(
        self,
        seller_id: UUID,
        tenant_id: int,
        period_start: datetime,
        period_end: datetime
    ) -> Dict:
        """Calculate message-related metrics"""
        try:
            # Messages sent by seller
            messages_sent = await db.fetchval("""
                SELECT COUNT(*)
                FROM chat_messages
                WHERE assigned_seller_id = $1
                AND tenant_id = $2
                AND role = 'assistant'
                AND created_at BETWEEN $3 AND $4
            """, seller_id, tenant_id, period_start, period_end) or 0
            
            # Messages received from leads
            messages_received = await db.fetchval("""
                SELECT COUNT(*)
                FROM chat_messages cm
                WHERE cm.assigned_seller_id = $1
                AND cm.tenant_id = $2
                AND cm.role = 'user'
                AND cm.created_at BETWEEN $3 AND $4
            """, seller_id, tenant_id, period_start, period_end) or 0
            
            # Total chat minutes
            chat_minutes = await db.fetchval("""
                SELECT SUM(EXTRACT(EPOCH FROM (MAX(created_at) - MIN(created_at)))) / 60
                FROM chat_messages
                WHERE assigned_seller_id = $1
                AND tenant_id = $2
                AND created_at BETWEEN $3 AND $4
                GROUP BY from_number
            """, seller_id, tenant_id, period_start, period_end) or 0
            
            return {
                "total_messages_sent": int(messages_sent),
                "total_messages_received": int(messages_received),
                "total_chat_minutes": round(float(chat_minutes), 1),
                "message_ratio": round(messages_sent / max(messages_received, 1), 2)
            }
            
        except Exception as e:
            logger.error(f"Error calculating message metrics: {e}")
            return {
                "total_messages_sent": 0,
                "total_messages_received": 0,
                "total_chat_minutes": 0,
                "message_ratio": 0
            }
    
    async def _calculate_lead_metrics(
        self,
        seller_id: UUID,
        tenant_id: int,
        period_start: datetime,
        period_end: datetime
    ) -> Dict:
        """Calculate lead conversion metrics"""
        try:
            # Leads assigned
            leads_assigned = await db.fetchval("""
                SELECT COUNT(*)
                FROM leads
                WHERE assigned_seller_id = $1
                AND tenant_id = $2
                AND created_at BETWEEN $3 AND $4
            """, seller_id, tenant_id, period_start, period_end) or 0
            
            # Leads converted (status = 'converted' or similar)
            leads_converted = await db.fetchval("""
                SELECT COUNT(*)
                FROM leads
                WHERE assigned_seller_id = $1
                AND tenant_id = $2
                AND status IN ('converted', 'closed_won', 'client')
                AND created_at BETWEEN $3 AND $4
            """, seller_id, tenant_id, period_start, period_end) or 0
            
            # Conversion rate
            conversion_rate = round((leads_converted / max(leads_assigned, 1)) * 100, 2)
            
            # Prospecting metrics
            prospects_generated = await db.fetchval("""
                SELECT COUNT(*)
                FROM leads
                WHERE assigned_seller_id = $1
                AND tenant_id = $2
                AND lead_source = 'PROSPECTING'
                AND created_at BETWEEN $3 AND $4
            """, seller_id, tenant_id, period_start, period_end) or 0
            
            prospects_converted = await db.fetchval("""
                SELECT COUNT(*)
                FROM leads
                WHERE assigned_seller_id = $1
                AND tenant_id = $2
                AND lead_source = 'PROSPECTING'
                AND status IN ('converted', 'closed_won', 'client')
                AND created_at BETWEEN $3 AND $4
            """, seller_id, tenant_id, period_start, period_end) or 0
            
            return {
                "leads_assigned": int(leads_assigned),
                "leads_converted": int(leads_converted),
                "conversion_rate": conversion_rate,
                "prospects_generated": int(prospects_generated),
                "prospects_converted": int(prospects_converted),
                "prospect_conversion_rate": round((prospects_converted / max(prospects_generated, 1)) * 100, 2)
            }
            
        except Exception as e:
            logger.error(f"Error calculating lead metrics: {e}")
            return {
                "leads_assigned": 0,
                "leads_converted": 0,
                "conversion_rate": 0,
                "prospects_generated": 0,
                "prospects_converted": 0,
                "prospect_conversion_rate": 0
            }
    
    async def _calculate_response_metrics(
        self,
        seller_id: UUID,
        tenant_id: int,
        period_start: datetime,
        period_end: datetime
    ) -> Dict:
        """Calculate response time metrics"""
        try:
            # Get response times between user messages and seller responses
            response_times = await db.fetch("""
                WITH user_messages AS (
                    SELECT 
                        from_number,
                        created_at as user_time,
                        LEAD(created_at) OVER (PARTITION BY from_number ORDER BY created_at) as next_user_time
                    FROM chat_messages
                    WHERE tenant_id = $2
                    AND from_number IN (
                        SELECT DISTINCT from_number 
                        FROM chat_messages 
                        WHERE assigned_seller_id = $1 AND tenant_id = $2
                    )
                    AND role = 'user'
                    AND created_at BETWEEN $3 AND $4
                ),
                seller_responses AS (
                    SELECT 
                        from_number,
                        created_at as response_time
                    FROM chat_messages
                    WHERE assigned_seller_id = $1
                    AND tenant_id = $2
                    AND role = 'assistant'
                    AND created_at BETWEEN $3 AND $4
                )
                SELECT 
                    EXTRACT(EPOCH FROM (sr.response_time - um.user_time)) as response_seconds
                FROM user_messages um
                JOIN seller_responses sr ON um.from_number = sr.from_number
                WHERE sr.response_time > um.user_time
                AND (um.next_user_time IS NULL OR sr.response_time < um.next_user_time)
                ORDER BY um.user_time
            """, seller_id, tenant_id, period_start, period_end)
            
            if response_times:
                response_seconds = [rt['response_seconds'] for rt in response_times if rt['response_seconds']]
                avg_response_seconds = sum(response_seconds) / len(response_seconds) if response_seconds else 0
                
                # Calculate percentiles
                sorted_times = sorted(response_seconds)
                p50 = sorted_times[len(sorted_times) // 2] if sorted_times else 0
                p90 = sorted_times[int(len(sorted_times) * 0.9)] if len(sorted_times) > 1 else 0
                
                return {
                    "avg_response_time_seconds": round(avg_response_seconds, 1),
                    "response_time_p50_seconds": round(p50, 1),
                    "response_time_p90_seconds": round(p90, 1),
                    "total_responses_analyzed": len(response_times)
                }
            else:
                return {
                    "avg_response_time_seconds": 0,
                    "response_time_p50_seconds": 0,
                    "response_time_p90_seconds": 0,
                    "total_responses_analyzed": 0
                }
                
        except Exception as e:
            logger.error(f"Error calculating response metrics: {e}")
            return {
                "avg_response_time_seconds": 0,
                "response_time_p50_seconds": 0,
                "response_time_p90_seconds": 0,
                "total_responses_analyzed": 0
            }
    
    async def _calculate_activity_metrics(
        self,
        seller_id: UUID,
        tenant_id: int,
        period_start: datetime,
        period_end: datetime
    ) -> Dict:
        """Calculate activity and engagement metrics"""
        try:
            # Days active in period
            active_days = await db.fetchval("""
                SELECT COUNT(DISTINCT DATE(created_at))
                FROM chat_messages
                WHERE assigned_seller_id = $1
                AND tenant_id = $2
                AND created_at BETWEEN $3 AND $4
            """, seller_id, tenant_id, period_start, period_end) or 0
            
            # Last activity timestamp
            last_activity = await db.fetchval("""
                SELECT MAX(created_at)
                FROM chat_messages
                WHERE assigned_seller_id = $1
                AND tenant_id = $2
            """, seller_id, tenant_id)
            
            # Average messages per day
            total_days = (period_end - period_start).days or 1
            avg_messages_per_day = await db.fetchval("""
                SELECT COUNT(*) / $3
                FROM chat_messages
                WHERE assigned_seller_id = $1
                AND tenant_id = $2
                AND created_at BETWEEN $4 AND $5
            """, seller_id, tenant_id, total_days, period_start, period_end) or 0
            
            return {
                "active_days_in_period": int(active_days),
                "last_activity_at": last_activity.isoformat() if last_activity else None,
                "avg_messages_per_day": round(float(avg_messages_per_day), 1),
                "activity_rate_percent": round((active_days / total_days) * 100, 1)
            }
            
        except Exception as e:
            logger.error(f"Error calculating activity metrics: {e}")
            return {
                "active_days_in_period": 0,
                "last_activity_at": None,
                "avg_messages_per_day": 0,
                "activity_rate_percent": 0
            }
    
    async def _save_metrics_to_db(
        self,
        seller_id: UUID,
        tenant_id: int,
        metrics: Dict,
        period_start: datetime,
        period_end: datetime
    ):
        """Save calculated metrics to database"""
        try:
            await db.execute("""
                INSERT INTO seller_metrics (
                    seller_id, tenant_id,
                    total_conversations, active_conversations, conversations_assigned_today,
                    total_messages_sent, total_messages_received, avg_response_time_seconds,
                    leads_assigned, leads_converted, conversion_rate,
                    prospects_generated, prospects_converted,
                    total_chat_minutes, avg_session_duration_minutes,
                    last_activity_at, metrics_calculated_at,
                    metrics_period_start, metrics_period_end
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11,
                    $12, $13, $14, $15, $16, $17, $18, $19
                )
                ON CONFLICT (seller_id, tenant_id, metrics_period_start) 
                DO UPDATE SET
                    total_conversations = EXCLUDED.total_conversations,
                    active_conversations = EXCLUDED.active_conversations,
                    conversations_assigned_today = EXCLUDED.conversations_assigned_today,
                    total_messages_sent = EXCLUDED.total_messages_sent,
                    total_messages_received = EXCLUDED.total_messages_received,
                    avg_response_time_seconds = EXCLUDED.avg_response_time_seconds,
                    leads_assigned = EXCLUDED.leads_assigned,
                    leads_converted = EXCLUDED.leads_converted,
                    conversion_rate = EXCLUDED.conversion_rate,
                    prospects_generated = EXCLUDED.prospects_generated,
                    prospects_converted = EXCLUDED.prospects_converted,
                    total_chat_minutes = EXCLUDED.total_chat_minutes,
                    avg_session_duration_minutes = EXCLUDED.avg_session_duration_minutes,
                    last_activity_at = EXCLUDED.last_activity_at,
                    metrics_calculated_at = EXCLUDED.metrics_calculated_at,
                    metrics_period_end = EXCLUDED.metrics_period_end
            """,
                seller_id, tenant_id,
                metrics.get('total_conversations', 0),
                metrics.get('active_conversations', 0),
                metrics.get('conversations_assigned_today', 0),
                metrics.get('total_messages_sent', 0),
                metrics.get('total_messages_received', 0),
                metrics.get('avg_response_time_seconds', 0),
                metrics.get('leads_assigned', 0),
                metrics.get('leads_converted', 0),
                metrics.get('conversion_rate', 0),
                metrics.get('prospects_generated', 0),
                metrics.get('prospects_converted', 0),
                metrics.get('total_chat_minutes', 0),
                metrics.get('avg_conversation_duration_minutes', 0),
                metrics.get('last_activity_at'),
                datetime.now(),
                period_start,
                period_end
            )
            
        except Exception as e:
            logger.error(f"Error saving metrics to DB: {e}")
    
    async def get_seller_metrics(
        self,
        seller_id: UUID,
        tenant_id: int,
        period_days: int = 7
    ) -> Dict:
        """Get seller metrics from database or calculate if not exists"""
        try:
            period_start = datetime.now() - timedelta(days=period_days)
            
            # Try to get from database first
            metrics = await db.fetchrow("""
                SELECT * FROM seller_metrics
                WHERE seller_id = $1
                AND tenant_id = $2
                AND metrics_period_start >= $3
                ORDER BY metrics_period_start DESC
                LIMIT 1
            """, seller_id, tenant_id, period_start)
            
            if metrics:
                return {
                    "success": True,
                    "metrics": dict(metrics),
                    "source": "database",
                    "cached": True
                }
            
            # Calculate fresh metrics
            return await self.calculate_seller_metrics(seller_id, tenant_id, period_days)
            
        except Exception as e:
            logger.error(f"Error getting seller metrics: {e}")
            return {"success": False, "message": f"Error: {str(e)}"}
    
    async def get_team_metrics(
        self,
        tenant_id: int,
        period_days: int = 7
    ) -> Dict:
        """Get metrics for all sellers in a team"""
        try:
            # Get all active sellers
            sellers = await db.fetch("""
                SELECT id, first_name, last_name, role
                FROM users
                WHERE tenant_id = $1
                AND status = 'active'
                AND role IN ('setter', 'closer', 'professional', 'ceo')
            """, tenant_id)
            
            team_metrics = []
            for seller in sellers:
                metrics_result = await self.get_seller_metrics(
                    seller['id'], tenant_id, period_days
                )
                
                if metrics_result['success']:
                    seller_data = {
                        "seller_id": str(seller['id']),
                        "first_name": seller['first_name'],
                        "last_name": seller['last_name'],
                        "role": seller['role'],
                        "metrics": metrics_result.get('metrics', {})
                    }
                    team_metrics.append(seller_data)
            
            # Calculate team totals
            totals = self._calculate_team_totals(team_metrics)
            
            return {
                "success": True,
                "team_metrics": team_metrics,
                "totals": totals,
                "period_days": period_days,
                "seller_count": len(team_metrics)
            }
            
        except Exception as e:
            logger.error(f"Error getting team metrics: {e}")
            return {"success": False, "message": f"Error: {str(e)}"}
    
    def _calculate_team_totals(self, team_metrics: List[Dict]) -> Dict:
        """Calculate totals for team metrics"""
        totals = {
            "total_conversations": 0,
            "active_conversations": 0,
            "total_messages_sent": 0,
            "total_messages_received": 0,
            "leads_assigned": 0,
            "leads_converted": 0,
            "prospects_generated": 0,
            "prospects_converted": 0,
            "seller_count": len(team_metrics)
        }
        
        for seller in team_metrics:
            metrics = seller.get('metrics', {})
            totals['total_conversations'] += metrics.get('total_conversations', 0)
            totals['active_conversations'] += metrics.get('active_conversations', 0)
            totals['total_messages_sent'] += metrics.get('total_messages_sent', 0)
            totals['total_messages_received'] += metrics.get('total_messages_received', 0)
            totals['leads_assigned'] += metrics.get('leads_assigned', 0)
            totals['leads_converted'] += metrics.get('leads_converted', 0)
            totals['prospects_generated'] += metrics.get('prospects_generated', 0)
            totals['prospects_converted'] += metrics.get('prospects_converted', 0)
        
        # Calculate team averages
        if totals['seller_count'] > 0:
            totals['avg_conversion_rate'] = round(
                (totals['leads_converted'] / max(totals['leads_assigned'], 1)) * 100, 2
            )
            totals['avg_response_time'] = "N/A"  # Would need individual response times
            totals['avg_conversations_per_seller'] = round(
                totals['total_conversations'] / totals['seller_count'], 1
            )
        
        return totals
    
    async def update_metrics_for_new_message(
        self,
        seller_id: UUID,
        tenant_id: int,
        message_type: str  # 'sent' or 'received'
    ):
        """Update metrics in real-time when a new message is sent/received"""
        try:
            # Get current metrics for today
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            if message_type == 'sent':
                await db.execute("""
                    INSERT INTO seller_metrics 
                    (seller_id, tenant_id, total_messages_sent, metrics_period_start, metrics_period_end)
                    VALUES ($1, $2, 1, $3, $3 + INTERVAL '1 day')
                    ON CONFLICT (seller_id, tenant_id, metrics_period_start) 
                    DO UPDATE SET 
                        total_messages_sent = seller_metrics.total_messages_sent + 1,
                        metrics_calculated_at = NOW()
                """, seller_id, tenant_id, today_start)
            
            elif message_type == 'received':
                await db.execute("""
                    INSERT INTO seller_metrics 
                    (seller_id, tenant_id, total_messages_received, metrics_period_start, metrics_period_end)
                    VALUES ($1, $2, 1, $3, $3 + INTERVAL '1 day')
                    ON CONFLICT (seller_id, tenant_id, metrics_period_start) 
                    DO UPDATE SET 
                        total_messages_received = seller_metrics.total_messages_received + 1,
                        metrics_calculated_at = NOW()
                """, seller_id, tenant_id, today_start)
            
            # Update last activity
            await db.execute("""
                UPDATE seller_metrics
                SET last_activity_at = NOW()
                WHERE seller_id = $1 AND tenant_id = $2
                AND metrics_period_start = $3
            """, seller_id, tenant_id, today_start)
            
        except Exception as e:
            logger.error(f"Error updating metrics for new message: {e}")
    
    async def get_performance_leaderboard(
        self,
        tenant_id: int,
        metric: str = "conversion_rate",
        limit: int = 10
    ) -> List[Dict]:
        """Get leaderboard of top performing sellers"""
        try:
            valid_metrics = ["conversion_rate", "leads_converted", "total_conversations", 
                           "total_messages_sent", "avg_response_time_seconds"]
            
            if metric not in valid_metrics:
                metric = "conversion_rate"
            
            order_by = f"{metric} DESC" if metric != "avg_response_time_seconds" else "avg_response_time_seconds ASC"
            
            query = f"""
                SELECT 
                    sm.seller_id,
                    sm.{metric},
                    u.first_name,
                    u.last_name,
                    u.role,
                    sm.metrics_period_start
                FROM seller_metrics sm
                JOIN users u ON sm.seller_id = u.id
                WHERE sm.tenant_id = $1
                AND sm.metrics_period_start >= NOW() - INTERVAL '30 days'
                AND u.status = 'active'
                ORDER BY {order_by}
                LIMIT $2
            """
            
            leaderboard = await db.fetch(query, tenant_id, limit)
            return [dict(row) for row in leaderboard]
            
        except Exception as e:
            logger.error(f"Error getting performance leaderboard: {e}")
            return []
    
    async def get_daily_summary(self, tenant_id: int) -> Dict:
        """Obtener resumen diario de métricas para un tenant"""
        try:
            query = """
                SELECT 
                    COUNT(DISTINCT sm.seller_id) as active_sellers,
                    SUM(sm.total_conversations) as total_conversations,
                    SUM(sm.leads_converted) as leads_converted_today,
                    AVG(sm.avg_response_time_seconds) / 60 as avg_response_time_minutes,
                    MAX(sm.metrics_period_start) as last_updated
                FROM seller_metrics sm
                JOIN users u ON sm.seller_id = u.id
                WHERE sm.tenant_id = $1
                    AND sm.metrics_period_start >= DATE_TRUNC('day', NOW())
                    AND u.status = 'active'
                    AND u.role IN ('setter', 'closer')
            """
            
            result = await db.fetchrow(query, tenant_id)
            
            if result:
                return {
                    "active_sellers": result["active_sellers"] or 0,
                    "total_conversations": result["total_conversations"] or 0,
                    "leads_converted_today": result["leads_converted_today"] or 0,
                    "avg_response_time_minutes": float(result["avg_response_time_minutes"] or 0),
                    "last_updated": result["last_updated"].isoformat() if result["last_updated"] else None
                }
            else:
                return {
                    "active_sellers": 0,
                    "total_conversations": 0,
                    "leads_converted_today": 0,
                    "avg_response_time_minutes": 0,
                    "last_updated": None
                }
                
        except Exception as e:
            logger.error(f"Error getting daily summary: {e}")
            return {
                "active_sellers": 0,
                "total_conversations": 0,
                "leads_converted_today": 0,
                "avg_response_time_minutes": 0,
                "last_updated": None
            }
    
    async def refresh_all_metrics(self, tenant_id: int) -> Dict:
        """Refrescar métricas para todos los vendedores de un tenant"""
        try:
            # Obtener todos los vendedores activos del tenant
            query = """
                SELECT id FROM users 
                WHERE tenant_id = $1 
                    AND status = 'active' 
                    AND role IN ('setter', 'closer', 'ceo', 'professional')
            """
            
            sellers = await db.fetch(query, tenant_id)
            
            refreshed_count = 0
            error_count = 0
            
            for seller in sellers:
                try:
                    await self.calculate_seller_metrics(
                        seller_id=seller["id"],
                        tenant_id=tenant_id,
                        period_days=1  # Solo hoy
                    )
                    refreshed_count += 1
                except Exception as e:
                    logger.error(f"Error refreshing metrics for seller {seller['id']}: {e}")
                    error_count += 1
            
            return {
                "success": True,
                "refreshed_count": refreshed_count,
                "error_count": error_count,
                "total_sellers": len(sellers)
            }
            
        except Exception as e:
            logger.error(f"Error refreshing all metrics for tenant {tenant_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "refreshed_count": 0,
                "error_count": 0,
                "total_sellers": 0
            }

# Singleton instance
seller_metrics_service = SellerMetricsService()