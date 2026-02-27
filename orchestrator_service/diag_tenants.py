import os
from dotenv import load_dotenv

# Load FIRST before any project imports
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(env_path)

import asyncio
from db import db

async def diag():
    print(f"DEBUG: POSTGRES_DSN in env: {bool(os.getenv('POSTGRES_DSN'))}")
    # Force db to see the DSN if it missed it
    import db as db_module
    db_module.POSTGRES_DSN = os.getenv("POSTGRES_DSN")
    
    await db.connect()
    print(f"DEBUG: db.pool after connect: {db.pool}")
    if not db.pool:
        print("❌ ERROR: Pool is still None.")
        return
        
    print("Checking 'tenants' table...")
    rows = await db.fetch("SELECT id, clinic_name, bot_phone_number FROM tenants")
    for r in rows:
        print(f"ID: {r['id']} | Name: {r['clinic_name']} | Phone: {r['bot_phone_number']}")
    
    print("\nChecking 'credentials' table for integration keys...")
    creds = await db.fetch("SELECT tenant_id, name, category FROM credentials WHERE category = 'integration'")
    for c in creds:
        print(f"Tenant: {c['tenant_id']} | Key: {c['name']} | Cat: {c['category']}")

if __name__ == "__main__":
    asyncio.run(diag())
