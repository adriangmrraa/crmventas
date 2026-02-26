# 🏗️ ARQUITECTURA TÉCNICA: SISTEMA AVANZADO DE ESTADOS PARA LEADS

**Fecha:** 26 de Febrero 2026  
**Contexto:** Arquitectura detallada para mejora de estados de leads  
**Estado:** 📋 **PLANIFICACIÓN TÉCNICA**

---

## 📐 **ARQUITECTURA DE ALTO NIVEL**

### **Diagrama del Sistema:**
```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐    │
│  │LeadStatus   │  │LeadPipeline │  │LeadStatusConfig │    │
│  │Selector     │  │View         │  │View             │    │
│  └─────────────┘  └─────────────┘  └─────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    API GATEWAY (FastAPI)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐    │
│  │/lead-status │  │/leads/{id}/ │  │/lead-triggers   │    │
│  │             │  │status       │  │                 │    │
│  └─────────────┘  └─────────────┘  └─────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    BUSINESS LOGIC LAYER                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐    │
│  │LeadStatus   │  │LeadAuto-    │  │LeadHistory      │    │
│  │Service      │  │mationService│  │Service          │    │
│  └─────────────┘  └─────────────┘  └─────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    DATA ACCESS LAYER                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                PostgreSQL Database                   │    │
│  │  lead_statuses       lead_status_history            │    │
│  │  lead_status_transitions lead_status_triggers       │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🗄️ **ESQUEMA DE BASE DE DATOS DETALLADO**

### **1. Tabla `lead_statuses` (Estados Configurables):**
```sql
CREATE TABLE lead_statuses (
    -- Identificación
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    -- Información del estado
    name TEXT NOT NULL,                    -- Nombre legible: 'Nuevo', 'Contactado'
    code TEXT NOT NULL,                    -- Código único: 'new', 'contacted'
    description TEXT,                      -- Descripción para tooltips
    category TEXT,                         -- 'initial', 'active', 'final', 'archived'
    
    -- Apariencia UI
    color VARCHAR(7) DEFAULT '#6B7280',    -- Color hexadecimal
    icon VARCHAR(50) DEFAULT 'circle',     -- Nombre icono Lucide
    badge_style TEXT DEFAULT 'default',    -- 'default', 'outline', 'soft'
    
    -- Comportamiento
    is_active BOOLEAN DEFAULT TRUE,
    is_initial BOOLEAN DEFAULT FALSE,      -- Estado inicial para nuevos leads
    is_final BOOLEAN DEFAULT FALSE,        -- Estado final (no más transiciones)
    requires_comment BOOLEAN DEFAULT FALSE, -- Requiere comentario al cambiar a este estado
    
    -- Orden y metadata
    sort_order INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',           -- Configuración adicional
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    UNIQUE(tenant_id, code),
    CHECK (color ~ '^#[0-9A-Fa-f]{6}$'),
    CHECK (code ~ '^[a-z_]+$')            -- Solo minúsculas y underscores
);

-- Índices para performance
CREATE INDEX idx_lead_statuses_tenant ON lead_statuses(tenant_id);
CREATE INDEX idx_lead_statuses_active ON lead_statuses(tenant_id, is_active);
CREATE INDEX idx_lead_statuses_initial ON lead_statuses(tenant_id, is_initial);
CREATE INDEX idx_lead_statuses_final ON lead_statuses(tenant_id, is_final);
```

### **2. Tabla `lead_status_transitions` (Workflow):**
```sql
CREATE TABLE lead_status_transitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    -- Transición
    from_status_code TEXT NOT NULL,        -- Estado origen (NULL para cualquier)
    to_status_code TEXT NOT NULL,          -- Estado destino
    
    -- Reglas de transición
    is_allowed BOOLEAN DEFAULT TRUE,
    requires_approval BOOLEAN DEFAULT FALSE, -- Requiere aprobación manager
    approval_role TEXT,                     -- Rol que puede aprobar
    max_daily_transitions INTEGER,          -- Límite diario de esta transición
    
    -- UI/UX
    label TEXT,                            -- Etiqueta personalizada para UI
    description TEXT,                      -- Descripción de la transición
    icon VARCHAR(50),                      -- Icono para botón
    button_style TEXT DEFAULT 'default',   -- 'default', 'primary', 'danger'
    
    -- Validaciones
    validation_rules JSONB DEFAULT '{}',   -- Reglas de validación
    pre_conditions JSONB DEFAULT '{}',     -- Condiciones previas requeridas
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints y foreign keys
    FOREIGN KEY (tenant_id, from_status_code) 
        REFERENCES lead_statuses(tenant_id, code) ON DELETE CASCADE,
    FOREIGN KEY (tenant_id, to_status_code) 
        REFERENCES lead_statuses(tenant_id, code) ON DELETE CASCADE,
    
    -- Una transición única por tenant
    UNIQUE(tenant_id, from_status_code, to_status_code)
);

-- Índices para búsquedas rápidas
CREATE INDEX idx_transitions_from ON lead_status_transitions(tenant_id, from_status_code);
CREATE INDEX idx_transitions_to ON lead_status_transitions(tenant_id, to_status_code);
CREATE INDEX idx_transitions_allowed ON lead_status_transitions(tenant_id, is_allowed);
```

### **3. Tabla `lead_status_history` (Audit Trail):**
```sql
CREATE TABLE lead_status_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Referencias
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    -- Cambio de estado
    from_status_code TEXT,                 -- NULL para estado inicial
    to_status_code TEXT NOT NULL,
    
    -- Quién y por qué
    changed_by_user_id UUID REFERENCES users(id),
    changed_by_name TEXT,                  -- Cache para evitar joins frecuentes
    changed_by_role TEXT,                  -- Rol del usuario en el momento
    changed_by_ip INET,                    -- IP del usuario
    changed_by_user_agent TEXT,            -- User agent del navegador
    
    -- Contexto
    comment TEXT,                          -- Comentario del usuario
    reason_code TEXT,                      -- Código razón predefinida
    source TEXT DEFAULT 'manual',          -- 'manual', 'api', 'automation', 'import'
    
    -- Metadata
    metadata JSONB DEFAULT '{}',           -- Datos adicionales del cambio
    session_id UUID,                       -- ID de sesión para tracking
    request_id TEXT,                       -- ID de request para debugging
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Índices para consultas comunes
    INDEX idx_history_lead_tenant (lead_id, tenant_id, created_at DESC),
    INDEX idx_history_tenant_date (tenant_id, created_at DESC),
    INDEX idx_history_user (changed_by_user_id, created_at DESC),
    INDEX idx_history_status (to_status_code, created_at DESC),
    INDEX idx_history_source (source, created_at DESC)
);

-- Tabla de partición por mes para performance (opcional para grandes volúmenes)
-- CREATE TABLE lead_status_history_y2026m02 PARTITION OF lead_status_history
-- FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
```

### **4. Tabla `lead_status_triggers` (Automatización):**
```sql
CREATE TABLE lead_status_triggers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    -- Activación del trigger
    trigger_name TEXT NOT NULL,
    from_status_code TEXT,                 -- NULL para cualquier estado origen
    to_status_code TEXT NOT NULL,
    
    -- Configuración de la acción
    action_type TEXT NOT NULL,             -- 'email', 'whatsapp', 'task', 'webhook', 'api_call'
    action_config JSONB NOT NULL,          -- {
                                           --   "template": "welcome_email",
                                           --   "recipients": ["assignee", "lead"],
                                           --   "delay_minutes": 30
                                           -- }
    
    -- Ejecución
    execution_mode TEXT DEFAULT 'immediate', -- 'immediate', 'delayed', 'scheduled'
    delay_minutes INTEGER DEFAULT 0,
    scheduled_time TIME,                   -- Hora específica del día
    timezone TEXT DEFAULT 'UTC',
    
    -- Condiciones adicionales
    conditions JSONB DEFAULT '{}',         -- Condiciones para ejecutar
    filters JSONB DEFAULT '{}',            -- Filtros de leads específicos
    
    -- Estado y control
    is_active BOOLEAN DEFAULT TRUE,
    max_executions INTEGER,                -- Límite de ejecuciones
    error_handling TEXT DEFAULT 'retry',   -- 'retry', 'skip', 'stop'
    retry_count INTEGER DEFAULT 3,
    retry_delay_minutes INTEGER DEFAULT 5,
    
    -- Metadata
    description TEXT,
    tags TEXT[],                           -- Tags para organización
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_executed_at TIMESTAMP,
    execution_count INTEGER DEFAULT 0,
    
    -- Constraints
    FOREIGN KEY (tenant_id, from_status_code) 
        REFERENCES lead_statuses(tenant_id, code) ON DELETE CASCADE,
    FOREIGN KEY (tenant_id, to_status_code) 
        REFERENCES lead_statuses(tenant_id, code) ON DELETE CASCADE,
    CHECK (action_type IN ('email', 'whatsapp', 'task', 'webhook', 'api_call', 'notification')),
    CHECK (execution_mode IN ('immediate', 'delayed', 'scheduled'))
);

-- Índices para búsqueda rápida de triggers activos
CREATE INDEX idx_triggers_active ON lead_status_triggers(tenant_id, is_active, to_status_code);
CREATE INDEX idx_triggers_type ON lead_status_triggers(tenant_id, action_type);
CREATE INDEX idx_triggers_execution ON lead_status_triggers(tenant_id, execution_mode, scheduled_time);
```

### **5. Tabla `lead_status_trigger_logs` (Logging de Automatización):**
```sql
CREATE TABLE lead_status_trigger_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trigger_id UUID REFERENCES lead_status_triggers(id) ON DELETE CASCADE,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    -- Contexto de ejecución
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    from_status_code TEXT,
    to_status_code TEXT NOT NULL,
    
    -- Ejecución
    execution_status TEXT NOT NULL,        -- 'pending', 'running', 'success', 'failed'
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    execution_duration_ms INTEGER,
    
    -- Resultados
    result_data JSONB DEFAULT '{}',        -- Datos de resultado
    error_message TEXT,                    -- Mensaje de error si falló
    error_stack TEXT,                      -- Stack trace para debugging
    retry_count INTEGER DEFAULT 0,
    
    -- Metadata
    worker_id TEXT,                        -- ID del worker que ejecutó
    attempt_number INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Índices
    INDEX idx_trigger_logs_status (execution_status, created_at),
    INDEX idx_trigger_logs_trigger (trigger_id, created_at DESC),
    INDEX idx_trigger_logs_lead (lead_id, created_at DESC),
    INDEX idx_trigger_logs_tenant (tenant_id, created_at DESC)
);
```

### **6. Modificación a tabla `leads` existente:**
```sql
-- Agregar foreign key a lead_statuses
ALTER TABLE leads 
ADD CONSTRAINT fk_leads_status 
FOREIGN KEY (tenant_id, status) 
REFERENCES lead_statuses(tenant_id, code)
ON DELETE RESTRICT;

-- Agregar columnas para tracking avanzado
ALTER TABLE leads 
ADD COLUMN IF NOT EXISTS status_changed_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS status_changed_by UUID REFERENCES users(id),
ADD COLUMN IF NOT EXISTS days_in_current_status INTEGER GENERATED ALWAYS AS (
    EXTRACT(DAY FROM (COALESCE(status_changed_at, created_at) - CURRENT_TIMESTAMP))
) STORED,
ADD COLUMN IF NOT EXISTS status_metadata JSONB DEFAULT '{}';

-- Índices para queries de estado
CREATE INDEX idx_leads_status ON leads(tenant_id, status);
CREATE INDEX idx_leads_status_changed ON leads(tenant_id, status_changed_at DESC);
CREATE INDEX idx_leads_days_in_status ON leads(tenant_id, days_in_current_status);
```

---

## 🔧 **BACKEND - ARQUITECTURA DE SERVICIOS**

### **1. LeadStatusService:**
```python
class LeadStatusService:
    """Servicio principal para gestión de estados de leads"""
    
    async def get_statuses(self, tenant_id: int) -> List[Dict]:
        """Obtiene todos los estados activos para un tenant"""
    
    async def get_available_transitions(self, tenant_id: int, current_status: str) -> List[Dict]:
        """Obtiene transiciones disponibles desde un estado"""
    
    async def validate_transition(self, tenant_id: int, from_status: str, to_status: str) -> bool:
        """Valida si una transición es permitida"""
    
    async def change_lead_status(self, lead_id: UUID, new_status: str, user_id: UUID, comment: str = None) -> Dict:
        """Cambia el estado de un lead con validaciones"""
    
    async def bulk_change_status(self, lead_ids: List[UUID], new_status: str, user_id: UUID) -> Dict:
        """Cambia estado de múltiples leads"""
    
    async def get_status_history(self, lead_id: UUID, limit: int = 50) -> List[Dict]:
        """Obtiene histórico de cambios de estado de un lead"""
```

### **2. LeadAutomationService:**
```python
class LeadAutomationService:
    """Servicio para ejecución de triggers automáticos"""
    
    async def execute_triggers_for_transition(self, tenant_id: int, lead_id: UUID, 
                                              from_status: str, to_status: str) -> List[Dict]:
        """Ejecuta todos los triggers para una transición"""
    
    async def schedule_delayed_trigger(self, trigger_id: UUID, lead_id: UUID, 
                                       execute_at: datetime) -> bool:
        """Programa trigger para ejecución diferida"""
    
    async def process_trigger_queue(self) -> Dict:
        """Procesa cola de triggers pendientes"""
    
    async def retry_failed_triggers(self, hours_ago: int = 24) -> Dict:
        """Reintenta triggers fallados"""
```

### **3. LeadHistoryService:**
```python
class LeadHistoryService:
    """Servicio para gestión de histórico y auditoría"""
    
    async def log_status_change(self, lead_id: UUID, tenant_id: int, 
                                from_status: str, to_status: str, 
                                user_id: UUID, metadata: Dict) -> UUID:
        """Registra un cambio de estado en el histórico"""
    
    async def get_lead_timeline(self, lead_id: UUID, days: int = 30) -> List[Dict]:
        """Obtiene timeline completo de un lead"""
    
    async def get_status_analytics(self, tenant_id: int, start_date: date, 
                                   end_date: date) -> Dict:
        """Genera analytics de cambios de estado"""
    
    async def export_status_history(self, tenant_id: int, format: str = 'csv') -> bytes:
        """Exporta histórico de cambios"""
```

### **4. StatusConfigService:**
```python
class StatusConfigService:
    """Servicio para configuración de estados y workflows"""
    
    async def create_status(self, tenant_id: int, status_data: Dict) -> Dict:
        """Crea un nuevo estado"""
    
    async def update_status(self, tenant_id: int, status_code: str, updates: Dict) -> Dict:
        """Actualiza un estado existente"""
    
    async def define_transition(self, tenant_id: int, transition_data: Dict) -> Dict:
        """Define una nueva transición"""
    
    async def create_trigger(self, tenant_id: int, trigger_data: Dict) -> Dict:
        """Crea un nuevo trigger de automatización"""
    
    async def