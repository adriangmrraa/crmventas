import sys
import os

filepath = r'e:\Antigravity Projects\estabilizacion\CRM VENTAS\frontend_react\src\views\ChatsView.tsx'

if not os.path.exists(filepath):
    print(f"File not found: {filepath}")
    sys.exit(1)

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix 1: Missing </div> after line 949 (to close line 919)
# BUT WAIT, did I already apply it? Let's check for "Header Actions" around there.
already_fixed_div = False
for i in range(940, 960):
    if i < len(lines) and '</div>' in lines[i] and 'Header Actions' in ''.join(lines[i:i+5]):
        already_fixed_div = True
        break

if not already_fixed_div:
    # Find original line 949 (it might have shifted)
    target_idx = -1
    for i in range(900, 1000):
        if 'RefreshCw' in lines[i] and 'animate-spin' in lines[i]:
            # This is around 945. Find the next </button>
            for j in range(i, i+10):
                if '</button>' in lines[j]:
                    target_idx = j
                    break
            break
    
    if target_idx != -1:
        lines.insert(target_idx + 1, '                </div>\n')
        print(f"Fixed missing div at line {target_idx + 2}")

# Fix 2: Missing )} after the empty session div
# Find 'to_start_chatting'
empty_div_idx = -1
for i in range(1200, len(lines)):
    if 'to_start_chatting' in lines[i]:
        # Find next </div>
        for j in range(i, i+10):
            if '</div>' in lines[j]:
                empty_div_idx = j
                break
        break

if empty_div_idx != -1:
    # Check if )} already exists
    if ')}' not in lines[empty_div_idx + 1]:
        lines.insert(empty_div_idx + 1, '      )}\n')
        print(f"Fixed missing ternary closer at line {empty_div_idx + 2}")

# Fix 3: Balanced tail
# Find the start of seller selector
selector_idx = -1
for i in range(len(lines)):
    if 'showSellerSelector' in lines[i] and '&&' in lines[i]:
        selector_idx = i
        break

if selector_idx != -1:
    # Find where it ends
    selector_end = -1
    for i in range(selector_idx, len(lines)):
        if ')}' in lines[i]:
            selector_end = i
            break
    
    if selector_end != -1:
        # Final content
        final_lines = lines[:selector_end + 1]
        final_lines.append('\n')
        final_lines.append('    </div>\n')
        final_lines.append('  );\n')
        final_lines.append('}\n')
        lines = final_lines

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Fix applied successfully.")
