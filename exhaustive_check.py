import re

def final_check(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Strip comments
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    content = re.sub(r'//.*', '', content)
    
    opens = len(re.findall(r'<div\b', content))
    closes = len(re.findall(r'</div\s*>', content))
    self_closes = len(re.findall(r'<div\b[^>]*?/>', content, flags=re.DOTALL))
    
    return opens, closes, self_closes

files = [
    r'e:\Antigravity Projects\estabilizacion\CRM VENTAS\frontend_react\src\modules\crm_sales\views\LeadsView.tsx',
    r'e:\Antigravity Projects\estabilizacion\CRM VENTAS\frontend_react\src\components\Layout.tsx',
    r'e:\Antigravity Projects\estabilizacion\CRM VENTAS\frontend_react\src\components\marketing\MetaConnectionWizard.tsx',
    r'e:\Antigravity Projects\estabilizacion\CRM VENTAS\frontend_react\src\views\ChatsView.tsx'
]

for f in files:
    filename = f.split('\\')[-1]
    o, c, sc = final_check(f)
    print(f"{filename}: Total Opens={o}, Normal Closes={c}, Self Closes={sc}, Net={o - c - sc}")
