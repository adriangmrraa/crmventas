# 01 — Premium Sidebar with Background Images

**Feature**: Sidebar Premium con imagenes de fondo por seccion
**Source**: `clinicforge/frontend_react/src/components/Sidebar.tsx`
**Target**: `CRM VENTAS/frontend_react/src/components/Sidebar.tsx`
**Priority**: P1 — Visual identity / brand perception
**Estimated effort**: 2-3 hours

---

## 1. Context

### What ClinicForge has (reference implementation)

The ClinicForge sidebar is a premium navigation component with layered visual effects per menu item:

- **CARD_IMAGES constant**: A `Record<string, string>` mapping each menu `id` to an Unsplash thumbnail URL (`w=400&q=60`).
- **Background image layer**: An absolutely-positioned div with `bg-cover bg-center` that fades from `opacity: 0` to `opacity: 0.12` on hover/active, with `transition-opacity duration-500`.
- **Scale spring**: The entire button scales to `scale(1.03)` on hover using `cubic-bezier(0.34, 1.56, 0.64, 1)` (spring overshoot easing).
- **Ring highlight**: Active items get `ring-1 ring-white/[0.12] shadow-lg`; hovered items get `ring-1 ring-white/[0.06]`.
- **Active indicator bar**: A `w-[2px] h-5 bg-blue-400 rounded-r-full` bar pinned to the left edge, vertically centered.
- **Gradient edge**: A `bg-gradient-to-r from-blue-500/[0.06] to-transparent` overlay on hover/active.
- **Tooltip on hover**: After 600ms delay, a floating tooltip slides in from the left (`translateX(-4px) -> 0`) with 0.15s ease-out animation, showing title + hint text.
- **Touch support**: `onTouchStart` activates hover state; `onTouchEnd` clears it after 300ms delay; tooltip triggers after 500ms hold.
- **Image preloading**: All CARD_IMAGES are preloaded in a `useEffect` on mount.
- **Logout button**: On hover shows `bg-red-500/[0.08]` background with `scale(1.03)` spring effect.
- **Dark theme**: Root `bg-[#0a0e1a]`, borders `border-white/[0.06]`, text hierarchy `text-white` / `text-white/50` / `text-white/40`.

### What CRM VENTAS has now

The current CRM sidebar is functional but visually flat:

- Root background: `bg-medical-900` (custom Tailwind color).
- Hover: `hover:bg-white/[0.06] hover:text-white` — a single flat tint.
- Active: `bg-white/10 text-white` — slightly brighter flat tint.
- No background images, no scale animation, no ring highlights, no indicator bar, no gradient edge, no tooltips.
- Logout: `hover:bg-red-500/10` with `group-hover:rotate-12` on the icon (this rotate behavior is already present and should be kept).
- Icon size: `20px` (ClinicForge uses `17px` for a more refined feel).
- Borders use `border-medical-800` instead of the semi-transparent `border-white/[0.06]` pattern.

---

## 2. Requirements

### 2.1 SIDEBAR_IMAGES constant

Add a `SIDEBAR_IMAGES` constant (named differently from ClinicForge's `CARD_IMAGES` to avoid confusion if both projects are open) mapping each CRM menu item `id` to a thematic Unsplash URL. All URLs must use `w=400&q=60` format to keep payloads small.

```ts
const SIDEBAR_IMAGES: Record<string, string> = {
  dashboard:   'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=400&q=60',  // analytics dashboard
  leads:       'https://images.unsplash.com/photo-1552664730-d307ca884978?w=400&q=60',  // team meeting / leads
  pipeline:    'https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=400&q=60',  // data pipeline charts
  meta_leads:  'https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=400&q=60',  // social media / meta
  clients:     'https://images.unsplash.com/photo-1521791136064-7986c2920216?w=400&q=60',  // handshake / clients
  crm_agenda:  'https://images.unsplash.com/photo-1506784983877-45594efa4cbe?w=400&q=60',  // calendar / agenda
  chats:       'https://images.unsplash.com/photo-1577563908411-5077b6dc7624?w=400&q=60',  // messaging
  prospecting: 'https://images.unsplash.com/photo-1553877522-43269d4ea984?w=400&q=60',  // search / exploration
  analytics:   'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=400&q=60',  // charts
  marketing:   'https://images.unsplash.com/photo-1533750349088-cd871a92f312?w=400&q=60',  // marketing campaign
  hsm_automation: 'https://images.unsplash.com/photo-1586281380349-632531db7ed4?w=400&q=60',  // templates / automation
  sellers:     'https://images.unsplash.com/photo-1556745757-8d76bdb6984b?w=400&q=60',  // sales team
  tenants:     'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=400&q=60',  // buildings / companies
  profile:     'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=400&q=60',  // person portrait
  settings:    'https://images.unsplash.com/photo-1558618666-fcd25c85f82e?w=400&q=60',  // gears / config
};
```

### 2.2 Image preloading

On component mount, preload all images in a `useEffect`:

```ts
useEffect(() => {
  Object.values(SIDEBAR_IMAGES).forEach(src => {
    const img = new Image();
    img.src = src;
  });
}, []);
```

### 2.3 State additions

Add three new state variables to the component:

```ts
const [hoveredId, setHoveredId] = useState<string | null>(null);
const [touchedId, setTouchedId] = useState<string | null>(null);
const [tooltipId, setTooltipId] = useState<string | null>(null);
const tooltipTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
```

Add a `hint` field (string) to each menu item for tooltip content.

### 2.4 Hover effect (mouse)

Each menu item button must:

| Property | Default | Hover/Active |
|----------|---------|--------------|
| `transform` | `scale(1)` | `scale(1.03)` |
| Easing | - | `cubic-bezier(0.34, 1.56, 0.64, 1)` (spring overshoot) |
| Transition duration | - | `0.3s` |
| Ring | none | `ring-1 ring-white/[0.06]` |

Apply via inline `style` for the transform (since Tailwind cannot do custom cubic-bezier on hover) and className for the ring.

### 2.5 Background image layer

Inside each menu button, add an absolutely-positioned div **before** the content:

```
position: absolute; inset: 0;
background-image: url(SIDEBAR_IMAGES[item.id]);
background-size: cover; background-position: center;
opacity: 0 (default) -> 0.12 (hover/active);
transition: opacity 500ms ease-out;
```

### 2.6 Dark overlay

A second absolute div on top of the image:

| State | Class |
|-------|-------|
| Active | `bg-white/[0.08]` |
| Hovered (not active) | `bg-white/[0.04]` |
| Default | `bg-transparent` |

Transition: `transition-all duration-500`.

### 2.7 Gradient edge on hover

When hovered or active, render an additional absolute overlay:

```
bg-gradient-to-r from-blue-500/[0.06] to-transparent
pointer-events-none
```

Only rendered when `showImage` is true (hover or active).

### 2.8 Active state

| Element | Value |
|---------|-------|
| Ring | `ring-1 ring-white/[0.12]` |
| Shadow | `shadow-lg shadow-white/[0.03]` |
| Left indicator bar | `absolute left-0 top-1/2 -translate-y-1/2 w-[2px] h-5 bg-blue-400 rounded-r-full` |
| Icon color | `text-white` (full opacity) |
| Label color | `text-white` (full opacity) |

### 2.9 Collapsed tooltip

When `collapsed && !onCloseMobile` and the item has a `hint`, show a floating tooltip after 600ms hover delay:

- Position: `absolute left-full top-0 ml-3 z-50`
- Size: `w-56`
- Background: `bg-[#0d1117]`
- Border: `border border-white/[0.08]`
- Shadow: `shadow-2xl`
- Corner radius: `rounded-xl`
- Content: Title (`text-[11px] font-semibold text-white/80`) + hint (`text-[10px] text-white/40 leading-relaxed`)
- Arrow: CSS triangle on the left edge pointing back toward the sidebar
- Animation: slide in from left, `translateX(-4px) -> translateX(0)`, `opacity 0 -> 1`, duration `0.15s ease-out`
- Keyframe name: `sidebar-tooltip-in`

The tooltip is also shown when the sidebar is expanded (`!collapsed || onCloseMobile`) after the 600ms delay, providing contextual hints on any item.

### 2.10 Touch support (mobile)

| Event | Action |
|-------|--------|
| `onTouchStart` | Set `touchedId` to item id; start 500ms timer for tooltip |
| `onTouchEnd` | Clear `touchedId` after 300ms delay (`setTimeout`); clear tooltip timer |

The `isHovered` helper returns `true` if `hoveredId === id || touchedId === id`, unifying mouse and touch states.

### 2.11 Logout button

| Property | Default | Hover |
|----------|---------|-------|
| Background | `bg-transparent` | `bg-red-500/[0.08]` |
| Scale | `scale(1)` | `scale(1.03)` with same spring easing |
| Icon | `text-red-400/60` | `text-red-400` + existing `rotate-12` transform |
| Label | `text-red-400/60` | `text-red-400` |

### 2.12 Button geometry

- Border radius: `rounded-xl` (upgrade from current `rounded-lg`)
- Height: `h-11` (expanded), `h-10` (collapsed)
- Icon size: reduce from `20` to `17` for refined appearance
- Text size: `text-[13px]` (matches ClinicForge)
- Padding: `px-3` expanded, `justify-center px-0` collapsed
- Margin bottom: `mb-1` between items

### 2.13 Root sidebar styling

Replace current classes:

| Element | Current | New |
|---------|---------|-----|
| Sidebar `<aside>` | `bg-medical-900` | `bg-[#0a0e1a]` |
| Shadow | `shadow-xl` | `shadow-2xl` |
| Logo border | `border-medical-800` | `border-white/[0.06]` |
| Footer border | `border-medical-800` | `border-white/[0.06]` |
| Footer bg | `bg-medical-900/50` | (remove, inherit from aside) |
| User avatar | `bg-medical-600 rounded-full` | `bg-white/[0.06] rounded-lg` |
| User email | `text-white` | `text-white/70` |
| Toggle button | `bg-white/[0.08] text-white/70 border-white/[0.10]` | `bg-white/90 text-[#0a0e1a] hover:bg-white` (no border) |

---

## 3. Implementation Plan

### 3.1 Files to modify

| File | Action |
|------|--------|
| `frontend_react/src/components/Sidebar.tsx` | Primary modification (all changes below) |

No new files required. No new dependencies.

### 3.2 Step-by-step

1. Add imports: `useState`, `useEffect`, `useRef` from React (if not already imported).
2. Add `SIDEBAR_IMAGES` constant above the component (outside the function).
3. Add `useEffect` for image preloading.
4. Add state: `hoveredId`, `touchedId`, `tooltipId`, `tooltipTimer` ref.
5. Add `hint` property to each item in `menuItems` array (Spanish, concise).
6. Add `isHovered` helper: `(id: string) => hoveredId === id || touchedId === id`.
7. Replace each menu `<button>` with the layered structure:
   - Wrap in a `<div className="relative mb-1">` container.
   - Button gets `onMouseEnter`, `onMouseLeave`, `onTouchStart`, `onTouchEnd` handlers.
   - Inside button: image layer div, overlay div, gradient div (conditional), content div with icon + label + active bar.
   - After button: tooltip div (conditional).
8. Update logout button with `hoveredId` tracking, scale style, and `bg-red-500/[0.08]` overlay.
9. Update root `<aside>` and footer classes per section 2.13.
10. Add `<style>` block with `@keyframes sidebar-tooltip-in` at the bottom of the component.

### 3.3 Hint texts (suggested)

```ts
{ id: 'dashboard',      hint: 'Metricas clave de ventas, leads y conversion en tiempo real' },
{ id: 'leads',           hint: 'Todos los leads con estado, origen y seguimiento' },
{ id: 'pipeline',        hint: 'Kanban visual de oportunidades por etapa de venta' },
{ id: 'meta_leads',      hint: 'Leads entrantes desde formularios de Meta Ads' },
{ id: 'clients',         hint: 'Base de clientes convertidos con historial de compras' },
{ id: 'crm_agenda',      hint: 'Agenda de llamadas, demos y reuniones del equipo' },
{ id: 'chats',           hint: 'Conversaciones de WhatsApp e Instagram en un solo lugar' },
{ id: 'prospecting',     hint: 'Busqueda activa de prospectos y enriquecimiento de datos' },
{ id: 'analytics',       hint: 'Rendimiento por vendedor, canal y campana' },
{ id: 'marketing',       hint: 'ROI de campanas publicitarias con atribucion de leads' },
{ id: 'hsm_automation',  hint: 'Plantillas HSM y secuencias de automatizacion' },
{ id: 'sellers',         hint: 'Equipo de ventas: setters, closers y asignacion de leads' },
{ id: 'tenants',         hint: 'Empresas y organizaciones registradas en la plataforma' },
{ id: 'profile',         hint: 'Tu perfil, cuenta y preferencias personales' },
{ id: 'settings',        hint: 'Configuracion general, integraciones y credenciales' },
```

---

## 4. Acceptance Criteria (Gherkin)

### Scenario 1: Background image fades in on hover

```gherkin
Feature: Sidebar menu item hover effect

  Scenario: User hovers over a menu item and sees background image
    Given the sidebar is visible and expanded
    When the user hovers over the "Leads" menu item
    Then the background image for "leads" fades in to opacity 0.12 over 500ms
    And the button scales to 1.03 with spring easing (cubic-bezier 0.34, 1.56, 0.64, 1)
    And a ring-1 ring-white/[0.06] border appears around the button
    And a blue gradient overlay (from-blue-500/[0.06] to-transparent) is visible
    When the user moves the mouse away
    Then the background image fades back to opacity 0 over 500ms
    And the button returns to scale(1)
    And the ring and gradient disappear
```

### Scenario 2: Active item shows indicator bar and persistent styling

```gherkin
Feature: Sidebar active item visual state

  Scenario: User navigates to a page and sees the active indicator
    Given the user is on the "/crm/leads" page
    Then the "leads" menu item displays:
      | property              | value                                         |
      | ring                  | ring-1 ring-white/[0.12]                      |
      | shadow                | shadow-lg shadow-white/[0.03]                 |
      | left bar              | w-[2px] h-5 bg-blue-400 rounded-r-full        |
      | background image      | visible at opacity 0.12                       |
      | icon color            | text-white (full)                             |
      | label color           | text-white (full)                             |
    And all other menu items show default (non-active) styling
```

### Scenario 3: Tooltip appears on hover after delay

```gherkin
Feature: Sidebar tooltip on hover

  Scenario: Tooltip slides in after hovering for 600ms
    Given the sidebar is visible (expanded or collapsed)
    When the user hovers over the "Pipeline" menu item
    And waits for 600 milliseconds
    Then a tooltip appears to the right of the item
    And the tooltip slides in from the left (translateX -4px to 0) over 0.15s
    And the tooltip shows the title "Pipeline" in text-[11px] font-semibold
    And the tooltip shows the hint "Kanban visual de oportunidades por etapa de venta" in text-[10px]
    And the tooltip has a left-pointing arrow
    When the user moves the mouse away before 600ms
    Then no tooltip is shown
```

---

## 5. Dark Theme Compliance

All styling must follow the established dark palette. No light mode exists.

| Element | Required class | Forbidden |
|---------|---------------|-----------|
| Sidebar root | `bg-[#0a0e1a]` | `bg-white`, `bg-gray-*`, `bg-medical-900` |
| Borders | `border-white/[0.06]` | `border-medical-*`, `border-gray-*` |
| Primary text | `text-white` | `text-black`, `text-gray-900` |
| Secondary text | `text-white/50` | `text-gray-400`, `text-gray-500` |
| Muted text | `text-white/40` or `text-white/30` | `text-gray-600` |
| Card/tooltip bg | `bg-[#0d1117]` | `bg-white`, `bg-gray-100` |
| Input/avatar bg | `bg-white/[0.06]` or `bg-white/[0.04]` | `bg-gray-200` |
| Active tint | `bg-white/[0.08]` | `bg-blue-500`, `bg-primary-*` |
| Hover tint | `bg-white/[0.04]` | `bg-gray-700`, `bg-white/10` |
| Shadows | `shadow-white/[0.03]` | `shadow-black` (default is acceptable) |

### Image opacity rule

Background images must **never** exceed `opacity: 0.12`. This ensures text remains readable on dark backgrounds without additional blur filters. The dark overlay (`bg-white/[0.04]` or `bg-white/[0.08]`) stacks on top for further contrast.

### Accent color

The left indicator bar and gradient edge use `blue-400` / `blue-500` as the accent. This is consistent with ClinicForge and works well on the `#0a0e1a` background. If CRM VENTAS adopts a different brand accent later, only these two values need updating.

---

## 6. Notes

- The `SIDEBAR_IMAGES` URLs point to Unsplash which serves images via CDN. For production, consider self-hosting these thumbnails or using a proxy to avoid third-party dependency.
- Icon size reduction from 20 to 17 is a visual refinement. If the team prefers the larger icons, keep 20 but adjust `gap` from `gap-3` to `gap-2.5` to maintain proportions.
- The `bg-medical-900` class is replaced entirely. If `medical-900` is used elsewhere in the app and maps to a value close to `#0a0e1a`, consider updating the Tailwind config instead of hardcoding the hex. However, for sidebar-specific premium styling, the hardcoded hex ensures exact parity with ClinicForge.
- The tooltip `hint` texts are in Spanish (default language per CLAUDE.md). They should be added to locale files (`es.json`, `en.json`, `fr.json`) if i18n is a requirement for CRM VENTAS. For the initial implementation, inline strings are acceptable since hints are supplementary UI.
