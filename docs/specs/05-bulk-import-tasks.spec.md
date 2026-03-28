# SPEC: Bulk Lead Import (CSV/Excel) + Task Management

**Fecha:** 2026-03-27
**Prioridad:** Alta
**Esfuerzo:** Medio (2 features independientes, pueden paralelizarse)
**Confidence:** 90%

---

## 1. Contexto y Objetivos

El CRM VENTAS no tiene forma de importar leads masivamente. Los vendedores que migran desde planillas Excel o exportaciones de Meta/Google Ads necesitan cargar cientos de leads a mano. Ademas, no existe un sistema de tareas/to-dos por lead, lo que impide dar seguimiento estructurado al pipeline de ventas.

**Objetivos:**
1. **Feature A** — Importar leads en bulk desde CSV/XLSX con preview, mapeo de columnas, y deduplicacion.
2. **Feature B** — CRUD de tareas vinculadas a leads con prioridades, estados, y recordatorios.

---

## 2. Feature A: Bulk Lead Import

### 2.1 Flujo General

```
Upload (drag & drop)  →  Preview (5 rows + mapeo)  →  Execute  →  Resumen
```

Patron identico al de ClinicForge (`/admin/patients/import/preview` + `/admin/patients/import/execute`), adaptado al modelo `leads`.

### 2.2 Backend

#### Endpoint 1: Preview

```
POST /admin/core/crm/leads/import/preview
Content-Type: multipart/form-data
Body: file (CSV or XLSX)
```

**Logica:**
1. Detectar formato (extension `.csv` o `.xlsx`).
2. Para CSV: auto-detectar encoding (UTF-8 → latin-1 fallback) usando `chardet`.
3. Parsear headers y mapearlos automaticamente via alias table:

| Header (case-insensitive) | Campo DB |
|---------------------------|----------|
| `nombre`, `first_name`, `name` | `first_name` |
| `apellido`, `last_name`, `surname` | `last_name` |
| `telefono`, `phone`, `celular`, `mobile`, `whatsapp` | `phone_number` |
| `email`, `correo`, `e-mail`, `mail` | `email` |
| `empresa`, `company`, `compania`, `negocio` | `company` |
| `origen`, `source`, `fuente` | `source` |
| `estado`, `status` | `status` |
| `etiquetas`, `tags` | `tags` |
| `notas`, `notes`, `observaciones` | `notes` |
| `vendedor`, `seller`, `asignado` | `assigned_seller_name` |

4. Validar limite: max **1000 filas**. Si excede, retornar error 400.
5. Normalizar telefono: strip espacios, agregar `+` si falta, quitar guiones.
6. Detectar duplicados contra DB: `SELECT phone_number FROM leads WHERE tenant_id = $1 AND phone_number = ANY($2)`.
7. Retornar response:

```json
{
  "total_rows": 847,
  "columns_detected": ["nombre", "telefono", "empresa", "origen"],
  "columns_mapped": {
    "nombre": "first_name",
    "telefono": "phone_number",
    "empresa": "company",
    "origen": "source"
  },
  "columns_unmapped": [],
  "sample_rows": [
    {"first_name": "Maria Lopez", "phone_number": "+5491112345678", "company": "ABC SRL", "source": "referral"},
    ...
  ],
  "duplicates_found": 23,
  "new_leads": 824
}
```

#### Endpoint 2: Execute

```
POST /admin/core/crm/leads/import/execute
Content-Type: application/json
Body: {
  "import_id": "uuid-from-preview",
  "duplicate_action": "skip" | "update",
  "column_mapping": { ... },      // allows manual override
  "default_status": "new",
  "default_source": "import_csv",
  "assigned_seller_id": null       // optional: assign all to a seller
}
```

**Logica:**
1. Recuperar archivo parseado de Redis (key: `import:{import_id}`, TTL 15 min) o re-parsear si no hay cache.
2. Para cada fila:
   - **Nuevo lead**: `INSERT INTO leads (...) VALUES (...)`.
   - **Duplicado + skip**: ignorar.
   - **Duplicado + update**: `UPDATE leads SET ... WHERE tenant_id = $1 AND phone_number = $2` usando COALESCE (solo rellena campos vacios, no sobreescribe datos existentes).
3. Batch insert con `executemany` para performance (chunks de 100).
4. Registrar en `lead_history` si existe.
5. Retornar response:

```json
{
  "total_processed": 847,
  "created": 824,
  "updated": 12,
  "skipped": 11,
  "errors": [
    {"row": 156, "error": "phone_number missing"}
  ]
}
```

#### Validaciones
- `phone_number` es obligatorio. Filas sin telefono se marcan como error (no se generan placeholders, a diferencia de ClinicForge el telefono es el identificador clave del CRM).
- `status` debe ser uno de: `new`, `contacted`, `interested`, `negotiation`, `closed_won`, `closed_lost`. Default: `new`.
- `email` formato validado si presente.
- `tags` puede venir como string separado por comas → se convierte a JSONB array.

### 2.3 Frontend

**Componente:** `LeadImportModal.tsx` en `frontend_react/src/modules/crm_sales/components/`

**Estados del modal:**

1. **Upload** — Zona drag & drop (o click to browse). Acepta `.csv`, `.xlsx`. Icono `Upload` de lucide-react. Texto: `t('leads.import.dropzone')`.
2. **Preview** — Tabla con 5 sample rows. Headers mapeados en verde, sin mapear en amarillo con selector dropdown. Badges mostrando `{new_leads} nuevos` y `{duplicates_found} duplicados`. Radio buttons para accion de duplicados (skip/update). Selector opcional de vendedor para asignar todos.
3. **Executing** — Spinner + progress text.
4. **Result** — Resumen con contadores (created, updated, skipped, errors). Si hay errores, tabla expandible con detalle por fila. Boton "Cerrar" + "Descargar errores (CSV)".

**Trigger:** Boton "Importar" en la vista de leads (`LeadsListView` o equivalente) con icono `FileUp`.

### 2.4 Migracion de Base de Datos

```sql
-- patch_019_bulk_import_company.sql

-- Add company field to leads (needed for import mapping)
ALTER TABLE leads ADD COLUMN IF NOT EXISTS company TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS notes TEXT;

CREATE INDEX IF NOT EXISTS idx_leads_company ON leads(tenant_id, company);

-- Import history tracking
CREATE TABLE IF NOT EXISTS lead_imports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    uploaded_by INTEGER REFERENCES users(id),
    filename TEXT NOT NULL,
    total_rows INTEGER NOT NULL,
    created_count INTEGER DEFAULT 0,
    updated_count INTEGER DEFAULT 0,
    skipped_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending', -- pending, processing, completed, failed
    errors JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_lead_imports_tenant ON lead_imports(tenant_id);
```

**Modelo Pydantic** (agregar a `core/models/crm.py`):

```python
class LeadImportPreviewResponse(BaseModel):
    import_id: str
    total_rows: int
    columns_detected: List[str]
    columns_mapped: Dict[str, str]
    columns_unmapped: List[str]
    sample_rows: List[Dict[str, Any]]
    duplicates_found: int
    new_leads: int

class LeadImportExecuteRequest(BaseModel):
    import_id: str
    duplicate_action: str = "skip"  # "skip" | "update"
    column_mapping: Optional[Dict[str, str]] = None
    default_status: str = "new"
    default_source: str = "import_csv"
    assigned_seller_id: Optional[UUID] = None

class LeadImportResult(BaseModel):
    total_processed: int
    created: int
    updated: int
    skipped: int
    errors: List[Dict[str, Any]]
```

### 2.5 Acceptance Criteria

```gherkin
Scenario: Importar CSV con mapeo automatico
  Given tengo un archivo "clientes.csv" con headers "nombre,telefono,empresa,origen"
  When subo el archivo en el modal de importacion
  Then veo la tabla de preview con 5 filas de muestra
  And las columnas aparecen mapeadas: nombre→first_name, telefono→phone_number, empresa→company, origen→source
  And veo el badge "X nuevos" y "Y duplicados"

Scenario: Ejecutar importacion con duplicados en modo update
  Given el preview muestra 100 leads nuevos y 15 duplicados
  And selecciono la opcion "Actualizar existentes" para duplicados
  When presiono "Importar"
  Then se crean 100 leads nuevos en la base de datos
  And se actualizan 15 leads existentes (solo campos vacios via COALESCE)
  And veo el resumen con created=100, updated=15, skipped=0

Scenario: Rechazo de archivo con mas de 1000 filas
  Given tengo un archivo Excel con 2500 filas
  When intento subirlo en el modal de importacion
  Then veo un error "El archivo excede el limite de 1000 filas"
  And el boton de importar permanece deshabilitado
```

---

## 3. Feature B: Task Management per Lead

### 3.1 Modelo de Datos

```sql
-- patch_020_lead_tasks.sql

CREATE TABLE IF NOT EXISTS lead_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    lead_id UUID REFERENCES leads(id) ON DELETE CASCADE NOT NULL,
    seller_id INTEGER REFERENCES users(id),           -- assigned seller (optional)
    created_by INTEGER REFERENCES users(id),          -- who created the task

    title TEXT NOT NULL,
    description TEXT,
    due_date TIMESTAMP,
    status TEXT DEFAULT 'pending',     -- pending, in_progress, completed
    priority TEXT DEFAULT 'medium',    -- low, medium, high, urgent
    completed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_lead_tasks_tenant ON lead_tasks(tenant_id);
CREATE INDEX IF NOT EXISTS idx_lead_tasks_lead ON lead_tasks(lead_id);
CREATE INDEX IF NOT EXISTS idx_lead_tasks_seller ON lead_tasks(tenant_id, seller_id);
CREATE INDEX IF NOT EXISTS idx_lead_tasks_due ON lead_tasks(tenant_id, due_date) WHERE status != 'completed';
CREATE INDEX IF NOT EXISTS idx_lead_tasks_status ON lead_tasks(tenant_id, status);
```

### 3.2 Backend Endpoints

Todos bajo el prefijo `/admin/core/crm` (misma ruta que el resto del modulo CRM).

| Method | Path | Descripcion |
|--------|------|-------------|
| `GET` | `/tasks` | Listar tareas del tenant (filtros: seller_id, status, priority, due_before, lead_id) |
| `GET` | `/tasks/{task_id}` | Detalle de una tarea |
| `POST` | `/tasks` | Crear tarea |
| `PUT` | `/tasks/{task_id}` | Actualizar tarea (titulo, descripcion, status, priority, due_date, seller_id) |
| `DELETE` | `/tasks/{task_id}` | Eliminar tarea |
| `GET` | `/leads/{lead_id}/tasks` | Tareas de un lead especifico |
| `POST` | `/leads/{lead_id}/tasks` | Quick-add tarea desde lead detail |

**Request body para crear/actualizar:**

```python
class TaskCreate(BaseModel):
    lead_id: UUID
    seller_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: str = "medium"  # low, medium, high, urgent

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = None      # pending, in_progress, completed
    priority: Optional[str] = None
    seller_id: Optional[int] = None

class TaskResponse(BaseModel):
    id: UUID
    tenant_id: int
    lead_id: UUID
    seller_id: Optional[int]
    created_by: Optional[int]
    title: str
    description: Optional[str]
    due_date: Optional[datetime]
    status: str
    priority: str
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    # Joins
    lead_name: Optional[str] = None
    seller_name: Optional[str] = None
```

**Logica de transiciones de status:**
- `pending` → `in_progress` | `completed`
- `in_progress` → `pending` | `completed`
- `completed` → `pending` (reabrir)
- Al cambiar a `completed`, se seta `completed_at = NOW()`. Al reabrir, `completed_at = NULL`.

### 3.3 Background Job: Due Date Reminders

**Archivo:** `orchestrator_service/jobs/task_reminders.py`

**Frecuencia:** Cada 30 minutos via scheduler (APScheduler o cron interno).

**Logica:**
1. Query: `SELECT * FROM lead_tasks WHERE status != 'completed' AND due_date IS NOT NULL AND due_date <= NOW() + INTERVAL '1 hour' AND reminded_at IS NULL`.
2. Para cada tarea vencida o proxima a vencer:
   - Emitir Socket.IO event `TASK_DUE_REMINDER` al seller (si tiene `seller_id`) o al tenant admin.
   - Crear notificacion en tabla `notifications` (si existe) o emitir solo via socket.
   - Marcar `reminded_at = NOW()` para no re-enviar.
3. Para tareas ya vencidas (due_date < NOW()):
   - Emitir `TASK_OVERDUE` event.

**Columna adicional en migracion:**

```sql
ALTER TABLE lead_tasks ADD COLUMN IF NOT EXISTS reminded_at TIMESTAMP;
```

### 3.4 Frontend

#### LeadDetailView — Nueva seccion "Tareas"

**Ubicacion:** Tab o seccion dentro de `LeadDetailView.tsx` (ya existe en `frontend_react/src/modules/crm_sales/views/LeadDetailView.tsx`).

**Layout:**
- Header: "Tareas" + boton `+ Nueva tarea` (icono `Plus` de lucide-react)
- Lista de tareas ordenadas por: overdue primero (rojo), luego por due_date ASC
- Cada tarea card muestra:
  - Checkbox para marcar completada (click directo → `PUT /tasks/{id}` con `status: "completed"`)
  - Titulo (tachado si completed)
  - Badge de prioridad: `low` (gris), `medium` (azul), `high` (naranja), `urgent` (rojo)
  - Due date con icono `Calendar` (rojo si overdue)
  - Avatar/nombre del seller asignado (si hay)
  - Menu kebab (editar, eliminar)
- Quick-add inline: input de titulo + selector de fecha + boton crear (sin abrir modal para tareas simples)

**Componentes nuevos:**
- `TaskList.tsx` — Lista de tareas con filtros
- `TaskCard.tsx` — Card individual de tarea
- `TaskFormModal.tsx` — Modal para crear/editar tarea completa (con descripcion, prioridad, seller)
- `TaskQuickAdd.tsx` — Inline form para agregar tarea rapida

#### Vista global de tareas (opcional, fase 2)

Pagina `/tasks` en sidebar para ver todas las tareas del tenant, con filtros por seller, status, prioridad, y fecha. Kanban view (pending | in_progress | completed). No incluido en esta spec — se puede agregar en un spec posterior.

### 3.5 Acceptance Criteria

```gherkin
Scenario: Crear tarea rapida desde lead detail
  Given estoy en el detalle del lead "Maria Lopez"
  When escribo "Llamar para seguimiento" en el campo de tarea rapida
  And selecciono fecha manana
  And presiono Enter o el boton de crear
  Then la tarea aparece en la lista con status "pending" y prioridad "medium"
  And la tarea tiene lead_id del lead actual y mi user_id como created_by

Scenario: Completar tarea con checkbox
  Given el lead "Juan Perez" tiene 3 tareas pendientes
  When hago click en el checkbox de la tarea "Enviar presupuesto"
  Then la tarea cambia a status "completed" con completed_at = ahora
  And el titulo aparece tachado con opacidad reducida
  And las tareas restantes se reordenan (completadas al final)

Scenario: Recordatorio de tarea proxima a vencer
  Given existe una tarea con due_date en 45 minutos y status "pending"
  When el job de recordatorios se ejecuta
  Then se emite un evento Socket.IO "TASK_DUE_REMINDER" al seller asignado
  And la tarea se marca con reminded_at = ahora
  And no se vuelve a enviar el recordatorio en la proxima ejecucion
```

---

## 4. Archivos a Crear

| Archivo | Descripcion |
|---------|-------------|
| `orchestrator_service/migrations/patch_019_bulk_import_company.sql` | Migracion: columnas company/notes en leads + tabla lead_imports |
| `orchestrator_service/migrations/patch_020_lead_tasks.sql` | Migracion: tabla lead_tasks |
| `orchestrator_service/services/lead_import_service.py` | Servicio de import: parse, preview, execute, dedup |
| `orchestrator_service/jobs/task_reminders.py` | Background job para recordatorios de tareas |
| `frontend_react/src/modules/crm_sales/components/LeadImportModal.tsx` | Modal de importacion con drag & drop + preview + result |
| `frontend_react/src/modules/crm_sales/components/TaskList.tsx` | Lista de tareas con filtros |
| `frontend_react/src/modules/crm_sales/components/TaskCard.tsx` | Card individual de tarea |
| `frontend_react/src/modules/crm_sales/components/TaskFormModal.tsx` | Modal crear/editar tarea |
| `frontend_react/src/modules/crm_sales/components/TaskQuickAdd.tsx` | Inline quick-add form |

## 5. Archivos a Modificar

| Archivo | Cambios |
|---------|---------|
| `orchestrator_service/core/models/crm.py` | Agregar modelos Pydantic: LeadImportPreview/Execute/Result, TaskCreate/Update/Response. Agregar `company` y `notes` a LeadBase/LeadCreate/LeadUpdate. |
| `orchestrator_service/modules/crm_sales/routes.py` | Agregar endpoints: `POST /leads/import/preview`, `POST /leads/import/execute`, CRUD `/tasks`, `/leads/{id}/tasks` |
| `frontend_react/src/modules/crm_sales/views/LeadDetailView.tsx` | Agregar seccion/tab de tareas con TaskList + TaskQuickAdd |
| `frontend_react/src/modules/crm_sales/views/LeadsListView.tsx` (o equivalente) | Agregar boton "Importar" que abre LeadImportModal |
| `frontend_react/src/locales/es.json` | Keys: `leads.import.*`, `tasks.*` |
| `frontend_react/src/locales/en.json` | Keys: `leads.import.*`, `tasks.*` |
| `frontend_react/src/locales/fr.json` | Keys: `leads.import.*`, `tasks.*` |
| `orchestrator_service/requirements.txt` | Agregar `openpyxl` (lectura XLSX), `chardet` (deteccion encoding) |
| `orchestrator_service/main.py` | Registrar job de task_reminders en scheduler (si existe) |

---

## 6. Dependencias Python

| Paquete | Version | Proposito |
|---------|---------|-----------|
| `openpyxl` | >=3.1.0 | Lectura de archivos .xlsx |
| `chardet` | >=5.0.0 | Auto-deteccion de encoding para CSV |

Ambos son livianos y no tienen conflictos conocidos con el stack actual.

---

## 7. Riesgos y Mitigaciones

| Riesgo | Impacto | Mitigacion |
|--------|---------|------------|
| **Archivo malicioso** (formula injection en CSV/XLSX) | Medio | Sanitizar celdas: strip `=`, `+`, `-`, `@` al inicio. No ejecutar formulas. |
| **Timeout en imports grandes** | Medio | Batch insert en chunks de 100. Si >500 rows, procesar en background task y notificar via Socket.IO al completar. BFF ya tiene timeout de 60s. |
| **Encoding incorrecto** | Bajo | Cadena de fallback: UTF-8 → latin-1 → cp1252. Chardet como detector primario. |
| **Telefono duplicado cross-tenant** | Nulo | Constraint `unique_lead_per_tenant` ya existe en leads table. Queries siempre filtran por `tenant_id`. |
| **Race condition en preview → execute** | Bajo | Preview guarda datos parseados en Redis con TTL 15 min. Si expira, se re-parsea el archivo (frontend puede re-subir). |
| **Tareas huerfanas al borrar lead** | Nulo | `ON DELETE CASCADE` en FK `lead_tasks.lead_id → leads.id`. |
| **Job de reminders duplicado en multi-instancia** | Medio | Usar Redis lock (`SETNX task_reminder_lock 1 EX 300`) para asegurar single execution. |
| **Columna company no existe en leads** | Alto (blocker) | Migracion `patch_019` agrega la columna ANTES de desplegar el feature. Ejecutar migracion primero. |

---

## 8. Orden de Implementacion

1. **Migraciones** — patch_019 (company + lead_imports) y patch_020 (lead_tasks). Ejecutar y verificar.
2. **Modelos Pydantic** — Actualizar `core/models/crm.py` con todos los modelos nuevos.
3. **Feature A backend** — `lead_import_service.py` + endpoints en `routes.py`.
4. **Feature A frontend** — `LeadImportModal.tsx` + boton en lista de leads.
5. **Feature B backend** — Endpoints CRUD de tasks en `routes.py`.
6. **Feature B frontend** — `TaskList`, `TaskCard`, `TaskQuickAdd`, `TaskFormModal` + integracion en `LeadDetailView`.
7. **Background job** — `task_reminders.py` + registro en scheduler.
8. **i18n** — Keys en es/en/fr.
9. **Tests** — Unit tests para import service (parsing, dedup) y task CRUD.

---

## 9. Fuera de Alcance (Fase 2)

- Vista global Kanban de tareas (`/tasks` en sidebar)
- Tareas recurrentes (repetir cada X dias)
- Notificaciones push/email para tareas vencidas (solo Socket.IO en esta fase)
- Import desde Google Sheets directo (solo archivo local)
- Mapeo de columnas drag & drop (solo dropdown en esta fase)
- Asignacion automatica de seller basada en reglas durante import
