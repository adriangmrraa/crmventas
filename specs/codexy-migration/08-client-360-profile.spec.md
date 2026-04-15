# SPEC-08: Client 360° Profile

**Priority:** Media
**Complexity:** Media
**Source:** crmcodexy — `/clientes/[id]` con Promise.allSettled y 4 tabs unificadas
**Target:** CRM VENTAS — extender `LeadDetailView` con tabs unificadas (WhatsApp + Files + Calls + Notes)
**Estado:** Draft
**Fecha:** 2026-04-14

---

## Contexto y Motivación

CRM VENTAS tiene `LeadDetailView` con historial, notas y tareas, pero NO tiene una vista unificada que combine llamadas, WhatsApp, archivos y notas en pestañas independientes y fault-tolerant. crmcodexy resuelve esto con `Promise.allSettled` (cada tab carga independientemente — un fallo no afecta a las otras) y tabs especializadas con funcionalidad rica. Esta migración trae el patrón a CRM VENTAS.

---

## Alcance

### Incluido

- `ClienteDetailView` con `ClienteHeader` (modo edición inline)
- 4 tabs cargadas de forma independiente y fault-tolerant:
  1. **Notas** — timeline cronológico con author badges
  2. **Llamadas** — CRUD inline + sincronización con agenda
  3. **WhatsApp** — polling cada 10s, mensajes agrupados por fecha, iconos de estado
  4. **Archivos** — drag&drop upload, vista en grid
- `EstadoBadge` con 5 estados color-coded
- Cada tab tiene su propio estado de loading/error — no comparten estado
- Navegación a la vista desde el pipeline (click en tarjeta de lead/cliente)

### Excluido

- Chat en tiempo real con WebSocket (polling es suficiente para v1)
- Preview de archivos inline (PDF/imagen) — solo descarga en v1
- Historial de ediciones del header (audit trail)
- Merge de contactos duplicados

---

## Modelo de Datos — Extensiones Requeridas

### Tab Notas

```python
class Nota(BaseModel):
    id: UUID
    cliente_id: UUID
    contenido: str
    autor_id: UUID
    autor_nombre: str
    autor_avatar_url: str | None
    created_at: datetime
    updated_at: datetime
```

### Tab Llamadas (extiende modelo existente si aplica)

```python
class Llamada(BaseModel):
    id: UUID
    cliente_id: UUID
    vendedor_id: UUID
    fecha_hora: datetime
    duracion_seg: int | None
    resultado: Literal["completada", "no_contesto", "reagendada"] | None
    nota_auto: str | None          # prefijo automático según resultado
    agenda_event_id: str | None    # ID externo del evento de agenda
    created_at: datetime
```

### Tab WhatsApp

```python
class WhatsAppMensaje(BaseModel):
    id: str                        # ID de Whapi/360dialog/etc.
    cliente_id: UUID
    from_number: str
    to_number: str
    body: str
    tipo: Literal["text", "image", "document", "audio"]
    estado: Literal["sent", "delivered", "read", "failed"]
    timestamp: datetime
    es_entrante: bool
```

### Tab Archivos

```python
class Archivo(BaseModel):
    id: UUID
    cliente_id: UUID
    nombre_original: str
    url: str
    mime_type: str
    tamaño_bytes: int
    subido_por_id: UUID
    created_at: datetime
```

### ClienteHeader — estados

```python
EstadoCliente = Literal[
    "prospecto",    # Gris
    "activo",       # Verde
    "negociacion",  # Amarillo/Naranja
    "cerrado",      # Azul
    "perdido",      # Rojo
]
```

---

## Endpoints de Backend Requeridos

### Notas

```
GET    /api/clientes/{id}/notas              → list[Nota]
POST   /api/clientes/{id}/notas              → Nota
DELETE /api/clientes/{id}/notas/{nota_id}    → 204
```

### Llamadas

```
GET    /api/clientes/{id}/llamadas           → list[Llamada]
POST   /api/clientes/{id}/llamadas           → Llamada
PUT    /api/clientes/{id}/llamadas/{lid}     → Llamada
DELETE /api/clientes/{id}/llamadas/{lid}     → 204
```

### WhatsApp

```
GET    /api/clientes/{id}/whatsapp/mensajes  → list[WhatsAppMensaje]
  Query params: since={ISO8601}              # polling incremental
```

### Archivos

```
GET    /api/clientes/{id}/archivos           → list[Archivo]
POST   /api/clientes/{id}/archivos           → Archivo  (multipart/form-data)
DELETE /api/clientes/{id}/archivos/{aid}     → 204
```

### Cliente (header inline edit)

```
GET    /api/clientes/{id}                    → ClienteDetail
PUT    /api/clientes/{id}                    → ClienteDetail
```

---

## Interfaz de Componentes (Frontend)

```
ClienteDetailPage
├── ClienteHeader
│   ├── EstadoBadge (5 estados color-coded)
│   ├── InlineEditForm (toggle con botón editar/guardar/cancelar)
│   └── ContactInfo (teléfono, email, empresa)
└── TabContainer (fault-tolerant)
    ├── TabNotas
    │   ├── NotaTimeline (lista cronológica)
    │   ├── AutorBadge (avatar + nombre)
    │   └── NotaForm (crear nueva nota)
    ├── TabLlamadas
    │   ├── LlamadaList (con inline edit/delete)
    │   ├── LlamadaForm (crear nueva)
    │   ├── ResolverDialog (completada/no_contesto/reagendada)
    │   └── AgendaSyncIndicator
    ├── TabWhatsApp
    │   ├── MensajeGroupedList (agrupado por fecha)
    │   ├── MensajeStatusIcon (sent/delivered/read/failed)
    │   └── PollingIndicator (10s interval)
    └── TabArchivos
        ├── DropZone (drag&drop)
        ├── ArchivoGrid (vista en cuadrícula)
        └── ArchivoCard (nombre, tamaño, descarga, eliminar)
```

---

## Escenarios (BDD)

### SC-08-01: Carga fault-tolerant — un tab falla, los demás cargan

```
DADO que el endpoint /whatsapp/mensajes devuelve 503
  Y los endpoints de notas, llamadas y archivos responden 200
CUANDO se carga ClienteDetailPage
ENTONCES el tab WhatsApp muestra un estado de error con mensaje descriptivo
  Y los tabs Notas, Llamadas y Archivos muestran su contenido correctamente
  Y NO hay crash de la página completa
```

### SC-08-02: Edición inline del header

```
DADO que estoy en ClienteDetailPage
CUANDO hago click en "Editar"
ENTONCES los campos del header se convierten en inputs editables
CUANDO modifico el nombre y hago click en "Guardar"
ENTONCES se llama PUT /api/clientes/{id} con los nuevos datos
  Y el header muestra los datos actualizados sin recargar la página
CUANDO hago click en "Cancelar"
ENTONCES los campos vuelven al valor original sin llamada a la API
```

### SC-08-03: EstadoBadge — 5 estados con colores

```
DADO un cliente con estado "negociacion"
CUANDO se renderiza EstadoBadge
ENTONCES el badge muestra color naranja/amarillo y texto "En negociación"

Estados y colores:
  prospecto   → Gris    (#6B7280)
  activo      → Verde   (#10B981)
  negociacion → Naranja (#F59E0B)
  cerrado     → Azul    (#3B82F6)
  perdido     → Rojo    (#EF4444)
```

### SC-08-04: Tab Notas — crear nota con autor badge

```
DADO que estoy en el tab Notas
CUANDO escribo una nota y hago click en "Agregar"
ENTONCES se llama POST /api/clientes/{id}/notas
  Y la nota aparece al tope del timeline con avatar y nombre del autor actual
  Y el form queda vacío listo para otra nota
```

### SC-08-05: Tab Llamadas — resolver con dialog y auto-nota

```
DADO una llamada programada en el tab Llamadas
CUANDO hago click en "Resolver"
ENTONCES aparece ResolverDialog con 3 opciones: Completada / No contestó / Reagendada
CUANDO elijo "No contestó"
ENTONCES se llama PUT /api/clientes/{id}/llamadas/{lid} con resultado="no_contesto"
  Y se crea automáticamente una nota con prefijo "[Llamada - No contestó]"
  Y si había agenda_event_id, se actualiza el evento de agenda como completado
```

### SC-08-06: Tab Llamadas — reagendar con sincronización de agenda

```
DADO que elegí "Reagendada" en el ResolverDialog
CUANDO selecciono nueva fecha/hora
ENTONCES se crea una nueva Llamada con la nueva fecha
  Y se crea un nuevo evento en la agenda con la nueva fecha
  Y la llamada original queda marcada como reagendada
```

### SC-08-07: Tab WhatsApp — polling cada 10 segundos

```
DADO que estoy en el tab WhatsApp
CUANDO han pasado 10 segundos desde la última carga
ENTONCES se llama GET /api/clientes/{id}/whatsapp/mensajes?since={last_timestamp}
  Y los nuevos mensajes aparecen al final de la lista
  Y los mensajes están agrupados por fecha (hoy, ayer, DD/MM/YYYY)
```

### SC-08-08: Tab WhatsApp — iconos de estado

```
DADO mensajes con distintos estados
ENTONCES:
  "sent"      → un check gris
  "delivered" → dos checks grises
  "read"      → dos checks azules
  "failed"    → ícono de error rojo con tooltip
```

### SC-08-09: Tab Archivos — drag & drop upload

```
DADO que arrastro un archivo PDF al DropZone
CUANDO lo suelto
ENTONCES aparece una barra de progreso
  Y se llama POST /api/clientes/{id}/archivos con multipart/form-data
  Y al completarse, el archivo aparece en el grid sin recargar el tab
```

### SC-08-10: Tab Archivos — eliminar archivo

```
DADO un archivo en el grid
CUANDO hago click en "Eliminar" y confirmo
ENTONCES se llama DELETE /api/clientes/{id}/archivos/{aid}
  Y el archivo desaparece del grid
  Y si falla la eliminación, se muestra toast de error
```

---

## Implementación — Estructura de Archivos

```
# Backend
app/
  routers/
    clientes/
      notas.py
      llamadas.py
      whatsapp.py
      archivos.py
  services/
    clientes/
      notas_service.py
      llamadas_service.py
      whatsapp_service.py
      archivos_service.py
      agenda_sync_service.py    # sincronización bidireccional con agenda
  schemas/
    clientes/
      nota.py
      llamada.py
      whatsapp.py
      archivo.py

# Frontend (estructura sugerida)
src/
  features/
    clientes/
      pages/
        ClienteDetailPage.tsx
      components/
        ClienteHeader/
          ClienteHeader.tsx
          InlineEditForm.tsx
          EstadoBadge.tsx
        tabs/
          TabNotas/
            TabNotas.tsx
            NotaTimeline.tsx
            AutorBadge.tsx
          TabLlamadas/
            TabLlamadas.tsx
            LlamadaList.tsx
            ResolverDialog.tsx
            AgendaSyncIndicator.tsx
          TabWhatsApp/
            TabWhatsApp.tsx
            MensajeGroupedList.tsx
            MensajeStatusIcon.tsx
          TabArchivos/
            TabArchivos.tsx
            DropZone.tsx
            ArchivoGrid.tsx
      hooks/
        useClienteDetail.ts
        useNotasTab.ts
        useLlamadasTab.ts
        useWhatsAppPolling.ts
        useArchivosTab.ts
      api/
        clientes.api.ts        # generado por Orval
```

---

## Patrón de Carga Fault-Tolerant

Equivalente Python/React de `Promise.allSettled`:

```typescript
// hooks/useClienteDetail.ts
const [notasResult, llamadasResult, whatsappResult, archivosResult] =
  await Promise.allSettled([
    fetchNotas(clienteId),
    fetchLlamadas(clienteId),
    fetchWhatsApp(clienteId),
    fetchArchivos(clienteId),
  ]);

// Cada tab recibe { data, error } independiente
// Un error en uno NO afecta a los otros
```

---

## Tests Requeridos (TDD)

### Backend

- `test_notas_router.py`: CRUD completo, autorización
- `test_llamadas_router.py`: CRUD, resultado enum, auto-nota, agenda sync
- `test_whatsapp_router.py`: GET con filtro `since`, polling semántico
- `test_archivos_router.py`: upload multipart, eliminación, max file size

### Frontend

- `ClienteDetailPage.test.tsx`: fault-tolerant loading (SC-08-01)
- `ClienteHeader.test.tsx`: inline edit toggle, guardar, cancelar (SC-08-02)
- `EstadoBadge.test.tsx`: 5 estados y colores (SC-08-03)
- `TabLlamadas.test.tsx`: ResolverDialog, auto-nota, agenda sync (SC-08-05, SC-08-06)
- `TabWhatsApp.test.tsx`: polling interval, agrupado por fecha, iconos (SC-08-07, SC-08-08)
- `TabArchivos.test.tsx`: drag&drop, upload progress, eliminar (SC-08-09, SC-08-10)

---

## Criterios de Aceptación

- [ ] Si cualquier endpoint de tab retorna error, los otros tabs funcionan normalmente
- [ ] InlineEdit del header no llama a la API hasta hacer click en "Guardar"
- [ ] EstadoBadge renderiza el color correcto para cada uno de los 5 estados
- [ ] ResolverDialog crea auto-nota con prefijo correcto según resultado elegido
- [ ] WhatsApp polling se detiene cuando el tab no está visible (visibility API)
- [ ] Upload de archivos muestra progreso real (no fake loader)
- [ ] Cobertura de tests backend >= 85% en rutas nuevas
- [ ] Cobertura de tests frontend >= 80% en componentes nuevos

---

## Notas de Migración desde crmcodexy

| crmcodexy | CRM VENTAS |
|---|---|
| Next.js App Router con `Promise.allSettled` en Server Component | React con `Promise.allSettled` en hook client-side |
| `/clientes/[id]` page | `ClienteDetailPage` en `features/clientes/pages/` |
| 4 tabs con estado independiente | Mismo patrón, cada tab tiene su propio hook |
| Polling con `setInterval` + cleanup en `useEffect` | Mismo patrón, detener con `document.visibilityState` |
| Drag&drop con `react-dropzone` | Evaluar `react-dropzone` (ya en deps) o HTML5 nativo |
| Agenda sync bidireccional | Adaptar al proveedor de agenda configurado en CRM VENTAS |
