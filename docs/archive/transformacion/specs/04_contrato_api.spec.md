# Specification: API Contract Design

## 1. Context and Goals
- **Goal**: Define the separation of the API contract into Agnostic Core routes and Niche Specific routes.
- **Source**: `docs/TRANSFORMACION_AGNOSTICA_NICHO.md` (Prompt 4).
- **Output**: `docs/transformacion/04_contrato_api_agnostico.md`.

## 2. Requirements
### 2.1 Route Separation
The design must explicitly list:
1.  **Common Routes**: `/admin/auth`, `/admin/tenants`, `/admin/chat`, `/admin/users`, `/admin/settings`.
2.  **Niche Routes (Dental)**: `/admin/patients`, `/admin/appointments`, `/admin/treatments`, `/admin/professionals`.
3.  **Niche Routes (CRM)**: `/admin/leads`, `/admin/templates`, `/admin/sellers`, `/admin/metrics`.

### 2.2 URL Conventions
- Propose a convention for niche routes.
    *   Option A: `/admin/dental/...` vs `/admin/crm/...` (Explicit namespacing).
    *   Option B: `/admin/niche/...` (Generic namespace, resources depend on context).
    *   Option C: Keep flat `/admin/...` but load conditionally (confusing documentation).
- **Recommendation**: Option B (`/niche`) or Option A (`/dental`). Prompt asks to propose one.

## 3. Acceptance Criteria
- [ ] Output file `docs/transformacion/04_contrato_api_agnostico.md` exists.
- [ ] Lists specific routes for Core vs Dental vs CRM.
- [ ] Defines the URL structure clearly.
