import sys
import os

filepath = r'e:\Antigravity Projects\estabilizacion\CRM VENTAS\frontend_react\src\views\ChatsView.tsx'

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Search for the last good line of SellerSelector
target_idx = -1
for i in range(len(lines)):
    if 'onCancel={() => setShowSellerSelector(false)}' in lines[i]:
        target_idx = i
        break

if target_idx != -1:
    new_lines = lines[:target_idx + 1]
    new_lines.extend([
        '              showAssignToMe={true}\n',
        '              showAutoAssign={true}\n',
        '            />\n',
        '          </div>\n',
        '        </div>\n',
        '      )}\n',
        '\n',
        '      {/* ======================================== */}\n',
        '      {/* CSS for animations - Removed to fix build error */}\n',
        '      {/* ======================================== */}\n',
        '    </div>\n',
        '  );\n',
        '}\n'
    ])
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print("File restored and fixed.")
else:
    print("Could not find expected line for restoration.")
