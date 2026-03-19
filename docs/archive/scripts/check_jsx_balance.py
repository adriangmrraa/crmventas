#!/usr/bin/env python3
"""
Verificar balance de tags JSX
"""

import re

def check_jsx_balance(filepath):
    """Verificar que los tags JSX estén balanceados"""
    print(f"🔍 Checking JSX balance in {filepath}")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Contar fragment tags
    fragment_open = len(re.findall(r'<>', content))
    fragment_close = len(re.findall(r'</>', content))
    
    print(f"\n📊 Fragment tags:")
    print(f"  Opening <>: {fragment_open}")
    print(f"  Closing </>: {fragment_close}")
    print(f"  Balance: {'✅' if fragment_open == fragment_close else '❌'}")
    
    if fragment_open != fragment_close:
        print(f"  ⚠️  Unbalanced by {abs(fragment_open - fragment_close)}")
    
    # Encontrar líneas con fragment tags
    lines = content.split('\n')
    print(f"\n📍 Fragment tag locations:")
    
    for i, line in enumerate(lines):
        if '<>' in line:
            print(f"  Line {i+1}: Opening fragment")
        if '</>' in line:
            print(f"  Line {i+1}: Closing fragment")
    
    # Verificar div tags (simplificado)
    div_open = len(re.findall(r'<div[^>]*>', content))
    div_close = len(re.findall(r'</div>', content))
    
    print(f"\n📊 Div tags:")
    print(f"  Opening <div>: {div_open}")
    print(f"  Closing </div>: {div_close}")
    print(f"  Balance: {'✅' if div_open == div_close else '❌'}")
    
    # Verificar problemas comunes
    print(f"\n🔍 Common JSX issues:")
    
    # 1. )} dentro de JSX
    for i, line in enumerate(lines):
        if ')}' in line:
            # Verificar si está dentro de JSX
            parts = line.split(')}')
            for part in parts:
                if '<' in part and '>' in part:
                    # Verificar si )} está entre tags
                    tag_start = part.rfind('<')
                    tag_end = part.find('>', tag_start)
                    if tag_start != -1 and tag_end != -1:
                        print(f"  Line {i+1}: Possible ){'}'} inside JSX element")
                        print(f"    Context: {line.strip()}")
                        break
    
    # 2. Fragment dentro de fragment (anidamiento)
    # Simplificado: buscar patrones problemáticos
    if re.search(r'<>.*<>.*</>.*</>', content, re.DOTALL):
        print("  ⚠️  Nested fragments detected")
    
    return fragment_open == fragment_close and div_open == div_close

def test_build():
    """Probar si el archivo compila"""
    import subprocess
    import os
    
    print(f"\n🚀 Testing build...")
    
    # Cambiar al directorio frontend
    original_dir = os.getcwd()
    frontend_dir = os.path.join(original_dir, 'frontend_react')
    
    if os.path.exists(frontend_dir):
        os.chdir(frontend_dir)
        
        # Verificar TypeScript
        print("  Running TypeScript check...")
        result = subprocess.run(['npx', 'tsc', '--noEmit', '--skipLibCheck'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("  ✅ TypeScript check passed")
        else:
            print("  ❌ TypeScript errors:")
            print(result.stdout)
            print(result.stderr)
        
        os.chdir(original_dir)
    else:
        print(f"  ⚠️  Frontend directory not found: {frontend_dir}")

def main():
    filepath = 'frontend_react/src/views/ChatsView.tsx'
    
    print("🚀 JSX BALANCE CHECK")
    print("="*60)
    
    if check_jsx_balance(filepath):
        print("\n✅ JSX tags appear to be balanced")
    else:
        print("\n⚠️  JSX tags are unbalanced")
    
    # Probar build
    test_build()
    
    print("\n" + "="*60)
    print("📋 RECOMMENDATIONS:")
    print("1. Ensure all <> have matching </>")
    print("2. Ensure all <div> have matching </div>")
    print("3. Check for )} inside JSX elements")
    print("4. Run: npx tsc --noEmit to check TypeScript")
    print("5. Run: npm run build to test compilation")

if __name__ == "__main__":
    main()