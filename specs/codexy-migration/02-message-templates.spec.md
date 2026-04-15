# SPEC-02: Plantillas de Mensajes Reutilizables con Variables

| Campo       | Valor                          |
|-------------|--------------------------------|
| Origin      | crmcodexy migration            |
| Priority    | Media                          |
| Complexity  | Media                          |
| Status      | Draft                          |
| Created     | 2026-04-14                     |
| Author      | SDD Migration Agent            |

---

## Intent

Migrar el sistema de plantillas de mensajes reutilizables de crmcodexy al CRM VENTAS, adaptando la arquitectura a FastAPI + PostgreSQL multi-tenant. El feature permite a los usuarios de ventas crear, editar y reutilizar mensajes con variables dinámicas (`{{variable_name}}`) para WhatsApp, email y distintas etapas del funnel. El sistema NO reemplaza las HSM templates oficiales de WhatsApp —que son plantillas aprobadas por Meta—, sino que coexiste como capa de plantillas editables libres por el usuario.

---

## Requirements

### Funcionales

- **MUST** el sistema soportar 5 categorías de plantilla: `whatsapp`, `email`, `seguimiento`, `prospeccion`, `cierre`.
- **MUST** el contenido de una plantilla poder contener variables con el patrón `{{variable_name}}` (regex: `/\{\{(\w+)\}\}/g`).
- **MUST** el sistema extraer automáticamente las variables del contenido al crear o editar una plantilla; el usuario no las ingresa manualmente.
- **MUST** el sistema ofrecer 7 variables predefinidas para inserción rápida: `nombre`, `empresa`, `telefono`, `email`, `producto`, `precio`, `fecha`.
- **MUST** el editor de plantillas permitir insertar una variable en la posición del cursor (selectionStart/selectionEnd) mediante un botón de acceso rápido.
- **MUST** existir un modo "Vista Previa" que reemplace las variables con datos de muestra antes de guardar.
- **MUST** el sistema registrar un contador de uso (`uso_count`) que se incrementa cada vez que el usuario copia o usa una plantilla.
- **MUST** la tabla `plantillas` incluir `tenant_id` para aislamiento multi-tenant.
- **MUST** todas las operaciones de lectura y escritura filtrar por `tenant_id` del usuario autenticado.
- **MUST** existir endpoints CRUD completos: crear, leer (listado + detalle), actualizar, eliminar.
- **MUST** el listado soportar filtro por categoría y búsqueda por nombre o contenido.
- **MUST** el listado ordenarse por `uso_count DESC` por defecto.
- **SHOULD** existir un seed de plantillas base por tenant (adaptadas al contexto de ventas del CRM VENTAS).
- **SHOULD** el incremento de `uso_count` ser atómico (UPDATE ... SET uso_count = uso_count + 1).
- **SHOULD** los datos de muestra para vista previa ser configurables por tenant en el futuro (por ahora, valores fijos).
- **MAY** implementarse paginación en el listado si el volumen de plantillas supera 100 por tenant.
- **MUST NOT** el sistema de plantillas de usuario interferir con las HSM templates de WhatsApp oficial.
- **MUST NOT** un usuario acceder a plantillas de otro tenant.

### No funcionales

- **MUST** el tiempo de respuesta del listado ser inferior a 300ms para hasta 200 plantillas por tenant.
- **MUST** el sistema tolerar contenido de hasta 4000 caracteres por plantilla.
- **MUST** los nombres de plantilla ser únicos dentro de un mismo tenant (constraint de base de datos).

---

## Database Schema

### Tabla: `plantillas`

```sql
CREATE TABLE plantillas (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    nombre      TEXT NOT NULL,
    categoria   TEXT NOT NULL DEFAULT 'whatsapp'
                    CHECK (categoria IN ('whatsapp', 'email', 'seguimiento', 'prospeccion', 'cierre')),
    contenido   TEXT NOT NULL CHECK (char_length(contenido) <= 4000),
    variables   TEXT[] NOT NULL DEFAULT '{}',
    uso_count   INTEGER NOT NULL DEFAULT 0,
    created_by  UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Índices
CREATE INDEX idx_plantillas_tenant_id        ON plantillas(tenant_id);
CREATE INDEX idx_plantillas_tenant_categoria  ON plantillas(tenant_id, categoria);
CREATE INDEX idx_plantillas_tenant_uso_count  ON plantillas(tenant_id, uso_count DESC);
CREATE UNIQUE INDEX idx_plantillas_tenant_nombre ON plantillas(tenant_id, nombre);

-- Trigger para updated_at automático
CREATE TRIGGER trg_plantillas_updated_at
    BEFORE UPDATE ON plantillas
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

### Función RPC: `increment_plantilla_uso`

```sql
CREATE OR REPLACE FUNCTION increment_plantilla_uso(
    p_plantilla_id UUID,
    p_tenant_id    UUID
) RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    UPDATE plantillas
    SET uso_count = uso_count + 1,
        updated_at = now()
    WHERE id = p_plantilla_id
      AND tenant_id = p_tenant_id;
END;
$$;
```

> **Nota de migración**: La tabla fuente en crmcodexy no tiene `tenant_id` ni `UNIQUE(tenant_id, nombre)`. El seed de datos de crmcodexy puede importarse como plantillas base del primer tenant, renombrando los `nombre` que sean internos de Codexy a nombres neutrales.

---

## API Endpoints (FastAPI)

Base path: `/api/v1/plantillas`

Todas las rutas requieren token JWT válido. El `tenant_id` se extrae del token —nunca del request body.

### `GET /api/v1/plantillas`

Listado con filtros opcionales.

**Query params:**
| Param      | Tipo   | Descripción                                      |
|------------|--------|--------------------------------------------------|
| `categoria`| string | Filtro por categoría (opcional)                  |
| `q`        | string | Búsqueda libre en `nombre` y `contenido` (opcional) |
| `skip`     | int    | Paginación offset (default: 0)                   |
| `limit`    | int    | Paginación limit (default: 100, max: 200)        |

**Response `200`:**
```json
{
  "items": [
    {
      "id": "uuid",
      "nombre": "Saludo inicial WhatsApp",
      "categoria": "whatsapp",
      "contenido": "Hola {{nombre}}, soy de...",
      "variables": ["nombre", "empresa"],
      "uso_count": 12,
      "created_by": "uuid | null",
      "created_at": "2026-04-14T00:00:00Z",
      "updated_at": "2026-04-14T00:00:00Z"
    }
  ],
  "total": 42
}
```

### `GET /api/v1/plantillas/{id}`

Detalle de una plantilla.

**Response `200`:** objeto `PlantillaOut` (misma forma que ítem del listado).
**Response `404`:** `{ "detail": "Plantilla no encontrada" }` si no existe o pertenece a otro tenant.

### `POST /api/v1/plantillas`

Crear plantilla.

**Request body:**
```json
{
  "nombre": "string (requerido, max 100 chars)",
  "categoria": "whatsapp | email | seguimiento | prospeccion | cierre",
  "contenido": "string (requerido, max 4000 chars)"
}
```

> Las variables se extraen automáticamente del `contenido` en el backend. No se aceptan en el body.

**Response `201`:** objeto `PlantillaOut` creado.
**Response `409`:** nombre duplicado dentro del tenant.
**Response `422`:** validación fallida (contenido vacío, categoría inválida, etc.).

### `PUT /api/v1/plantillas/{id}`

Actualizar plantilla.

**Request body:** igual que POST (todos los campos requeridos para reemplazo completo).

**Response `200`:** objeto `PlantillaOut` actualizado.
**Response `404`:** no encontrada o de otro tenant.
**Response `409`:** nuevo nombre ya existe en el tenant (si cambió).

### `DELETE /api/v1/plantillas/{id}`

Eliminar plantilla.

**Response `204`:** sin cuerpo.
**Response `404`:** no encontrada o de otro tenant.

### `POST /api/v1/plantillas/{id}/uso`

Incrementar contador de uso (fire-and-forget desde el frontend al copiar).

**Response `200`:** `{ "uso_count": 13 }`
**Response `404`:** no encontrada o de otro tenant.

---

## UI Components (React 18)

### `PlantillasPage` — página contenedora

- Fetcha plantillas vía React Query (`useQuery`).
- Pasa estado de filtros (categoría activa, búsqueda) como props a los hijos.
- Maneja apertura de dialogs de crear/editar.

### `PlantillasCategoryTabs`

- Botones pill para cada categoría + "Todas".
- Muestra conteo de plantillas por categoría.
- Íconos: `MessageCircle` (whatsapp), `Mail` (email), `UserCheck` (seguimiento), `Target` (prospeccion), `Handshake` (cierre).
- Estado activo con ring visual.

### `PlantillasSearchBar`

- Input con ícono `Search`.
- Debounce de 300ms antes de filtrar.

### `PlantillasGrid`

- Grid responsive: 1 col mobile / 2 col sm / 3 col lg.
- Renderiza `PlantillaCard` por cada item.
- Estado vacío con CTA para crear primera plantilla.

### `PlantillaCard`

- Muestra: nombre, badge de categoría con color semántico, preview de primeros 120 chars (con variables resueltas a datos de muestra), chips de variables detectadas, contador de usos.
- Acciones en hover: Copiar (llama `/uso` endpoint), Editar, Eliminar.
- Click en card abre edición.

**Colores por categoría:**
```
whatsapp   → green
email      → blue
seguimiento → amber
prospeccion → purple
cierre     → emerald
```

### `PlantillaFormDialog`

- Modo crear y editar (prop `plantilla?: Plantilla`).
- Campos: nombre (Input), categoría (Select), contenido (Textarea con ref para cursor).
- Botones de variables predefinidas que insertan `{{variable}}` en la posición del cursor.
- Toggle "Vista Previa" / "Editar" que reemplaza variables con `SAMPLE_DATA`.
- Sección "Variables detectadas" con badges de colores (actualizada en tiempo real al escribir).
- Validación client-side antes de submit.
- Llama a `useMutation` de React Query; invalida cache `['plantillas']` en onSuccess.

**`SAMPLE_DATA` (datos de muestra fijos):**
```
nombre   → "Juan Pérez"
empresa  → "Soluciones CRM"
telefono → "+54 11 1234 5678"
email    → "juan@empresa.com"
producto → "Plan Pro"
precio   → "$150.000 ARS"
fecha    → "14 de abril"
```

### `PlantillaDeleteConfirm`

- Dialog de confirmación con texto: `"Se eliminará permanentemente la plantilla '{nombre}'. Esta acción no se puede deshacer."`.
- Botón destructivo con loading state.

---

## Scenarios (BDD)

### Scenario 1: Crear plantilla con variables detectadas automáticamente

```gherkin
Given el usuario está autenticado con tenant_id "tenant-001"
And navega a /plantillas
When hace clic en "Crear Plantilla"
And completa nombre "Saludo WhatsApp"
And selecciona categoría "whatsapp"
And escribe contenido "Hola {{nombre}}, soy de {{empresa}}. ¿Hablamos?"
And hace clic en "Crear Plantilla" (submit)
Then el sistema extrae automáticamente variables ["nombre", "empresa"]
And persiste la plantilla con tenant_id "tenant-001"
And la nueva plantilla aparece en el grid con uso_count 0
And los badges de variables muestran "nombre" y "empresa"
```

### Scenario 2: Insertar variable en posición del cursor

```gherkin
Given el dialog de creación está abierto
And el textarea de contenido tiene el texto "Hola , ¿cómo estás?"
And el cursor está posicionado en la posición 5 (después de "Hola ")
When el usuario hace clic en el botón "{{nombre}}"
Then el contenido del textarea pasa a ser "Hola {{nombre}}, ¿cómo estás?"
And el foco vuelve al textarea
And el cursor queda posicionado inmediatamente después de "{{nombre}}"
```

### Scenario 3: Vista previa con datos de muestra

```gherkin
Given el dialog tiene contenido "Hola {{nombre}}, tu cita en {{empresa}} es el {{fecha}}"
When el usuario activa el toggle "Vista Previa"
Then el panel de previsualización muestra "Hola Juan Pérez, tu cita en Soluciones CRM es el 14 de abril"
And el textarea original permanece oculto pero conserva su valor
When el usuario desactiva el toggle "Vista Previa"
Then el textarea vuelve a mostrarse con el contenido original con variables
```

### Scenario 4: Filtrado por categoría y búsqueda

```gherkin
Given el tenant tiene 10 plantillas: 4 de "whatsapp", 3 de "seguimiento", 3 de "cierre"
When el usuario hace clic en la categoría "seguimiento"
Then solo se muestran las 3 plantillas de "seguimiento"
And el tab "seguimiento" muestra el badge con conteo "3"
When el usuario escribe "demo" en el buscador
Then solo se muestran plantillas cuyo nombre o contenido contengan "demo"
And el filtro de categoría se mantiene activo simultáneamente
```

### Scenario 5: Copiar plantilla incrementa uso_count

```gherkin
Given existe una plantilla con id "uuid-123" y uso_count 5
When el usuario hace clic en el ícono de copiar en la PlantillaCard
Then el contenido de la plantilla se copia al portapapeles
And se muestra un toast "Contenido copiado al portapapeles"
And el frontend llama POST /api/v1/plantillas/uuid-123/uso
And la card actualiza optimistamente uso_count a 6
And la base de datos ejecuta UPDATE uso_count = uso_count + 1 atómicamente
```

### Scenario 6: Aislamiento multi-tenant

```gherkin
Given existen dos tenants: "tenant-A" y "tenant-B"
And "tenant-A" tiene 5 plantillas
And "tenant-B" tiene 3 plantillas
When un usuario de "tenant-B" consulta GET /api/v1/plantillas
Then solo recibe sus 3 plantillas
And no puede ver ni acceder a las plantillas de "tenant-A"
When un usuario de "tenant-B" intenta GET /api/v1/plantillas/{id-de-tenant-A}
Then recibe 404
```

### Scenario 7: Validación de nombre duplicado dentro del tenant

```gherkin
Given "tenant-001" ya tiene una plantilla llamada "Saludo Inicial"
When un usuario del mismo tenant intenta crear otra plantilla con nombre "Saludo Inicial"
Then el backend responde 409 Conflict
And el mensaje de error es "Ya existe una plantilla con ese nombre en tu organización"
And no se crea ningún registro en la base de datos
```

---

## Testing Strategy (TDD)

### Backend (FastAPI + pytest)

Seguir orden TDD: escribir el test, verlo fallar, implementar.

**Tests de unidad — extracción de variables:**
```python
def test_extract_variables_basic():
    assert extract_variables("Hola {{nombre}}") == ["nombre"]

def test_extract_variables_multiple():
    assert extract_variables("{{nombre}} de {{empresa}}") == ["nombre", "empresa"]

def test_extract_variables_dedup():
    assert extract_variables("{{nombre}} y {{nombre}}") == ["nombre"]

def test_extract_variables_none():
    assert extract_variables("Sin variables") == []

def test_extract_variables_custom():
    assert extract_variables("Texto {{mi_var_123}}") == ["mi_var_123"]
```

**Tests de integración — endpoints:**
- `test_create_plantilla_success` — POST devuelve 201 con variables extraídas
- `test_create_plantilla_duplicate_nombre` — POST devuelve 409
- `test_create_plantilla_empty_content` — POST devuelve 422
- `test_list_plantillas_filtered_by_tenant` — GET solo devuelve plantillas del tenant
- `test_list_plantillas_filter_categoria` — GET con `?categoria=whatsapp`
- `test_list_plantillas_search` — GET con `?q=demo` filtra por nombre y contenido
- `test_get_plantilla_wrong_tenant` — GET de otra empresa devuelve 404
- `test_update_plantilla_reextract_variables` — PUT recalcula variables del nuevo contenido
- `test_delete_plantilla` — DELETE devuelve 204 y ya no aparece en listado
- `test_increment_uso_atomic` — POST /uso actualiza correctamente sin race condition

**Tests de aislamiento:**
- Crear plantillas en dos tenants distintos, verificar que el listado de cada uno solo muestra las propias.

### Frontend (Vitest + React Testing Library)

- `PlantillaFormDialog` — inserción de variable en cursor: simular `selectionStart/End`, verificar nuevo valor del textarea.
- `PlantillaFormDialog` — toggle preview: verificar que el texto muestra datos de muestra y desaparece el textarea.
- `PlantillaFormDialog` — variables detectadas: escribir contenido con `{{x}}` y verificar que aparece el badge.
- `PlantillaCard` — click en copiar: mock clipboard API, verificar llamada a endpoint `/uso`.
- `PlantillasCategoryTabs` — click en categoría: verificar que el filtro cambia y el conteo es correcto.
- `PlantillasGrid` — estado vacío: verificar que se muestra el CTA cuando no hay items.

---

## Migration Notes

### Diferencias clave respecto a crmcodexy

| Aspecto              | crmcodexy (fuente)                        | CRM VENTAS (destino)                        |
|----------------------|-------------------------------------------|---------------------------------------------|
| Multi-tenant         | No (tabla sin tenant_id)                  | Sí (tenant_id obligatorio en toda query)    |
| Backend              | Next.js Server Actions + Supabase RPC     | FastAPI + SQLAlchemy / asyncpg              |
| Cache                | `use cache` + `cacheTag` (Next.js)        | Redis o cache de query (según infra)        |
| Auth                 | Supabase Auth (cookies)                   | JWT en header Authorization                 |
| Nombre único         | No constraint                             | UNIQUE(tenant_id, nombre)                   |
| HSM coexistencia     | N/A (no hay HSM)                          | Las plantillas de usuario son DISTINTAS de las HSM de WhatsApp oficial |

### Datos de seed

Los 19 templates del seed de crmcodexy (`007_seed_plantillas.sql`) se pueden importar como plantillas base del tenant inicial, con estas adaptaciones:
- Renombrar prefijos `codexy_` por nombres neutrales (ej: `estetica_inicial`, `dental_followup`).
- El `created_by` del seed original es `'system'` (text); en CRM VENTAS debe ser `NULL` (UUID o null de FK).
- Ajustar datos de muestra de SAMPLE_DATA a contexto argentino (precios en ARS, formato de fecha en español).

---

## Files to Create / Modify

### Backend (FastAPI)

```
app/
├── modules/
│   └── plantillas/
│       ├── __init__.py
│       ├── models.py          # SQLAlchemy: Plantilla model con tenant_id
│       ├── schemas.py         # Pydantic: PlantillaCreate, PlantillaOut, PlantillaUpdate
│       ├── service.py         # Lógica: extract_variables(), CRUD, increment_uso
│       ├── router.py          # FastAPI router: todos los endpoints
│       └── dependencies.py    # get_current_tenant() dependency
├── migrations/
│   └── versions/
│       └── xxxx_create_plantillas.py   # Alembic migration
└── seeds/
    └── plantillas_base.py     # Seed adaptado de crmcodexy
```

### Frontend (React 18)

```
src/
├── features/
│   └── plantillas/
│       ├── api/
│       │   └── plantillas.api.ts       # React Query hooks: useGetPlantillas, useCreatePlantilla, etc.
│       ├── components/
│       │   ├── PlantillasPage.tsx
│       │   ├── PlantillasCategoryTabs.tsx
│       │   ├── PlantillasSearchBar.tsx
│       │   ├── PlantillasGrid.tsx
│       │   ├── PlantillaCard.tsx
│       │   ├── PlantillaFormDialog.tsx
│       │   └── PlantillaDeleteConfirm.tsx
│       ├── hooks/
│       │   └── useVariableExtractor.ts  # Hook: extrae variables de un string en tiempo real
│       └── types/
│           └── plantilla.types.ts       # PlantillaCategoria, Plantilla, etc.
└── pages/
    └── PlantillasRoute.tsx              # Lazy-loaded route
```

---

## Dependencies

- **Backend**: `fastapi`, `sqlalchemy[asyncio]`, `asyncpg`, `pydantic v2`, `alembic`
- **Frontend**: `@tanstack/react-query`, `lucide-react`, UI component library existente en el proyecto
- **Database**: PostgreSQL (ya existente en CRM VENTAS)
- **Sin dependencias nuevas significativas**: la feature usa stacks ya presentes en el proyecto

---

## Acceptance Criteria

- [ ] La tabla `plantillas` existe con `tenant_id` y todos los índices descritos en el schema.
- [ ] La función SQL `increment_plantilla_uso` existe y es atómica.
- [ ] Todos los endpoints CRUD responden según la documentación de esta spec.
- [ ] El filtro por `tenant_id` está presente en TODA query que toca la tabla `plantillas` (verificado en code review y tests).
- [ ] Un usuario de un tenant no puede ver, editar, ni eliminar plantillas de otro tenant (tests de integración lo cubren).
- [ ] La extracción de variables desde el contenido funciona correctamente para los 7 nombres predefinidos y para variables custom con el patrón `\w+`.
- [ ] El modo "Vista Previa" muestra el contenido con variables reemplazadas por `SAMPLE_DATA`.
- [ ] El botón de inserción de variable posiciona el cursor correctamente luego del texto insertado.
- [ ] El `uso_count` se incrementa en exactamente 1 por cada acción de "Copiar".
- [ ] El nombre de plantilla es único por tenant (error 409 al duplicar).
- [ ] Todos los tests unitarios y de integración del backend pasan (`pytest` en CI).
- [ ] Todos los tests del frontend pasan (`vitest` en CI).
- [ ] Las plantillas de usuario NO aparecen en el flujo de HSM templates de WhatsApp oficial.
- [ ] La UI es funcional en mobile (1 columna) y desktop (3 columnas).
