import asyncio
import os
import sys

# Setup paths to import orchestrator modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'orchestrator_service'))

from db import db
from services.marketing.marketing_service import MarketingService

async def debug_stats():
    # Connect to DB
    await db.connect()
    
    # Get stats for tenant 1
    tenant_id = 1
    print("Testing get_campaign_stats for tenant 1...")
    
    try:
        stats = await MarketingService.get_campaign_stats(tenant_id, "last_30d")
        print("\nCampaign Stats Result:")
        print(f"Number of Campaigns: {len(stats.get('campaigns', []))}")
        for c in stats.get('campaigns', []):
            print(f"  - {c['ad_name']} ({c['status']}): Spend={c['spend']}")
            
        print(f"\nNumber of Creatives: {len(stats.get('creatives', []))}")
        for c in stats.get('creatives', []):
            print(f"  - {c['ad_name']} ({c['status']}): Spend={c['spend']}")
            
        print(f"\nAccount Total Spend: {stats.get('account_total_spend')}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await db.disconnect()

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv("orchestrator_service/.env")
    asyncio.run(debug_stats())
