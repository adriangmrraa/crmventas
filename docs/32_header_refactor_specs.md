# 🎨 Header Refactor Specifications v1.0
**Fecha**: 28/03/2026 | **Status**: SPECS LISTA PARA IMPLEMENTACIÓN  
**Target**: ClinicForge React Frontend (v7.6+)

---

## 📋 TABLA DE CONTENIDOS
1. [Arquitectura General](#arquitectura-general)
2. [Componentes Detallados](#componentes-detallados)
3. [Especificaciones de UI/UX](#especificaciones-de-uiux)
4. [Animaciones & Micro-interacciones](#animaciones--micro-interacciones)
5. [i18n Keys](#i18n-keys)
6. [Testing Checklist](#testing-checklist)

---

## 🏗️ ARQUITECTURA GENERAL

### Estructura de Carpetas
```
src/components/
├── Header/
│   ├── GlobalTopBar.tsx
│   ├── TenantSwitcher.tsx
│   ├── CommandBar.tsx
│   ├── StatusAlertsCluster.tsx
│   ├── ContextualSubheader.tsx
│   ├── BreadcrumbNav.tsx
│   ├── FilterPopover.tsx
│   ├── AnimationDefinitions.ts
│   └── types.ts
├── Notifications/
│   └── PulsingBell.tsx (REFACTOR)
└── Skeleton/
    └── ShimmerLoader.tsx (NEW)
```

### Jerarquía de Z-Index
```
z-40  → GlobalTopBar (fijo debajo de modales)
z-30  → ContextualSubheader (sticky debajo de topbar)
z-20  → Modales/Drawer
z-10  → Popovers/Tooltips
z-0   → Contenido principal
```

### Layout en Layout.tsx
```tsx
<Layout>
  <GlobalTopBar>
    ├─ TenantSwitcher
    ├─ CommandBar
    └─ StatusAlertsCluster
  
  <ContextualSubheader>
    ├─ BreadcrumbNav
    ├─ FilterPopover
    └─ PrimaryActionButton
  
  <main className="flex-1 overflow-hidden">
    {children}
  </main>
</Layout>
```

---

## 🎯 COMPONENTES DETALLADOS

### 1. GlobalTopBar.tsx

**Responsabilidad**: Barra superior fija (64px) con tenant selector, búsqueda y status.

```tsx
interface GlobalTopBarProps {
  currentTenant?: { id: number; clinic_name: string; logo_url?: string };
  tenants?: Array<{ id: number; clinic_name: string; logo_url?: string }>;
  onTenantChange?: (tenantId: number) => void;
  isLoading?: boolean;
}

export const GlobalTopBar: React.FC<GlobalTopBarProps> = ({
  currentTenant,
  tenants = [],
  onTenantChange,
  isLoading = false,
}) => { ... }
```

**Renders**:
- Left: Logo ClinicForge (16px icon) + TenantSwitcher
- Center: CommandBar (flexible width)
- Right: StatusAlertsCluster
- Height: h-16 (64px)
- BG: `bg-black/60 backdrop-blur-md border-b border-white/5`
- Z-Index: `z-40`
- Position: `fixed top-0 left-0 right-0`
- Responsive: En móvil, CommandBar se reduce a icono

**CSS**:
```css
/* Glass effect */
background: rgba(0, 0, 0, 0.6);
backdrop-filter: blur(12px);
border-bottom: 1px solid rgba(255, 255, 255, 0.05);

/* Container flex */
display: flex;
align-items: center;
justify-content: space-between;
padding: 0 1.5rem;
gap: 2rem;
```

---

### 2. TenantSwitcher.tsx

**Responsabilidad**: Dropdown con clínicas disponibles.

```tsx
interface TenantSwitcherProps {
  currentTenant?: { id: number; clinic_name: string; logo_url?: string };
  tenants?: Array<{ id: number; clinic_name: string; logo_url?: string }>;
  onTenantChange?: (tenantId: number) => void;
  disabled?: boolean;
}
```

**Renders**:
- Button con logo/avatar + nombre + flecha
- Dropdown menu (popover)
- Animación scale-in + fade-in en apertura
- Solo visible si `user.role === 'ceo'` O múltiples tenants

**Comportamiento**:
- Avatar: Logo de clínica O iniciales en círculo (bg-medical-500)
- Nombre: Truncado con ellipsis si es largo
- Ícono: Chevron rotado 180° cuando abierto
- Animación del dropdown: `scale-in from-origin cubic-bezier(0.4, 0, 0.2, 1)`

**Mobile**:
- En sm: Solo mostrar avatar sin nombre
- Flecha siempre visible

**CSS**:
```css
/* Button */
.tenant-button {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 1rem;
  border-radius: 0.75rem;
  background: white/5;
  border: 1px solid white/10;
  cursor: pointer;
  transition: all 200ms cubic-bezier(0.4, 0, 0.2, 1);
}

.tenant-button:hover {
  background: white/10;
  border-color: white/20;
}

.tenant-button:active {
  transform: scale(0.96);
}

/* Avatar */
.tenant-avatar {
  width: 2rem;
  height: 2rem;
  border-radius: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 0.875rem;
  background: linear-gradient(135deg, #0066cc, #004d99);
  color: white;
}

/* Dropdown */
.tenant-dropdown {
  position: absolute;
  top: calc(100% + 0.5rem);
  left: 0;
  background: #0a0a12;
  border: 1px solid white/10;
  border-radius: 0.75rem;
  min-width: 250px;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
  animation: scaleIn 200ms cubic-bezier(0.4, 0, 0.2, 1);
}

.tenant-item {
  padding: 0.75rem 1rem;
  cursor: pointer;
  transition: background 150ms;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.tenant-item:hover {
  background: white/5;
}

.tenant-item.active {
  background: white/10;
  border-left: 3px solid #0066cc;
  padding-left: calc(1rem - 3px);
}
```

---

### 3. CommandBar.tsx

**Responsabilidad**: Búsqueda omnipresente central (Cmd+K).

```tsx
interface CommandBarProps {
  placeholder?: string;
  onSearch?: (query: string) => void;
  onCommandKey?: () => void;
  isLoading?: boolean;
}
```

**Renders**:
- Input con icono de búsqueda (left)
- Texto "Cmd+K" (right, dimmed)
- Buscador fantasmal (low opacity)
- "Buscar paciente, turno o DNI..."

**Comportamiento**:
- Detecta Cmd+K (macOS) y Ctrl+K (Windows/Linux)
- Focus automático al presionar
- Debounce: 300ms antes de hacer búsqueda
- Mobile: Collapsa a icono de lupa con modal overlay

**Integración**:
- Llama a `onSearch(query)` con debounce
- Opcional: Devuelve array de resultados (pacientes, turnos)

**CSS**:
```css
.command-bar {
  flex: 1;
  max-width: 500px;
  position: relative;
  margin: 0 auto;
}

.command-input {
  width: 100%;
  padding: 0.5rem 1rem 0.5rem 2.5rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.75rem;
  color: white;
  font-size: 0.875rem;
  transition: all 200ms;
}

.command-input:focus {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(0, 102, 204, 0.5);
  outline: none;
}

.command-input::placeholder {
  color: rgba(255, 255, 255, 0.3);
}

.command-icon {
  position: absolute;
  left: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  color: rgba(255, 255, 255, 0.4);
  pointer-events: none;
}

.command-shortcut {
  position: absolute;
  right: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.2);
  pointer-events: none;
}
```

---

### 4. StatusAlertsCluster.tsx

**Responsabilidad**: Help icon + Notification bell + Status indicators.

```tsx
interface StatusAlertsClusterProps {
  hasNewGuide?: boolean;
  notificationCount?: number;
  onHelpClick?: () => void;
  onNotificationClick?: () => void;
  isOnline?: boolean;
  connectionStatus?: 'online' | 'offline' | 'unstable';
}
```

**Renders**:
- Help icon (?) → Tooltip con pulse sutil
- Notification bell (🔔) → Badge rojo con ping animation
- Status dot (opcional) → Verde=online, Rojo=offline
- Tooltip: "Pulsa ? para ayuda" (aparece en hover)

**Animaciones**:
- Help: Pulse suave infinito `opacity: 1 → 0.6 → 1` (2s loop)
- Bell badge: Ping scale `scale: 1 → 1.25 → 1` + opacity fade (1.5s loop)
- Status dot: Pulse constante si hay notificaciones

**CSS**:
```css
.status-cluster {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.status-icon {
  width: 2.5rem;
  height: 2.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.75rem;
  background: white/5;
  border: 1px solid white/10;
  cursor: pointer;
  transition: all 200ms cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
}

.status-icon:hover {
  background: white/10;
  border-color: white/20;
}

.status-icon:active {
  transform: scale(0.96);
}

/* Notification badge */
.notification-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  width: 20px;
  height: 20px;
  background: #dc3545;
  border: 2px solid #0a0a12;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.625rem;
  font-weight: 700;
  color: white;
  animation: ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite;
}

/* Pulse animation for help icon */
@keyframes pulseSoft {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.help-icon-pulsing {
  animation: pulseSoft 2s ease-in-out infinite;
}

/* Ping animation for bell */
@keyframes ping {
  75%, 100% {
    transform: scale(2);
    opacity: 0;
  }
}
```

---

### 5. ContextualSubheader.tsx

**Responsabilidad**: Breadcrumbs + Filtros consolidados + Acción primaria.

```tsx
interface ContextualSubheaderProps {
  breadcrumbs?: Array<{ label: string; path?: string }>;
  filterActive?: boolean;
  filterCount?: number;
  onFilterClick?: () => void;
  primaryAction?: {
    label: string;
    icon?: ReactNode;
    onClick: () => void;
  };
}
```

**Renders**:
- BreadcrumbNav (left)
- FilterPopover trigger button (center, conditional)
- Primary action button (right)
- Height: h-12 (48px)
- BG: `bg-white/[0.02] border-b border-white/5`
- Position: `sticky top-16 z-30`

**Comportamiento**:
- Si no hay breadcrumbs/filtros, el subheader se oculta
- Filtro button muestra contador cuando activos
- Acción primaria: Gradiente sutil + elevación en hover

**CSS**:
```css
.contextual-subheader {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1.5rem;
  height: 3rem;
  background: rgba(255, 255, 255, 0.02);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  gap: 1rem;
}

/* Primary action button */
.primary-action-btn {
  padding: 0.5rem 1rem;
  background: linear-gradient(135deg, #0066cc, #0052a3);
  border: 1px solid rgba(0, 102, 204, 0.3);
  border-radius: 0.75rem;
  color: white;
  font-weight: 500;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 200ms cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  gap: 0.5rem;
  box-shadow: 0 4px 6px rgba(0, 102, 204, 0.1);
}

.primary-action-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 12px rgba(0, 102, 204, 0.2);
  background: linear-gradient(135deg, #0073e6, #005cbb);
}

.primary-action-btn:active {
  transform: scale(0.96) translateY(-1px);
}
```

---

### 6. BreadcrumbNav.tsx

**Responsabilidad**: Ruta de navegación inteligente.

```tsx
interface BreadcrumbNavProps {
  crumbs?: Array<{ label: string; path?: string }>;
}
```

**Renders**:
- Home icon → "/" link
- Chevron separators
- Links navegables
- Último item (actual) en texto (no clickeable)

**Ejemplo**:
```
🏠 / Agenda / Editar Turno #123
```

---

### 7. FilterPopover.tsx

**Responsabilidad**: UI consolidada de filtros (collapsa chips).

```tsx
interface FilterPopoverProps {
  filters?: Record<string, any>;
  onFiltersChange?: (filters: Record<string, any>) => void;
  filterOptions?: Array<{ id: string; label: string; values: any[] }>;
  activeFilterCount?: number;
}
```

**Renders**:
- Trigger button: "Filtros" (cambia color si hay activos)
- Popover con checkboxes/selects
- Clear filters button
- Animación: Scale-in + fade-in

---

### 8. AnimationDefinitions.ts

**Responsabilidad**: Centralizar curvas y transiciones.

```ts
export const animationConfig = {
  // Curvas Bézier estándar
  cubic: {
    standard: 'cubic-bezier(0.4, 0, 0.2, 1)',  // Material Design standard
    enter: 'cubic-bezier(0, 0, 0.2, 1)',       // Accelerating entrance
    exit: 'cubic-bezier(0.4, 0, 1, 1)',        // Decelerating exit
  },
  
  // Duraciones
  duration: {
    immediate: 100,      // Instant feedback
    fast: 150,          // Micro interactions
    normal: 200,        // Standard transition
    slow: 300,          // Complex animations
  },
  
  // Keyframes
  keyframes: {
    scaleIn: '@keyframes scaleIn { from { transform: scale(0.95); opacity: 0; } to { transform: scale(1); opacity: 1; } }',
    fadeIn: '@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }',
    slideIn: '@keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }',
    pulse: '@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }',
    ping: '@keyframes ping { 75%, 100% { transform: scale(2); opacity: 0; } }',
  },
};

export const getTransitionClass = (property: string, duration: 'immediate' | 'fast' | 'normal' | 'slow' = 'normal') => {
  return `transition-${property} duration-${duration === 'immediate' ? '100' : duration === 'fast' ? '150' : duration === 'normal' ? '200' : '300'}`;
};
```

---

## 🎬 ESPECIFICACIONES DE UI/UX

### Colores & Contrastes (Dark Mode)
```
Background primario:  #06060e    (casi negro)
Background vidrio:    rgba(0, 0, 0, 0.6)
Border primario:      rgba(255, 255, 255, 0.05)
Border hover:         rgba(255, 255, 255, 0.1)
Text primario:        #ffffff (100%)
Text secundario:      rgba(255, 255, 255, 0.7)
Text terciario:       rgba(255, 255, 255, 0.4)
Accent primario:      #0066cc
Accent hover:         #0073e6
Success:              #28a745
Warning:              #ffc107
Danger:               #dc3545
```

### Tipografía
```
Body:       Inter, 0.875rem (14px), weight 400
Label:      Inter, 0.75rem (12px), weight 500
Button:     Inter, 0.875rem (14px), weight 500
Heading:    Outfit, 1rem (16px), weight 600
```

### Espaciado
```
xs:  0.25rem (4px)
sm:  0.5rem  (8px)
md:  1rem    (16px)
lg:  1.5rem  (24px)
xl:  2rem    (32px)
```

### Border Radius
```
tight:   0.375rem (6px)    - Inputs, badges
normal:  0.75rem (12px)    - Buttons, cards
rounded: 1rem (16px)       - Modales, popovers
full:    9999px           - Avatars, badges
```

---

## 💫 ANIMACIONES & MICRO-INTERACCIONES

### Estados de Botón
```
Idle:    scale(1.0)
Hover:   scale(1.02) + shadow elevation
Active:  scale(0.96) instant → scale(1.0) bounce
Focus:   border accent + shadow glow
```

### Entrada de Componentes
```
Duration:   200ms
Curve:      cubic-bezier(0.4, 0, 0.2, 1)
Transform:  scale(0.95) → scale(1.0)
Opacity:    0 → 1
```

### Notificaciones & Badges
```
Bell badge ping:     1.5s infinite, scale(1→1.25→1) + fade
Help icon pulse:     2s infinite, opacity(1→0.5→1)
Filter badge:        Scale-in 200ms on change
```

### Loading States (Shimmer)
```
Background:  Linear gradient moving left-to-right
Speed:       1.5s per cycle
Colors:      white/[0.02] → white/[0.08] → white/[0.02]
Border-radius: Match content (4px, 12px, etc.)
```

---

## 🌐 i18n KEYS

**Archivo**: `src/locales/{es,en,fr}.json`

```json
{
  "header": {
    "tenant_switcher": "Sígueme de Seleccionar",
    "tenant_selector": "Selector de Clínica",
    "search_placeholder": "Buscar paciente, turno o DNI...",
    "search_shortcut": "Cmd+K",
    "filters": "Filtros",
    "filters_active": "Filtros activos",
    "filters_clear": "Limpiar filtros",
    "help": "Ayuda",
    "help_tooltip": "Pulsa ? para abrir guía",
    "online": "En línea",
    "offline": "Sin conexión",
    "status_online": "En línea",
    "status_unstable": "Conexión inestable"
  },
  "breadcrumb": {
    "home": "Inicio",
    "dashboard": "Dashboard",
    "agenda": "Agenda",
    "edit_appointment": "Editar Turno",
    "patients": "Pacientes",
    "leads": "Leads",
    "pipeline": "Pipeline",
    "chats": "Chats",
    "settings": "Configuración"
  },
  "actions": {
    "new_appointment": "+ Nuevo Turno",
    "new_patient": "+ Nuevo Paciente",
    "new_lead": "+ Nuevo Lead",
    "save": "Guardar",
    "cancel": "Cancelar"
  }
}
```

**EN (English)**:
```json
{
  "header": {
    "tenant_selector": "Clinic Selector",
    "search_placeholder": "Search patient, appointment or ID...",
    "search_shortcut": "Cmd+K",
    "filters": "Filters",
    "help": "Help",
    "online": "Online",
    "offline": "Offline"
  }
}
```

**FR (Français)**:
```json
{
  "header": {
    "tenant_selector": "Sélecteur de Clinique",
    "search_placeholder": "Rechercher patient, rendez-vous ou ID...",
    "search_shortcut": "Cmd+K",
    "filters": "Filtres",
    "help": "Aide",
    "online": "En ligne",
    "offline": "Hors ligne"
  }
}
```

---

## ✅ TESTING CHECKLIST

### Unit Tests
- [ ] TenantSwitcher renderiza lista correcta
- [ ] CommandBar detecta Cmd+K / Ctrl+K
- [ ] Filtros se aplican correctamente
- [ ] Breadcrumbs reflejan ruta actual
- [ ] StatusAlertsCluster muestra badge si hay notificaciones

### Integration Tests
- [ ] GlobalTopBar se integra con AuthContext
- [ ] ContextualSubheader aparece/desaparece según breadcrumbs
- [ ] Cambio de tenant recarga datos
- [ ] Búsqueda debouncea correctamente

### E2E Tests
- [ ] Header visible en todas las vistas
- [ ] Responsive en mobile/tablet/desktop
- [ ] Animaciones fluidas (no jank)
- [ ] Keyboard shortcuts funcionan (Cmd+K)

### Accessibility
- [ ] Todos los botones tienen `aria-label`
- [ ] Tooltips accesibles con `aria-describedby`
- [ ] Z-index manejo de focus (modales)
- [ ] Color contrast ≥ 4.5:1 (WCAG AA)

### Performance
- [ ] No re-renders innecesarios en Layout
- [ ] Debounce en búsqueda (300ms max)
- [ ] Animaciones no bloquean el main thread (GPU accelerated)

---

## 📦 DEPENDENCIES

**Necesarias**:
- `react-router-dom` (ya presente)
- `lucide-react` (ya presente)
- `framer-motion` (para animaciones, si no está instalado)

**Opcional**:
- `react-use-measure` (para popovers dinámicos)
- `use-keyboard-event` (para Cmd+K listener)

---

## 🚀 PRIORIDAD DE IMPLEMENTACIÓN

### Fase 1 (CRÍTICA)
- [x] Specs documento
- [ ] GlobalTopBar.tsx
- [ ] TenantSwitcher.tsx
- [ ] Layout.tsx integration

### Fase 2 (ALTA)
- [ ] CommandBar.tsx
- [ ] StatusAlertsCluster.tsx
- [ ] i18n keys update

### Fase 3 (MEDIA)
- [ ] ContextualSubheader.tsx
- [ ] BreadcrumbNav.tsx
- [ ] FilterPopover.tsx

### Fase 4 (PULIDO)
- [ ] Animaciones avanzadas
- [ ] ShimmerLoader.tsx
- [ ] Testing & QA

---

**Documento Generado**: 28/03/2026 | **Versión**: 1.0-FINAL
