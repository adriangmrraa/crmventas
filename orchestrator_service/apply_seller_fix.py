
import asyncio
import os
import asyncpg

POSTGRES_DSN = os.getenv("POSTGRES_DSN")

async def apply_fix():
    if not POSTGRES_DSN:
        print("❌ POSTGRES_DSN not set")
        return

    dsn = POSTGRES_DSN.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(dsn)
    
    try:
        print("Applying backfill to sellers table...")
        # Get active users with eligible roles
        users = await conn.fetch("""
            SELECT id, tenant_id, first_name, last_name, email, role
            FROM users 
            WHERE status = 'active' 
            AND role IN ('setter', 'closer', 'professional', 'ceo')
        """)
        
        print(f"Found {len(users)} eligible active users.")
        
        for u in users:
            print(f" - Processing {u['email']} ({u['role']})...")
            await conn.execute("""
                INSERT INTO sellers (user_id, tenant_id, first_name, last_name, email, is_active, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, TRUE, NOW(), NOW())
                ON CONFLICT (user_id) DO UPDATE 
                SET is_active = TRUE, 
                    updated_at = NOW(),
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    email = EXCLUDED.email;
            """, u['id'], u['tenant_id'], u['first_name'], u['last_name'], u['email'])

        print("✅ Backfill completed.")

    except Exception as e:
        print(f"Error applying fix: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(apply_fix())
