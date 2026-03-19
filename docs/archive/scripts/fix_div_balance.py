#!/usr/bin/env python3
"""
Script para encontrar y corregir desbalance de divs en ChatsView.tsx
"""

import re

def analyze_div_balance(filepath):
    """Analizar balance de divs en un archivo"""
    print(f"🔍 Analyzing div balance in {filepath}")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Encontrar todas las líneas con divs
    lines = content.split('\n')
    
    div_stack = []
    line_numbers = []
    
    for i, line in enumerate(lines):
        # Buscar div openings
        div_open_matches = list(re.finditer(r'<div[^>]*>', line))
        for match in div_open_matches:
            div_stack.append(('open', i+1, match.group()))
            line_numbers.append(i+1)
        
        # Buscar div closings
        div_close_matches = list(re.finditer(r'</div>', line))
        for match in div_close_matches:
            if div_stack and div_stack[-1][0] == 'open':
                div_stack.pop()
            else:
                div_stack.append(('close', i+1, '</div>'))
            line_numbers.append(i+1)
        
        # Buscar fragment openings
        if '<>' in line:
            div_stack.append(('fragment_open', i+1, '<>'))
            line_numbers.append(i+1)
        
        # Buscar fragment closings
        if '</>' in line:
            if div_stack and div_stack[-1][0] == 'fragment_open':
                div_stack.pop()
            else:
                div_stack.append(('fragment_close', i+1, '</>'))
            line_numbers.append(i+1)
    
    print(f"\n📊 Stack analysis:")
    print(f"  Remaining in stack: {len(div_stack)} items")
    
    if div_stack:
        print(f"\n⚠️  Unbalanced tags:")
        for tag_type, line_num, tag in div_stack:
            print(f"  Line {line_num}: {tag_type} - {tag}")
        
        # Mostrar contexto para los primeros 5 problemas
        print(f"\n📍 Context for first 5 issues:")
        for i, (tag_type, line_num, tag) in enumerate(div_stack[:5]):
            print(f"\n  Issue {i+1} at line {line_num}:")
            start = max(0, line_num - 3)
            end = min(len(lines), line_num + 2)
            for j in range(start, end):
                prefix = ">>> " if j == line_num - 1 else "    "
                print(f"{prefix}{j+1}: {lines[j]}")
    
    return div_stack, lines

def fix_div_balance(filepath, div_stack, lines):
    """Intentar corregir el desbalance de divs"""
    print(f"\n🔧 Attempting to fix div balance...")
    
    if not div_stack:
        print("  ✅ No balancing issues found")
        return lines
    
    # Crear copia de las líneas
    fixed_lines = lines.copy()
    
    # Estrategia 1: Agregar divs faltantes al final
    open_count = sum(1 for tag_type, _, _ in div_stack if tag_type in ['open', 'fragment_open'])
    close_count = sum(1 for tag_type, _, _ in div_stack if tag_type in ['close', 'fragment_close'])
    
    diff = open_count - close_count
    
    if diff > 0:
        # Faltan divs de cierre
        print(f"  Missing {diff} closing div(s)")
        
        # Encontrar el último return statement
        last_return_line = -1
        for i, line in enumerate(reversed(fixed_lines)):
            if 'return (' in line:
                last_return_line = len(fixed_lines) - i - 1
                break
        
        if last_return_line != -1:
            # Insertar divs de cierre antes del último return
            for _ in range(diff):
                # Buscar dónde insertar (antes del cierre del componente)
                insert_line = last_return_line
                while insert_line < len(fixed_lines) and ');' not in fixed_lines[insert_line]:
                    insert_line += 1
                
                if insert_line < len(fixed_lines):
                    fixed_lines.insert(insert_line, '    </div>')
                    print(f"  Added </div> at line {insert_line + 1}")
    
    elif diff < 0:
        # Faltan divs de apertura
        print(f"  Missing {-diff} opening div(s)")
        # Esto es más complejo, necesitaríamos análisis más profundo
    
    return fixed_lines

def create_safe_version(filepath):
    """Crear versión segura del archivo"""
    print(f"\n🛡️ Creating safe version of {filepath}...")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Estrategia conservadora: Asegurar que el componente cierra correctamente
    # Buscar el return principal
    lines = content.split('\n')
    
    # Encontrar el return principal
    main_return_line = -1
    for i, line in enumerate(lines):
        if 'return (' in line and 'const' not in line and 'function' not in line:
            main_return_line = i
            break
    
    if main_return_line != -1:
        print(f"  Found main return at line {main_return_line + 1}")
        
        # Contar divs desde el return hasta el final
        div_count = 0
        for i in range(main_return_line, len(lines)):
            div_open = len(re.findall(r'<div[^>]*>', lines[i]))
            div_close = len(re.findall(r'</div>', lines[i]))
            div_count += div_open - div_close
        
        print(f"  Div balance from return to end: {div_count}")
        
        if div_count > 0:
            # Faltan divs de cierre
            # Encontrar el cierre del componente
            closing_line = -1
            for i in range(len(lines) - 1, main_return_line, -1):
                if ');' in lines[i]:
                    closing_line = i
                    break
            
            if closing_line != -1:
                # Agregar divs faltantes
                for _ in range(div_count):
                    lines.insert(closing_line, '    </div>')
                    print(f"  Added </div> before line {closing_line + 1}")
    
    # Guardar versión corregida
    backup_path = filepath + '.backup'
    with open(backup_path, 'w') as f:
        f.write(content)
    print(f"  Backup saved to: {backup_path}")
    
    fixed_content = '\n'.join(lines)
    with open(filepath, 'w') as f:
        f.write(fixed_content)
    
    print(f"  Fixed version saved to: {filepath}")
    
    return fixed_content

def main():
    filepath = 'frontend_react/src/views/ChatsView.tsx'
    
    print("🚀 DIV BALANCE FIX SCRIPT")
    print("="*60)
    
    # 1. Analizar balance
    div_stack, lines = analyze_div_balance(filepath)
    
    # 2. Crear versión segura
    create_safe_version(filepath)
    
    # 3. Verificar después del fix
    print(f"\n✅ Verification after fix:")
    with open(filepath, 'r') as f:
        content = f.read()
    
    div_open = len(re.findall(r'<div[^>]*>', content))
    div_close = len(re.findall(r'</div>', content))
    frag_open = len(re.findall(r'<>', content))
    frag_close = len(re.findall(r'</>', content))
    
    print(f"  Divs: {div_open} openings, {div_close} closings")
    print(f"  Fragments: {frag_open} openings, {frag_close} closings")
    
    if div_open == div_close and frag_open == frag_close:
        print(f"\n🎉 All tags are balanced!")
    else:
        print(f"\n⚠️  Still unbalanced:")
        if div_open != div_close:
            print(f"  Divs: {abs(div_open - div_close)} difference")
        if frag_open != frag_close:
            print(f"  Fragments: {abs(frag_open - frag_close)} difference")
    
    print(f"\n📋 Next steps:")
    print(f"1. Test build: npm run build in frontend_react directory")
    print(f"2. If still errors, check specific lines mentioned above")
    print(f"3. Consider manual review of JSX structure")

if __name__ == "__main__":
    main()