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
    
    # Count normal opens: <div ... > (not ending in />)
    # This is tricky with regex. Let's use a stack approach.
    
    stack = 0
    # Find all div related tokens
    # 1. <div ... /> (self-closing)
    # 2. <div ... > (opening)
    # 3. </div> (closing)
    
    tokens = re.findall(r'<(div\b[^>]*?/?>)|(</div\s*>)', content)
    for t_open, t_close in tokens:
        if t_open:
            if t_open.endswith('/>'):
                # Self-closing, balances itself
                pass
            else:
                stack += 1
        else:
            stack -= 1
            
    if stack != 0:
        print(f"UNBALANCED: {os.path.basename(filepath)} (Net: {stack})")
    else:
        # print(f"OK: {os.path.basename(filepath)}")
        pass

print("Audit complete.")
