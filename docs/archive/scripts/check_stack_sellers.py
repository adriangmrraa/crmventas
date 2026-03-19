import re

def check_balance(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    stack = []
    for line_num, line in enumerate(lines, 1):
        # Find all tags in line
        # Simple regex that looks for <div or </div>
        tokens = re.findall(r'<(/?div\b)', line)
        for token in tokens:
            if token == 'div':
                stack.append(line_num)
            else:
                if not stack:
                    print(f"Extra closing div at line {line_num}")
                else:
                    stack.pop()
    
    while stack:
        print(f"Unclosed div from line {stack.pop()}")

print("Checking SellersView.tsx:")
check_balance(r'e:\Antigravity Projects\estabilizacion\CRM VENTAS\frontend_react\src\modules\crm_sales\views\SellersView.tsx')
