#!/usr/bin/env python3
"""
Script para verificar deployment completo
"""

import os
import sys
import subprocess

def check_python_syntax(filepath):
    """Verificar sintaxis Python de un archivo"""
    print(f"🔍 Checking Python syntax: {filepath}")
    
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Intentar compilar para verificar sintaxis
        compile(content, filepath, 'exec')
        print(f"  ✅ Syntax OK")
        return True
    except SyntaxError as e:
        print(f"  ❌ Syntax error: {e}")
        print(f"    Line {e.lineno}: {e.text}")
        return False
    except Exception as e:
        print(f"  ⚠️  Other error: {e}")
        return False

def check_imports(filepath):
    """Verificar importaciones de un archivo"""
    print(f"🔍 Checking imports: {filepath}")
    
    # Extraer directorio del archivo
    dir_path = os.path.dirname(filepath)
    
    # Cambiar al directorio del archivo
    original_cwd = os.getcwd()
    os.chdir(dir_path)
    
    try:
        # Intentar importar el módulo
        module_name = os.path.basename(filepath).replace('.py', '')
        
        # Para archivos en subdirectorios, necesitamos ajustar
        if dir_path != original_cwd:
            rel_path = os.path.relpath(dir_path, original_cwd)
            module_path = rel_path.replace('/', '.')
            full_module_name = f"{module_path}.{module_name}"
        else:
            full_module_name = module_name
        
        print(f"  Attempting to import: {full_module_name}")
        
        # Intentar importar
        __import__(full_module_name)
        print(f"  ✅ Imports OK")
        return True
        
    except ImportError as e:
        print(f"  ❌ Import error: {e}")
        return False
    except SyntaxError as e:
        print(f"  ❌ Syntax error during import: {e}")
        return False
    except Exception as e:
        print(f"  ⚠️  Other error during import: {e}")
        return False
    finally:
        os.chdir(original_cwd)

def check_critical_files():
    """Verificar archivos críticos para deployment"""
    print("\n🚀 VERIFYING CRITICAL DEPLOYMENT FILES")
    print("="*60)
    
    critical_files = [
        # Backend core
        "orchestrator_service/main.py",
        "orchestrator_service/core/socket_notifications.py",
        "orchestrator_service/services/seller_notification_service.py",
        "orchestrator_service/services/scheduled_tasks.py",
        
        # Routes
        "orchestrator_service/routes/notification_routes.py",
        "orchestrator_service/routes/scheduled_tasks_routes.py",
        
        # Config
        "orchestrator_service/requirements.txt",
        "orchestrator_service/config.py",
    ]
    
    all_ok = True
    
    for filepath in critical_files:
        if not os.path.exists(filepath):
            print(f"❌ File not found: {filepath}")
            all_ok = False
            continue
        
        # Verificar sintaxis
        if not check_python_syntax(filepath):
            all_ok = False
        
        # Verificar importaciones (solo para archivos Python)
        if filepath.endswith('.py'):
            if not check_imports(filepath):
                all_ok = False
        
        print()
    
    return all_ok

def check_dependencies():
    """Verificar dependencias instaladas"""
    print("\n📦 CHECKING DEPENDENCIES")
    print("="*60)
    
    # Leer requirements.txt
    req_file = "orchestrator_service/requirements.txt"
    if not os.path.exists(req_file):
        print(f"❌ Requirements file not found: {req_file}")
        return False
    
    with open(req_file, 'r') as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    print(f"Found {len(requirements)} requirements")
    
    missing = []
    for req in requirements[:10]:  # Verificar solo las primeras 10
        package = req.split('==')[0].split('>=')[0].split('<=')[0].strip()
        
        try:
            __import__(package.replace('-', '_'))
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} - MISSING")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️  Missing dependencies: {', '.join(missing)}")
        print(f"💡 Run: pip install {' '.join(missing)}")
        return False
    
    return True

def create_minimal_deployment_package():
    """Crear paquete mínimo para deployment"""
    print("\n📦 CREATING MINIMAL DEPLOYMENT PACKAGE")
    print("="*60)
    
    # Crear directorio temporal
    import tempfile
    import shutil
    
    temp_dir = tempfile.mkdtemp(prefix="crmventas_deploy_")
    print(f"Created temp directory: {temp_dir}")
    
    # Archivos esenciales para deployment mínimo
    essential_files = [
        "orchestrator_service/main_minimal.py",
        "orchestrator_service/requirements.txt",
        "orchestrator_service/config.py",
        "orchestrator_service/db.py",
    ]
    
    # Copiar archivos
    for filepath in essential_files:
        if os.path.exists(filepath):
            dest_path = os.path.join(temp_dir, os.path.basename(filepath))
            shutil.copy2(filepath, dest_path)
            print(f"  ✅ Copied: {filepath}")
        else:
            print(f"  ⚠️  Not found: {filepath}")
    
    # Crear Dockerfile mínimo
    dockerfile_content = """FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main_minimal.py"]
"""
    
    dockerfile_path = os.path.join(temp_dir, "Dockerfile")
    with open(dockerfile_path, 'w') as f:
        f.write(dockerfile_content)
    
    print(f"  ✅ Created: Dockerfile")
    
    print(f"\n📁 Minimal deployment package created at: {temp_dir}")
    print(f"📋 Files: {os.listdir(temp_dir)}")
    
    return temp_dir

def main():
    print("🚀 DEPLOYMENT VERIFICATION SCRIPT")
    print("="*60)
    
    # 1. Verificar archivos críticos
    files_ok = check_critical_files()
    
    # 2. Verificar dependencias
    deps_ok = check_dependencies()
    
    # 3. Crear paquete mínimo si hay problemas
    if not files_ok or not deps_ok:
        print("\n⚠️  DEPLOYMENT ISSUES DETECTED")
        print("Creating minimal deployment package...")
        temp_dir = create_minimal_deployment_package()
        
        print(f"\n💡 RECOMMENDATION:")
        print(f"1. Deploy minimal version first from: {temp_dir}")
        print(f"2. Use main_minimal.py as entry point")
        print(f"3. Gradually add Sprint 2 features")
    else:
        print("\n✅ ALL CHECKS PASSED")
        print("\n🎯 DEPLOYMENT READY")
        print("You can deploy the full system.")
    
    print("\n" + "="*60)
    print("📋 NEXT STEPS:")
    print("1. Fix any syntax/import errors reported above")
    print("2. Install missing dependencies")
    print("3. Test with main_minimal.py first")
    print("4. Gradually enable Sprint 2 features")

if __name__ == "__main__":
    main()