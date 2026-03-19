#!/usr/bin/env python3
"""
🚀 SPRINT 2 - TESTING AUTOMATIZADO
Verifica componentes críticos del Sistema de Control CEO
"""

import os
import json
import re
from pathlib import Path

def print_header(text):
    print(f"\n{'='*60}")
    print(f"🔍 {text}")
    print(f"{'='*60}")

def print_success(text):
    print(f"✅ {text}")

def print_warning(text):
    print(f"⚠️  {text}")

def print_error(text):
    print(f"❌ {text}")

def check_file_exists(path, description):
    if os.path.exists(path):
        print_success(f"{description}: EXISTE")
        return True
    else:
        print_error(f"{description}: NO EXISTE")
        return False

def check_translations():
    """Verifica traducciones críticas en es.json"""
    print_header("VERIFICANDO TRADUCCIONES")
    
    es_json_path = "frontend_react/src/locales/es.json"
    if not check_file_exists(es_json_path, "Archivo es.json"):
        return False
    
    try:
        with open(es_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        critical_keys = {
            "nav.meta_leads": "FORMULARIO META",
            "sellers.agent_ia": "AGENTE IA", 
            "roles.setter": "Setter",
            "roles.closer": "Closer",
            "roles.ceo": "CEO",
            "sellers.assign_to_me": "Asignarme a mí",
            "sellers.auto_assign": "Auto asignar"
        }
        
        all_ok = True
        nav_section = data.get('nav', {})
        sellers_section = data.get('sellers', {})
        roles_section = data.get('roles', {})
        
        for key, expected in critical_keys.items():
            section, subkey = key.split('.')
            
            if section == 'nav':
                actual = nav_section.get(subkey, '')
            elif section == 'sellers':
                actual = sellers_section.get(subkey, '')
            elif section == 'roles':
                actual = roles_section.get(subkey, '')
            else:
                actual = ''
            
            if actual == expected:
                print_success(f"{key}: '{actual}'")
            else:
                print_error(f"{key}: Esperado '{expected}', encontrado '{actual}'")
                all_ok = False
        
        return all_ok
        
    except Exception as e:
        print_error(f"Error leyendo es.json: {e}")
        return False

def check_react_components():
    """Verifica componentes React críticos"""
    print_header("VERIFICANDO COMPONENTES REACT")
    
    components = {
        "SellerBadge.tsx": "Badge de vendedor en conversaciones",
        "SellerSelector.tsx": "Modal para seleccionar vendedor", 
        "AssignmentHistory.tsx": "Historial de asignaciones",
        "SellerMetricsDashboard.tsx": "Dashboard de métricas",
        "MetaLeadsView.tsx": "Vista FORMULARIO META"
    }
    
    all_ok = True
    for filename, description in components.items():
        path = f"frontend_react/src/components/{filename}"
        if filename == "MetaLeadsView.tsx":
            path = f"frontend_react/src/views/{filename}"
        
        if check_file_exists(path, f"{filename} ({description})"):
            # Verificar que tenga contenido mínimo
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if len(content) < 100:
                    print_warning(f"{filename}: Contenido muy corto ({len(content)} chars)")
                else:
                    print_success(f"{filename}: {len(content)} chars")
                    
            except Exception as e:
                print_error(f"{filename}: Error leyendo archivo: {e}")
                all_ok = False
        else:
            all_ok = False
    
    return all_ok

def check_routes():
    """Verifica rutas en App.tsx"""
    print_header("VERIFICANDO RUTAS EN App.tsx")
    
    app_tsx_path = "frontend_react/src/App.tsx"
    if not check_file_exists(app_tsx_path, "Archivo App.tsx"):
        return False
    
    try:
        with open(app_tsx_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Buscar ruta para meta-leads
        meta_leads_pattern = r'path="crm/meta-leads"'
        if re.search(meta_leads_pattern, content):
            print_success("Ruta /crm/meta-leads encontrada")
            
            # Extraer contexto alrededor de la ruta
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'crm/meta-leads' in line:
                    start = max(0, i-2)
                    end = min(len(lines), i+3)
                    context = '\n'.join(lines[start:end])
                    print_success("Contexto de la ruta:")
                    print(f"  {context}")
                    break
        else:
            print_error("Ruta /crm/meta-leads NO encontrada")
            return False
        
        # Buscar import de MetaLeadsView
        import_pattern = r'import.*MetaLeadsView'
        if re.search(import_pattern, content):
            print_success("MetaLeadsView importado")
        else:
            print_error("MetaLeadsView NO importado")
            return False
        
        return True
        
    except Exception as e:
        print_error(f"Error leyendo App.tsx: {e}")
        return False

def check_sidebar():
    """Verifica item en Sidebar.tsx"""
    print_header("VERIFICANDO SIDEBAR")
    
    sidebar_path = "frontend_react/src/components/Sidebar.tsx"
    if not check_file_exists(sidebar_path, "Archivo Sidebar.tsx"):
        return False
    
    try:
        with open(sidebar_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Buscar item meta_leads en menuItems
        meta_leads_pattern = r"id: 'meta_leads'.*path: '/crm/meta-leads'"
        if re.search(meta_leads_pattern, content, re.DOTALL):
            print_success("Item 'meta_leads' encontrado en sidebar")
            
            # Extraer línea completa
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if "'meta_leads'" in line:
                    print_success(f"Línea {i+1}: {line.strip()}")
                    break
        else:
            print_error("Item 'meta_leads' NO encontrado en sidebar")
            return False
        
        return True
        
    except Exception as e:
        print_error(f"Error leyendo Sidebar.tsx: {e}")
        return False

def check_backend_services():
    """Verifica servicios backend"""
    print_header("VERIFICANDO SERVICIOS BACKEND")
    
    services = {
        "seller_assignment_service.py": "Servicio de asignación de vendedores",
        "seller_metrics_service.py": "Servicio de métricas de vendedores",
        "seller_routes.py": "Endpoints API para vendedores"
    }
    
    all_ok = True
    for filename, description in services.items():
        path = f"orchestrator_service/services/{filename}"
        if filename == "seller_routes.py":
            path = f"orchestrator_service/routes/{filename}"
        
        if check_file_exists(path, f"{filename} ({description})"):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                print_success(f"{filename}: {len(content)} chars")
                
            except Exception as e:
                print_error(f"{filename}: Error leyendo archivo: {e}")
                all_ok = False
        else:
            all_ok = False
    
    return all_ok

def check_database_migrations():
    """Verifica migraciones de base de datos"""
    print_header("VERIFICANDO MIGRACIONES DE BASE DE DATOS")
    
    migration_path = "orchestrator_service/migrations/patch_015_seller_assignment.py"
    if not check_file_exists(migration_path, "Migración Parche 11"):
        return False
    
    try:
        with open(migration_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar tablas críticas
        tables_to_check = [
            "seller_metrics",
            "assignment_rules", 
            "assigned_seller_id",
            "assignment_history"
        ]
        
        all_ok = True
        for table in tables_to_check:
            if table in content:
                print_success(f"Tabla/columna '{table}' mencionada en migración")
            else:
                print_error(f"Tabla/columna '{table}' NO encontrada en migración")
                all_ok = False
        
        return all_ok
        
    except Exception as e:
        print_error(f"Error leyendo migración: {e}")
        return False

def generate_test_report():
    """Genera reporte de testing"""
    print_header("🚀 GENERANDO REPORTE DE TESTING - SPRINT 2")
    
    tests = [
        ("Traducciones críticas", check_translations),
        ("Componentes React", check_react_components),
        ("Rutas en App.tsx", check_routes),
        ("Sidebar integration", check_sidebar),
        ("Servicios backend", check_backend_services),
        ("Migraciones database", check_database_migrations)
    ]
    
    results = []
    total_tests = len(tests)
    passed_tests = 0
    
    for test_name, test_func in tests:
        print(f"\n🧪 EJECUTANDO: {test_name}")
        try:
            if test_func():
                results.append((test_name, "✅ PASÓ"))
                passed_tests += 1
            else:
                results.append((test_name, "❌ FALLÓ"))
        except Exception as e:
            results.append((test_name, f"❌ ERROR: {str(e)}"))
    
    # Mostrar resumen
    print_header("📊 RESUMEN DE TESTING")
    
    for test_name, result in results:
        print(f"{result} {test_name}")
    
    print(f"\n🎯 RESULTADO: {passed_tests}/{total_tests} tests pasaron")
    
    if passed_tests == total_tests:
        print_success("¡TODOS LOS TESTS PASARON! 🎉")
        print("\n🚀 SISTEMA LISTO PARA:")
        print("  1. Testing de integración con servicios corriendo")
        print("  2. Demo al CEO")
        print("  3. Deployment a producción")
    else:
        print_error(f"{total_tests - passed_tests} tests fallaron")
        print("\n🔧 ACCIONES REQUERIDAS:")
        print("  1. Corregir los tests que fallaron")
        print("  2. Volver a ejecutar testing")
        print("  3. Solo proceder a demo cuando todos pasen")
    
    # Guardar reporte
    report_path = "sprint2_test_report.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# 📊 REPORTE DE TESTING - SPRINT 2\n\n")
        f.write(f"**Fecha:** 27 de Febrero 2026\n")
        f.write(f"**Resultado:** {passed_tests}/{total_tests} tests pasaron\n\n")
        
        f.write("## 🧪 RESULTADOS POR TEST:\n")
        for test_name, result in results:
            f.write(f"- {result} {test_name}\n")
        
        f.write("\n## 🚀 RECOMENDACIONES:\n")
        if passed_tests == total_tests:
            f.write("✅ **SISTEMA LISTO PARA DEMO Y DEPLOYMENT**\n")
            f.write("1. Iniciar servicios backend (PostgreSQL, Redis, FastAPI)\n")
            f.write("2. Iniciar frontend development server\n")
            f.write("3. Ejecutar testing de integración manual\n")
            f.write("4. Preparar demo para el CEO\n")
            f.write("5. Planificar deployment a producción\n")
        else:
            f.write("⚠️ **CORREGIR ISSUES ANTES DE CONTINUAR**\n")
            f.write("1. Revisar logs de tests fallidos\n")
            f.write("2. Corregir archivos problemáticos\n")
            f.write("3. Volver a ejecutar testing\n")
            f.write("4. Solo proceder cuando todos los tests pasen\n")
    
    print_success(f"Reporte guardado en: {report_path}")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    # Cambiar al directorio del proyecto
    project_root = "/home/node/.openclaw/workspace/projects/crmventas"
    os.chdir(project_root)
    
    print("🚀 INICIANDO TESTING AUTOMATIZADO - SPRINT 2")
    print("Sistema de Control CEO sobre Vendedores")
    print(f"Directorio: {project_root}")
    
    success = generate_test_report()
    
    if success:
        print("\n🎉 ¡SPRINT 2 AVANZANDO CORRECTAMENTE!")
        print("Próximo paso: Testing de integración con servicios corriendo")
    else:
        print("\n🔧 ¡CORREGIR ISSUES ANTES DE CONTINUAR!")
        print("Revisar el reporte para ver qué tests fallaron")