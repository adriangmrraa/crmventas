#!/usr/bin/env python3
"""
Script para verificar importaciones en el proyecto
"""

import sys
import os

# Agregar el directorio del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'orchestrator_service'))

def test_imports():
    """Probar todas las importaciones críticas"""
    print("🔍 Testing imports...")
    print("="*60)
    
    imports_to_test = [
        # Core imports
        ("core.socket_notifications", "register_notification_socket_handlers"),
        ("core.socket_manager", "sio"),
        
        # Services imports
        ("services.seller_notification_service", "notification_service"),
        ("services.seller_metrics_service", "seller_metrics_service"),
        ("services.scheduled_tasks", "scheduled_tasks_service"),
        ("services.seller_assignment_service", "seller_assignment_service"),
        
        # Routes imports
        ("routes.health_routes", "router as health_router"),
        ("routes.notification_routes", "router as notification_router"),
        ("routes.scheduled_tasks_routes", "router as scheduled_tasks_router"),
        ("routes.seller_routes", "router as seller_router"),
        
        # Main app
        ("main", "app"),
    ]
    
    failed_imports = []
    
    for module_path, import_name in imports_to_test:
        try:
            if ' as ' in import_name:
                # Handle aliased imports
                actual_import = import_name.split(' as ')[0].strip()
            else:
                actual_import = import_name
            
            print(f"Testing: {module_path}.{actual_import}")
            
            # Try absolute import
            module = __import__(module_path, fromlist=[actual_import])
            imported = getattr(module, actual_import)
            
            print(f"  ✅ Success: {type(imported).__name__}")
            
        except ImportError as e:
            print(f"  ❌ ImportError: {e}")
            failed_imports.append((module_path, import_name, str(e)))
        except AttributeError as e:
            print(f"  ❌ AttributeError: {e}")
            failed_imports.append((module_path, import_name, str(e)))
        except Exception as e:
            print(f"  ❌ Unexpected error: {e}")
            failed_imports.append((module_path, import_name, str(e)))
    
    print("\n" + "="*60)
    print("📊 RESULTS:")
    
    if failed_imports:
        print(f"❌ {len(failed_imports)} imports failed:")
        for module_path, import_name, error in failed_imports:
            print(f"  • {module_path}.{import_name}: {error}")
        
        print("\n🔧 RECOMMENDATIONS:")
        for module_path, import_name, error in failed_imports:
            if 'relative import' in error or 'beyond top-level' in error:
                print(f"  • Fix relative import in {module_path}")
            elif 'No module named' in error:
                print(f"  • Check module exists: {module_path}")
        
        return False
    else:
        print("✅ All imports successful!")
        return True

def test_specific_problematic_imports():
    """Test específico para importaciones problemáticas"""
    print("\n🔧 Testing problematic imports...")
    print("="*60)
    
    # Test the specific problematic import
    print("Testing: from services.seller_notification_service import notification_service")
    try:
        from services.seller_notification_service import notification_service
        print("  ✅ Success (absolute import)")
    except ImportError as e:
        print(f"  ❌ Absolute import failed: {e}")
        
        print("\nTrying: from ..services.seller_notification_service import notification_service")
        try:
            # This would only work if run from core/ directory
            import os
            os.chdir('orchestrator_service/core')
            from ..services.seller_notification_service import notification_service
            print("  ✅ Success (relative import from core/)")
            os.chdir('../..')
        except Exception as e2:
            print(f"  ❌ Relative import failed: {e2}")
            os.chdir('../..')
    
    # Test socket_notifications module directly
    print("\nTesting socket_notifications module...")
    try:
        from core.socket_notifications import register_notification_socket_handlers
        print("  ✅ socket_notifications imports successfully")
    except Exception as e:
        print(f"  ❌ socket_notifications import failed: {e}")

def check_python_path():
    """Verificar Python path"""
    print("\n📁 Python Path:")
    for i, path in enumerate(sys.path[:10]):  # Show first 10
        print(f"  {i}: {path}")

if __name__ == "__main__":
    print("🚀 IMPORT TEST SCRIPT")
    print("Testing imports for orchestrator_service")
    print("="*60)
    
    check_python_path()
    
    if test_imports():
        print("\n🎉 All imports are working correctly!")
        sys.exit(0)
    else:
        test_specific_problematic_imports()
        print("\n⚠️  Some imports failed. Check recommendations above.")
        sys.exit(1)