"""
Sales Analytics Service — CRM VENTAS
Provides funnel analysis, revenue forecast, and sales velocity calculations.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Default stage probabilities for weighted forecast
STAGE_PROBABILITIES = {
    "new": 0.05,
    "contacted": 0.10,
    "qualified": 0.25,
    "proposal_sent": 0.40,
    "negotiation": 0.60,
    "won": 1.0,
    "lost": 0.0,
}


async def get_funnel_data(pool, tenant_id: int, days: int = 30) -> dict:
    """Conversion funnel: leads per stage with conversion rates."""
    try:
        since = datetime.now(timezone.utc) - timedelta(days=days)

        stages = await pool.fetch("""
            SELECT ls.code, ls.name, ls.color, ls.sort_order, ls.is_final,
                   COUNT(l.id) AS lead_count
            FROM lead_statuses ls
            LEFT JOIN leads l ON l.status = ls.code AND l.tenant_id = $1
                AND l.created_at >= $2
            WHERE ls.tenant_id = $1
            GROUP BY ls.id, ls.code, ls.name, ls.color, ls.sort_order, ls.is_final
            ORDER BY ls.sort_order ASC
        """, tenant_id, since)

        total_leads = await pool.fetchval(
            "SELECT COUNT(*) FROM leads WHERE tenant_id = $1 AND created_at >= $2",
            tenant_id, since
        ) or 1

        funnel = []
        for i, stage in enumerate(stages):
            count = stage["lead_count"] or 0
            conversion_from_top = round((count / total_leads) * 100, 1) if total_leads > 0 else 0
            prev_count = stages[i - 1]["lead_count"] if i > 0 and stages[i - 1]["lead_count"] else count
            conversion_from_prev = round((count / prev_count) * 100, 1) if prev_count > 0 and i > 0 else 100

            funnel.append({
                "code": stage["code"],
                "name": stage["name"],
                "color": stage["color"],
                "count": count,
                "conversion_from_top": conversion_from_top,
                "conversion_from_prev": conversion_from_prev,
                "is_final": stage["is_final"],
            })

        won = sum(s["count"] for s in funnel if s["code"] == "won")
        lost = sum(s["count"] for s in funnel if s["code"] == "lost")
        win_rate = round((won / (won + lost)) * 100, 1) if (won + lost) > 0 else 0

        return {
            "funnel": funnel,
            "total_leads": total_leads,
            "won": won,
            "lost": lost,
            "win_rate": win_rate,
            "period_days": days,
        }
    except Exception as e:
        logger.error(f"Funnel error: {e}")
        return {"funnel": [], "total_leads": 0, "won": 0, "lost": 0, "win_rate": 0}


async def get_forecast_data(pool, tenant_id: int) -> dict:
    """Revenue forecast: weighted pipeline value using per-lead close_probability when available."""
    try:
        leads = await pool.fetch("""
            SELECT l.status,
                   COALESCE(l.estimated_value, 0) AS estimated_value,
                   COALESCE(l.close_probability, 0) AS close_probability
            FROM leads l
            WHERE l.tenant_id = $1
            AND l.status NOT IN ('won', 'lost')
        """, tenant_id)

        # Aggregate per-stage using per-lead probability (fallback to STAGE_PROBABILITIES)
        stage_buckets: dict = {}
        for lead in leads:
            code = lead["status"] or "new"
            ev = float(lead["estimated_value"] or 0)
            cp = float(lead["close_probability"] or 0)
            # Use per-lead probability if explicitly set (> 0), else stage default
            prob = (cp / 100) if cp > 0 else STAGE_PROBABILITIES.get(code, 0.1)
            weighted = ev * prob

            if code not in stage_buckets:
                stage_buckets[code] = {"count": 0, "total_value": 0.0, "total_weighted": 0.0, "prob_sum": 0.0}
            stage_buckets[code]["count"] += 1
            stage_buckets[code]["total_value"] += ev
            stage_buckets[code]["total_weighted"] += weighted
            stage_buckets[code]["prob_sum"] += prob

        pipeline = []
        total_weighted = 0.0
        total_unweighted = 0.0

        for code, bucket in stage_buckets.items():
            count = bucket["count"]
            value = bucket["total_value"]
            weighted = bucket["total_weighted"]
            avg_prob = round(bucket["prob_sum"] / count, 4) if count > 0 else 0.0

            pipeline.append({
                "stage": code,
                "count": count,
                "total_value": round(value, 2),
                "probability": avg_prob,
                "weighted_value": round(weighted, 2),
            })

            total_weighted += weighted
            total_unweighted += value

        # Won revenue (actual)
        won_revenue = await pool.fetchval("""
            SELECT COALESCE(SUM(estimated_value), 0) FROM leads
            WHERE tenant_id = $1 AND status = 'won'
        """, tenant_id) or 0

        return {
            "pipeline": pipeline,
            "total_pipeline_value": round(total_unweighted, 2),
            "weighted_forecast": round(total_weighted, 2),
            "won_revenue": float(won_revenue),
            "total_expected": round(total_weighted + float(won_revenue), 2),
        }
    except Exception as e:
        logger.error(f"Forecast error: {e}")
        return {"pipeline": [], "total_pipeline_value": 0, "weighted_forecast": 0, "won_revenue": 0}


async def get_velocity_data(pool, tenant_id: int, days: int = 90) -> dict:
    """Sales velocity: avg cycle, deals/month, avg deal size, win rate."""
    try:
        since = datetime.now(timezone.utc) - timedelta(days=days)

        # Won deals in period
        won = await pool.fetch("""
            SELECT id, estimated_value, created_at, updated_at
            FROM leads WHERE tenant_id = $1 AND status = 'won' AND updated_at >= $2
        """, tenant_id, since)

        total_won = len(won)
        months = max(1, days / 30)
        deals_per_month = round(total_won / months, 1)

        # Avg deal size
        values = [float(w["estimated_value"] or 0) for w in won]
        avg_deal_size = round(sum(values) / max(1, len(values)), 2)

        # Avg cycle length (created_at to updated_at for won deals)
        cycles = []
        for w in won:
            if w["created_at"] and w["updated_at"]:
                delta = (w["updated_at"] - w["created_at"]).days
                if delta >= 0:
                    cycles.append(delta)
        avg_cycle = round(sum(cycles) / max(1, len(cycles)), 1)

        # Win rate
        total_closed = await pool.fetchval("""
            SELECT COUNT(*) FROM leads
            WHERE tenant_id = $1 AND status IN ('won', 'lost') AND updated_at >= $2
        """, tenant_id, since) or 1
        win_rate = round((total_won / total_closed) * 100, 1) if total_closed > 0 else 0

        # Velocity formula: (deals/month × avg_size × win_rate) / avg_cycle
        velocity = round((deals_per_month * avg_deal_size * (win_rate / 100)) / max(1, avg_cycle), 2)

        return {
            "deals_won": total_won,
            "deals_per_month": deals_per_month,
            "avg_deal_size": avg_deal_size,
            "avg_cycle_days": avg_cycle,
            "win_rate": win_rate,
            "velocity": velocity,
            "period_days": days,
        }
    except Exception as e:
        logger.error(f"Velocity error: {e}")
        return {"deals_won": 0, "deals_per_month": 0, "avg_deal_size": 0, "avg_cycle_days": 0, "win_rate": 0, "velocity": 0}
