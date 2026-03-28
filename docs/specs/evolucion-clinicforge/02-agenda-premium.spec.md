# 02 — Agenda Premium: Dark Mode + Mobile-First

**Origen**: ClinicForge `AgendaView.tsx` (lines 640-930+) + `MobileAgenda.tsx` + `DateStrip.tsx`
**Destino**: CRM VENTAS `CrmAgendaView.tsx` + shared components
**Prioridad**: Alta — la agenda es la vista mas usada del CRM

---

## 1. Context: ClinicForge vs CRM VENTAS

### ClinicForge Agenda (referencia)
| Aspecto | Estado |
|---------|--------|
| FullCalendar dark mode | 30+ CSS variables override, todo oscuro (`bg-white/[0.03]`, borders `white/[0.06]`) |
| Mobile detection | `window.innerWidth < 768` con resize listener, render condicional |
| MobileAgenda | Componente completo con 4 view modes (day/week/month/list) |
| DateStrip | Scroll horizontal, dark theme, selected = `bg-blue-600`, today = dot indicator |
| Event cards (mobile) | `border-l-4` por status, `bg-white/[0.03]`, payment dots, duration badge |
| Source legend | 4 sources: Ventas IA (blue), Nova (purple), Manual (green), GCal (gray) |
| Empty state | `<Clock size={48}>` icon con `text-white/20`, mensaje `text-white/40` |
| Now indicator | Red line `#ef4444`, pulsing dot (`pulse-red` animation), glowing arrow |
| Past days | Opacidad 0.5, grayscale en eventos pasados |
| Slot height | 70px min, eventos tipo tarjeta con `border-radius: 8px` |
| Calendar wrapper | `bg-white/[0.03] backdrop-blur-lg border-white/[0.06] rounded-2xl` |
| Resource view | `resourceTimeGridDay` para ver profesionales lado a lado |
| AppointmentCard | Componente reutilizable con status colors, payment status, source badge |

### CRM VENTAS Agenda (estado actual)
| Aspecto | Estado |
|---------|--------|
| FullCalendar dark mode | **Sin overrides** — fondo blanco `bg-white/60`, borders `white/40` |
| Mobile detection | Implementado (`isMobile` state + resize listener) |
| MobileAgenda | Importa el shared `MobileAgenda.tsx`, pero falta dark CSS en desktop |
| DateStrip | Usa el shared `DateStrip.tsx` (ya tiene dark theme) |
| Event cards (mobile) | Delegado a MobileAgenda, funciona pero sin payment dots |
| Source legend | No existe — todos los eventos son azul `#3b82f6` plano |
| Empty state | No existe — calendario vacio sin indicacion visual |
| Now indicator | `nowIndicator={true}` pero sin CSS overrides (default rojo sin glow) |
| Past days | Sin tratamiento visual |
| Slot height | Default FullCalendar (pequeño) |
| Calendar wrapper | `bg-white/60 backdrop-blur-lg border-white/40` **(blanco, NO dark)** |
| Resource view | No usa resource plugin — solo timeGrid basico |
| Seller filter | Implementado con dropdown (funcional) |

### Gap principal
El desktop FullCalendar en CRM VENTAS usa wrapper **blanco** (`bg-white/60 border-white/40`) y no tiene CSS overrides para dark mode. En contraste, ClinicForge tiene 30+ CSS rules que hacen el calendario completamente oscuro. La mobile experience ya esta parcialmente resuelta porque reutiliza `MobileAgenda`, pero el desktop necesita la migracion completa de estilos.

---

## 2. Requirements

### 2.1 FullCalendar Dark Mode CSS Overrides

Copiar el bloque completo de `<style>` de ClinicForge `AgendaView.tsx` (lines 653-861) al `CrmAgendaView.tsx`. Incluye:

#### Slot y eventos base (lines 654-693)
```css
/* Slot height */
.fc-timegrid-slot { height: 70px !important; min-height: 70px !important; }

/* Eventos tipo tarjeta */
.fc-timegrid-event { border-radius: 8px !important; padding: 6px !important; min-height: 60px !important; box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important; }
.fc-timegrid-event-harness { margin: 2px 4px !important; }

/* Slot labels */
.fc-timegrid-slot-label { font-size: 14px !important; font-weight: 600 !important; padding: 8px !important; }

/* Past days opacity */
.fc-day-past { background-color: rgba(255,255,255,0.02) !important; opacity: 0.5 !important; }
.fc-timegrid-col.fc-day-past { background-color: rgba(255,255,255,0.02) !important; }
.fc-event-past { opacity: 0.7 !important; filter: grayscale(0.5); }
```

#### Now indicator (lines 696-739)
```css
/* Red line */
.fc-now-indicator-line { border-color: #ef4444 !important; border-width: 2px !important; z-index: 10 !important; }
.fc-now-indicator-line::before { content: ''; position: absolute; left: 0; top: -4px; width: 10px; height: 10px; background: #ef4444; border-radius: 50%; box-shadow: 0 0 8px rgba(239,68,68,0.6); }

/* Glowing arrow */
.fc-now-indicator-arrow { margin-top: -6px !important; border-width: 6px 0 6px 8px !important; border-color: transparent transparent transparent #ef4444 !important; filter: drop-shadow(0 0 4px rgba(239,68,68,0.8)); }
.fc-now-indicator-arrow::after { content: ''; position: absolute; top: -4px; left: -12px; width: 8px; height: 8px; background-color: #ef4444; border-radius: 50%; box-shadow: 0 0 10px #ef4444; animation: pulse-red 2s infinite; }

/* Pulse animation */
@keyframes pulse-red {
  0% { box-shadow: 0 0 0 0 rgba(239,68,68,0.7); }
  70% { box-shadow: 0 0 0 10px rgba(239,68,68,0); }
  100% { box-shadow: 0 0 0 0 rgba(239,68,68,0); }
}
```

#### Dark mode CSS variables (lines 741-753) — MANDATORY
```css
.fc {
  --fc-border-color: rgba(255,255,255,0.06);
  --fc-page-bg-color: transparent;
  --fc-neutral-bg-color: rgba(255,255,255,0.04);
  --fc-list-event-hover-bg-color: rgba(255,255,255,0.04);
  --fc-today-bg-color: rgba(59,130,246,0.08);
  --fc-highlight-color: rgba(59,130,246,0.12);
  --fc-non-business-color: rgba(255,255,255,0.02);
  --fc-bg-event-opacity: 0.15;
  --fc-neutral-text-color: rgba(255,255,255,0.5);
  --fc-event-text-color: #fff;
  color: rgba(255,255,255,0.85);
}
```

#### Toolbar buttons (lines 757-783)
```css
.fc .fc-button-primary { background-color: rgba(255,255,255,0.04) !important; border-color: rgba(255,255,255,0.08) !important; color: rgba(255,255,255,0.7) !important; }
.fc .fc-button-primary:hover { background-color: rgba(255,255,255,0.08) !important; color: #fff !important; }
.fc .fc-button-primary.fc-button-active,
.fc .fc-button-primary:not(:disabled).fc-button-active { background-color: #fff !important; color: #0a0e1a !important; border-color: #fff !important; }
.fc .fc-today-button { background-color: rgba(255,255,255,0.04) !important; border-color: rgba(255,255,255,0.08) !important; color: rgba(255,255,255,0.7) !important; }
.fc .fc-today-button:hover { background-color: rgba(255,255,255,0.08) !important; color: #fff !important; }
.fc .fc-today-button:disabled { opacity: 0.3 !important; }
```

#### Toolbar title (line 787)
```css
.fc .fc-toolbar-title { color: #fff !important; }
```

#### Column headers (lines 791-797)
```css
.fc .fc-col-header-cell { background-color: rgba(255,255,255,0.04) !important; border-color: rgba(255,255,255,0.06) !important; }
.fc .fc-col-header-cell-cushion { color: rgba(255,255,255,0.7) !important; }
```

#### Time slot labels (lines 800-802)
```css
.fc .fc-timegrid-slot-label-cushion { color: rgba(255,255,255,0.5) !important; }
```

#### Day number in month view (lines 805-807)
```css
.fc .fc-daygrid-day-number { color: rgba(255,255,255,0.7) !important; }
```

#### List view (lines 810-827)
```css
.fc .fc-list-day-cushion { background-color: rgba(255,255,255,0.04) !important; }
.fc .fc-list-day-cushion a { color: #fff !important; }
.fc .fc-list-event td { border-color: rgba(255,255,255,0.06) !important; }
.fc .fc-list-event:hover td { background-color: rgba(255,255,255,0.04) !important; }
.fc .fc-list-event-title a { color: rgba(255,255,255,0.85) !important; }
.fc .fc-list-event-time { color: rgba(255,255,255,0.5) !important; }
```

#### Resource labels (lines 830-833)
```css
.fc .fc-resource-cell { background-color: rgba(255,255,255,0.04) !important; color: rgba(255,255,255,0.7) !important; }
```

#### Scrollbar (lines 836-845)
```css
.fc ::-webkit-scrollbar { width: 6px; }
.fc ::-webkit-scrollbar-track { background: transparent; }
.fc ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 3px; }
```

#### More link (lines 848-850)
```css
.fc .fc-daygrid-more-link { color: rgba(255,255,255,0.6) !important; }
```

#### Popover (lines 853-860)
```css
.fc .fc-popover { background: #0d1117 !important; border-color: rgba(255,255,255,0.06) !important; }
.fc .fc-popover-header { background: rgba(255,255,255,0.04) !important; color: #fff !important; }
```

### 2.2 Calendar Wrapper — Dark Background

**Current** (line 292 of CrmAgendaView):
```tsx
<div className="h-[calc(100vh-140px)] bg-white/60 backdrop-blur-lg border border-white/40 shadow-xl rounded-2xl p-2 sm:p-4 overflow-y-auto">
```

**Target**:
```tsx
<div className="h-[calc(100vh-140px)] bg-white/[0.03] backdrop-blur-lg border border-white/[0.06] shadow-2xl rounded-2xl md:rounded-3xl p-2 sm:p-4 overflow-y-auto">
```

### 2.3 Mobile Detection + MobileAgenda

Already implemented in CRM VENTAS (lines 45-57, 270-289). Verify:
- `isMobile` state with `window.innerWidth < 768` -- DONE
- Resize event listener -- DONE
- Conditional render: `isMobile ? <MobileAgenda> : <FullCalendar>` -- DONE
- `mobileAppointments` mapping CRM fields to MobileAgenda interface -- DONE

**No changes needed for mobile detection.** The shared `MobileAgenda.tsx` and `DateStrip.tsx` already have dark theme from ClinicForge.

### 2.4 Source Colors + Event Color by Source

Add `SOURCE_COLORS` constant (adapted for CRM sources):

```typescript
const SOURCE_COLORS: Record<string, { hex: string; label: string; bgClass: string; textClass: string }> = {
  ai: {
    hex: '#3b82f6',
    label: 'Ventas IA',
    bgClass: 'bg-blue-500/10',
    textClass: 'text-blue-400'
  },
  nova: {
    hex: '#a855f7',
    label: 'Nova',
    bgClass: 'bg-purple-500/10',
    textClass: 'text-purple-400'
  },
  manual: {
    hex: '#22c55e',
    label: 'Manual',
    bgClass: 'bg-green-500/10',
    textClass: 'text-green-400'
  },
  gcalendar: {
    hex: '#6b7280',
    label: 'GCalendar',
    bgClass: 'bg-white/[0.06]',
    textClass: 'text-white/50'
  },
};
```

Update `calendarEvents` mapping to use `SOURCE_COLORS[evt.source]?.hex` instead of hardcoded `#3b82f6`:

```typescript
const calendarEvents = filteredEvents.map((evt) => ({
  id: evt.id,
  title: evt.title,
  start: evt.start_datetime,
  end: evt.end_datetime,
  backgroundColor: SOURCE_COLORS[evt.source || 'manual']?.hex || '#3b82f6',
  borderColor: SOURCE_COLORS[evt.source || 'manual']?.hex || '#3b82f6',
  extendedProps: { ...evt, eventType: 'agenda_event' },
}));
```

### 2.5 Source Legend

Add a source legend row below the header (visible on desktop only):

```tsx
<div className="hidden md:flex items-center gap-4 mb-3">
  {Object.entries(SOURCE_COLORS).map(([key, src]) => (
    <div key={key} className="flex items-center gap-1.5">
      <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: src.hex }} />
      <span className="text-xs text-white/50">{src.label}</span>
    </div>
  ))}
</div>
```

### 2.6 Seller Filter Dropdown

Already implemented (lines 247-261). The dropdown uses dark-compatible styling. No changes required beyond verifying the `<option>` elements render correctly against the dark background.

### 2.7 Empty State

Add an empty state inside the calendar wrapper when `loading === false` and `events.length === 0`:

```tsx
{!loading && events.length === 0 && (
  <div className="absolute inset-0 flex flex-col items-center justify-center z-10">
    <Clock size={48} className="text-white/20 mb-3" />
    <p className="text-sm text-white/40">{t('agenda_crm.no_events')}</p>
  </div>
)}
```

The calendar wrapper needs `relative` positioning to support the absolute overlay.

### 2.8 Now Indicator (Red Pulse)

Already enabled via `nowIndicator={true}` on line 307. The CSS overrides from section 2.1 (now-indicator rules) will activate the red pulse glow and dot animation. No FullCalendar prop changes needed.

---

## 3. Components to Create/Modify

### 3.1 Components already shared (NO action needed)

| Component | Path | Dark theme |
|-----------|------|------------|
| `MobileAgenda.tsx` | `frontend_react/src/components/MobileAgenda.tsx` | Yes (all `bg-white/[0.03]`, `text-white`, `border-white/[0.06]`) |
| `DateStrip.tsx` | `frontend_react/src/components/DateStrip.tsx` | Yes (`bg-white/[0.02]`, `bg-blue-600` selected, `text-white/50` text) |

Both are already imported by `CrmAgendaView.tsx` and work correctly. No new components to create.

### 3.2 Files to modify

| File | Changes |
|------|---------|
| `modules/crm_sales/views/CrmAgendaView.tsx` | (1) Add `<style>` block with all 30+ CSS overrides, (2) change calendar wrapper from `bg-white/60` to `bg-white/[0.03]`, (3) add `SOURCE_COLORS` constant, (4) use dynamic event colors, (5) add source legend, (6) add empty state with Clock icon, (7) add `listPlugin` import for list view support |
| `locales/es.json` | Add `agenda_crm.no_events` key |
| `locales/en.json` | Add `agenda_crm.no_events` key |
| `locales/fr.json` | Add `agenda_crm.no_events` key |

### 3.3 Imports to add in CrmAgendaView.tsx

```typescript
import listPlugin from '@fullcalendar/list';
import { Clock } from 'lucide-react';
```

---

## 4. FullCalendar CSS Variables — Complete Override List

All variables set on the `.fc` selector:

| Variable | Value | Purpose |
|----------|-------|---------|
| `--fc-border-color` | `rgba(255,255,255,0.06)` | All grid borders |
| `--fc-page-bg-color` | `transparent` | Calendar background |
| `--fc-neutral-bg-color` | `rgba(255,255,255,0.04)` | Header cells, non-business bg |
| `--fc-list-event-hover-bg-color` | `rgba(255,255,255,0.04)` | List view hover |
| `--fc-today-bg-color` | `rgba(59,130,246,0.08)` | Today column highlight |
| `--fc-highlight-color` | `rgba(59,130,246,0.12)` | Selection highlight |
| `--fc-non-business-color` | `rgba(255,255,255,0.02)` | Non-business hours bg |
| `--fc-bg-event-opacity` | `0.15` | Background event opacity |
| `--fc-neutral-text-color` | `rgba(255,255,255,0.5)` | Secondary text |
| `--fc-event-text-color` | `#fff` | Event text color |

Plus the `color` property on `.fc`:
| Property | Value | Purpose |
|----------|-------|---------|
| `color` | `rgba(255,255,255,0.85)` | Base text color |

### Additional CSS selectors overridden (20+)

| Selector | Key properties |
|----------|---------------|
| `.fc .fc-button-primary` | `bg rgba(255,255,255,0.04)`, `border rgba(255,255,255,0.08)`, `color rgba(255,255,255,0.7)` |
| `.fc .fc-button-primary:hover` | `bg rgba(255,255,255,0.08)`, `color #fff` |
| `.fc .fc-button-primary.fc-button-active` | `bg #fff`, `color #0a0e1a`, `border #fff` |
| `.fc .fc-today-button` | Same as button-primary |
| `.fc .fc-today-button:hover` | Same as button-primary:hover |
| `.fc .fc-today-button:disabled` | `opacity 0.3` |
| `.fc .fc-toolbar-title` | `color #fff` |
| `.fc .fc-col-header-cell` | `bg rgba(255,255,255,0.04)`, `border rgba(255,255,255,0.06)` |
| `.fc .fc-col-header-cell-cushion` | `color rgba(255,255,255,0.7)` |
| `.fc .fc-timegrid-slot-label-cushion` | `color rgba(255,255,255,0.5)` |
| `.fc .fc-daygrid-day-number` | `color rgba(255,255,255,0.7)` |
| `.fc .fc-list-day-cushion` | `bg rgba(255,255,255,0.04)` |
| `.fc .fc-list-day-cushion a` | `color #fff` |
| `.fc .fc-list-event td` | `border rgba(255,255,255,0.06)` |
| `.fc .fc-list-event:hover td` | `bg rgba(255,255,255,0.04)` |
| `.fc .fc-list-event-title a` | `color rgba(255,255,255,0.85)` |
| `.fc .fc-list-event-time` | `color rgba(255,255,255,0.5)` |
| `.fc .fc-resource-cell` | `bg rgba(255,255,255,0.04)`, `color rgba(255,255,255,0.7)` |
| `.fc ::-webkit-scrollbar` | `width 6px` |
| `.fc ::-webkit-scrollbar-track` | `bg transparent` |
| `.fc ::-webkit-scrollbar-thumb` | `bg rgba(255,255,255,0.1)`, `border-radius 3px` |
| `.fc .fc-daygrid-more-link` | `color rgba(255,255,255,0.6)` |
| `.fc .fc-popover` | `bg #0d1117`, `border rgba(255,255,255,0.06)` |
| `.fc .fc-popover-header` | `bg rgba(255,255,255,0.04)`, `color #fff` |
| `.fc-timegrid-slot` | `height 70px` |
| `.fc-timegrid-event` | `border-radius 8px`, `padding 6px`, `min-height 60px` |
| `.fc-timegrid-event-harness` | `margin 2px 4px` |
| `.fc-timegrid-slot-label` | `font-size 14px`, `font-weight 600` |
| `.fc-day-past` | `bg rgba(255,255,255,0.02)`, `opacity 0.5` |
| `.fc-event-past` | `opacity 0.7`, `filter grayscale(0.5)` |
| `.fc-now-indicator-line` | `border-color #ef4444`, `border-width 2px`, `z-index 10` |
| `.fc-now-indicator-line::before` | Red dot with glow |
| `.fc-now-indicator-arrow` | Red arrow with drop-shadow |
| `.fc-now-indicator-arrow::after` | Pulsing red dot (pulse-red keyframes) |

**Total: 11 CSS variables + 33 selector overrides + 1 keyframes animation = 45 CSS rules**

---

## 5. Acceptance Criteria (Gherkin)

```gherkin
Feature: CRM Agenda Premium Dark Mode

  Scenario: Desktop FullCalendar renders in dark mode
    Given I am on the CRM Agenda page on a desktop browser (>= 768px)
    When the page loads
    Then the calendar wrapper has class "bg-white/[0.03]" and "border-white/[0.06]"
    And the FullCalendar toolbar title is white (#fff)
    And the toolbar buttons have dark background (rgba(255,255,255,0.04))
    And the active toolbar button is inverted (bg white, text #0a0e1a)
    And the column headers have dark background (rgba(255,255,255,0.04))
    And the time slot labels are semi-transparent white (rgba(255,255,255,0.5))
    And the today column has a subtle blue highlight (rgba(59,130,246,0.08))
    And the now-indicator line is red (#ef4444) with a pulsing glow dot
    And past days have reduced opacity (0.5) and past events have grayscale filter

  Scenario: Source legend and dynamic event colors
    Given the CRM Agenda has events from sources "ai", "nova", "manual", "gcalendar"
    When I view the desktop calendar
    Then each event's background color matches its source (blue/purple/green/gray)
    And a source legend is visible below the header with 4 colored dots and labels
    And the source legend is hidden on mobile (< 768px)

  Scenario: Mobile agenda renders with 4 view modes
    Given I am on the CRM Agenda page on a mobile device (< 768px)
    When the page loads
    Then the MobileAgenda component is rendered instead of FullCalendar
    And I see 4 view mode buttons: Day, Week, Month, List
    And each event card has a left border color based on its status
    And each event card has dark background (bg-white/[0.03]) with white text
    And the DateStrip shows in day view with dark theme (bg-white/[0.02])

  Scenario: Empty state displays when no events exist
    Given I am on the CRM Agenda page
    And there are no events for the current date range
    When the page finishes loading
    Then I see a Clock icon (size 48) with opacity 20%
    And below it a text message "No hay eventos programados" in text-white/40
    And the FullCalendar grid is still rendered behind the overlay
```

---

## 6. Files to Create/Modify — Summary

| Action | File | Description |
|--------|------|-------------|
| **MODIFY** | `frontend_react/src/modules/crm_sales/views/CrmAgendaView.tsx` | Add `<style>` with 45 CSS rules, change wrapper classes, add SOURCE_COLORS, dynamic event colors, source legend, empty state, import listPlugin + Clock |
| **MODIFY** | `frontend_react/src/locales/es.json` | Add `"agenda_crm.no_events": "No hay eventos programados"` |
| **MODIFY** | `frontend_react/src/locales/en.json` | Add `"agenda_crm.no_events": "No scheduled events"` |
| **MODIFY** | `frontend_react/src/locales/fr.json` | Add `"agenda_crm.no_events": "Aucun evenement programme"` |
| **VERIFY** | `frontend_react/src/components/MobileAgenda.tsx` | Confirm dark theme classes are present (no changes expected) |
| **VERIFY** | `frontend_react/src/components/DateStrip.tsx` | Confirm dark theme classes are present (no changes expected) |

No new files need to be created. The shared `MobileAgenda.tsx` and `DateStrip.tsx` are already imported and dark-themed.
