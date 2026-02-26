import asyncio
import os
import sys
from dotenv import load_dotenv

# Add current directory to path for imports
sys.path.append(os.getcwd())

from db import db

async def run():
    await db.connect()
    try:
        rows = await db.fetch("SELECT id, tenant_id, phone_number, first_name, last_name, lead_source FROM leads WHERE tenant_id = 1")
        print("IDS | TENANT | PHONE | FIRST | LAST | SOURCE")
        for r in rows:
            print(f"{r['id']} | {r['tenant_id']} | {r['phone_number']} | '{r['first_name']}' | '{r['last_name']}' | {r['lead_source']}")
            
        print("\nChecking chat_messages numbers for tenant 1:")
        msg_nums = await db.fetch("SELECT DISTINCT from_number FROM chat_messages WHERE tenant_id = 1")
        for m in msg_nums:
            print(f"Message number: '{m['from_number']}'")
            
    finally:
        await db.disconnect()

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(run())
