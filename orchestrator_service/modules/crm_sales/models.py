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
    
    # Apify / Prospecting fields
    apify_title: Optional[str] = None
    apify_category_name: Optional[str] = None
    apify_address: Optional[str] = None
    apify_city: Optional[str] = None
    apify_state: Optional[str] = None
    apify_country_code: Optional[str] = None
    apify_website: Optional[str] = None
    apify_place_id: Optional[str] = None
    apify_total_score: Optional[float] = None
    apify_reviews_count: Optional[int] = None
    apify_scraped_at: Optional[datetime] = None
    prospecting_niche: Optional[str] = None
    prospecting_location_query: Optional[str] = None
    outreach_message_sent: bool = False
    outreach_send_requested: bool = False
    outreach_message_content: Optional[str] = None
    outreach_last_requested_at: Optional[datetime] = None
    outreach_last_sent_at: Optional[datetime] = None
    apify_rating: Optional[float] = None
    apify_reviews: Optional[int] = None
    social_links: Optional[dict] = {}

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
# PROSPECTING (APIFY SCRAP PHONES)
# ============================================

class ProspectingScrapeRequest(BaseModel):
    """Request to scrape prospects from Apify."""
    tenant_id: int
    niche: str = Field(..., min_length=2)
    location: str = Field(..., min_length=2)
    max_places: int = Field(default=30, ge=1, le=100)


class ProspectingLeadResponse(BaseModel):
    """Response model for prospecting leads list."""
    id: UUID
    tenant_id: int
    phone_number: str
    first_name: Optional[str] = None
    status: Optional[str] = None
    source: Optional[str] = None
    apify_title: Optional[str] = None
    apify_category_name: Optional[str] = None
    apify_address: Optional[str] = None
    apify_city: Optional[str] = None
    apify_state: Optional[str] = None
    apify_country_code: Optional[str] = None
    apify_website: Optional[str] = None
    apify_place_id: Optional[str] = None
    apify_total_score: Optional[float] = None
    apify_reviews_count: Optional[int] = None
    apify_scraped_at: Optional[datetime] = None
    prospecting_niche: Optional[str] = None
    prospecting_location_query: Optional[str] = None
    outreach_message_sent: bool = False
    outreach_send_requested: bool = False
    outreach_message_content: Optional[str] = None
    outreach_last_requested_at: Optional[datetime] = None
    outreach_last_sent_at: Optional[datetime] = None
    apify_rating: Optional[float] = None
    apify_reviews: Optional[int] = None
    tags: List[str] = []
    social_links: Optional[dict] = {}
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProspectingSendRequest(BaseModel):
    """Request to queue/send template outreach (Phase 3)."""
    tenant_id: int
    lead_ids: Optional[List[UUID]] = None
    only_pending: bool = True
    template_name: Optional[str] = None
    language: str = "es_AR"


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
    lead_id: Optional[UUID] = Field(None, description="If provided, this lead is marked as closed_won after creating the client")


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


# ============================================
# SELLER AGENDA EVENTS (agenda por vendedor)
# ============================================

class AgendaEventCreate(BaseModel):
    """Request body for creating an agenda event"""
    seller_id: int = Field(..., description="Professional (seller) ID")
    title: str = Field(..., min_length=1)
    start_datetime: datetime
    end_datetime: datetime
    lead_id: Optional[UUID] = None
    client_id: Optional[int] = None
    notes: Optional[str] = None
    source: str = Field(default="manual", description="manual | ai")


class AgendaEventUpdate(BaseModel):
    """Request body for updating an agenda event"""
    title: Optional[str] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    lead_id: Optional[UUID] = None
    client_id: Optional[int] = None
    notes: Optional[str] = None
    status: Optional[str] = None  # scheduled | completed | cancelled


# ============================================
# CRM DASHBOARD STATS
# ============================================

class CrmDashboardStats(BaseModel):
    """Response model for CRM dashboard statistics"""
    total_leads: int
    total_clients: int
    active_leads: int
    converted_leads: int
    total_revenue: float
    conversion_rate: float
    status_distribution: List[dict] = Field(default_factory=list)
    revenue_leads_trend: List[dict] = Field(default_factory=list)
    recent_leads: List[dict] = Field(default_factory=list)
    
    class Config:
        from_attributes = True
