"""
Internal Chat Service — SPEC-04
Team chat with fixed channels, DMs, and notification cards.
"""

import uuid
import logging
from typing import Optional

from db import db
from core.socket_manager import sio

logger = logging.getLogger(__name__)

FIXED_CHANNELS = ["general", "ventas", "operaciones"]
SUPERVISION_ROLES = ["ceo", "admin"]


def dm_canal_id(user_a: str, user_b: str) -> str:
    """Canonical DM channel ID. Always the same regardless of who initiates."""
    return "dm_" + "_".join(sorted([str(user_a), str(user_b)]))


class InternalChatService:
    """Service for internal team chat."""

    async def ensure_channels_exist(self, tenant_id: int) -> None:
        """Create fixed channels for a tenant if they don't exist."""
        async with db.pool.acquire() as conn:
            for canal in FIXED_CHANNELS:
                await conn.execute(
                    """INSERT INTO chat_conversaciones (canal_id, tenant_id, tipo, participantes)
                       VALUES ($1, $2, 'canal', '{}')
                       ON CONFLICT (canal_id, tenant_id) DO NOTHING""",
                    canal, tenant_id,
                )

    async def get_canales(self, tenant_id: int, user_id: str) -> dict:
        """Get fixed channels + user's DMs with unread counts."""
        async with db.pool.acquire() as conn:
            # Fixed channels
            canales = [
                {"canal_id": c, "label": c, "tipo": "canal"}
                for c in FIXED_CHANNELS
            ]

            # User's DMs
            dms = await conn.fetch(
                """SELECT c.canal_id, c.tipo, c.participantes, c.ultima_actividad,
                          COALESCE(n.count, 0) as no_leidos
                   FROM chat_conversaciones c
                   LEFT JOIN chat_dm_no_leidos n
                     ON n.canal_id = c.canal_id AND n.tenant_id = c.tenant_id AND n.user_id = $2
                   WHERE c.tenant_id = $1 AND c.tipo = 'dm'
                     AND $2 = ANY(c.participantes)
                   ORDER BY c.ultima_actividad DESC""",
                tenant_id, user_id,
            )

            dm_list = []
            for dm in dms:
                participantes = list(dm["participantes"])
                otro = [p for p in participantes if p != user_id]
                otro_id = otro[0] if otro else user_id

                # Get other participant info
                other_user = await conn.fetchrow(
                    "SELECT id, email, role FROM users WHERE id = $1",
                    uuid.UUID(otro_id),
                )

                dm_list.append({
                    "canal_id": dm["canal_id"],
                    "tipo": "dm",
                    "otro_participante": {
                        "id": otro_id,
                        "nombre": other_user["email"].split("@")[0] if other_user else otro_id,
                        "rol": other_user["role"] if other_user else "unknown",
                    } if other_user else {"id": otro_id, "nombre": otro_id, "rol": "unknown"},
                    "ultima_actividad": str(dm["ultima_actividad"]),
                    "no_leidos": dm["no_leidos"],
                })

            return {"canales": canales, "dms": dm_list}

    async def get_mensajes(
        self,
        tenant_id: int,
        canal_id: str,
        user_id: str,
        user_role: str,
        limit: int = 50,
        before: Optional[str] = None,
    ) -> list:
        """Get messages from a channel/DM."""
        async with db.pool.acquire() as conn:
            # DM access check
            if canal_id.startswith("dm_"):
                if user_role not in SUPERVISION_ROLES:
                    parts = canal_id.replace("dm_", "").split("_")
                    if user_id not in parts:
                        return None  # Forbidden

            params = [tenant_id, canal_id, limit]
            query = """SELECT id, canal_id, autor_id, autor_nombre, autor_rol,
                              contenido, tipo, metadata, created_at
                       FROM chat_mensajes
                       WHERE tenant_id = $1 AND canal_id = $2"""

            if before:
                query += " AND created_at < $4"
                params.append(before)

            query += " ORDER BY created_at DESC LIMIT $3"

            rows = await conn.fetch(query, *params)
            return [dict(r) for r in reversed(rows)]

    async def enviar_mensaje(
        self,
        tenant_id: int,
        canal_id: str,
        autor_id: str,
        autor_nombre: str,
        autor_rol: str,
        contenido: str,
        tipo: str = "mensaje",
        metadata: Optional[dict] = None,
    ) -> dict:
        """Send a message and emit Socket.IO event."""
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO chat_mensajes
                       (tenant_id, canal_id, autor_id, autor_nombre, autor_rol, contenido, tipo, metadata)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb)
                   RETURNING id, canal_id, autor_id, autor_nombre, autor_rol, contenido, tipo, metadata, created_at""",
                tenant_id, canal_id, autor_id, autor_nombre, autor_rol,
                contenido, tipo,
                __import__("json").dumps(metadata) if metadata else None,
            )

            msg = dict(row)
            msg_serialized = _serialize_msg(msg)

            # Emit to channel room
            room = f"chat:{tenant_id}:{canal_id}"
            await sio.emit("chat:nuevo_mensaje", msg_serialized, room=room)

            # DM badge update
            if canal_id.startswith("dm_"):
                parts = canal_id.replace("dm_", "").split("_")
                destinatario = [p for p in parts if p != autor_id]
                if destinatario:
                    dest_id = destinatario[0]
                    # Increment unread
                    await conn.execute(
                        """INSERT INTO chat_dm_no_leidos (tenant_id, user_id, canal_id, count, updated_at)
                           VALUES ($1, $2, $3, 1, NOW())
                           ON CONFLICT (tenant_id, user_id, canal_id)
                           DO UPDATE SET count = chat_dm_no_leidos.count + 1, updated_at = NOW()""",
                        tenant_id, dest_id, canal_id,
                    )
                    # Get new count
                    new_count = await conn.fetchval(
                        "SELECT count FROM chat_dm_no_leidos WHERE tenant_id=$1 AND user_id=$2 AND canal_id=$3",
                        tenant_id, dest_id, canal_id,
                    )
                    await sio.emit(
                        "chat:dm_badge_update",
                        {"canal_id": canal_id, "no_leidos": new_count or 0},
                        room=f"notifications:{dest_id}",
                    )

            return msg_serialized

    async def iniciar_dm(self, tenant_id: int, user_id: str, destinatario_id: str) -> str:
        """Create or retrieve a DM conversation."""
        canal_id = dm_canal_id(user_id, destinatario_id)

        async with db.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO chat_conversaciones (canal_id, tenant_id, tipo, participantes)
                   VALUES ($1, $2, 'dm', $3)
                   ON CONFLICT (canal_id, tenant_id) DO NOTHING""",
                canal_id, tenant_id,
                [user_id, destinatario_id],
            )

        return canal_id

    async def marcar_dm_leido(self, tenant_id: int, canal_id: str, user_id: str) -> None:
        """Mark a DM as read — reset unread counter."""
        async with db.pool.acquire() as conn:
            await conn.execute(
                """UPDATE chat_dm_no_leidos SET count = 0, updated_at = NOW()
                   WHERE tenant_id = $1 AND user_id = $2 AND canal_id = $3""",
                tenant_id, user_id, canal_id,
            )

        await sio.emit(
            "chat:badge_clear",
            {"canal_id": canal_id},
            room=f"notifications:{user_id}",
        )

    async def get_all_dms(self, tenant_id: int) -> list:
        """CEO supervision: get all DM conversations for the tenant."""
        async with db.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT canal_id, participantes, ultima_actividad
                   FROM chat_conversaciones
                   WHERE tenant_id = $1 AND tipo = 'dm'
                   ORDER BY ultima_actividad DESC""",
                tenant_id,
            )
            return [dict(r) for r in rows]

    async def get_perfiles(self, tenant_id: int) -> list:
        """List all users in the tenant (for new DM dialog)."""
        async with db.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT id, email, role FROM users
                   WHERE tenant_id = $1 AND status = 'active'
                   ORDER BY email""",
                tenant_id,
            )
            return [
                {"id": str(r["id"]), "nombre": r["email"].split("@")[0], "email": r["email"], "rol": r["role"]}
                for r in rows
            ]


def _serialize_msg(msg: dict) -> dict:
    return {
        "id": str(msg["id"]),
        "canal_id": msg["canal_id"],
        "autor_id": str(msg["autor_id"]),
        "autor_nombre": msg["autor_nombre"],
        "autor_rol": msg["autor_rol"],
        "contenido": msg["contenido"],
        "tipo": msg["tipo"],
        "metadata": msg.get("metadata"),
        "created_at": str(msg["created_at"]),
    }


# Integration helper
async def notificar_llamada_en_chat(
    tenant_id: int,
    autor_id: str,
    autor_nombre: str,
    cliente_nombre: str,
    descripcion: str,
    url: str,
) -> None:
    """Publish a call notification to #general."""
    await chat_service.enviar_mensaje(
        tenant_id=tenant_id,
        canal_id="general",
        autor_id=autor_id,
        autor_nombre=autor_nombre,
        autor_rol="vendedor",
        contenido=f"Se agendo una llamada con {cliente_nombre}",
        tipo="notificacion_llamada",
        metadata={
            "cliente_nombre": cliente_nombre,
            "descripcion": descripcion,
            "url": url,
        },
    )


chat_service = InternalChatService()
