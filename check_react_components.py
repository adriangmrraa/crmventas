#!/usr/bin/env python3
"""
Verificar componentes React creados para el sistema de vendedores
"""
import os
import re

def check_file(filepath):
    """Verificar un archivo TypeScript/React"""
    print(f"\n🔍 Verificando: {filepath}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar imports
        imports = re.findall(r'import\s+.*?from\s+[\'"](.*?)[\'"]', content)
        if imports:
            print(f"   📦 Imports: {len(imports)}")
            for imp in imports[:3]:
                print(f"      → {imp}")
            if len(imports) > 3:
                print(f"      ... y {len(imports) - 3} más")
        
        # Verificar componentes definidos
        components = re.findall(r'(?:export\s+)?(?:default\s+)?(?:class|const|function)\s+(\w+)\s*(?:<.*?>)?\s*(?:extends\s+\w+)?\s*[{(]', content)
        if components:
            print(f"   🏗️  Componentes: {', '.join(components)}")
        
        # Verificar hooks
        hooks = re.findall(r'\b(useState|useEffect|useContext|useRef|useMemo|useCallback)\b', content)
        if hooks:
            print(f"   🪝 Hooks: {', '.join(set(hooks))}")
        
        # Verificar errores comunes
        errors = []
        
        # JSX no cerrado
        jsx_tags = re.findall(r'<(\w+)(?:\s+[^>]*)?>(?!.*</\1>)', content, re.DOTALL)
        if jsx_tags:
            errors.append(f"JSX no cerrado: {set(jsx_tags)}")
        
        # Template literals mal formados
        template_errors = re.findall(r'\${[^}]*$', content, re.MULTILINE)
        if template_errors:
            errors.append("Template literals mal formados")
        
        if errors:
            print(f"   ❌ Posibles errores: {errors}")
            return False
        else:
            print(f"   ✅ Sintaxis OK")
            return True
            
    except Exception as e:
        print(f"   ❌ Error leyendo archivo: {e}")
        return False

def main():
    """Función principal"""
    print("🧪 VERIFICACIÓN DE COMPONENTES REACT - SISTEMA DE VENDEDORES")
    print("=" * 60)
    
    frontend_dir = "frontend_react/src"
    
    # Componentes creados
    seller_components = [
        "components/SellerBadge.tsx",
        "components/SellerSelector.tsx", 
        "components/AssignmentHistory.tsx",
        "components/SellerMetricsDashboard.tsx"
    ]
    
    # Archivos modificados
    modified_files = [
        "views/ChatsView.tsx",
        "locales/es.json"
    ]
    
    all_files = seller_components + modified_files
    
    results = []
    for file in all_files:
        filepath = os.path.join(frontend_dir, file)
        if os.path.exists(filepath):
            ok = check_file(filepath)
            results.append((file, ok))
        else:
            print(f"\n❌ Archivo no encontrado: {filepath}")
            results.append((file, False))
    
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE VERIFICACIÓN")
    print("=" * 60)
    
    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    failed = total - passed
    
    print(f"Total archivos: {total}")
    print(f"✅ Correctos: {passed}")
    print(f"❌ Con problemas: {failed}")
    
    if failed > 0:
        print("\n📋 Archivos con problemas:")
        for file, ok in results:
            if not ok:
                print(f"   ❌ {file}")
    
    # Verificar integración en App.tsx
    print("\n🔍 VERIFICANDO INTEGRACIÓN EN App.tsx...")
    app_path = os.path.join(frontend_dir, "App.tsx")
    if os.path.exists(app_path):
        with open(app_path, 'r', encoding='utf-8') as f:
            app_content = f.read()
        
        # Verificar si ChatsView está importado
        if "ChatsView" in app_content:
            print("   ✅ ChatsView está importado en App.tsx")
        else:
            print("   ⚠️  ChatsView no encontrado en App.tsx")
        
        # Verificar rutas
        if "path=\"chats\"" in app_content or "path=\"conversations\"" in app_content:
            print("   ✅ Ruta de chats configurada")
        else:
            print("   ⚠️  Ruta de chats no encontrada")
    else:
        print("   ❌ App.tsx no encontrado")
    
    print("\n" + "=" * 60)
    if failed == 0:
        print("🎉 TODOS LOS COMPONENTES ESTÁN CORRECTOS!")
        print("✅ Sistema listo para desarrollo frontend")
    else:
        print("⚠️  ALGUNOS COMPONENTES NECESITAN REVISIÓN")
        print("❌ Corregir los errores antes de continuar")
    
    print("\n📋 RECOMENDACIONES:")
    print("1. Ejecutar 'npm install' en frontend_react/")
    print("2. Ejecutar 'npm run dev' para desarrollo")
    print("3. Verificar que los componentes se rendericen correctamente")
    print("4. Probar la funcionalidad de asignación de vendedores")

if __name__ == "__main__":
    main()