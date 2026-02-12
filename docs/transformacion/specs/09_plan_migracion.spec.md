# Specification: Migration Plan Design

## 1. Context and Goals
- **Goal**: Create a phased roadmap for the transformation.
- **Source**: `docs/TRANSFORMACION_AGNOSTICA_NICHO.md` (Prompt 9).
- **Output**: `docs/transformacion/09_plan_migracion_fases.md`.

## 2. Requirements
### 2.1 Phases
The plan must include:
1.  **Phase 0: Preparation**: Documentation (Current step), Backups.
2.  **Phase 1: Agnostic Core Extraction**: Move current dental logic to `modules/dental` without breaking functionality. This is a refactor-only step.
3.  **Phase 2: Configuration Switch**: Implement `niche_config` in `tenants` and the loading logic in Backend/Frontend.
4.  **Phase 3: CRM Niche Implementation**: Build the new `modules/crm_sales`, DB tables, and Frontend views.
5.  **Phase 4: Multi-Niche Live**: Activate a second tenant type.

### 2.2 Tasks per Phase
- List specific files to touch in each phase.
- Estimate risk/complexity.

## 3. Acceptance Criteria
- [ ] Output file `docs/transformacion/09_plan_migracion_fases.md` exists.
- [ ] Logical sequence ensuring zero downtime/breakage for existing dental tenants.
