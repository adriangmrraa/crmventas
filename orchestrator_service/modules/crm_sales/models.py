"""
CRM Sales Module - Pydantic Models
Data validation models for CRM endpoints
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
from uuid import UUID

# ============================================
# LEADS
# ============================================

class LeadBase(BaseModel):
    phone_number: str = Field(..., description="Lead's phone number")
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    status: str = Field(default="new", description="Lead status: new, contacted, interested, negotiation, closed_won, closed_lost")
    source: Optional[str] = Field(None, description="Lead source: meta_ads, website, referral")
    meta_lead_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class LeadCreate(LeadBase):
    """Request body for creating a lead"""
    pass


class LeadUpdate(BaseModel):
    """Request body for updating a lead"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    status: Optional[str] = None
    source: Optional[str] = None
    tags: Optional[List[str]] = None
    assigned_seller_id: Optional[UUID] = None


class LeadResponse(LeadBase):
    """Response model for lead data"""
    id: UUID
    tenant_id: int
    assigned_seller_id: Optional[UUID] = None
    stage_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LeadAssignRequest(BaseModel):
    """Request to assign a lead to a seller"""
    seller_id: UUID = Field(..., description="User ID of the seller to assign")


class LeadStageUpdateRequest(BaseModel):
    """Request to update lead stage"""
    status: str = Field(..., description="New status for the lead")


# ============================================
# CLIENTS (página Clientes CRM - tabla propia, análoga a patients)
# ============================================

class ClientCreate(BaseModel):
    """Request body for creating a client"""
    phone_number: str = Field(..., description="Client phone number")
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    status: str = Field(default="active", description="active, inactive, etc.")
    notes: Optional[str] = None


class ClientUpdate(BaseModel):
    """Request body for updating a client"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class ClientResponse(BaseModel):
    """Response model for client data"""
    id: int
    tenant_id: int
    phone_number: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    status: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================
# WHATSAPP CONNECTIONS
# ============================================

class WhatsAppConnectionBase(BaseModel):
    phonenumber_id: str = Field(..., description="Meta WhatsApp Phone Number ID")
    waba_id: str = Field(..., description="WhatsApp Business Account ID")
    access_token_vault_id: str = Field(..., description="Vault ID for encrypted access token")
    friendly_name: Optional[str] = Field(None, description="Friendly name for this connection")
    seller_id: Optional[UUID] = Field(None, description="Optional seller-specific connection")


class WhatsAppConnectionCreate(WhatsAppConnectionBase):
    """Request body for creating a WhatsApp connection"""
    pass


class WhatsAppConnectionResponse(WhatsAppConnectionBase):
    """Response model for WhatsApp connection"""
    id: UUID
    tenant_id: int
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================
# TEMPLATES
# ============================================

class TemplateBase(BaseModel):
    meta_template_id: str = Field(..., description="Meta template ID")
    name: str = Field(..., description="Template name")
    language: str = Field(default="es", description="Template language code")
    category: Optional[str] = Field(None, description="MARKETING, UTILITY, AUTHENTICATION")
    components: dict = Field(..., description="Template structure (header, body, footer, buttons)")
    status: Optional[str] = Field(None, description="APPROVED, REJECTED, PAUSED, PENDING")


class TemplateResponse(TemplateBase):
    """Response model for template data"""
    id: UUID
    tenant_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TemplateSyncRequest(BaseModel):
    """Request to sync templates from Meta API"""
    force: bool = Field(default=False, description="Force sync even if recently synced")


# ============================================
# CAMPAIGNS
# ============================================

class CampaignBase(BaseModel):
    name: str = Field(..., description="Campaign name")
    template_id: UUID = Field(..., description="Template to use for this campaign")
    target_segment: Optional[dict] = Field(None, description="Lead filters (e.g., tags=['interested'])")
    scheduled_at: Optional[datetime] = Field(None, description="When to start the campaign")


class CampaignCreate(CampaignBase):
    """Request body for creating a campaign"""
    pass


class CampaignUpdate(BaseModel):
    """Request body for updating a campaign"""
    name: Optional[str] = None
    target_segment: Optional[dict] = None
    scheduled_at: Optional[datetime] = None
    status: Optional[str] = None


class CampaignResponse(CampaignBase):
    """Response model for campaign data"""
    id: UUID
    tenant_id: int
    status: str
    stats: dict
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CampaignLaunchRequest(BaseModel):
    """Request to launch a campaign"""
    immediate: bool = Field(default=False, description="Launch immediately or use scheduled_at")


# ============================================
# SELLERS (vendedores: setter/closer en professionals)
# ============================================

class SellerCreate(BaseModel):
    """Request body for creating a seller (admin)"""
    first_name: str
    last_name: Optional[str] = ""
    email: str
    phone_number: Optional[str] = None
    role: str = Field(..., description="setter | closer")
    tenant_id: Optional[int] = None


class SellerUpdate(BaseModel):
    """Request body for updating a seller"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    is_active: Optional[bool] = None
