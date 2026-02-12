from uuid import UUID
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

# --- LEADS ---
class LeadBase(BaseModel):
    phone_number: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    status: Optional[str] = "new"
    lead_score: Optional[str] = None
    source: Optional[str] = None
    tags: List[str] = []
    meta_lead_id: Optional[str] = None

class LeadCreate(LeadBase):
    tenant_id: int
    assigned_seller_id: Optional[UUID] = None

class LeadUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    status: Optional[str] = None
    lead_score: Optional[str] = None
    assigned_seller_id: Optional[UUID] = None
    tags: Optional[List[str]] = None

class Lead(LeadBase):
    id: UUID
    tenant_id: int
    assigned_seller_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- WHATSAPP CONNECTIONS ---
class WhatsAppConnectionBase(BaseModel):
    phonenumber_id: str
    waba_id: str
    friendly_name: Optional[str] = None
    status: str = "active"

class WhatsAppConnectionCreate(WhatsAppConnectionBase):
    tenant_id: int
    seller_id: Optional[UUID] = None
    access_token_vault_id: str

class WhatsAppConnection(WhatsAppConnectionBase):
    id: UUID
    tenant_id: int
    seller_id: Optional[UUID] = None
    # access_token_vault_id is kept internal/secure
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- TEMPLATES ---
class TemplateBase(BaseModel):
    meta_template_id: str
    name: str
    language: str = "es"
    category: Optional[str] = None
    components: List[Dict[str, Any]] = []
    status: Optional[str] = None

class TemplateCreate(TemplateBase):
    tenant_id: int

class Template(TemplateBase):
    id: UUID
    tenant_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- CAMPAIGNS ---
class CampaignBase(BaseModel):
    name: str
    target_segment: Dict[str, Any] = {}
    status: str = "draft"
    scheduled_at: Optional[datetime] = None

class CampaignCreate(CampaignBase):
    tenant_id: int
    template_id: Optional[UUID] = None

class Campaign(CampaignBase):
    id: UUID
    tenant_id: int
    template_id: Optional[UUID] = None
    stats: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
