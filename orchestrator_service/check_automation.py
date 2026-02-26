import asyncio
import os
import json
from dotenv import load_dotenv

# Load env from .env if it exists in the parent dir
load_dotenv(os.path.join(os.getcwd(), '.env'))

from db import db

async def check_automation():
    print("--- 🤖 Automation Diagnostics ---")
    await db.connect()
    
    # 1. Check Active Rules
    rules = await db.pool.fetch("SELECT id, name, is_active, trigger_type FROM automation_rules WHERE is_active = TRUE")
    print(f"\nActive Rules ({len(rules)}):")
    for r in rules:
        print(f" - [{r['id']}] {r['name']} ({r['trigger_type']})")
        
    # 2. Check Recent Logs
    # We want to see logs from the last hour
    logs = await db.pool.fetch("""
        SELECT l.id, l.trigger_type, l.status, l.created_at, p.phone_number, p.first_name
        FROM automation_logs l
        JOIN leads p ON l.patient_id = p.id
        WHERE l.created_at > NOW() - INTERVAL '1 hour'
        ORDER BY l.created_at DESC
        LIMIT 20
    """)
    print(f"\nRecent Automation Logs ({len(logs)}):")
    for l in logs:
        print(f" - {l['created_at']} | {l['trigger_type']} | {l['status']} | To: {l['phone_number']} ({l['first_name']})")

    # 3. Check Lead Status for the specific phone if we can infer it
    # The user's phone from screenshot is +5493704868421 -> digits: 5493704868421
    target_phone = '5493704868421'
    leads = await db.pool.fetch("SELECT id, first_name, status, lead_source, created_at FROM leads WHERE phone_number LIKE '%' || $1", target_phone)
    print(f"\nTarget Lead Info ({target_phone}):")
    for l in leads:
        print(f" - [{l['id']}] {l['first_name']} | Status: {l['status']} | Source: {l['lead_source']} | Created: {l['created_at']}")
        
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(check_automation())
