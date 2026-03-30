import logging
from typing import List, dict
from db import db
import datetime

logger = logging.getLogger(__name__)

class AnalyticsService:
    async def get_funnel_analytics(self, tenant_id: int):
        """
        Calculates sales funnel metrics:
        - Lead distribution by status
        - Conversion rates between key stages
        - Potential revenue (sum of estimated_value)
        """
        # 1. Distribution by status
        status_query = """
            SELECT status, COUNT(*) as count, SUM(estimated_value) as total_value
            FROM leads 
            WHERE tenant_id = $1
            GROUP BY status
        """
        status_rows = await db.fetch(status_query, tenant_id)
        
        # 2. Conversion metrics (using lead_status_history)
        # We want to see how many unique leads passed through each key stage
        stages = ['nuevo', 'contactado', 'calificado', 'llamada_agendada', 'negociacion', 'cerrado_ganado']
        
        funnel_data = []
        for stage in stages:
            # Count leads that ever reached this stage (including current status)
            count_query = """
                SELECT COUNT(DISTINCT lead_id) 
                FROM lead_status_history 
                WHERE tenant_id = $1 AND to_status_code = $2
            """
            
            # Plus leads that were born in 'nuevo' (they don't have history entry for going to 'nuevo' usually)
            if stage == 'nuevo':
                count_query = """
                    SELECT COUNT(*) FROM leads WHERE tenant_id = $1
                """
                count = await db.fetchval(count_query, tenant_id)
            else:
                count = await db.fetchval(count_query, tenant_id, stage)
                
            funnel_data.append({
                "stage": stage,
                "count": count or 0
            })

        # Calculate conversion rates (%)
        for i in range(len(funnel_data)):
            if i == 0:
                funnel_data[i]["conversion_rate"] = 100
            else:
                prev_count = funnel_data[i-1]["count"]
                curr_count = funnel_data[i]["count"]
                funnel_data[i]["conversion_rate"] = round((curr_count / prev_count * 100), 2) if prev_count > 0 else 0

        # 3. Revenue Metrics
        revenue_query = """
            SELECT 
                SUM(estimated_value) FILTER (WHERE status NOT IN ('cerrado_ganado', 'cerrado_perdido')) as potential_revenue,
                SUM(conversion_value) FILTER (WHERE status = 'cerrado_ganado') as actual_revenue
            FROM leads
            WHERE tenant_id = $1
        """
        rev_row = await db.fetchrow(revenue_query, tenant_id)

        return {
            "status_distribution": [dict(r) for r in status_rows],
            "funnel": funnel_data,
            "revenue": {
                "potential": float(rev_row['potential_revenue'] or 0),
                "actual": float(rev_row['actual_revenue'] or 0)
            }
        }

analytics_service = AnalyticsService()
