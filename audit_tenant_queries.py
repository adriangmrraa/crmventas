import os
import re
import asyncio
from typing import List, Tuple

# Colores para salida terminal
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

async def audit_queries():
    print(f"{YELLOW}--- Iniciando Auditoría de Aislamiento Multi-tenant ---{RESET}")
    
    search_dirs = [
        "orchestrator_service",
    ]
    
    # Patrones que indican consultas SQL que podrían omitir tenant_id
    # Buscamos SELECT/UPDATE/DELETE que no contengan 'tenant_id' en la misma cadena o línea siguiente
    dangerous_patterns = [
        r"(SELECT|UPDATE|DELETE).*FROM\s+(leads|chat_messages|appointments|agents|professionals|sellers|seller_agenda_events|credentials)",
    ]
    
    findings = []
    
    for root_dir in search_dirs:
        for root, dirs, files in os.walk(root_dir):
            for file in files:
                if file.endswith(".py") or file.endswith(".ts"):
                    filepath = os.path.join(root, file)
                    with open(filepath, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        content = "".join(lines)
                        
                        for pattern in dangerous_patterns:
                            matches = re.finditer(pattern, content, re.IGNORECASE | re.DOTALL)
                            for match in matches:
                                start_idx = match.start()
                                end_idx = match.end()
                                # Extraer bloque de contexto (500 chars)
                                block = content[start_idx : start_idx + 600]
                                
                                # Si el bloque NO contiene 'tenant_id', es sospechoso
                                if "tenant_id" not in block.lower():
                                    line_num = content.count("\n", 0, start_idx) + 1
                                    findings.append((filepath, line_num, match.group(0).replace("\n", " ")))

    if not findings:
        print(f"{GREEN}✅ No se encontraron consultas sospechosas sin tenant_id.{RESET}")
    else:
        print(f"{RED}❌ SE ENCONTRARON {len(findings)} CONSULTAS SOSPECHOSAS:{RESET}")
        for path, line, snippet in findings:
            print(f"  - {path}:{line} -> {YELLOW}{snippet}{RESET}")
            
    return len(findings)

if __name__ == "__main__":
    asyncio.run(audit_queries())
