"""Lead Forms Service — F-02: Public lead capture forms."""
import uuid, secrets, logging, json
from typing import Optional
from db import db

logger = logging.getLogger(__name__)

class LeadFormsService:

    async def list(self, tenant_id: int) -> list:
        async with db.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM lead_forms WHERE tenant_id=$1 ORDER BY created_at DESC", tenant_id
            )
            return [_ser(r) for r in rows]

    async def get(self, tenant_id: int, form_id: str) -> Optional[dict]:
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM lead_forms WHERE id=$1 AND tenant_id=$2", uuid.UUID(form_id), tenant_id
            )
            return _ser(row) if row else None

    async def get_by_slug(self, slug: str) -> Optional[dict]:
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM lead_forms WHERE slug=$1 AND active=TRUE", slug)
            return _ser(row) if row else None

    async def create(self, tenant_id: int, name: str, fields: list, thank_you_message: str = "", redirect_url: str = "", created_by: Optional[int] = None) -> dict:
        slug = secrets.token_urlsafe(6)[:8]
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO lead_forms (tenant_id, name, slug, fields, thank_you_message, redirect_url, created_by)
                   VALUES ($1,$2,$3,$4,$5,$6,$7) RETURNING *""",
                tenant_id, name, slug, json.dumps(fields), thank_you_message, redirect_url, created_by,
            )
            return _ser(row)

    async def update(self, tenant_id: int, form_id: str, name: str, fields: list, thank_you_message: str = "", redirect_url: str = "", active: bool = True) -> Optional[dict]:
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                """UPDATE lead_forms SET name=$3, fields=$4, thank_you_message=$5, redirect_url=$6, active=$7, updated_at=NOW()
                   WHERE id=$1 AND tenant_id=$2 RETURNING *""",
                uuid.UUID(form_id), tenant_id, name, json.dumps(fields), thank_you_message, redirect_url, active,
            )
            return _ser(row) if row else None

    async def delete(self, tenant_id: int, form_id: str) -> bool:
        async with db.pool.acquire() as conn:
            result = await conn.execute("DELETE FROM lead_forms WHERE id=$1 AND tenant_id=$2", uuid.UUID(form_id), tenant_id)
            return "DELETE 1" in result

    async def submit(self, slug: str, data: dict, ip: str) -> dict:
        async with db.pool.acquire() as conn:
            form = await conn.fetchrow("SELECT * FROM lead_forms WHERE slug=$1 AND active=TRUE", slug)
            if not form:
                return None

            # Create lead
            phone = data.get("phone", data.get("telefono", data.get("phone_number", "")))
            lead_row = await conn.fetchrow(
                """INSERT INTO leads (tenant_id, phone_number, first_name, last_name, email, source, status, tags)
                   VALUES ($1,$2,$3,$4,$5,'web_form','new',$6)
                   ON CONFLICT (tenant_id, phone_number) DO UPDATE SET updated_at=NOW()
                   RETURNING id""",
                form["tenant_id"],
                phone or f"form_{uuid.uuid4().hex[:8]}",
                data.get("nombre", data.get("first_name", "")),
                data.get("apellido", data.get("last_name", "")),
                data.get("email", ""),
                json.dumps(["formulario_web", slug]),
            )

            # Record submission
            await conn.execute(
                """INSERT INTO lead_form_submissions (form_id, lead_id, data, ip_address)
                   VALUES ($1,$2,$3,$4)""",
                form["id"], lead_row["id"] if lead_row else None, json.dumps(data), ip,
            )

            return {
                "ok": True,
                "thank_you_message": form["thank_you_message"],
                "redirect_url": form["redirect_url"],
            }

    async def get_stats(self, tenant_id: int, form_id: str) -> dict:
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT COUNT(*) as submissions,
                          MAX(s.submitted_at) as last_submission
                   FROM lead_form_submissions s
                   JOIN lead_forms f ON f.id = s.form_id
                   WHERE f.id=$1 AND f.tenant_id=$2""",
                uuid.UUID(form_id), tenant_id,
            )
            return {"submissions_count": row["submissions"] or 0, "last_submission_at": str(row["last_submission"]) if row["last_submission"] else None}

def _ser(row) -> dict:
    if not row: return {}
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, uuid.UUID): d[k] = str(v)
        elif hasattr(v, 'isoformat'): d[k] = v.isoformat() if v else None
        elif k == 'fields' and isinstance(v, str):
            try: d[k] = json.loads(v)
            except: pass
    return d

lead_forms_service = LeadFormsService()
