#!/usr/bin/env python3
"""
Script to run Meta Ads database migrations.
Usage: python run_meta_ads_migrations.py
"""

import os
import sys
import asyncio
import asyncpg
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

async def run_migration():
    """Run the Meta Ads migration script."""
    
    # Get database connection parameters from environment
    postgres_dsn = os.getenv("POSTGRES_DSN", "")
    if not postgres_dsn:
        print("❌ POSTGRES_DSN environment variable not set")
        print("Please set: export POSTGRES_DSN='postgresql://user:password@host:port/database'")
        return False
    
    # Parse DSN to get connection parameters
    try:
        # Simple parsing - in production use urllib.parse
        if postgres_dsn.startswith("postgresql://"):
            # Remove protocol
            dsn_parts = postgres_dsn.replace("postgresql://", "").split("@")
            if len(dsn_parts) != 2:
                raise ValueError("Invalid DSN format")
            
            creds_host = dsn_parts[0].split(":")
            if len(creds_host) != 2:
                raise ValueError("Invalid credentials format")
            
            user, password = creds_host[0], creds_host[1]
            host_db = dsn_parts[1].split("/")
            if len(host_db) != 2:
                raise ValueError("Invalid host/database format")
            
            host_port = host_db[0].split(":")
            host = host_port[0]
            port = int(host_port[1]) if len(host_port) > 1 else 5432
            database = host_db[1]
            
            print(f"🔗 Connecting to: {host}:{port}/{database}")
        else:
            # Assume it's already a valid DSN for asyncpg
            print("🔗 Using provided DSN directly")
    except Exception as e:
        print(f"❌ Error parsing DSN: {e}")
        print(f"DSN: {postgres_dsn}")
        return False
    
    migration_file = Path(__file__).parent / "migrations" / "patch_009_meta_ads_tables.sql"
    
    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    try:
        # Read migration SQL
        with open(migration_file, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        print(f"📄 Migration file: {migration_file.name}")
        print(f"📏 SQL size: {len(migration_sql)} characters")
        
        # Connect to database
        print("🔄 Connecting to database...")
        conn = await asyncpg.connect(postgres_dsn)
        
        # Start transaction
        print("🚀 Starting migration transaction...")
        async with conn.transaction():
            # Execute migration
            print("⚡ Executing migration SQL...")
            await conn.execute(migration_sql)
        
        print("✅ Migration completed successfully!")
        
        # Verify tables were created
        print("🔍 Verifying created tables...")
        
        tables_to_check = [
            'meta_ads_campaigns',
            'meta_ads_insights', 
            'meta_templates',
            'automation_rules',
            'automation_logs',
            'opportunities',
            'sales_transactions'
        ]
        
        for table in tables_to_check:
            try:
                result = await conn.fetchrow(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = $1
                    )
                """, table)
                
                if result and result['exists']:
                    print(f"   ✅ {table} table exists")
                else:
                    print(f"   ❌ {table} table NOT found")
            except Exception as e:
                print(f"   ⚠️ Error checking {table}: {e}")
        
        # Check leads table columns
        print("🔍 Checking leads table updates...")
        new_columns = ['lead_source', 'meta_campaign_id', 'meta_ad_id', 'meta_ad_headline', 'meta_ad_body', 'external_ids']
        
        for column in new_columns:
            try:
                result = await conn.fetchrow(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = 'leads' 
                        AND column_name = $1
                    )
                """, column)
                
                if result and result['exists']:
                    print(f"   ✅ leads.{column} column exists")
                else:
                    print(f"   ❌ leads.{column} column NOT found")
            except Exception as e:
                print(f"   ⚠️ Error checking leads.{column}: {e}")
        
        # Test ROI function
        print("🧪 Testing ROI calculation function...")
        try:
            # Just check if function exists
            result = await conn.fetchrow("""
                SELECT EXISTS (
                    SELECT FROM pg_proc 
                    WHERE proname = 'calculate_campaign_roi'
                )
            """)
            
            if result and result['exists']:
                print("   ✅ calculate_campaign_roi function exists")
            else:
                print("   ❌ calculate_campaign_roi function NOT found")
        except Exception as e:
            print(f"   ⚠️ Error checking ROI function: {e}")
        
        await conn.close()
        print("\n🎉 Migration verification complete!")
        return True
        
    except asyncpg.PostgresError as e:
        print(f"❌ Database error during migration: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def rollback_migration():
    """Rollback the Meta Ads migration (emergency only)."""
    
    postgres_dsn = os.getenv("POSTGRES_DSN", "")
    if not postgres_dsn:
        print("❌ POSTGRES_DSN environment variable not set")
        return False
    
    print("⚠️ WARNING: This will DROP all Meta Ads tables!")
    print("This operation cannot be undone!")
    confirmation = input("Type 'YES' to confirm rollback: ")
    
    if confirmation != "YES":
        print("❌ Rollback cancelled")
        return False
    
    rollback_sql = """
    BEGIN;
    
    -- Drop tables in reverse order (due to foreign keys)
    DROP TABLE IF EXISTS sales_transactions CASCADE;
    DROP TABLE IF EXISTS opportunities CASCADE;
    DROP TABLE IF EXISTS automation_logs CASCADE;
    DROP TABLE IF EXISTS automation_rules CASCADE;
    DROP TABLE IF EXISTS meta_templates CASCADE;
    DROP TABLE IF EXISTS meta_ads_insights CASCADE;
    DROP TABLE IF EXISTS meta_ads_campaigns CASCADE;
    
    -- Remove function
    DROP FUNCTION IF EXISTS calculate_campaign_roi;
    
    -- Remove columns from leads table
    ALTER TABLE leads DROP COLUMN IF EXISTS lead_source;
    ALTER TABLE leads DROP COLUMN IF EXISTS meta_campaign_id;
    ALTER TABLE leads DROP COLUMN IF EXISTS meta_ad_id;
    ALTER TABLE leads DROP COLUMN IF EXISTS meta_ad_headline;
    ALTER TABLE leads DROP COLUMN IF EXISTS meta_ad_body;
    ALTER TABLE leads DROP COLUMN IF EXISTS external_ids;
    
    -- Drop indexes
    DROP INDEX IF EXISTS idx_leads_lead_source;
    DROP INDEX IF EXISTS idx_leads_meta_campaign;
    DROP INDEX IF EXISTS idx_leads_meta_ad;
    
    COMMIT;
    """
    
    try:
        conn = await asyncpg.connect(postgres_dsn)
        
        print("🔄 Starting rollback transaction...")
        async with conn.transaction():
            print("⚡ Executing rollback SQL...")
            await conn.execute(rollback_sql)
        
        await conn.close()
        print("✅ Rollback completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during rollback: {e}")
        return False

async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Meta Ads Database Migration Tool")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    parser.add_argument("--verify", action="store_true", help="Only verify, don't migrate")
    
    args = parser.parse_args()
    
    if args.rollback:
        return await rollback_migration()
    elif args.verify:
        # Just verify current state
        postgres_dsn = os.getenv("POSTGRES_DSN", "")
        if not postgres_dsn:
            print("❌ POSTGRES_DSN environment variable not set")
            return False
        
        try:
            conn = await asyncpg.connect(postgres_dsn)
            print("🔍 Verifying current database state...")
            
            # Check tables
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE 'meta_%' 
                OR table_name IN ('automation_rules', 'automation_logs', 'opportunities', 'sales_transactions')
                ORDER BY table_name
            """)
            
            if tables:
                print("📊 Found Meta Ads tables:")
                for table in tables:
                    print(f"   • {table['table_name']}")
            else:
                print("📊 No Meta Ads tables found")
            
            await conn.close()
            return True
            
        except Exception as e:
            print(f"❌ Verification error: {e}")
            return False
    else:
        # Run migration
        return await run_migration()

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)