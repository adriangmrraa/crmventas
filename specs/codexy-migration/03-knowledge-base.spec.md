# SPEC-03: Knowledge Base / Manuales

**Proyecto:** CRM VENTAS
**Migración desde:** crmcodexy
**Priority:** Media
**Complexity:** Media
**Estado:** Draft
**Fecha:** 2026-04-14
**Autor:** Migración codexy → CRM VENTAS

---

## 1. Intent

Migrar el sistema de Manuales (Knowledge Base) de crmcodexy al CRM VENTAS, adaptando el modelo
single-tenant (Supabase + Next.js) a la arquitectura multi-tenant (FastAPI + PostgreSQL + React 18)
del CRM de ventas.

El objetivo es proveer a los equipos de ventas (setters, closers) y supervisores (CEO, secretary)
acceso centralizado a documentación de entrenamiento, guiones, manejo de objeciones y procesos,
con control de escritura restringido a roles administrativos.

---

## 2. Requirements

Las palabras clave MUST, MUST NOT, SHOULD, MAY siguen RFC 2119.

### 2.1 Base de Datos

- R-01: La tabla `manuales` MUST incluir `tenant_id` (FK a `tenants.id`) para aislamiento multi-tenant.
- R-02: Toda consulta a `manuales` MUST filtrar por `tenant_id` extraído del token JWT autenticado.
- R-03: El campo `categoria` MUST ser una de las 6 categorías válidas: `general`, `guion_ventas`, `objeciones`, `producto`, `proceso`, `onboarding`.
- R-04: Los campos `titulo` y `contenido` MUST NOT ser nulos ni cadenas vacías.
- R-05: El campo `autor` SHOULD registrar el nombre del creador; MAY ser nulo.
- R-06: La tabla MUST incluir índices en `(tenant_id, categoria)` y `(tenant_id, updated_at DESC)`.

### 2.2 API

- R-07: El endpoint de listado MUST soportar filtrado por `categoria` y búsqueda full-text por `titulo` y `contenido` vía query params.
- R-08: Todos los endpoints MUST requerir autenticación JWT válida.
- R-09: Los endpoints de creación, edición y eliminación MUST requerir rol `ceo` o `secretary`. Roles `setter`, `closer`, y `professional` MUST NOT acceder a estas operaciones (403 Forbidden).
- R-10: El endpoint de listado y detalle MUST ser accesible para todos los roles autenticados del tenant.
- R-11: La API MUST devolver errores estructurados con `detail` en formato JSON.
- R-12: El endpoint de creación y edición MUST validar que `categoria` sea uno de los valores permitidos.

### 2.3 Frontend

- R-13: La vista MUST agrupar los manuales por categoría en secciones colapsables.
- R-14: Cada card MUST mostrar un preview de 150 caracteres del contenido (sin markup Markdown).
- R-15: El contenido expandido MUST renderizar Markdown básico: encabezados `#`/`##`, **negrita**, y listas `-`.
- R-16: La búsqueda MUST operar sobre `titulo`, `contenido` y `categoria` en el cliente o vía API.
- R-17: El botón "Nuevo Manual" y los controles de edición/eliminación MUST ser visibles únicamente para roles `ceo` y `secretary`.
- R-18: La vista MUST mostrar un estado vacío descriptivo cuando no hay manuales o sin resultados de búsqueda.
- R-19: El formulario de creación/edición MUST indicar al usuario que el contenido soporta Markdown básico.

---

## 3. Database Schema

### Migración SQL: `patch_019_manuales.py`

```sql
CREATE TABLE IF NOT EXISTS manuales (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    titulo      TEXT NOT NULL CHECK (char_length(trim(titulo)) > 0),
    contenido   TEXT NOT NULL CHECK (char_length(trim(contenido)) > 0),
    categoria   TEXT NOT NULL DEFAULT 'general'
                    CHECK (categoria IN (
                        'general', 'guion_ventas', 'objeciones',
                        'producto', 'proceso', 'onboarding'
                    )),
    autor       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_manuales_tenant_cat
    ON manuales(tenant_id, categoria);

CREATE INDEX IF NOT EXISTS idx_manuales_tenant_updated
    ON manuales(tenant_id, updated_at DESC);

-- Full-text search index (búsqueda por titulo + contenido)
CREATE INDEX IF NOT EXISTS idx_manuales_fts
    ON manuales USING GIN (
        to_tsvector('spanish', titulo || ' ' || contenido)
    );
```

### SQLAlchemy Model (agregar en `models.py`)

```python
class Manual(Base):
    __tablename__ = "manuales"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id  = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    titulo     = Column(Text, nullable=False)
    contenido  = Column(Text, nullable=False)
    categoria  = Column(String(50), nullable=False, default="general")
    autor      = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_manuales_tenant_cat", "tenant_id", "categoria"),
        Index("idx_manuales_tenant_updated", "tenant_id", updated_at.desc()),
        CheckConstraint(
            "categoria IN ('general','guion_ventas','objeciones','producto','proceso','onboarding')",
            name="ck_manuales_categoria"
        ),
    )
```

---

## 4. API Endpoints (FastAPI)

Router prefix: `/admin/core/manuales`
Tags: `["Knowledge Base"]`
Archivo: `orchestrator_service/routes/manuales_routes.py`

### 4.1 Pydantic Schemas

```python
CATEGORIAS_VALIDAS = Literal[
    "general", "guion_ventas", "objeciones",
    "producto", "proceso", "onboarding"
]

class ManualCreate(BaseModel):
    titulo:    str = Field(..., min_length=1, max_length=300)
    contenido: str = Field(..., min_length=1)
    categoria: CATEGORIAS_VALIDAS = "general"
    autor:     Optional[str] = None

class ManualUpdate(BaseModel):
    titulo:    Optional[str] = Field(None, min_length=1, max_length=300)
    contenido: Optional[str] = Field(None, min_length=1)
    categoria: Optional[CATEGORIAS_VALIDAS] = None
    autor:     Optional[str] = None

class ManualResponse(BaseModel):
    id:         UUID
    tenant_id:  int
    titulo:     str
    contenido:  str
    categoria:  str
    autor:      Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

### 4.2 Endpoints

| Método | Path                           | Roles permitidos             | Descripción                          |
|--------|--------------------------------|------------------------------|--------------------------------------|
| GET    | `/admin/core/manuales`         | Todos los roles autenticados | Listar manuales con filtros y búsqueda |
| GET    | `/admin/core/manuales/{id}`    | Todos los roles autenticados | Obtener un manual por ID             |
| POST   | `/admin/core/manuales`         | `ceo`, `secretary`           | Crear un nuevo manual                |
| PUT    | `/admin/core/manuales/{id}`    | `ceo`, `secretary`           | Actualizar manual existente          |
| DELETE | `/admin/core/manuales/{id}`    | `ceo`, `secretary`           | Eliminar manual                      |

### 4.3 Query Params — GET `/admin/core/manuales`

| Param      | Tipo   | Requerido | Descripción                                    |
|------------|--------|-----------|------------------------------------------------|
| `categoria`| string | No        | Filtrar por categoría exacta                   |
| `q`        | string | No        | Búsqueda full-text en titulo y contenido       |
| `limit`    | int    | No        | Default 50, max 200                            |
| `offset`   | int    | No        | Paginación, default 0                          |

### 4.4 Response Shape — GET `/admin/core/manuales`

```json
{
  "items": [...],
  "total": 42,
  "has_more": false
}
```

### 4.5 Error Responses

| Status | Caso                                                    |
|--------|---------------------------------------------------------|
| 400    | Categoria inválida, campos requeridos vacíos            |
| 403    | Rol sin permiso de escritura                            |
| 404    | Manual no encontrado o no pertenece al tenant           |
| 422    | Validación Pydantic fallida                             |

---

## 5. UI Components (React 18)

Directorio: `frontend_react/src/modules/crm_sales/`

### 5.1 Estructura de archivos

```
modules/crm_sales/
├── views/
│   └── ManualesView.tsx          # Vista principal (contenedor)
├── components/
│   ├── ManualCard.tsx            # Card expandible individual
│   ├── ManualDialog.tsx          # Dialog crear/editar
│   ├── ManualCategorySection.tsx # Sección por categoría con header
│   └── ManualMarkdownRenderer.tsx# Renderer Markdown básico
├── hooks/
│   └── useManuales.ts            # Estado, fetch, CRUD, búsqueda
└── types/
    └── manual.types.ts           # Interfaces TypeScript
```

### 5.2 Tipos TypeScript

```typescript
export type CategoriaManual =
  | 'general'
  | 'guion_ventas'
  | 'objeciones'
  | 'producto'
  | 'proceso'
  | 'onboarding';

export interface Manual {
  id: string;
  tenant_id: number;
  titulo: string;
  contenido: string;
  categoria: CategoriaManual;
  autor: string | null;
  created_at: string;
  updated_at: string;
}

export interface ManualesListResponse {
  items: Manual[];
  total: number;
  has_more: boolean;
}
```

### 5.3 Hook `useManuales`

Responsabilidades:
- Fetch inicial al montar, con `tenant_id` del `AuthContext`
- Filtro por categoría y búsqueda `q` como query params a la API
- CRUD: `createManual`, `updateManual`, `deleteManual` usando `api` (axios instance)
- Estado: `manuales`, `loading`, `error`, `search`, `categoriaFiltro`
- Refetch tras mutaciones exitosas
- Búsqueda con debounce de 300ms antes de enviar a la API

### 5.4 `ManualesView` (contenedor)

- Header con título "Manuales", contador de resultados
- Input de búsqueda (debounced)
- Filtro por categoría (pills/tabs)
- Botón "Nuevo Manual" — visible solo si `user.role` es `ceo` o `secretary`
- Secciones por categoría: `ManualCategorySection` por cada categoría presente
- Estado vacío: mensaje diferenciado para "sin manuales" vs "sin resultados"
- `ManualDialog` controlado por estado local

### 5.5 `ManualCard`

- Muestra `titulo` y badge de categoría con color único por categoría
- Preview de 150 chars del contenido (strip chars `#`, `*`, `-`)
- Botón "Ver más / Ver menos" para expandir
- Contenido expandido renderizado con `ManualMarkdownRenderer`
- Botones editar/eliminar visibles solo para roles `ceo` y `secretary`
- Confirmación antes de eliminar (ventana de confirmación o `window.confirm`)

### 5.6 `ManualMarkdownRenderer`

Soporta:
- `# Titulo` → `<h2>` (14px bold)
- `## Sección` → `<h3>` (13px semibold)
- `**texto**` → `<strong>`
- `- item` → lista `<ul>` con bullet custom
- Párrafos y saltos de línea

### 5.7 Paleta de colores por categoría

| Categoría       | Color token   |
|-----------------|---------------|
| general         | blue          |
| guion_ventas    | violet        |
| objeciones      | rose          |
| producto        | emerald       |
| proceso         | amber         |
| onboarding      | cyan          |

---

## 6. Scenarios

### SC-01: Vendedor lee un manual de objeciones

**Given** un usuario con rol `closer` autenticado en el tenant 7
**When** navega a `/manuales` y expande el manual "Cómo manejar objeciones de precio"
**Then** ve el contenido completo renderizado en Markdown
**And** los botones de editar y eliminar NO son visibles

### SC-02: CEO crea un manual nuevo

**Given** un usuario con rol `ceo`
**When** hace clic en "Nuevo Manual", completa titulo "Guion primera llamada", categoría "guion_ventas", contenido con formato Markdown, y confirma
**Then** se llama `POST /admin/core/manuales` con `tenant_id` del JWT
**And** el manual aparece en la sección "Guion de Ventas" de la vista sin reload completo

### SC-03: Intento de creación por setter (403)

**Given** un usuario con rol `setter`
**When** intenta `POST /admin/core/manuales` (directamente vía API)
**Then** recibe `403 Forbidden` con `{"detail": "Permiso insuficiente"}`
**And** el botón "Nuevo Manual" no es visible en la UI

### SC-04: Búsqueda por contenido

**Given** existen 10 manuales, 2 mencionan "rebatir precio"
**When** el usuario escribe "rebatir precio" en el campo de búsqueda
**Then** la vista muestra solo los 2 manuales relevantes agrupados por su categoría
**And** si no hay resultados, aparece el estado vacío "Sin resultados para 'rebatir precio'"

### SC-05: Aislamiento multi-tenant

**Given** el tenant 5 tiene 3 manuales y el tenant 8 tiene 7 manuales
**When** un usuario del tenant 5 consulta `GET /admin/core/manuales`
**Then** recibe únicamente los 3 manuales del tenant 5
**And** los manuales del tenant 8 nunca son retornados

### SC-06: Secretary edita un manual existente

**Given** un usuario con rol `secretary` y un manual existente con id `abc-123`
**When** abre el dialog de edición, modifica el contenido y confirma
**Then** se llama `PUT /admin/core/manuales/abc-123` con los campos modificados
**And** `updated_at` se actualiza en la base de datos
**And** la vista refleja el contenido actualizado

### SC-07: Filtro por categoría

**Given** la vista tiene manuales de todas las categorías
**When** el usuario selecciona el filtro "Objeciones"
**Then** solo se muestran los manuales de categoría `objeciones`
**And** las demás secciones desaparecen de la vista

---

## 7. Testing Strategy

### 7.1 Backend (pytest + pytest-asyncio)

Archivo: `orchestrator_service/tests/test_manuales.py`

```
test_list_manuales_authenticated_all_roles
test_list_manuales_filters_by_tenant_id
test_list_manuales_filter_by_categoria
test_list_manuales_search_by_titulo
test_list_manuales_search_by_contenido
test_get_manual_by_id_found
test_get_manual_by_id_not_found_returns_404
test_get_manual_wrong_tenant_returns_404
test_create_manual_ceo_success
test_create_manual_secretary_success
test_create_manual_setter_returns_403
test_create_manual_closer_returns_403
test_create_manual_titulo_vacio_returns_422
test_create_manual_categoria_invalida_returns_400
test_update_manual_ceo_success
test_update_manual_wrong_tenant_returns_404
test_delete_manual_ceo_success
test_delete_manual_not_found_returns_404
test_tenant_isolation_cannot_read_other_tenant
```

### 7.2 Frontend (Vitest + Testing Library)

Archivo: `frontend_react/src/modules/crm_sales/components/__tests__/ManualCard.test.tsx`
Archivo: `frontend_react/src/modules/crm_sales/hooks/__tests__/useManuales.test.ts`

```
ManualCard — muestra preview de 150 chars sin markdown chars
ManualCard — expande y renderiza markdown al hacer click en "Ver más"
ManualCard — oculta controles de edición para rol closer
ManualCard — muestra controles de edición para rol ceo
ManualMarkdownRenderer — renderiza h2, h3, negrita y listas
useManuales — llama a GET /admin/core/manuales al montar
useManuales — refetch tras createManual exitoso
useManuales — debounce 300ms en búsqueda antes de fetch
ManualesView — muestra estado vacío cuando items es []
ManualesView — oculta botón "Nuevo Manual" para rol setter
```

---

## 8. Migration Notes

### Diferencias clave codexy → CRM VENTAS

| Aspecto              | crmcodexy (origen)                        | CRM VENTAS (destino)                          |
|----------------------|-------------------------------------------|-----------------------------------------------|
| Auth                 | Supabase Auth + RLS policies              | JWT custom + `tenant_id` en query             |
| Roles escritura      | `admin` (Supabase)                        | `ceo`, `secretary`                            |
| Roles lectura        | `authenticated` (todos)                   | Todos los roles (`setter`, `closer`, etc.)    |
| Cache                | Next.js `"use cache"` + `cacheTag`        | Sin caching en v1; agregar Redis en v2        |
| Multi-tenancy        | No (single tenant por proyecto Supabase)  | `tenant_id` obligatorio en todas las queries  |
| Search               | Client-side filter sobre array en memoria | Query param `q` con FTS PostgreSQL (GIN)      |
| Framework backend    | Next.js Server Actions                    | FastAPI router                                |
| Framework frontend   | Next.js 15 + React 19                     | React 18 + Axios                              |
| ORM / DB client      | Supabase JS client                        | SQLAlchemy 2.0 async                          |

### Datos iniciales

Si el cliente ya tiene manuales en crmcodexy, se DEBE proveer un script de migración de datos
que:
1. Exporte desde Supabase (`pg_dump` o CSV de la tabla `manuales`)
2. Asigne el `tenant_id` correcto
3. Inserte con `INSERT INTO manuales (...) VALUES (...)` vía `psql` o script Python

### Consideraciones de seguridad

- El `tenant_id` NUNCA debe venir del request body; siempre debe resolverse del JWT via `get_resolved_tenant_id()`.
- El endpoint de eliminación debe verificar que el manual pertenece al tenant antes de borrar (evita IDOR).

---

## 9. Files

### Nuevos archivos a crear

| Archivo | Descripción |
|---------|-------------|
| `orchestrator_service/routes/manuales_routes.py` | FastAPI router con los 5 endpoints |
| `orchestrator_service/migrations/patch_019_manuales.py` | Migración de base de datos |
| `orchestrator_service/tests/test_manuales.py` | Tests de API (19 casos) |
| `frontend_react/src/modules/crm_sales/views/ManualesView.tsx` | Vista principal contenedor |
| `frontend_react/src/modules/crm_sales/components/ManualCard.tsx` | Card individual |
| `frontend_react/src/modules/crm_sales/components/ManualDialog.tsx` | Dialog crear/editar |
| `frontend_react/src/modules/crm_sales/components/ManualCategorySection.tsx` | Sección por categoría |
| `frontend_react/src/modules/crm_sales/components/ManualMarkdownRenderer.tsx` | Renderer Markdown |
| `frontend_react/src/modules/crm_sales/hooks/useManuales.ts` | Hook principal |
| `frontend_react/src/modules/crm_sales/types/manual.types.ts` | Interfaces TypeScript |

### Archivos a modificar

| Archivo | Cambio |
|---------|--------|
| `orchestrator_service/models.py` | Agregar modelo `Manual` |
| `orchestrator_service/main.py` | Registrar `manuales_router` |
| `frontend_react/src/modules/crm_sales/index.ts` | Exportar `ManualesView` |
| `frontend_react/src/App.tsx` o router | Agregar ruta `/manuales` |

---

## 10. Dependencies

- **Backend:** No nuevas dependencias. Usa FastAPI, SQLAlchemy, y PostgreSQL ya instalados.
- **Frontend:** No nuevas dependencias. Usa React 18, Axios, y el sistema de componentes existente.
- **DB:** PostgreSQL 14+ (requerido para `gen_random_uuid()` nativo y GIN FTS index con `spanish` config).

---

## 11. Acceptance Criteria

- [ ] AC-01: La tabla `manuales` existe en PostgreSQL con `tenant_id` FK y constraint de categoría.
- [ ] AC-02: `GET /admin/core/manuales` filtra correctamente por `tenant_id` del JWT.
- [ ] AC-03: `POST`/`PUT`/`DELETE` retornan 403 para roles `setter`, `closer`, `professional`.
- [ ] AC-04: La búsqueda por `q` encuentra manuales por `titulo` y `contenido`.
- [ ] AC-05: La vista agrupa manuales por categoría con la paleta de colores correcta.
- [ ] AC-06: El preview muestra máximo 150 chars sin caracteres Markdown (`#`, `*`, `-`).
- [ ] AC-07: El contenido expandido renderiza `#`, `##`, `**negrita**`, y listas `-` correctamente.
- [ ] AC-08: El botón "Nuevo Manual" y controles editar/eliminar son invisibles para `setter` y `closer`.
- [ ] AC-09: Un manual de tenant A no es retornado en queries del tenant B (aislamiento verificado con test).
- [ ] AC-10: Todos los tests backend (19) y frontend (10) pasan sin errores.
- [ ] AC-11: El estado vacío se muestra cuando no hay manuales o la búsqueda no tiene resultados.
- [ ] AC-12: El formulario valida que `titulo` y `contenido` no sean vacíos antes de enviar.
