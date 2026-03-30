"""
DEV-47 — Reactivation Service
Secuencias automáticas de follow-up para leads inactivos.
Lógica: si ventana 24h abierta → mensaje libre. Si no → template HSM.
"""
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger("reactivation")


async def check_and_trigger_sequences(tenant_id: int, pool, sio=None):
    """
    Job principal (cada 30 min):
    Busca leads inactivos que califican para una secuencia de reactivación
    y crea entradas pending en reactivation_logs.
    """
    try:
        # Obtener secuencias activas del tenant
        sequences = await pool.fetch(
            """
            SELECT id, name, trigger_after_days, target_statuses
            FROM reactivation_sequences
            WHERE tenant_id = $1 AND is_active = TRUE
            """,
            tenant_id,
        )

        if not sequences:
            return

        for seq in sequences:
            trigger_days = seq["trigger_after_days"]
            target_statuses = seq["target_statuses"] or ["sin_respuesta", "seguimiento_pendiente"]

            # Buscar leads candidatos: inactivos, con status en target_statuses,
            # sin log de reactivación pendiente/enviado para esta secuencia
            cutoff = datetime.now(timezone.utc) - timedelta(days=trigger_days)

            candidates = await pool.fetch(
                """
                SELECT l.id, l.phone_number, l.first_name, l.last_name,
                       l.assigned_seller_id, l.updated_at
                FROM leads l
                WHERE l.tenant_id = $1
                  AND l.status = ANY($2)
                  AND l.updated_at < $3
                  AND l.status != 'merged'
                  AND NOT EXISTS (
                    SELECT 1 FROM reactivation_logs rl
                    WHERE rl.lead_id = l.id
                      AND rl.sequence_id = $4
                      AND rl.status IN ('pending', 'sent')
                  )
                LIMIT 50
                """,
                tenant_id,
                target_statuses,
                cutoff,
                seq["id"],
            )

            # Obtener el primer paso de la secuencia
            first_step = await pool.fetchrow(
                """
                SELECT id, step_order, delay_hours, message_type,
                       template_id, template_name, template_params, free_text_message
                FROM reactivation_steps
                WHERE sequence_id = $1
                ORDER BY step_order ASC
                LIMIT 1
                """,
                seq["id"],
            )

            if not first_step:
                logger.warning(f"DEV-47: Secuencia {seq['id']} sin pasos configurados")
                continue

            for lead in candidates:
                scheduled = datetime.now(timezone.utc) + timedelta(hours=first_step["delay_hours"])
                try:
                    await pool.execute(
                        """
                        INSERT INTO reactivation_logs
                            (tenant_id, lead_id, sequence_id, step_id, status, scheduled_at)
                        VALUES ($1, $2, $3, $4, 'pending', $5)
                        ON CONFLICT DO NOTHING
                        """,
                        tenant_id, lead["id"], seq["id"], first_step["id"], scheduled,
                    )
                    logger.info(
                        f"DEV-47: Scheduled reactivation for lead {lead['id']} "
                        f"via sequence '{seq['name']}' at {scheduled}"
                    )
                except Exception as e:
                    logger.warning(f"DEV-47: Error scheduling lead {lead['id']}: {e}")

    except Exception as e:
        logger.error(f"DEV-47: Error in check_and_trigger_sequences: {e}")


async def execute_pending_steps(tenant_id: int, pool, sio=None):
    """
    Job principal (cada 15 min):
    Ejecuta los pasos de reactivación que ya están listos para enviar.
    Lógica: ventana 24h abierta → free_text; cerrada → template HSM.
    """
    try:
        now = datetime.now(timezone.utc)

        # Obtener logs pendientes cuya scheduled_at ya pasó
        pending = await pool.fetch(
            """
            SELECT rl.id as log_id, rl.lead_id, rl.sequence_id, rl.step_id,
                   rs.message_type, rs.template_name, rs.template_params, rs.free_text_message,
                   rs.step_order,
                   l.phone_number, l.first_name, l.last_name,
                   l.assigned_seller_id
            FROM reactivation_logs rl
            JOIN reactivation_steps rs ON rs.id = rl.step_id
            JOIN leads l ON l.id = rl.lead_id
            WHERE rl.tenant_id = $1
              AND rl.status = 'pending'
              AND rl.scheduled_at <= $2
              AND l.status != 'merged'
            LIMIT 20
            """,
            tenant_id,
            now,
        )

        for step_log in pending:
            await _execute_step(tenant_id, step_log, pool, sio)

    except Exception as e:
        logger.error(f"DEV-47: Error in execute_pending_steps: {e}")


async def _execute_step(tenant_id: int, step_log, pool, sio=None):
    """Ejecuta un paso de reactivación individual."""
    log_id = step_log["log_id"]
    lead_phone = step_log["phone_number"]

    try:
        # Verificar si la ventana de 24h está abierta (último mensaje del lead < 24h)
        last_msg = await pool.fetchrow(
            """
            SELECT created_at FROM chat_messages
            WHERE from_number = $1 AND tenant_id = $2 AND role = 'user'
            ORDER BY created_at DESC LIMIT 1
            """,
            lead_phone, tenant_id,
        )

        window_open = False
        if last_msg:
            elapsed = datetime.now(timezone.utc) - last_msg["created_at"].replace(tzinfo=timezone.utc)
            window_open = elapsed.total_seconds() < 86400  # 24h

        # Determinar tipo de mensaje a enviar
        message_sent = False
        error_detail = None

        if window_open and step_log["free_text_message"]:
            # Ventana abierta: enviar mensaje libre
            message_sent = await _send_free_text(
                tenant_id, lead_phone,
                step_log["free_text_message"],
                step_log["first_name"] or "",
                pool,
            )
        elif step_log["template_name"]:
            # Fuera de ventana: enviar template HSM
            message_sent = await _send_template(
                tenant_id, lead_phone,
                step_log["template_name"],
                json.loads(step_log["template_params"]) if step_log["template_params"] else [],
                pool,
            )
        else:
            error_detail = "No hay mensaje libre ni template configurado para este paso"
            logger.warning(f"DEV-47: Step sin mensaje para log {log_id}: {error_detail}")

        # Actualizar log
        if message_sent:
            await pool.execute(
                "UPDATE reactivation_logs SET status = 'sent', sent_at = NOW() WHERE id = $1",
                log_id,
            )
            # Programar el próximo paso
            await _schedule_next_step(tenant_id, step_log, pool)
        else:
            await pool.execute(
                "UPDATE reactivation_logs SET status = 'failed', error_details = $1 WHERE id = $2",
                error_detail or "Send failed",
                log_id,
            )

    except Exception as e:
        logger.error(f"DEV-47: Error executing step log {log_id}: {e}")
        await pool.execute(
            "UPDATE reactivation_logs SET status = 'failed', error_details = $1 WHERE id = $2",
            str(e), log_id,
        )


async def _send_free_text(
    tenant_id: int, phone: str, message: str, first_name: str, pool
) -> bool:
    """Envía un mensaje de texto libre via YCloud."""
    try:
        # Personalizar mensaje con nombre
        personalized = message.replace("{nombre}", first_name or "").replace("{name}", first_name or "")

        from services.meta_messaging_client import send_whatsapp_message
        result = await send_whatsapp_message(
            tenant_id=tenant_id,
            to=phone,
            message=personalized,
            pool=pool,
        )
        return result is not None
    except ImportError:
        logger.warning("DEV-47: meta_messaging_client no disponible, usando fallback")
        return False
    except Exception as e:
        logger.error(f"DEV-47: Error sending free text to {phone}: {e}")
        return False


async def _send_template(
    tenant_id: int, phone: str, template_name: str, params: list, pool
) -> bool:
    """Envía un template HSM via YCloud."""
    try:
        from services.meta_messaging_client import send_whatsapp_template
        result = await send_whatsapp_template(
            tenant_id=tenant_id,
            to=phone,
            template_name=template_name,
            params=params,
            pool=pool,
        )
        return result is not None
    except ImportError:
        logger.warning("DEV-47: meta_messaging_client.send_whatsapp_template no disponible")
        return False
    except Exception as e:
        logger.error(f"DEV-47: Error sending template {template_name} to {phone}: {e}")
        return False


async def _schedule_next_step(tenant_id: int, current_step_log, pool):
    """Programa el siguiente paso de la secuencia si existe."""
    try:
        next_step = await pool.fetchrow(
            """
            SELECT id, step_order, delay_hours
            FROM reactivation_steps
            WHERE sequence_id = $1 AND step_order > $2
            ORDER BY step_order ASC
            LIMIT 1
            """,
            current_step_log["sequence_id"],
            current_step_log["step_order"],
        )
        if next_step:
            scheduled = datetime.now(timezone.utc) + timedelta(hours=next_step["delay_hours"])
            await pool.execute(
                """
                INSERT INTO reactivation_logs
                    (tenant_id, lead_id, sequence_id, step_id, status, scheduled_at)
                VALUES ($1, $2, $3, $4, 'pending', $5)
                ON CONFLICT DO NOTHING
                """,
                tenant_id,
                current_step_log["lead_id"],
                current_step_log["sequence_id"],
                next_step["id"],
                scheduled,
            )
    except Exception as e:
        logger.warning(f"DEV-47: Error scheduling next step: {e}")


async def cancel_sequence_for_lead(lead_id: str, tenant_id: int, reason: str, pool):
    """Cancela todos los pasos pendientes de reactivación para un lead (ej: respondió)."""
    try:
        import uuid as uuid_lib
        lead_uuid = uuid_lib.UUID(lead_id) if isinstance(lead_id, str) else lead_id
        result = await pool.execute(
            """
            UPDATE reactivation_logs
            SET status = 'cancelled', error_details = $1
            WHERE lead_id = $2 AND tenant_id = $3 AND status = 'pending'
            """,
            reason, lead_uuid, tenant_id,
        )
        logger.info(f"DEV-47: Cancelled reactivation for lead {lead_id}: {reason} ({result})")
    except Exception as e:
        logger.error(f"DEV-47: Error cancelling sequence for lead {lead_id}: {e}")
