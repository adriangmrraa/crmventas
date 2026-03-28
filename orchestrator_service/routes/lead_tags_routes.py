"""
Lead Tags Management - FastAPI Routes
Endpoints for managing predefined lead tags/labels with color, icon, and category.
"""
import json
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from core.security import verify_admin_token, get_resolved_tenant_id
from db import db

logger = logging.getLogger("orchestrator")

router = APIRouter(prefix="/admin/core/crm", tags=["Lead Tags"])


# ============================================
# PYDANTIC MODELS
# ============================================

class LeadTagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Tag name")
    color: str = Field(default="#6B7280", description="Hex color code")
    icon: Optional[str] = Field(None, max_length=50, description="Icon name (e.g. Lucide icon)")
    category: Optional[str] = Field(None, max_length=100, description="Tag category for grouping")


class LeadTagUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    color: Optional[str] = None
    icon: Optional[str] = None
    category: Optional[str] = None


class LeadTagResponse(BaseModel):
    id: UUID
    tenant_id: int
    name: str
    color: str
    icon: Optional[str] = None
    category: Optional[str] = None
    is_active: bool
    created_at: str  # ISO format

    class Config:
        from_attributes = True


class LeadTagAssign(BaseModel):
    tag_name: str = Field(..., description="Tag name to add to the lead")


# ============================================
# TAG MANAGEMENT ENDPOINTS
# ============================================

@router.get("/lead-tags", response_model=List[LeadTagResponse])
async def list_lead_tags(
    tenant_id: int = Depends(get_resolved_tenant_id),
    include_inactive: bool = False,
    admin_token: str = Depends(verify_admin_token),
):
    """List all predefined tags for the tenant."""
    query = "SELECT * FROM lead_tags WHERE tenant_id = $1"
    if not include_inactive:
        query += " AND is_active = TRUE"
    query += " ORDER BY category NULLS LAST, name"

    rows = await db.pool.fetch(query, tenant_id)
    return [
        {
            **dict(row),
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
        for row in rows
    ]


@router.post("/lead-tags", response_model=LeadTagResponse, status_code=201)
async def create_lead_tag(
    tag: LeadTagCreate,
    tenant_id: int = Depends(get_resolved_tenant_id),
    admin_token: str = Depends(verify_admin_token),
):
    """Create a new predefined tag for leads."""
    # Check duplicate
    existing = await db.pool.fetchrow(
        "SELECT id FROM lead_tags WHERE tenant_id = $1 AND LOWER(name) = LOWER($2)",
        tenant_id,
        tag.name,
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"Tag '{tag.name}' already exists for this tenant")

    row = await db.pool.fetchrow(
        """
        INSERT INTO lead_tags (tenant_id, name, color, icon, category)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING *
        """,
        tenant_id,
        tag.name.strip(),
        tag.color,
        tag.icon,
        tag.category,
    )
    return {
        **dict(row),
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


@router.put("/lead-tags/{tag_id}", response_model=LeadTagResponse)
async def update_lead_tag(
    tag_id: UUID,
    tag: LeadTagUpdate,
    tenant_id: int = Depends(get_resolved_tenant_id),
    admin_token: str = Depends(verify_admin_token),
):
    """Update an existing tag (name, color, icon, category)."""
    existing = await db.pool.fetchrow(
        "SELECT * FROM lead_tags WHERE id = $1 AND tenant_id = $2",
        tag_id,
        tenant_id,
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Tag not found")

    # Build dynamic SET clause
    updates = {}
    if tag.name is not None:
        # Check name uniqueness if changing
        dup = await db.pool.fetchrow(
            "SELECT id FROM lead_tags WHERE tenant_id = $1 AND LOWER(name) = LOWER($2) AND id != $3",
            tenant_id,
            tag.name,
            tag_id,
        )
        if dup:
            raise HTTPException(status_code=409, detail=f"Tag '{tag.name}' already exists")
        updates["name"] = tag.name.strip()
    if tag.color is not None:
        updates["color"] = tag.color
    if tag.icon is not None:
        updates["icon"] = tag.icon
    if tag.category is not None:
        updates["category"] = tag.category

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_parts = []
    params = []
    for i, (col, val) in enumerate(updates.items(), start=1):
        set_parts.append(f"{col} = ${i}")
        params.append(val)

    param_idx = len(params) + 1
    query = f"UPDATE lead_tags SET {', '.join(set_parts)} WHERE id = ${param_idx} AND tenant_id = ${param_idx + 1} RETURNING *"
    params.extend([tag_id, tenant_id])

    row = await db.pool.fetchrow(query, *params)
    return {
        **dict(row),
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


@router.delete("/lead-tags/{tag_id}", status_code=200)
async def delete_lead_tag(
    tag_id: UUID,
    tenant_id: int = Depends(get_resolved_tenant_id),
    admin_token: str = Depends(verify_admin_token),
):
    """Soft-delete a tag by setting is_active=false."""
    result = await db.pool.fetchrow(
        "UPDATE lead_tags SET is_active = FALSE WHERE id = $1 AND tenant_id = $2 RETURNING id, name",
        tag_id,
        tenant_id,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Tag not found")
    return {"detail": f"Tag '{result['name']}' deactivated", "id": str(result["id"])}


# ============================================
# LEAD <-> TAG ASSIGNMENT ENDPOINTS
# ============================================

@router.post("/leads/{lead_id}/tags", status_code=200)
async def add_tag_to_lead(
    lead_id: UUID,
    body: LeadTagAssign,
    tenant_id: int = Depends(get_resolved_tenant_id),
    admin_token: str = Depends(verify_admin_token),
):
    """Add a tag to a lead's tags JSONB array. Creates the tag in lead_tags if it doesn't exist."""
    async with db.pool.acquire() as conn:
        # Verify lead exists
        lead = await conn.fetchrow(
            "SELECT id, tags FROM leads WHERE id = $1 AND tenant_id = $2",
            lead_id,
            tenant_id,
        )
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")

        tag_name = body.tag_name.strip()

        # Auto-create tag in lead_tags if it doesn't exist
        await conn.execute(
            """
            INSERT INTO lead_tags (tenant_id, name)
            VALUES ($1, $2)
            ON CONFLICT (tenant_id, name) DO NOTHING
            """,
            tenant_id,
            tag_name,
        )

        # Get current tags
        current_tags = lead["tags"] or []
        if isinstance(current_tags, str):
            current_tags = json.loads(current_tags)

        if tag_name in current_tags:
            return {"detail": f"Tag '{tag_name}' already on this lead", "tags": current_tags}

        current_tags.append(tag_name)

        await conn.execute(
            "UPDATE leads SET tags = $1::jsonb, updated_at = NOW() WHERE id = $2 AND tenant_id = $3",
            json.dumps(current_tags),
            lead_id,
            tenant_id,
        )

    return {"detail": f"Tag '{tag_name}' added", "tags": current_tags}


@router.delete("/leads/{lead_id}/tags/{tag_name}", status_code=200)
async def remove_tag_from_lead(
    lead_id: UUID,
    tag_name: str,
    tenant_id: int = Depends(get_resolved_tenant_id),
    admin_token: str = Depends(verify_admin_token),
):
    """Remove a tag from a lead's tags JSONB array."""
    async with db.pool.acquire() as conn:
        lead = await conn.fetchrow(
            "SELECT id, tags FROM leads WHERE id = $1 AND tenant_id = $2",
            lead_id,
            tenant_id,
        )
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")

        current_tags = lead["tags"] or []
        if isinstance(current_tags, str):
            current_tags = json.loads(current_tags)

        if tag_name not in current_tags:
            raise HTTPException(status_code=404, detail=f"Tag '{tag_name}' not found on this lead")

        current_tags.remove(tag_name)

        await conn.execute(
            "UPDATE leads SET tags = $1::jsonb, updated_at = NOW() WHERE id = $2 AND tenant_id = $3",
            json.dumps(current_tags),
            lead_id,
            tenant_id,
        )

    return {"detail": f"Tag '{tag_name}' removed", "tags": current_tags}
