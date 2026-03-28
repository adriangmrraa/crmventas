# SPEC: Kanban Pipeline View — CRM VENTAS

**Fecha:** 2026-03-27
**Prioridad:** Alta (Core feature — visual pipeline management)
**Esfuerzo:** Medio (3-5 dias)
**Confidence:** 90%

---

## 1. Contexto

### Por que un Kanban es critico para un CRM de ventas

El CRM VENTAS ya tiene un sistema robusto de leads con estados (`lead_statuses`), transiciones validadas (`lead_status_transitions`), historial auditado (`lead_status_history`) y endpoints para mutar estados individual y masivamente. Sin embargo, **la unica forma de avanzar un lead por el pipeline es editandolo manualmente desde su ficha o la tabla**.

Un tablero Kanban es la representacion visual nativa de un pipeline de ventas:

- **Visibilidad instantanea**: un vendedor ve todos sus leads agrupados por etapa sin abrir filtros ni tablas. Identifica cuellos de botella (columna "Negociacion" con 15 cards vs. "Propuesta Enviada" con 2).
- **Accion rapida**: arrastrar una card de "Contactado" a "Calificado" es un gesto de 300ms vs. abrir ficha, buscar dropdown, seleccionar, guardar (4 clicks, ~5s).
- **Contexto visual**: cada card muestra nombre, empresa, valor, vendedor asignado, dias en etapa y ultima actividad. El vendedor prioriza sin entrar a ningun detalle.
- **Accountability**: el tablero actua como un standup visual permanente. El closer sabe cuantos leads tiene en negociacion, el manager ve la distribucion global.

### Estado actual del proyecto

| Componente | Estado |
|------------|--------|
| Tabla `leads` con campo `status` (FK a `lead_statuses.code`) | Existente |
| Tabla `lead_statuses` (name, code, color, icon, sort_order, is_initial, is_final) | Existente |
| Tabla `lead_status_transitions` (from/to, is_allowed, requires_approval) | Existente |
| Tabla `lead_status_history` (audit trail completo) | Existente |
| `PUT /admin/core/crm/{lead_id}/status` (cambio con historial) | Existente |
| `PUT /admin/crm/leads/{lead_id}/stage` (cambio directo de status) | Existente |
| `GET /admin/core/crm/lead-statuses` (lista de estados del tenant) | Existente |
| `GET /admin/core/crm/leads/{lead_id}/available-transitions` | Existente |
| `POST /admin/core/crm/leads/bulk-status` (cambio masivo) | Existente |
| Tabla `opportunities` | Existente pero huerfana (sin uso activo) |
| Vista Kanban en frontend | **NO existe** |

**Conclusion**: el backend ya soporta toda la logica necesaria. Este spec es 90% frontend.

---

## 2. Requerimientos Tecnicos

### 2.1 Frontend: Vista Kanban

#### Estructura de columnas

Cada columna representa un estado de `lead_statuses` del tenant, ordenadas por `sort_order`. Los estados por defecto son:

| Columna | Codigo | Color | sort_order | Categoria |
|---------|--------|-------|------------|-----------|
| Nuevo | `new` | `#6B7280` | 10 | initial |
| Contactado | `contacted` | `#3B82F6` | 20 | active |
| Calificado | `qualified` | `#10B981` | 30 | active |
| Propuesta Enviada | `proposal_sent` | `#8B5CF6` | 40 | active |
| Negociacion | `negotiation` | `#F59E0B` | 50 | active |
| Ganado | `won` | `#10B981` | 60 | final |
| Perdido | `lost` | `#EF4444` | 70 | final |

> **Nota**: `archived` (sort_order 80) no se muestra como columna Kanban por defecto. Los leads archivados se ocultan. Un toggle "Mostrar archivados" puede aniadirlo como columna colapsada al final.

Los estados son dinamicos por tenant (el tenant puede crear estados custom). El frontend debe renderizar columnas segun lo que devuelva `GET /admin/core/crm/lead-statuses`.

#### Card del lead

Cada card muestra la siguiente informacion:

```
+-----------------------------------------------+
| ● Juan Perez                          $12,000  |
|   Empresa ABC                                  |
|   ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄  |
|   👤 Maria Lopez (setter)     📅 hace 2 dias  |
|   ⏱ 5 dias en esta etapa                      |
+-----------------------------------------------+
```

**Campos**:
- **Nombre completo**: `first_name + last_name` — texto principal, `text-white`, `font-medium`
- **Empresa/Titulo**: `apify_title` si es lead de prospecting, o tag de empresa si existe — `text-white/50`, `text-sm`
- **Valor estimado**: formateado con moneda local (del tenant) — alineado a la derecha, `text-emerald-400` si > 0
- **Vendedor asignado**: nombre del seller via `assigned_seller_id` JOIN a `professionals` — `text-white/40`, `text-xs`
- **Ultima actividad**: timestamp relativo desde `updated_at` — `text-white/40`, `text-xs`
- **Dias en etapa**: calculado desde el ultimo registro en `lead_status_history` con `to_status_code = status_actual`, o desde `created_at` si nunca cambio — `text-white/30`, `text-xs`
- **Tags**: badges compactos si el lead tiene `tags[]` — `bg-{color}-500/10 text-{color}-400`, max 2 visibles + "+N"
- **Fuente**: icono pequenio de source (`meta_ads` → Meta icon, `website` → globe, `referral` → users, `apify` → search)

#### Encabezado de columna

```
+-----------------------------------------------+
|  ● Contactado                        12 leads  |
|  ━━━━━━━━━━━━━━━━━ (barra color status) ━━━━  |
+-----------------------------------------------+
```

- Nombre del estado con icono Lucide (`icon` de `lead_statuses`)
- Color indicator: barra fina `h-0.5` con el `color` del estado
- Contador de leads en esa columna
- Valor total agregado (suma de `estimated_value` o deal value de los leads en esa etapa)

#### Drag and Drop

**Libreria recomendada**: `@dnd-kit/core` + `@dnd-kit/sortable`

Razon: ligera (~13KB gzip), accesible (keyboard DnD built-in), mantenida activamente, soporta scroll containers horizontales y touch nativo. Alternativa aceptable: `react-beautiful-dnd` (mas pesada pero probada).

**Comportamiento**:

1. El usuario agarra una card (mouse down / touch start de 200ms).
2. La card se eleva con `shadow-xl shadow-black/20` y `scale-[1.03]` con `transition: transform 150ms cubic-bezier(0.2, 0, 0, 1)`.
3. En la columna de origen, un placeholder fantasma (`bg-white/[0.02] border-2 border-dashed border-white/[0.08] rounded-lg`) ocupa el espacio.
4. Al pasar sobre otra columna, el header de esa columna brilla: `ring-1 ring-{status_color}/30` con `transition: box-shadow 200ms`.
5. Al soltar:
   - **Animacion pop**: la card hace `scale-[1.05]` → `scale-[1.0]` en 200ms con `cubic-bezier(0.34, 1.56, 0.64, 1)` (overshoot bounce).
   - Se llama a `PUT /admin/core/crm/{lead_id}/status` con el `new_status_id` de la columna destino.
   - **Optimistic update**: la card se mueve visualmente de inmediato. Si la API falla (e.g. transicion no permitida, requires_approval), la card vuelve a su columna original con una animacion de retorno y un toast de error.
6. **Validacion de transiciones**: antes de permitir el drop, consultar las transiciones permitidas. Si `lead_status_transitions` no tiene una fila `(from_status, to_status)` con `is_allowed = true`, el drop se rechaza visualmente (columna se pone `ring-red-500/20` al hover, cursor `not-allowed`).

**Reordenamiento dentro de la misma columna**: no requerido en v1. Los leads dentro de una columna se ordenan por `updated_at DESC` (mas reciente arriba).

#### Filtros y busqueda

Barra superior del Kanban con:

- **Busqueda**: input de texto, filtra cards por nombre, empresa, telefono (`client-side` para rapidez, con debounce 300ms)
- **Filtro por vendedor**: dropdown multi-select con sellers del tenant
- **Filtro por fuente**: dropdown multi-select (meta_ads, website, referral, apify, manual)
- **Filtro por tags**: dropdown multi-select
- **Toggle vista**: icono para alternar entre vista Kanban y vista tabla (LeadsView actual)

#### Cabecera de la vista

```
Pipeline de Ventas                [🔍 Buscar...] [Vendedor ▼] [Fuente ▼] [Tags ▼] [≡ Tabla | ▦ Kanban]
                                                                                    [+ Nuevo Lead]
```

### 2.2 Dark Theme

Siguiendo el design system del CRM VENTAS:

| Elemento | Clases Tailwind |
|----------|----------------|
| Board background | `bg-[#06060e]` |
| Column background | `bg-white/[0.02]` |
| Column header | `bg-white/[0.03] border-b border-white/[0.06]` |
| Card background | `bg-white/[0.03] hover:bg-white/[0.05]` |
| Card border | `border border-white/[0.06]` |
| Card dragging | `bg-white/[0.06] shadow-xl shadow-black/30 ring-1 ring-white/[0.1]` |
| Drop placeholder | `bg-white/[0.02] border-2 border-dashed border-white/[0.08]` |
| Column drag-over highlight | `ring-1 ring-{status_color}/30 bg-{status_color}/[0.02]` |
| Column invalid drop | `ring-1 ring-red-500/20` |
| Text primary | `text-white` |
| Text secondary | `text-white/50` |
| Text muted | `text-white/30` |
| Value badge | `text-emerald-400 font-semibold` |
| Filter bar | `bg-white/[0.03] border-b border-white/[0.06]` |

### 2.3 Animaciones

| Animacion | Trigger | CSS |
|-----------|---------|-----|
| Card lift | Drag start | `transform: scale(1.03); box-shadow: 0 20px 40px rgba(0,0,0,0.3)` transition 150ms |
| Card pop | Drop | `scale(1.05)` → `scale(1.0)` 200ms `cubic-bezier(0.34, 1.56, 0.64, 1)` |
| Card return | Failed drop | `transform: translate(0,0)` 300ms ease-out (animated back to origin) |
| Column glow | Drag over | `box-shadow: 0 0 0 1px {color}30` transition 200ms |
| Column pulse | Card dropped in | `opacity: 0.7` → `1.0` flash 300ms on the status bar |
| Counter update | Count changes | `tabular-nums` + brief `text-white` flash |
| Card enter | New lead created | `opacity: 0` → `1`, `translateY(-8px)` → `0` 300ms ease-out |

### 2.4 Mobile (< 768px)

- **Layout**: columnas en `flex` horizontal con `overflow-x-auto`, `scroll-snap-type: x mandatory`
- Cada columna: `scroll-snap-align: start`, `min-w-[85vw]` para que una columna ocupe casi toda la pantalla
- **Scroll indicator**: puntos (dots) debajo del board indicando columna activa, usando el `color` del estado
- **Touch DnD**: long-press de 300ms para activar el drag. Haptic feedback via `navigator.vibrate(50)` si disponible.
- **Swipe entre columnas**: gesto nativo de scroll con snap, independiente del drag de cards
- **Card compacta**: en mobile se ocultan los tags y la fuente, solo se muestra nombre, valor, vendedor y dias en etapa
- **Header fijo**: el encabezado de la columna actual se mantiene sticky durante el scroll vertical de cards

### 2.5 Accesibilidad

- Cards son `role="listitem"` dentro de columnas `role="list"`
- Keyboard drag: `Space` para pick up, `Arrow Left/Right` para mover entre columnas, `Space` para drop
- `aria-label` en cada card: "Lead {nombre}, {valor}, en etapa {etapa}, {dias} dias"
- `aria-live="polite"` en el contador de cada columna para anunciar cambios
- Focus visible: `ring-2 ring-blue-500/50` en cards cuando reciben foco via teclado

---

## 3. Backend

### Endpoints existentes (no se requieren cambios)

| Endpoint | Metodo | Proposito para Kanban |
|----------|--------|----------------------|
| `GET /admin/crm/leads` | GET | Cargar todos los leads con status, seller, etc. |
| `GET /admin/core/crm/lead-statuses` | GET | Obtener columnas (estados del tenant) |
| `GET /admin/core/crm/leads/{id}/available-transitions` | GET | Validar drops permitidos |
| `PUT /admin/core/crm/{lead_id}/status` | PUT | Mutar status al hacer drop (con historial) |
| `PUT /admin/crm/leads/{lead_id}/stage` | PUT | Alternativa: mutacion directa sin historial |

### Endpoint recomendado para optimizar

Para evitar N+1 en la carga inicial (un request de transiciones por lead), se recomienda un nuevo endpoint opcional:

```
GET /admin/core/crm/lead-status-transitions
```

Devuelve la matriz completa de transiciones del tenant: `{ from_code: string, to_code: string, is_allowed: boolean }[]`. El frontend cachea esta matriz y valida los drops client-side sin requests individuales.

> **Alternativa sin nuevo endpoint**: pre-cargar las transiciones con el endpoint existente una sola vez al montar la vista (ya que las transiciones son por tenant, no por lead). El endpoint `GET /admin/core/crm/leads/{id}/available-transitions` internamente consulta por `from_status_code`, asi que se puede hacer un request por estado unico (6-7 requests vs. N por lead).

### Nota sobre la tabla `opportunities`

La tabla `opportunities` esta huerfana y no se usa en ningun endpoint activo. Para v1 del Kanban, se ignora. En una v2 futura, cada lead podria tener N opportunities (deals), y el Kanban podria mostrar un "deal board" separado. Esto queda fuera de alcance.

---

## 4. Criterios de Aceptacion

```gherkin
Feature: Kanban Pipeline View

  Scenario: Visualizar el pipeline completo
    Given estoy autenticado como vendedor en el CRM
    And existen 15 leads distribuidos en los estados "new", "contacted", "qualified" y "negotiation"
    When navego a la vista de Pipeline (Kanban)
    Then veo una columna por cada estado activo del tenant, ordenadas por sort_order
    And cada columna muestra su nombre, icono, color, contador de leads y valor total
    And cada card muestra nombre, empresa, valor, vendedor asignado, ultima actividad y dias en etapa
    And los leads dentro de cada columna estan ordenados por updated_at descendente

  Scenario: Mover un lead entre etapas via drag and drop
    Given estoy en la vista Kanban
    And existe un lead "Juan Perez" en la columna "Contactado"
    And la transicion de "contacted" a "qualified" esta permitida en lead_status_transitions
    When arrastro la card de "Juan Perez" a la columna "Calificado"
    Then la card se mueve visualmente con animacion pop al soltar
    And se llama a PUT /admin/core/crm/{lead_id}/status con new_status_id="qualified"
    And el contador de "Contactado" disminuye en 1 y el de "Calificado" aumenta en 1
    And se registra la transicion en lead_status_history

  Scenario: Rechazar una transicion no permitida
    Given estoy en la vista Kanban
    And existe un lead "Maria Lopez" en la columna "Nuevo"
    And no existe una transicion directa de "new" a "negotiation" en lead_status_transitions
    When arrastro la card de "Maria Lopez" hacia la columna "Negociacion"
    Then la columna "Negociacion" muestra un borde rojo (ring-red-500/20)
    And el cursor cambia a not-allowed
    When suelto la card sobre "Negociacion"
    Then la card vuelve a la columna "Nuevo" con animacion de retorno
    And se muestra un toast: "Transicion no permitida: Nuevo → Negociacion"

  Scenario: Kanban en dispositivo movil
    Given estoy en un dispositivo con viewport < 768px
    When abro la vista Kanban
    Then las columnas se muestran en scroll horizontal con snap
    And puedo deslizar lateralmente para cambiar de columna
    And veo indicadores (dots) con el color de cada etapa debajo del board
    When hago long-press (300ms) sobre una card
    Then la card se activa para drag and drop con feedback haptico
    And puedo arrastrarla a otra columna visible
```

---

## 5. Archivos a Crear/Modificar

### Nuevos archivos

| Archivo | Proposito |
|---------|-----------|
| `frontend_react/src/modules/crm_sales/views/KanbanPipelineView.tsx` | Vista principal del tablero Kanban |
| `frontend_react/src/modules/crm_sales/components/KanbanColumn.tsx` | Componente de columna (droppable area) |
| `frontend_react/src/modules/crm_sales/components/KanbanCard.tsx` | Componente de card de lead (draggable item) |
| `frontend_react/src/modules/crm_sales/hooks/useLeadTransitions.ts` | Hook para cargar y cachear la matriz de transiciones permitidas |
| `frontend_react/src/modules/crm_sales/hooks/useKanbanDragDrop.ts` | Hook que encapsula la logica de dnd-kit (sensors, handlers, validation) |

### Archivos a modificar

| Archivo | Cambio |
|---------|--------|
| `frontend_react/src/App.tsx` | Agregar ruta `/crm/pipeline` apuntando a `KanbanPipelineView` |
| `frontend_react/src/components/Layout.tsx` (Sidebar) | Agregar item "Pipeline" con icono `Columns3` (Lucide) entre "Leads" y "Clientes" |
| `frontend_react/src/modules/crm_sales/views/LeadsView.tsx` | Agregar boton/toggle para navegar a vista Kanban |
| `frontend_react/src/locales/es.json` | Claves: `pipeline.title`, `pipeline.daysInStage`, `pipeline.totalValue`, `pipeline.dropNotAllowed`, `pipeline.moveSuccess`, `pipeline.showArchived` |
| `frontend_react/src/locales/en.json` | Mismas claves en ingles |
| `frontend_react/src/locales/fr.json` | Mismas claves en frances |
| `package.json` | Agregar dependencia `@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities` |

### Archivos backend (opcionales, solo si se implementa el endpoint de transiciones bulk)

| Archivo | Cambio |
|---------|--------|
| `orchestrator_service/routes/lead_status_routes.py` | Agregar `GET /lead-status-transitions` que devuelve la matriz completa |
| `orchestrator_service/services/lead_status_service.py` | Metodo `get_all_transitions(tenant_id)` |

---

## 6. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigacion |
|--------|-------------|---------|------------|
| **N+1 de transiciones**: sin endpoint bulk, la validacion de drops requiere un request por cada status unico al cargar | Media | Bajo (6-8 requests max, son por status no por lead) | Cachear la matriz de transiciones en un hook con stale-while-revalidate. Los estados de un tenant cambian muy rara vez. |
| **Optimistic update falla**: el API rechaza la transicion despues de que el usuario ya vio el movimiento | Baja | Media (confusion visual) | Animacion de retorno clara + toast con el motivo de error. Siempre validar client-side antes del drop usando la matriz cacheada. |
| **Performance con >200 leads**: renderizar 200+ cards con drag-and-drop puede causar lag en scroll | Baja | Media | Virtualizar las cards dentro de cada columna con `react-window` si hay >50 en una columna. En v1, paginar a 100 leads por columna es suficiente. |
| **Touch conflicts en mobile**: swipe horizontal (cambiar columna) vs. drag horizontal (mover card) | Media | Alta (UX rota en mobile) | Separar gestos: swipe horizontal = scroll entre columnas (gesto nativo). Long-press 300ms = activar drag mode. En drag mode, el scroll de columnas se bloquea (`overflow-x: hidden`). |
| **Estados custom del tenant**: un tenant podria tener 15 estados, haciendo el board ilegible | Baja | Baja | Permitir colapsar columnas (click en header). Columnas finales (`is_final`) se colapsan por defecto mostrando solo contador. |
| **Race conditions**: dos vendedores mueven el mismo lead simultaneamente | Baja | Media | `updated_at` como campo de concurrencia. Si el backend detecta un `updated_at` mas reciente, devolver 409 Conflict. El frontend recarga el lead. |
| **Dependencia de @dnd-kit**: si la libreria se abandona | Baja | Baja | @dnd-kit tiene API estable y es el estandar de facto para React DnD. Alternativa: migrar a `pragmatic-drag-and-drop` (Atlassian) que es mas nueva pero less ergonomica. |

---

## 7. Fuera de Alcance (v2+)

- **Deal board**: Kanban de `opportunities` separado del pipeline de leads.
- **Swimlanes por vendedor**: filas horizontales que agrupan cards por seller.
- **Automations**: mover un lead automaticamente cuando se completa una reunion de agenda.
- **WIP limits**: limitar la cantidad de leads por columna (e.g., max 10 en "Negociacion").
- **Pipeline analytics overlay**: conversion funnel superpuesto sobre las columnas.
- **Bulk drag**: seleccionar multiples cards y moverlas juntas.
- **Custom card fields**: permitir al tenant elegir que campos se muestran en cada card.
