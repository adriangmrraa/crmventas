# Specification: Niche Configuration Design

## 1. Context and Goals
- **Goal**: Design a configuration schema to define a "Niche" (e.g., Dental, CRM Sales).
- **Source**: `docs/TRANSFORMACION_AGNOSTICA_NICHO.md` (Prompt 3).
- **Output**: `docs/transformacion/03_config_nicho_diseño.md`.

## 2. Requirements
### 2.1 Configuration Schema
The design must propose a JSON schema or DB table structure (`niche_config`) containing:
1.  **Niche Identity**: `niche_name` (enums: 'dental', 'crm_sales'), `description`.
2.  **Agent Logic**:
    *   `tools`: List of allowed tools (names, descriptions, parameters).
    *   `system_prompt`: Template or reference to a prompt file.
3.  **API Resources**: List of exposed resources/routes (e.g., `['patients', 'appointments']` vs `['leads', 'templates']`).
4.  **UI Configuration**: List of active views/modules.

### 2.2 Storage Strategy
- Propose where this config lives (DB table `niches` vs valid JSON in `tenants.config` vs Code objects).
- Note: Code objects (Classes/Dicts) might be safer for complex logic (Tools), but DB allows dynamic updates. Proposal should weigh these.

## 3. Acceptance Criteria
- [ ] Output file `docs/transformacion/03_config_nicho_diseño.md` exists.
- [ ] Concrete JSON examples for "Dental" and "CRM Sales" niches.
- [ ] Explanation of how the Orchestrator reads this config.
