# Design F-02: Lead Forms — Captura Publica de Leads

**Spec:** `02-leads-forms.spec.md`
**Fecha:** 2026-04-14

---

## Arquitectura General

```
┌─────────────────────────────────────────────────────────────────┐
│  FRONTEND (React 19)                                            │
│                                                                 │
│  Privado (JWT)                     Publico (sin auth)           │
│  /crm/formularios                  /f/:slug                     │
│  ├─ LeadFormsView.tsx              └─ PublicFormView.tsx         │
│  └─ FormBuilder modal                 usa publicAxios            │
│     ├─ FieldEditor                    (sin Authorization header) │
│     ├─ DraggableFieldList                                       │
│     ├─ FormPreview                                              │
│     └─ EmbedCodePanel                                           │
└──────────────┬──────────────────────────────┬───────────────────┘
               │ axios (JWT)                   │ publicAxios
               ▼                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  BACKEND (FastAPI)                                              │
│                                                                 │
│  /admin/core/crm/forms/*           /f/{slug}                    │
│  (verify_admin_token)              /f/{slug}/submit             │
│  CRUD + stats                      (sin auth, rate-limited)     │
│  lead_forms_routes.py              lead_forms_routes.py          │
│                                                                 │
│  lead_forms_service.py ─────────────────────────────────────────│
│  ├─ CRUD lead_forms                                             │
│  ├─ slug generation (secrets.token_urlsafe)                     │
│  ├─ submit → create lead + record submission                    │
│  └─ stats aggregation                                           │
└──────────────┬──────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────┐
│  PostgreSQL                                                     │
│  ├─ lead_forms (definicion)                                     │
│  ├─ lead_form_submissions (registro)                            │
│  └─ leads (lead creado al submit)                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### Tabla `lead_forms`

```sql
CREATE TABLE lead_forms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    fields JSONB NOT NULL DEFAULT '[]',
    thank_you_message TEXT DEFAULT '¡Gracias! Nos pondremos en contacto pronto.',
    redirect_url TEXT,
    active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_lead_forms_tenant ON lead_forms(tenant_id);
CREATE INDEX idx_lead_forms_slug ON lead_forms(slug);
```

**Notas:**
- `slug` es UNIQUE global (no por tenant) — simplifica lookup publico sin necesidad de tenant_id
- `fields` es JSONB con array de `FieldDefinition` (ver contrato abajo)
- `is_deleted` para soft-delete — queries filtran `WHERE is_deleted = FALSE`
- `created_by` es UUID porque `users.id` es UUID en este proyecto

### Tabla `lead_form_submissions`

```sql
CREATE TABLE lead_form_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    form_id UUID NOT NULL REFERENCES lead_forms(id),
    lead_id UUID REFERENCES leads(id),
    data JSONB NOT NULL,
    submitted_ip TEXT,
    submitted_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_lead_form_submissions_form ON lead_form_submissions(form_id);
```

**Notas:**
- `lead_id` nullable — si la creacion del lead falla por alguna razon, el submission se registra igual
- `data` guarda `{ field_id: value }` tal como viene del frontend
- `submitted_ip` para rate-limiting analytics y trazabilidad

### Slug Generation

```python
import secrets

def generate_slug(length=6) -> str:
    """Genera slug alfanumerico de 6 chars, URL-safe."""
    return secrets.token_urlsafe(length)[:length]
```

Verificacion de unicidad: `SELECT 1 FROM lead_forms WHERE slug = $1` antes de INSERT. Retry hasta 3 intentos si hay colision (probabilidad negligible con 6 chars = ~2.8 billones combinaciones).

### Migracion — Parche en `db/migrations.py`

Sigue el patron existente de parches idempotentes con `DO $$ ... END $$`:

```python
# Parche 18: Lead Forms (SPEC F-02)
"""DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'lead_forms') THEN
    CREATE TABLE lead_forms (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        slug TEXT NOT NULL UNIQUE,
        fields JSONB NOT NULL DEFAULT '[]',
        thank_you_message TEXT DEFAULT '¡Gracias! Nos pondremos en contacto pronto.',
        redirect_url TEXT,
        active BOOLEAN DEFAULT TRUE,
        is_deleted BOOLEAN DEFAULT FALSE,
        created_by UUID REFERENCES users(id),
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX idx_lead_forms_tenant ON lead_forms(tenant_id);
    CREATE INDEX idx_lead_forms_slug ON lead_forms(slug);
END IF; END $$;""",

# Parche 19: Lead Form Submissions (SPEC F-02)
"""DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'lead_form_submissions') THEN
    CREATE TABLE lead_form_submissions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        form_id UUID NOT NULL REFERENCES lead_forms(id),
        lead_id UUID REFERENCES leads(id),
        data JSONB NOT NULL,
        submitted_ip TEXT,
        submitted_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX idx_lead_form_submissions_form ON lead_form_submissions(form_id);
END IF; END $$;""",
```

---

## Backend — Contratos API

### Modelos Pydantic

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from uuid import UUID
from datetime import datetime


class FieldDefinition(BaseModel):
    id: str                           # UUID string generado en frontend
    type: Literal["text", "email", "phone", "select", "textarea"]
    label: str = Field(..., min_length=1, max_length=200)
    placeholder: Optional[str] = None
    required: bool = False
    options: Optional[List[str]] = None  # Solo para type='select'
    order: int


class CreateFormRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    fields: List[FieldDefinition] = Field(..., min_length=1)
    thank_you_message: str = "¡Gracias! Nos pondremos en contacto pronto."
    redirect_url: Optional[str] = None
    active: bool = True


class UpdateFormRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    fields: Optional[List[FieldDefinition]] = None
    thank_you_message: Optional[str] = None
    redirect_url: Optional[str] = None
    active: Optional[bool] = None


class FormSubmitRequest(BaseModel):
    data: Dict[str, Any]  # { field_id: value }


class FormResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    fields: List[FieldDefinition]
    thank_you_message: str
    redirect_url: Optional[str]
    active: bool
    submissions_count: int = 0
    created_at: datetime
    updated_at: datetime


class PublicFormResponse(BaseModel):
    name: str
    fields: List[FieldDefinition]
    thank_you_message: str
    redirect_url: Optional[str]


class FormStatsResponse(BaseModel):
    submissions_count: int
    leads_created: int
    conversion_rate: float
    last_submission_at: Optional[datetime]
```

### Endpoints Privados — `routes/lead_forms_routes.py`

Router prefix: `/admin/core/crm/forms`

| Metodo | Path | Handler | Auth | Response |
|--------|------|---------|------|----------|
| GET | `/` | `list_forms` | `verify_admin_token` + `get_resolved_tenant_id` | `{ items: FormResponse[], total: int }` |
| POST | `/` | `create_form` | `verify_admin_token` + `get_resolved_tenant_id` | `FormResponse` |
| GET | `/{form_id}` | `get_form` | `verify_admin_token` + `get_resolved_tenant_id` | `FormResponse` |
| PUT | `/{form_id}` | `update_form` | `verify_admin_token` + `get_resolved_tenant_id` | `FormResponse` |
| DELETE | `/{form_id}` | `delete_form` | `verify_admin_token` + `get_resolved_tenant_id` | `{ ok: true }` |
| GET | `/{form_id}/stats` | `get_form_stats` | `verify_admin_token` + `get_resolved_tenant_id` | `FormStatsResponse` |

### Endpoints Publicos — Misma archivo, router separado

Router sin prefix (montado directamente en app):

| Metodo | Path | Handler | Auth | Rate Limit |
|--------|------|---------|------|------------|
| GET | `/f/{slug}` | `get_public_form` | NINGUNO | - |
| POST | `/f/{slug}/submit` | `submit_public_form` | NINGUNO | `5/minute` per IP (slowapi) |

**Estrategia de doble router:**
```python
# Router privado (CRUD, autenticado)
router = APIRouter(prefix="/admin/core/crm/forms", tags=["Lead Forms"])

# Router publico (sin auth, endpoints /f/...)
public_router = APIRouter(tags=["Lead Forms Public"])
```

Ambos se registran en `main.py`:
```python
from routes.lead_forms_routes import router as lead_forms_router
from routes.lead_forms_routes import public_router as lead_forms_public_router

app.include_router(lead_forms_router, tags=["Lead Forms"])
app.include_router(lead_forms_public_router, tags=["Lead Forms Public"])
```

### Rate Limiting

Usa `slowapi` (ya importado en `main.py`):

```python
from core.rate_limiter import limiter

@public_router.post("/f/{slug}/submit")
@limiter.limit("5/minute")
async def submit_public_form(request: Request, slug: str, body: FormSubmitRequest):
    ...
```

### Logica de Submit (Service)

```
submit_form(slug, data, ip_address):
  1. SELECT form WHERE slug = $1 AND is_deleted = FALSE
  2. Si form.active = FALSE → 404 "Formulario no disponible"
  3. Validar data contra form.fields:
     - Campos required presentes
     - Formato email basico (regex)
     - Formato phone (10+ digitos)
  4. Extraer first_name, last_name, email, phone_number del data (matching por field type)
  5. INSERT INTO leads (tenant_id, first_name, last_name, email, phone_number, status, source, tags)
     VALUES (form.tenant_id, ..., 'nuevo', 'web_form', ['formulario_web', form.slug])
  6. INSERT INTO lead_form_submissions (form_id, lead_id, data, submitted_ip)
  7. Return { success: true, thank_you_message, redirect_url }
```

**Mapping de campos a lead:**
- Campo con `type: "email"` → `leads.email` (primer campo email encontrado)
- Campo con `type: "phone"` → `leads.phone_number` (primer campo phone)
- Campos con label conteniendo "nombre" → `leads.first_name` / `leads.last_name`
- Si no hay match explicito, `first_name` = email username como fallback

### CORS para Endpoints Publicos

Los endpoints `/f/...` necesitan CORS permisivo para embeds en sitios de terceros. El CORS de FastAPI ya esta configurado globalmente en `main.py`. Si es restrictivo, agregar middleware adicional solo para rutas `/f/`:

```python
# En main.py, si el CORS global no permite "*":
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

# El CORS global del proyecto ya usa allow_origins=["*"] — suficiente
```

---

## Backend — Service Layer

### `services/lead_forms_service.py`

```python
class LeadFormsService:
    """CRUD + public submission logic for lead forms."""

    async def list(self, tenant_id: int, skip=0, limit=50) -> dict:
        """Lista formularios del tenant con submissions_count."""

    async def create(self, tenant_id: int, created_by: str, data: dict) -> dict:
        """Crea formulario con slug auto-generado."""

    async def get(self, tenant_id: int, form_id: str) -> dict | None:
        """Detalle de formulario por ID."""

    async def update(self, tenant_id: int, form_id: str, data: dict) -> dict | None:
        """Actualiza formulario existente."""

    async def delete(self, tenant_id: int, form_id: str) -> bool:
        """Soft-delete (is_deleted = TRUE)."""

    async def get_stats(self, tenant_id: int, form_id: str) -> dict:
        """Estadisticas: submissions_count, leads_created, conversion_rate, last_submission_at."""

    async def get_public_form(self, slug: str) -> dict | None:
        """Retorna formulario activo por slug (sin data sensible)."""

    async def submit(self, slug: str, data: dict, ip_address: str) -> dict:
        """Procesa submission: valida, crea lead, registra submission."""

    def _generate_slug(self) -> str:
        """Genera slug unico de 6 chars."""

    def _validate_submission(self, fields: list, data: dict) -> list[str]:
        """Valida data contra field definitions. Retorna lista de errores."""

    def _extract_lead_fields(self, fields: list, data: dict) -> dict:
        """Extrae first_name, last_name, email, phone del submission data."""

lead_forms_service = LeadFormsService()  # Singleton
```

### Queries SQL Clave

**List con submissions count:**
```sql
SELECT f.*, COALESCE(s.cnt, 0) AS submissions_count
FROM lead_forms f
LEFT JOIN (
    SELECT form_id, COUNT(*) AS cnt
    FROM lead_form_submissions
    GROUP BY form_id
) s ON s.form_id = f.id
WHERE f.tenant_id = $1 AND f.is_deleted = FALSE
ORDER BY f.created_at DESC
LIMIT $2 OFFSET $3
```

**Stats:**
```sql
SELECT
    COUNT(*) AS submissions_count,
    COUNT(lead_id) AS leads_created,
    MAX(submitted_at) AS last_submission_at
FROM lead_form_submissions
WHERE form_id = $1
```

---

## Frontend — Component Tree

```
App.tsx
├── /crm/formularios (ProtectedRoute ceo/secretary)
│   └── LeadFormsView.tsx
│       ├── Header: titulo + boton "Nuevo Formulario"
│       ├── FormList (tabla/cards)
│       │   └── FormRow: nombre, slug, submissions, active badge, actions
│       │       └── Actions: editar, eliminar, copiar link, copiar embed
│       ├── FormBuilder.tsx (Modal/Drawer)
│       │   ├── Input: nombre (required)
│       │   ├── DraggableFieldList.tsx
│       │   │   └── FieldEditor.tsx (por cada campo)
│       │   │       ├── Select: tipo (text/email/phone/select/textarea)
│       │   │       ├── Input: label
│       │   │       ├── Input: placeholder
│       │   │       ├── Toggle: required
│       │   │       ├── Input[]: options (condicional si tipo=select)
│       │   │       └── Boton: eliminar campo
│       │   ├── Boton: "Agregar campo"
│       │   ├── Textarea: thank_you_message
│       │   ├── Input: redirect_url
│       │   ├── Toggle: active
│       │   └── FormPreview.tsx (preview en tiempo real, lado derecho)
│       └── EmbedCodePanel.tsx (modal/popover)
│           ├── Input readonly: URL publica
│           ├── Textarea readonly: iframe snippet
│           └── Botones: copiar URL, copiar iframe
│
├── /f/:slug (SIN ProtectedRoute, SIN Layout)
│   └── PublicFormView.tsx
│       ├── FormHeader: nombre del formulario
│       ├── DynamicForm: campos renderizados segun fields[]
│       │   └── DynamicField: renderiza input segun type
│       ├── Submit button
│       ├── ThankYouMessage (post-submit)
│       ├── ErrorState: form not found / inactive
│       └── RateLimitError: 429 handling
```

### Ubicacion de archivos

```
frontend_react/src/
├── views/
│   └── PublicFormView.tsx                    -- NUEVO (ruta publica)
├── modules/crm_sales/
│   ├── views/
│   │   └── LeadFormsView.tsx                -- NUEVO (ruta privada)
│   └── components/forms/
│       ├── FormBuilder.tsx                  -- NUEVO
│       ├── FieldEditor.tsx                  -- NUEVO
│       ├── DraggableFieldList.tsx           -- NUEVO
│       ├── FormPreview.tsx                  -- NUEVO
│       ├── FormStats.tsx                    -- NUEVO
│       ├── EmbedCodePanel.tsx               -- NUEVO
│       └── types.ts                         -- NUEVO (interfaces compartidas)
├── api/
│   └── publicAxios.ts                       -- NUEVO
```

---

## Frontend — Estado y Data Flow

### LeadFormsView (Privado)

```
State:
  forms: FormResponse[]         -- lista de formularios
  loading: boolean
  error: string | null
  selectedForm: FormResponse | null  -- para editar
  showBuilder: boolean          -- modal abierto/cerrado
  showEmbed: { slug, name } | null

Data flow:
  mount → GET /admin/core/crm/forms → forms[]
  create → POST /admin/core/crm/forms → prepend to forms[]
  update → PUT /admin/core/crm/forms/{id} → replace in forms[]
  delete → DELETE /admin/core/crm/forms/{id} → remove from forms[]
  copy link → navigator.clipboard.writeText(publicUrl)
  copy embed → navigator.clipboard.writeText(iframeSnippet)
```

### PublicFormView (Publico)

```
State:
  form: PublicFormResponse | null
  formData: Record<string, string>  -- { field_id: value }
  errors: Record<string, string>    -- { field_id: error_message }
  status: 'loading' | 'ready' | 'submitting' | 'success' | 'error' | 'not_found' | 'rate_limited'
  submitError: string | null

Data flow:
  mount → GET /f/{slug} (publicAxios) → form
  input → update formData[field_id]
  submit → validate client-side → POST /f/{slug}/submit (publicAxios)
    success → status='success', show thank_you_message or redirect
    429 → status='rate_limited'
    404 → status='not_found'
```

### Instancia Axios Publica

```typescript
// api/publicAxios.ts
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const publicAxios = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
  // SIN interceptor de Authorization
  // SIN X-Tenant-ID — el tenant se resuelve desde el slug del form
});

export default publicAxios;
```

---

## Frontend — Validacion Client-Side

### PublicFormView Validacion

```typescript
function validateForm(fields: FieldDefinition[], data: Record<string, string>): Record<string, string> {
  const errors: Record<string, string> = {};

  for (const field of fields) {
    const value = (data[field.id] || '').trim();

    // Required check
    if (field.required && !value) {
      errors[field.id] = `${field.label} es obligatorio`;
      continue;
    }

    if (!value) continue; // skip optional empty

    // Type-specific
    if (field.type === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
      errors[field.id] = 'Por favor ingresa un email valido';
    }

    if (field.type === 'phone' && !/^\+?\d{10,15}$/.test(value.replace(/[\s\-()]/g, ''))) {
      errors[field.id] = 'El telefono debe tener al menos 10 digitos';
    }

    if (field.type === 'select' && field.options && !field.options.includes(value)) {
      errors[field.id] = 'Selecciona una opcion valida';
    }
  }

  return errors;
}
```

---

## Frontend — Routing

### App.tsx Modificaciones

```tsx
// Imports nuevos
import LeadFormsView from './modules/crm_sales/views/LeadFormsView';
import PublicFormView from './views/PublicFormView';

// Ruta PUBLICA — FUERA del ProtectedRoute, al mismo nivel que /login
<Route path="/f/:slug" element={<PublicFormView />} />

// Ruta PRIVADA — dentro del bloque protegido
<Route path="crm/formularios" element={
  <ProtectedRoute allowedRoles={['ceo', 'secretary']}>
    <LeadFormsView />
  </ProtectedRoute>
} />
```

**Critico:** La ruta `/f/:slug` va FUERA del `<ProtectedRoute>` wrapper y FUERA del `<Layout>` — es una pagina standalone sin sidebar, sin header, sin auth.

### Sidebar Modificacion

Agregar item en la seccion CRM del Sidebar:

```tsx
{
  label: 'Formularios',
  icon: ClipboardDocumentListIcon, // o DocumentPlusIcon
  path: '/crm/formularios',
  roles: ['ceo', 'secretary'],
}
```

---

## Error Handling

### Backend

| Situacion | HTTP Code | Response |
|-----------|-----------|----------|
| Form no encontrado (CRUD) | 404 | `{ detail: "Formulario no encontrado" }` |
| Form no encontrado (publico) | 404 | `{ detail: "Formulario no disponible" }` |
| Form inactivo (publico GET) | 404 | `{ detail: "Este formulario ya no esta disponible" }` |
| Validacion de submission | 422 | `{ detail: "Errores de validacion", errors: { field_id: "mensaje" } }` |
| Rate limit excedido | 429 | `{ detail: "Demasiados intentos. Intenta de nuevo en un minuto." }` |
| Slug generation fallo (3 intentos) | 500 | `{ detail: "Error interno al crear formulario" }` |

### Frontend

| Situacion | UI |
|-----------|-----|
| Form no encontrado | Pagina centered: "Este formulario no existe" con icono |
| Form inactivo | Pagina centered: "Este formulario ya no esta disponible" |
| Submit exitoso | Mostrar `thank_you_message` o redirect a `redirect_url` |
| Rate limited (429) | Alert: "Demasiados intentos. Intenta de nuevo en un minuto." |
| Network error | Alert: "Error de conexion. Verifica tu internet e intenta de nuevo." |
| Validacion client-side | Mensajes inline bajo cada campo con error |

---

## Dependencias Externas

### Frontend

| Paquete | Uso | Nota |
|---------|-----|------|
| `@dnd-kit/core` + `@dnd-kit/sortable` | Drag-drop de campos | Verificar si ya esta en node_modules. Si no, `yarn add @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities` |

### Backend

| Paquete | Uso | Nota |
|---------|-----|------|
| `slowapi` | Rate limiting | Ya instalado y configurado en `core/rate_limiter.py` |

---

## Seguridad

1. **Endpoints publicos sin auth** — NO exponen data del tenant, solo la definicion del formulario (nombre + campos)
2. **Rate limit** — 5/min por IP protege contra spam y bots
3. **Validacion server-side** — La data se valida contra las field definitions del formulario antes de crear el lead
4. **Slug opaco** — No expone tenant_id ni form_id, imposible enumerar formularios
5. **Soft-delete** — Formularios eliminados no son accesibles via slug (filtro `is_deleted = FALSE`)
6. **CORS** — Ya configurado globalmente con `allow_origins=["*"]` en main.py
7. **IP tracking** — Se registra la IP del visitante en submissions para auditoria

---

## Registro en `main.py`

Sigue el patron existente de try/except con logger:

```python
# ── Lead Forms (SPEC F-02) ──────────────────────────────────────────────
try:
    from routes.lead_forms_routes import router as lead_forms_router
    from routes.lead_forms_routes import public_router as lead_forms_public_router
    app.include_router(lead_forms_router, tags=["Lead Forms"])
    app.include_router(lead_forms_public_router, tags=["Lead Forms Public"])
    logger.info("✅ Lead Forms routes loaded")
except Exception as e:
    logger.warning(f"⚠️ Lead Forms routes not loaded: {e}")
```
