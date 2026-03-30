"""
DEV-49 — Frustration Detection Service
Detecta frustración en mensajes de leads mediante pattern matching léxico
y validación con IA. Escala automáticamente si score > 70.
"""
import re
import json
import logging
from typing import Optional

logger = logging.getLogger("frustration_detection")

# ─── Patrones de frustración (score léxico) ───────────────────────────────────
FRUSTRATION_PATTERNS = {
    "explicit_human_request": {
        "patterns": [
            r"\bhablar con (?:una )?persona\b",
            r"\b(?:agente|asesor|humano|persona real|operador)\b",
            r"\bno quiero (?:robot|bot|máquina)\b",
            r"\bpóngame con alguien\b",
            r"\bquiero hablar con (?:alguien|una persona)\b",
        ],
        "weight": 55,
    },
    "anger": {
        "patterns": [
            r"\bme (?:cansé|harté|molestó|enojé)\b",
            r"\bestoy (?:harto|enojado|molesto|indignado)\b",
            r"\bno (?:sirve|funciona|entiendo nada)\b",
            r"\binútil\b",
            r"\bpésimo\b",
            r"\bdesastre\b",
            r"\bno puedo creer\b",
            r"\bque (?:vergüenza|porquería)\b",
        ],
        "weight": 45,
    },
    "confusion_repetition": {
        "patterns": [
            r"\bya (?:lo )?dije\b",
            r"\bya pregunté\b",
            r"\bme (?:están |)repiten?\b",
            r"\bno (?:me |)entend(?:és|iste|en)\b",
            r"\bcuántas veces\b",
            r"\bya (?:expliqué|respondí)\b",
        ],
        "weight": 35,
    },
    "abandonment": {
        "patterns": [
            r"\bme voy\b",
            r"\bchau\b",
            r"\bno (?:me interesa|quiero|gracias)\b",
            r"\bcancelo\b",
            r"\bolvídalo\b",
            r"\bdéjame\b",
            r"\bbusco (?:otra|otro)\b",
        ],
        "weight": 40,
    },
    "profanity": {
        "patterns": [
            r"\bqué mierda\b",
            r"\bputa\b",
            r"\bbolud[oa]\b",
            r"\bcarajo\b",
        ],
        "weight": 50,
    },
}

ESCALATION_THRESHOLD = 70  # Score >= 70 → escalar
AI_VALIDATION_THRESHOLD = 40  # Score léxico >= 40 → confirmar con IA


def _compute_lexical_score(message: str) -> tuple[int, list[str]]:
    """Analiza el mensaje con regex y retorna (score, categorías_disparadas)."""
    text = message.lower()
    total_weight = 0
    triggered = []

    for category, data in FRUSTRATION_PATTERNS.items():
        for pattern in data["patterns"]:
            if re.search(pattern, text):
                total_weight += data["weight"]
                triggered.append(category)
                break  # Una coincidencia por categoría es suficiente

    # Clamp a 100
    return min(total_weight, 100), triggered


async def _validate_with_ai(
    message: str,
    recent_messages: list,
    model: str = "gpt-4o-mini",
) -> int:
    """Llama a OpenAI para validar el score de frustración. Retorna 0-100."""
    import os
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return 0

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=api_key)

        context = "\n".join([f"{m.get('role','?').upper()}: {m.get('content','')[:200]}" for m in recent_messages[-5:]])
        prompt = f"""Analiza el siguiente mensaje de un cliente en un CRM de ventas y determina su nivel de frustración.

Mensajes recientes de contexto:
{context}

Mensaje actual: "{message}"

Responde ÚNICAMENTE con un JSON:
{{"frustration_score": <0-100>, "reason": "<breve explicación>"}}

Donde 0=nada frustrado, 100=extremadamente frustrado/a punto de abandonar."""

        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=100,
            temperature=0.1,
        )
        data = json.loads(response.choices[0].message.content)
        return max(0, min(100, int(data.get("frustration_score", 0))))
    except Exception as e:
        logger.warning(f"DEV-49: AI validation error: {e}")
        return 0


async def detect_frustration(
    message: str,
    recent_messages: list,
    tenant_id: int,
    lead_phone: str,
    pool,
    model: str = "gpt-4o-mini",
) -> dict:
    """
    Pipeline principal de detección de frustración.
    Retorna: {score, triggered_categories, should_escalate, source}
    """
    # Fase 1: Pattern matching léxico
    lexical_score, triggered = _compute_lexical_score(message)

    # Fase 2: Validación IA si score léxico supera umbral
    ai_score = 0
    source = "lexical"
    if lexical_score >= AI_VALIDATION_THRESHOLD:
        ai_score = await _validate_with_ai(message, recent_messages, model)
        source = "lexical+ai"
        # Combinar: 40% léxico + 60% IA
        final_score = int(lexical_score * 0.4 + ai_score * 0.6)
    else:
        final_score = lexical_score

    should_escalate = final_score >= ESCALATION_THRESHOLD

    logger.info(
        f"DEV-49: phone={lead_phone} lex={lexical_score} ai={ai_score} "
        f"final={final_score} escalate={should_escalate} categories={triggered}"
    )

    return {
        "score": final_score,
        "lexical_score": lexical_score,
        "ai_score": ai_score,
        "triggered_categories": triggered,
        "should_escalate": should_escalate,
        "source": source,
    }


async def handle_escalation(
    tenant_id: int,
    lead_phone: str,
    conv_id: Optional[str],
    score: int,
    message: str,
    pool,
    sio=None,
) -> bool:
    """
    Al detectar frustración crítica:
    1. Pausa la conversación (24h)
    2. Crea notificación crítica al seller asignado
    3. Emite evento Socket.IO
    4. Registra en lead_notes + activity_events
    """
    try:
        import uuid as uuid_lib
        from datetime import datetime, timedelta, timezone

        async with pool.acquire() as conn:
            # 1. Obtener info del lead y seller asignado
            lead_row = await conn.fetchrow(
                """
                SELECT l.id, l.first_name, l.last_name, l.assigned_seller_id
                FROM leads l
                WHERE l.tenant_id = $1 AND l.phone_number = $2
                LIMIT 1
                """,
                tenant_id, lead_phone,
            )
            if not lead_row:
                logger.warning(f"DEV-49: Lead con phone {lead_phone} no encontrado en tenant {tenant_id}")
                return False

            lead_id = lead_row["id"]
            lead_name = f"{lead_row['first_name'] or ''} {lead_row['last_name'] or ''}".strip() or lead_phone
            seller_id = lead_row["assigned_seller_id"]

            async with conn.transaction():
                # 2. Pausa conversación si conv_id dado, o buscar por phone
                if conv_id:
                    await conn.execute(
                        """
                        UPDATE chat_conversations
                        SET paused_until = $1, pause_reason = 'frustration_detected', updated_at = NOW()
                        WHERE id = $2 AND tenant_id = $3
                        """,
                        datetime.now(timezone.utc) + timedelta(hours=24),
                        uuid_lib.UUID(conv_id) if isinstance(conv_id, str) else conv_id,
                        tenant_id,
                    )
                else:
                    await conn.execute(
                        """
                        UPDATE chat_conversations
                        SET paused_until = $1, pause_reason = 'frustration_detected', updated_at = NOW()
                        WHERE tenant_id = $2 AND session_id = $3
                        """,
                        datetime.now(timezone.utc) + timedelta(hours=24),
                        tenant_id,
                        lead_phone,
                    )

                # 3. Actualizar lead con score de frustración
                await conn.execute(
                    """
                    UPDATE leads
                    SET frustration_score = $1, frustration_detected_at = NOW(),
                        frustration_escalated_to = $2, updated_at = NOW()
                    WHERE id = $3 AND tenant_id = $4
                    """,
                    score,
                    seller_id,
                    lead_id,
                    tenant_id,
                )

                # 4. Crear lead_note automática
                note_content = (
                    f"⚠️ Frustración detectada (score: {score}/100). "
                    f"Mensaje: \"{message[:200]}\". "
                    f"Conversación pausada 24h. Requiere intervención humana inmediata."
                )
                await conn.execute(
                    """
                    INSERT INTO lead_notes (tenant_id, lead_id, note_type, content, structured_data, visibility)
                    VALUES ($1, $2, 'internal', $3, $4, 'all')
                    """,
                    tenant_id,
                    lead_id,
                    note_content,
                    json.dumps({
                        "type": "frustration_escalation",
                        "score": score,
                        "message": message[:500],
                        "auto_generated": True,
                    }),
                )

                # 5. Notificación crítica al seller
                if seller_id:
                    import time
                    notif_id = f"frustration_{lead_id}_{int(time.time())}"
                    await conn.execute(
                        """
                        INSERT INTO notifications (id, tenant_id, type, title, message, priority,
                            recipient_id, related_entity_type, related_entity_id, metadata)
                        VALUES ($1, $2, 'frustration_alert', $3, $4, 'critical', $5, 'lead', $6, $7)
                        ON CONFLICT (id) DO NOTHING
                        """,
                        notif_id, tenant_id,
                        f"⚠️ Lead {lead_name} — Frustración detectada",
                        f"Score de frustración: {score}/100. El agente IA ha sido pausado. Intervención urgente requerida.",
                        str(seller_id),
                        str(lead_id),
                        json.dumps({"score": score, "message": message[:200], "phone": lead_phone}),
                    )

        # 6. Emitir Socket.IO
        if sio:
            try:
                await sio.emit("FRUSTRATION_ESCALATION", {
                    "tenant_id": tenant_id,
                    "lead_id": str(lead_id),
                    "lead_name": lead_name,
                    "phone": lead_phone,
                    "score": score,
                    "message": message[:200],
                    "seller_id": str(seller_id) if seller_id else None,
                })
            except Exception as e:
                logger.warning(f"DEV-49: Socket.IO emit error: {e}")

        logger.info(f"DEV-49: Escalation handled for lead {lead_id} (score={score})")
        return True

    except Exception as e:
        logger.error(f"DEV-49: Escalation error for phone {lead_phone}: {e}")
        return False
