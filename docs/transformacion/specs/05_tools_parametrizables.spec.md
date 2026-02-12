# Specification: Parametrizable Tools Design

## 1. Context and Goals
- **Goal**: Design a mechanism to load LangChain tools dynamically per tenant niche.
- **Source**: `docs/TRANSFORMACION_AGNOSTICA_NICHO.md` (Prompt 5).
- **Output**: `docs/transformacion/05_tools_parametrizables.md`.

## 2. Requirements
### 2.1 Dynamic Tool Loading
The design must propose:
1.  **Registry/Factory**: A central `ToolRegistry` or `get_tools_for_niche(niche_type)` function.
2.  **Configuration**: How tools are defined in the config (by name string vs import path).
3.  **Implementation**: How to refactor `main.py` where tools are currently hardcoded imports.

### 2.2 Niche Specific Tools
- Example for Dental: `check_availability`, `book_appointment`.
- Example for CRM: `list_templates`, `send_whatsapp_template`.

## 3. Acceptance Criteria
- [ ] Output file `docs/transformacion/05_tools_parametrizables.md` exists.
- [ ] Detailed Python code snippets for the factory pattern.
- [ ] Explanation of how to add a new tool without modifying Core.
