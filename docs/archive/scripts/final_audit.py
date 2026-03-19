import re

def count_tags(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Strip comments
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    content = re.sub(r'//.*', '', content)
    
    # Use a simpler but safer approach
    # Find all <div or </div
    opens = 0
    closes = 0
    
    # Iterate through all matches of <div or </div
    for m in re.finditer(r'<(div\b|/div\b)', content):
        tag = m.group(1)
        # Check if it's an open or self-close
        if tag == 'div':
            # Check if this tag is self-closing by looking ahead for />
            # We search from the start of the tag until the first >
            tag_end = content.find('>', m.start())
            if tag_end != -1:
                tag_content = content[m.start():tag_end+1]
                if tag_content.strip().endswith('/>'):
                    # print(f"Self-close found: {tag_content}")
                    pass
                else:
                    opens += 1
        elif tag == '/div':
            closes += 1
            
    return opens, closes

files = [
    r'e:\Antigravity Projects\estabilizacion\CRM VENTAS\frontend_react\src\modules\crm_sales\views\LeadsView.tsx',
    r'e:\Antigravity Projects\estabilizacion\CRM VENTAS\frontend_react\src\components\Layout.tsx',
    r'e:\Antigravity Projects\estabilizacion\CRM VENTAS\frontend_react\src\components\marketing\MetaConnectionWizard.tsx',
    r'e:\Antigravity Projects\estabilizacion\CRM VENTAS\frontend_react\src\views\ChatsView.tsx'
]

for f in files:
    filename = f.split('\\')[-1]
    o, c = count_tags(f)
    print(f"{filename}: Opens={o}, Closes={c}, Balanced={o==c}")
