# SPEC-01: Drive / File Storage System

## Origin: crmcodexy migration
## Priority: Alta
## Estimated Complexity: Alta

---

### Intent

CRM VENTAS actualmente no tiene sistema de almacenamiento de archivos. Los equipos comerciales necesitan adjuntar, organizar y acceder a documentos relacionados a clientes (contratos, propuestas, facturas, audios de llamadas, presentaciones) desde el mismo CRM, sin depender de herramientas externas.

Esta feature migra el sistema Drive de crmcodexy (Next.js + Supabase Storage) hacia la arquitectura de CRM VENTAS (FastAPI + PostgreSQL + almacenamiento compatible con S3). Se adapta el modelo multi-tenant con `tenant_id` en todas las tablas, y se reemplaza Supabase Storage por un backend configurable (MinIO o S3).

---

### Requirements

#### MUST (obligatorio)

- MUST soportar carpetas anidadas con jerarquía `parent_id` (árbol ilimitado)
- MUST soportar subida de archivos de hasta 50MB
- MUST aceptar los tipos MIME: `image/*`, `video/*`, `audio/*`, `application/pdf`, `application/msword`, `application/vnd.openxmlformats-officedocument.*`, `application/vnd.ms-excel`, `application/vnd.ms-powerpoint`, `application/zip`, `application/x-zip-compressed`
- MUST asociar carpetas y archivos a un `cliente_id` y a un `tenant_id`
- MUST generar URLs de descarga firmadas con expiración de 60 segundos
- MUST sanitizar el nombre del archivo antes de almacenarlo: reemplazar caracteres no alfanuméricos (excepto `.` y `-`) con `_`
- MUST soportar eliminación de carpetas (recursiva: borra subcarpetas y archivos)
- MUST soportar eliminación de archivos (elimina del storage y del registro en DB)
- MUST retornar el breadcrumb completo de una carpeta (traversal recursivo hasta la raíz)
- MUST aplicar autenticación JWT + `X-Admin-Token` + `tenant_id` en todos los endpoints
- MUST aislar datos por `tenant_id` (ningún tenant puede ver archivos de otro)

#### SHOULD (recomendado)

- SHOULD proveer indicador de progreso durante la subida (upload progress via streaming o presigned PUT)
- SHOULD soportar drag & drop en el frontend
- SHOULD mostrar íconos diferenciados por tipo MIME (imagen, video, audio, hoja de cálculo, archivo comprimido, documento)
- SHOULD soportar vista grilla / lista con toggle persistido en el cliente
- SHOULD mostrar el tamaño del archivo formateado (bytes, KB, MB)
- SHOULD mostrar la fecha de subida

#### MAY (opcional)

- MAY soportar renombrado de archivos y carpetas
- MAY soportar mover archivos entre carpetas
- MAY soportar búsqueda de archivos por nombre dentro de un cliente
- MAY soportar previsualización inline de imágenes y PDFs

---

### Database Schema

> Todas las tablas incluyen `tenant_id` (multi-tenant). Se usa UUID v4 para todos los IDs.

```sql
-- Carpetas del drive, soportan jerarquía ilimitada via parent_id
CREATE TABLE drive_folders (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    cliente_id  UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    nombre      VARCHAR(255) NOT NULL,
    parent_id   UUID REFERENCES drive_folders(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_drive_folders_tenant    ON drive_folders(tenant_id);
CREATE INDEX idx_drive_folders_cliente   ON drive_folders(cliente_id);
CREATE INDEX idx_drive_folders_parent    ON drive_folders(parent_id);

-- Archivos del drive, siempre vinculados a una carpeta y a un cliente
CREATE TABLE drive_files (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    cliente_id      UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    folder_id       UUID NOT NULL REFERENCES drive_folders(id) ON DELETE CASCADE,
    nombre          VARCHAR(255) NOT NULL,        -- nombre original (display)
    storage_path    VARCHAR(1024) NOT NULL UNIQUE, -- ruta en el bucket (sanitizada)
    mime_type       VARCHAR(127) NOT NULL,
    size_bytes      BIGINT NOT NULL CHECK (size_bytes > 0),
    uploaded_by     UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_drive_files_tenant    ON drive_files(tenant_id);
CREATE INDEX idx_drive_files_cliente   ON drive_files(cliente_id);
CREATE INDEX idx_drive_files_folder    ON drive_files(folder_id);
```

**Notas de diseño:**
- `storage_path` es la ruta interna en el bucket (no la URL pública). Las URLs se generan en runtime (signed URL).
- El `nombre` en `drive_files` guarda el nombre original legible para el usuario. El nombre sanitizado solo se usa para construir `storage_path`.
- La eliminación de una carpeta es `CASCADE` en DB para subcarpetas, pero los archivos físicos en el bucket deben eliminarse explícitamente desde el backend (no hay CASCADE en el objeto storage).
- `storage_path` tiene el formato: `{tenant_id}/{cliente_id}/{folder_id}/{uuid}_{nombre_sanitizado}`

---

### API Endpoints

Prefijo base: `/api/v1/drive`

Todos los endpoints requieren header `Authorization: Bearer <token>` y resuelven `tenant_id` desde el JWT o `X-Admin-Token`.

| Método | Path | Descripción |
|--------|------|-------------|
| `GET`    | `/folders`                              | Lista carpetas raíz de un cliente |
| `GET`    | `/folders/{folder_id}`                  | Detalle de una carpeta |
| `GET`    | `/folders/{folder_id}/breadcrumb`       | Breadcrumb completo hasta la raíz |
| `GET`    | `/folders/{folder_id}/children`         | Subcarpetas directas de una carpeta |
| `POST`   | `/folders`                              | Crear carpeta (con `parent_id` opcional) |
| `DELETE` | `/folders/{folder_id}`                  | Eliminar carpeta y todo su contenido |
| `GET`    | `/files`                                | Lista archivos de una carpeta (`?folder_id=`) |
| `GET`    | `/files/{file_id}/download`             | Genera signed URL de descarga (60s) |
| `POST`   | `/files/upload`                         | Sube un archivo (multipart/form-data) |
| `DELETE` | `/files/{file_id}`                      | Elimina archivo del storage y de la DB |

#### Detalle de endpoints clave

**POST `/folders`**
```json
// Request body
{
  "nombre": "Contratos 2025",
  "cliente_id": "uuid",
  "parent_id": "uuid | null"
}

// Response 201
{
  "id": "uuid",
  "nombre": "Contratos 2025",
  "cliente_id": "uuid",
  "parent_id": "uuid | null",
  "created_at": "2025-04-14T10:00:00Z"
}
```

**POST `/files/upload`**
```
Content-Type: multipart/form-data

Fields:
  - file: <binary>          (required, max 50MB)
  - folder_id: uuid         (required)
  - cliente_id: uuid        (required)
```
```json
// Response 201
{
  "id": "uuid",
  "nombre": "propuesta_comercial.pdf",
  "mime_type": "application/pdf",
  "size_bytes": 2048576,
  "folder_id": "uuid",
  "created_at": "2025-04-14T10:00:00Z"
}
```

**GET `/files/{file_id}/download`**
```json
// Response 200
{
  "url": "https://storage.example.com/...?X-Amz-Expires=60&...",
  "expires_in": 60
}
```

**GET `/folders/{folder_id}/breadcrumb`**
```json
// Response 200
{
  "breadcrumb": [
    { "id": "uuid-raiz", "nombre": "Cliente ABC" },
    { "id": "uuid-nivel1", "nombre": "2025" },
    { "id": "uuid-nivel2", "nombre": "Contratos" }
  ]
}
```

**DELETE `/folders/{folder_id}`**
- Elimina recursivamente todas las subcarpetas y sus archivos del storage (bucket)
- Luego elimina los registros de DB (el CASCADE de FK limpia el resto)
- Response 204 No Content

---

### UI Components

Todos los componentes son React 18 + TypeScript + Tailwind 3.4. Se generan los hooks de API via Orval desde el OpenAPI de FastAPI.

| Componente | Responsabilidad |
|------------|-----------------|
| `DriveExplorer` | Contenedor principal. Gestiona estado de carpeta activa, vista (grilla/lista), y breadcrumb. |
| `DriveBreadcrumb` | Muestra la ruta actual con links clicables. Props: `items: BreadcrumbItem[]`, `onNavigate`. |
| `DriveFolderGrid` / `DriveFolderList` | Renderiza carpetas en vista grilla o lista. |
| `DriveFileGrid` / `DriveFileList` | Renderiza archivos con ícono MIME, nombre, tamaño y fecha. |
| `DriveViewToggle` | Botón toggle grilla/lista. Estado persistido en `localStorage`. |
| `DriveUploadZone` | Área drag & drop con input file fallback. Muestra barra de progreso durante upload. |
| `DriveCreateFolderModal` | Modal para crear carpeta nueva con validación de nombre. |
| `DriveFileIcon` | Selecciona ícono según MIME type: `Image`, `FileVideo`, `FileAudio`, `FileSpreadsheet`, `FileArchive`, `FileText`. |
| `DriveDeleteConfirmModal` | Modal de confirmación antes de eliminar carpeta o archivo. |

#### Árbol de componentes

```
DriveExplorer
├── DriveBreadcrumb
├── DriveViewToggle
├── DriveUploadZone
├── DriveCreateFolderModal
├── DriveDeleteConfirmModal
└── DriveContent (condicional según vista)
    ├── DriveFolderGrid | DriveFolderList
    └── DriveFileGrid  | DriveFileList
        └── DriveFileIcon
```

---

### Scenarios (Given/When/Then)

**Escenario 1: Crear carpeta raíz para un cliente**
```
Given: El usuario está autenticado con tenant_id válido
  And: El cliente existe y pertenece al mismo tenant
When: POST /api/v1/drive/folders con { nombre: "Documentos", cliente_id: "...", parent_id: null }
Then: Se crea la carpeta en drive_folders con parent_id = NULL
  And: La respuesta es 201 con el id y nombre de la carpeta creada
  And: La carpeta NO es visible para otros tenants
```

**Escenario 2: Subir un archivo PDF a una carpeta existente**
```
Given: Existe la carpeta con folder_id="abc" del tenant
  And: El archivo es un PDF de 2MB (dentro del límite de 50MB)
When: POST /api/v1/drive/files/upload con el archivo y folder_id="abc"
Then: El archivo se almacena en el bucket con storage_path sanitizado
  And: Se registra en drive_files con el mime_type, size_bytes y folder_id correctos
  And: La respuesta es 201 con los metadatos del archivo
```

**Escenario 3: Descargar un archivo con signed URL**
```
Given: Existe el archivo con file_id="xyz" del tenant
When: GET /api/v1/drive/files/xyz/download
Then: La respuesta incluye una URL firmada con expiración de 60 segundos
  And: La URL permite acceso directo al objeto en el bucket sin autenticación adicional
  And: Después de 60 segundos la URL ya no es válida
```

**Escenario 4: Navegar breadcrumb de carpeta anidada**
```
Given: Existe una jerarquía: Raíz → 2025 → Contratos → Firmados
  And: El usuario navega a la carpeta "Firmados"
When: GET /api/v1/drive/folders/{id-firmados}/breadcrumb
Then: La respuesta retorna la lista ordenada de ancestros: [Raíz, 2025, Contratos, Firmados]
  And: Cada elemento incluye su id y nombre
```

**Escenario 5: Eliminar carpeta con contenido anidado**
```
Given: La carpeta "2025" contiene subcarpetas y archivos en el bucket
When: DELETE /api/v1/drive/folders/{id-2025}
Then: Se eliminan todos los archivos físicos del bucket (sin dejar huérfanos)
  And: Se eliminan todos los registros de drive_files y drive_folders en cascada
  And: La respuesta es 204 No Content
```

**Escenario 6: Rechazar archivo que supera el límite de tamaño**
```
Given: El usuario intenta subir un archivo de 75MB
When: POST /api/v1/drive/files/upload con el archivo
Then: La respuesta es 422 Unprocessable Entity
  And: El mensaje de error indica que el límite máximo es 50MB
  And: Ningún archivo queda almacenado en el bucket
```

**Escenario 7: Aislamiento multi-tenant**
```
Given: El tenant A tiene el archivo con file_id="xyz"
  And: El usuario autenticado pertenece al tenant B
When: GET /api/v1/drive/files/xyz/download
Then: La respuesta es 404 Not Found (no expone que el recurso existe)
  And: No se genera ninguna signed URL
```

**Escenario 8: Sanitización de nombre de archivo**
```
Given: El usuario sube un archivo llamado "Contrato Pérez & Asociados (2025).pdf"
When: El backend procesa el archivo
Then: El storage_path contiene el nombre sanitizado: "Contrato_P_rez___Asociados__2025_.pdf"
  And: El campo `nombre` en drive_files conserva el nombre original: "Contrato Pérez & Asociados (2025).pdf"
```

---

### Testing Strategy

Se aplica TDD estricto. El orden es: test primero → implementación → refactor.

#### Backend (FastAPI + pytest + pytest-asyncio)

| Capa | Qué testear |
|------|-------------|
| **Unit — sanitización** | `sanitize_filename()` con caracteres especiales, unicode, múltiples espacios, extensiones compuestas |
| **Unit — breadcrumb** | Traversal recursivo: carpeta raíz, cadena de 2, cadena de 5, ciclo detectado (guard) |
| **Unit — storage service** | Mock del cliente S3/MinIO: upload, delete, presigned URL generada con TTL correcto |
| **Integration — endpoints** | Cada endpoint con DB real (pytest fixtures con rollback): happy path + error paths |
| **Integration — multi-tenant** | Confirmar que queries filtran por `tenant_id`; un tenant no puede leer/escribir datos de otro |
| **Integration — cascade delete** | Verificar que el delete de carpeta llama al storage service para cada archivo antes de eliminar en DB |
| **Contract** | Validar que los response schemas coinciden con el OpenAPI generado por FastAPI |

#### Frontend (Vitest + React Testing Library)

| Componente | Qué testear |
|------------|-------------|
| `DriveFileIcon` | Renderiza el ícono correcto para cada MIME type |
| `DriveBreadcrumb` | Renderiza items, dispara `onNavigate` al click |
| `DriveUploadZone` | Acepta drag & drop, rechaza archivos >50MB, muestra progreso |
| `DriveExplorer` | Integración: navegar carpetas, ver archivos, crear carpeta (mock de hooks Orval) |

---

### Migration Notes

| Aspecto | crmcodexy (origen) | CRM VENTAS (destino) |
|---------|-------------------|----------------------|
| **Storage** | Supabase Storage (`sales_drive` bucket) | MinIO / AWS S3 (configurable via env vars) |
| **Auth en storage** | Supabase RLS + anon key | Presigned URLs generadas desde el backend (sin exposición de credenciales al frontend) |
| **Server actions** | 10 Next.js server actions | 10 endpoints REST FastAPI (misma semántica) |
| **Multi-tenant** | Sin `tenant_id` (single-tenant) | `tenant_id` obligatorio en todas las tablas y queries |
| **Breadcrumb** | Recursión en server action JS | CTE recursiva en PostgreSQL (`WITH RECURSIVE`) o traversal en Python |
| **Signed URL** | `supabase.storage.from().createSignedUrl()` | `boto3.generate_presigned_url()` o cliente MinIO equivalente |
| **Upload progress** | Client-side con fetch + ReadableStream | Presigned PUT URL: el frontend hace PUT directo al bucket con `XMLHttpRequest` para obtener progress events |
| **MIME validation** | Solo en cliente (Next.js) | Validación en backend (FastAPI) + detección real con `python-magic` (no confiar solo en extensión) |
| **Cascade delete** | Supabase maneja storage cascade parcialmente | El backend DEBE iterar y eliminar cada objeto del bucket explícitamente antes de borrar en DB |
| **Nomenclatura** | `cliente_id` (crmcodexy usa `clientes`) | `cliente_id` (compatible — verificar FK hacia tabla `clientes` del CRM VENTAS) |

**Decisión arquitectural clave — Upload flow:**
En crmcodexy el upload es server-side (Next.js server action recibe el file y lo sube a Supabase). En CRM VENTAS se recomienda un flujo de dos pasos para archivos grandes:
1. `POST /files/upload/init` → backend valida, genera presigned PUT URL, registra metadato provisional en DB
2. Frontend hace `PUT` directo al bucket con la URL firmada (progreso nativo con XHR)
3. Frontend confirma con `POST /files/upload/confirm` → backend marca el archivo como activo

Alternativamente, el endpoint `POST /files/upload` puede recibir el archivo en `multipart/form-data` directamente (más simple, sin presigned PUT). Esta decisión se toma en el diseño técnico (DESIGN-01).

---

### Files to Create/Modify

#### Backend (`/backend/app/`)

```
app/
├── api/v1/
│   └── drive/
│       ├── __init__.py
│       ├── router.py           # FastAPI router con todos los endpoints
│       ├── schemas.py          # Pydantic request/response models
│       └── dependencies.py     # Deps: tenant_id, cliente_ownership check
├── services/
│   └── drive/
│       ├── __init__.py
│       ├── folder_service.py   # CRUD carpetas + breadcrumb
│       ├── file_service.py     # CRUD archivos + signed URL
│       └── storage_service.py  # Abstracción sobre S3/MinIO
├── repositories/
│   └── drive/
│       ├── folder_repository.py
│       └── file_repository.py
├── models/
│   └── drive.py                # SQLAlchemy models (DriveFolder, DriveFile)
└── utils/
    └── file_sanitizer.py       # sanitize_filename()
```

#### Migrations

```
alembic/versions/
└── XXXX_create_drive_tables.py
```

#### Frontend (`/frontend/src/`)

```
src/
├── features/
│   └── drive/
│       ├── components/
│       │   ├── DriveExplorer.tsx
│       │   ├── DriveBreadcrumb.tsx
│       │   ├── DriveFolderGrid.tsx
│       │   ├── DriveFolderList.tsx
│       │   ├── DriveFileGrid.tsx
│       │   ├── DriveFileList.tsx
│       │   ├── DriveViewToggle.tsx
│       │   ├── DriveUploadZone.tsx
│       │   ├── DriveCreateFolderModal.tsx
│       │   ├── DriveDeleteConfirmModal.tsx
│       │   └── DriveFileIcon.tsx
│       ├── hooks/              # Auto-generados por Orval desde OpenAPI
│       └── types.ts            # Tipos locales complementarios
└── pages/
    └── clientes/
        └── [clienteId]/
            └── drive/
                └── index.tsx   # Página que monta DriveExplorer
```

#### Tests

```
backend/tests/
└── drive/
    ├── test_folder_service.py
    ├── test_file_service.py
    ├── test_storage_service.py
    ├── test_file_sanitizer.py
    └── test_drive_endpoints.py

frontend/src/features/drive/
└── __tests__/
    ├── DriveFileIcon.test.tsx
    ├── DriveBreadcrumb.test.tsx
    ├── DriveUploadZone.test.tsx
    └── DriveExplorer.test.tsx
```

---

### Dependencies

- **Infra**: Bucket S3-compatible disponible (MinIO en dev, S3 en prod) — configurado via `STORAGE_BUCKET`, `STORAGE_ENDPOINT`, `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY`
- **Backend libs**: `boto3` (o `miniopy-async`), `python-magic` (detección real de MIME), `aiofiles`
- **DB**: Migración de Alembic ejecutada — tablas `drive_folders` y `drive_files` presentes
- **Auth**: Middleware JWT + X-Admin-Token ya implementado (no es parte de esta spec)
- **Clientes**: Tabla `clientes` existente con `id` y `tenant_id` (FK target)
- **Frontend**: Orval configurado y apuntando al OpenAPI de FastAPI para generación de hooks
- **Orval**: Regenerar hooks (`yarn api:gen`) después de que el backend exponga los endpoints en el OpenAPI

---

### Acceptance Criteria

- [ ] Las tablas `drive_folders` y `drive_files` existen en PostgreSQL con todos los campos, índices y constraints definidos en el schema
- [ ] Todos los endpoints REST están documentados en el OpenAPI de FastAPI (`/docs`)
- [ ] Un archivo de 50MB se puede subir exitosamente; un archivo de 50MB + 1 byte es rechazado con 422
- [ ] Los tipos MIME válidos son aceptados; cualquier otro tipo es rechazado con 422
- [ ] El nombre de archivo se sanitiza correctamente antes de construir el `storage_path`
- [ ] El nombre original del archivo se conserva en el campo `nombre` de `drive_files`
- [ ] La signed URL de descarga expira en 60 segundos (verificable inspeccionando los query params de la URL)
- [ ] El breadcrumb retorna los ancestros en orden correcto (raíz primero, carpeta actual al final)
- [ ] Eliminar una carpeta elimina físicamente todos los objetos del bucket (sin huérfanos)
- [ ] Un usuario del tenant A no puede acceder a recursos del tenant B (responde 404)
- [ ] El frontend muestra drag & drop funcional con indicador de progreso
- [ ] El toggle grilla/lista funciona y persiste entre recargas de página
- [ ] Los íconos MIME se muestran correctamente para los 6 tipos: imagen, video, audio, hoja de cálculo, archivo comprimido, documento
- [ ] La cobertura de tests del backend es >= 80% para los módulos `drive/`
- [ ] Todos los tests del frontend para componentes Drive pasan sin errores
- [ ] `yarn api:gen` genera los hooks de Orval sin errores tras exponer los endpoints
