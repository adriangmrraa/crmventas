#!/usr/bin/env python3
"""
Diagnóstico rápido del problema de leads no visibles
"""
import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_connection():
    """Obtener conexión a PostgreSQL"""
    dsn = os.getenv("POSTGRES_DSN")
    if not dsn:
        print("❌ ERROR: POSTGRES_DSN no está definida")
        print("Ejemplo: postgresql://user:password@localhost:5432/crmventas")
        sys.exit(1)
    
    # Convertir DSN de asyncpg a psycopg2
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://")
    
    try:
        conn = psycopg2.connect(dsn)
        return conn
    except Exception as e:
        print(f"❌ Error conectando a la base de datos: {e}")
        sys.exit(1)

def check_leads_table(conn):
    """Verificar estado de la tabla leads"""
    print("\n🔍 VERIFICANDO TABLA LEADS:")
    print("=" * 50)
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # 1. Verificar si la tabla existe
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'leads'
            ) as exists;
        """)
        exists = cur.fetchone()['exists']
        
        if not exists:
            print("❌ La tabla 'leads' NO EXISTE en la base de datos")
            return False
        
        print("✅ La tabla 'leads' existe")
        
        # 2. Contar leads
        cur.execute("SELECT COUNT(*) as count FROM leads")
        count = cur.fetchone()['count']
        print(f"📊 Total de leads en la tabla: {count}")
        
        # 3. Verificar estructura de la tabla
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'leads'
            ORDER BY ordinal_position
        """)
        columns = cur.fetchall()
        
        print(f"\n📋 Estructura de la tabla ({len(columns)} columnas):")
        for col in columns:
            print(f"  - {col['column_name']}: {col['data_type']} ({'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'})")
        
        # 4. Verificar foreign key a tenants
        cur.execute("""
            SELECT tc.table_name, kcu.column_name, 
                   ccu.table_name AS foreign_table_name,
                   ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY' 
              AND tc.table_name = 'leads'
              AND ccu.table_name = 'tenants'
        """)
        fk = cur.fetchone()
        
        if fk:
            print(f"\n✅ Foreign key a tenants: {fk['column_name']} → {fk['foreign_table_name']}.{fk['foreign_column_name']}")
        else:
            print("\n⚠️ No hay foreign key a tenants (puede ser normal si se usa tenant_id sin constraint)")
        
        # 5. Verificar algunos leads de ejemplo
        if count > 0:
            print(f"\n📄 Ejemplo de leads (primeros 5):")
            cur.execute("""
                SELECT id, phone_number, first_name, last_name, status, lead_source, created_at
                FROM leads 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            leads = cur.fetchall()
            
            for i, lead in enumerate(leads, 1):
                print(f"  {i}. {lead['phone_number']} - {lead['first_name']} {lead['last_name']} - {lead['status']} ({lead['lead_source']})")
        
        return True

def check_tenants_table(conn):
    """Verificar estado de la tabla tenants"""
    print("\n🔍 VERIFICANDO TABLA TENANTS:")
    print("=" * 50)
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # 1. Verificar si la tabla existe
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'tenants'
            ) as exists;
        """)
        exists = cur.fetchone()['exists']
        
        if not exists:
            print("❌ La tabla 'tenants' NO EXISTE en la base de datos")
            return False
        
        print("✅ La tabla 'tenants' existe")
        
        # 2. Contar tenants
        cur.execute("SELECT COUNT(*) as count FROM tenants")
        count = cur.fetchone()['count']
        print(f"📊 Total de tenants: {count}")
        
        # 3. Listar tenants
        cur.execute("SELECT id, clinic_name, bot_phone_number, niche_type FROM tenants")
        tenants = cur.fetchall()
        
        for tenant in tenants:
            print(f"  - ID {tenant['id']}: {tenant['clinic_name']} ({tenant['niche_type']}) - Bot: {tenant['bot_phone_number']}")
        
        return True

def check_lead_status_system(conn):
    """Verificar si el sistema de estados fue aplicado"""
    print("\n🔍 VERIFICANDO SISTEMA DE ESTADOS:")
    print("=" * 50)
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        tables_to_check = [
            'lead_statuses',
            'lead_status_transitions', 
            'lead_status_history',
            'lead_status_triggers',
            'lead_status_trigger_logs'
        ]
        
        for table in tables_to_check:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                ) as exists;
            """, (table,))
            exists = cur.fetchone()['exists']
            
            if exists:
                # Contar registros
                cur.execute(f"SELECT COUNT(*) as count FROM {table}")
                count = cur.fetchone()['count']
                print(f"✅ {table}: EXISTE ({count} registros)")
            else:
                print(f"❌ {table}: NO EXISTE")
        
        # Verificar si la columna status en leads tiene foreign key constraint
        cur.execute("""
            SELECT tc.constraint_name, tc.constraint_type
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
            WHERE tc.table_name = 'leads'
              AND kcu.column_name = 'status'
              AND tc.constraint_type = 'FOREIGN KEY'
        """)
        fk_constraint = cur.fetchone()
        
        if fk_constraint:
            print(f"\n⚠️ ADVERTENCIA: La columna 'status' en 'leads' tiene una foreign key constraint")
            print(f"   Esto puede causar problemas si los leads tienen estados que no existen en lead_statuses")
        else:
            print(f"\n✅ La columna 'status' en 'leads' NO tiene foreign key constraint")

def check_users_table(conn):
    """Verificar estado de la tabla users"""
    print("\n🔍 VERIFICANDO TABLA USERS:")
    print("=" * 50)
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # 1. Verificar si la tabla existe
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'users'
            ) as exists;
        """)
        exists = cur.fetchone()['exists']
        
        if not exists:
            print("❌ La tabla 'users' NO EXISTE en la base de datos")
            return False
        
        print("✅ La tabla 'users' existe")
        
        # 2. Contar usuarios
        cur.execute("SELECT COUNT(*) as count FROM users")
        count = cur.fetchone()['count']
        print(f"📊 Total de usuarios: {count}")
        
        # 3. Listar usuarios activos
        cur.execute("""
            SELECT id, email, role, status, first_name, last_name
            FROM users 
            WHERE status = 'active'
            ORDER BY role, email
        """)
        users = cur.fetchall()
        
        if users:
            print(f"\n👥 Usuarios activos ({len(users)}):")
            for user in users:
                print(f"  - {user['email']} ({user['role']}): {user['first_name']} {user['last_name']}")
        else:
            print("\n⚠️ No hay usuarios activos")
        
        return True

def check_prospecting_data(conn):
    """Verificar datos de prospección"""
    print("\n🔍 VERIFICANDO DATOS DE PROSPECCIÓN:")
    print("=" * 50)
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Verificar leads con source de prospección
        cur.execute("""
            SELECT lead_source, COUNT(*) as count
            FROM leads
            GROUP BY lead_source
            ORDER BY count DESC
        """)
        sources = cur.fetchall()
        
        if sources:
            print("📊 Leads por fuente:")
            for source in sources:
                print(f"  - {source['lead_source']}: {source['count']} leads")
        else:
            print("⚠️ No hay leads en la base de datos")
        
        # Verificar leads de Apify específicamente
        cur.execute("""
            SELECT COUNT(*) as count 
            FROM leads 
            WHERE lead_source = 'APIFY' 
               OR apify_place_id IS NOT NULL
        """)
        apify_count = cur.fetchone()['count']
        print(f"\n🤖 Leads de Apify: {apify_count}")

def main():
    print("🔧 DIAGNÓSTICO CRM VENTAS - PROBLEMA DE LEADS NO VISIBLES")
    print("=" * 60)
    
    conn = get_db_connection()
    
    try:
        # Ejecutar todas las verificaciones
        check_tenants_table(conn)
        check_users_table(conn)
        check_leads_table(conn)
        check_lead_status_system(conn)
        check_prospecting_data(conn)
        
        print("\n" + "=" * 60)
        print("🎯 RESUMEN DEL DIAGNÓSTICO:")
        print("=" * 60)
        
        # Resumen final
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Verificar problema común: tenant_id incorrecto
            cur.execute("""
                SELECT COUNT(*) as problematic_leads
                FROM leads l
                WHERE NOT EXISTS (
                    SELECT 1 FROM tenants t WHERE t.id = l.tenant_id
                )
            """)
            problematic = cur.fetchone()['problematic_leads']
            
            if problematic > 0:
                print(f"❌ PROBLEMA ENCONTRADO: {problematic} leads con tenant_id que no existe en tenants")
                print("   Esto hará que los leads no sean visibles en la UI")
                print("\n💡 SOLUCIÓN: Ejecutar:")
                print("   python3 orchestrator_service/scripts/migrate_existing_statuses.py --fix-tenant-issues")
            
            # Verificar si hay datos pero no se ven
            cur.execute("SELECT COUNT(*) as total FROM leads")
            total = cur.fetchone()['total']
            
            if total > 0:
                print(f"✅ Hay {total} leads en la base de datos")
                print("   Si no se ven en la UI, puede ser por:")
                print("   1. Filtros aplicados en la interfaz")
                print("   2. Problema de permisos del usuario")
                print("   3. Tenant_id incorrecto en la sesión del usuario")
            else:
                print("⚠️ No hay leads en la base de datos")
                print("   Los leads deben crearse via:")
                print("   1. Prospección Apify")
                print("   2. Formularios web")
                print("   3. Importación manual")
        
    finally:
        conn.close()
        print("\n🔧 Diagnóstico completado")

if __name__ == "__main__":
    main()