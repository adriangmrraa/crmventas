#!/usr/bin/env python3
"""
Script para corregir terminología en backend.
"""

import os
import re
from pathlib import Path

# Mapeo de términos para backend
TERMINOLOGY_MAP = {
    # SQL queries
    r'\bpatients\b': 'leads',
    r'\bpatient\b': 'lead',
    r'\bPatient\b': 'Lead',
    
    r'\bappointments\b': 'opportunities',
    r'\bappointment\b': 'opportunity',
    r'\bAppointment\b': 'Opportunity',
    
    r'\bclinics\b': 'accounts',
    r'\bclinic\b': 'account',
    r'\bClinic\b': 'Account',
    
    r'\bdental\b': 'sales',
    r'\bDental\b': 'Sales',
    
    # Column names
    r'\bpatient_id\b': 'lead_id',
    r'\bpatient_name\b': 'lead_name',
    r'\bpatient_email\b': 'lead_email',
    r'\bpatient_phone\b': 'lead_phone',
    
    r'\bappointment_id\b': 'opportunity_id',
    r'\bappointment_date\b': 'opportunity_date',
    r'\bappointment_time\b': 'opportunity_time',
    r'\bappointment_datetime\b': 'opportunity_datetime',
    r'\bappointment_status\b': 'opportunity_status',
    
    r'\bclinic_id\b': 'account_id',
    r'\bclinic_name\b': 'account_name',
    
    # Table names in SQL
    r'\bFROM patients\b': 'FROM leads',
    r'\bJOIN patients\b': 'JOIN leads',
    r'\bLEFT JOIN patients\b': 'LEFT JOIN leads',
    
    r'\bFROM appointments\b': 'FROM opportunities',
    r'\bJOIN appointments\b': 'JOIN opportunities',
    r'\bLEFT JOIN appointments\b': 'LEFT JOIN opportunities',
    
    r'\bFROM clinics\b': 'FROM accounts',
    r'\bJOIN clinics\b': 'JOIN accounts',
    r'\bLEFT JOIN clinics\b': 'LEFT JOIN accounts',
    
    # Function parameters
    r'\bpatient_data\b': 'lead_data',
    r'\bappointment_data\b': 'opportunity_data',
    r'\bclinic_data\b': 'account_data',
    
    # Variable names
    r'\bpatient_count\b': 'lead_count',
    r'\bappointment_count\b': 'opportunity_count',
    r'\bclinic_count\b': 'account_count',
    
    # Comments/documentation
    r'\b# Patient\b': '# Lead',
    r'\b# Appointment\b': '# Opportunity',
    r'\b# Clinic\b': '# Account',
    
    r'\b"""Patient\b': '"""Lead',
    r'\b"""Appointment\b': '"""Opportunity',
    r'\b"""Clinic\b': '"""Account',
}

def fix_backend_file(file_path):
    """Fix terminology in a backend file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Apply all replacements
        for pattern, replacement in TERMINOLOGY_MAP.items():
            content = re.sub(pattern, replacement, content)
        
        # Check if changes were made
        if content != original_content:
            # Count changes
            changes = 0
            for pattern in TERMINOLOGY_MAP:
                matches_original = len(re.findall(pattern, original_content))
                matches_new = len(re.findall(pattern, content))
                changes += matches_original - matches_new
            
            # Write back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True, changes
        else:
            return False, 0
            
    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return False, 0

def main():
    """Main function"""
    print("🔧 CORRIGIENDO TERMINOLOGÍA BACKEND")
    print("=" * 60)
    
    # Backend files to fix
    backend_dir = Path("/home/node/.openclaw/workspace/projects/crmventas/orchestrator_service")
    
    files = [
        "services/marketing/marketing_service.py",
        "services/marketing/meta_ads_service.py",
        "routes/marketing.py",
        "routes/meta_auth.py",
        "main.py",
    ]
    
    total_changes = 0
    files_fixed = 0
    
    for file in files:
        file_path = backend_dir / file
        if file_path.exists():
            fixed, changes = fix_backend_file(str(file_path))
            if fixed:
                print(f"✅ {file}: {changes} cambios")
                total_changes += changes
                files_fixed += 1
            else:
                print(f"ℹ️  {file}: Sin cambios necesarios")
        else:
            print(f"⚠️  {file}: No encontrado")
    
    print(f"\n📊 RESUMEN:")
    print(f"  Archivos corregidos: {files_fixed}")
    print(f"  Cambios totales: {total_changes}")
    
    if files_fixed > 0:
        print(f"\n🎉 Terminología backend corregida exitosamente!")
    else:
        print(f"\nℹ️  No se necesitaron correcciones en backend.")

if __name__ == "__main__":
    main()