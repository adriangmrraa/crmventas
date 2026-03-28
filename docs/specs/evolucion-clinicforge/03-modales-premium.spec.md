# 03 — Modales Premium (ClinicForge Pattern Library)

**Fecha**: 2026-03-27
**Estado**: Draft
**Origen**: Portado desde ClinicForge (`frontend_react/src/components/`)
**Impacto**: Todos los modales, formularios y wizards del CRM VENTAS

---

## 1. Contexto

### ClinicForge (estado actual)

ClinicForge implementa 3 patrones de modal premium con dark mode nativo, animaciones CSS de alto nivel y responsive-first:

| Patron | Componente referencia | Uso |
|--------|----------------------|-----|
| **A. Slide-over panel** | `AppointmentForm.tsx` | Formularios densos (citas, facturacion, historial clinico) |
| **B. 3D tilt card** | `OnboardingGuide.tsx` | Guias informativas, onboarding, tutoriales |
| **C. Generic modal** | `UserApprovalView.tsx`, `SellersView.tsx` | Confirmaciones, formularios cortos, seleccion |

Los tres comparten: `bg-[#0d1117]`, backdrop-blur, `border-white/[0.08]`, animaciones con cubic-bezier, y consistencia total con el design system oscuro.

### CRM VENTAS (estado actual - problemas)

El CRM tiene ~20 instancias de modal repartidas en 15+ archivos con inconsistencias graves:

| Problema | Archivos afectados |
|----------|--------------------|
| `Modal.tsx` usa CSS classes legacy (`modal-overlay`, `modal-${size}`) con inline styles | Toda view que importa `<Modal>` |
| Z-index inconsistente: 40, 50, 60, 70, 100, 200 sin jerarquia definida | Todos |
| Overlay: mezcla de `bg-black/50`, `bg-black/60`, `bg-slate-900/50`, `bg-black bg-opacity-50` | Todos |
| Sin animacion de entrada/salida en la mayoria de modales | `PatientsView`, `ClientsView`, `PatientDetail`, `AgendaEventForm` |
| Sin soporte mobile (bottom sheet) en ninguno excepto `UserApprovalView` y `SellersView` | La mayoria |
| Inputs sin estilo unificado: algunos usan `bg-white/[0.03]`, otros no tienen background | `AgendaEventForm`, `BulkStatusUpdate`, `LeadsView` |
| `AppointmentForm.tsx` ya implementa slide-over parcialmente pero con `border-white/[0.06]` en vez de `/[0.08]` | `AppointmentForm` |

---

## 2. Patrones de Modal

### A. SLIDE-OVER PANEL (formularios densos)

Panel que se desliza desde el borde derecho. Ideal para formularios con multiples campos, tabs, o contenido scrollable.

#### Estructura

```
[Backdrop overlay]
  [Panel fixed right]
    [Header: titulo + subtitulo + close]
    [Tabs bar (opcional)]
    [Content area: flex-1 overflow-y-auto]
    [Footer: sticky actions]
```

#### Especificacion de estilos

**Contenedor backdrop:**
```
fixed inset-0 z-[60]
bg-black/20 backdrop-blur-sm
transition-opacity duration-300
onClick={onClose}
```

**Panel:**
```
fixed inset-y-0 right-0 z-[70]
w-full md:w-[450px]
bg-[#0d1117] backdrop-blur-xl
shadow-2xl shadow-black/20
border-l border-white/[0.08]
flex flex-col
transform transition-transform duration-300 ease-out
```
- Estado cerrado: `translate-x-full`
- Estado abierto: `translate-x-0`

**Header:**
```
px-6 py-4
border-b border-white/[0.06]
bg-white/[0.02]
flex items-center justify-between
```
- Titulo: `text-xl font-bold text-white`
- Subtitulo: `text-xs text-white/40`
- Close button: `p-2 hover:bg-white/[0.06] rounded-full text-white/30 hover:text-white/60 transition-colors`
- Source badge (opcional): `text-[10px] px-2 py-0.5 rounded-full bg-{color}-500/10 text-{color}-400`

**Tabs bar (opcional):**
```
flex border-b border-white/[0.04] bg-white/[0.02]
```
- Tab activa: `border-b-2 border-blue-500 text-blue-400 bg-blue-500/[0.06]`
- Tab inactiva: `text-white/40 hover:text-white/60 hover:bg-white/[0.04]`
- Cada tab: `flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium transition-all`

**Content area:**
```
flex-1 min-h-0 overflow-y-auto p-6 space-y-6
```

**Inputs (todos los campos del formulario):**
```
w-full px-3 py-2.5
bg-white/[0.04] border border-white/[0.08]
rounded-xl text-white placeholder-white/30
focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500/50
transition-colors
```
- Labels: `text-xs font-semibold text-white/40 uppercase tracking-wider`
- Select: mismos estilos + `cursor-pointer`
- Textarea: mismos estilos + `resize-none`

**Alert boxes:**
```
p-3 rounded-xl flex items-center gap-2 text-sm
```
- Error: `bg-red-500/10 text-red-400 border border-red-500/20`
- Warning: `bg-amber-500/10 text-amber-400 border border-amber-500/20`
- Info: `bg-blue-500/10 text-blue-400 border border-blue-500/20`
- Success: `bg-emerald-500/10 text-emerald-400 border border-emerald-500/20`

**Footer (sticky):**
```
sticky bottom-0
px-6 py-4
bg-[#0d1117]/90 backdrop-blur-md
border-t border-white/[0.06]
flex items-center justify-between gap-3
```
- Cancel button: `px-4 py-2 rounded-xl border border-white/[0.06] text-white/50 hover:bg-white/[0.04] transition-colors`
- Primary button: `px-5 py-2.5 rounded-xl bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-50 transition-all`
- Danger button: `px-4 py-2 rounded-xl border border-red-500/20 text-red-400 hover:bg-red-500/10 transition-colors`

---

### B. 3D TILT CARD (guias / informacion)

Card flotante centrada con efecto de perspectiva 3D que reacciona al movimiento del puntero. Incluye swipe gestures para navegacion entre pasos.

#### Estructura

```
[Backdrop overlay]
  [Card container: perspective + tilt]
    [Header: icono + titulo + progress bar]
    [Content area: step content + swipe zone]
    [Footer: dots + nav buttons]
```

#### Especificacion de estilos

**Backdrop:**
```
fixed inset-0 z-[200]
bg-black/50 backdrop-blur-sm
onClick={onClose}
```

**Container (para centrar sin capturar clicks):**
```
fixed inset-0 z-[201]
flex items-center justify-center p-4
pointer-events-none
```

**Card:**
```
pointer-events-auto
w-full max-w-md
bg-[#0c1018]/95 backdrop-blur-2xl
border border-white/[0.08]
rounded-3xl
shadow-2xl shadow-black/40
overflow-hidden
```
- Animacion de entrada: `from { opacity:0; transform: scale(0.92) translateY(20px); } to { opacity:1; transform: scale(1) translateY(0); }` — `0.35s cubic-bezier(0.16,1,0.3,1)`
- Transform dinamico: `perspective(800px) rotateY(${tiltX}deg) rotateX(${tiltY}deg)` — rango +-4deg
- Transition on transform: `0.15s ease-out`

**Logica de tilt (onPointerMove):**
```typescript
const rect = cardRef.current.getBoundingClientRect();
const x = ((e.clientX - rect.left) / rect.width - 0.5) * 8;   // rotateY
const y = ((e.clientY - rect.top) / rect.height - 0.5) * -8;  // rotateX
```
- onPointerLeave: reset a `{ x: 0, y: 0 }`

**Swipe gestures (touch):**
- Threshold: 50px horizontal
- Swipe izquierda (< -50px): siguiente paso o completar
- Swipe derecha (> 50px): paso anterior (si no es el primero)
- During swipe: `translateX(${dx * 0.4}px)`, opacity decay `max(0.3, 1 - abs(dx) / 200)`
- Contenedor swipeable: `touch-pan-y select-none`

**Progress bar:**
```
flex-1 h-1 bg-white/[0.06] rounded-full overflow-hidden
```
- Fill: `bg-gradient-to-r from-blue-500 to-cyan-400 rounded-full transition-all duration-500 ease-out`
- Counter: `text-[10px] font-bold text-white/25 tabular-nums`

**Step dots:**
```
h-1 rounded-full transition-all duration-300
```
- Activo: `w-5 bg-blue-500`
- Completado: `w-1.5 bg-blue-500/30`
- Pendiente: `w-1.5 bg-white/[0.08]`

**Step transition animations:**
```css
@keyframes cardSlideLeft  { from { opacity:0; transform: translateX(40px); }  to { opacity:1; transform: translateX(0); } }
@keyframes cardSlideRight { from { opacity:0; transform: translateX(-40px); } to { opacity:1; transform: translateX(0); } }
```

**Complete button (ultimo paso):**
```
bg-gradient-to-r from-blue-500 to-cyan-400
text-white font-bold
shadow-md shadow-blue-500/20
hover:shadow-lg hover:shadow-blue-500/30
```

---

### C. GENERIC MODAL (confirmaciones / formularios cortos)

Modal responsivo: bottom sheet en mobile, centrado en desktop. Para confirmaciones, formularios breves, selecciones, y wizards con pasos.

#### Estructura

```
[Overlay]
  [Card: bottom-sheet (mobile) / centered (desktop)]
    [Header: titulo + close]
    [Body: contenido]
    [Footer: acciones]
```

#### Especificacion de estilos

**Overlay:**
```
fixed inset-0 z-50
bg-black/60 backdrop-blur-sm
animate-in fade-in duration-200
```

**Card container (responsivo):**
```
fixed inset-0 z-50
flex items-end sm:items-center justify-center
p-0 sm:p-4
```

**Card:**
```
bg-[#0d1117]
border border-white/[0.08]
rounded-t-2xl sm:rounded-2xl
shadow-xl shadow-black/20
w-full sm:max-w-md
max-h-[90vh] sm:max-h-[85vh]
overflow-hidden
flex flex-col
animate-in slide-in-from-bottom-4 sm:zoom-in-95 fade-in duration-200
```

**Header:**
```
px-6 py-4
border-b border-white/[0.06]
bg-white/[0.02]
flex items-center justify-between
```
- Titulo: `text-lg font-semibold text-white`
- Close button: `w-8 h-8 rounded-full bg-white/[0.04] hover:bg-white/[0.08] flex items-center justify-center text-white/30 hover:text-white/60 transition-all`

**Body:**
```
flex-1 min-h-0 overflow-y-auto p-6
```

**Footer:**
```
px-6 py-4
bg-white/[0.02]
border-t border-white/[0.06]
flex items-center justify-end gap-3
```
- Cancel: `px-4 py-2 text-sm font-semibold text-white/50 hover:text-white hover:bg-white/[0.04] rounded-xl transition-colors`
- Primary: `px-5 py-2.5 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition-all disabled:opacity-50`
- Danger: `px-4 py-2 text-sm font-semibold text-red-400 border border-red-500/20 hover:bg-red-500/10 rounded-xl transition-colors`

#### Variante: Wizard con pasos

Para `GoogleConnectionWizard` y `MetaConnectionWizard`, el body incluye un step indicator:

**Step indicator:**
```
flex items-center justify-center gap-2 mb-6
```
- Cada step: `w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-all`
- Completado: `bg-blue-500 text-white`
- Activo: `bg-blue-500/20 text-blue-400 ring-2 ring-blue-500/40`
- Pendiente: `bg-white/[0.04] text-white/30`
- Conector entre steps: `w-8 h-px bg-white/[0.08]` (completado: `bg-blue-500/40`)

---

## 3. Mapping: Componentes CRM VENTAS a migrar

### Patron A (Slide-over panel)

| Archivo | Estado actual | Cambios necesarios |
|---------|--------------|-------------------|
| `src/components/AppointmentForm.tsx` | Ya implementa slide-over parcialmente | Cambiar `border-white/[0.06]` a `/[0.08]` en border-l. Agregar footer sticky con `bg-[#0d1117]/90 backdrop-blur-md`. Estandarizar inputs a `bg-white/[0.04] border-white/[0.08]`. |

### Patron B (3D tilt card)

| Archivo | Estado actual | Cambios necesarios |
|---------|--------------|-------------------|
| `src/components/OnboardingGuide.tsx` | Ya implementado correctamente | Sin cambios. Este es el componente de referencia. |

### Patron C (Generic modal)

| Archivo | Estado actual | Cambios necesarios |
|---------|--------------|-------------------|
| `src/components/Modal.tsx` | CSS classes legacy, inline styles, sin responsive, sin animaciones | **Reescritura completa** segun patron C. Agregar bottom-sheet mobile. |
| `src/components/leads/BulkStatusUpdate.tsx` | `bg-slate-900/50` overlay, sin bottom-sheet, classes dobles (`bg-white/[0.03]/[0.04]`) | Migrar overlay a `bg-black/60`. Corregir classes invalidas. Agregar bottom-sheet mobile. |
| `src/modules/crm_sales/components/AgendaEventForm.tsx` | `bg-black/50` overlay, `bg-white/[0.03]` card, sin animacion, sin bottom-sheet | Migrar a patron C completo. Card `bg-[#0d1117]`. Footer con `bg-white/[0.02]`. |
| `src/components/marketing/GoogleConnectionWizard.tsx` | `bg-black/60 backdrop-blur-sm`, centrado, sin bottom-sheet | Migrar a patron C variante wizard. Agregar step indicator. Agregar bottom-sheet mobile. |
| `src/components/marketing/MetaConnectionWizard.tsx` | Igual que GoogleConnectionWizard | Idem. |
| `src/components/leads/LeadHistoryTimeline.tsx` | `bg-slate-900/50` overlay | Migrar overlay a `bg-black/60 backdrop-blur-sm`. Estandarizar card. |
| `src/views/CompaniesView.tsx` (modal inline) | `bg-black/50`, centrado basico | Extraer a patron C o usar `<Modal>` refactorizado. |
| `src/views/ChatsView.tsx` (modal imagen) | `bg-black bg-opacity-50` | Migrar a `bg-black/60 backdrop-blur-sm`. |
| `src/views/MetaLeadsView.tsx` (detail modal) | z-[100], `bg-black/60 backdrop-blur-sm` | Bajar z-index a 50. Estandarizar card. |
| `src/modules/dental/views/TreatmentsView.tsx` (modal inline) | `bg-black/50 backdrop-blur-sm` | Migrar a patron C. |
| `src/modules/dental/views/ProfessionalsView.tsx` (modal inline) | `bg-black/60 backdrop-blur-md` | Migrar a patron C. `backdrop-blur-sm` (no md). |
| `src/modules/dental/views/PatientsView.tsx` (modal inline) | `bg-black bg-opacity-50`, sin blur | Migrar a patron C. Agregar backdrop-blur-sm. |
| `src/modules/dental/views/PatientDetail.tsx` (modal inline) | `bg-black bg-opacity-50`, sin blur | Migrar a patron C. |
| `src/modules/crm_sales/views/ClientsView.tsx` (modal inline) | `bg-black bg-opacity-50`, sin blur | Migrar a patron C. |
| `src/modules/crm_sales/views/LeadsView.tsx` (modal inline) | `bg-black/60 backdrop-blur-sm` | Estandarizar a patron C. |
| `src/modules/crm_sales/views/SellersView.tsx` (2 modales) | Ya usa `items-end sm:items-center` (bottom-sheet) | Ajustar close button y card bg a patron C. Mas cercano al target. |
| `src/views/UserApprovalView.tsx` (2 modales) | Ya usa `items-end sm:items-center` (bottom-sheet) | Ajustar close button y card bg a patron C. Mas cercano al target. |

---

## 4. Jerarquia de Z-index

Todos los modales del CRM VENTAS deben seguir esta jerarquia estricta:

| Z-index | Uso | Ejemplo |
|---------|-----|---------|
| `z-30` | Sidebar (desktop) | `Layout.tsx` sidebar |
| `z-40` | Sidebar overlay (mobile), popovers | `Layout.tsx` mobile overlay, `FilterPopover`, `NotificationBell` |
| `z-50` | Generic modals (patron C) overlay + card | `Modal.tsx`, `BulkStatusUpdate`, `AgendaEventForm`, wizards |
| `z-[60]` | Slide-over backdrop (patron A) | `AppointmentForm` backdrop |
| `z-[70]` | Slide-over panel (patron A) | `AppointmentForm` panel |
| `z-[200]` | Onboarding overlay (patron B) | `OnboardingGuide` backdrop |
| `z-[201]` | Onboarding card (patron B) | `OnboardingGuide` card container |

**Regla**: Un modal nunca debe usar un z-index que no este en esta tabla. Si se necesita un nuevo nivel, se documenta aqui primero.

---

## 5. Archivos a modificar

### Reescritura completa (1 archivo)

```
src/components/Modal.tsx
```

### Ajustes menores (2 archivos)

```
src/components/AppointmentForm.tsx
src/components/OnboardingGuide.tsx  (sin cambios, referencia)
```

### Migracion a patron C (15 archivos)

```
src/components/leads/BulkStatusUpdate.tsx
src/components/leads/LeadHistoryTimeline.tsx
src/components/marketing/GoogleConnectionWizard.tsx
src/components/marketing/MetaConnectionWizard.tsx
src/modules/crm_sales/components/AgendaEventForm.tsx
src/modules/crm_sales/views/ClientsView.tsx
src/modules/crm_sales/views/LeadsView.tsx
src/modules/crm_sales/views/SellersView.tsx
src/modules/dental/views/PatientsView.tsx
src/modules/dental/views/PatientDetail.tsx
src/modules/dental/views/ProfessionalsView.tsx
src/modules/dental/views/TreatmentsView.tsx
src/views/ChatsView.tsx
src/views/CompaniesView.tsx
src/views/MetaLeadsView.tsx
src/views/UserApprovalView.tsx
```

### Total: 18 archivos

---

## 6. Acceptance Criteria

### Scenario 1: Slide-over panel abre y cierra con animacion

```gherkin
Feature: Slide-over panel (patron A)

  Scenario: Usuario abre el formulario de cita desde la agenda
    Given el usuario esta en la vista de Agenda
    When hace click en un slot de horario vacio
    Then el backdrop aparece con bg-black/20 y backdrop-blur-sm
    And el panel se desliza desde la derecha con translate-x-full a translate-x-0 en 300ms
    And el panel tiene ancho completo en mobile y 450px en desktop
    And el header muestra el titulo, subtitulo y boton de cerrar
    And los inputs tienen bg-white/[0.04] con border-white/[0.08]
    And el footer queda sticky en la parte inferior con bg-[#0d1117]/90

  Scenario: Usuario cierra el slide-over clickeando el backdrop
    Given el formulario slide-over esta abierto
    When el usuario hace click en el area oscura fuera del panel
    Then el panel se desliza hacia la derecha (translate-x-0 a translate-x-full) en 300ms
    And el backdrop se desvanece
    And el foco vuelve al contenido de la pagina
```

### Scenario 2: Generic modal se adapta a mobile como bottom sheet

```gherkin
Feature: Generic modal responsive (patron C)

  Scenario: Modal de confirmacion en mobile se muestra como bottom sheet
    Given el usuario esta en un dispositivo con viewport < 640px
    When se dispara un modal de confirmacion (ej: bulk status update)
    Then el modal aparece anclado al fondo de la pantalla (items-end)
    And tiene bordes redondeados solo arriba (rounded-t-2xl)
    And el overlay es bg-black/60 con backdrop-blur-sm
    And el card tiene bg-[#0d1117] con border-white/[0.08]

  Scenario: Mismo modal en desktop se muestra centrado
    Given el usuario esta en un dispositivo con viewport >= 640px
    When se dispara el mismo modal de confirmacion
    Then el modal aparece centrado vertical y horizontalmente (sm:items-center)
    And tiene bordes redondeados completos (sm:rounded-2xl)
    And tiene ancho maximo de max-w-md
```

### Scenario 3: Z-index no genera conflictos entre capas

```gherkin
Feature: Jerarquia de z-index

  Scenario: Slide-over coexiste con sidebar sin solaparse
    Given la sidebar esta visible en desktop (z-30)
    When el usuario abre un formulario slide-over (panel z-[70], backdrop z-[60])
    Then el backdrop cubre la sidebar
    And el panel queda por encima del backdrop
    And ningun elemento de la sidebar es clickeable a traves del backdrop

  Scenario: Onboarding guide se muestra por encima de todo
    Given el usuario tiene un slide-over abierto (z-[70])
    When activa la guia de onboarding (z-[200]/z-[201])
    Then la guia aparece por encima del slide-over
    And el backdrop de onboarding cubre toda la pantalla incluyendo el slide-over
```

---

## 7. Orden de implementacion

1. **Modal.tsx** -- Reescribir como patron C con bottom-sheet responsive. Este es el fundamento.
2. **AppointmentForm.tsx** -- Ajustar border y footer al patron A exacto.
3. **BulkStatusUpdate.tsx**, **AgendaEventForm.tsx**, **LeadHistoryTimeline.tsx** -- Migrar a `<Modal>` refactorizado o aplicar patron C directamente.
4. **GoogleConnectionWizard.tsx**, **MetaConnectionWizard.tsx** -- Migrar a patron C variante wizard.
5. **Modales inline en views** (CompaniesView, ChatsView, PatientsView, etc.) -- Reemplazar por `<Modal>` o aplicar patron C inline.
6. **SellersView.tsx**, **UserApprovalView.tsx** -- Ajustar estilos (ya tienen bottom-sheet, solo necesitan estandarizacion visual).

---

## 8. Notas de implementacion

- **No crear un sistema de temas**: dark mode es el unico modo. Los valores son constantes, no variables CSS.
- **Animaciones**: Usar `tailwindcss-animate` plugin (ya presente en el proyecto) para `animate-in`, `fade-in`, `slide-in-from-bottom-4`, `zoom-in-95`. Si no esta instalado, agregar.
- **Escape key**: Todos los modales deben cerrarse con `Escape`. Agregar `useEffect` con `keydown` listener si no existe.
- **Focus trap**: Considerar agregar `@headlessui/react` Dialog o implementar focus trap manual para accesibilidad.
- **Body scroll lock**: Cuando un modal esta abierto, el body no debe scrollear. Usar `overflow-hidden` en `<body>` o `@radix-ui/react-dialog`.
- **Portal**: Los modales deben renderizarse en un portal (`createPortal`) para evitar problemas de z-index con parents que tengan `overflow: hidden` o `transform`.
