# Specification: CRM Data Model Design

## 1. Context and Goals
- **Goal**: Design the Data Model and API for the "CRM Sales" niche.
- **Source**: `docs/TRANSFORMACION_AGNOSTICA_NICHO.md` (Prompt 8).
- **Output**: `docs/transformacion/08_modelo_crm_ventas.md`.

## 2. Requirements
### 2.1 Entities
The design must define the following tables/entities, all with `tenant_id`:
1.  **`leads`**: Potential customers (phone, name, source, status).
2.  **`sellers`**: Sales agents (linked to core `users`).
3.  **`whatsapp_connections`**: Meta API credentials per seller/tenant.
4.  **`templates`**: Approved WhatsApp templates.
5.  **`template_sends`**: Log of template usage.

### 2.2 API Endpoints
- CRUD for entities above.
- Special actions: `POST /send-template`, `POST /assign-lead`.

## 3. Acceptance Criteria
- [ ] Output file `docs/transformacion/08_modelo_crm_ventas.md` exists.
- [ ] SQL Schema snippets (CREATE TABLE).
- [ ] Python Pydantic models for API resources.
