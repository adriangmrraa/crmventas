#!/usr/bin/env python3
"""
Script para corregir problemas de sintaxis JSX en ChatsView.tsx
"""

import re

def analyze_jsx_issues(filepath):
    """Analizar problemas de JSX en el archivo"""
    print(f"🔍 Analyzing {filepath}...")
    
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    # Buscar problemas específicos mencionados en el error
    print("\n📋 Error messages from build:")
    print("1. Line 1238: Unexpected closing fragment tag does not match opening 'div' tag")
    print("2. Line 1245: The character '}' is not valid inside a JSX element")
    print("3. Line 1287: Unexpected closing 'div' tag does not match opening fragment tag")
    print("4. Line 1288: Expected ':' but found ';'")
    
    print("\n📄 Checking lines around errors...")
    
    # Mostrar líneas problemáticas
    problematic_lines = [1238, 1245, 1287, 1288]
    for line_num in problematic_lines:
        if line_num - 1 < len(lines):
            print(f"\nLine {line_num}: {lines[line_num-1].rstrip()}")
            # Mostrar contexto
            start = max(0, line_num - 5)
            end = min(len(lines), line_num + 5)
            print(f"Context (lines {start+1}-{end}):")
            for i in range(start, end):
                prefix = ">>> " if i == line_num - 1 else "    "
                print(f"{prefix}{i+1}: {lines[i].rstrip()}")
    
    return lines

def fix_jsx_issues(lines):
    """Corregir problemas de JSX"""
    print("\n🔧 Applying fixes...")
    
    # Convertir a lista mutable
    lines = lines.copy()
    
    # FIX 1: Línea 1238 - Problema con fragment tag
    # La línea 1238 tiene </> pero parece que debería ser </div>
    if len(lines) >= 1238:
        print(f"\nFix 1: Line 1238 - Changing '</>' to '</div>'")
        print(f"  Before: {lines[1237].rstrip()}")
        lines[1237] = lines[1237].replace('</>', '</div>')
        print(f"  After:  {lines[1237].rstrip()}")
    
    # FIX 2: Línea 1245 - Carácter '}' inválido
    # Parece que hay un )} que debería estar fuera del JSX
    if len(lines) >= 1245:
        print("\nFix 2: Line 1245 - Checking for misplaced '){}'".format('}'))
        print(f"  Before: {lines[1244].rstrip()}")
        
        # Buscar el patrón problemático
        line_1245 = lines[1244]
        if ')})' in line_1245:
            lines[1244] = line_1245.replace(')})', '})')
            print(f"  After:  {lines[1244].rstrip()}")
        elif ')}' in line_1245 and not line_1245.strip().startswith(')'):
            # Si )} está en medio de la línea, podría ser un error
            # Revisar el contexto para entender mejor
            pass
    
    # FIX 3: Línea 1287 - Closing div no coincide
    # Podría ser que falta un fragment opening tag
    if len(lines) >= 1287:
        print(f"\nFix 3: Line 1287 - Checking div/fragment mismatch")
        print(f"  Before: {lines[1286].rstrip()}")
        
        # Buscar el opening tag correspondiente
        # Necesitamos ver el contexto completo
        pass
    
    # FIX 4: Línea 1288 - Expected ':' but found ';'
    # Esto podría ser un error en la sintaxis del return
    if len(lines) >= 1288:
        print(f"\nFix 4: Line 1288 - Checking syntax error")
        print(f"  Before: {lines[1287].rstrip()}")
        
        # Si la línea es solo ");" podría ser parte del return
        if lines[1287].strip() == ');':
            # Verificar si hay un return antes
            for i in range(1287, max(0, 1287-10), -1):
                if 'return (' in lines[i-1] or 'return' in lines[i-1]:
                    print(f"  Found return statement at line {i}")
                    break
    
    return lines

def create_safe_version(filepath):
    """Crear versión segura del archivo"""
    print(f"\n🛡️ Creating safe version of {filepath}...")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Estrategia 1: Encontrar y corregir el área problemática específica
    # Basado en los errores, el problema está en la sección del conditional render
    
    # Buscar el patrón problemático
    pattern = r'(\s*</>\s*\)\s*:\s*\(\s*<div[^>]*>.*?</div>\s*\)\s*\}?)'
    
    # Reemplazar con versión corregida
    # El problema parece ser: </> ) : ( <div>...</div> )}
    # Debería ser: </div> ) : ( <div>...</div> ) }
    
    fixed_content = re.sub(
        r'(\s*)</>(\s*\)\s*:\s*\(\s*<div[^>]*>.*?</div>\s*\)\s*)\}?',
        r'\1</div>\2 }',
        content,
        flags=re.DOTALL
    )
    
    # También corregir cualquier )} suelto dentro de JSX
    fixed_content = re.sub(
        r'(<[^>]*>)\s*\)\s*\}',
        r'\1 }',
        fixed_content
    )
    
    # Guardar versión corregida
    backup_path = filepath + '.backup'
    with open(backup_path, 'w') as f:
        f.write(content)
    print(f"  Backup saved to: {backup_path}")
    
    with open(filepath, 'w') as f:
        f.write(fixed_content)
    
    print(f"  Fixed version saved to: {filepath}")
    
    return fixed_content

def verify_fix(filepath):
    """Verificar que el fix funciona"""
    print(f"\n✅ Verifying fix for {filepath}...")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Verificar problemas comunes
    issues = []
    
    # 1. Fragment tags desbalanceados
    fragment_open = content.count('<>')
    fragment_close = content.count('</>')
    if fragment_open != fragment_close:
        issues.append(f"Fragment tags unbalanced: {fragment_open} openings, {fragment_close} closings")
    
    # 2. Buscar )} dentro de tags JSX
    # Esto es complejo, hacemos una verificación simple
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if ')}' in line and '<' in line and '>' in line:
            # Verificar si )} está dentro de un tag
            parts = line.split(')}')
            for part in parts:
                if '<' in part and '>' in part and part.index('<') < part.index('>'):
                    issues.append(f"Line {i+1}: Possible )} inside JSX element")
                    break
    
    if issues:
        print("⚠️  Potential issues found:")
        for issue in issues:
            print(f"  • {issue}")
    else:
        print("✅ No obvious JSX syntax issues found")
    
    return len(issues) == 0

def main():
    filepath = 'frontend_react/src/views/ChatsView.tsx'
    
    print("🚀 JSX SYNTAX FIX SCRIPT")
    print("="*60)
    
    # 1. Analizar problemas
    lines = analyze_jsx_issues(filepath)
    
    # 2. Crear versión segura
    create_safe_version(filepath)
    
    # 3. Verificar fix
    if verify_fix(filepath):
        print("\n🎉 JSX syntax should be fixed!")
        print("\n📋 Next steps:")
        print("1. Commit the fixed file: git add frontend_react/src/views/ChatsView.tsx")
        print("2. Push to GitHub: git push origin main")
        print("3. Redeploy on Easypanel")
    else:
        print("\n⚠️  Some issues may still exist")
        print("💡 Consider:")
        print("  • Running a TypeScript compiler check: npx tsc --noEmit")
        print("  • Using a JSX linter")
        print("  • Manually reviewing the problematic sections")

if __name__ == "__main__":
    main()