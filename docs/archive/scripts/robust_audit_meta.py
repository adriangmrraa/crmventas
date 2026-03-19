import re

filepath = r'e:\Antigravity Projects\estabilizacion\CRM VENTAS\frontend_react\src\components\marketing\MetaConnectionWizard.tsx'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Strip comments
content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
content = re.sub(r'//.*', '', content)

# Count div tags using DOTALL to handle multi-line
opens = len(re.findall(r'<div\b(?![^>]*?/>)', content, flags=re.DOTALL))
self_closes = len(re.findall(r'<div\b[^>]*?/>', content, flags=re.DOTALL))
closes = len(re.findall(r'</div\s*>', content))

print(f"Opens (Normal): {opens}")
print(f"Self-Closes: {self_closes}")
print(f"Closes: {closes}")
print(f"Net Balance (Normal Opens - Closes): {opens - closes}")
