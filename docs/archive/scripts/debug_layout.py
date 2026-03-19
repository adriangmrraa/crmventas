import re

filepath = r'e:\Antigravity Projects\estabilizacion\CRM VENTAS\frontend_react\src\components\Layout.tsx'

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines, 1):
    tokens = re.findall(r'<(div\b[^>]*?/?>)|(</div\s*>)', line)
    for t_open, t_close in tokens:
        if t_open:
            if t_open.endswith('/>'):
                print(f"L{i}: SELF-CLOSE DIV")
            else:
                print(f"L{i}: OPEN DIV")
        else:
            print(f"L{i}: CLOSE DIV")
