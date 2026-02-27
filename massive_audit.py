import re
import os

def check_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Strip comments
    clean_content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    clean_content = re.sub(r'//.*', '', clean_content)
    
    # Check div balance
    opens = len(re.findall(r'<div\b', clean_content))
    closes = len(re.findall(r'</div\s*>', clean_content))
    self_closes = len(re.findall(r'<div\b[^>]*?/>', clean_content, flags=re.DOTALL))
    
    div_balance = (opens - closes - self_closes) == 0
    
    # Check curly brace balance
    b_opens = clean_content.count('{')
    b_closes = clean_content.count('}')
    brace_balance = (b_opens == b_closes)
    
    # Check duplicate declarations (const handle...)
    decls = re.findall(r'const\s+(\w+)\s*=', clean_content)
    seen = set()
    dupes = []
    for d in decls:
        if d in seen:
            dupes.append(d)
        seen.add(d)
    
    return {
        'div_balance': div_balance,
        'div_net': opens - closes - self_closes,
        'brace_balance': brace_balance,
        'brace_net': b_opens - b_closes,
        'duplicates': dupes
    }

files_to_audit = [
    r'e:\Antigravity Projects\estabilizacion\CRM VENTAS\frontend_react\src\components\Layout.tsx',
    r'e:\Antigravity Projects\estabilizacion\CRM VENTAS\frontend_react\src\components\marketing\MetaConnectionWizard.tsx',
    r'e:\Antigravity Projects\estabilizacion\CRM VENTAS\frontend_react\src\components\NotificationCenter.tsx',
    r'e:\Antigravity Projects\estabilizacion\CRM VENTAS\frontend_react\src\modules\crm_sales\views\LeadsView.tsx',
    r'e:\Antigravity Projects\estabilizacion\CRM VENTAS\frontend_react\src\modules\crm_sales\components\LeadStatusSelector.tsx',
    r'e:\Antigravity Projects\estabilizacion\CRM VENTAS\frontend_react\src\modules\crm_sales\components\LeadHistoryTimeline.tsx',
    r'e:\Antigravity Projects\estabilizacion\CRM VENTAS\frontend_react\src\modules\crm_sales\components\BulkStatusUpdate.tsx',
    r'e:\Antigravity Projects\estabilizacion\CRM VENTAS\frontend_react\src\views\ChatsView.tsx'
]

print(f"{'File':<40} | Div | Braces | Dupes")
print("-" * 75)

for f in files_to_audit:
    if not os.path.exists(f):
        print(f"{os.path.basename(f):<40} | MISSING")
        continue
    res = check_file(f)
    div_str = f"{res['div_net']:+}" if not res['div_balance'] else "OK"
    brace_str = f"{res['brace_net']:+}" if not res['brace_balance'] else "OK"
    dupe_str = ",".join(res['duplicates']) if res['duplicates'] else "None"
    print(f"{os.path.basename(f):<40} | {div_str:<3} | {brace_str:<6} | {dupe_str}")
