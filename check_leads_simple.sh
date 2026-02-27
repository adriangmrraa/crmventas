#!/bin/bash
echo "🔍 Verificando estado de la base de datos CRM Ventas"
echo "=================================================="

# Verificar si hay variable de entorno POSTGRES_DSN
if [ -z "$POSTGRES_DSN" ]; then
    echo "❌ ERROR: POSTGRES_DSN no está definida"
    echo "Ejecuta: export POSTGRES_DSN='postgresql+asyncpg://user:password@localhost:5432/crmventas'"
    exit 1
fi

echo "✅ POSTGRES_DSN está definida"
echo "DSN: $(echo $POSTGRES_DSN | sed 's/:[^:@]*@/:****@/')"

# Extraer información de conexión
DB_NAME=$(echo $POSTGRES_DSN | grep -o '/[^/]*$' | cut -d'/' -f2)
DB_HOST=$(echo $POSTGRES_DSN | grep -o '@[^:/]*' | cut -d'@' -f2)
DB_PORT=$(echo $POSTGRES_DSN | grep -o ':[0-9]*/' | cut -d':' -f2 | cut -d'/' -f1)

echo ""
echo "📊 Información de conexión:"
echo "  - Host: $DB_HOST"
echo "  - Puerto: ${DB_PORT:-5432}"
echo "  - Base de datos: $DB_NAME"

# Verificar si podemos conectarnos con psql
echo ""
echo "🧪 Probando conexión con psql..."
if command -v psql &> /dev/null; then
    # Convertir DSN a formato psql
    PSQL_DSN=$(echo $POSTGRES_DSN | sed 's/postgresql+asyncpg:\/\///' | sed 's/\/[^/]*$/\/postgres/')
    
    if PGPASSWORD=$(echo $POSTGRES_DSN | grep -o ':[^:@]*@' | cut -d':' -f2 | cut -d'@' -f1) psql -h $DB_HOST -p ${DB_PORT:-5432} -U $(echo $POSTGRES_DSN | grep -o '//[^:]*' | cut -d'/' -f3) -d $DB_NAME -c "\q" 2>/dev/null; then
        echo "✅ Conexión exitosa a PostgreSQL"
        
        # Ejecutar consultas básicas
        echo ""
        echo "📋 Consultando información de la base de datos..."
        
        # 1. Verificar tablas principales
        PGPASSWORD=$(echo $POSTGRES_DSN | grep -o ':[^:@]*@' | cut -d':' -f2 | cut -d'@' -f1) psql -h $DB_HOST -p ${DB_PORT:-5432} -U $(echo $POSTGRES_DSN | grep -o '//[^:]*' | cut -d'/' -f3) -d $DB_NAME -c "
SELECT '=== TABLAS PRINCIPALES ===' as info;
SELECT table_name, 
       (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as columnas
FROM information_schema.tables t 
WHERE table_schema = 'public' 
  AND table_name IN ('tenants', 'users', 'leads', 'lead_statuses', 'lead_status_history')
ORDER BY table_name;
        " 2>/dev/null || echo "❌ Error ejecutando consulta"
        
        # 2. Contar leads
        echo ""
        PGPASSWORD=$(echo $POSTGRES_DSN | grep -o ':[^:@]*@' | cut -d':' -f2 | cut -d'@' -f1) psql -h $DB_HOST -p ${DB_PORT:-5432} -U $(echo $POSTGRES_DSN | grep -o '//[^:]*' | cut -d'/' -f3) -d $DB_NAME -c "
SELECT '=== ESTADÍSTICAS LEADS ===' as info;
SELECT 
    (SELECT COUNT(*) FROM leads) as total_leads,
    (SELECT COUNT(*) FROM leads WHERE lead_source = 'APIFY') as leads_apify,
    (SELECT COUNT(*) FROM leads WHERE lead_source = 'META_ADS') as leads_meta_ads,
    (SELECT COUNT(*) FROM leads WHERE lead_source = 'ORGANIC') as leads_organic;
        " 2>/dev/null || echo "❌ Error contando leads"
        
        # 3. Verificar tenants
        echo ""
        PGPASSWORD=$(echo $POSTGRES_DSN | grep -o ':[^:@]*@' | cut -d':' -f2 | cut -d'@' -f1) psql -h $DB_HOST -p ${DB_PORT:-5432} -U $(echo $POSTGRES_DSN | grep -o '//[^:]*' | cut -d'/' -f3) -d $DB_NAME -c "
SELECT '=== TENANTS ===' as info;
SELECT id, clinic_name, niche_type, bot_phone_number FROM tenants ORDER BY id;
        " 2>/dev/null || echo "❌ Error consultando tenants"
        
        # 4. Verificar usuarios
        echo ""
        PGPASSWORD=$(echo $POSTGRES_DSN | grep -o ':[^:@]*@' | cut -d':' -f2 | cut -d'@' -f1) psql -h $DB_HOST -p ${DB_PORT:-5432} -U $(echo $POSTGRES_DSN | grep -o '//[^:]*' | cut -d'/' -f3) -d $DB_NAME -c "
SELECT '=== USUARIOS ACTIVOS ===' as info;
SELECT email, role, status, first_name, last_name 
FROM users 
WHERE status = 'active'
ORDER BY role, email;
        " 2>/dev/null || echo "❌ Error consultando usuarios"
        
        # 5. Verificar sistema de estados
        echo ""
        PGPASSWORD=$(echo $POSTGRES_DSN | grep -o ':[^:@]*@' | cut -d':' -f2 | cut -d'@' -f1) psql -h $DB_HOST -p ${DB_PORT:-5432} -U $(echo $POSTGRES_DSN | grep -o '//[^:]*' | cut -d'/' -f3) -d $DB_NAME -c "
SELECT '=== SISTEMA DE ESTADOS ===' as info;
SELECT 
    (SELECT COUNT(*) FROM lead_statuses) as total_statuses,
    (SELECT COUNT(*) FROM lead_status_transitions) as total_transitions,
    (SELECT COUNT(*) FROM lead_status_history) as total_history_entries;
        " 2>/dev/null || echo "❌ Error consultando sistema de estados (puede ser normal si no se aplicó la migración)"
        
    else
        echo "❌ No se pudo conectar a PostgreSQL"
        echo "Verifica:"
        echo "  1. Que PostgreSQL esté corriendo"
        echo "  2. Que las credenciales sean correctas"
        echo "  3. Que la base de datos exista"
    fi
else
    echo "⚠️ psql no está instalado. Instala con: sudo apt-get install postgresql-client"
fi

echo ""
echo "🔧 Para diagnóstico más detallado, ejecuta:"
echo "   python3 orchestrator_service/diag_db.py"
echo ""
echo "🔄 Para aplicar migraciones pendientes:"
echo "   python3 orchestrator_service/run_meta_ads_migrations.py"
echo "   python3 orchestrator_service/scripts/migrate_existing_statuses.py"