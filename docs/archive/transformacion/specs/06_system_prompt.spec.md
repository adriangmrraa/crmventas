# Specification: Dynamic System Prompt Design

## 1. Context and Goals
- **Goal**: Design a mechanism to load LangChain system prompts dynamically per tenant niche.
- **Source**: `docs/TRANSFORMACION_AGNOSTICA_NICHO.md` (Prompt 6).
- **Output**: `docs/transformacion/06_system_prompt_por_nicho.md`.

## 2. Requirements
### 2.1 Prompt Loading
The design must propose:
1.  **Storage**: File-based (e.g., `modules/dental/prompts/base.md`) vs DB-based (field in `tenants`).
2.  **Injection**: How dynamic variables (`clinic_name`, `current_time`) are injected using Jinja2 or f-strings.
3.  **Implementation**: How `main.py` should load the prompt text.

### 2.2 Niche Specific Prompts
- Example for Dental: "You are a dental assistant...".
- Example for CRM: "You are a sales setter...".

## 3. Acceptance Criteria
- [ ] Output file `docs/transformacion/06_system_prompt_por_nicho.md` exists.
- [ ] Detailed Python code snippets for loading and formatting the prompt.
- [ ] Explanation of variable injection.
