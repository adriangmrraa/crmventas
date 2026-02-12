# Plan de Migración: Dentalogic → Nexus Multi-Niche Platform

**Status**: ✅ **COMPLETED** (All 8 phases implemented)

Este documento detalla la transformación real de la plataforma, desde un sistema monolítico dental hacia una arquitectura multi-niche que soporta múltiples verticales de negocio.

---

## 📊 Resumen Ejecutivo

### Plan Original vs. Realidad

**Plan Teórico** (4 fases):
1. Preparación
2. Extracción Core
3. Motor de Configuración
4. Implementación CRM

**Implementación Real** (8 fases especializadas):
1. Agnostic Core Extraction
2. CRM Data Model Design
3. Niche Configuration
4. API Contract Refactoring
5. Parametrizable Tools
6. Dynamic System Prompts
7. Frontend Multi-Niche
8. CRM Data Model Implementation

**Razón de la diferencia**: El diseño granular permitió cambios incrementales con menor riesgo y mayor control de calidad en cada paso.

---

## ✅ Fase 0: Diseño y Documentación (COMPLETADA)

**Objetivo**: Crear los planos técnicos de la transformación.

### Documentos Creados:
1. [`01_inventario_dental.md`](01_inventario_dental.md) - Catálogo de dominio dental
2. [`02_nucleo_agnostico_propuesta.md`](02_nucleo_agnostico_propuesta.md) - Arquitectura Core
3. [`03_config_nicho_diseño.md`](03_config_nicho_diseño.md) - Sistema de configuración
4. [`04_contrato_api_agnostico.md`](04_contrato_api_agnostico.md) - Patrones de routing
5. [`05_tools_parametrizables.md`](05_tools_parametrizables.md) - Tool Registry
6. [`06_system_prompt_dinamico.md`](06_system_prompt_dinamico.md) - Prompt Loader
7. [`07_frontend_multinicho.md`](07_frontend_multinicho.md) - UI Architecture
8. [`08_modelo_crm_ventas.md`](08_modelo_crm_ventas.md) - CRM Data Model
9. [`09_plan_migracion_fases.md`](09_plan_migracion_fases.md) - Este documento
10. [`10_checklist_validacion.md`](10_checklist_validacion.md) - Validation guide

### Archivos de Especificación:
- 10 archivos `.spec.md` en `specs/` con criterios de aceptación Gherkin

**Resultado**: Base teórica sólida para implementación incremental sin ambigüedades.

---

## ✅ Fase 1: Agnostic Core Extraction (COMPLETADA)

**Objetivo**: Separar lógica dental de lógica core sin romper funcionalidad.

### Backend
**Estructura creada**:
```
orchestrator_service/
├── core/                    # [NUEVO] Lógica agnóstica
│   ├── security.py
│   ├── context.py
│   ├── niche_manager.py
│   └── socket_manager.py
└── modules/
    └── dental/              # [MOVIDO] Lógica dental
        ├── routes.py
        ├── tools.py
        └── prompts/
```

**Cambios clave**:
- ✅ Extraído `admin_routes.py` → `modules/dental/routes.py`
- ✅ Creado `core/niche_manager.py` para carga dinámica de módulos
- ✅ Actualizado `main.py` para usar imports dinámicos

### Frontend
**Estructura creada**:
```
frontend_react/src/
├── core/                    # [NUEVO] Shell components
│   └── layout/
│       └── Sidebar.tsx
└── modules/
    └── dental/              # [MOVIDO] Vistas dentales
        └── views/
            ├── AgendaView.tsx
            ├── ProfessionalsView.tsx
            └── ...
```

**Resultado**: Código dental aislado en módulos, core reutilizable.

---

## ✅ Fase 2: CRM Data Model Design (COMPLETADA)

**Objetivo**: Diseñar esquema de datos para el segundo niche (CRM Sales).

### Tablas Diseñadas:
1. **`leads`** - Prospectos (equivalente a `patients`)
2. **`whatsapp_connections`** - Credenciales Meta API
3. **`templates`** - Plantillas de WhatsApp aprobadas
4. **`campaigns`** - Campañas de envío masivo

**Resultado**: Modelo de datos listo para implementación (usado en Fase 8).

---

## ✅ Fase 3: Niche Configuration (COMPLETADA)

**Objetivo**: Habilitar que cada tenant declare su tipo de negocio.

### Database
**Migración aplicada**:
```sql
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS niche_type VARCHAR(50) DEFAULT 'dental';
```

**Valores posibles**: `'dental'`, `'crm_sales'`

### Backend
**Archivos creados/modificados**:
- [`core/niche_manager.py`](../../orchestrator_service/core/niche_manager.py) - Carga dinámica de routers y tools
- `main.py` - Loop de carga automática de niches

**Código clave**:
```python
SUPPORTED_NICHES = ["dental", "crm_sales"]
for niche in SUPPORTED_NICHES:
    NicheManager.load_niche_router(app, niche)
```

### Frontend
**Archivos modificados**:
- [`Sidebar.tsx`](../../frontend_react/src/core/layout/Sidebar.tsx) - Filtrado de items por `user.niche_type`
- [`AuthContext.tsx`](../../frontend_react/src/context/AuthContext.tsx) - Almacena `niche_type` del usuario

**Resultado**: Tenants pueden tener diferentes configuraciones, UI se adapta automáticamente.

---

## ✅ Fase 4: API Contract Refactoring (COMPLETADA)

**Objetivo**: Establecer convención de rutas para core vs. niche-specific.

### Convención de Rutas:
- **Core Admin**: `/admin/core/*` (usuarios, tenants, configuración)
  - Ejemplo: `GET /admin/core/users`
- **Dental Niche**: `/admin/dental/*` (pacientes, turnos, odontología)
  - Ejemplo: `GET /admin/dental/appointments`
- **CRM Niche**: `/niche/crm_sales/*` (leads, campañas, templates)
  - Ejemplo: `GET /niche/crm_sales/leads`

### Backend
**Archivos modificados**:
- `admin_routes.py` - Renombrado a `core/admin_routes.py` con rutas core
- `modules/dental/routes.py` - Rutas dentales con prefijo `/dental`

**Resultado**: API organizada por responsabilidad, fácil de escalar.

---

## ✅ Fase 5: Parametrizable Tools (COMPLETADA)

**Objetivo**: Permitir que cada niche defina sus propias herramientas para el agente.

### Backend
**Archivos creados**:
- [`core/tools.py`](../../orchestrator_service/core/tools.py) - `ToolRegistry` central
- [`modules/dental/tools_provider.py`](../../orchestrator_service/modules/dental/tools_provider.py) - Registro de tools dentales

**Patrón de uso**:
```python
# Cada módulo registra sus tools
from core.tools import tool_registry

@tool_registry.register("schedule_appointment", niche="dental")
def schedule_appointment_tool(...):
    pass
```

**Resultado**: Agentes tienen acceso solo a las tools relevantes para su niche.

---

## ✅ Fase 6: Dynamic System Prompts (COMPLETADA)

**Objetivo**: Cargar system prompts específicos según el niche del tenant.

### Backend
**Archivos creados**:
- [`core/agent/prompt_loader.py`](../../orchestrator_service/core/agent/prompt_loader.py) - Carga dinámica de prompts

**Estructura de prompts**:
```
modules/
├── dental/prompts/
│   └── base_assistant.txt   # Prompt dental
└── crm_sales/prompts/
    └── sales_assistant.txt    # Prompt CRM (futuro)
```

**Código clave**:
```python
prompt = prompt_loader.load_prompt(niche_type, tenant_id)
```

**Resultado**: Agente adapta su personalidad y expertise según el vertical de negocio.

---

## ✅ Fase 7: Frontend Multi-Niche (COMPLETADA)

**Objetivo**: Actualizar frontend para usar nuevas rutas del backend.

### Cambios Realizados:
- ✅ Actualizadas **27 API endpoints** en 11 archivos TypeScript/TSX
- ✅ Cambio: `/admin/*` → `/admin/core/*` para rutas core

### Archivos Modificados:
| Archivo | Endpoints Actualizados |
|---------|------------------------|
| `UserApprovalView.tsx` | 4 |
| `ChatsView.tsx` | 8 |
| `ClinicsView.tsx` | 4 |
| `Stores.tsx` | 3 |
| `ConfigView.tsx` | 2 |
| `DashboardView.tsx` | 2 |
| `Setup.tsx` | 2 |
| `Credentials.tsx` | 1 |
| `ProfessionalsView.tsx` | 1 |
| `AgendaView.tsx` | 1 |
| `LanguageContext.tsx` | 1 |

**Resultado**: Frontend sincronizado con backend, sin 404s.

---

## ✅ Fase 8: CRM Data Model Implementation (COMPLETADA)

**Objetivo**: Implementar API y base de datos para el niche CRM.

### Database
**Migración aplicada** (ya existía en `db.py` como Patch 16):
- Tablas: `leads`, `whatsapp_connections`, `templates`, `campaigns`
- Todos con `tenant_id` para multi-tenancy

### Backend
**Archivos creados**:
- [`modules/crm_sales/models.py`](../../orchestrator_service/modules/crm_sales/models.py) - Pydantic models
- [`modules/crm_sales/routes.py`](../../orchestrator_service/modules/crm_sales/routes.py) - 16 endpoints CRUD

**Endpoints CRM**:
- **Leads**: 8 endpoints (GET, POST, PUT, assign, stage)
- **WhatsApp**: 2 endpoints
- **Templates**: 2 endpoints
- **Campaigns**: 3 endpoints + launch

**Resultado**: Backend listo para tenants CRM, frontend pending (futuro).

---

## 🎯 Estado Actual de la Plataforma

### Capacidades Habilitadas:
✅ Multi-tenancy con soberanía de datos  
✅ Dos verticales soportados: Dental, CRM Sales  
✅ Carga dinámica de módulos por niche  
✅ API organizada por responsabilidad  
✅ Frontend actualizado para dental  

### Pendiente:
⏳ Frontend CRM (vistas de leads, campañas)  
⏳ Integración Meta API (WhatsApp templates)  
⏳ Testing automatizado end-to-end  
⏳ Despliegue a producción  

---

## 🔄 Procedimientos de Rollback

### Si falla en Producción:
1. **Database**: Las migraciones son aditivas (`IF NOT EXISTS`), seguro hacer rollback de código
2. **Backend**: Revertir a imagen Docker anterior vía Git tag
3. **Frontend**: Revertir deployment en plataforma de hosting
4. **Verificación**: Smoke test en endpoints `/admin/core/users` y `/admin/dental/appointments`

### Rollback Selectivo:
- **Solo Backend**: Revertir código, DB mantiene compatibilidad
- **Solo Frontend**: Revertir deployment, backend responde a ambas versiones de rutas (temporal)

---

## 📝 Lecciones Aprendidas

### ✅ Aciertos:
1. **Diseño primero**: Los 10 documentos de diseño evitaron retrabajos
2. **Fases granulares**: 8 fases pequeñas fueron más controlables que 4 grandes
3. **Idempotencia**: Migraciones con `IF NOT EXISTS` permitieron tests sin miedo
4. **Multi-tenancy desde día 1**: Toda tabla tiene `tenant_id`, no hay deuda técnica

### ⚠️ Desafíos:
1. **Coordinación Frontend-Backend**: Deploy debe ser sincronizado (breaking changes)
2. **Testing manual**: Falta suite automatizada, validación es manual y lenta
3. **Documentación drift**: Docs pueden quedar desactualizados si no se mantienen

---

## 🚀 Próximos Pasos (Futuro)

### Fase 10: CRM Frontend (Pendiente)
- Crear vistas React para gestión de leads
- Dashboard de campañas
- UI para templates de WhatsApp

### Fase 11: Meta Integration (Pendiente)
- OAuth con Meta Business
- Sincronización de templates
- Envío de mensajes vía WhatsApp API

### Fase 12: Testing & CI/CD (Pendiente)
- Pytest para backend (coverage >80%)
- Vitest para frontend
- GitHub Actions pipeline

---

**Documento actualizado**: 2026-02-12  
**Autor**: Adrián (con asistencia de Antigravity AI)
