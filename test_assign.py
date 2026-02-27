import asyncio
import os
import sys

# Modify path to allow importing orchestrator_service modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'orchestrator_service'))

from db import Database
from uuid import UUID

async def test_assign():
    db = Database()
    await db.connect()
    
    try:
        from services.seller_assignment_service import SellerAssignmentService
        service = SellerAssignmentService()
        
        # Get one recent phone with a chat message
        msg = await db.pool.fetchrow("SELECT from_number, tenant_id FROM chat_messages ORDER BY created_at DESC LIMIT 1")
        if not msg:
            print("No chat messages found")
            return
            
        # Get one active seller
        seller = await db.pool.fetchrow("SELECT id FROM users WHERE role IN ('setter', 'closer') AND status = 'active' LIMIT 1")
        if not seller:
            print("No active sellers found")
            return
            
        print(f"Assigning {msg['from_number']} to seller {seller['id']}")
        res = await service.assign_conversation_to_seller(
            phone=msg['from_number'],
            seller_id=seller['id'],
            assigned_by=seller['id'], # Just use same UUID for test
            tenant_id=msg['tenant_id'],
            source="manual"
        )
        print("Result:", res)
        
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), 'orchestrator_service', '.env'))
    asyncio.run(test_assign())
