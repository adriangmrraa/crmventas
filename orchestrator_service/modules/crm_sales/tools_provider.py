"""
CRM Sales Module - Tool Provider
Registers the CRM Sales niche tools with the global tool registry.
"""
from typing import List
from langchain.tools import BaseTool

from core.tools import tool_registry

# Import tools from the niche implementation (stubs until full implementation)
try:
    from niches.crm_sales.sales_tools import (
        lead_scoring,
        list_templates,
        book_sales_meeting,
        assign_lead_tags,
        get_lead_tags,
        qualify_lead,
        request_human_handoff,
        derive_to_setter,
    )
    _CRM_TOOLS = [
        lead_scoring,
        list_templates,
        book_sales_meeting,
        assign_lead_tags,
        get_lead_tags,
        qualify_lead,
        request_human_handoff,
        derive_to_setter,
    ]
except ImportError:
    _CRM_TOOLS = []


def crm_sales_tools_provider(tenant_id: int) -> List[BaseTool]:
    """
    Returns the list of tools available for the CRM Sales niche.
    """
    return list(_CRM_TOOLS)


# Auto-register when module is imported
tool_registry.register_provider("crm_sales", crm_sales_tools_provider)
