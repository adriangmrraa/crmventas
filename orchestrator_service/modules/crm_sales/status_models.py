from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

# ==========================================
# LEAD STATUS MODELS (NEW)
# ==========================================

class LeadStatusBase(BaseModel):
    name: str = Field(..., description="Nombre legible del estado")
    code: str = Field(..., description="Código único del estado")
    description: Optional[str] = None
    category: Optional[str] = Field(None, description="initial, active, final, archived")
    color: str = Field(default="#6B7280", description="Color en formato hexadecimal")
    icon: str = Field(default="circle", description="Ícono representativo de Lucide")
    badge_style: str = Field(default="default", description="Estilo de badge UI")
    is_active: bool = True
    is_initial: bool = False
    is_final: bool = False
    requires_comment: bool = False
    sort_order: int = 0
    metadata_config: Dict[str, Any] = Field(default_factory=dict, alias="metadata")

class LeadStatusResponse(LeadStatusBase):
    id: UUID
    tenant_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class LeadStatusTransitionResponse(BaseModel):
    id: UUID
    from_status_code: Optional[str]
    to_status_code: str
    label: Optional[str]
    description: Optional[str]
    icon: Optional[str]
    button_style: str
    requires_approval: bool
    approval_role: Optional[str]
    to_status_name: str
    to_status_color: str
    to_status_icon: str
    
    class Config:
        from_attributes = True

class LeadStatusChangeRequest(BaseModel):
    """Payload para mutar el estado de un lead sencillo"""
    status: str = Field(..., description="El código del nuevo estado a aplicar")
    comment: Optional[str] = Field(None, description="Comentario o razón de cambio (opcional o requerido según DB)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
class LeadBulkStatusChangeRequest(BaseModel):
    """Payload para mutar masivamente varios leads de forma concurrente"""
    lead_ids: List[UUID] = Field(..., description="Lista de UUIDs de leads a mutar")
    status: str = Field(..., description="El código del nuevo estado a aplicar")
    comment: Optional[str] = Field(None, description="Comentario general para todos los leads")

class LeadStatusHistoryResponse(BaseModel):
    """Respuesta de la auditoría temporal de historial de un lead"""
    id: UUID
    lead_id: UUID
    tenant_id: int
    from_status_code: Optional[str]
    to_status_code: str
    changed_by_user_id: Optional[UUID]
    changed_by_name: Optional[str]
    comment: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class LeadStatusUpdate(BaseModel):
    """Payload para actualizar el estado de un lead desde la interfaz nexus"""
    new_status_id: str = Field(..., description="El código del nuevo estado a aplicar")
    reason: Optional[str] = Field(None, description="Comentario o razón de cambio")
