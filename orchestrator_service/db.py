"""
Database Module - Main Entry Point
=================================
This file provides backward compatibility with the old db.py interface.
All functionality is now delegated to the modular db/ package.

For new code, prefer:
    from db import db
    from db.queries import leads, users, tenants, chat
    from db.pool import pool_manager
"""

# Re-export everything from the new modular structure for backward compatibility
from .db import db, Database
from .pool import pool_manager, DatabasePool
from .migrations import create_migration_runner

# Also expose the query functions at module level for backward compatibility
from . import db as _db_module

# These are the main functions used throughout the codebase
fetch = _db_module.fetch
fetchrow = _db_module.fetchrow
execute = _db_module.execute
execute_many = _db_module.execute_many

# Query helpers
tenants_get_all = _db_module.tenants_get_all
tenants_get_by_id = _db_module.tenants_get_by_id
users_get_by_tenant = _db_module.users_get_by_tenant
users_get_by_email = _db_module.users_get_by_email
users_create = _db_module.users_create
leads_get_by_tenant = _db_module.leads_get_by_tenant
leads_create = _db_module.leads_create
leads_update = _db_module.leads_update
chat_get_sessions = _db_module.chat_get_sessions
chat_get_messages = _db_module.chat_get_messages

__all__ = [
    "db",
    "Database",
    "pool_manager",
    "DatabasePool",
    "create_migration_runner",
    "fetch",
    "fetchrow",
    "execute",
    "execute_many",
    "tenants_get_all",
    "tenants_get_by_id",
    "users_get_by_tenant",
    "users_get_by_email",
    "users_create",
    "leads_get_by_tenant",
    "leads_create",
    "leads_update",
    "chat_get_sessions",
    "chat_get_messages",
]
