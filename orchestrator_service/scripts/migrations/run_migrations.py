
import asyncio
import os
import sys

# Add the current directory to sys.path to import db
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import db

async def run_migration():
    try:
        print("Running evolution pipeline...")
        await db.connect()
        print("✅ Evolution pipeline completed.")
        
        # Verify backfill
        print("Verifying sellers backfill...")
        sellers = await db.pool.fetch("""
            SELECT s.email, s.role, u.status 
            FROM sellers s
            JOIN users u ON s.user_id = u.id
            WHERE u.status = 'active'
        """)
        print(f"Total active sellers in table: {len(sellers)}")
        for s in sellers:
            print(f" - {s['email']} ({s['role']})")

    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(run_migration())
