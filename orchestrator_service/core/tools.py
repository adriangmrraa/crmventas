from typing import List, Dict, Any, Callable, Optional
from langchain.tools import BaseTool
import logging

logger = logging.getLogger("tool_registry")

class ToolRegistry:
    def __init__(self):
        # Maps niche_type -> provider_function(tenant_id) -> List[BaseTool]
        self._providers: Dict[str, Callable[[int], List[BaseTool]]] = {}
        # Keep track of globally registered tools (legacy support or core tools)
        self._global_tools: List[BaseTool] = []

    def register_provider(self, niche_type: str, provider_func: Callable[[int], List[BaseTool]]):
        """Registers a function that returns tools for a given niche."""
        self._providers[niche_type] = provider_func
        logger.info(f"Registered tool provider for niche: {niche_type}")

    def register_global_tool(self, tool: BaseTool):
        """Registers a tool available to ALL agents/niches."""
        self._global_tools.append(tool)

    def get_tools(self, niche_type: str, tenant_id: int) -> List[BaseTool]:
        """Returns the list of instantiated tools for a specific niche and tenant."""
        tools = list(self._global_tools)
        
        provider = self._providers.get(niche_type)
        if provider:
            try:
                niche_tools = provider(tenant_id)
                tools.extend(niche_tools)
            except Exception as e:
                logger.error(f"Error loading tools for niche {niche_type} (tenant {tenant_id}): {e}")
        else:
            logger.warning(f"No tool provider found for niche: {niche_type}")
            
        return tools

    def clear(self):
        self._providers = {}
        self._global_tools = []

# Global instance
tool_registry = ToolRegistry()
