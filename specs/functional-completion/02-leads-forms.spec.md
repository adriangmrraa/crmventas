# SPEC F-02: Leads Forms — Captura Pública de Leads

**Prioridad:** Media
**Complejidad:** Alta
**Estado:** No existe — implementación completa desde cero
**Página nueva en:** `/crm/formularios` (privada, CEO/secretary) + `/f/:slug` (pública, sin auth)

---

## Intent

El CEO necesita crear formularios web públicos que capturen leads directamente al CRM, al estilo de Google Forms pero integrados con el pipeline de ventas. Esta funcionalidad es completamente nueva: no existe ni en el frontend ni en el backend. La spec cubre el backend (FastAPI) y el frontend (React SPA).

---

## Estado Actual (Discovery)

### Frontend:
- No existe ninguna vista de formularios. Habría que crear la ruta y el componente.
- El router de `frontend_react` debe ser inspeccionado para agregar rutas.
- Existe `api/axios.ts` con instancia autenticada, y también necesitaremos una instancia pública (sin auth headers) para el endpoint de submission.

### Backend:
- No existe ningún router de formularios en `orchestrator_service/main.py` ni en `routes/`.
- Existen tablas de `leads` con campos `first_name`, `last_name`, `email`, `phone_number`, `status`, `tenant_id`, `tags`.
- Existe `POST /admin/core/crm/leads` (en `modules/crm_sales/routes`) para crear leads — la submission pública debe crear un lead via este endpoint internamente.
- No hay tabla `lead_forms` ni `lead_form_submissions` — hay que crearlas (o documentar la migración SQL necesaria).

---

## Requirements

### MUST (crítico)

#### Backend — Form Definition CRUD

- M1. `GET /admin/core/crm/forms` — listar formularios del tenant (paginado, CEO/secretary)
- M2. `POST /admin/core/crm/forms` — crear formulario con: `name`, `fields` (array de definición), `thank_you_message`, `redirect_url`, `active`
- M3. `GET /admin/core/crm/forms/{form_id}` — detalle del formulario
- M4. `PUT /admin/core/crm/forms/{form_id}` — actualizar formulario (CEO/secretary)
- M5. `DELETE /admin/core/crm/forms/{form_id}` — soft-delete (CEO only)
- M6. Cada formulario genera un `slug` único auto-generado (ej: `adf83k`) que se usa en la URL pública

#### Backend — Public Submission (sin auth)

- M7. `GET /f/{slug}` — retorna la definición del formulario (nombre, campos, mensaje de gracias) sin auth
- M8. `POST /f/{slug}/submit` — recibe los datos del formulario y crea un lead en el tenant correspondiente; sin autenticación requerida; rate-limited (5/min por IP)
- M9. Al submit: crear lead con `status='nuevo'`, `tags=['formulario_web', form.slug]`, `source='web_form'`
- M10. Al submit: registrar en tabla `lead_form_submissions` (form_id, lead_id, data JSONB, ip, submitted_at)

#### Backend — Analytics

- M11. `GET /admin/core/crm/forms/{form_id}/stats` — retorna `{ submissions_count, leads_created, conversion_rate, last_submission_at }`

#### Frontend — Form Builder (privado)

- M12. Vista `/crm/formularios` con lista de formularios: nombre, slug, submissions count, estado activo/inactivo, acciones (editar, eliminar, copiar link, copiar embed)
- M13. Modal/drawer de creación/edición con:
  - Nombre del formulario (required)
  - Lista de campos con drag-drop para reordenar
  - Botón "Agregar campo"
  - Para cada campo: tipo (text/email/phone/select/textarea), label, placeholder, required toggle, opciones (si tipo = select)
  - Mensaje de agradecimiento (textarea)
  - URL de redirect post-submit (opcional)
  - Toggle activo/inactivo
- M14. Panel de embed: mostrar URL pública y código iframe para copiar

#### Frontend — Public Form (sin auth)

- M15. Ruta pública `/f/:slug` que usa instancia axios sin auth headers
- M16. Renderiza el formulario dinámico según la definición del backend
- M17. Validación client-side: campos required, formato email, formato teléfono (10+ dígitos)
- M18. Post-submit: mostrar `thank_you_message` o redirigir a `redirect_url`
- M19. Estado de error si el formulario no existe (slug inválido) o está inactivo

### SHOULD (deseable)

- S1. Preview en tiempo real del formulario mientras se edita en el builder
- S2. Estadísticas en la lista: chip con número de submissions
- S3. Contador de submissions en la vista detalle del formulario
- S4. Selector de tags adicionales que se agregan al lead al hacer submit
- S5. Selector de seller asignado por defecto al lead captado via formulario
- S6. Validación de unicidad de email/phone al submit (si ya existe lead con mismo teléfono, actualizar en lugar de duplicar)

---

## API Endpoints

### Endpoints privados (requieren JWT)

| Método | Path | Descripción |
|--------|------|-------------|
| GET | `/admin/core/crm/forms` | Listar formularios del tenant |
| POST | `/admin/core/crm/forms` | Crear formulario |
| GET | `/admin/core/crm/forms/{form_id}` | Detalle formulario |
| PUT | `/admin/core/crm/forms/{form_id}` | Actualizar formulario |
| DELETE | `/admin/core/crm/forms/{form_id}` | Soft-delete formulario |
| GET | `/admin/core/crm/forms/{form_id}/stats` | Analytics de submissions |

### Endpoints públicos (sin auth, con rate-limit)

| Método | Path | Descripción |
|--------|------|-------------|
| GET | `/f/{slug}` | Definición pública del formulario |
| POST | `/f/{slug}/submit` | Submit de lead |

### Modelos Pydantic (backend)

```python
class FieldDefinition(BaseModel):
    id: str  # UUID generado en frontend para ordering
    type: Literal["text", "email", "phone", "select", "textarea"]
    label: str
    placeholder: Optional[str] = None
    required: bool = False
    options: Optional[List[str]] = None  # Solo para type='select'
    order: int

class CreateFormRequest(BaseModel):
    name: str
    fields: List[FieldDefinition]
    thank_you_message: str = "¡Gracias! Nos pondremos en contacto pronto."
    redirect_url: Optional[str] = None
    active: bool = True

class FormSubmitRequest(BaseModel):
    data: Dict[str, Any]  # { field_id: value }
```

---

## Esquema de DB requerido

```sql
-- Tabla de definición de formularios
CREATE TABLE lead_forms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
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

-- Tabla de submissions
CREATE TABLE lead_form_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    form_id UUID NOT NULL REFERENCES lead_forms(id),
    lead_id UUID REFERENCES leads(id),
    data JSONB NOT NULL,
    submitted_ip TEXT,
    submitted_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_lead_forms_tenant ON lead_forms(tenant_id);
CREATE INDEX idx_lead_forms_slug ON lead_forms(slug);
CREATE INDEX idx_lead_form_submissions_form ON lead_form_submissions(form_id);
```

---

## React Components

### Nuevos archivos a crear

```
frontend_react/src/
├── views/
│   ├── LeadFormsView.tsx        — Lista de formularios (privado)
│   └── PublicFormView.tsx       — Formulario público (ruta /f/:slug)
└── modules/crm_sales/components/forms/
    ├── FormBuilder.tsx           — Modal/drawer de creación/edición
    ├── FieldEditor.tsx           — Editor de un campo individual
    ├── DraggableFieldList.tsx    — Lista de campos con drag-drop (dnd-kit o similar)
    ├── FormPreview.tsx           — Preview en tiempo real
    ├── FormStats.tsx             — Panel de analytics
    └── EmbedCodePanel.tsx        — URL + iframe snippet
```

### Modificaciones requeridas

```
frontend_react/src/App.tsx (o router)  — Agregar rutas:
  /crm/formularios → LeadFormsView (protegida)
  /f/:slug → PublicFormView (pública, sin ProtectedRoute)

frontend_react/src/api/publicAxios.ts  — Crear instancia axios sin auth (baseURL igual, sin Authorization header)

frontend_react/src/components/Sidebar.tsx  — Agregar ítem "Formularios" en la nav del CRM
```

---

## Scenarios

### SC-01: CEO crea formulario de captación básico
**Dado** que el CEO está en `/crm/formularios`
**Cuando** hace click en "Nuevo formulario", ingresa nombre "Captación Cursos Mayo", agrega campos email (required) y teléfono (required) y un select "Curso de interés" con opciones [Ventas, Marketing, Liderazgo], y guarda
**Entonces** el formulario aparece en la lista con slug auto-generado (ej: `xk94ab`), estado activo, y URL pública `https://app.com/f/xk94ab`.

### SC-02: Potencial lead llena formulario público
**Dado** que existe el formulario con slug `xk94ab` y está activo
**Cuando** alguien visita `/f/xk94ab` sin estar logueado, completa email="juan@mail.com", teléfono="+5491187654321", curso="Ventas" y hace submit
**Entonces** se crea un lead en el tenant correspondiente con `status='nuevo'`, `tags=['formulario_web', 'xk94ab']`, `source='web_form'`, y se muestra el mensaje de gracias.

### SC-03: Formulario inactivo muestra error
**Dado** que el CEO desactivó el formulario `xk94ab`
**Cuando** alguien intenta acceder a `/f/xk94ab`
**Entonces** la página muestra "Este formulario ya no está disponible" sin renderizar los campos.

### SC-04: Rate limit en submissions
**Dado** que alguien (o un bot) hace 5 submissions desde la misma IP en menos de un minuto
**Cuando** intenta el sexto submit
**Entonces** el backend retorna 429 Too Many Requests y el frontend muestra "Demasiados intentos. Intentá de nuevo en un minuto."

### SC-05: Drag-drop reordena campos del formulario
**Dado** que el CEO tiene un formulario con campos: [Nombre, Email, Teléfono, Mensaje]
**Cuando** arrastra el campo "Mensaje" a la primera posición
**Entonces** la preview se actualiza en tiempo real mostrando [Mensaje, Nombre, Email, Teléfono] y al guardar el orden se persiste en `fields[].order`.

### SC-06: CEO copia código de embed
**Dado** que el formulario `xk94ab` existe y está activo
**Cuando** el CEO hace click en "Código de embed"
**Entonces** se muestra el snippet: `<iframe src="https://app.com/f/xk94ab" width="100%" height="600" frameborder="0"></iframe>` con botón "Copiar" que copia al portapapeles.

### SC-07: Validación de email inválido
**Dado** que el formulario tiene campo email como required
**Cuando** el visitante ingresa "noesunmail" y hace submit
**Entonces** la validación client-side bloquea el submit y muestra "Por favor ingresá un email válido" bajo el campo, sin llamar al backend.

---

## Testing Strategy

### Unit Tests (Vitest + Testing Library)
- `FormBuilder.test.tsx`: agregar campo, reordenar, validación de nombre requerido
- `PublicFormView.test.tsx`: render dinámico de campos, validación required, submit exitoso, mensaje de gracias
- `FieldEditor.test.tsx`: cambio de tipo, opciones de select

### Integration Tests
- Mock `GET /f/xk94ab` → render campos dinámicos
- Mock `POST /f/xk94ab/submit` → verificar payload con data correcta
- Mock `GET /admin/core/crm/forms` → render lista
- Mock `POST /admin/core/crm/forms` → formulario aparece en lista

### Backend Tests (pytest)
- `test_lead_forms.py`: crear form, get public form, submit → lead creado, rate limit 429, slug único

---

## Files to Create/Modify

| Archivo | Tipo |
|---------|------|
| `orchestrator_service/routes/lead_forms_routes.py` | Crear |
| `orchestrator_service/main.py` | Modificar — registrar router |
| `frontend_react/src/views/LeadFormsView.tsx` | Crear |
| `frontend_react/src/views/PublicFormView.tsx` | Crear |
| `frontend_react/src/modules/crm_sales/components/forms/FormBuilder.tsx` | Crear |
| `frontend_react/src/modules/crm_sales/components/forms/FieldEditor.tsx` | Crear |
| `frontend_react/src/modules/crm_sales/components/forms/DraggableFieldList.tsx` | Crear |
| `frontend_react/src/modules/crm_sales/components/forms/FormPreview.tsx` | Crear |
| `frontend_react/src/modules/crm_sales/components/forms/EmbedCodePanel.tsx` | Crear |
| `frontend_react/src/api/publicAxios.ts` | Crear |
| `frontend_react/src/App.tsx` (o router) | Modificar — agregar rutas |
| `frontend_react/src/components/Sidebar.tsx` | Modificar — agregar ítem |
| DB migration SQL | Crear — tablas `lead_forms` y `lead_form_submissions` |

---

## Acceptance Criteria

- [ ] CEO puede crear un formulario con al menos 3 tipos de campos
- [ ] Formulario creado tiene slug único y URL pública funcional
- [ ] URL pública es accesible sin autenticación
- [ ] Submit crea un lead en el CRM con tags correctos
- [ ] Formulario inactivo retorna 404/mensaje de error al visitante
- [ ] Rate limit de 5 submissions/min por IP está activo
- [ ] CEO puede ver cantidad de submissions por formulario
- [ ] Código de embed se puede copiar con un click
- [ ] Formulario con redirect_url redirige al visitante post-submit
- [ ] Drag-drop de campos funciona y persiste el orden

---

## Notas Técnicas

- **Slug generation:** usar `secrets.token_urlsafe(4)[:6]` en Python para generar slugs de 6 chars, verificar unicidad con SELECT antes de INSERT.
- **Instancia axios pública:** crear `publicAxios.ts` con `baseURL` del env (mismo que `api/axios.ts`) pero sin interceptor que agrega Authorization header. Necesario para que el formulario público funcione sin login.
- **Drag-drop:** evaluar `@dnd-kit/core` (ya puede estar en node_modules) vs `react-beautiful-dnd`. Verificar con `ls node_modules | grep dnd` antes de agregar dependencia.
- **CORS en endpoint público:** los endpoints `/f/...` deben permitir `allow_origins: ["*"]` ya que serán embebidos en sitios de terceros. Agregar override de CORS solo para estas rutas.
- **No usar LocalStorage** para estado del form builder — todo se guarda al hacer "Guardar", no hay auto-save.
