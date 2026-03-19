import re

filepath = r'e:\Antigravity Projects\estabilizacion\CRM VENTAS\frontend_react\src\modules\crm_sales\views\LeadsView.tsx'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Simple count of div tags
opens = len(re.findall(r'<div\b', content))
closes = len(re.findall(r'</div\s*>', content))

print(f"Opens: {opens}")
print(f"Closes: {closes}")

# Check for unbalanced ternaries or JS blocks
# This is harder but let's look at the return block
return_match = re.search(r'return \((.*?)\);', content, re.DOTALL)
if return_match:
    return_content = return_match.group(1)
    ret_opens = len(re.findall(r'<div\b', return_content))
    ret_closes = len(re.findall(r'</div\s*>', return_content))
    print(f"In return - Opens: {ret_opens}, Closes: {ret_closes}")
else:
    print("Could not find return block accurately")
