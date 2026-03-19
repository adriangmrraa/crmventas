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
    
    async def import_workflow_template(self, tenant_id: int, template_name: str) -> Dict:
        """Importa un workflow predefinido"""
```

### **5. StatusValidationService:**
```python
class StatusValidationService:
    """Servicio para validaciones complejas de estados"""
    
    async def validate_status_change(self, lead_id: UUID, new_status: str, 
                                     user_id: UUID) -> ValidationResult:
        """Valida todos los aspectos de un cambio de estado"""
    
    async def check_pre_conditions(self, lead_id: UUID, transition_data: Dict) -> bool:
        """Verifica condiciones previas para una transición"""
    
    async def validate_bulk_operation(self, lead_ids: List[UUID], new_status: str) -> BulkValidationResult:
        """Valida operación masiva de cambio de estado"""
    
    async def get_validation_rules(self, tenant_id: int, status_code: str) -> Dict:
        """Obtiene reglas de validación para un estado"""
```

---

## 🌐 **FRONTEND - ARQUITECTURA DE COMPONENTES**

### **1. LeadStatusBadge Component:**
```typescript
interface LeadStatusBadgeProps {
  statusCode: string;
  statusName?: string;
  color?: string;
  icon?: string;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  onClick?: () => void;
}

// Características:
// - Badge coloreado con tooltip
// - Icono dinámico basado en estado
// - Tamaños responsivos
// - Click para abrir selector
```

### **2. LeadStatusSelector Component:**
```typescript
interface LeadStatusSelectorProps {
  leadId: string;
  currentStatusCode: string;
  onStatusChange: (newStatus: string, comment?: string) => Promise<void>;
  showCommentField?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

// Características:
// - Dropdown con transiciones disponibles
// - Validación en tiempo real
// - Campo de comentario opcional
// - Loading states durante cambios
// - Error handling con rollback visual
```

### **3. LeadStatusTimeline Component:**
```typescript
interface LeadStatusTimelineProps {
  leadId: string;
  limit?: number;
  showDetails?: boolean;
  onItemClick?: (historyItem: StatusHistory) => void;
}

// Características:
// - Timeline visual de cambios
// - Filtros por fecha/usuario
// - Export a PDF/CSV
// - Integración con sistema de auditoría
```

### **4. BulkStatusUpdate Component:**
```typescript
interface BulkStatusUpdateProps {
  selectedLeadIds: string[];
  onComplete: (results: BulkUpdateResult[]) => void;
  onCancel: () => void;
}

// Características:
// - Modal para operaciones masivas
// - Progress bar durante procesamiento
// - Resultados detallados (éxitos/fallos)
// - Retry para operaciones fallidas
```

### **5. StatusConfigView Component:**
```typescript
interface StatusConfigViewProps {
  tenantId: number;
  onSave: (config: StatusConfig) => Promise<void>;
  onTest: (config: StatusConfig) => Promise<void>;
}

// Características:
// - Drag & drop para workflow builder
// - Preview de estados y transiciones
// - Testing de triggers
// - Import/export de configuraciones
```

---

## 🔗 **INTEGRACIONES Y DEPENDENCIAS**

### **1. Con Sistema Existente:**
- **Nexus Security v7.7.1** - Para audit logging y rate limiting
- **Multi-tenant Architecture** - Aislamiento de datos por `tenant_id`
- **Existing User System** - Para `changed_by_user_id` tracking
- **Email/Notification System** - Para triggers de notificación

### **2. Servicios Externos:**
- **WhatsApp Service** - Para triggers de mensajes automáticos
- **Email Service** - Para triggers de correos automáticos
- **Task Management** - Para creación automática de tareas
- **Webhook System** - Para integraciones con herramientas externas

### **3. Infraestructura:**
- **PostgreSQL 14+** - Para tablas relacionales
- **Redis** - Para cache de estados frecuentes
- **Message Queue** - Para procesamiento async de triggers
- **Monitoring Stack** - Para métricas y alertas

---

## 📊 **CONSIDERACIONES DE PERFORMANCE**

### **1. Estrategias de Caching:**
```python
# Cache de estados por tenant (TTL: 1 hora)
STATUS_CACHE_KEY = f"lead_statuses:{tenant_id}"
statuses = await cache.get(STATUS_CACHE_KEY)
if not statuses:
    statuses = await db.get_statuses(tenant_id)
    await cache.set(STATUS_CACHE_KEY, statuses, ttl=3600)

# Cache de transiciones por estado (TTL: 30 minutos)
TRANSITIONS_CACHE_KEY = f"transitions:{tenant_id}:{current_status}"
```

### **2. Optimización de Consultas:**
```sql
-- Usar vistas materializadas para reports frecuentes
CREATE MATERIALIZED VIEW mv_lead_status_daily AS
SELECT 
    tenant_id,
    DATE(created_at) as date,
    to_status_code,
    COUNT(*) as change_count
FROM lead_status_history
GROUP BY tenant_id, DATE(created_at), to_status_code;

-- Refresh cada hora
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_lead_status_daily;
```

### **3. Particionamiento de Datos:**
```sql
-- Particionar histórico por mes para grandes volúmenes
CREATE TABLE lead_status_history PARTITION BY RANGE (created_at);

CREATE TABLE lead_status_history_2026_02 
PARTITION OF lead_status_history
FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
```

### **4. Índices Críticos:**
```sql
-- Para queries de dashboard
CREATE INDEX idx_dashboard ON leads(tenant_id, status, created_at);

-- Para búsquedas por usuario
CREATE INDEX idx_user_changes ON lead_status_history(changed_by_user_id, created_at DESC);

-- Para analytics
CREATE INDEX idx_analytics ON lead_status_history(tenant_id, to_status_code, created_at);
```

---

## 🛡️ **CONSIDERACIONES DE SEGURIDAD**

### **1. Tenant Isolation:**
```python
# TODAS las queries deben incluir tenant_id
async def get_lead_status(self, tenant_id: int, lead_id: UUID):
    query = """
        SELECT * FROM lead_status_history 
        WHERE lead_id = $1 AND tenant_id = $2
        ORDER BY created_at DESC
    """
    return await self.db.fetch(query, lead_id, tenant_id)
```

### **2. Role-Based Access Control:**
```python
# Definir permisos por rol
STATUS_CHANGE_PERMISSIONS = {
    'sales_rep': ['new', 'contacted', 'qualified'],
    'sales_manager': ['new', 'contacted', 'qualified', 'proposal_sent', 'negotiation'],
    'ceo': ALL_STATUSES,
    'admin': ALL_STATUSES
}
```

### **3. Rate Limiting:**
```python
# Limitar cambios masivos
RATE_LIMITS = {
    'status_change': {'limit': 100, 'period': 60},  # 100 cambios/minuto
    'bulk_status_change': {'limit': 5, 'period': 300},  # 5 operaciones masivas/5min
}
```

### **4. Audit Logging:**
```python
# Log detallado de todos los cambios
audit_logger.log({
    'event': 'lead_status_change',
    'lead_id': str(lead_id),
    'from_status': from_status,
    'to_status': to_status,
    'user_id': str(user_id),
    'user_ip': request.client.host,
    'user_agent': request.headers.get('user-agent'),
    'timestamp': datetime.utcnow().isoformat(),
    'metadata': metadata
})
```

---

## 🚀 **PLAN DE IMPLEMENTACIÓN TÉCNICO**

### **Fase 1: Infraestructura (Días 1-3)**
1. **Día 1:** Diseño DB + scripts migración
2. **Día 2:** Implementación tablas + índices
3. **Día 3:** Servicios core + validaciones básicas

### **Fase 2: Compatibilidad (Días 4-6)**
4. **Día 4:** Migración datos existentes
5. **Día 5:** Testing compatibilidad completa
6. **Día 6:** Endpoints API + integración existente

### **Fase 3: Funcionalidad Nueva (Días 7-9)**
7. **Día 7:** Componentes frontend básicos
8. **Día 8:** Integración UI existente
9. **Día 9:** Testing end-to-end

### **Fase 4: Automatización (Días 10-11)**
10. **Día 10:** Sistema triggers + queue
11. **Día 11:** Configuración UI + testing

### **Fase 5: Polish (Días 12-13)**
12. **Día 12:** Performance optimizations
13. **Día 13:** Monitoring + alerting + docs

---

## 🎯 **RECOMENDACIONES ARQUITECTÓNICAS PARA DEVS**

### **🔧 **PATRONES ARQUITECTÓNICOS RECOMENDADOS:**

#### **1. Event-Driven Architecture para Triggers:**
```python
# Emitir eventos en lugar de llamadas directas
async def change_lead_status(lead_id, new_status, user_id):
    # 1. Validar y ejecutar cambio
    await validate_and_execute_change(lead_id, new_status, user_id)
    
    # 2. Emitir evento
    await event_bus.publish('lead.status.changed', {
        'lead_id': lead_id,
        'from_status': old_status,
        'to_status': new_status,
        'user_id': user_id,
        'timestamp': datetime.utcnow()
    })
    
    # 3. Handlers escuchan evento y ejecutan triggers
    #    → Email handler envía notificación
    #    → WhatsApp handler envía mensaje
    #    → Task handler crea tarea
```

#### **2. CQRS para Histórico y Analytics:**
```python
# Separar comandos (write) de queries (read)
class LeadStatusCommandHandler:
    async def handle_change_status(self, command: ChangeStatusCommand):
        # Write side: validar + actualizar DB
        # Emitir eventos de dominio

class LeadStatusQueryHandler:
    async def handle_get_status_history(self, query: GetStatusHistoryQuery):
        # Read side: consultar vistas optimizadas
        # Usar cache, vistas materializadas
```

#### **3. Circuit Breaker para Integraciones Externas:**
```python
# Proteger contra fallos de servicios externos
class TriggerExecutor:
    def __init__(self):
        self.email_circuit = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=300
        )
        self.whatsapp_circuit = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=600
        )
    
    async def execute_email_trigger(self, trigger, lead_data):
        async with self.email_circuit:
            return await email_service.send(trigger.template, lead_data)
```

### **💡 **DECISIONES ARQUITECTÓNICAS CRÍTICAS:**

#### **1. Base de Datos: Normalización vs Performance**
```sql
-- ❌ SOBRE-NORMALIZACIÓN: Demasiadas joins para consultas frecuentes
SELECT l.*, ls.name, ls.color, ls.icon
FROM leads l
JOIN lead_statuses ls ON l.tenant_id = ls.tenant_id AND l.status = ls.code
JOIN lead_status_history lsh ON l.id = lsh.lead_id
WHERE l.tenant_id = 1;

-- ✅ BALANCEADO: Denormalización estratégica
-- lead_status_history almacena nombres/colores en el momento del cambio
-- leads tiene cache de status_changed_at, status_changed_by
```

#### **2. Cache Strategy: Invalidation Complex**
```python
# ❌ CACHE NAIVE: Invalidación manual propensa a errores
cache.delete(f"lead:{lead_id}")

# ✅ CACHE PATTERN: Tags-based invalidation
cache.set(f"lead:{lead_id}", lead_data, tags=[f"tenant:{tenant_id}", "leads"])
# Invalidar todo cache de tenant cuando cambia configuración
cache.delete_by_tag(f"tenant:{tenant_id}")
```

#### **3. Async Processing: Queue vs Direct**
```python
# ❌ SYNCHRONOUS: Bloquea respuesta HTTP
async def change_status(lead_id, new_status):
    # Operación larga...
    await send_email_notification()  # 2-5 segundos
    await create_followup_task()     # 1-2 segundos
    return response  # Usuario espera 3-7 segundos

# ✅ ASYNC: Respuesta inmediata, procesamiento en background
async def change_status(lead_id, new_status):
    # Cambio inmediato
    await db.execute(...)
    
    # Encolar tareas async
    await queue.enqueue('send_status_change_email', lead_id, new_status)
    await queue.enqueue('create_followup_task', lead_id, new_status)
    
    return response  # Usuario recibe respuesta en < 200ms
```

### **🔍 **CONSIDERACIONES DE ESCALABILIDAD:**

#### **1. Particionamiento Horizontal:**
```sql
-- Plan para > 1 millón de leads por tenant
-- 1. Particionar por tenant_id (sharding)
-- 2. Particionar histórico por tiempo (monthly partitions)
-- 3. Usar read replicas para queries de reporting
```

#### **2. Carga de Trabajo Separada:**
```python
# Separar servicios por tipo de carga
class RealTimeStatusService:  # Low latency, high throughput
    async def change_status(self, lead_id, new_status):
        # Operaciones críticas de baja latencia
        
class BackgroundProcessingService:  # High latency, batch processing
    async def process_bulk_updates(self, lead_ids, new_status):
        # Operaciones masivas, puede tomar minutos
        
class AnalyticsService:  # Read-heavy, complex queries
    async def generate_status_report(self, tenant_id, date_range):
        # Consultas complejas, puede usar vistas materializadas
```

#### **3. Monitoring de Capacity Planning:**
```yaml
# Alertas de capacidad
alerts:
  - name: HighStatusHistoryGrowth
    expr: rate(pg_table_size_bytes{table="lead_status_history"}[24h]) > 10GB
    for: 1h
    
  - name: HighTriggerQueueBacklog
    expr: redis_queue_length{queue="status_triggers"} > 10000
    for: 30m
    
  - name: DatabaseConnectionPoolExhausted
    expr: pg_connection_pool_used{pool="status_service"} > 0.9
    for: 5m
```

### **🔧 **HERRAMIENTAS Y CONFIGURACIÓN RECOMENDADA:**

#### **1. Database Configuration:**
```sql
-- PostgreSQL tuning para este workload
ALTER DATABASE crmventas SET work_mem = '64MB';
ALTER DATABASE crmventas SET maintenance_work_mem = '1GB';
ALTER DATABASE crmventas SET effective_cache_size = '8GB';

-- Extensions útiles
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pg_partman" FOR PARTITION MANAGEMENT;
```

#### **2. Application Configuration:**
```yaml
# config/status_service.yaml
database:
  pool_size: 20
  max_overflow: 10
  pool_recycle: 3600

cache:
  redis:
    host: redis-cluster
    ttl_default: 3600
    ttl_statuses: 7200

queue:
  workers: 10
  max_retries: 3
  retry_delay: 60

rate_limits:
  status_changes_per_user_per_minute: 100
  bulk_operations_per_user_per_hour: 10
```

#### **3. Deployment Configuration:**
```dockerfile
# Dockerfile para status service
FROM python:3.11-slim

# Instalar dependencias de performance
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Configurar para low latency
ENV PYTHONUNBUFFERED=1
ENV UVICORN_WORKERS=4
ENV UVICORN_TIMEOUT=30

# Health checks específicos
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```

### **🎯 **CHECKLIST DE IMPLEMENTACIÓN ARQUITECTÓNICA:**

#### **✅ PRE-IMPLEMENTACIÓN:**
- [ ] **Capacity planning** basado