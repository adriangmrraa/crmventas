import re

def count_tags(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Strip comments
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    content = re.sub(r'//.*', '', content)
    
    opens = 0
    closes = 0
    
    for m in re.finditer(r'<(div\b|/div\b)', content):
        tag = m.group(1)
        if tag == 'div':
            tag_end = content.find('>', m.start())
            if tag_end != -1:
                tag_content = content[m.start():tag_end+1]
                if tag_content.strip().endswith('/>'):
                    pass
                else:
                    opens += 1
        elif tag == '/div':
            closes += 1
            
    return opens, closes

f = r'e:\Antigravity Projects\estabilizacion\CRM VENTAS\frontend_react\src\components\NotificationBell.tsx'
o, c = count_tags(f)
print(f"NotificationBell.tsx: Opens={o}, Closes={c}, Balanced={o==c}")
