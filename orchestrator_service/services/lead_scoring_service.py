"""
Lead Scoring Service — CRM VENTAS
Calculates a 0-100 score for each lead based on:
  - Engagement (0-40): message activity, response speed, recency
  - Fit (0-30): source quality, tags, completeness
  - Behavior (0-30): urgency signals, pricing mentions, demo requests
"""

import json
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


async def calculate_lead_score(pool, lead_id, tenant_id: int) -> dict:
    """Calculate and store lead score. Returns { score, breakdown }."""
    try:
        lead = await pool.fetchrow(
            "SELECT * FROM leads WHERE id = $1 AND tenant_id = $2",
            lead_id, tenant_id
        )
        if not lead:
            return {"score": 0, "breakdown": {}}

        engagement = await _score_engagement(pool, lead, tenant_id)
        fit = _score_fit(lead)
        behavior = await _score_behavior(pool, lead, tenant_id)

        total = min(100, engagement["score"] + fit["score"] + behavior["score"])
        breakdown = {
            "engagement": engagement,
            "fit": fit,
            "behavior": behavior,
            "calculated_at": datetime.now(timezone.utc).isoformat(),
        }

        await pool.execute(
            "UPDATE leads SET score = $1, score_breakdown = $2::jsonb, score_updated_at = NOW() WHERE id = $3 AND tenant_id = $4",
            total, json.dumps(breakdown), lead_id, tenant_id
        )

        return {"score": total, "breakdown": breakdown}

    except Exception as e:
        logger.error(f"Error calculating lead score for {lead_id}: {e}")
        return {"score": 0, "breakdown": {"error": str(e)}}


async def _score_engagement(pool, lead, tenant_id: int) -> dict:
    """Engagement Score (0-40): message frequency, recency, conversation depth."""
    score = 0
    details = {}

    phone = lead.get("phone_number", "")
    if not phone:
        return {"score": 0, "details": {"no_phone": True}}

    # Message count (0-15)
    msg_count = await pool.fetchval(
        """SELECT COUNT(*) FROM chat_messages cm
           JOIN chat_conversations cc ON cm.conversation_id = cc.id
           WHERE cc.external_user_id = $1 AND cc.tenant_id = $2""",
        phone, tenant_id
    ) or 0

    if msg_count >= 20:
        score += 15
    elif msg_count >= 10:
        score += 12
    elif msg_count >= 5:
        score += 8
    elif msg_count >= 1:
        score += 4
    details["messages"] = msg_count

    # Recency — last message (0-15)
    last_msg = await pool.fetchval(
        """SELECT MAX(cm.created_at) FROM chat_messages cm
           JOIN chat_conversations cc ON cm.conversation_id = cc.id
           WHERE cc.external_user_id = $1 AND cc.tenant_id = $2""",
        phone, tenant_id
    )

    if last_msg:
        days_ago = (datetime.now(timezone.utc) - last_msg.replace(tzinfo=timezone.utc)).days
        if days_ago <= 1:
            score += 15
        elif days_ago <= 3:
            score += 12
        elif days_ago <= 7:
            score += 8
        elif days_ago <= 14:
            score += 4
        elif days_ago <= 30:
            score += 2
        details["last_message_days_ago"] = days_ago
    else:
        details["last_message_days_ago"] = None

    # Conversation depth — multiple sessions (0-10)
    conv_count = await pool.fetchval(
        """SELECT COUNT(*) FROM chat_conversations
           WHERE external_user_id = $1 AND tenant_id = $2""",
        phone, tenant_id
    ) or 0
    if conv_count >= 3:
        score += 10
    elif conv_count >= 2:
        score += 6
    elif conv_count >= 1:
        score += 3
    details["conversations"] = conv_count

    return {"score": min(40, score), "details": details}


def _score_fit(lead) -> dict:
    """Fit Score (0-30): source quality, data completeness, tags."""
    score = 0
    details = {}

    # Source quality (0-15)
    source = (lead.get("source") or "").lower()
    source_scores = {
        "meta_ads": 15, "google_ads": 15, "meta_lead_form": 14,
        "referral": 12, "website": 10, "prospecting": 8,
        "whatsapp_inbound": 6, "manual": 4, "import": 3,
    }
    src_score = source_scores.get(source, 5)
    score += src_score
    details["source"] = source
    details["source_score"] = src_score

    # Data completeness (0-10)
    completeness = 0
    if lead.get("first_name"): completeness += 2
    if lead.get("last_name"): completeness += 2
    if lead.get("email"): completeness += 3
    if lead.get("company"): completeness += 3
    score += completeness
    details["completeness"] = completeness

    # Tags (0-5)
    tags = lead.get("tags") or []
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except:
            tags = []
    tag_score = min(5, len(tags) * 2)
    score += tag_score
    details["tags_count"] = len(tags)

    return {"score": min(30, score), "details": details}


async def _score_behavior(pool, lead, tenant_id: int) -> dict:
    """Behavior Score (0-30): urgency signals in messages."""
    score = 0
    details = {}

    phone = lead.get("phone_number", "")
    if not phone:
        return {"score": 0, "details": {}}

    # Get recent messages content
    messages = await pool.fetch(
        """SELECT cm.content FROM chat_messages cm
           JOIN chat_conversations cc ON cm.conversation_id = cc.id
           WHERE cc.external_user_id = $1 AND cc.tenant_id = $2
           AND cm.role = 'user'
           ORDER BY cm.created_at DESC LIMIT 20""",
        phone, tenant_id
    )

    all_text = " ".join((m["content"] or "").lower() for m in messages)

    # Urgency keywords (0-10)
    urgency_words = ["urgente", "rapido", "necesito ya", "cuanto antes", "hoy", "ahora", "inmediato"]
    urgency_hits = sum(1 for w in urgency_words if w in all_text)
    urgency_score = min(10, urgency_hits * 3)
    score += urgency_score
    details["urgency_signals"] = urgency_hits

    # Pricing/value interest (0-10)
    pricing_words = ["precio", "costo", "cuanto sale", "presupuesto", "cotizacion", "descuento", "plan", "paquete"]
    pricing_hits = sum(1 for w in pricing_words if w in all_text)
    pricing_score = min(10, pricing_hits * 3)
    score += pricing_score
    details["pricing_interest"] = pricing_hits

    # Demo/meeting request (0-10)
    demo_words = ["demo", "reunion", "llamada", "agendar", "cita", "conocer", "probar", "presentacion"]
    demo_hits = sum(1 for w in demo_words if w in all_text)
    demo_score = min(10, demo_hits * 4)
    score += demo_score
    details["demo_interest"] = demo_hits

    return {"score": min(30, score), "details": details}


async def decay_scores(pool, tenant_id: int):
    """Reduce scores for leads with no recent activity (run every 15 min)."""
    try:
        # Leads with score > 0 and no message in last 7 days lose 2 points
        result = await pool.execute("""
            UPDATE leads SET score = GREATEST(0, score - 2), score_updated_at = NOW()
            WHERE tenant_id = $1 AND score > 0
            AND id NOT IN (
                SELECT DISTINCT l.id FROM leads l
                JOIN chat_conversations cc ON cc.external_user_id = l.phone_number AND cc.tenant_id = l.tenant_id
                JOIN chat_messages cm ON cm.conversation_id = cc.id
                WHERE l.tenant_id = $1 AND cm.created_at > NOW() - INTERVAL '7 days'
            )
            AND (score_updated_at IS NULL OR score_updated_at < NOW() - INTERVAL '1 hour')
        """, tenant_id)
        logger.info(f"Lead score decay applied for tenant {tenant_id}: {result}")
    except Exception as e:
        logger.error(f"Error in score decay: {e}")


async def batch_calculate_scores(pool, tenant_id: int, limit: int = 50):
    """Calculate scores for leads that don't have one yet or are stale."""
    try:
        leads = await pool.fetch("""
            SELECT id FROM leads
            WHERE tenant_id = $1
            AND (score IS NULL OR score = 0 OR score_updated_at IS NULL OR score_updated_at < NOW() - INTERVAL '1 hour')
            ORDER BY updated_at DESC LIMIT $2
        """, tenant_id, limit)

        for lead in leads:
            await calculate_lead_score(pool, lead["id"], tenant_id)

        logger.info(f"Batch scored {len(leads)} leads for tenant {tenant_id}")
    except Exception as e:
        logger.error(f"Error in batch scoring: {e}")
