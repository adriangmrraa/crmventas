#!/usr/bin/env python3
"""
Script para corregir terminología en componentes frontend.
Reemplaza términos de ClinicForge por términos de CRM Ventas.
"""

import os
import re
from pathlib import Path

# Mapeo de términos: ClinicForge → CRM Ventas
TERMINOLOGY_MAP = {
    # Core terms
    r'\bpatient\b': 'lead',
    r'\bpatients\b': 'leads',
    r'\bPatient\b': 'Lead',
    r'\bPatients\b': 'Leads',
    
    r'\bappointment\b': 'opportunity',
    r'\bappointments\b': 'opportunities',
    r'\bAppointment\b': 'Opportunity',
    r'\bAppointments\b': 'Opportunities',
    
    r'\bclinic\b': 'account',
    r'\bclinics\b': 'accounts',
    r'\bClinic\b': 'Account',
    r'\bClinics\b': 'Accounts',
    
    r'\bdental\b': 'sales',
    r'\bDental\b': 'Sales',
    
    r'\bmedical\b': 'business',
    r'\bMedical\b': 'Business',
    
    # Medical specific → Business specific
    r'\btreatment\b': 'service',
    r'\btreatments\b': 'services',
    r'\bTreatment\b': 'Service',
    r'\bTreatments\b': 'Services',
    
    r'\bdoctor\b': 'manager',
    r'\bdoctors\b': 'managers',
    r'\bDoctor\b': 'Manager',
    r'\bDoctors\b': 'Managers',
    
    r'\bnurse\b': 'assistant',
    r'\bnurses\b': 'assistants',
    r'\bNurse\b': 'Assistant',
    r'\bNurses\b': 'Assistants',
    
    # UI text
    r'\bNew Patient\b': 'New Lead',
    r'\bNew Patients\b': 'New Leads',
    r'\bSchedule Appointment\b': 'Schedule Opportunity',
    r'\bSchedule Appointments\b': 'Schedule Opportunities',
    r'\bClinic Settings\b': 'Account Settings',
    r'\bDental Records\b': 'Sales Records',
    
    # API/Data fields
    r'\bpatient_id\b': 'lead_id',
    r'\bpatient_name\b': 'lead_name',
    r'\bpatient_email\b': 'lead_email',
    r'\bpatient_phone\b': 'lead_phone',
    
    r'\bappointment_id\b': 'opportunity_id',
    r'\bappointment_date\b': 'opportunity_date',
    r'\bappointment_time\b': 'opportunity_time',
    r'\bappointment_status\b': 'opportunity_status',
    
    r'\bclinic_id\b': 'account_id',
    r'\bclinic_name\b': 'account_name',
    
    # Component props
    r'\bpatientData\b': 'leadData',
    r'\bappointmentData\b': 'opportunityData',
    r'\bclinicData\b': 'accountData',
    
    # State variables
    r'\bselectedPatient\b': 'selectedLead',
    r'\bselectedPatients\b': 'selectedLeads',
    r'\bselectedAppointment\b': 'selectedOpportunity',
    r'\bselectedAppointments\b': 'selectedOpportunities',
    r'\bselectedClinic\b': 'selectedAccount',
    
    # Functions
    r'\bgetPatient\b': 'getLead',
    r'\bgetPatients\b': 'getLeads',
    r'\bcreatePatient\b': 'createLead',
    r'\bupdatePatient\b': 'updateLead',
    r'\bdeletePatient\b': 'deleteLead',
    
    r'\bgetAppointment\b': 'getOpportunity',
    r'\bgetAppointments\b': 'getOpportunities',
    r'\bcreateAppointment\b': 'createOpportunity',
    r'\bupdateAppointment\b': 'updateOpportunity',
    r'\bdeleteAppointment\b': 'deleteOpportunity',
    
    r'\bgetClinic\b': 'getAccount',
    r'\bgetClinics\b': 'getAccounts',
    r'\bcreateClinic\b': 'createAccount',
    r'\bupdateClinic\b': 'updateAccount',
    
    # Types/Interfaces
    r'\bPatientType\b': 'LeadType',
    r'\bAppointmentType\b': 'OpportunityType',
    r'\bClinicType\b': 'AccountType',
    
    r'\bIPatient\b': 'ILead',
    r'\bIAppointment\b': 'IOpportunity',
    r'\bIClinic\b': 'IAccount',
}

def fix_file(file_path):
    """Fix terminology in a single file"""
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
    print("🔧 CORRIGIENDO TERMINOLOGÍA FRONTEND")
    print("=" * 60)
    
    # Frontend components to fix
    frontend_dir = Path("/home/node/.openclaw/workspace/projects/crmventas/frontend_react/src")
    
    components = [
        "views/marketing/MarketingHubView.tsx",
        "views/marketing/MetaTemplatesView.tsx",
        "components/marketing/MarketingPerformanceCard.tsx",
        "components/marketing/MetaTokenBanner.tsx",
        "components/marketing/MetaConnectionWizard.tsx",
        "api/marketing.ts",
        "types/marketing.ts",
        "App.tsx",
        "components/Sidebar.tsx",
    ]
    
    total_changes = 0
    files_fixed = 0
    
    for component in components:
        file_path = frontend_dir / component
        if file_path.exists():
            fixed, changes = fix_file(str(file_path))
            if fixed:
                print(f"✅ {component}: {changes} cambios")
                total_changes += changes
                files_fixed += 1
            else:
                print(f"ℹ️  {component}: Sin cambios necesarios")
        else:
            print(f"⚠️  {component}: No encontrado")
    
    print(f"\n📊 RESUMEN:")
    print(f"  Archivos corregidos: {files_fixed}")
    print(f"  Cambios totales: {total_changes}")
    
    if files_fixed > 0:
        print(f"\n🎉 Terminología corregida exitosamente!")
        print("🔍 Verificar que los componentes funcionen correctamente.")
    else:
        print(f"\nℹ️  No se necesitaron correcciones.")

if __name__ == "__main__":
    main()