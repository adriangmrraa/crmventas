#!/usr/bin/env python3
"""
Google OAuth Migration Script for CRM Ventas.
Adds Google OAuth columns to users table and creates necessary indexes.
"""

import os
import sys
import logging
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db import get_db_connection

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def run_migration():
    """
    Run Google OAuth database migration.
    """
    logger.info("🚀 Starting Google OAuth migration...")
    
    try:
        async with get_db_connection() as conn:
            # Check if columns already exist
            columns = await conn.fetch("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users'
            """)
            
            existing_columns = {col["column_name"] for col in columns}
            logger.info(f"Existing columns in users table: {existing_columns}")
            
            # Add google_id column if it doesn't exist
            if "google_id" not in existing_columns:
                logger.info("Adding google_id column to users table...")
                await conn.execute("""
                    ALTER TABLE users 
                    ADD COLUMN google_id VARCHAR(255)
                """)
                logger.info("✅ Added google_id column")
            else:
                logger.info("✅ google_id column already exists")
            
            # Add google_email column if it doesn't exist
            if "google_email" not in existing_columns:
                logger.info("Adding google_email column to users table...")
                await conn.execute("""
                    ALTER TABLE users 
                    ADD COLUMN google_email VARCHAR(255)
                """)
                logger.info("✅ Added google_email column")
            else:
                logger.info("✅ google_email column already exists")
            
            # Add google_profile_picture column if it doesn't exist
            if "google_profile_picture" not in existing_columns:
                logger.info("Adding google_profile_picture column to users table...")
                await conn.execute("""
                    ALTER TABLE users 
                    ADD COLUMN google_profile_picture TEXT
                """)
                logger.info("✅ Added google_profile_picture column")
            else:
                logger.info("✅ google_profile_picture column already exists")
            
            # Create index on google_id for faster lookups
            logger.info("Creating index on google_id...")
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_google_id 
                ON users(google_id)
            """)
            logger.info("✅ Created index on google_id")
            
            # Create index on google_email for faster lookups
            logger.info("Creating index on google_email...")
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_google_email 
                ON users(google_email)
            """)
            logger.info("✅ Created index on google_email")
            
            # Add unique constraint on google_id (optional, can be commented out)
            # logger.info("Adding unique constraint on google_id...")
            # await conn.execute("""
            #     ALTER TABLE users 
            #     ADD CONSTRAINT unique_google_id UNIQUE (google_id)
            # """)
            # logger.info("✅ Added unique constraint on google_id")
            
            # Verify the migration
            logger.info("Verifying migration...")
            updated_columns = await conn.fetch("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'users'
                AND column_name IN ('google_id', 'google_email', 'google_profile_picture')
                ORDER BY column_name
            """)
            
            logger.info("Migration verification results:")
            for col in updated_columns:
                logger.info(f"  - {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']})")
            
            # Check indexes
            indexes = await conn.fetch("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'users'
                AND indexname LIKE '%google%'
            """)
            
            logger.info("Google-related indexes:")
            for idx in indexes:
                logger.info(f"  - {idx['indexname']}")
            
            logger.info("🎉 Google OAuth migration completed successfully!")
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        sys.exit(1)

async def rollback_migration():
    """
    Rollback Google OAuth migration (for testing/development).
    """
    logger.info("🔄 Rolling back Google OAuth migration...")
    
    try:
        async with get_db_connection() as conn:
            # Drop indexes first
            logger.info("Dropping google indexes...")
            await conn.execute("DROP INDEX IF EXISTS idx_users_google_id")
            await conn.execute("DROP INDEX IF EXISTS idx_users_google_email")
            logger.info("✅ Dropped indexes")
            
            # Drop columns
            logger.info("Dropping google columns...")
            await conn.execute("ALTER TABLE users DROP COLUMN IF EXISTS google_id")
            await conn.execute("ALTER TABLE users DROP COLUMN IF EXISTS google_email")
            await conn.execute("ALTER TABLE users DROP COLUMN IF EXISTS google_profile_picture")
            logger.info("✅ Dropped columns")
            
            logger.info("✅ Rollback completed successfully!")
            
    except Exception as e:
        logger.error(f"❌ Rollback failed: {e}", exc_info=True)
        sys.exit(1)

async def check_migration_status():
    """
    Check current migration status.
    """
    logger.info("🔍 Checking Google OAuth migration status...")
    
    try:
        async with get_db_connection() as conn:
            # Check columns
            columns = await conn.fetch("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'users'
                AND column_name IN ('google_id', 'google_email', 'google_profile_picture')
                ORDER BY column_name
            """)
            
            logger.info("Google OAuth columns:")
            if columns:
                for col in columns:
                    logger.info(f"  ✅ {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']})")
            else:
                logger.info("  ❌ No Google OAuth columns found")
            
            # Check indexes
            indexes = await conn.fetch("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'users'
                AND indexname LIKE '%google%'
            """)
            
            logger.info("Google-related indexes:")
            if indexes:
                for idx in indexes:
                    logger.info(f"  ✅ {idx['indexname']}")
            else:
                logger.info("  ❌ No Google-related indexes found")
            
            # Count users with Google IDs
            google_users = await conn.fetchrow("""
                SELECT COUNT(*) as count
                FROM users
                WHERE google_id IS NOT NULL
            """)
            
            logger.info(f"Users with Google IDs: {google_users['count']}")
            
    except Exception as e:
        logger.error(f"❌ Error checking migration status: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Google OAuth Migration Script")
    parser.add_argument("action", choices=["run", "rollback", "status"], 
                       help="Action to perform: run, rollback, or status")
    
    args = parser.parse_args()
    
    if args.action == "run":
        asyncio.run(run_migration())
    elif args.action == "rollback":
        asyncio.run(rollback_migration())
    elif args.action == "status":
        asyncio.run(check_migration_status())
    else:
        print(f"Unknown action: {args.action}")
        sys.exit(1)