
import asyncio
import os
import asyncpg
import json

POSTGRES_DSN = os.getenv("POSTGRES_DSN")

async def diagnose_sellers():
    if not POSTGRES_DSN:
        print("❌ POSTGRES_DSN not set")
        return

    dsn = POSTGRES_DSN.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(dsn)
    
    try:
        print("Checking users with seller roles...")
        users = await conn.fetch("""
            SELECT id, first_name, last_name, role, status, tenant_id 
            FROM users 
            WHERE role IN ('setter', 'closer', 'professional', 'ceo')
        """)
        
        if not users:
            print("❌ No users found with seller roles.")
        else:
            print(f"Found {len(users)} users with seller roles:")
            for u in users:
                print(f" - {u['first_name']} {u['last_name']} ({u['role']}) | Status: {u['status']} | ID: {u['id']} | Tenant: {u['tenant_id']}")
        
        print("\nChecking sellers table...")
        # Check if table exists first
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'sellers'
            )
        """)
        
        if not table_exists:
            print("❌ sellers table does NOT exist in information_schema.")
        else:
            sellers = await conn.fetch("SELECT * FROM sellers")
            if not sellers:
                print("❌ sellers table is EMPTY.")
            else:
                print(f"Found {len(sellers)} entries in sellers table:")
                for s in sellers:
                    print(f" - ID: {s['id']} | UserID: {s['user_id']} | Tenant: {s['tenant_id']}")
                
        print("\nChecking available sellers query from service (testing Tenant 1)...")
        tenant_id = 1
        query = """
            SELECT 
                u.id,
                u.first_name,
                u.last_name,
                u.role,
                u.email
            FROM users u
            WHERE u.tenant_id = $1 
            AND u.status = 'active'
            AND u.role IN ('setter', 'closer', 'professional', 'ceo')
            AND EXISTS (SELECT 1 FROM sellers s WHERE s.user_id = u.id)
        """
        available = await conn.fetch(query, tenant_id)
        print(f"Available sellers for Tenant {tenant_id}: {len(available)}")
        for a in available:
            print(f" - {a['first_name']} {a['last_name']} ({a['role']})")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(diagnose_sellers())
