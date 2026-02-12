# Specification: Inventory of Dental Domain

## 1. Context and Goals
- **Goal**: Analyze the current "Dentalogic" repository to identify all domain-specific concepts (Code, DB, UI, Prompts) that need to be abstracted or separated for the transformation to a Generic CRM.
- **Source**: `docs/transformacion.md` (Prompt 1).
- **Scope**: Entire repository (`orchestrator_service`, `frontend_react`, `docs`, `db`).
- **Output**: `docs/transformacion/01_inventario_dominio_dental.md`.

## 2. Requirements
### 2.1 Analysis Categories
The inventory must categorize findings into:
1.  **Data Model**: Tables, columns, and JSONB fields specific to dental (e.g., `patients`, `clinical_records`, `odontogram`, `treatment_types`).
2.  **API Endpoints**: Routes that imply dental logic (e.g., `/admin/patients`, `/admin/treatment-types`).
3.  **Agent Logic**:
    *   **Tools**: Specific function calls (e.g., `list_services` vs `list_products`, `triage_urgency`).
    *   **Prompt**: Hardcoded texts in the system prompt (e.g., "Asistente de clínica dental", "turnos").
4.  **Frontend/UI**:
    *   **Views**: Specific pages (Agenda, Pacientes, Odontograma).
    *   **Components**: Dental-specific UI elements.
    *   **Terminology**: Hardcoded strings in `locales` (es/en/fr).

### 2.2 Constraints
- **Read-Only**: Do not modify any code.
- **Documentation Only**: Output must be a Markdown file.
- **Sovereignty**: Note any multi-tenant violations if found (though primarily focusing on domain coupling).

## 3. Acceptance Criteria
- [ ] The output file `docs/transformacion/01_inventario_dominio_dental.md` exists.
- [ ] All 4 categories (Data, API, Agent, UI) are populated.
- [ ] Specific dental concepts like "odontogram", "clinical records", "triage" are listed.
