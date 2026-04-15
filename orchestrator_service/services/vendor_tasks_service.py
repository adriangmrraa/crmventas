"""Vendor Tasks Service — SPEC-06: Admin-to-Vendor notes and tasks."""
import uuid, logging
from typing import Optional
from db import db
from core.socket_manager import sio

logger = logging.getLogger(__name__)

class VendorTasksService:

    async def create(self, tenant_id: int, vendor_id: int, created_by: int, contenido: str, es_tarea: bool = False, fecha_limite: Optional[str] = None) -> dict:
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO vendor_tasks (tenant_id, vendor_id, created_by, contenido, es_tarea, fecha_limite)
                   VALUES ($1, $2, $3, $4, $5, $6)
                   RETURNING id, tenant_id, vendor_id, created_by, contenido, es_tarea, fecha_limite, completada, completada_at, created_at""",
                tenant_id, vendor_id, created_by, contenido, es_tarea, fecha_limite,
            )
            result = _ser(row)
            if es_tarea:
                await sio.emit("VENDOR_TASK_ASSIGNED", {"task_id": result["id"], "contenido": contenido[:100]}, room=f"notifications:{vendor_id}")
            return result

    async def list_for_admin(self, tenant_id: int, vendor_id: Optional[int] = None, es_tarea: Optional[bool] = None, completada: Optional[bool] = None) -> list:
        async with db.pool.acquire() as conn:
            where, params, idx = ["tenant_id = $1"], [tenant_id], 2
            if vendor_id is not None:
                where.append(f"vendor_id = ${idx}"); params.append(vendor_id); idx += 1
            if es_tarea is not None:
                where.append(f"es_tarea = ${idx}"); params.append(es_tarea); idx += 1
            if completada is not None:
                where.append(f"completada = ${idx}"); params.append(completada); idx += 1
            rows = await conn.fetch(f"SELECT * FROM vendor_tasks WHERE {' AND '.join(where)} ORDER BY created_at DESC", *params)
            return [_ser(r) for r in rows]

    async def get_mine(self, tenant_id: int, user_id: int) -> dict:
        async with db.pool.acquire() as conn:
            all_rows = await conn.fetch(
                "SELECT * FROM vendor_tasks WHERE tenant_id=$1 AND vendor_id=$2 ORDER BY created_at DESC",
                tenant_id, user_id,
            )
            asignadas = [_ser(r) for r in all_rows if r["es_tarea"] and r["created_by"] != user_id]
            notas = [_ser(r) for r in all_rows if not r["es_tarea"] and r["created_by"] != user_id]
            personales = [_ser(r) for r in all_rows if r["created_by"] == user_id]
            return {"asignadas": asignadas, "notas": notas, "personales": personales}

    async def create_personal(self, tenant_id: int, user_id: int, contenido: str, fecha_limite: Optional[str] = None) -> dict:
        return await self.create(tenant_id, user_id, user_id, contenido, True, fecha_limite)

    async def toggle_completada(self, tenant_id: int, task_id: str, user_id: int, completada: bool) -> Optional[dict]:
        async with db.pool.acquire() as conn:
            task = await conn.fetchrow("SELECT id, vendor_id FROM vendor_tasks WHERE id=$1 AND tenant_id=$2", uuid.UUID(task_id), tenant_id)
            if not task:
                return None
            if task["vendor_id"] != user_id:
                raise PermissionError("No podes completar tareas de otro vendedor")
            if completada:
                row = await conn.fetchrow("UPDATE vendor_tasks SET completada=TRUE, completada_at=NOW() WHERE id=$1 RETURNING *", uuid.UUID(task_id))
            else:
                row = await conn.fetchrow("UPDATE vendor_tasks SET completada=FALSE, completada_at=NULL WHERE id=$1 RETURNING *", uuid.UUID(task_id))
            return _ser(row)

    async def delete(self, tenant_id: int, task_id: str) -> bool:
        async with db.pool.acquire() as conn:
            task = await conn.fetchrow("SELECT completada FROM vendor_tasks WHERE id=$1 AND tenant_id=$2", uuid.UUID(task_id), tenant_id)
            if not task:
                return False
            if task["completada"]:
                raise ValueError("No se puede eliminar una tarea completada")
            result = await conn.execute("DELETE FROM vendor_tasks WHERE id=$1 AND tenant_id=$2", uuid.UUID(task_id), tenant_id)
            return "DELETE 1" in result

    async def pending_count(self, tenant_id: int, user_id: int) -> int:
        async with db.pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT COUNT(*) FROM vendor_tasks WHERE tenant_id=$1 AND vendor_id=$2 AND es_tarea=TRUE AND completada=FALSE AND created_by != $2",
                tenant_id, user_id,
            ) or 0

def _ser(row) -> dict:
    if not row: return {}
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, uuid.UUID): d[k] = str(v)
        elif hasattr(v, 'isoformat'): d[k] = v.isoformat() if v else None
    return d

vendor_tasks_service = VendorTasksService()
