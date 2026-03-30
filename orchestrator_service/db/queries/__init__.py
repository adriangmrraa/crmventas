"""
Database Queries Module
========================
Exports query classes for each domain

Usage:
    from db.queries import leads, users, tenants, chat

    # Get leads
    all_leads = await leads.get_by_tenant(tenant_id=1)

    # Create lead
    new_lead = await leads.create(tenant_id=1, phone_number="+54911...")
"""

from .base import (
    BaseQuery,
    LeadsQueries,
    UsersQueries,
    TenantsQueries,
    ChatQueries,
    create_queries,
)

# These will be initialized when db.pool is available
# Use through the db module interface
leads = None
users = None
tenants = None
chat = None


def init_queries(pool):
    """Initialize query instances with a pool"""
    global leads, users, tenants, chat
    instances = create_queries(pool)
    leads = instances["leads"]
    users = instances["users"]
    tenants = instances["tenants"]
    chat = instances["chat"]
    return instances


__all__ = [
    "BaseQuery",
    "LeadsQueries",
    "UsersQueries",
    "TenantsQueries",
    "ChatQueries",
    "create_queries",
    "init_queries",
    "leads",
    "users",
    "tenants",
    "chat",
]
