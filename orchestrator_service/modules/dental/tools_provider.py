from typing import List
from langchain.tools import BaseTool
from .tools import check_availability, book_appointment
from core.tools import tool_registry

def dental_tools_provider(tenant_id: int) -> List[BaseTool]:
    """
    Returns the list of tools available for the Dental niche.
    In the future, we can filter this list based on tenant_id config.
    """
    # Simply return the imports for now
    return [check_availability, book_appointment]

# Auto-registry when module is imported
tool_registry.register_provider("dental", dental_tools_provider)
