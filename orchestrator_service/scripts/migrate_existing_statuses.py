import argparse
import asyncio
import asyncpg
import os
from typing import Dict, List

STATUS_MAPPING = {
    'new': 'new',
    'contacted': 'contacted',
    'qualified': 'qualified',
    'proposal_sent': 'proposal_sent',
    'negotiation': 'negotiation',
    'won': 'won',
    'converted': 'won',
    'lost': 'lost',
    'archived': 'archived',
    'pending': 'new',
    'in_progress': 'contacted',
    'completed': 'won',
    'cancelled': 'lost'
}

DEFAULT_STATUSES = [
    ('new', 'Nuevo', '#6B7280', 'circle', True, False, 10),
    ('contacted', 'Contactado', '#3B82F6', 'phone', False, False, 20),
    ('qualified', 'Calificado', '#10B981', 'check-circle', False, False, 30),
    ('proposal_sent', 'Propuesta Enviada', '#8B5CF6', 'file-text', False, False, 40),
    ('negotiation', 'Negociación', '#F59E0B', 'users', False, False, 50),
    ('won', 'Ganado', '#10B981', 'trophy', True, True, 60),
    ('lost', 'Perdido', '#EF4444', 'x-circle', True, True, 70),
    ('archived', 'Archivado', '#9CA3AF', 'archive', True, True, 80)
]

DEFAULT_TRANSITIONS = [
    ('new', 'contacted', 'Contactar', 'Marcar como contactado'),
    ('contacted', 'qualified', 'Calificar', 'Marcar como calificado'),
    ('qualified', 'proposal_sent', 'Enviar Propuesta', 'Enviar propuesta comercial'),
    ('proposal_sent', 'negotiation', 'Iniciar Negociación', 'Iniciar proceso de negociación'),
    ('negotiation', 'won', 'Ganar', 'Marcar como ganado'),
    ('negotiation', 'lost', 'Perder', 'Marcar como perdido'),
    (None, 'archived', 'Archivar', 'Archivar lead')
]

async def seed_tenant_defaults(conn: asyncpg.Connection, tenant_id: int):
    # Seed Statuses
    for code, name, color, icon, is_initial, is_final, sort_order in DEFAULT_STATUSES:
        await conn.execute("""
            INSERT INTO lead_statuses (tenant_id, code, name, color, icon, is_initial, is_final, sort_order, is_active)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, true)
            ON CONFLICT (tenant_id, code) DO NOTHING
        """, tenant_id, code, name, color, icon, is_initial, is_final, sort_order)
        
    # Seed Transitions 
    for from_code, to_code, label, desc in DEFAULT_TRANSITIONS:
        if from_code is None:
            await conn.execute("""
                INSERT INTO lead_status_transitions (tenant_id, from_status_code, to_status_code, label, description)
                VALUES ($1, NULL, $2, $3, $4)
                ON CONFLICT (tenant_id, from_status_code, to_status_code) DO NOTHING
            """, tenant_id, to_code, label, desc)
        else:
            await conn.execute("""
                INSERT INTO lead_status_transitions (tenant_id, from_status_code, to_status_code, label, description)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (tenant_id, from_status_code, to_status_code) DO NOTHING
            """, tenant_id, from_code, to_code, label, desc)

async def migrate_existing_statuses(dsn: str, dry_run: bool = True):
    print(f"🚀 Iniciando migración de estados (dry_run={dry_run})...")
    
    async with asyncpg.create_pool(dsn) as pool:
        async with pool.acquire() as conn:
            # 1. Obtener todos los tenants
            tenants = await conn.fetch("SELECT id FROM tenants")
            
            for tenant in tenants:
                tenant_id = tenant['id']
                print(f"\\n📊 Procesando tenant {tenant_id}...")
                
                async with conn.transaction():
                    # 2. Seed defaults for this tenant
                    if not dry_run:
                        await seed_tenant_defaults(conn, tenant_id)
                    
                    # 3. Analizar estados existentes
                    existing_statuses = await conn.fetch("""
                        SELECT DISTINCT status, COUNT(*) as count
                        FROM leads
                        WHERE tenant_id = $1 AND status IS NOT NULL
                        GROUP BY status
                        ORDER BY count DESC
                    """, tenant_id)
                    
                    if existing_statuses:
                        print("📈 Distribución de estados existentes:")
                        for row in existing_statuses:
                            mapped = STATUS_MAPPING.get(row['status'].lower() if row['status'] else '', 'new')
                            print(f"   - {row['status']}: {row['count']} leads → mapeará a '{mapped}'")
                    
                    if dry_run:
                        continue
                        
                    # 4. Asegurar que los estados mapeados existen en config 
                    for status in existing_statuses:
                        status_code = STATUS_MAPPING.get(status['status'].lower() if status['status'] else '', 'new')
                        
                        exists = await conn.fetchval("""
                            SELECT 1 FROM lead_statuses
                            WHERE tenant_id = $1 AND code = $2
                        """, tenant_id, status_code)
                        
                        if not exists:
                            print(f"➕ Creando estado '{status_code}' para tenant {tenant_id}")
                            await conn.execute("""
                                INSERT INTO lead_statuses (tenant_id, code, name, color, is_active)
                                VALUES ($1, $2, $3, $4, true)
                                ON CONFLICT (tenant_id, code) DO NOTHING
                            """, tenant_id, status_code, status_code.title(), '#6B7280')
                    
                    # 5. Actualizar los leads con status nuevos
                    mapping_logic = "CASE "
                    for k, v in STATUS_MAPPING.items():
                        mapping_logic += f"WHEN LOWER(status) = '{k}' THEN '{v}' "
                    mapping_logic += "ELSE 'new' END"

                    updated = await conn.execute(f"""
                        UPDATE leads
                        SET status = {mapping_logic}
                        WHERE tenant_id = $1 AND status IS NOT NULL
                    """, tenant_id)
                    
                    print(f"✅ Migración para tenant {tenant_id} completada: {updated} leads act.")

            # 6. Una vez migrados, intentar añadir la FK (Fuera del bucle por tenant, pero requiere que todos los leads de todos los tenants estén correctos)
            if not dry_run:
                try:
                    await conn.execute("""
                        ALTER TABLE leads DROP CONSTRAINT IF EXISTS fk_leads_status;
                        ALTER TABLE leads 
                        ADD CONSTRAINT fk_leads_status 
                        FOREIGN KEY (tenant_id, status) 
                        REFERENCES lead_statuses(tenant_id, code);
                    """)
                    print("✅ Foreign Key fk_leads_status añadida exitosamente.")
                except Exception as e:
                    print(f"❌ Error al añadir Foreign Key: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--dsn', default=os.getenv('DATABASE_URL'))
    parser.add_argument('--commit', action='store_true', help="Execute changes in DB")
    
    args = parser.parse_args()
    
    if not args.dsn:
        # Fallback local DSN
        args.dsn = "postgresql://postgres:postgres@localhost:5432/crmventas_dev"
        print(f"⚠️  DATABASE_URL no provisto. Usando fallback local: {args.dsn}")
        
    asyncio.run(migrate_existing_statuses(args.dsn, dry_run=not args.commit))
