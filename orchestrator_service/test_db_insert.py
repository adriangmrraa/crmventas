import asyncio
from dotenv import load_dotenv
load_dotenv()

from db import db
from core.credentials import save_tenant_credential

async def main():
    await db.connect()
    
    # List all tenants to find the "Codexy" tenant
    tenants = await db.fetch("SELECT id, clinic_name FROM tenants")
    print("Tenants:", [dict(t) for t in tenants])
    
    # Fetch credentials
    print("\nExisting credentials for integration:")
    creds = await db.fetch("SELECT id, tenant_id, name, category, length(value) as len FROM credentials WHERE category = 'integration'")
    print([dict(c) for c in creds])
    
    # Try inserting for a typical tenant (like 1 or 2)
    print("\nTesting save_tenant_credential for tenant 1...")
    success = await save_tenant_credential(1, "YCLOUD_API_KEY", "test_key_script", "integration")
    print("Saved?", success)
    
    await db.disconnect()

asyncio.run(main())
