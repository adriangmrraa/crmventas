# Specification: Agnostic Core Proposal

## 1. Context and Goals
- **Goal**: Propose a technical architecture that separates the "Agnostic Core" from the "Dental Niche Module".
- **Source**: `docs/TRANSFORMACION_AGNOSTICA_NICHO.md` (Prompt 2).
- **Input**: `docs/transformacion/01_inventario_dominio_dental.md`.
- **Output**: `docs/transformacion/02_nucleo_agnostico_propuesta.md`.

## 2. Requirements
### 2.1 Core vs. Niche Definition
The proposal must explicitly list:
1.  **Agnostic Core**: Components to remain in the main structure.
    *   Auth, Tenants, Users, Chat/Messaging, Tenant Configuration.
    *   Base UI (Layout, Login, Settings).
2.  **Niche Module (Dental)**: Components to be extracted/modularized.
    *   Entities: Patients, Appointments, Treatments, Clinical Records.
    *   API: Dental-specific endpoints.
    *   Agent: Dental tools and prompts.
    *   UI: Specific views (Odontogram, Agenda).

### 2.2 Technical Proposal
- List specific files/folders to move or rename.
- Propose a directory structure for the "Niche Modules" (e.g., `modules/dental`, `modules/crm_sales`).
- Define how the Core will load/interact with the Niche module (Conceptually).

## 3. Acceptance Criteria
- [ ] Output file `docs/transformacion/02_nucleo_agnostico_propuesta.md` exists.
- [ ] Clear distinction between Core and Niche components.
- [ ] Specific file paths are mentioned for migration.
- [ ] No code is modified, only a plan/proposal document.
