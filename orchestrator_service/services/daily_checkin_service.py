"""
Daily Check-in Service — SPEC-05
Daily work sessions with check-in/check-out, CEO panel, and weekly summaries.
"""

import uuid
import logging
from typing import Optional
from decimal import Decimal

from db import db
from core.socket_manager import sio

logger = logging.getLogger(__name__)


class CheckinAlreadyExistsError(Exception):
    pass

class CheckinAlreadyClosedError(Exception):
    pass


class DailyCheckinService:

    async def checkin(self, seller_id: str, tenant_id: int, llamadas_planeadas: int) -> dict:
        async with db.pool.acquire() as conn:
            existing = await conn.fetchrow(
                "SELECT id FROM daily_checkins WHERE tenant_id=$1 AND seller_id=$2 AND fecha=CURRENT_DATE",
                tenant_id, uuid.UUID(seller_id),
            )
            if existing:
                raise CheckinAlreadyExistsError("Ya existe check-in para hoy")

            row = await conn.fetchrow(
                """INSERT INTO daily_checkins (tenant_id, seller_id, llamadas_planeadas)
                   VALUES ($1, $2, $3)
                   RETURNING id, tenant_id, seller_id, fecha, llamadas_planeadas, estado, checkin_at""",
                tenant_id, uuid.UUID(seller_id), llamadas_planeadas,
            )
            result = _serialize(row)
            await sio.emit("checkin_created", result, room=f"checkin:{tenant_id}")
            return result

    async def checkout(
        self, checkin_id: str, seller_id: str, tenant_id: int,
        llamadas_logradas: int, contactos_logrados: int, notas: Optional[str] = None,
    ) -> dict:
        async with db.pool.acquire() as conn:
            record = await conn.fetchrow(
                "SELECT id, estado, llamadas_planeadas FROM daily_checkins WHERE id=$1 AND seller_id=$2 AND tenant_id=$3",
                uuid.UUID(checkin_id), uuid.UUID(seller_id), tenant_id,
            )
            if not record:
                return None
            if record["estado"] != "active":
                raise CheckinAlreadyClosedError("Jornada ya cerrada")

            planeadas = record["llamadas_planeadas"]
            pct = round((llamadas_logradas / planeadas) * 100, 2) if planeadas > 0 else 0

            row = await conn.fetchrow(
                """UPDATE daily_checkins
                   SET llamadas_logradas=$3, contactos_logrados=$4, notas=$5,
                       checkout_at=NOW(), estado='completed', cumplimiento_pct=$6, updated_at=NOW()
                   WHERE id=$1 AND tenant_id=$2
                   RETURNING id, tenant_id, seller_id, fecha, llamadas_planeadas, llamadas_logradas,
                             contactos_logrados, cumplimiento_pct, estado, checkin_at, checkout_at""",
                uuid.UUID(checkin_id), tenant_id,
                llamadas_logradas, contactos_logrados, notas, pct,
            )
            result = _serialize(row)
            await sio.emit("checkin_completed", result, room=f"checkin:{tenant_id}")
            return result

    async def get_today(self, seller_id: str, tenant_id: int) -> Optional[dict]:
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT id, tenant_id, seller_id, fecha, llamadas_planeadas, llamadas_logradas,
                          contactos_logrados, notas, cumplimiento_pct, estado, checkin_at, checkout_at
                   FROM daily_checkins WHERE tenant_id=$1 AND seller_id=$2 AND fecha=CURRENT_DATE""",
                tenant_id, uuid.UUID(seller_id),
            )
            return _serialize(row) if row else None

    async def get_ceo_today(self, tenant_id: int) -> dict:
        async with db.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT u.id as seller_id, u.email,
                          dc.llamadas_planeadas, dc.llamadas_logradas, dc.contactos_logrados,
                          dc.cumplimiento_pct, dc.estado, dc.checkin_at, dc.checkout_at
                   FROM users u
                   LEFT JOIN daily_checkins dc ON dc.seller_id = u.id AND dc.tenant_id = u.tenant_id AND dc.fecha = CURRENT_DATE
                   WHERE u.tenant_id = $1 AND u.status = 'active' AND u.role IN ('setter', 'closer', 'professional')
                   ORDER BY u.email""",
                tenant_id,
            )
            vendedores = []
            for r in rows:
                vendedores.append({
                    "seller_id": str(r["seller_id"]),
                    "nombre": r["email"].split("@")[0],
                    "estado": r["estado"] or "sin_checkin",
                    "llamadas_planeadas": r["llamadas_planeadas"],
                    "llamadas_logradas": r["llamadas_logradas"],
                    "contactos_logrados": r["contactos_logrados"],
                    "cumplimiento_pct": float(r["cumplimiento_pct"]) if r["cumplimiento_pct"] else None,
                    "checkin_at": str(r["checkin_at"]) if r["checkin_at"] else None,
                    "checkout_at": str(r["checkout_at"]) if r["checkout_at"] else None,
                })
            return {
                "total_sellers": len(vendedores),
                "con_checkin": sum(1 for v in vendedores if v["estado"] != "sin_checkin"),
                "completados": sum(1 for v in vendedores if v["estado"] == "completed"),
                "vendedores": vendedores,
            }

    async def get_weekly(self, tenant_id: int, weeks: int = 1) -> list:
        async with db.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT seller_id,
                          COUNT(*) as jornadas_total,
                          COUNT(*) FILTER (WHERE estado IN ('completed','auto_closed')) as jornadas_completadas,
                          COALESCE(SUM(llamadas_planeadas),0) as planeadas_total,
                          COALESCE(SUM(llamadas_logradas),0) as logradas_total,
                          COALESCE(SUM(contactos_logrados),0) as contactos_total
                   FROM daily_checkins
                   WHERE tenant_id=$1 AND fecha >= CURRENT_DATE - ($2 * 7)
                   GROUP BY seller_id""",
                tenant_id, weeks,
            )
            return [dict(r) for r in rows]

    async def get_history(self, seller_id: str, tenant_id: int, limit: int = 30) -> list:
        async with db.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT id, fecha, llamadas_planeadas, llamadas_logradas, contactos_logrados,
                          cumplimiento_pct, estado, checkin_at, checkout_at
                   FROM daily_checkins WHERE tenant_id=$1 AND seller_id=$2
                   ORDER BY fecha DESC LIMIT $3""",
                tenant_id, uuid.UUID(seller_id), limit,
            )
            return [_serialize(r) for r in rows]

    async def auto_close_open(self, tenant_id: int) -> int:
        async with db.pool.acquire() as conn:
            result = await conn.execute(
                """UPDATE daily_checkins SET estado='auto_closed', checkout_at=NOW(), updated_at=NOW()
                   WHERE estado='active' AND fecha=CURRENT_DATE AND tenant_id=$1""",
                tenant_id,
            )
            count = int(result.split()[-1]) if result else 0
            if count > 0:
                await sio.emit("checkin_auto_closed", {"count": count}, room=f"checkin:{tenant_id}")
            return count


def _serialize(row) -> dict:
    if not row:
        return {}
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, uuid.UUID):
            d[k] = str(v)
        elif isinstance(v, Decimal):
            d[k] = float(v)
        elif hasattr(v, 'isoformat'):
            d[k] = v.isoformat() if v else None
    return d


checkin_service = DailyCheckinService()
