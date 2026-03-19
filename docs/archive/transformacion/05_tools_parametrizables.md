# Diseño de Tools Parametrizables por Nicho

Este documento define la arquitectura para cargar dinámicamente las herramientas (Tools) de LangChain según el nicho del tenant, eliminando el hardcoding actual en `main.py`.

## 1. Problema Actual
Actualmente, `main.py` importa explícitamente `check_availability` y `book_appointment` y las pasa al `AgentExecutor`. Esto impide que un tenant de CRM (que necesita `list_leads`) funcione sin cargar tools dentales innecesarias.

## 2. Propuesta de Solución: Tool Registry Pattern

Se propone crear un `ToolRegistry` central que actúe como factoría.

### 2.1 Estructura de Código

**`orchestrator_service/core/agent/tool_registry.py`**:

```python
from typing import List, Dict, Callable
from langchain.tools import BaseTool

class ToolRegistry:
    _providers = {}

    @classmethod
    def register_provider(cls, niche_type: str, provider_func: Callable[[int], List[BaseTool]]):
        """Registra una función que devuelve tools para un nicho dado."""
        cls._providers[niche_type] = provider_func

    @classmethod
    def get_tools(cls, niche_type: str, tenant_id: int) -> List[BaseTool]:
        """Obtiene las tools instanciadas para un nicho y tenant específicos."""
        provider = cls._providers.get(niche_type)
        if not provider:
            # Fallback o error
            return []
        return provider(tenant_id)
```

### 2.2 Implementación en Módulos

**`orchestrator_service/modules/dental/tools_provider.py`**:

```python
from .tools import check_availability, book_appointment
from core.agent.tool_registry import ToolRegistry

def dental_tools_provider(tenant_id: int):
    # Aquí se podrían configurar tools con parámetros del tenant si fuera necesario
    return [check_availability, book_appointment]

# Al importar este módulo, se registra
ToolRegistry.register_provider("dental", dental_tools_provider)
```

**`orchestrator_service/modules/crm_sales/tools_provider.py`**:

```python
from .tools import list_templates, send_template
from core.agent.tool_registry import ToolRegistry

def crm_tools_provider(tenant_id: int):
    return [list_templates, send_template]

ToolRegistry.register_provider("crm_sales", crm_tools_provider)
```

## 3. Integración en `main.py`

El entrypoint debe cargar los proveedores (importar los módulos) y luego solicitar las tools al registro.

```python
# main.py startup
import modules.dental.tools_provider
import modules.crm_sales.tools_provider

# ... en el request loop del agente ...
async def run_agent(tenant_id, message):
    niche_type = await get_tenant_niche(tenant_id) # 'dental' o 'crm_sales'
    
    tools = ToolRegistry.get_tools(niche_type, tenant_id)
    
    agent_executor = AgentExecutor(tools=tools, ...)
    # ...
```

## 4. Configuración vía Base de Datos
La tabla `tenants.niche_config` (ver Documento 03) puede contener una lista blanca de tools para permitir una granularidad mayor:

```json
// niche_config para un tenant dental específico
{
  "allowed_tools": ["check_availability"] // Deshabilita book_appointment para este cliente
}
```

El `dental_tools_provider` leería esta config y filtraría la lista retornada.
