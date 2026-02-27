#!/usr/bin/env python3
"""
Diagnóstico rápido del problema de leads no visibles
"""
import subprocess
import sys

def run_sql_query(query):
    """Ejecuta una consulta SQL usando psql si está disponible"""
    try:
        # Primero intentar con psql si hay variables de entorno
        import os
        dsn = os.getenv("POSTGRES_DSN")
        if not dsn:
            print("❌ POSTGRES_DSN no está definida")
            return None
            
        # Extraer credenciales
        import re
        match = re.search(r'postgresql\+asyncpg://([^:]+):([^@]+)@([^:/]+):?(\d+)?/(.+)', dsn)
        if not match:
            match = re.search(r'postgresql://([^:]+):([^@]+)@([^:/]+):?(\d+)?/(.+)', dsn)
        
        if match:
            user, password, host, port, dbname = match.groups()
            port = port or "5432"
            
            cmd = [
                "psql",
                "-h", host,
                "-p", port,
                "-U", user,
                "-d", dbname,
                "-c", query
            ]
            
            env = os.environ.copy()
            env["PGPASSWORD"] = password
            
            result = subprocess.run(cmd, capture_output=True, text=True, env=env)
            return result.stdout
    except Exception as e:
        pass
    
    return None

def main():
    print("🔍 DIAGNÓSTICO RÁPIDO - LEADS NO VISIBLES")
    print("=" * 60)
    
    # Consultas clave
    queries = [
        ("📊 Total de leads", "SELECT COUNT(*) as total_leads FROM leads;"),
        ("📊 Leads por status", """
            SELECT 
                status,
                COUNT(*) as count,
                CASE 
                    WHEN status IS NULL THEN 'NULL (aparecerán)'
                    WHEN status = 'deleted' THEN 'deleted (NO aparecerán)'
                    ELSE 'Otro status (aparecerán)'
                END as visibility
            FROM leads 
            GROUP BY status 
            ORDER BY count DESC;
        """),
        ("📊 Leads por fuente", "SELECT source, COUNT(*) as count FROM leads GROUP BY source ORDER BY count DESC;"),
        ("🏢 Tenants existentes", "SELECT id, clinic_name, niche_type FROM tenants ORDER BY id;"),
        ("👥 Usuarios activos", "SELECT email, role, status FROM users WHERE status = 'active' ORDER BY role;"),
        ("🎯 Sistema de estados", """
            SELECT 
                (SELECT COUNT(*) FROM lead_statuses) as total_statuses,
                (SELECT COUNT(*) FROM lead_status_transitions) as total_transitions,
                (SELECT COUNT(*) FROM lead_status_history) as total_history;
        """),
        ("🔍 Problemas potenciales", """
            -- Leads con status que no existe en lead_statuses
            SELECT COUNT(*) as leads_with_invalid_status
            FROM leads l
            WHERE l.status IS NOT NULL 
              AND NOT EXISTS (
                SELECT 1 FROM lead_statuses ls WHERE ls.code = l.status
              );
            
            -- Leads con tenant_id que no existe
            SELECT COUNT(*) as leads_with_invalid_tenant
            FROM leads l
            WHERE NOT EXISTS (
                SELECT 1 FROM tenants t WHERE t.id = l.tenant_id
            );
        """)
    ]
    
    for title, query in queries:
        print(f"\n{title}:")
        print("-" * 40)
        result = run_sql_query(query)
        if result:
            print(result)
        else:
            print("❌ No se pudo ejecutar la consulta")
            print("💡 Ejecuta manualmente en psql:")
            print(query)
    
    print("\n" + "=" * 60)
    print("🎯 POSIBLES CAUSAS DEL PROBLEMA:")
    print("=" * 60)
    
    print("""
1. ✅ Leads con status = 'deleted' - NO aparecen en la UI
   - La query filtra: `(status IS NULL OR status != 'deleted')`
   - Solución: Cambiar status o modificar la query

2. ✅ Foreign key constraint entre leads.status y lead_statuses.code
   - Si existe constraint y los leads tienen estados inválidos, las queries fallan
   - Solución: Crear estados faltantes o remover constraint

3. ✅ Tenant_id incorrecto
   - Si leads.tenant_id no existe en tenants, no aparecen
   - Solución: Corregir tenant_id o crear tenant faltante

4. ✅ Usuario sin permisos
   - El usuario actual no tiene acceso al tenant de los leads
   - Solución: Verificar permisos del usuario

5. ✅ Filtros aplicados en UI
   - Puede haber filtros activos en la interfaz
   - Solución: Limpiar filtros en la página de leads
""")
    
    print("\n🔧 SOLUCIONES RÁPIDAS:")
    print("""
1. Verificar status de leads:
   SELECT status, COUNT(*) FROM leads GROUP BY status;

2. Si hay leads con status='deleted', cambiarlos:
   UPDATE leads SET status = 'new' WHERE status = 'deleted';

3. Si el sistema de estados tiene problemas:
   - Ejecutar: python3 orchestrator_service/scripts/migrate_existing_statuses.py --fix

4. Si no hay leads en absoluto:
   - Verificar prospección Apify
   - Verificar importación de datos
""")

if __name__ == "__main__":
    main()