# Validation Checklist: Multi-Niche Transformation

**Purpose**: Verify that the Dentalogic → Nexus Multi-Niche transformation was successful and all systems are operational.

**Status Key**:
- ✅ = Passed
- ❌ = Failed
- ⏳ = Pending verification
- ⚠️ = Partial / Needs attention

---

## 🗄️ Database Layer

### Schema Validation
- [ ] **Tenants table has `niche_type` column**
  - SQL: `SELECT column_name FROM information_schema.columns WHERE table_name='tenants' AND column_name='niche_type';`
  - Expected: Returns 1 row

- [ ] **CRM tables exist** (`leads`, `whatsapp_connections`, `templates`, `campaigns`)
  - SQL: `SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('leads', 'whatsapp_connections', 'templates', 'campaigns');`
  - Expected: Returns 4 rows

- [ ] **All CRM tables have `tenant_id` column**
  - SQL: `SELECT table_name FROM information_schema.columns WHERE table_schema='public' AND column_name='tenant_id' AND table_name IN ('leads', 'whatsapp_connections', 'templates', 'campaigns');`
  - Expected: Returns 4 rows

- [ ] **Existing dental data intact**
  - SQL: `SELECT COUNT(*) FROM patients;`
  - Expected: Count matches pre-migration value (if you have data)

### Indexes Validation
- [ ] **CRM tables have tenant indexes**
  - SQL: `SELECT tablename, indexname FROM pg_indexes WHERE tablename IN ('leads', 'whatsapp_connections', 'templates', 'campaigns');`
  - Expected: At least 4 indexes (one per table for tenant_id)

---

## 🔧 Backend Layer

### Module Structure
- [ ] **Core module exists**: `orchestrator_service/core/` directory present
- [ ] **Dental module exists**: `orchestrator_service/modules/dental/` directory present
- [ ] **CRM module exists**: `orchestrator_service/modules/crm_sales/` directory present

### File Verification
- [ ] **NicheManager exists**: `core/niche_manager.py` file present
- [ ] **PromptLoader exists**: `core/agent/prompt_loader.py` file present
- [ ] **ToolRegistry exists**: `core/tools.py` file present
- [ ] **Dental routes**: `modules/dental/routes.py` file present
- [ ] **CRM routes**: `modules/crm_sales/routes.py` file present
- [ ] **CRM models**: `modules/crm_sales/models.py` file present

### Startup Validation
- [ ] **Orchestrator starts without errors**
  - Command: `uvicorn main:app --reload`
  - Check logs for: "✅ Loaded router for niche: dental"
  - Check logs for: "✅ Loaded router for niche: crm_sales"

- [ ] **No import errors in logs**
  - Search logs for "ImportError" or "ModuleNotFoundError"

---

## 🌐 API Endpoints

### Core Admin Endpoints (`/admin/core/*`)
Test with valid JWT token for a dental tenant:

- [ ] **GET /admin/core/users** → Returns list of users
- [ ] **GET /admin/core/tenants** → Returns list of tenants
- [ ] **GET /admin/core/settings/clinic** → Returns clinic settings
- [ ] **POST /admin/core/chat/sessions/pause** → Pauses chat session

**Command template**:
```bash
curl -H "Authorization: Bearer $JWT_TOKEN" http://localhost:8000/admin/core/users
```

### Dental Endpoints (`/admin/dental/*`)
Test with JWT for dental tenant:

- [ ] **GET /admin/dental/appointments** → Returns appointments for tenantverify `tenant_id` in response matches JWT
- [ ] **GET /admin/dental/patients** → Returns patients
- [ ] **GET /admin/dental/professionals** → Returns professionals

### CRM Endpoints (`/niche/crm_sales/*`)
Test with JWT (can use dental tenant for now, leads will be empty):

- [ ] **GET /niche/crm_sales/leads** → Returns empty array `[]` (new tenant)
- [ ] **POST /niche/crm_sales/leads** → Creates a lead
  - Body: `{"phone_number": "+123456", "first_name": "Test", "status": "new"}`
  - Expected: Returns created lead with UUID

- [ ] **GET /niche/crm_sales/whatsapp/connections** → Returns empty array
- [ ] **GET /niche/crm_sales/templates** → Returns empty array
- [ ] **GET /niche/crm_sales/campaigns** → Returns empty array

---

## 🛡️ Multi-Tenancy Security

### Tenant Isolation
- [ ] **Create lead for tenant A, verify tenant B cannot see it**
  - Step 1: Login as user from tenant_id=1, create a lead
  - Step 2: Login as user from tenant_id=2 (if available), GET /niche/crm_sales/leads
  - Expected: Second request returns empty array `[]`

- [ ] **Verify `tenant_id` extracted from JWT, not URL**
  - Check `core/security.py` → `get_current_user_context` function
  - Confirm: `tenant_id` comes from decoded JWT payload
  - Confirm: NOT from `request.query_params` or `request.path_params`

- [ ] **SQL queries include `WHERE tenant_id = $X`**
  - Check `modules/crm_sales/routes.py` → All SELECT queries
  - Confirm: Every query filters by tenant_id

---

## 🎨 Frontend Layer

### File Structure
- [ ] **Core layout exists**: `frontend_react/src/core/layout/Sidebar.tsx`
- [ ] **Dental module exists**: `frontend_react/src/modules/dental/`
- [ ] **AuthContext stores niche**: Open `src/context/AuthContext.tsx`, verify `niche_type` field

### API Calls
- [ ] **Open browser console, start frontend dev server**:
  ```bash
  cd frontend_react && npm run dev
  ```

- [ ] **Login as dental user, check Network tab**:
  - [ ] No 404 errors in console
  - [ ] API calls use `/admin/core/*` for users, tenants, settings
  - [ ] API calls use `/admin/dental/*` for appointments, patients

### Sidebar Filtering
- [ ] **Dental user sees dental menu items**:
  - Expected items: Pacientes, Agenda, Profesionales, etc.
  - NOT expected: Leads, Campañas (CRM items)

- [ ] **CRM user would see CRM items** (manual test if CRM tenant exists):
  - Expected: Leads, Campañas, Templates
  - NOT expected: Pacientes, Agenda

---

## 🔄 Dynamic Loading

### Niche Router Loading
- [ ] **Check main.py line ~67**:
  ```python
  SUPPORTED_NICHES = ["dental", "crm_sales"]
  for niche in SUPPORTED_NICHES:
      NicheManager.load_niche_router(app, niche)
  ```
  - Verify loop exists

- [ ] **Verify NicheManager.load_niche_router logic**:
  - Open `core/niche_manager.py`
  - Confirm dynamic `importlib.import_module(f"modules.{niche_type}.routes")`

### Prompt Loading
- [ ] **Prompt loader resolves correct file**:
  - For dental: `modules/dental/prompts/base_assistant.txt`
  - Path construction: `modules/{niche_type}/prompts/...`

- [ ] **Test prompt loading** (Python console):
  ```python
  from core.agent.prompt_loader import prompt_loader
  prompt = prompt_loader.load_prompt("dental", tenant_id=1)
  print(len(prompt))  # Should return >100 characters
  ```

---

## 📊 Idempotency & Migrations

### Database Migrations
- [ ] **Restart orchestrator service 3 times**:
  - Check logs each time for "✅ Base de datos verificada"
  - No errors like "column already exists"
  - Expected: All migrations use `IF NOT EXISTS`

- [ ] **Verify Patch 16 (CRM tables) in db.py**:
  - Open `orchestrator_service/db.py`
  - Search for "# Parche 16"
  - Confirm CRM table creation statements present

---

## 🧪 Regression Testing

### Critical Dental Flows (Should NOT break)
- [ ] **Login flow**: CEO can login with existing credentials
- [ ] **View patients**: GET /admin/dental/patients returns data
- [ ] **Schedule appointment**: POST /admin/dental/appointments works
- [ ] **Chat sessions**: Chat view loads, messages display

### Known Issues (If Any)
Document any failing tests here:
- ⚠️ Issue 1: ...
- ⚠️ Issue 2: ...

---

## 🚀 Deployment Readiness

### Pre-Deployment Checklist
- [ ] **All 8 phases completed** (see migration plan)
- [ ] **Documentation updated** (this checklist + migration plan)
- [ ] **Rollback plan documented** (in migration plan)
- [ ] **Environment variables set**:
  - `POSTGRES_DSN`
  - `OPENAI_API_KEY`
  - `JWT_SECRET`

### Post-Deployment Smoke Tests
Run these in production after deploy:

- [ ] **Health check**: `GET /health` (if endpoint exists)
- [ ] **Core endpoints**: `GET /admin/core/users` with prod JWT
- [ ] **Dental endpoints**: `GET /admin/dental/appointments`
- [ ] **CRM endpoints**: `GET /niche/crm_sales/leads`
- [ ] **Frontend loads**: Browse to production URL, no console errors

---

## 📝 Validation Report

**Date**: _____________  
**Validator**: _____________  
**Environment**: ☐ Local  ☐ Staging  ☐ Production

### Summary:
- Total checks: _____ / _____
- Passed: _____
- Failed: _____
- Blocked: _____

### Critical Issues:
(List any blocking issues)

### Recommendation:
☐ **APPROVED** for production deployment  
☐ **NEEDS FIXES** before deployment  
☐ **BLOCKED** - cannot proceed

---

**Document version**: 1.0  
**Last updated**: 2026-02-12  
**Author**: Adrián (Dentalogic Team)
