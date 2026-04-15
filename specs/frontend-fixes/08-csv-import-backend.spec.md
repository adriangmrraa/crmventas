# FIX-08: Lead CSV Import Backend Endpoints

## Priority: ALTA
## Complexity: Media

## Current State

El frontend (`LeadImportModal.tsx`) tiene una implementación COMPLETA de CSV import:
- Drag-drop upload
- Preview con column mapping
- Duplicate handling (skip/update)
- Result summary (created/updated/skipped/errors)

Pero los 3 endpoints que necesita NO EXISTEN en el backend:
- `GET /admin/core/crm/leads/csv-template` → 404
- `POST /admin/core/crm/leads/import/preview` → 404
- `POST /admin/core/crm/leads/import/execute` → 404

## Solution

Implementar los 3 endpoints en el backend.

### GET /admin/core/crm/leads/csv-template
- Retorna un archivo CSV con headers y 2 filas de ejemplo
- Columnas: phone_number, first_name, last_name, email, status, source, tags

### POST /admin/core/crm/leads/import/preview
- Recibe: multipart/form-data con archivo CSV
- Parsea CSV (manejar: comillas, encoding UTF-8/latin-1, BOM)
- Valida cada fila (phone requerido, status válido, etc.)
- Retorna: { total_rows, valid_rows, invalid_rows, preview: first 5 rows, column_mapping, errors[] }

### POST /admin/core/crm/leads/import/execute
- Recibe: { file_id o file content, column_mapping, duplicate_strategy: 'skip'|'update' }
- Importa las filas válidas
- Para duplicados (mismo phone+tenant): skip o update según estrategia
- Retorna: { created, updated, skipped, errors[] }

## Files to Create
- `orchestrator_service/routes/lead_import_routes.py` — 3 endpoints
- Registrar en `main.py`

## Files to Modify
- `orchestrator_service/main.py` — include_router

## Acceptance Criteria
- [ ] CSV template se descarga correctamente
- [ ] Preview muestra las primeras 5 filas y errores de validación
- [ ] Import crea leads válidos en la DB con tenant_id correcto
- [ ] Duplicados se manejan según la estrategia elegida
- [ ] El frontend completo funciona end-to-end sin cambios
