# 🚀 PLAN DE IMPLEMENTACIÓN: SISTEMA AVANZADO DE ESTADOS PARA LEADS

**Fecha:** 26 de Febrero 2026  
**Contexto:** Plan paso a paso para implementación  
**Estado:** 📋 **PLAN DE EJECUCIÓN**

---

## 📅 **CRONOGRAMA DE IMPLEMENTACIÓN**

### **Duración Total Estimada:** 10-15 días hábiles
### **Enfoque:** Implementación incremental por fases

```
FASE 1: Base de Datos (2-3 días)
  ├── Diseño esquema final
  ├── Creación tablas
  ├── Migración datos existentes
  └── Backend básico

FASE 2: UI Básica (2-3 días)
  ├── Componentes React básicos
  ├── Integración en vistas existentes
  ├── Cambio individual de estados
  └── Validaciones frontend

FASE 3: Funcionalidades Avanzadas (3-4 días)
  ├── Bulk actions
  ├── Histórico visual
  ├── Pipeline visualization
  └── Filtros avanzados

FASE 4: Automatización (2-3 días)
  ├── Sistema de triggers
  ├── Configuración UI
  ├── Integración notificaciones
  └── Testing end-to-end

FASE 5: Polish y Docs (1-2 días)
  ├── UI/UX refinements
  ├── Performance optimizations
  ├── Documentación completa
  └── User training
```

---

## 🏗️ **FASE 1: BASE DE DATOS Y BACKEND (Días 1-3)**

### **Día 1: Diseño y Creación de Tablas**

#### **Tareas:**
1. **Revisar esquema final** - Validar con equipo
2. **Crear script de migración** `migrations/patch_018_lead_status_system.sql`
3. **Implementar tablas:**
   - `lead_statuses`
   - `lead_status_transitions`
   - `lead_status_history`
   - `lead_status_triggers`
   - `lead_status_trigger_logs`
4. **Modificar tabla `leads`** - Agregar constraints y columnas
5. **Crear índices** para performance
6. **Script de rollback** por si falla

#### **Archivos a crear:**
```
orchestrator_service/migrations/patch_018_lead_status_system.sql
orchestrator_service/migrations/rollback_018_lead_status_system.sql
orchestrator_service/scripts/seed_default_statuses.py
```

#### **Script de migración ejemplo:**
```sql
-- patch_018_lead_status_system.sql
BEGIN;

-- 1. Crear tabla lead_statuses
CREATE TABLE lead_statuses (...);

-- 2. Crear tabla lead_status_transitions
CREATE TABLE lead_status_transitions (...);

-- 3. Crear tabla lead_status_history
CREATE TABLE lead_status_history (...);

-- 4. Crear tabla lead_status_triggers
CREATE TABLE lead_status_triggers (...);

-- 5. Crear tabla lead_status_trigger_logs
CREATE TABLE lead_status_trigger_logs (...);

-- 6. Modificar tabla leads
ALTER TABLE leads ADD COLUMN status_changed_at TIMESTAMP;
ALTER TABLE leads ADD COLUMN status_changed_by UUID REFERENCES users(id);
ALTER TABLE leads ADD COLUMN status_metadata JSONB DEFAULT '{}';

-- 7. Agregar foreign key constraint
ALTER TABLE leads 
ADD CONSTRAINT fk_leads_status 
FOREIGN KEY (tenant_id, status) 
REFERENCES lead_statuses(tenant_id, code);

-- 8. Insertar estados por defecto
INSERT INTO lead_statuses (tenant_id, name, code, description, color, icon, is_initial, sort_order)
VALUES 
(1, 'Nuevo', 'new', 'Lead nuevo sin contacto', '#6B7280', 'circle', true, 10),
(1, 'Contactado', 'contacted', 'Se ha contactado al lead', '#3B82F6', 'phone', false, 20),
(1, 'Calificado', 'qualified', 'Lead calificado como prospecto', '#10B981', 'check-circle', false, 30),
(1, 'Propuesta Enviada', 'proposal_sent', 'Propuesta comercial enviada', '#8B5CF6', 'file-text', false, 40),
(1, 'Negociación', 'negotiation', 'En proceso de negociación', '#F59E0B', 'users', false, 50),
(1, 'Ganado', 'won', 'Lead convertido en cliente', '#10B981', 'trophy', true, 60),
(1, 'Perdido', 'lost', 'Lead no convertido', '#EF4444', 'x-circle', true, 70),
(1, 'Archivado', 'archived', 'Lead archivado', '#9CA3AF', 'archive', true, 80);

-- 9. Insertar transiciones por defecto
INSERT INTO lead_status_transitions (tenant_id, from_status_code, to_status_code, label, description)
VALUES
(1, 'new', 'contacted', 'Contactar', 'Marcar como contactado'),
(1, 'contacted', 'qualified', 'Calificar', 'Marcar como calificado'),
(1, 'qualified', 'proposal_sent', 'Enviar Propuesta', 'Enviar propuesta comercial'),
(1, 'proposal_sent', 'negotiation', 'Iniciar Negociación', 'Iniciar proceso de negociación'),
(1, 'negotiation', 'won', 'Ganar', 'Marcar como ganado'),
(1, 'negotiation', 'lost', 'Perder', 'Marcar como perdido'),
(1, NULL, 'archived', 'Archivar', 'Archivar lead');

COMMIT;
```

### **Día 2: Servicios Backend Básicos**

#### **Tareas:**
1. **Crear `services/lead_status_service.py`**
2. **Implementar métodos básicos:**
   - `get_statuses()`
   - `get_available_transitions()`
   - `validate_transition()`
   - `change_lead_status()`
3. **Crear `services/lead_history_service.py`**
4. **Implementar logging de cambios**
5. **Integrar con sistema de auditoría Nexus**
6. **Unit tests básicos**

#### **Archivos a crear:**
```
orchestrator_service/services/lead_status_service.py
orchestrator_service/services/lead_history_service.py
orchestrator_service/tests/test_lead_status_service.py
```

#### **Estructura del servicio:**
```python
# lead_status_service.py
from typing import List, Dict, Optional
from uuid import UUID
import asyncpg

class LeadStatusService:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
    
    async def get_statuses(self, tenant_id: int, include_inactive: bool = False) -> List[Dict]:
        """Obtiene estados para un tenant"""
        query = """
            SELECT id, name, code, description, color, icon, 
                   is_active, is_initial, is_final, sort_order,
                   requires_comment, category, badge_style
            FROM lead_statuses
            WHERE tenant_id = $1
            {active_filter}
            ORDER BY sort_order, name
        """.format(
            active_filter="" if include_inactive else "AND is_active = true"
        )
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, tenant_id)
            return [dict(row) for row in rows]
    
    async def get_available_transitions(self, tenant_id: int, current_status: Optional[str]) -> List[Dict]:
        """Obtiene transiciones disponibles desde un estado"""
        query = """
            SELECT t.id, t.from_status_code, t.to_status_code,
                   t.label, t.description, t.icon, t.button_style,
                   t.requires_approval, t.approval_role,
                   s_to.name as to_status_name,
                   s_to.color as to_status_color,
                   s_to.icon as to_status_icon
            FROM lead_status_transitions t
            JOIN lead_statuses s_to ON t.tenant_id = s_to.tenant_id 
                AND t.to_status_code = s_to.code
            WHERE t.tenant_id = $1 
                AND t.is_allowed = true
                AND (t.from_status_code = $2 OR t.from_status_code IS NULL)
                AND s_to.is_active = true
            ORDER BY t.from_status_code NULLS LAST, t.label
        """
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, tenant_id, current_status)
            return [dict(row) for row in rows]
    
    async def validate_transition(self, tenant_id: int, from_status: Optional[str], 
                                  to_status: str) -> Dict:
        """Valida si una transición es permitida"""
        # 1. Verificar que el estado destino existe y está activo
        # 2. Verificar que la transición está permitida
        # 3. Verificar reglas adicionales (límites diarios, etc.)
        # 4. Retornar resultado de validación
        pass
    
    async def change_lead_status(self, lead_id: UUID, new_status: str, 
                                 user_id: UUID, comment: Optional[str] = None,
                                 metadata: Optional[Dict] = None) -> Dict:
        """Cambia el estado de un lead con todas las validaciones"""
        # 1. Obtener lead actual
        # 2. Validar transición
        # 3. Actualizar tabla leads
        # 4. Registrar en histórico
        # 5. Ejecutar triggers (si aplica)
        # 6. Retornar resultado
        pass
```

### **Día 3: Endpoints API y Migración de Datos**

#### **Tareas:**
1. **Crear `routes/lead_status_routes.py`**
2. **Implementar endpoints:**
   - `GET /admin/core/crm/lead-statuses`
   - `GET /admin/core/crm/leads/{id}/available-transitions`
   - `POST /admin/core/crm/leads/{id}/status`
   - `GET /admin/core/crm/leads/{id}/status-history`
3. **Integrar en `main.py`**
4. **Crear script de migración de datos existentes**
5. **Testing endpoints con Postman/curl**
6. **Documentación OpenAPI/Swagger**

#### **Archivos a crear:**
```
orchestrator_service/routes/lead_status_routes.py
orchestrator_service/scripts/migrate_existing_statuses.py
docs/endpoints/lead_status_endpoints.md
```

#### **Ejemplo de endpoint:**
```python
# lead_status_routes.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from uuid import UUID

from ..services.lead_status_service import LeadStatusService
from ..dependencies import get_db_pool, verify_admin_token, get_resolved_tenant_id

router = APIRouter(prefix="/admin/core/crm", tags=["Lead Status"])

@router.get("/lead-statuses")
async def get_lead_statuses(
    tenant_id: int = Depends(get_resolved_tenant_id),
    include_inactive: bool = False,
    db_pool = Depends(get_db_pool),
    admin_token: str = Depends(verify_admin_token)
):
    """Obtiene todos los estados de leads para el tenant"""
    service = LeadStatusService(db_pool)
    statuses = await service.get_statuses(tenant_id, include_inactive)
    return {"statuses": statuses}

@router.get("/leads/{lead_id}/available-transitions")
async def get_available_transitions(
    lead_id: UUID,
    tenant_id: int = Depends(get_resolved_tenant_id),
    db_pool = Depends(get_db_pool),
    admin_token: str = Depends(verify_admin_token)
):
    """Obtiene transiciones disponibles para un lead específico"""
    # 1. Obtener estado actual del lead
    # 2. Usar servicio para obtener transiciones disponibles
    # 3. Retornar lista de transiciones
    pass

@router.post("/leads/{lead_id}/status")
async def change_lead_status(
    lead_id: UUID,
    request: Dict,
    tenant_id: int = Depends(get_resolved_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
    db_pool = Depends(get_db_pool),
    admin_token: str = Depends(verify_admin_token)
):
    """Cambia el estado de un lead"""
    new_status = request.get("status")
    comment = request.get("comment")
    metadata = request.get("metadata", {})
    
    if not new_status:
        raise HTTPException(status_code=400, detail="Status is required")
    
    service = LeadStatusService(db_pool)
    result = await service.change_lead_status(
        lead_id=lead_id,
        new_status=new_status,
        user_id=user_id,
        comment=comment,
        metadata=metadata
    )
    
    return result
```

#### **Script de migración de datos existentes:**
```python
# migrate_existing_statuses.py
import asyncio
import asyncpg
from typing import Dict, List

async def migrate_existing_statuses(dsn: str):
    """Migra estados existentes de la columna `status` a nuevo sistema"""
    
    # Mapeo de estados antiguos a nuevos códigos
    STATUS_MAPPING = {
        'new': 'new',
        'contacted': 'contacted', 
        'qualified': 'qualified',
        'converted': 'won',
        'lost': 'lost',
        'archived': 'archived'
    }
    
    async with asyncpg.create_pool(dsn) as pool:
        async with pool.acquire() as conn:
            # 1. Verificar que existen los estados por defecto
            # 2. Para cada lead, mapear estado antiguo a nuevo código
            # 3. Actualizar foreign key
            # 4. Registrar en histórico
            pass

if __name__ == "__main__":
    import os
    dsn = os.getenv("POSTGRES_DSN")
    asyncio.run(migrate_existing_statuses(dsn))
```

---

## 🎨 **FASE 2: UI BÁSICA (Días 4-6)**

### **Día 4: Componentes React Básicos**

#### **Tareas:**
1. **Crear `components/leads/LeadStatusBadge.tsx`**
2. **Crear `components/leads/LeadStatusSelector.tsx`**
3. **Crear `hooks/useLeadStatus.ts`**
4. **Crear `api/leadStatus.ts`**
5. **Testing componentes con Storybook**
6. **Integración con sistema de traducciones**

#### **Archivos a crear:**
```
frontend_react/src/components/leads/LeadStatusBadge.tsx
frontend_react/src/components/leads/LeadStatusSelector.tsx
frontend_react/src/hooks/useLeadStatus.ts
frontend_react/src/api/leadStatus.ts
frontend_react/src/stories/LeadStatusBadge.stories.tsx
frontend_react/src/stories/LeadStatusSelector.stories.tsx
```

#### **LeadStatusBadge.tsx:**
```typescript
import React from 'react';
import { cn } from '../../lib/utils';
import { useTranslation } from '../../context/LanguageContext';

interface LeadStatusBadgeProps {
  statusCode: string;
  statusName?: string;
  color?: string;
  icon?: string;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  className?: string;
  onClick?: () => void;
}

const LeadStatusBadge: React.FC<LeadStatusBadgeProps> = ({
  statusCode,
  statusName,
  color = '#6B7280',
  icon,
  size = 'md',
  showLabel = true,
  className,
  onClick
}) => {
  const { t } = useTranslation();
  
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-3 py-1 text-sm',
    lg: 'px-4 py-1.5 text-base'
  };
  
  const displayName = statusName || t(`lead_status.${statusCode}`, statusCode);
  
  return (
    <div
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full font-medium',
        'border border-opacity-20 transition-all',
        sizeClasses[size],
        onClick && 'cursor-pointer hover:opacity-90',
        className
      )}
      style={{
        backgroundColor: `${color}15`,
        borderColor: color,
        color: color
      }}
      onClick={onClick}
    >
      {icon && (
        <span className="text-xs">
          {/* Icono dinámico basado en nombre */}
        </span>
      )}
      {showLabel && (
        <span className="font-semibold">{displayName}</span>
      )}
    </div>
  );
};

export default LeadStatusBadge;
```

#### **LeadStatusSelector.tsx:**
```typescript
import React, { useState, useEffect } from 'react';
import { ChevronDown, Check } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useTranslation } from '../../context/LanguageContext';
import api from '../../api/axios';
import LeadStatusBadge from './LeadStatusBadge';

interface Transition {
  id: string;
  to_status_code: string;
  to_status_name: string;
  to_status_color: string;
  to_status_icon: string;
  label: string;
  description: string;
  icon: string;
  button_style: string;
  requires_approval: boolean;
}

interface LeadStatus