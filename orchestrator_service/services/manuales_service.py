"""Knowledge Base Service — SPEC-03: Manuales / documentacion."""
import uuid, logging
from typing import Optional
from db import db

logger = logging.getLogger(__name__)
VALID_CATEGORIAS = ["general", "guion_ventas", "objeciones", "producto", "proceso", "onboarding"]

class ManualesService:

    async def list(self, tenant_id: int, categoria: Optional[str] = None, q: Optional[str] = None, limit: int = 50, offset: int = 0) -> dict:
        async with db.pool.acquire() as conn:
            where, params, idx = ["tenant_id = $1"], [tenant_id], 2
            if categoria and categoria in VALID_CATEGORIAS:
                where.append(f"categoria = ${idx}"); params.append(categoria); idx += 1
            if q:
                where.append(f"to_tsvector('spanish', titulo || ' ' || contenido) @@ plainto_tsquery('spanish', ${idx})")
                params.append(q); idx += 1
            wc = " AND ".join(where)
            total = await conn.fetchval(f"SELECT COUNT(*) FROM manuales WHERE {wc}", *params)
            params.extend([limit, offset])
            rows = await conn.fetch(f"SELECT * FROM manuales WHERE {wc} ORDER BY updated_at DESC LIMIT ${idx} OFFSET ${idx+1}", *params)
            return {"items": [_ser(r) for r in rows], "total": total, "has_more": (offset + limit) < total}

    async def get(self, tenant_id: int, manual_id: str) -> Optional[dict]:
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM manuales WHERE id=$1 AND tenant_id=$2", uuid.UUID(manual_id), tenant_id)
            return _ser(row) if row else None

    async def create(self, tenant_id: int, titulo: str, contenido: str, categoria: str = "general", autor: Optional[str] = None) -> dict:
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO manuales (tenant_id, titulo, contenido, categoria, autor) VALUES ($1,$2,$3,$4,$5) RETURNING *",
                tenant_id, titulo, contenido, categoria, autor,
            )
            return _ser(row)

    async def update(self, tenant_id: int, manual_id: str, titulo: Optional[str] = None, contenido: Optional[str] = None, categoria: Optional[str] = None, autor: Optional[str] = None) -> Optional[dict]:
        async with db.pool.acquire() as conn:
            existing = await conn.fetchrow("SELECT * FROM manuales WHERE id=$1 AND tenant_id=$2", uuid.UUID(manual_id), tenant_id)
            if not existing: return None
            row = await conn.fetchrow(
                "UPDATE manuales SET titulo=COALESCE($3,titulo), contenido=COALESCE($4,contenido), categoria=COALESCE($5,categoria), autor=COALESCE($6,autor), updated_at=NOW() WHERE id=$1 AND tenant_id=$2 RETURNING *",
                uuid.UUID(manual_id), tenant_id, titulo, contenido, categoria, autor,
            )
            return _ser(row)

    async def delete(self, tenant_id: int, manual_id: str) -> bool:
        async with db.pool.acquire() as conn:
            result = await conn.execute("DELETE FROM manuales WHERE id=$1 AND tenant_id=$2", uuid.UUID(manual_id), tenant_id)
            return "DELETE 1" in result

def _ser(row) -> dict:
    if not row: return {}
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, uuid.UUID): d[k] = str(v)
        elif hasattr(v, 'isoformat'): d[k] = v.isoformat() if v else None
    return d

manuales_service = ManualesService()
