# 📊 PLAN DE MEJORA: SISTEMA AVANZADO DE ESTADOS PARA LEADS

**Fecha:** 26 de Febrero 2026  
**Contexto:** Mejora del tracking de estados de leads en CRM Ventas  
**Estado:** 📋 **PLANIFICACIÓN** (no ejecución)

---

## 🎯 **VISIÓN Y OBJETIVOS**

### **Problema Actual:**
- Estados de leads básicos o limitados
- Cambio de estados no centralizado en UI
- Falta de automatización en transiciones de estado
- No hay triggers/acciones automáticas al cambiar estado

### **Objetivos de la Mejora:**

#### **1. UI Avanzada:**
- **Selector de estados** desde cualquier vista de lead
- **Visualización clara** del estado actual y histórico
- **Transiciones permitidas** definidas por workflow
- **Bulk actions** para cambiar múltiples leads

#### **2. Persistencia Robusta:**
- **Base de datos** con histórico de cambios
- **Audit trail** quién, cuándo y por qué cambió el estado
- **Integridad referencial** con tablas existentes

#### **3. Automatización:**
- **Triggers/Acciones** al cambiar estado
- **Notificaciones** automáticas
- **Workflows** predefinidos
- **Integración** con otras funcionalidades

#### **4. Escalabilidad:**
- **Sistema configurable** por tenant
- **Estados personalizables**
- **Workflows adaptables** a diferentes tipos de negocio

---

## 📈 **ANÁLISIS DEL ESTADO ACTUAL**

### **Tabla `leads` existente:**
```sql
-- Columnas actuales relevantes:
- id UUID PRIMARY KEY
- tenant_id INTEGER REFERENCES tenants(id)
- status TEXT  -- Estado actual (ej: 'new', 'contacted', 'qualified', 'converted')
- created_at TIMESTAMP
- updated_at TIMESTAMP
```

### **Limitaciones identificadas:**
1. **Estados fijos** - No configurables por tenant
2. **Sin histórico** - No se guarda quién/cuándo cambió
3. **Sin workflow** - Cualquier transición permitida
4. **Sin triggers** - No hay acciones automáticas
5. **UI básica** - Selector simple sin contexto

---

## 🏗️ **ARQUITECTURA PROPUESTA**

### **Componentes del Sistema:**

#### **1. Configuración de Estados (Backend):**
- **Tabla `lead_statuses`** - Estados disponibles por tenant
- **Tabla `lead_status_transitions`** - Transiciones permitidas
- **Tabla `lead_status_triggers`** - Acciones automáticas

#### **2. Histórico y Tracking:**
- **Tabla `lead_status_history`** - Audit trail completo
- **Integración** con sistema de auditoría existente (Nexus v7.7.1)

#### **3. UI/UX Mejorada:**
- **Componente `LeadStatusSelector`** - Selector avanzado
- **Vista `LeadStatusHistory`** - Histórico visual
- **Bulk actions** en lista de leads
- **Badges/indicadores** visuales

#### **4. Automatización:**
- **Service `LeadAutomationService`** - Ejecuta triggers
- **Integración** con WhatsApp, email, tasks
- **Sistema de notificaciones** push/in-app

---

## 🔄 **WORKFLOWS DE ESTADO TÍPICOS**

### **Workflow Básico CRM:**
```
Nuevo → Contactado → Calificado → Negociación → Ganado/Perdido
```

### **Workflow Avanzado (Configurable):**
```
Nuevo
  ↓
Contactado (Email/WhatsApp)
  ↓
Interesado (Demo agendada)
  ↓
Calificado (Fit confirmado)
  ↓
Propuesta Enviada
  ↓
Negociación
  ↓
[ Ganado → Cliente ]
[ Perdido → Archivado ]
```

### **Estados Especiales:**
- **En Pausa** - Lead temporalmente inactivo
- **Recontactar** - Programado para follow-up
- **No Calificado** - No es prospecto válido
- **Duplicado** - Lead repetido

---

## ⚙️ **TRIGGERS Y AUTOMATIZACIONES**

### **Tipos de Triggers:**
1. **Notificaciones:**
   - Email al vendedor asignado
   - Notificación in-app
   - Mensaje WhatsApp al lead

2. **Acciones de Sistema:**
   - Crear tarea automática
   - Programar follow-up
   - Actualizar pipeline analytics

3. **Integraciones:**
   - Sincronizar con Google Calendar
   - Actualizar Meta Ads conversion
   - Enviar a sistema externo

### **Ejemplos de Automatización:**
- **Lead → Contactado:** Enviar email de bienvenida automático
- **Contactado → Calificado:** Crear tarea "Preparar propuesta"
- **Calificado → Propuesta Enviada:** Programar follow-up en 3 días
- **Ganado:** Crear cliente automáticamente

---

## 🎨 **UI/UX MEJORADA**

### **Componentes a Desarrollar:**

#### **1. LeadStatusSelector:**
- **Dropdown inteligente** con transiciones permitidas
- **Badges coloreados** por estado
- **Tooltips** con descripción del estado
- **Validación** en tiempo real

#### **2. LeadStatusHistoryPanel:**
- **Timeline visual** de cambios
- **Filtros** por fecha/usuario
- **Exportación** a CSV/PDF
- **Comentarios** en cada cambio

#### **3. Bulk Status Updater:**
- **Selección múltiple** en lista de leads
- **Cambio masivo** de estados
- **Validación** de transiciones permitidas
- **Preview** antes de aplicar

#### **4. Status Dashboard:**
- **Pipeline visualization** - Gráfico de embudo
- **Conversion rates** por estado
- **Time in stage** analytics
- **Forecasting** basado en histórico

---

## 🗄️ **BASE DE DATOS - ESQUEMA PROPUESTO**

### **Nuevas Tablas:**

#### **1. lead_statuses:**
```sql
CREATE TABLE lead_statuses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    name TEXT NOT NULL,                    -- 'Nuevo', 'Contactado', etc.
    code TEXT NOT NULL,                    -- 'new', 'contacted', etc.
    description TEXT,
    color VARCHAR(7),                      -- '#3B82F6' (blue-500)
    icon VARCHAR(50),                      -- 'circle', 'check', 'clock', etc.
    is_active BOOLEAN DEFAULT TRUE,
    is_initial BOOLEAN DEFAULT FALSE,      -- Estado inicial para nuevos leads
    is_final BOOLEAN DEFAULT FALSE,        -- Estado final (Ganado/Perdido)
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, code)
);
```

#### **2. lead_status_transitions:**
```sql
CREATE TABLE lead_status_transitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    from_status_code TEXT NOT NULL,        -- Código estado origen
    to_status_code TEXT NOT NULL,          -- Código estado destino
    is_allowed BOOLEAN DEFAULT TRUE,
    requires_comment BOOLEAN DEFAULT FALSE,
    auto_trigger TEXT,                     -- Trigger automático opcional
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id, from_status_code) REFERENCES lead_statuses(tenant_id, code),
    FOREIGN KEY (tenant_id, to_status_code) REFERENCES lead_statuses(tenant_id, code)
);
```

#### **3. lead_status_history:**
```sql
CREATE TABLE lead_status_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID NOT NULL REFERENCES leads(id),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    from_status_code TEXT,                 -- NULL para estado inicial
    to_status_code TEXT NOT NULL,
    changed_by_user_id UUID REFERENCES users(id),
    changed_by_name TEXT,                  -- Cache del nombre para performance
    comment TEXT,                          -- Comentario opcional del cambio
    metadata JSONB DEFAULT '{}',           -- Datos adicionales
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_lead_status_history_lead (lead_id, created_at DESC),
    INDEX idx_lead_status_history_tenant (tenant_id, created_at)
);
```

#### **4. lead_status_triggers:**
```sql
CREATE TABLE lead_status_triggers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    trigger_name TEXT NOT NULL,            -- 'send_welcome_email', 'create_task', etc.
    from_status_code TEXT,                 -- NULL para cualquier estado origen
    to_status_code TEXT NOT NULL,          -- Estado destino que activa el trigger
    action_type TEXT NOT NULL,             -- 'email', 'whatsapp', 'task', 'webhook'
    action_config JSONB NOT NULL,          -- Configuración específica de la acción
    is_active BOOLEAN DEFAULT TRUE,
    delay_minutes INTEGER DEFAULT 0,       -- Retardo antes de ejecutar
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### **Modificación a tabla `leads`:**
```sql
-- Agregar foreign key a lead_statuses
ALTER TABLE leads 
ADD CONSTRAINT fk_leads_status 
FOREIGN KEY (tenant_id, status) 
REFERENCES lead_statuses(tenant_id, code);
```

---

## 🔧 **BACKEND - SERVICIOS Y ENDPOINTS**

### **Nuevos Servicios:**

#### **1. LeadStatusService:**
- Gestión de estados y transiciones
- Validación de cambios de estado
- Carga de configuración por tenant

#### **2. LeadAutomationService:**
- Ejecución de triggers automáticos
- Manejo de colas de acciones
- Retry logic para fallos

#### **3. LeadHistoryService:**
- Registro de cambios de estado
- Consulta de histórico
- Exportación de datos

### **Nuevos Endpoints:**

#### **1. Gestión de Estados:**
```
GET    /admin/core/crm/lead-statuses           # Lista estados del tenant
POST   /admin/core/crm/lead-statuses           # Crear nuevo estado
PUT    /admin/core/crm/lead-statuses/{code}    # Actualizar estado
DELETE /admin/core/crm/lead-statuses/{code}    # Eliminar estado (soft delete)
```

#### **2. Transiciones:**
```
GET    /admin/core/crm/lead-statuses/{code}/transitions  # Transiciones desde un estado
POST   /admin/core/crm/lead-statuses/transitions         # Definir transición
DELETE /admin/core/crm/lead-statuses/transitions/{id}    # Eliminar transición
```

#### **3. Cambio de Estado:**
```
POST   /admin/core/crm/leads/{id}/status       # Cambiar estado de un lead
POST   /admin/core/crm/leads/bulk-status       # Cambio masivo de estados
```

#### **4. Histórico:**
```
GET    /admin/core/crm/leads/{id}/status-history  # Histórico de cambios
GET    /admin/core/crm/leads/status-analytics     # Analytics de estados
```

#### **5. Triggers/Automatización:**
```
GET    /admin/core/crm/lead-triggers           # Lista triggers
POST   /admin/core/crm/lead-triggers           # Crear trigger
PUT    /admin/core/crm/lead-triggers/{id}      # Actualizar trigger
DELETE /admin/core/crm/lead-triggers/{id}      # Eliminar trigger
```

---

## 🎨 **FRONTEND - COMPONENTES Y VISTAS**

### **Componentes Nuevos:**

#### **1. LeadStatusBadge:**
- Badge coloreado con icono
- Tooltip con descripción
- Estado clickeable para cambiar

#### **2. LeadStatusSelector:**
- Dropdown con estados disponibles
- Validación de transiciones
- Campo para comentario (opcional)

#### **3. LeadStatusHistory:**
- Timeline de cambios
- Filtros por fecha/usuario
- Exportación de datos

#### **4. LeadPipelineView:**
- Vista kanban o embudo
- Drag & drop entre estados
- Estadísticas en tiempo real

### **Vistas Modificadas/Mejoradas:**

#### **1. LeadsView:**
- **Columna estado** con badge interactivo
- **Filtros por estado** avanzados
- **Bulk actions** para cambio masivo
- **Pipeline visualization** opcional

#### **2. LeadDetailView:**
- **Sección estado** prominente
- **Histórico de cambios** integrado
- **Selector de estado** en contexto
- **Próximos pasos** sugeridos

#### **3. ConfigView (nueva pestaña):**
- **Configuración de estados** por tenant
- **Definición de workflows**
- **Configuración de triggers**
- **Personalización de colores/iconos**

---

## 🚀 **PLAN DE IMPLEMENTACIÓN**

### **Fase 1: Base de Datos y Backend (2-3 días)**
1. Crear tablas nuevas
2. Implementar servicios backend
3. Crear endpoints básicos
4. Migración datos existentes

### **Fase 2: UI Básica (2-3 días)**
1. Componente LeadStatusBadge
2. Componente LeadStatusSelector
3. Integración en LeadsView y LeadDetailView
4. Cambio individual de estados

### **Fase 3: Funcionalidades Avanzadas (3-4 días)**
1. Bulk actions
2. Histórico de cambios
3. Pipeline visualization
4. Filtros avanzados

### **Fase 4: Automatización (2-3 días)**
1. Sistema de triggers
2. Configuración UI
3. Integración con notificaciones
4. Testing end-to-end

### **Fase 5: Polish y Documentación (1-2 días)**
1. UI/UX refinements
2. Performance optimizations
3. Documentación completa
4. User training materials

---

## 📊 **MÉTRICAS DE ÉXITO**

### **Técnicas:**
- ✅ **Performance:** Cambio de estado < 200ms
- ✅ **Confiabilidad:** 99.9% uptime del servicio
- ✅ **Escalabilidad:** Soporte 10,000+ leads por tenant
- ✅ **Auditability:** Histórico completo de todos los cambios

### **De Negocio:**
- 📈 **Conversion rate improvement:** +15% objetivo
- ⏱️ **Time to conversion reduction:** -20% objetivo
- 👥 **User adoption:** 90%+ de vendedores usando el sistema
- 🔄 **Automation rate:** 40%+ de cambios con triggers automáticos

---

## 🔗 **INTEGRACIONES EXISTENTES**

### **Con Sistema Actual:**
1. **Nexus Security v7.7.1** - Audit logging automático
2. **Multi-tenant isolation** - Filtrado por `tenant_id`
3. **Existing leads table** - Migración suave de datos
4. **User authentication** - Registro de `changed_by_user_id`

### **Con Otras Funcionalidades:**
1. **Marketing Hub** - Triggers para leads de Meta Ads
2. **WhatsApp Service** - Notificaciones automáticas
3. **Email system** - Comunicaciones programadas
4. **Task management** - Tareas automáticas

---

## ⚠️ **RIESGOS Y MITIGACIONES**

### **Riesgos Técnicos:**
1. **Migración de datos** - Backup completo antes de cambios
2. **Performance impact** - Indexes optimizados desde inicio
3. **Backward compatibility** - Mantener API existente durante transición

### **Riesgos de Negocio:**
1. **User adoption** - Training y documentación clara
2. **Workflow disruption** - Implementación gradual por tenant
3. **Data integrity** - Validaciones estrictas y rollback plan

---

## 🎯 **PRÓXIMOS PASOS (PLANIFICACIÓN)**

### **Documentación Adicional a Cre