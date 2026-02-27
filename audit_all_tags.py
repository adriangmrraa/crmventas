import re
import os

src_path = r'e:\Antigravity Projects\estabilizacion\CRM VENTAS\frontend_react\src'
total_unbalanced = 0

for root, dirs, files in os.walk(src_path):
    for file in files:
        if file.endswith('.tsx') or file.endswith('.jsx'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            stack = 0
            # A bit more robust regex for div tags
            # Matches <div...>, <div.../>, and </div>
            tokens = re.findall(r'<(div\b[^>]*?/?>)|(</div\s*>)', content)
            for t_open, t_close in tokens:
                if t_open:
                    if t_open.endswith('/>'):
                        pass
                    else:
                        stack += 1
                else:
                    stack -= 1
            
            if stack != 0:
                print(f"UNBALANCED: {os.path.relpath(filepath, src_path)} (Net: {stack})")
                total_unbalanced += 1

print(f"Audit complete. Total unbalanced files: {total_unbalanced}")
