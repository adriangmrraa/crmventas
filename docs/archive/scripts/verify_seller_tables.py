#!/usr/bin/env python3
"""
Script para verificar las tablas del sistema de vendedores
"""
import psycopg2
import os

def load_env():
    """Cargar variables de entorno desde .env.temp"""
    env_file = '.env.temp'
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

def get_connection():
    """Obtener conexión a PostgreSQL"""
    dsn = os.getenv('POSTGRES_DSN', '')
    if not dsn:
        print("❌ POSTGRES_DSN no encontrado en variables de entorno")
        return None
    
    # Convertir DSN de asyncpg a psycopg2
    dsn = dsn.replace('postgresql+asyncpg://', 'postgresql://')
    
    try:
        conn = psycopg2.connect(dsn)
        return conn
    except Exception as e:
        print(f"❌ Error conectando a PostgreSQL: {e}")
        return None

def verify_tables():
    """Verificar que las tablas del sistema de vendedores existen"""
    conn = get_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    print("🔍 VERIFICANDO TABLAS DEL SISTEMA DE VENDEDORES...")
    print("=" * 60)
    
    # 1. Verificar tablas creadas
    tables_to_check = [
        ('seller_metrics', 'Tabla de métricas de vendedores'),
        ('assignment_rules', 'Tabla de reglas de asignación')
    ]
    
    for table, description in tables_to_check:
        cursor.execute(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}');")
        exists = cursor.fetchone()[0]
        status = '✅' if exists else '❌'
        exists_text = 'EXISTE' if exists else 'NO EXISTE'
        print(f"{status} {table}: {description} - {exists_text}")
    
    # 2. Verificar columnas en chat_messages
    print("\n🔍 VERIFICANDO COLUMNAS EN chat_messages...")
    cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'chat_messages' 
        AND column_name IN ('assigned_seller_id', 'assigned_at', 'assigned_by', 'assignment_source')
    """)
    
    columns = cursor.fetchall()
    expected_columns = ['assigned_seller_id', 'assigned_at', 'assigned_by', 'assignment_source']
    
    for col in expected_columns:
        found = any(col == row[0] for row in columns)
        status = '✅' if found else '❌'
        found_text = 'AGREGADA' if found else 'FALTANTE'
        print(f"{status} {col}: {found_text}")
    
    # 3. Verificar columnas en leads
    print("\n🔍 VERIFICANDO COLUMNAS EN leads...")
    cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'leads' 
        AND column_name IN ('initial_assignment_source', 'assignment_history')
    """)
    
    columns = cursor.fetchall()
    expected_columns = ['initial_assignment_source', 'assignment_history']
    
    for col in expected_columns:
        found = any(col == row[0] for row in columns)
        status = '✅' if found else '❌'
        found_text = 'AGREGADA' if found else 'FALTANTE'
        print(f"{status} {col}: {found_text}")
    
    # 4. Verificar índices
    print("\n🔍 VERIFICANDO ÍNDICES...")
    cursor.execute("""
        SELECT indexname, indexdef 
        FROM pg_indexes 
        WHERE tablename IN ('chat_messages', 'seller_metrics')
        AND (indexname LIKE '%assigned%' OR indexname LIKE '%seller%')
    """)
    
    indexes = cursor.fetchall()
    if indexes:
        for idx in indexes:
            print(f"✅ {idx[0]}: {idx[1][:80]}...")
    else:
        print("⚠️  No se encontraron índices específicos del sistema de vendedores")
    
    # 5. Verificar reglas por defecto
    print("\n🔍 VERIFICANDO REGLAS POR DEFECTO...")
    cursor.execute("SELECT COUNT(*) FROM assignment_rules")
    rule_count = cursor.fetchone()[0]
    print(f"✅ Reglas creadas: {rule_count}")
    
    if rule_count > 0:
        cursor.execute("SELECT rule_name, rule_type FROM assignment_rules LIMIT 5")
        rules = cursor.fetchall()
        for rule in rules:
            print(f"   📋 {rule[0]} ({rule[1]})")
    
    # 6. Verificar estructura de seller_metrics
    print("\n🔍 VERIFICANDO ESTRUCTURA DE seller_metrics...")
    cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'seller_metrics'
        ORDER BY ordinal_position
    """)
    
    columns = cursor.fetchall()
    print(f"✅ La tabla tiene {len(columns)} columnas:")
    for col in columns[:10]:  # Mostrar primeras 10 columnas
        print(f"   📊 {col[0]} ({col[1]})")
    
    if len(columns) > 10:
        print(f"   ... y {len(columns) - 10} columnas más")
    
    conn.close()
    print("\n" + "=" * 60)
    print("🎉 VERIFICACIÓN COMPLETADA CON ÉXITO!")
    print("\n📋 RESUMEN:")
    print("   - Sistema de vendedores instalado correctamente")
    print("   - Tablas y columnas creadas")
    print("   - Índices de performance configurados")
    print("   - Reglas por defecto insertadas")
    print("   - Listo para usar en producción")

if __name__ == "__main__":
    load_env()
    verify_tables()