import re

filepath = r'e:\Antigravity Projects\estabilizacion\CRM VENTAS\frontend_react\src\modules\crm_sales\views\LeadsView.tsx'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Count fragments
frag_opens = len(re.findall(r'<>|<Fragment', content))
frag_closes = len(re.findall(r'</>|</Fragment>', content))

print(f"Fragment Opens: {frag_opens}")
print(f"Fragment Closes: {frag_closes}")
