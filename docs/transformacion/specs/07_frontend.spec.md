# Specification: Frontend Multi-Niche Design

## 1. Context and Goals
- **Goal**: Design a Frontend architecture that supports multiple niches within a single Shell.
- **Source**: `docs/TRANSFORMACION_AGNOSTICA_NICHO.md` (Prompt 7).
- **Output**: `docs/transformacion/07_frontend_multinicho.md`.

## 2. Requirements
### 2.1 Shell vs Modules
The design must propose:
1.  **Shell**: Generic components (Layout, Auth, Settings, Chat Shell).
2.  **Dental Module**: Specific views (Agenda, Patients, Treatments).
3.  **CRM Module**: Specific views (Leads, Templates, Campaigns).

### 2.2 Dynamic Routing
- How `App.tsx` loads the correct routes based on `user.niche_type` or tenant config.
- Proposed directory structure (e.g., `src/modules/dental`).

## 3. Acceptance Criteria
- [ ] Output file `docs/transformacion/07_frontend_multinicho.md` exists.
- [ ] Detailed directory tree.
- [ ] Code snippet for dynamic route loading.
