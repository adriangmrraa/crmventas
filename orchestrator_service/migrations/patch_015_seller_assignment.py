"""
Migration for seller assignment system - CRM Ventas
Patch 015: Add seller assignment tracking to chat_messages and leads
"""
import asyncio
import os
import sys
import logging
from datetime import datetime

# Add parent directory to path to import db module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

async def run_migration():
    print("🚀 Running migration for seller assignment system...")
    
    try:
        # Import db here after path is set
        from db import db
        
        # Connect to database
        await db.connect()
        
        # 1. Add columns to chat_messages for seller assignment
        print("📝 Adding seller assignment columns to chat_messages...")
        await db.execute("""
            ALTER TABLE chat_messages 
            ADD COLUMN IF NOT EXISTS assigned_seller_id UUID REFERENCES users(id),
            ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS assigned_by UUID REFERENCES users(id),
            ADD COLUMN IF NOT EXISTS assignment_source TEXT DEFAULT 'manual'
        """)
        print("✅ Added columns to chat_messages")
        
        # 2. Create seller_metrics table for performance tracking
        print("📊 Creating seller_metrics table...")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS seller_metrics (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                seller_id UUID NOT NULL REFERENCES users(id),
                tenant_id INTEGER NOT NULL REFERENCES tenants(id),
                
                -- Conversaciones
                total_conversations INTEGER DEFAULT 0,
                active_conversations INTEGER DEFAULT 0,
                conversations_assigned_today INTEGER DEFAULT 0,
                
                -- Mensajes
                total_messages_sent INTEGER DEFAULT 0,
                total_messages_received INTEGER DEFAULT 0,
                avg_response_time_seconds INTEGER,
                
                -- Leads
                leads_assigned INTEGER DEFAULT 0,
                leads_converted INTEGER DEFAULT 0,
                conversion_rate DECIMAL(5,2),
                
                -- Prospección
                prospects_generated INTEGER DEFAULT 0,
                prospects_converted INTEGER DEFAULT 0,
                
                -- Tiempo
                total_chat_minutes INTEGER DEFAULT 0,
                avg_session_duration_minutes INTEGER,
                
                -- Metadata
                last_activity_at TIMESTAMPTZ,
                metrics_calculated_at TIMESTAMPTZ DEFAULT NOW(),
                metrics_period_start TIMESTAMPTZ,
                metrics_period_end TIMESTAMPTZ,
                
                -- Constraints
                UNIQUE(seller_id, tenant_id, metrics_period_start),
                CHECK (conversion_rate >= 0 AND conversion_rate <= 100)
            )
        """)
        print("✅ Created seller_metrics table")
        
        # 3. Create assignment_rules table for auto-assignment configuration
        print("⚙️ Creating assignment_rules table...")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS assignment_rules (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id INTEGER NOT NULL REFERENCES tenants(id),
                
                -- Regla
                rule_name TEXT NOT NULL,
                rule_type TEXT NOT NULL CHECK (rule_type IN ('round_robin', 'performance', 'specialty', 'load_balance')),
                is_active BOOLEAN DEFAULT TRUE,
                priority INTEGER DEFAULT 0,
                
                -- Configuración
                config JSONB NOT NULL DEFAULT '{}',
                
                -- Filtros
                apply_to_lead_source TEXT[],
                apply_to_lead_status TEXT[],
                apply_to_seller_roles TEXT[],
                
                -- Límites
                max_conversations_per_seller INTEGER,
                min_response_time_seconds INTEGER,
                
                -- Metadata
                description TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                
                UNIQUE(tenant_id, rule_name)
            )
        """)
        print("✅ Created assignment_rules table")
        
        # 4. Add assignment tracking to leads table
        print("📋 Adding assignment tracking to leads table...")
        await db.execute("""
            ALTER TABLE leads 
            ADD COLUMN IF NOT EXISTS initial_assignment_source TEXT,
            ADD COLUMN IF NOT EXISTS assignment_history JSONB DEFAULT '[]'
        """)
        print("✅ Added assignment tracking to leads")
        
        # 5. Create indexes for performance
        print("⚡ Creating indexes for performance...")
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_messages_assigned_seller 
            ON chat_messages(assigned_seller_id);
            
            CREATE INDEX IF NOT EXISTS idx_chat_messages_assignment_source 
            ON chat_messages(assignment_source);
            
            CREATE INDEX IF NOT EXISTS idx_seller_metrics_tenant 
            ON seller_metrics(tenant_id);
            
            CREATE INDEX IF NOT EXISTS idx_seller_metrics_seller 
            ON seller_metrics(seller_id);
            
            CREATE INDEX IF NOT EXISTS idx_seller_metrics_period 
            ON seller_metrics(metrics_period_start DESC);
        """)
        print("✅ Created indexes")
        
        # 6. Insert default round-robin rule for each tenant
        print("🎯 Inserting default assignment rules...")
        tenants = await db.fetch("SELECT id FROM tenants")
        for tenant in tenants:
            await db.execute("""
                INSERT INTO assignment_rules 
                (tenant_id, rule_name, rule_type, config, description, priority)
                VALUES ($1, 'Round Robin Default', 'round_robin', 
                        '{"enabled": true, "exclude_inactive": true}', 
                        'Default round-robin assignment for new conversations',
                        0)
                ON CONFLICT (tenant_id, rule_name) DO NOTHING
            """, tenant['id'])
        
        print(f"✅ Inserted default rules for {len(tenants)} tenants")
        
        print("\n🎉 Migration completed successfully!")
        print("📊 Summary:")
        print("  - Added seller assignment to chat_messages")
        print("  - Created seller_metrics table")
        print("  - Created assignment_rules table")
        print("  - Added assignment tracking to leads")
        print("  - Created performance indexes")
        print("  - Inserted default assignment rules")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(run_migration())