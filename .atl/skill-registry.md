# Skill Registry

**Project**: CRM VENTAS
**Last Updated**: 2026-03-30

## User-Level Skills

| Skill Name | Trigger | Description |
|:-----------|:--------|:------------|
| sdd-init | sdd init, iniciar sdd, openspec init | Initialize SDD context |
| sdd-explore | sdd-explore <topic> | Explore codebase and investigate ideas |
| sdd-propose | sdd-propose <change> | Create change proposals |
| sdd-spec | sdd-spec <change> | Write specifications |
| sdd-design | sdd-design <change> | Technical design documents |
| sdd-tasks | sdd-tasks <change> | Break down into tasks |
| sdd-apply | sdd-apply <change> | Implement code changes |
| sdd-verify | sdd-verify <change> | Validate implementation |
| sdd-archive | sdd-archive <change> | Archive completed changes |
| branch-pr | PR creation, opening PR | PR creation workflow |
| issue-creation | Creating issues, bug reports | Issue creation workflow |
| judgment-day | judgment day, adversarial review | Dual blind review protocol |
| go-testing | Go tests, Bubbletea TUI | Go testing patterns |
| skill-creator | Create new skill | Create AI agent skills |

## Project Conventions

### Primary Convention File
- `AGENTS.md` - Project manual with architecture, rules, and conventions

### Key Project Rules (from AGENTS.md)

**Backend (Python/FastAPI):**
- Always use `Depends(get_current_user)` for protected routes
- Include `tenant_id` filter in ALL queries (SELECT/INSERT/UPDATE/DELETE)
- Use global exception handler in main.py for CORS stability
- Maintenance Robot: idempotent PL/pgSQL patches in db.py

**Frontend (React/TypeScript):**
- Use wildcard routes: `path="/*"` for nested Routes
- Scroll Isolation: `h-screen`, `overflow-hidden` global, `overflow-y-auto` internal
- Axios: Authorization and X-Admin-Token injected automatically via api/axios.ts
- i18n: LanguageProvider wraps app, default English, use useTranslation()

**Architecture:**
- Multi-tenant with tenant_id isolation (mandatory)
- Hybrid calendar: local or Google Calendar per clinic
- 24h Human Override mechanism per (tenant_id, phone_number)
- Tool names: list_professionals, list_services, check_availability, book_appointment, list_my_appointments, cancel_appointment, reschedule_appointment, triage_urgency, derivhumano

## Skill Resolver Rules

**Compact Rules:**

### Python Backend
- Filter: `*.py` files in `orchestrator_service/`, `whatsapp_service/`, `bff_service/`, `shared/`
- Include: Auth layers with JWT, SQLAlchemy models, FastAPI routes, LangChain integration
- Must include tenant_id in all database queries

### React Frontend  
- Filter: `*.tsx`, `*.ts` files in `frontend_react/`
- Include: Components, hooks, context, routing
- Must follow scroll isolation patterns
- Use axios for API calls (already configured)

### Database
- Filter: `*.py` files with SQL, alembic migrations
- Include: db.py maintenance robot, migrations
- Patches must be idempotent (use DO $$ BEGIN ... END $$)
