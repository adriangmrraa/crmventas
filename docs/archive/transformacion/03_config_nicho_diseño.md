# Diseño de Configuración de Nicho

Este documento define cómo la plataforma cargará y ejecutará la lógica específica de cada nicho (Dental vs CRM) de manera dinámica.

## 1. Estrategia de Configuración

Se propone un enfoque híbrido:
1.  **Código Modular (`modules/`)**: La lógica compleja (Tools de LangChain, Rutas de API) reside en paquetes de Python.
2.  **Configuración en BD (`tenants.niche_config`)**: Cada tenant tiene una referencia a qué módulo de nicho utiliza y configuraciones específicas (ej. qué features habilitar dentro del nicho).

## 2. Esquema de Configuración (JSON)

Este JSON podría residir en una nueva columna `niche_config` en la tabla `tenants` o ser parte del campo `config` existente.

### Ejemplo: Nicho Dental (Actual)
```json
{
  "niche_type": "dental",
  "enabled_features": ["agenda", "clinical_records", "google_calendar_sync"],
  "ui_modules": {
    "dashboard": "dental_dashboard",
    "sidebar_items": ["agenda", "patients", "treatments", "professionals"]
  },
  "agent_config": {
    "system_prompt_source": "modules.dental.prompts.base_prompt",
    "tools_module": "modules.dental.tools",
    "required_context_variables": ["clinic_name", "working_hours"]
  }
}
```

### Ejemplo: Nicho CRM Ventas (Futuro)
```json
{
  "niche_type": "crm_sales",
  "enabled_features": ["lead_scoring", "template_management", "meta_api"],
  "ui_modules": {
    "dashboard": "sales_dashboard",
    "sidebar_items": ["leads", "templates", "campaigns", "analytics_sales"]
  },
  "agent_config": {
    "system_prompt_source": "modules.crm_sales.prompts.setter_prompt",
    "tools_module": "modules.crm_sales.tools",
    "required_context_variables": ["company_name", "product_catalog"]
  }
}
```

## 3. Integración en el Backend (`orchestrator_service`)

### 3.1 Carga Dinámica de Módulos
El archivo `main.py` (o un nuevo `module_loader.py`) deberá implementar un patrón Factory:

```python
# Pseudocódigo de carga
import importlib

def load_niche_routes(app, niche_type):
    try:
        # Importa dinámicamente el router del módulo
        module = importlib.import_module(f"modules.{niche_type}.routes")
        app.include_router(module.router, prefix=f"/niche/{niche_type}")
    except ImportError:
        logger.error(f"No se encontró el módulo para el nicho {niche_type}")
```

### 3.2 Inyección en el Agente
Al instanciar el agente para un tenant específico:

```python
async def get_agent_for_tenant(tenant_id):
    config = await get_tenant_config(tenant_id)
    niche_type = config.get("niche_type", "dental")
    
    # Cargar tools específicas
    tools_module = importlib.import_module(f"modules.{niche_type}.tools")
    tools = tools_module.get_tools(tenant_id)
    
    # Cargar prompt específico
    prompt_module = importlib.import_module(f"modules.{niche_type}.prompts")
    system_prompt = prompt_module.get_prompt(tenant_id)
    
    return AgentExecutor(tools=tools, prompt=system_prompt, ...)
```

## 4. Integración en Frontend

El frontend debe conocer el `niche_type` del usuario logueado (vía `/auth/me` o `/auth/config`) para renderizar el Sidebar correcto.

*   **Lazy Loading**: Los componentes de las vistas dentales (`AgendView`, `PatientDetail`) deben cargarse con `React.lazy` solo si el nicho es 'dental', para no inflar el bundle de usuarios de CRM.

---

## 5. Resumen de Cambios Necesarios

1.  **BD**: Migración para asegurar que `tenants` tenga `niche_type` (default 'dental').
2.  **Backend**: Refactorizar `admin_routes` y `main.py` para soportar carga dinámica.
3.  **Frontend**: Refactorizar `Sidebar.tsx` y `routes.tsx` para ser configurables por nicho.
