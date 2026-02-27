#!/usr/bin/env python3
"""
Simple fix for ChatsView.tsx - Add missing divs at the end
"""

import re

def add_missing_divs(filepath, num_missing=4):
    """Agregar divs faltantes al final del componente"""
    print(f"🔧 Adding {num_missing} missing divs to {filepath}")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    lines = content.split('\n')
    
    # Encontrar el cierre del componente (último ");")
    last_close = -1
    for i in range(len(lines) - 1, -1, -1):
        if ');' in lines[i]:
            last_close = i
            break
    
    if last_close == -1:
        print("❌ Could not find component closing")
        return False
    
    print(f"  Found component closing at line {last_close + 1}")
    
    # Insertar divs faltantes antes del cierre
    for i in range(num_missing):
        lines.insert(last_close, '    </div>')
        print(f"  Added </div> before line {last_close + 1}")
        last_close += 1  # La línea se movió hacia abajo
    
    # Guardar
    with open(filepath, 'w') as f:
        f.write('\n'.join(lines))
    
    print(f"✅ Added {num_missing} closing divs")
    return True

def verify_fix(filepath):
    """Verificar que el fix funciona"""
    print(f"\n✅ Verifying fix for {filepath}...")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Contar divs
    div_open = len(re.findall(r'<div[^>]*>', content))
    div_close = len(re.findall(r'</div>', content))
    
    print(f"  Divs: {div_open} openings, {div_close} closings")
    print(f"  Difference: {div_open - div_close}")
    
    if div_open == div_close:
        print("  ✅ Divs are balanced!")
        return True
    else:
        print(f"  ❌ Still unbalanced by {abs(div_open - div_close)}")
        return False

def check_for_template_literal_issues(filepath):
    """Verificar problemas con template literals"""
    print(f"\n🔍 Checking for template literal issues...")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Contar backticks
    backticks = content.count('`')
    print(f"  Total backticks: {backticks}")
    
    if backticks % 2 != 0:
        print(f"  ⚠️  Uneven number of backticks - possible unterminated template literal")
        
        # Buscar la última línea con backtick
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if '`' in line:
                print(f"    Line {i+1}: {line.strip()[:60]}...")
        
        return False
    
    print(f"  ✅ Template literals appear balanced")
    return True

def main():
    filepath = 'frontend_react/src/views/ChatsView.tsx'
    
    print("🚀 SIMPLE FIX FOR CHATSVIEW.TSX")
    print("="*60)
    
    # 1. Verificar estado actual
    print("\n📊 Current state:")
    with open(filepath, 'r') as f:
        content = f.read()
    
    div_open = len(re.findall(r'<div[^>]*>', content))
    div_close = len(re.findall(r'</div>', content))
    print(f"  Divs: {div_open} openings, {div_close} closings")
    print(f"  Missing: {div_open - div_close} closing div(s)")
    
    # 2. Agregar divs faltantes
    missing = div_open - div_close
    if missing > 0:
        add_missing_divs(filepath, missing)
    elif missing < 0:
        print(f"\n⚠️  Has {abs(missing)} extra closing div(s)")
        print("   This is more complex to fix automatically")
    else:
        print(f"\n✅ Divs are already balanced")
    
    # 3. Verificar fix
    verify_fix(filepath)
    
    # 4. Verificar template literals
    check_for_template_literal_issues(filepath)
    
    print(f"\n📋 Next steps:")
    print(f"1. Commit and push the fix")
    print(f"2. Try deployment again")
    print(f"3. If still errors, check for other JSX issues")

if __name__ == "__main__":
    main()