"""
DEV-50 — Lead Deduplication Service
Normalización de teléfonos, detección de duplicados y fusión atómica de leads.
"""
import re
import json
import logging
import uuid as uuid_lib
import datetime
from typing import Optional

logger = logging.getLogger("deduplication")

AUTO_MERGE_THRESHOLD = 90   # >= 90% → auto-merge (actualmente no activo, va a review)
CANDIDATE_THRESHOLD = 60    # >= 60% → crear DuplicateCandidate para revisión


def normalize_phone(phone: str, country_code: str = "54") -> str:
    """
    Normaliza un teléfono al formato E.164 sin +.
    +54 9 11 1234-5678 → 5491112345678
    011 1234-5678 → 5491112345678
    """
    if not phone:
        return ""

    # Quitar todo excepto dígitos y +
    raw = re.sub(r"[^\d+]", "", phone.strip())

    # Si empieza con +, quitar el +
    if raw.startswith("+"):
        raw = raw[1:]

    # Si empieza con el código de país → normalizar "9" móvil argentina
    if raw.startswith(country_code):
        rest = raw[len(country_code):]
        # Argentina: código 9 + área + número
        if rest.startswith("9") and len(rest) > 10:
            return country_code + rest
        if not rest.startswith("9") and len(rest) == 10:
            # Agregar 9 para móvil argentino
            return country_code + "9" + rest
        return country_code + rest

    # Si empieza con 0 (formato local argentino: 011...)
    if raw.startswith("0") and len(raw) >= 10:
        # Quitar 0 inicial, agregar país + 9
        rest = raw[1:]
        if not rest.startswith("9"):
            rest = "9" + rest
        return country_code + rest

    # Si es un número corto (10-11 dígitos), agregar código de país
    if 10 <= len(raw) <= 11:
        if not raw.startswith("9"):
            raw = "9" + raw
        return country_code + raw

    return raw


def _name_similarity(name_a: str, name_b: str) -> float:
    """Similitud aproximada entre nombres (0.0 - 1.0)."""
    if not name_a or not name_b:
        return 0.0
    a = re.sub(r"\s+", " ", name_a.lower().strip())
    b = re.sub(r"\s+", " ", name_b.lower().strip())
    if a == b:
        return 1.0
    # Overlap de tokens
    tokens_a = set(a.split())
    tokens_b = set(b.split())
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


async def find_duplicates_for_lead(
    tenant_id: int,
    lead_id: str,
    phone: str,
    email: Optional[str],
    first_name: str,
    last_name: str,
    pool,
    limit: int = 5,
) -> list:
    """
    Busca duplicados candidatos para un lead dado.
    Retorna lista de {lead_id, confidence, match_reasons}.
    """
    candidates = {}
    lead_uuid = uuid_lib.UUID(lead_id) if isinstance(lead_id, str) else lead_id
    normalized = normalize_phone(phone)

    # 1. Match exacto por teléfono normalizado (confianza 90)
    if normalized:
        rows = await pool.fetch(
            """
            SELECT id, first_name, last_name, email, phone_number
            FROM leads
            WHERE tenant_id = $1 AND phone_number = $2 AND id != $3
            LIMIT 10
            """,
            tenant_id, normalized, lead_uuid,
        )
        for r in rows:
            lid = str(r["id"])
            if lid not in candidates:
                candidates[lid] = {"lead_id": lid, "confidence": 0, "match_reasons": [], "row": dict(r)}
            candidates[lid]["confidence"] = max(candidates[lid]["confidence"], 90)
            candidates[lid]["match_reasons"].append("phone_normalized_exact")

    # 2. Match exacto por email (confianza 85)
    if email:
        rows = await pool.fetch(
            """
            SELECT id, first_name, last_name, email, phone_number
            FROM leads
            WHERE tenant_id = $1 AND LOWER(email) = LOWER($2) AND id != $3
            LIMIT 10
            """,
            tenant_id, email, lead_uuid,
        )
        for r in rows:
            lid = str(r["id"])
            if lid not in candidates:
                candidates[lid] = {"lead_id": lid, "confidence": 0, "match_reasons": [], "row": dict(r)}
            candidates[lid]["confidence"] = max(candidates[lid]["confidence"], 85)
            candidates[lid]["match_reasons"].append("email_exact")

    # 3. Fuzzy match por nombre (si confidence ya existe o nombre muy similar)
    if first_name and last_name:
        full_name = f"{first_name} {last_name}".lower()
        rows = await pool.fetch(
            """
            SELECT id, first_name, last_name, email, phone_number
            FROM leads
            WHERE tenant_id = $1 AND id != $2
              AND (LOWER(first_name) LIKE $3 OR LOWER(last_name) LIKE $4)
            LIMIT 20
            """,
            tenant_id, lead_uuid,
            f"%{first_name.lower()}%",
            f"%{last_name.lower()}%",
        )
        for r in rows:
            lid = str(r["id"])
            candidate_name = f"{r['first_name'] or ''} {r['last_name'] or ''}".lower()
            similarity = _name_similarity(full_name, candidate_name)
            if similarity >= 0.7:
                if lid not in candidates:
                    candidates[lid] = {"lead_id": lid, "confidence": 0, "match_reasons": [], "row": dict(r)}
                name_conf = int(similarity * 70)  # max 70 por nombre solo
                candidates[lid]["confidence"] = max(candidates[lid]["confidence"], name_conf)
                candidates[lid]["match_reasons"].append(f"name_fuzzy_{int(similarity * 100)}pct")

    # Filtrar por umbral mínimo
    result = [
        {
            "lead_id": v["lead_id"],
            "confidence": v["confidence"],
            "match_reasons": list(set(v["match_reasons"])),
        }
        for v in candidates.values()
        if v["confidence"] >= CANDIDATE_THRESHOLD
    ]
    result.sort(key=lambda x: x["confidence"], reverse=True)
    return result[:limit]


async def create_duplicate_candidates(
    tenant_id: int,
    lead_id: str,
    duplicates: list,
    pool,
    lead_name: Optional[str] = None,
    lead_phone: Optional[str] = None,
):
    """Persiste los candidatos de duplicados en la tabla duplicate_candidates.
    Cuando confidence >= 85, emite notificación a CEO/admin (R6).
    """
    if not duplicates:
        return
    lead_uuid = uuid_lib.UUID(lead_id) if isinstance(lead_id, str) else lead_id
    high_confidence_found = False

    for dup in duplicates:
        dup_uuid = uuid_lib.UUID(dup["lead_id"]) if isinstance(dup["lead_id"], str) else dup["lead_id"]
        # Ordenar IDs para evitar duplicados bidireccionales
        a, b = sorted([str(lead_uuid), str(dup_uuid)])
        try:
            await pool.execute(
                """
                INSERT INTO duplicate_candidates (tenant_id, lead_a_id, lead_b_id, confidence, match_reasons)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (tenant_id, lead_a_id, lead_b_id) DO UPDATE
                    SET confidence = GREATEST(duplicate_candidates.confidence, EXCLUDED.confidence),
                        match_reasons = EXCLUDED.match_reasons
                """,
                tenant_id,
                uuid_lib.UUID(a),
                uuid_lib.UUID(b),
                dup["confidence"],
                json.dumps(dup["match_reasons"]),
            )
            if dup["confidence"] >= 85:
                high_confidence_found = True
        except Exception as e:
            logger.warning(f"DEV-50: Error creating duplicate candidate: {e}")

    # R6: notificar a CEO/admin cuando hay candidatos de alta confianza
    if high_confidence_found:
        try:
            await _notify_admin_duplicate_found(tenant_id, lead_name, lead_phone, pool)
        except Exception as e:
            logger.warning(f"DEV-50: Error sending duplicate notification: {e}")


async def _notify_admin_duplicate_found(
    tenant_id: int,
    lead_name: Optional[str],
    lead_phone: Optional[str],
    pool,
):
    """Crea una notificación para CEO/admin cuando se detecta un duplicado de alta confianza."""
    try:
        from services.seller_notification_service import seller_notification_service, Notification
    except ImportError:
        logger.warning("DEV-50: seller_notification_service not available for duplicate notification")
        return

    # Buscar CEO activo del tenant
    ceo_row = await pool.fetchrow(
        "SELECT id FROM users WHERE tenant_id = $1 AND role = 'ceo' AND status = 'active' LIMIT 1",
        tenant_id,
    )
    if not ceo_row:
        return

    display_name = lead_name or lead_phone or "Lead desconocido"
    display_phone = lead_phone or ""
    timestamp = datetime.datetime.utcnow().timestamp()

    notification = Notification(
        id=f"dup_{tenant_id}_{lead_phone}_{timestamp}",
        tenant_id=tenant_id,
        type="duplicate_found",
        title="Posible duplicado detectado",
        message=f"Posible duplicado detectado: {display_name} ({display_phone})",
        priority="high",
        recipient_id=str(ceo_row["id"]),
        related_entity_type="lead",
        related_entity_id=str(lead_phone) if lead_phone else None,
        metadata={"lead_name": display_name, "phone": display_phone},
    )

    await seller_notification_service.save_notifications([notification])
    await seller_notification_service.broadcast_notifications([notification])


async def merge_leads(
    tenant_id: int,
    primary_id: str,
    secondary_id: str,
    field_overrides: dict,
    resolved_by_id: str,
    pool,
) -> dict:
    """
    Fusiona secondary_id EN primary_id de forma atómica.
    - Mueve notas, tareas, eventos de actividad
    - Marca secondary como status='merged'
    - Resuelve el DuplicateCandidate
    """
    primary_uuid = uuid_lib.UUID(primary_id) if isinstance(primary_id, str) else primary_id
    secondary_uuid = uuid_lib.UUID(secondary_id) if isinstance(secondary_id, str) else secondary_id
    resolver_uuid = uuid_lib.UUID(resolved_by_id) if isinstance(resolved_by_id, str) else resolved_by_id

    async with pool.acquire() as conn:
        # Verificar soberanía: ambos leads deben pertenecer al tenant
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM leads WHERE tenant_id = $1 AND id = ANY($2)",
            tenant_id, [primary_uuid, secondary_uuid],
        )
        if count != 2:
            raise ValueError("Uno o ambos leads no pertenecen a este tenant")

        async with conn.transaction():
            # 1. Aplicar field_overrides al lead primario
            if field_overrides:
                allowed_fields = {
                    "first_name", "last_name", "email", "phone_number",
                    "company", "estimated_value", "source",
                }
                safe_overrides = {k: v for k, v in field_overrides.items() if k in allowed_fields}
                if safe_overrides:
                    set_clauses = [f"{k} = ${i+1}" for i, k in enumerate(safe_overrides.keys())]
                    params = list(safe_overrides.values())
                    params.extend([primary_uuid, tenant_id])
                    await conn.execute(
                        f"UPDATE leads SET {', '.join(set_clauses)}, updated_at = NOW() "
                        f"WHERE id = ${len(params)-1} AND tenant_id = ${len(params)}",
                        *params,
                    )

            # 2. Merge external_ids
            await conn.execute(
                """
                UPDATE leads
                SET external_ids = COALESCE(
                    (SELECT external_ids FROM leads WHERE id = $1) || '{}', '{}'
                ) || jsonb_build_object('merged_from', $2::text),
                updated_at = NOW()
                WHERE id = $1 AND tenant_id = $4
                """,
                primary_uuid, str(secondary_uuid), secondary_uuid, tenant_id,
            )

            # 3. Mover lead_notes
            await conn.execute(
                "UPDATE lead_notes SET lead_id = $1 WHERE lead_id = $2 AND tenant_id = $3",
                primary_uuid, secondary_uuid, tenant_id,
            )

            # 4. Mover lead_tasks
            await conn.execute(
                "UPDATE lead_tasks SET lead_id = $1 WHERE lead_id = $2 AND tenant_id = $3",
                primary_uuid, secondary_uuid, tenant_id,
            )

            # 5. Mover reactivation_logs
            await conn.execute(
                "UPDATE reactivation_logs SET lead_id = $1 WHERE lead_id = $2 AND tenant_id = $3",
                primary_uuid, secondary_uuid, tenant_id,
            )

            # 6. Mover activity_events
            await conn.execute(
                "UPDATE activity_events SET entity_id = $1 WHERE entity_id = $2::text AND entity_type = 'lead' AND tenant_id = $3",
                str(primary_uuid), str(secondary_uuid), tenant_id,
            )

            # 6b. Mover lead_status_history
            await conn.execute(
                "UPDATE lead_status_history SET lead_id = $1 WHERE lead_id = $2 AND tenant_id = $3",
                primary_uuid, secondary_uuid, tenant_id,
            )

            # 6c. Mover lead_status_trigger_logs
            await conn.execute(
                "UPDATE lead_status_trigger_logs SET lead_id = $1 WHERE lead_id = $2 AND tenant_id = $3",
                primary_uuid, secondary_uuid, tenant_id,
            )

            # 6d. Mover seller_agenda_events
            await conn.execute(
                "UPDATE seller_agenda_events SET lead_id = $1 WHERE lead_id = $2 AND tenant_id = $3",
                primary_uuid, secondary_uuid, tenant_id,
            )

            # 6e. Mover opportunities
            await conn.execute(
                "UPDATE opportunities SET lead_id = $1 WHERE lead_id = $2 AND tenant_id = $3",
                primary_uuid, secondary_uuid, tenant_id,
            )

            # 6f. Mover sales_transactions (via opportunity join — no direct lead_id)
            await conn.execute(
                """
                UPDATE sales_transactions st
                SET opportunity_id = st.opportunity_id
                FROM opportunities o
                WHERE o.id = st.opportunity_id
                  AND o.lead_id = $1
                  AND st.tenant_id = $2
                """,
                primary_uuid, tenant_id,
            )

            # 6g. Mover lead_tag_log (tabla creada condicionalmente, usar DO para IF EXISTS)
            await conn.execute(
                """
                DO $tag$ BEGIN
                    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'lead_tag_log') THEN
                        UPDATE lead_tag_log SET lead_id = $1 WHERE lead_id = $2 AND tenant_id = $3;
                    END IF;
                END $tag$;
                """,
                primary_uuid, secondary_uuid, tenant_id,
            )

            # 7. Soft-delete del lead secundario
            await conn.execute(
                """
                UPDATE leads
                SET status = 'merged',
                    external_ids = COALESCE(external_ids, '{}') || jsonb_build_object('merged_into', $1::text),
                    updated_at = NOW()
                WHERE id = $2 AND tenant_id = $3
                """,
                str(primary_uuid), secondary_uuid, tenant_id,
            )

            # 8. Resolver DuplicateCandidate
            a, b = sorted([str(primary_uuid), str(secondary_uuid)])
            await conn.execute(
                """
                UPDATE duplicate_candidates
                SET status = 'merged', resolved_by = $1, resolved_at = NOW()
                WHERE tenant_id = $2
                  AND lead_a_id = $3 AND lead_b_id = $4
                  AND status = 'pending'
                """,
                resolver_uuid, tenant_id,
                uuid_lib.UUID(a), uuid_lib.UUID(b),
            )

            # 9. Activity event
            await conn.execute(
                """
                INSERT INTO activity_events (tenant_id, actor_id, event_type, entity_type, entity_id, metadata)
                VALUES ($1, $2, 'lead_merged', 'lead', $3, $4)
                """,
                tenant_id, resolver_uuid, str(primary_uuid),
                json.dumps({"merged_from": str(secondary_uuid), "field_overrides": field_overrides}),
            )

    logger.info(f"DEV-50: Lead {secondary_id} merged into {primary_id} by {resolved_by_id}")
    return {"status": "merged", "primary_id": str(primary_uuid), "secondary_id": str(secondary_uuid)}
