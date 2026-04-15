# SPEC-10: Design System Migration (crmcodexy visual style)
## Origin: crmcodexy UI/UX migration
## Priority: Alta
## Estimated Complexity: Alta

### Intent

Migrar el estilo visual completo de crmcodexy a CRM VENTAS. Esto incluye: sistema de colores (violeta #8F3DFF como primary), tonos de fondo, cards con glassmorphism, badges, botones, tablas, scrollbars custom, glow effects, y la forma general de presentar datos. CRM VENTAS actualmente usa un dark theme con blue (#3b82f6) como primary — se cambia a violeta neón.

### Referencia Visual (Source)

**Archivo de referencia**: `C:/Users/Asus/Documents/estabilizacion/crmcodexy/src/app/globals.css`

#### Color System (oklch)

**Light Mode:**
- Background: `oklch(0.985 0.002 285)` — near-white con undertone violeta
- Foreground: `oklch(0.10 0.01 285)` — texto oscuro
- Primary: `oklch(0.50 0.27 285)` — #8F3DFF violeta neón
- Secondary: `oklch(0.96 0.012 285)`
- Muted: `oklch(0.96 0.008 285)`
- Border: `oklch(0.91 0.006 285)`
- Sidebar: `oklch(0.975 0.006 285)` — tinte violeta sutil

**Dark Mode:**
- Background: `oklch(0.07 0.015 285)` — ~#0A0A0A con undertone violeta
- Foreground: `oklch(0.95 0.005 285)` — near-white
- Primary: `oklch(0.58 0.27 285)` — violeta más brillante para contraste
- Card: `oklch(0.10 0.02 285)` — fondo de cards profundo
- Border: `oklch(0.25 0.02 285)`
- Sidebar: `oklch(0.09 0.03 285)` — violeta-black profundo

#### Glow Effects
```css
.glow-violet { box-shadow: 0 0 24px oklch(0.58 0.27 285 / 0.15); }
.glow-violet-sm { box-shadow: 0 0 12px oklch(0.58 0.27 285 / 0.1); }
.glow-emerald-sm { box-shadow: 0 0 10px oklch(0.7 0.18 160 / 0.1); }
.dark .card-glow { border-color: oklch(0.58 0.27 285 / 0.15); box-shadow: 0 0 20px oklch(0.58 0.27 285 / 0.08); }
.neon-text { text-shadow: 0 0 20px oklch(0.58 0.27 285 / 0.3); }
```

#### Custom Scrollbars
```css
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-thumb { background: oklch(0.5 0 0 / 20%); border-radius: 3px; }
.dark ::-webkit-scrollbar-thumb { background: oklch(1 0 0 / 8%); }
```

#### Radius Scale
```
--radius: 0.625rem
sm: 0.375rem | md: 0.5rem | lg: 0.625rem | xl: 0.875rem | 2xl: 1.125rem
```

### Requirements

#### Colors (MUST)
1. Primary color MUST change from blue (#3b82f6) to violeta (#8F3DFF / oklch 0.50-0.58 0.27 285)
2. Dark mode background MUST use oklch(0.07 0.015 285) — NOT pure black
3. Card backgrounds MUST use oklch(0.10 0.02 285) in dark mode
4. Borders MUST have violeta undertone (hue 285)
5. Sidebar MUST use violeta-tinted background
6. ALL accent colors MUST be recalibrated: emerald for success, amber for warning, red for error, violeta for primary actions

#### Components (MUST)
7. Buttons MUST use `bg-[#8F3DFF] hover:bg-[#7B2FE6]` for primary actions
8. Badges MUST use the crmcodexy pattern: colored dot (1.5px) + label with 10% opacity background
9. KPI cards MUST use glassmorphism: subtle border + background opacity + optional glow
10. Tables MUST use hover states with `hover:bg-muted/50` and subtle left-border on active/selected rows
11. Form inputs MUST use `bg-transparent border-border/60` with focus ring in primary color

#### Data Display Patterns (MUST)
12. Stats cards MUST show: icon in colored pill (top-right), large value (2xl-3xl font), description text, optional trend badge
13. Estado badges MUST use dot + label pattern (NOT filled badges):
    - Lead: blue dot + blue/10 bg
    - Contactado: amber dot + amber/10 bg
    - Negociacion: violet dot + violet/10 bg
    - Ganado: emerald dot + emerald/10 bg
    - Perdido: red dot + red/10 bg
14. Priority badges MUST follow: Baja (slate), Media (blue), Alta (amber), Urgente (red with glow)
15. Author/role badges: CEO/admin = purple (#8F3DFF/15 bg, #8F3DFF text), vendedor = blue
16. Time display MUST use relative format: "ahora", "hace 5m", "hace 3h", "hace 2d"

#### Layout (MUST)
17. Sidebar active state MUST show 3px left bar (rounded-r-full) in primary color
18. Sidebar collapsed mode MUST be 60px with icon-only + tooltips
19. Topbar MUST be 48px (h-12) with border-bottom
20. Content padding: mobile px-4 py-4, tablet px-6 py-5, desktop px-8 py-6

#### Effects (SHOULD)
21. Cards SHOULD have subtle glow on hover in dark mode
22. Active sidebar icon SHOULD have glow effect
23. Primary buttons SHOULD have subtle glow shadow
24. Scrollbars SHOULD be 6px, semi-transparent, rounded

### Scope of Changes

#### Global Styles (1 file)
- `frontend_react/src/index.css` or equivalent — complete rewrite of CSS custom properties

#### Tailwind Config
- `frontend_react/tailwind.config.ts` — extend colors with oklch values, add glow utilities

#### Component-by-Component Updates

**Layout Components:**
- `Layout.tsx` — sidebar bg, content bg, scrollbar styling
- `Sidebar` component — active state indicator, collapsed mode, logo glow
- Header/Topbar — height, border, user menu styling

**Data Display Components (update ALL existing views):**
- Every `<Badge>` usage → dot + label pattern
- Every stat/KPI card → icon pill + large value + description
- Every table → hover states, left-border accents
- Every button variant → primary = #8F3DFF, ghost, outline, destructive

**Specific Views to Restyle:**
- CrmDashboardView — KPI cards, activity feed, quick actions
- LeadsView — table rows, status badges, search bar
- LeadDetailView — tabs, notes timeline, task cards
- KanbanPipelineView — column headers, deal cards, drag states
- CrmAgendaView — event cards, color coding
- ChatsView — conversation list, message bubbles, unread badges
- SellersView — seller cards, approval cards
- SalesAnalyticsView — chart styling, period selector
- ALL new pages from specs 01-09 (these should already use the new style)

### Scenarios

#### Scenario 1: Primary button renders with violet
Given the user sees any primary action button
When the page renders
Then the button background MUST be #8F3DFF
And hover state MUST be #7B2FE6
And the button SHOULD have subtle violet glow shadow

#### Scenario 2: Dark mode background is NOT pure black
Given dark mode is active
When any page renders
Then the main background MUST be oklch(0.07 0.015 285) — NOT #000000
And cards MUST be oklch(0.10 0.02 285) — NOT #111111
And there MUST be a subtle violet undertone visible

#### Scenario 3: Lead status uses dot+label badge
Given a lead with status "contactado"
When displayed in a table or card
Then the badge MUST show: amber dot (2px) + "Contactado" text
And the background MUST be amber-500/10
And the text MUST be amber-700 (light) or amber-400 (dark)

#### Scenario 4: KPI card follows glassmorphism pattern
Given a KPI card on the dashboard
When rendered
Then it MUST show icon in colored pill (top-right corner)
And the value MUST be 2xl-3xl font size
And in dark mode the card SHOULD have subtle border glow

#### Scenario 5: Sidebar active state shows violet bar
Given the user is on /crm/leads
When the sidebar renders
Then the "Leads" menu item MUST have a 3px violet bar on the left
And the icon MUST be slightly scaled (scale-105)
And in dark mode the icon SHOULD have a subtle glow

### Testing Strategy

- Visual regression testing (screenshots before/after)
- Verify oklch support with @supports fallback to hex
- Test light/dark mode toggle on every view
- Verify no hardcoded blue (#3b82f6) remains in the codebase after migration
- Mobile responsive verification on all modified views

### Migration Notes

| Aspect | CRM VENTAS (current) | crmcodexy (target style) |
|--------|---------------------|-------------------------|
| Primary color | blue #3b82f6 | violet #8F3DFF |
| Color space | hex/rgb | oklch (with hex fallback) |
| Dark bg | ~#111827 (gray-900) | oklch(0.07 0.015 285) violet-tinted |
| Card bg | ~#1f2937 (gray-800) | oklch(0.10 0.02 285) |
| Badges | Filled colored badges | Dot + label with 10% bg |
| KPI cards | Simple cards | Glassmorphism with icon pill |
| Glow effects | None | violet glow on cards, buttons, sidebar |
| Scrollbars | Browser default | 6px custom, semi-transparent |
| Sidebar active | Background highlight | 3px left bar + icon glow |
| Border radius | Mixed | Consistent scale (sm→4xl) |
| Font | System defaults | Geist Sans + Inter |

### Files to Modify

**Critical (affects everything):**
- `frontend_react/src/index.css` — CSS custom properties
- `frontend_react/tailwind.config.ts` — color extensions, utilities

**Layout:**
- `frontend_react/src/components/Layout.tsx`
- Sidebar component
- Header/Topbar component

**Every view file** (20+ files) — badge patterns, card styling, button colors

### Acceptance Criteria

- [ ] Primary color is #8F3DFF everywhere (search for #3b82f6 returns 0 results)
- [ ] Dark mode uses violet-tinted backgrounds (not pure gray/black)
- [ ] All status badges use dot+label pattern
- [ ] KPI cards have icon pills and glassmorphism
- [ ] Sidebar has 3px active indicator and collapsed mode
- [ ] Custom scrollbars are 6px and semi-transparent
- [ ] Glow effects visible on primary buttons and cards in dark mode
- [ ] @supports fallback for browsers without oklch
- [ ] Light/dark toggle works on all views
- [ ] Mobile responsive maintained
- [ ] No visual regression on existing functionality
