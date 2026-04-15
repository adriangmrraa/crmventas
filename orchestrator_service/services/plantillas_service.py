"""
Plantillas de Mensajes Service — SPEC-02
Reusable message templates with dynamic {{variable}} extraction.
"""

import re
import uuid
import logging
from typing import Optional

from db import db

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

VALID_CATEGORIES = ["whatsapp", "email", "seguimiento", "prospeccion", "cierre"]

PREDEFINED_VARIABLES = ["nombre", "empresa", "telefono", "email", "producto", "precio", "fecha"]

SAMPLE_DATA = {
    "nombre": "Juan Perez",
    "empresa": "Soluciones CRM",
    "telefono": "+54 11 1234 5678",
    "email": "juan@empresa.com",
    "producto": "Plan Pro",
    "precio": "$150.000 ARS",
    "fecha": "14 de abril",
}

VARIABLE_PATTERN = re.compile(r"\{\{(\w+)\}\}")


# ─── Utilities ────────────────────────────────────────────────────────────────

def extract_variables(contenido: str) -> list[str]:
    """Extract unique {{variable}} names from template content."""
    matches = VARIABLE_PATTERN.findall(contenido)
    seen = set()
    result = []
    for m in matches:
        if m not in seen:
            seen.add(m)
            result.append(m)
    return result


def render_preview(contenido: str, data: Optional[dict] = None) -> str:
    """Replace {{variables}} with sample data for preview."""
    sample = data or SAMPLE_DATA
    result = contenido
    for key, value in sample.items():
        result = result.replace(f"{{{{{key}}}}}", str(value))
    return result


# ─── Service ──────────────────────────────────────────────────────────────────

class PlantillasService:
    """CRUD service for message templates."""

    async def list(
        self,
        tenant_id: int,
        categoria: Optional[str] = None,
        q: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> dict:
        """List templates with optional filters."""
        async with db.pool.acquire() as conn:
            where = ["tenant_id = $1"]
            params: list = [tenant_id]
            idx = 2

            if categoria and categoria in VALID_CATEGORIES:
                where.append(f"categoria = ${idx}")
                params.append(categoria)
                idx += 1

            if q:
                where.append(f"(nombre ILIKE ${idx} OR contenido ILIKE ${idx})")
                params.append(f"%{q}%")
                idx += 1

            where_clause = " AND ".join(where)

            # Count
            total = await conn.fetchval(
                f"SELECT COUNT(*) FROM plantillas WHERE {where_clause}",
                *params,
            )

            # Fetch
            params.extend([limit, skip])
            rows = await conn.fetch(
                f"""SELECT id, nombre, categoria, contenido, variables, uso_count,
                           created_by, created_at, updated_at
                    FROM plantillas
                    WHERE {where_clause}
                    ORDER BY uso_count DESC, created_at DESC
                    LIMIT ${idx} OFFSET ${idx + 1}""",
                *params,
            )

            return {"items": [dict(r) for r in rows], "total": total}

    async def get(self, tenant_id: int, plantilla_id) -> Optional[dict]:
        """Get a single template by ID."""
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT id, nombre, categoria, contenido, variables, uso_count,
                          created_by, created_at, updated_at
                   FROM plantillas WHERE id = $1 AND tenant_id = $2""",
                uuid.UUID(str(plantilla_id)),
                tenant_id,
            )
            return dict(row) if row else None

    async def create(
        self,
        tenant_id: int,
        nombre: str,
        categoria: str,
        contenido: str,
        created_by: Optional[int] = None,
    ) -> dict:
        """Create a new template. Variables are auto-extracted from content."""
        variables = extract_variables(contenido)

        async with db.pool.acquire() as conn:
            try:
                row = await conn.fetchrow(
                    """INSERT INTO plantillas (tenant_id, nombre, categoria, contenido, variables, created_by)
                       VALUES ($1, $2, $3, $4, $5, $6)
                       RETURNING id, nombre, categoria, contenido, variables, uso_count, created_by, created_at, updated_at""",
                    tenant_id,
                    nombre,
                    categoria,
                    contenido,
                    variables,
                    created_by,
                )
                return dict(row)
            except Exception as e:
                if "idx_plantillas_tenant_nombre" in str(e):
                    raise DuplicateTemplateNameError(nombre)
                raise

    async def update(
        self,
        tenant_id: int,
        plantilla_id,
        nombre: str,
        categoria: str,
        contenido: str,
    ) -> Optional[dict]:
        """Update an existing template. Variables are re-extracted."""
        variables = extract_variables(contenido)

        async with db.pool.acquire() as conn:
            try:
                row = await conn.fetchrow(
                    """UPDATE plantillas
                       SET nombre = $3, categoria = $4, contenido = $5, variables = $6, updated_at = NOW()
                       WHERE id = $1 AND tenant_id = $2
                       RETURNING id, nombre, categoria, contenido, variables, uso_count, created_by, created_at, updated_at""",
                    uuid.UUID(str(plantilla_id)),
                    tenant_id,
                    nombre,
                    categoria,
                    contenido,
                    variables,
                )
                return dict(row) if row else None
            except Exception as e:
                if "idx_plantillas_tenant_nombre" in str(e):
                    raise DuplicateTemplateNameError(nombre)
                raise

    async def delete(self, tenant_id: int, plantilla_id) -> bool:
        """Delete a template."""
        async with db.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM plantillas WHERE id = $1 AND tenant_id = $2",
                uuid.UUID(str(plantilla_id)),
                tenant_id,
            )
            return "DELETE 1" in result

    async def increment_uso(self, tenant_id: int, plantilla_id) -> Optional[int]:
        """Atomically increment usage count. Returns new count."""
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                """UPDATE plantillas
                   SET uso_count = uso_count + 1, updated_at = NOW()
                   WHERE id = $1 AND tenant_id = $2
                   RETURNING uso_count""",
                uuid.UUID(str(plantilla_id)),
                tenant_id,
            )
            return row["uso_count"] if row else None


# ─── Exceptions ───────────────────────────────────────────────────────────────

class DuplicateTemplateNameError(Exception):
    def __init__(self, nombre: str):
        self.nombre = nombre
        super().__init__(f"Ya existe una plantilla con ese nombre: {nombre}")


# ─── Singleton ────────────────────────────────────────────────────────────────

plantillas_service = PlantillasService()
