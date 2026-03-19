import re

def audit_details(filepath):
    print(f"Auditing: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Strip comments
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    content = re.sub(r'//.*', '', content)
    
    stack = []
    # Match <div (not self-closing) or </div>
    # Using a negative lookahead for />
    matches = re.finditer(r'<(div\b[^>]*?(?<!/)>)|(</div\s*>)', content, flags=re.DOTALL)
    
    for m in matches:
        line_num = content.count('\n', 0, m.start()) + 1
        if m.group(1): # Open
            tag = m.group(1)
            stack.append((line_num, tag))
            # print(f"Open: L{line_num} | {tag[:60]}")
        else: # Close
            if not stack:
                print(f"ERROR: Extra Close at L{line_num}")
            else:
                stack.pop()
    
    if stack:
        print(f"ERROR: Found {len(stack)} unclosed tags:")
        for line_num, tag in stack:
            print(f"  Unclosed Open at L{line_num}: {tag[:80]}")
    else:
        print("Balanced!")

audit_details(r'e:\Antigravity Projects\estabilizacion\CRM VENTAS\frontend_react\src\components\Layout.tsx')
audit_details(r'e:\Antigravity Projects\estabilizacion\CRM VENTAS\frontend_react\src\components\marketing\MetaConnectionWizard.tsx')
