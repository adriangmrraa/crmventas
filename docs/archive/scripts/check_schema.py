import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), 'orchestrator_service', '.env'))
import asyncio
import sys

# Modify path to allow importing orchestrator_service modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'orchestrator_service'))

from db import Database

async def main():
    db = Database()
    await db.connect()
    
    try:
        # Check chat_messages columns
        cols = await db.pool.fetch("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'chat_messages'
        """)
        print("=== CHAT_MESSAGES COLUMNS ===")
        for c in cols:
            print(f"- {c['column_name']} ({c['data_type']})")
            
        print("\n=== EXECUTING PARCHE 11 MANUALLY TO SEE ERRORS ===")
        # Execute line by line or without exception handler to see the real error
        await db.pool.execute("""
            -- 1. Add seller assignment columns to chat_messages
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='chat_messages' AND column_name='assigned_seller_id') THEN
                    ALTER TABLE chat_messages 
                    ADD COLUMN assigned_seller_id UUID REFERENCES users(id),
                    ADD COLUMN assigned_at TIMESTAMPTZ,
                    ADD COLUMN assigned_by UUID REFERENCES users(id),
                    ADD COLUMN assignment_source TEXT DEFAULT 'manual';
                END IF;
            END $$;
        """)
        print("Successfully executed ALTER TABLE chat_messages")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), 'orchestrator_service', '.env'))
    asyncio.run(main())
