#!/usr/bin/env python3
"""
Diagnóstico del problema de leads no visibles en CRM Ventas
Usa el sistema de base de datos existente
"""
import os
import sys
import asyncio

# Agregar el directorio del orchestrator al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'orchestrator_service'))

# Cargar variables de entorno temporales
env_file = os.path.join(os.path.dirname(__file__), '.env.temp')
if os.path.exists(env_file):
    print(f"📁 Cargando variables de entorno desde: {env_file}")
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()
                print(f"  {key}={'*' * len(value) if 'PASS' in key or 'KEY' in key else value}")

async def diagnose():
    """Diagnóstico principal"""
    print("\n🔧 DIAGNÓSTICO CRM VENTAS - LEADS NO VISIBLES")
    print("=" * 60)
    
    try:
        # Importar el módulo de base de datos
        from db import Database
        
        db = Database()
        await db.connect()
        
        if not db.pool:
            print("❌ No se pudo conectar a la base de datos")
            return
        
        print("✅ Conectado a la base de datos")
        
        async with db.pool.acquire() as conn:
            # 1. Verificar tablas principales
            print("\n📋 VERIFICANDO TABLAS PRINCIPALES:")
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            
            critical_tables = ['tenants', 'users', 'leads', 'lead_statuses', 'lead_status_history']
            found_tables = []
            
            for table in tables:
                table_name = table['table_name']
                if table_name in critical_tables:
                    found_tables.append(table_name)
            
            print(f"Tablas encontradas: {len(tables)}")
            print(f"Tablas críticas encontradas: {len(found_tables)}/{len(critical_tables)}")
            
            for table in critical_tables:
                if table in found_tables:
                    # Contar registros
                    count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                    print(f"  ✅ {table}: {count} registros")
                else:
                    print(f"  ❌ {table}: NO EXISTE")
            
            # 2. Verificar datos específicos
            print("\n📊 VERIFICANDO DATOS:")
            
            # Tenants
            tenants = await conn.fetch("SELECT id, clinic_name, niche_type FROM tenants")
            print(f"\n🏢 Tenants ({len(tenants)}):")
            for tenant in tenants:
                print(f"  - ID {tenant['id']}: {tenant['clinic_name']} ({tenant['niche_type']})")
            
            # Usuarios activos
            users = await conn.fetch("""
                SELECT id, email, role, status, first_name, last_name 
                FROM users 
                WHERE status = 'active'
                ORDER BY role, email
            """)
            print(f"\n👥 Usuarios activos ({len(users)}):")
            for user in users:
                print(f"  - {user['email']} ({user['role']}): {user['first_name']} {user['last_name']}")
            
            # Leads
            leads_count = await conn.fetchval("SELECT COUNT(*) FROM leads")
            print(f"\n📈 Leads totales: {leads_count}")
            
            if leads_count > 0:
                # Leads por fuente
                sources = await conn.fetch("""
                    SELECT lead_source, COUNT(*) as count
                    FROM leads
                    GROUP BY lead_source
                    ORDER BY count DESC
                """)
                print(f"\n📤 Leads por fuente:")
                for source in sources:
                    print(f"  - {source['lead_source']}: {source['count']}")
                
                # Ejemplo de leads
                sample_leads = await conn.fetch("""
                    SELECT id, phone_number, first_name, last_name, status, lead_source, created_at
                    FROM leads 
                    ORDER BY created_at DESC 
                    LIMIT 3
                """)
                print(f"\n📄 Ejemplo de leads (últimos 3):")
                for i, lead in enumerate(sample_leads, 1):
                    print(f"  {i}. {lead['phone_number']} - {lead['first_name']} {lead['last_name']} - {lead['status']} ({lead['lead_source']})")
                
                # Verificar problema común: tenant_id incorrecto
                problematic = await conn.fetchval("""
                    SELECT COUNT(*) as problematic_leads
                    FROM leads l
                    WHERE NOT EXISTS (
                        SELECT 1 FROM tenants t WHERE t.id = l.tenant_id
                    )
                """)
                
                if problematic > 0:
                    print(f"\n❌ PROBLEMA ENCONTRADO: {problematic} leads con tenant_id que no existe en tenants")
                    print("   Esto hará que los leads no sean visibles en la UI")
                else:
                    print(f"\n✅ Todos los leads tienen tenant_id válido")
            
            # 3. Verificar sistema de estados
            print("\n🎯 VERIFICANDO SISTEMA DE ESTADOS:")
            
            status_tables = [
                ('lead_statuses', 'Estados definidos'),
                ('lead_status_transitions', 'Transiciones'),
                ('lead_status_history', 'Histórico'),
                ('lead_status_triggers', 'Triggers'),
                ('lead_status_trigger_logs', 'Logs de triggers')
            ]
            
            for table_name, description in status_tables:
                exists = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = $1
                    )
                """, table_name)
                
                if exists:
                    count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
                    print(f"  ✅ {description} ({table_name}): {count} registros")
                else:
                    print(f"  ❌ {description} ({table_name}): NO EXISTE")
            
            # 4. Verificar si la migración patch_018 se aplicó
            print("\n🔄 VERIFICANDO MIGRACIONES:")
            
            # Buscar evidencia de la migración
            has_statuses = await conn.fetchval("SELECT COUNT(*) FROM lead_statuses") > 0
            has_history = await conn.fetchval("SELECT COUNT(*) FROM lead_status_history") > 0
            
            if has_statuses or has_history:
                print("✅ Sistema de estados parece estar implementado")
                
                # Verificar estados por defecto
                default_statuses = await conn.fetch("""
                    SELECT code, name, color, is_initial, is_final
                    FROM lead_statuses
                    WHERE tenant_id = 1
                    ORDER BY sort_order
                """)
                
                if default_statuses:
                    print(f"\n📋 Estados por defecto (tenant 1):")
                    for status in default_statuses:
                        flags = []
                        if status['is_initial']:
                            flags.append('inicial')
                        if status['is_final']:
                            flags.append('final')
                        flags_str = f" ({', '.join(flags)})" if flags else ""
                        print(f"  - {status['code']}: {status['name']}{flags_str}")
            else:
                print("⚠️ Sistema de estados NO parece estar implementado")
                print("   Ejecuta: python3 orchestrator_service/scripts/migrate_existing_statuses.py")
            
            print("\n" + "=" * 60)
            print("🎯 RESUMEN DEL DIAGNÓSTICO:")
            print("=" * 60)
            
            if leads_count == 0:
                print("❌ PROBLEMA: No hay leads en la base de datos")
                print("   Posibles causas:")
                print("   1. La prospección Apify no se ejecutó")
                print("   2. Los leads no se importaron")
                print("   3. La base de datos está vacía")
            elif leads_count > 0 and len(users) == 0:
                print("⚠️ ADVERTENCIA: Hay leads pero no hay usuarios activos")
                print("   Los usuarios necesitan estar 'active' para ver leads")
            elif leads_count > 0 and len(tenants) == 0:
                print("❌ PROBLEMA: Hay leads pero no hay tenants")
                print("   Cada lead necesita un tenant_id válido")
            else:
                print("✅ La base de datos parece estar en buen estado")
                print("   Si los leads no se ven en la UI, verifica:")
                print("   1. Filtros aplicados en la interfaz")
                print("   2. Permisos del usuario actual")
                print("   3. Console del navegador para errores")
                
    except Exception as e:
        print(f"\n❌ ERROR durante el diagnóstico: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(diagnose())