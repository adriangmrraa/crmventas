import re
import os

modules_path = r'e:\Antigravity Projects\estabilizacion\CRM VENTAS\frontend_react\src\modules'
view_files = []

for root, dirs, files in os.walk(modules_path):
    for file in files:
        if file.endswith('View.tsx'):
            view_files.append(os.path.join(root, file))

for filepath in view_files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    opens = len(re.findall(r'<div\b', content))
    closes = len(re.findall(r'</div\s*>', content))
    
    if opens != closes:
        print(f"UNBALANCED: {os.path.basename(filepath)} (Opens: {opens}, Closes: {closes})")
    else:
        # print(f"OK: {os.path.basename(filepath)}")
        pass

print("Audit complete.")
