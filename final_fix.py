import sys
import os

filepath = r'e:\Antigravity Projects\estabilizacion\CRM VENTAS\frontend_react\src\views\ChatsView.tsx'

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Truncate at line 1261 (0-indexed 1260) and rebuild the end
target_idx = 1261 # This is the line with 'onCancel={() => setShowSellerSelector(false)}'
if 'onCancel' in lines[target_idx]:
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
