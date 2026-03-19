#!/usr/bin/env python3
"""
Debug script para encontrar divs faltantes
"""

import re

def find_div_issues(filepath):
    """Encontrar problemas específicos con divs"""
    print(f"🔍 Analyzing {filepath}")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    lines = content.split('\n')
    
    # Encontrar todos los divs con números de línea
    divs = []
    for i, line in enumerate(lines):
        # Div openings
        for match in re.finditer(r'<div[^>]*>', line):
            divs.append(('open', i+1, match.group()))
        
        # Div closings
        for match in re.finditer(r'</div>', line):
            divs.append(('close', i+1, '</div>'))
    
    # Simular stack para encontrar desmatches
    stack = []
    issues = []
    
    for tag_type, line_num, tag in divs:
        if tag_type == 'open':
            stack.append((line_num, tag))
        else:  # close
            if stack:
                stack.pop()
            else:
                issues.append(f"Extra closing div at line {line_num}")
    
    # Los que quedan en el stack son openings sin cerrar
    for line_num, tag in stack:
        issues.append(f"Unclosed div at line {line_num}: {tag}")
    
    print(f"\n📊 Total divs: {len(divs)}")
    print(f"  Openings: {sum(1 for t,_,_ in divs if t == 'open')}")
    print(f"  Closings: {sum(1 for t,_,_ in divs if t == 'close')}")
    
    if issues:
        print(f"\n⚠️  Issues found:")
        for issue in issues:
            print(f"  • {issue}")
        
        # Mostrar contexto para los primeros 3 issues
        print(f"\n📍 Context for issues:")
        for i, issue in enumerate(issues[:3]):
            print(f"\n  Issue {i+1}: {issue}")
            # Extraer número de línea
            line_match = re.search(r'line (\d+)', issue)
            if line_match:
                line_num = int(line_match.group(1))
                start = max(0, line_num - 3)
                end = min(len(lines), line_num + 2)
                for j in range(start, end):
                    prefix = ">>> " if j == line_num - 1 else "    "
                    print(f"{prefix}{j+1}: {lines[j]}")
    
    return issues

def check_template_literals(filepath):
    """Verificar template literals (backticks)"""
    print(f"\n🔍 Checking template literals in {filepath}")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    lines = content.split('\n')
    
    # Contar backticks
    backticks = content.count('`')
    print(f"  Total backticks: {backticks}")
    
    if backticks % 2 != 0:
        print(f"  ⚠️  Uneven number of backticks ({backticks}) - possible unterminated template literal")
    
    # Buscar líneas con backticks
    for i, line in enumerate(lines):
        if '`' in line:
            print(f"  Line {i+1}: {line.count('`')} backtick(s) - {line.strip()[:50]}...")
    
    # Buscar problemas específicos con regex
    for i, line in enumerate(lines):
        if '/' in line and '`' in line:
            # Verificar si hay un / cerca de un backtick que podría confundir al parser
            parts = line.split('`')
            for j, part in enumerate(parts):
                if '/' in part and j % 2 == 1:  # Dentro de template literal
                    print(f"  ⚠️  Line {i+1}: / character inside template literal at position {part.find('/')}")

def main():
    filepath = 'frontend_react/src/views/ChatsView.tsx'
    
    print("🚀 DIV DEBUG SCRIPT")
    print("="*60)
    
    # 1. Encontrar problemas con divs
    issues = find_div_issues(filepath)
    
    # 2. Verificar template literals
    check_template_literals(filepath)
    
    # 3. Contar estructura general
    print(f"\n📊 Structure summary:")
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Contar returns (componentes)
    returns = len(re.findall(r'return \(', content))
    print(f"  Return statements: {returns}")
    
    # Buscar el componente principal
    component_match = re.search(r'export default function (\w+)', content)
    if component_match:
        print(f"  Component name: {component_match.group(1)}")
    
    print(f"\n📋 Recommendations:")
    if issues:
        print("1. Fix div issues listed above")
        print("2. Check template literals for unclosed backticks")
        print("3. Verify JSX structure is properly nested")
    else:
        print("1. No obvious div issues found")
        print("2. Check for other JSX syntax errors")

if __name__ == "__main__":
    main()