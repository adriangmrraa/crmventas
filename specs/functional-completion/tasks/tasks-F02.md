# Tasks F-02: Lead Forms — Captura Publica de Leads

**Spec:** `02-leads-forms.spec.md`
**Design:** `design/design-F02.md`
**Fecha:** 2026-04-14

---

## Fase 1: Database Migration

- [ ] **T01** Agregar parche 18 en `orchestrator_service/db/migrations.py` — tabla `lead_forms` (id UUID, tenant_id INT FK, name TEXT, slug TEXT UNIQUE, fields JSONB, thank_you_message TEXT, redirect_url TEXT, active BOOLEAN, is_deleted BOOLEAN, created_by UUID FK, created_at, updated_at) con indices en tenant_id y slug
- [ ] **T02** Agregar parche 19 en `orchestrator_service/db/migrations.py` — tabla `lead_form_submissions` (id UUID, form_id UUID FK, lead_id UUID FK nullable, data JSONB, submitted_ip TEXT, submitted_at TIMESTAMPTZ) con indice en form_id

## Fase 2: Backend Service

- [ ] **T03** Crear `orchestrator_service/services/lead_forms_service.py` — clase `LeadFormsService` con singleton `lead_forms_service`
- [ ] **T04** Implementar `_generate_slug()` — `secrets.token_urlsafe(4)[:6]`, verificar unicidad con SELECT, retry hasta 3 intentos
- [ ] **T05** Implementar `create(tenant_id, created_by, data)` — INSERT lead_forms con slug auto-generado, retornar form completo
- [ ] **T06** Implementar `list(tenant_id, skip, limit)` — SELECT con LEFT JOIN submissions count, filtro `is_deleted=FALSE`, ORDER BY created_at DESC
- [ ] **T07** Implementar `get(tenant_id, form_id)` — SELECT por id + tenant_id, filtro `is_deleted=FALSE`
- [ ] **T08** Implementar `update(tenant_id, form_id, data)` — UPDATE parcial (solo campos presentes), actualizar `updated_at`
- [ ] **T09** Implementar `delete(tenant_id, form_id)` — UPDATE `is_deleted=TRUE` (soft-delete)
- [ ] **T10** Implementar `get_stats(tenant_id, form_id)` — COUNT submissions, COUNT lead_id NOT NULL, calcular conversion_rate, MAX submitted_at
- [ ] **T11** Implementar `get_public_form(slug)` — SELECT por slug WHERE active=TRUE AND is_deleted=FALSE, retornar solo name+fields+thank_you_message+redirect_url
- [ ] **T12** Implementar `_validate_submission(fields, data)` — validar required, formato email, formato phone (10+ digitos), opciones de select
- [ ] **T13** Implementar `_extract_lead_fields(fields, data)` — mapear campos por type: email→leads.email, phone→leads.phone_number, text con label "nombre"→first_name
- [ ] **T14** Implementar `submit(slug, data, ip_address)` — orquestar: get form → validate → extract lead fields → INSERT lead (status=nuevo, source=web_form, tags=[formulario_web, slug]) → INSERT submission → retornar thank_you_message + redirect_url

## Fase 3: Backend Routes

- [ ] **T15** Crear `orchestrator_service/routes/lead_forms_routes.py` — definir modelos Pydantic: `FieldDefinition`, `CreateFormRequest`, `UpdateFormRequest`, `FormSubmitRequest`
- [ ] **T16** Implementar router privado `router = APIRouter(prefix="/admin/core/crm/forms")` con `GET /` (list), `POST /` (create), `GET /{form_id}` (get), `PUT /{form_id}` (update), `DELETE /{form_id}` (delete), `GET /{form_id}/stats` (stats) — todos con `verify_admin_token` + `get_resolved_tenant_id`
- [ ] **T17** Implementar router publico `public_router = APIRouter()` con `GET /f/{slug}` y `POST /f/{slug}/submit`
- [ ] **T18** Aplicar rate limit `@limiter.limit("5/minute")` en `POST /f/{slug}/submit` usando `slowapi` existente
- [ ] **T19** Registrar ambos routers en `orchestrator_service/main.py` — `lead_forms_router` y `lead_forms_public_router` con try/except y logger (patron existente)

## Fase 4: Backend Tests

- [ ] **T20** Crear `orchestrator_service/tests/test_lead_forms_service.py` — tests unitarios del service: generate_slug unicidad, validate_submission (required, email, phone), extract_lead_fields mapping
- [ ] **T21** Crear `orchestrator_service/tests/test_lead_forms_routes.py` — tests de integracion: crear form, listar, get publico, submit crea lead, submit form inactivo 404, rate limit 429, delete soft-delete

## Fase 5: Frontend — Infraestructura

- [ ] **T22** Crear `frontend_react/src/api/publicAxios.ts` — instancia axios sin interceptor de Authorization, baseURL desde `VITE_API_URL`, solo Content-Type header
- [ ] **T23** Crear `frontend_react/src/modules/crm_sales/components/forms/types.ts` — interfaces TypeScript: `FieldDefinition`, `LeadForm`, `PublicFormData`, `FormStats`, `FormSubmitData`
- [ ] **T24** Verificar si `@dnd-kit/core` ya esta en node_modules. Si no, instalar `@dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities`

## Fase 6: Frontend — Componentes del Form Builder

- [ ] **T25** Crear `FieldEditor.tsx` — editor de un campo individual: select tipo (text/email/phone/select/textarea), input label, input placeholder, toggle required, input[] opciones (condicional si tipo=select), boton eliminar campo. Recibe `field`, `onChange`, `onRemove` como props
- [ ] **T26** Crear `DraggableFieldList.tsx` — lista de `FieldEditor` con drag-drop via `@dnd-kit/sortable`. Recibe `fields[]`, `onReorder`, `onChange`, `onRemove`. Actualiza `order` en cada campo al reordenar
- [ ] **T27** Crear `FormPreview.tsx` — preview en tiempo real del formulario: renderiza campos segun fields[] con estilos similares al formulario publico. Recibe `fields[]`, `formName`, `thankYouMessage`
- [ ] **T28** Crear `EmbedCodePanel.tsx` — modal/popover con URL publica (input readonly + boton copiar) e iframe snippet (textarea readonly + boton copiar). Recibe `slug`, `formName`. Usa `navigator.clipboard.writeText`
- [ ] **T29** Crear `FormStats.tsx` — panel con submissions_count, leads_created, conversion_rate, last_submission_at. Recibe `formId`, fetch `GET /admin/core/crm/forms/{formId}/stats`
- [ ] **T30** Crear `FormBuilder.tsx` — modal/drawer de creacion/edicion: input nombre (required), `DraggableFieldList`, boton "Agregar campo" (agrega campo text default), textarea thank_you_message, input redirect_url, toggle active, `FormPreview` (panel derecho). Boton guardar: POST o PUT segun modo. Recibe `form?` (para edicion), `onSave`, `onClose`

## Fase 7: Frontend — Vista Privada (LeadFormsView)

- [ ] **T31** Crear `frontend_react/src/modules/crm_sales/views/LeadFormsView.tsx` — vista principal con header "Formularios de Captacion" + boton "Nuevo Formulario"
- [ ] **T32** Implementar lista/tabla de formularios: columnas nombre, slug (con link), submissions count, badge activo/inactivo, acciones (editar, eliminar, copiar link, embed)
- [ ] **T33** Implementar accion "Copiar link" — copia `${window.location.origin}/f/${slug}` al clipboard con toast de confirmacion
- [ ] **T34** Implementar accion "Embed" — abre `EmbedCodePanel` con slug y nombre del formulario
- [ ] **T35** Implementar accion "Eliminar" — modal de confirmacion, DELETE al backend, remover de la lista
- [ ] **T36** Integrar `FormBuilder` modal — abrir en modo creacion (boton nuevo) o edicion (accion editar), on save actualizar lista

## Fase 8: Frontend — Vista Publica (PublicFormView)

- [ ] **T37** Crear `frontend_react/src/views/PublicFormView.tsx` — pagina standalone sin Layout, sin sidebar, sin auth. Usa `useParams` para obtener `slug`
- [ ] **T38** Implementar fetch del formulario: `GET /f/{slug}` via `publicAxios`. Estados: loading, ready, not_found, error
- [ ] **T39** Implementar renderizado dinamico de campos segun `fields[]`: input text, input email, input phone, select, textarea. Cada campo muestra label, placeholder, required indicator
- [ ] **T40** Implementar validacion client-side: campos required no vacios, email con regex basico, phone con 10+ digitos. Mostrar errores inline bajo cada campo
- [ ] **T41** Implementar submit: POST `/f/{slug}/submit` via `publicAxios` con `{ data: { field_id: value } }`. Deshabilitar boton durante submit
- [ ] **T42** Implementar post-submit: si `redirect_url` → `window.location.href = redirect_url`, sino mostrar `thank_you_message` centrado con checkmark
- [ ] **T43** Implementar error states: 404 → "Este formulario no existe", form inactivo → "Este formulario ya no esta disponible", 429 → "Demasiados intentos. Intenta de nuevo en un minuto."
- [ ] **T44** Aplicar estilos responsive: centrado, max-width 600px, mobile-friendly, dark/light theme basico

## Fase 9: Frontend — Routing y Sidebar

- [ ] **T45** Modificar `frontend_react/src/App.tsx` — agregar import `PublicFormView` y ruta `/f/:slug` FUERA del ProtectedRoute (al nivel de /login, /demo, /legal)
- [ ] **T46** Modificar `frontend_react/src/App.tsx` — agregar import `LeadFormsView` y ruta `crm/formularios` DENTRO del ProtectedRoute con `allowedRoles={['ceo', 'secretary']}`
- [ ] **T47** Modificar `frontend_react/src/components/Sidebar.tsx` — agregar item "Formularios" en seccion CRM con icono `ClipboardDocumentListIcon` o similar, path `/crm/formularios`, roles `['ceo', 'secretary']`

## Fase 10: Frontend Tests

- [ ] **T48** Test `FieldEditor.test.tsx` — render con campo text, cambio de tipo a select muestra opciones, toggle required, eliminar campo llama onRemove
- [ ] **T49** Test `FormBuilder.test.tsx` — render vacio (creacion), agregar campo, reordenar (mock dnd), nombre requerido bloquea submit, guardar llama onSave con data correcta
- [ ] **T50** Test `PublicFormView.test.tsx` — render campos dinamicos (mock GET /f/slug), validacion required bloquea submit, validacion email invalido, submit exitoso muestra thank_you_message, 404 muestra error, 429 muestra rate limit
- [ ] **T51** Test `EmbedCodePanel.test.tsx` — render URL y iframe snippet correctos, boton copiar llama clipboard API
- [ ] **T52** Test `LeadFormsView.test.tsx` — render lista (mock GET), crear formulario (mock POST), eliminar con confirmacion (mock DELETE)

---

## Dependencias entre fases

```
Fase 1 (DB) ──────────────────────────────────────────────────────────┐
  │                                                                    │
  ▼                                                                    │
Fase 2 (Service) → Fase 3 (Routes) → Fase 4 (Backend Tests)          │
                                                                       │
Fase 5 (FE Infra) ────────────────────────────────────────────────────┤
  │                                                                    │
  ▼                                                                    │
Fase 6 (Components) → Fase 7 (LeadFormsView) ─┐                      │
  │                                              │                      │
  │                    Fase 8 (PublicFormView) ──┤                      │
  │                                              │                      │
  └────────────────── Fase 9 (Routing) ─────────┘                      │
                         │                                              │
                         ▼                                              │
                    Fase 10 (FE Tests)                                  │
```

**Nota:** Fases 2+3 (backend) y Fases 5+6+7+8 (frontend) pueden ejecutarse en PARALELO.

## Estimacion

| Fase | Esfuerzo | Descripcion |
|------|----------|-------------|
| Fase 1 | 0.5h | 2 parches SQL idempotentes |
| Fase 2 | 3h | Service completo con slug generation, validation, submit logic |
| Fase 3 | 2h | 2 routers (privado + publico), modelos Pydantic, rate limit |
| Fase 4 | 2h | Tests unitarios service + tests integracion routes |
| Fase 5 | 0.5h | publicAxios + types + verificar dnd-kit |
| Fase 6 | 4h | 6 componentes (FormBuilder es el mas complejo, incluye dnd) |
| Fase 7 | 2h | Vista con lista, acciones, integracion FormBuilder |
| Fase 8 | 2.5h | Vista publica con validacion, submit, error states, responsive |
| Fase 9 | 0.5h | 3 archivos modificados (App.tsx x2, Sidebar) |
| Fase 10 | 3h | 5 archivos de test |
| **Total** | **20h** | |

## Archivos a Crear

| Archivo | Fase |
|---------|------|
| `orchestrator_service/services/lead_forms_service.py` | 2 |
| `orchestrator_service/routes/lead_forms_routes.py` | 3 |
| `orchestrator_service/tests/test_lead_forms_service.py` | 4 |
| `orchestrator_service/tests/test_lead_forms_routes.py` | 4 |
| `frontend_react/src/api/publicAxios.ts` | 5 |
| `frontend_react/src/modules/crm_sales/components/forms/types.ts` | 5 |
| `frontend_react/src/modules/crm_sales/components/forms/FieldEditor.tsx` | 6 |
| `frontend_react/src/modules/crm_sales/components/forms/DraggableFieldList.tsx` | 6 |
| `frontend_react/src/modules/crm_sales/components/forms/FormPreview.tsx` | 6 |
| `frontend_react/src/modules/crm_sales/components/forms/EmbedCodePanel.tsx` | 6 |
| `frontend_react/src/modules/crm_sales/components/forms/FormStats.tsx` | 6 |
| `frontend_react/src/modules/crm_sales/components/forms/FormBuilder.tsx` | 6 |
| `frontend_react/src/modules/crm_sales/views/LeadFormsView.tsx` | 7 |
| `frontend_react/src/views/PublicFormView.tsx` | 8 |

## Archivos a Modificar

| Archivo | Fase | Cambio |
|---------|------|--------|
| `orchestrator_service/db/migrations.py` | 1 | Agregar parches 18 y 19 |
| `orchestrator_service/main.py` | 3 | Registrar lead_forms_router + lead_forms_public_router |
| `frontend_react/src/App.tsx` | 9 | Agregar rutas /f/:slug (publica) y crm/formularios (privada) |
| `frontend_react/src/components/Sidebar.tsx` | 9 | Agregar item "Formularios" |
