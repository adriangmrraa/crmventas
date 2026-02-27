import re

filepath = r'e:\Antigravity Projects\estabilizacion\CRM VENTAS\frontend_react\src\components\Layout.tsx'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Strip comments
content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
content = re.sub(r'//.*', '', content)

stack = []
matches = re.finditer(r'<(div\b[^>]*?(?<!/)>)|(</div\s*>)', content, flags=re.DOTALL)

for m in matches:
    if m.group(1): # Open
        line_num = content.count('\n', 0, m.start()) + 1
        stack.append((line_num, m.group(0)))
    else: # Close
        if not stack:
            line_num = content.count('\n', 0, m.start()) + 1
            print(f"Extra Close at L{line_num}")
        else:
            stack.pop()

if not stack:
    print("Balanced!")
else:
    for line_num, tag in stack:
        print(f"Unclosed Open from L{line_num}: {tag[:50]}...")
