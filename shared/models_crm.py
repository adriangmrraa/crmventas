from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, EmailStr
from datetime import datetime


class LeadBase(BaseModel):
    """Datos básicos de un lead (prospecto) en Nexus Core CRM."""

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: str = Field(..., description="Número de WhatsApp u otro canal primario")
    email: Optional[EmailStr] = None
    status: str = Field(
        default="new",
        description="Estado del lead: new | contacted | qualified | unqualified | customer",
    )
    lead_score: Optional[str] = Field(
        default=None,
        description="Etiqueta de scoring (cold | warm | hot, u otra convención definida por el tenant)",
    )
    source: Optional[str] = Field(
        default=None,
        description="Fuente del lead (ej. 'whatsapp', 'landing', 'import', etc.)",
    )


class LeadCreate(LeadBase):
    """Payload para crear un lead desde la API admin CRM."""

    pass


class LeadResponse(LeadBase):
    """Respuesta estándar de lead desde la API admin CRM."""

    id: str
    tenant_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SalesAgentResponse(BaseModel):
    """
    Representación simplificada de un agente de ventas.
    No asume un esquema físico concreto; sirve como DTO agnóstico.
    """

    id: int
    tenant_id: int
    first_name: str
    last_name: str
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DealMeetingResponse(BaseModel):
    """
    Resumen de una reunión o interacción relevante en el pipeline de ventas.
    Este modelo se alinea conceptualmente con appointments, pero en clave CRM.
    """

    id: str
    tenant_id: int
    lead_id: str
    sales_agent_id: Optional[int] = None
    scheduled_at: datetime
    duration_minutes: int = 30
    stage: Optional[str] = Field(
        default=None,
        description="Etapa del deal/meeting (ej. 'discovery', 'demo', 'proposal', 'closed_won', 'closed_lost')",
    )
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    extra: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

