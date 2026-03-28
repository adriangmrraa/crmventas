"""
Mention Service — DEV-43: Menciones @usuario en notas internas.
Parsea menciones, resuelve usuarios, envía notificaciones.
"""
import re
import logging
from typing import List, Optional
from uuid import UUID, uuid4

from db import db

logger = logging.getLogger("orchestrator")

# Regex para detectar @{Nombre Completo} o @nombre
MENTION_PATTERN = re.compile(r'@\{([^}]+)\}|@(\w+(?:\s\w+)?)')


async def parse_and_notify_mentions(
    content: str,
    tenant_id: int,
    note_id: UUID,
    author_id: UUID,
    lead_id: UUID,
    lead_name: str = "",
) -> List[dict]:
    """
    Parsea @menciones del contenido, inserta en note_mentions,
    y envía notificaciones a los mencionados.
    Returns lista de menciones resueltas.
    """
    mentions_found = MENTION_PATTERN.findall(content)
    if not mentions_found:
        return []

    # Extraer nombres de las menciones
    names = []
    for group1, group2 in mentions_found:
        name = group1 or group2  # group1 = {Nombre Completo}, group2 = nombre
        if name:
            names.append(name.strip())

    if not names:
        return []

    # Limitar a 5 menciones por nota
    names = names[:5]

    # Resolver usuarios del tenant
    resolved = []
    for name in names:
        user = await db.pool.fetchrow(
            """SELECT id, first_name, last_name, role FROM users
               WHERE tenant_id = $1 AND status = 'active'
                 AND (CONCAT(first_name, ' ', last_name) ILIKE $2
                      OR first_name ILIKE $2
                      OR last_name ILIKE $2)
               LIMIT 1""",
            tenant_id, f"%{name}%",
        )
        if user and user["id"] != author_id:
            resolved.append(user)

    if not resolved:
        return []

    # Insertar en note_mentions y enviar notificaciones
    result = []
    for user in resolved:
        mention_id = uuid4()
        await db.pool.execute(
            """INSERT INTO note_mentions (id, note_id, mentioned_user_id, tenant_id)
               VALUES ($1, $2, $3, $4)
               ON CONFLICT DO NOTHING""",
            mention_id, note_id, user["id"], tenant_id,
        )

        # Crear notificación
        try:
            from services.seller_notification_service import seller_notification_service, Notification
            if seller_notification_service and Notification:
                user_name = f"{user['first_name'] or ''} {user['last_name'] or ''}".strip()
                # Get author name
                author = await db.pool.fetchrow(
                    "SELECT first_name, last_name FROM users WHERE id = $1",
                    author_id,
                )
                author_name = f"{author['first_name'] or ''} {author['last_name'] or ''}".strip() if author else "Alguien"

                notif = Notification(
                    id=f"mention_{note_id}_{user['id']}",
                    tenant_id=tenant_id,
                    type="mention",
                    priority="high",
                    title=f"Te mencionaron en una nota",
                    message=f"{author_name} te mencionó en una nota del lead {lead_name}",
                    recipient_id=str(user["id"]),
                    sender_id=str(author_id),
                    related_entity_type="lead",
                    related_entity_id=str(lead_id),
                    metadata={"note_id": str(note_id), "author_name": author_name},
                )
                await seller_notification_service.create_notification(notif)
        except Exception as e:
            logger.warning(f"Could not send mention notification: {e}")

        # Emit via WebSocket
        try:
            from core.socket_manager import sio
            await sio.emit("NOTE_MENTION", {
                "note_id": str(note_id),
                "lead_id": str(lead_id),
                "mentioned_user_id": str(user["id"]),
                "author_id": str(author_id),
            }, room=f"notifications:{user['id']}")
        except Exception as e:
            logger.warning(f"Could not emit mention event: {e}")

        user_name = f"{user['first_name'] or ''} {user['last_name'] or ''}".strip()
        result.append({
            "user_id": str(user["id"]),
            "name": user_name,
            "role": user["role"],
        })

    return result


async def search_users_for_mention(tenant_id: int, query: str, limit: int = 10) -> list:
    """Busca usuarios del tenant por nombre parcial para autocomplete."""
    if not query or len(query) < 1:
        return []

    rows = await db.pool.fetch(
        """SELECT id, first_name, last_name, role FROM users
           WHERE tenant_id = $1 AND status = 'active'
             AND (first_name ILIKE $2 OR last_name ILIKE $2
                  OR CONCAT(first_name, ' ', last_name) ILIKE $2)
           ORDER BY first_name
           LIMIT $3""",
        tenant_id, f"%{query}%", limit,
    )

    return [
        {
            "id": str(r["id"]),
            "name": f"{r['first_name'] or ''} {r['last_name'] or ''}".strip(),
            "role": r["role"],
        }
        for r in rows
    ]
