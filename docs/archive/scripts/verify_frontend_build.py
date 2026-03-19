#!/usr/bin/env python3
"""
Script para verificar problemas de build del frontend
"""

import os
import re

def check_jsx_syntax(filepath):
    """Verificar sintaxis JSX básica"""
    print(f"🔍 Checking JSX syntax: {filepath}")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    issues = []
    
    # 1. Contar fragment tags
    fragment_open = len(re.findall(r'<>', content))
    fragment_close = len(re.findall(r'</>', content))
    
    if fragment_open != fragment_close:
        issues.append(f"Fragment tags unbalanced: {fragment_open} openings, {fragment_close} closings")
    
    # 2. Buscar )} dentro de JSX (problema común)
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if ')}' in line:
            # Verificar si está dentro de un tag JSX
            # Buscar si hay < antes de )} y > después
            parts = line.split(')}')
            for j, part in enumerate(parts):
                if '<' in part and '>' in part:
                    # Verificar si )} está entre tags
                    tag_start = part.rfind('<')
                    tag_end = part.find('>', tag_start)
                    if tag_start != -1 and tag_end != -1:
                        # Verificar si hay otro )} después
                        if j < len(parts) - 1:
                            issues.append(f"Line {i+1}: Possible ){'}'} inside JSX element")
                            break
    
    # 3. Verificar tags desbalanceados (simplificado)
    # Contar div openings y closings
    div_open = len(re.findall(r'<div[^>]*>', content))
    div_close = len(re.findall(r'</div>', content))
    
    if div_open != div_close:
        issues.append(f"Div tags unbalanced: {div_open} openings, {div_close} closings")
    
    # 4. Buscar problemas específicos reportados en el error
    error_patterns = [
        (r'Unexpected closing fragment tag', 'Fragment closing without opening'),
        (r'Unexpected closing "div" tag', 'Div closing without opening'),
        (r'The character "}" is not valid', 'Invalid } character in JSX'),
        (r'Expected ":" but found ";"', 'Syntax error in JSX/TSX'),
    ]
    
    for pattern, description in error_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            issues.append(f"Possible {description}")
    
    if issues:
        print(f"  ⚠️  Issues found:")
        for issue in issues:
            print(f"    • {issue}")
        return False
    else:
        print(f"  ✅ No obvious JSX syntax issues")
        return True

def check_typescript_errors(filepath):
    """Verificar errores TypeScript comunes"""
    print(f"🔍 Checking TypeScript patterns: {filepath}")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    issues = []
    
    # 1. Verificar imports faltantes
    # Buscar uso de componentes sin import
    component_patterns = [
        r'<SellerBadge',
        r'<SellerSelector',
        r'<NotificationBell',
        r'<NotificationCenter',
        r'<AssignmentHistory',
        r'<SellerMetricsDashboard',
    ]
    
    for pattern in component_patterns:
        if re.search(pattern, content):
            # Verificar si está importado
            import_pattern = pattern.replace('<', '').replace(' ', '')
            if import_pattern not in content[:500]:  # Buscar en primeros 500 chars (donde están los imports)
                issues.append(f"Component {import_pattern} used but may not be imported")
    
    # 2. Verificar hooks de React
    hook_patterns = [
        r'useState\(',
        r'useEffect\(',
        r'useContext\(',
        r'useRef\(',
    ]
    
    for pattern in hook_patterns:
        if re.search(pattern, content):
            # Verificar import de React
            if 'import React' not in content[:200] and 'from "react"' not in content[:200]:
                issues.append(f"Hook {pattern} used but React may not be imported")
    
    if issues:
        print(f"  ⚠️  TypeScript/React issues:")
        for issue in issues:
            print(f"    • {issue}")
        return False
    else:
        print(f"  ✅ No obvious TypeScript issues")
        return True

def analyze_build_error(log_text):
    """Analizar error de build específico"""
    print("\n🔍 ANALYZING BUILD ERROR")
    print("="*60)
    
    # Extraer líneas de error
    error_lines = []
    for line in log_text.split('\n'):
        if 'ERROR:' in line or 'error' in line.lower():
            error_lines.append(line)
    
    print(f"Found {len(error_lines)} error lines")
    
    # Buscar errores específicos
    specific_errors = []
    
    for line in error_lines:
        if 'Unexpected closing fragment tag' in line:
            specific_errors.append("Fragment tag mismatch")
        elif 'Unexpected closing "div" tag' in line:
            specific_errors.append("Div tag mismatch")
        elif 'The character "}" is not valid' in line:
            specific_errors.append("Invalid } character in JSX")
        elif 'Expected ":" but found ";"' in line:
            specific_errors.append("Syntax error (colon vs semicolon)")
        elif 'Transform failed' in line:
            specific_errors.append("JSX/TSX transformation failed")
    
    if specific_errors:
        print("Specific errors detected:")
        for error in specific_errors:
            print(f"  • {error}")
    
    # Extraer línea y archivo del primer error
    first_error = None
    for line in error_lines:
        if 'file:' in line:
            parts = line.split('file:')
            if len(parts) > 1:
                first_error = parts[1].strip()
                break
    
    if first_error:
        print(f"\nFirst error in file: {first_error}")
        
        # Extraer número de línea si está disponible
        line_match = re.search(r':(\d+):', first_error)
        if line_match:
            line_num = int(line_match.group(1))
            print(f"Error at line: {line_num}")
            
            # Leer el archivo y mostrar contexto
            filepath = first_error.split(':')[0]
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    lines = f.readlines()
                
                start = max(0, line_num - 3)
                end = min(len(lines), line_num + 2)
                
                print(f"\nContext (lines {start+1}-{end}):")
                for i in range(start, end):
                    prefix = ">>> " if i == line_num - 1 else "    "
                    print(f"{prefix}{i+1}: {lines[i].rstrip()}")
    
    return specific_errors

def main():
    print("🚀 FRONTEND BUILD VERIFICATION SCRIPT")
    print("="*60)
    
    # Archivos críticos del frontend
    critical_frontend_files = [
        "frontend_react/src/views/ChatsView.tsx",
        "frontend_react/src/views/MetaLeadsView.tsx",
        "frontend_react/src/components/NotificationBell.tsx",
        "frontend_react/src/components/NotificationCenter.tsx",
        "frontend_react/src/components/Layout.tsx",
    ]
    
    all_ok = True
    
    for filepath in critical_frontend_files:
        if not os.path.exists(filepath):
            print(f"❌ File not found: {filepath}")
            all_ok = False
            continue
        
        print(f"\n📄 {filepath}")
        print("-" * 40)
        
        # Verificar sintaxis JSX
        if not check_jsx_syntax(filepath):
            all_ok = False
        
        # Verificar TypeScript
        if not check_typescript_errors(filepath):
            all_ok = False
    
    # Mostrar error de build específico si está disponible
    build_error = """x Build failed in 6.43s
error during build:
[vite:esbuild] Transform failed with 4 errors:
/app/src/views/ChatsView.tsx:1238:10: ERROR: Unexpected closing fragment tag does not match opening "div" tag
/app/src/views/ChatsView.tsx:1245:7: ERROR: The character "}" is not valid inside a JSX element
/app/src/views/ChatsView.tsx:1287:6: ERROR: Unexpected closing "div" tag does not match opening fragment tag
/app/src/views/ChatsView.tsx:1288:3: ERROR: Expected ":" but found ";"
file: /app/src/views/ChatsView.tsx:1238:10"""
    
    analyze_build_error(build_error)
    
    print("\n" + "="*60)
    print("📋 RECOMMENDATIONS:")
    
    if not all_ok:
        print("1. ❌ Fix JSX syntax errors in files listed above")
        print("2. ❌ Check fragment and div tag balance")
        print("3. ❌ Verify TypeScript imports and hooks")
    else:
        print("1. ✅ All frontend files appear syntactically correct")
    
    print("\n🔧 QUICK FIXES FOR COMMON ERRORS:")
    print("• Fragment mismatch: Ensure every <> has matching </>")
    print('• Invalid } in JSX: Move )} outside of JSX elements')
    print("• Div/fragment mismatch: Check opening and closing tags match")
    print("• Colon vs semicolon: Check return statements and ternaries")
    
    print("\n🚀 NEXT STEPS:")
    print("1. Run: npm run build in frontend_react directory")
    print("2. Check for TypeScript errors: npx tsc --noEmit")
    print("3. Use the fix_jsx_syntax.py script for automated fixes")

if __name__ == "__main__":
    main()