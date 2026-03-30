"""
DEV-48 — AI Lead Summary Service
Genera resumen + score IA al derivar un lead de setter a closer.
Modelo configurable; default: gpt-4o-mini.
"""
import json
import logging
from typing import Optional

logger = logging.getLogger("ai_lead_summary")


async def generate_handoff_summary(
    tenant_id: int,
    lead_id: str,
    pool,
    model: str = "gpt-4o-mini",
) -> dict:
    """
    Genera un resumen inteligente del lead para el handoff setter → closer.
    Retorna dict con: summary, ai_score, score_breakdown, key_points.
    Fallback graceful si OpenAI no disponible.
    """
    import os
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("DEV-48: OPENAI_API_KEY no configurada, skipping AI summary")
        return {"summary": None, "ai_score": None, "score_breakdown": {}, "key_points": []}

    try:
        # 1. Obtener datos del lead
        lead_row = await pool.fetchrow(
            """
            SELECT l.first_name, l.last_name, l.phone_number, l.email,
                   l.status, l.score, l.tags, l.estimated_value,
                   l.created_at, l.source
            FROM leads l
            WHERE l.id = $1 AND l.tenant_id = $2
            """,
            lead_id if not isinstance(lead_id, str) else __import__('uuid').UUID(lead_id),
            tenant_id,
        )
        if not lead_row:
            return {"summary": None, "ai_score": None, "score_breakdown": {}, "key_points": []}

        # 2. Últimos 30 mensajes de chat
        messages_rows = await pool.fetch(
            """
            SELECT role, content, created_at
            FROM chat_messages
            WHERE tenant_id = $1 AND from_number = $2
            ORDER BY created_at DESC
            LIMIT 30
            """,
            tenant_id,
            lead_row["phone_number"],
        )
        chat_history = [
            {"role": r["role"], "content": r["content"][:500]}
            for r in reversed(messages_rows)
        ]

        # 3. Notas del lead
        notes_rows = await pool.fetch(
            """
            SELECT note_type, content, created_at
            FROM lead_notes
            WHERE lead_id = $1 AND tenant_id = $2 AND COALESCE(is_deleted, FALSE) = FALSE
            ORDER BY created_at DESC
            LIMIT 10
            """,
            lead_id if not isinstance(lead_id, str) else __import__('uuid').UUID(lead_id),
            tenant_id,
        )
        notes_text = "\n".join([f"[{n['note_type']}] {n['content'][:300]}" for n in notes_rows])

        # 4. Construir prompt
        lead_name = f"{lead_row['first_name'] or ''} {lead_row['last_name'] or ''}".strip()
        tags_str = ", ".join(json.loads(lead_row["tags"]) if lead_row["tags"] else [])
        chat_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in chat_history[-20:]])

        prompt = f"""Eres un analista senior de ventas. Analiza la siguiente información del lead y genera un resumen ejecutivo para el closer que va a tomar el caso.

LEAD: {lead_name} | Tel: {lead_row['phone_number']} | Status: {lead_row['status']} | Tags: {tags_str}
Valor estimado: ${lead_row['estimated_value'] or 0} | Fuente: {lead_row['source']}

HISTORIAL DE CHAT (últimos mensajes):
{chat_text or 'Sin historial de chat'}

NOTAS DEL SETTER:
{notes_text or 'Sin notas'}

Responde EXCLUSIVAMENTE con un JSON con esta estructura:
{{
  "summary": "Párrafo de 2-3 oraciones con el contexto clave del lead para el closer",
  "ai_score": <entero 0-100 que representa la probabilidad de cierre>,
  "score_breakdown": {{
    "engagement": <0-100>,
    "intent": <0-100>,
    "budget_signals": <0-100>,
    "urgency": <0-100>
  }},
  "key_points": ["punto clave 1", "punto clave 2", "punto clave 3"],
  "objections_detected": ["objeción 1 si aplica"],
  "recommended_approach": "Una frase con la estrategia recomendada para el closer"
}}"""

        # 5. Llamar OpenAI
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=api_key)

        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=800,
            temperature=0.3,
        )

        result_text = response.choices[0].message.content
        result = json.loads(result_text)

        # Validar campos mínimos
        result.setdefault("summary", "")
        result.setdefault("ai_score", 50)
        result.setdefault("score_breakdown", {})
        result.setdefault("key_points", [])
        result.setdefault("objections_detected", [])
        result.setdefault("recommended_approach", "")

        # Clamp score 0-100
        result["ai_score"] = max(0, min(100, int(result["ai_score"])))

        logger.info(f"DEV-48: AI summary generated for lead {lead_id} — score={result['ai_score']}")
        return result

    except Exception as e:
        logger.error(f"DEV-48: Error generating AI summary for lead {lead_id}: {e}")
        return {
            "summary": None,
            "ai_score": None,
            "score_breakdown": {},
            "key_points": [],
            "error": str(e),
        }


async def save_handoff_note(
    tenant_id: int,
    lead_id: str,
    author_id: str,
    summary_data: dict,
    pool,
) -> Optional[str]:
    """Guarda el resumen IA como lead_note type='handoff' con structured_data."""
    try:
        import uuid as uuid_lib
        lead_uuid = uuid_lib.UUID(lead_id) if isinstance(lead_id, str) else lead_id
        author_uuid = uuid_lib.UUID(author_id) if isinstance(author_id, str) else author_id

        content_parts = []
        if summary_data.get("summary"):
            content_parts.append(summary_data["summary"])
        if summary_data.get("key_points"):
            content_parts.append("Puntos clave: " + "; ".join(summary_data["key_points"]))
        if summary_data.get("ai_score") is not None:
            content_parts.append(f"Score IA: {summary_data['ai_score']}/100")

        content = " | ".join(content_parts) if content_parts else "Resumen IA no disponible"

        row = await pool.fetchrow(
            """
            INSERT INTO lead_notes (tenant_id, lead_id, author_id, note_type, content, structured_data, visibility)
            VALUES ($1, $2, $3, 'handoff', $4, $5, 'setter_closer')
            RETURNING id
            """,
            tenant_id,
            lead_uuid,
            author_uuid,
            content,
            json.dumps(summary_data),
        )

        # Actualizar score en lead si ai_score está disponible
        if summary_data.get("ai_score") is not None:
            await pool.execute(
                "UPDATE leads SET score = $1, score_updated_at = NOW() WHERE id = $2 AND tenant_id = $3",
                summary_data["ai_score"],
                lead_uuid,
                tenant_id,
            )

        return str(row["id"]) if row else None
    except Exception as e:
        logger.error(f"DEV-48: Error saving handoff note: {e}")
        return None
