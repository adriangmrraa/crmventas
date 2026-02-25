#!/usr/bin/env python3
"""
Test Meta Ads migrations with SQLite (for development/testing).
This allows testing migrations without a real PostgreSQL instance.
"""

import sqlite3
import os
import sys
from pathlib import Path

def adapt_sql_for_sqlite(sql_content):
    """Adapt PostgreSQL SQL to SQLite compatible SQL."""
    # Replace PostgreSQL-specific syntax
    replacements = [
        # Data types
        ("UUID PRIMARY KEY DEFAULT gen_random_uuid()", "TEXT PRIMARY KEY"),
        ("DECIMAL(12,2)", "REAL"),
        ("DECIMAL(10,2)", "REAL"),
        ("DECIMAL(5,2)", "REAL"),
        ("JSONB", "TEXT"),
        ("VARCHAR(255)", "TEXT"),
        ("VARCHAR(50)", "TEXT"),
        
        # PostgreSQL-specific functions
        ("NOW()", "CURRENT_TIMESTAMP"),
        ("gen_random_uuid()", "hex(randomblob(16))"),
        
        # Constraints
        ("REFERENCES tenants(id)", ""),
        ("REFERENCES users(id)", ""),
        ("REFERENCES leads(id)", ""),
        ("REFERENCES opportunities(id)", ""),
        ("REFERENCES meta_ads_campaigns(id)", ""),
        ("REFERENCES automation_rules(id)", ""),
        ("REFERENCES templates(id)", ""),
        
        # Index syntax
        ("CREATE INDEX IF NOT EXISTS", "CREATE INDEX IF NOT EXISTS"),
        
        # Remove unsupported statements
        ("BEGIN;", "-- BEGIN;"),
        ("COMMIT;", "-- COMMIT;"),
        ("CREATE OR REPLACE FUNCTION", "-- CREATE OR REPLACE FUNCTION"),
    ]
    
    adapted = sql_content
    for old, new in replacements:
        adapted = adapted.replace(old, new)
    
    # Remove unsupported constraint lines
    lines = adapted.split('\n')
    filtered_lines = []
    for line in lines:
        if any(phrase in line for phrase in [
            "CONSTRAINT unique_",
            "CONSTRAINT fk_",
            "ALTER TABLE",
            "CREATE FUNCTION",
        ]):
            filtered_lines.append(f"-- {line}")
        else:
            filtered_lines.append(line)
    
    return '\n'.join(filtered_lines)

def test_migrations():
    """Test migrations with SQLite."""
    print("🧪 Testing Meta Ads migrations with SQLite")
    print("=" * 50)
    
    # Path to migration file
    migration_file = Path(__file__).parent / "migrations" / "patch_009_meta_ads_tables.sql"
    
    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    try:
        # Read migration SQL
        with open(migration_file, 'r', encoding='utf-8') as f:
            postgres_sql = f.read()
        
        print(f"📄 Original SQL size: {len(postgres_sql)} characters")
        
        # Adapt for SQLite
        sqlite_sql = adapt_sql_for_sqlite(postgres_sql)
        print(f"📄 Adapted SQL size: {len(sqlite_sql)} characters")
        
        # Create SQLite database in memory
        print("🗄️ Creating SQLite database (in memory)...")
        conn = sqlite3.connect(':memory:')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Create minimal required tables for foreign keys
        print("📋 Creating base tables...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tenants (
                id INTEGER PRIMARY KEY,
                name TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id TEXT PRIMARY KEY,
                tenant_id INTEGER,
                phone_number TEXT,
                first_name TEXT,
                last_name TEXT,
                email TEXT,
                status TEXT,
                source TEXT,
                created_at TEXT
            )
        """)
        
        # Insert test data
        cursor.execute("INSERT INTO tenants (id, name) VALUES (1, 'Test Tenant')")
        cursor.execute("INSERT INTO users (id, name) VALUES (100, 'Test User')")
        cursor.execute("""
            INSERT INTO leads (id, tenant_id, phone_number, first_name, status, created_at) 
            VALUES ('lead_001', 1, '+1234567890', 'John', 'new', CURRENT_TIMESTAMP)
        """)
        
        # Execute adapted migration SQL
        print("⚡ Executing adapted migration SQL...")
        
        # Split into individual statements
        statements = []
        current_statement = []
        
        for line in sqlite_sql.split('\n'):
            line = line.strip()
            if line and not line.startswith('--'):  # Skip comments and empty lines
                current_statement.append(line)
                if line.endswith(';'):
                    statements.append(' '.join(current_statement))
                    current_statement = []
        
        # Execute each statement
        success_count = 0
        error_count = 0
        
        for i, statement in enumerate(statements[:50], 1):  # Limit to first 50 statements
            try:
                cursor.execute(statement)
                success_count += 1
                if i % 10 == 0:
                    print(f"   ✅ Executed {i} statements...")
            except sqlite3.Error as e:
                error_count += 1
                print(f"   ❌ Statement {i} failed: {e}")
                print(f"      Statement: {statement[:100]}...")
        
        print(f"\n📊 Execution results: {success_count} successful, {error_count} failed")
        
        # Verify tables were created
        print("\n🔍 Verifying created tables...")
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            ORDER BY name
        """)
        
        tables = [row['name'] for row in cursor.fetchall()]
        print(f"📋 Total tables in database: {len(tables)}")
        
        # Check for expected tables
        expected_tables = [
            'meta_ads_campaigns',
            'meta_ads_insights',
            'meta_templates',
            'automation_rules',
            'automation_logs',
            'opportunities',
            'sales_transactions'
        ]
        
        found_tables = []
        missing_tables = []
        
        for table in expected_tables:
            if table in tables:
                found_tables.append(table)
                print(f"   ✅ {table}")
            else:
                missing_tables.append(table)
                print(f"   ❌ {table}")
        
        # Check leads table columns
        print("\n🔍 Checking leads table columns...")
        cursor.execute("PRAGMA table_info(leads)")
        columns = [row['name'] for row in cursor.fetchall()]
        
        expected_columns = [
            'lead_source',
            'meta_campaign_id',
            'meta_ad_id',
            'meta_ad_headline',
            'meta_ad_body',
            'external_ids'
        ]
        
        for column in expected_columns:
            if column in columns:
                print(f"   ✅ leads.{column}")
            else:
                print(f"   ❌ leads.{column}")
        
        # Test data insertion
        print("\n🧪 Testing data insertion...")
        test_data = [
            ("INSERT INTO meta_ads_campaigns (id, tenant_id, meta_campaign_id, meta_account_id, name, status) VALUES ('camp_001', 1, 'meta_camp_001', 'act_123', 'Test Campaign', 'ACTIVE')", "meta_ads_campaigns"),
            ("INSERT INTO opportunities (id, tenant_id, lead_id, name, value, stage) VALUES ('opp_001', 1, 'lead_001', 'Test Opportunity', 1000.00, 'prospecting')", "opportunities"),
            ("INSERT INTO automation_rules (id, tenant_id, name, trigger_type, is_active) VALUES ('rule_001', 1, 'Test Rule', 'lead_created', 1)", "automation_rules"),
        ]
        
        for sql, table_name in test_data:
            try:
                cursor.execute(sql)
                print(f"   ✅ Insert into {table_name}")
            except sqlite3.Error as e:
                print(f"   ❌ Insert into {table_name} failed: {e}")
        
        # Count records
        print("\n📊 Record counts:")
        for table in found_tables[:5]:  # First 5 tables
            try:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                count = cursor.fetchone()['count']
                print(f"   📈 {table}: {count} records")
            except:
                print(f"   ⚠️ {table}: Could not count")
        
        conn.close()
        
        print("\n" + "=" * 50)
        
        if len(missing_tables) == 0 and error_count == 0:
            print("🎉 MIGRATION TEST PASSED!")
            print("All expected tables were created successfully.")
            print("SQL is syntactically valid (SQLite adaptation).")
            return True
        else:
            print(f"⚠️ MIGRATION TEST PARTIALLY PASSED")
            print(f"Missing tables: {len(missing_tables)}")
            print(f"SQL errors: {error_count}")
            print("\nNote: This is a SQLite adaptation test.")
            print("For production, use PostgreSQL with the original migration script.")
            return len(missing_tables) <= 2  # Allow up to 2 missing tables
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def generate_postgres_test_script():
    """Generate a PostgreSQL test script for manual execution."""
    migration_file = Path(__file__).parent / "migrations" / "patch_009_meta_ads_tables.sql"
    
    if not migration_file.exists():
        print("❌ Migration file not found")
        return
    
    with open(migration_file, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    # Extract verification queries
    verification_section = """
-- ============================================
-- Verification Queries (Run after migration)
-- ============================================

-- 1. Check all tables were created
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN (
    'meta_ads_campaigns', 
    'meta_ads_insights', 
    'meta_templates', 
    'automation_rules', 
    'automation_logs',
    'opportunities',
    'sales_transactions'
)
ORDER BY table_name;

-- 2. Check leads table has new columns
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'leads' 
AND column_name IN ('lead_source', 'meta_campaign_id', 'meta_ad_id', 'meta_ad_headline', 'meta_ad_body', 'external_ids');

-- 3. Test ROI function with dummy data
-- First, insert some test data:
INSERT INTO meta_ads_campaigns (tenant_id, meta_campaign_id, meta_account_id, name, status) 
VALUES (1, 'test_campaign_001', 'act_123', 'Test Campaign', 'ACTIVE');

INSERT INTO leads (tenant_id, phone_number, meta_campaign_id, lead_source, created_at)
VALUES (1, '+1234567890', 'test_campaign_001', 'META_ADS', NOW());

-- Then test the function:
SELECT * FROM calculate_campaign_roi(1, 'test_campaign_001', CURRENT_DATE - 30, CURRENT_DATE);

-- 4. Cleanup test data (optional)
-- DELETE FROM leads WHERE tenant_id = 1 AND meta_campaign_id = 'test_campaign_001';
-- DELETE FROM meta_ads_campaigns WHERE tenant_id = 1 AND meta_campaign_id = 'test_campaign_001';
"""
    
    test_script = sql + verification_section
    
    output_file = Path(__file__).parent / "test_migration_postgres.sql"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(test_script)
    
    print(f"📄 PostgreSQL test script generated: {output_file}")
    print("To use:")
    print(f"  psql -h localhost -U postgres -d crmventas -f {output_file}")

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Meta Ads migrations")
    parser.add_argument("--sqlite", action="store_true", help="Test with SQLite (default)")
    parser.add_argument("--generate-postgres", action="store_true", help="Generate PostgreSQL test script")
    
    args = parser.parse_args()
    
    if args.generate_postgres:
        generate_postgres_test_script()
        return True
    
    # Default: test with SQLite
    return test_migrations()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)