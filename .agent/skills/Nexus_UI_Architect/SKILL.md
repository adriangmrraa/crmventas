---
name: "Nexus UI Architect"
description: "Especialista en Diseno Responsivo (Mobile First / Desktop Adaptive) y UX para CRM Ventas."
trigger: "ui, diseño, responsive, mobile, desktop, layout, tailwind, componente, vista, pantalla"
scope: "FRONTEND"
auto-invoke: false
---

# Nexus UI Architect

## Mision
Garantizar que cada vista de **CRM Ventas (Nexus Core)** funcione perfectamente tanto en dispositivos moviles (iPhone SE/14 Pro) como en monitores Desktop (1080p/4k), manteniendo la estetica "Premium Deep Tech" de Nexus.

## Herramientas y Stack
- **Framework**: React 18 + Vite.
- **Styling**: Tailwind CSS (Strict Utility-First).
- **Iconografia**: `lucide-react`.
- **Animaciones**: CSS Nativo (`animate-pulse`, `animate-fade-in`).

## Estrategia de Diseno Responsivo

### 1. Mobile First (Base)
Disenamos pensando en pantallas verticales estrechas.
- **Container**: `w-full px-4`.
- **Tipografia**: Textos legibles (min 14px), H1 grandes pero ajustados.
- **Touch Targets**: Botones de minimo 44x44px.
- **Navegacion**: Menu hamburguesa o Bottom Bar para mobile. Sidebar colapsable.

### 2. Puntos de Quiebre (Breakpoints)
- **`md:` (768px)**: Tablets. Pasar de 1 col a 2 cols.
- **`lg:` (1024px)**: Laptops. Mostrar Sidebar fija. Main Layout 3-5 cols.
- **`xl:` (1280px)**: Desktop. Layout espacioso.

### 3. Patrones Comunes de Adaptacion

#### Grillas
```tsx
// Mobile: 1 columna | Desktop: 4 columnas
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
```

#### Elementos Ocultos
```tsx
// Solo visible en mobile
<div className="block lg:hidden">...</div>

// Solo visible en desktop
<div className="hidden lg:block">...</div>
```

#### Modales y Drawers
- **Mobile**: Full screen o Bottom Sheet.
- **Desktop**: Dialog centrado con backdrop blur.

## Checklist de Auditoria UI (Por Pagina)

1. **Overflow Horizontal**: Verificar que nada rompa el ancho de la pantalla en mobile. (`overflow-x-hidden` en root).
2. **Alturas Fijas**: Evitar `h-screen` en mobile por las barras del navegador. Usar `dvh` o `min-h`.
3. **Legibilidad**: Contraste suficiente en textos sobre fondos oscuros/glass.
4. **Espaciado**: Margenes laterales (`px-4` o `px-6`) para que el contenido no pegue al borde. Se recomienda aplicar el padding a nivel de vista maestra, no en el Layout global.
5. **Aislamiento de Scroll**: Evitar el scroll global de la pagina (`body`). Usar `h-screen overflow-hidden` en el root Layout y habilitar `overflow-y-auto` + `min-h-0` solo en los paneles de contenido.
6. **Interaccion**: Estados `:hover` solo en desktop. `:active` para feedback tactil en mobile.
7. **Patron Agenda CRM**:
    - **Desktop**: Vista de calendario completa con columnas por vendedor (seller). Uso de `resource-timegrid` para visualizar reuniones y citas de leads asignados a cada seller.
    - **Mobile**: Cambio obligatorio a `MobileAgenda` (Vertical Stack) + `DateStrip` (Horizontal Navigation). Lista de citas del dia con tarjetas compactas.
    - **Sincronizacion**: Utilizar `calendarApi.refetchEvents()` en eventos WebSocket (Socket.IO) para garantizar consistencia absoluta en entornos multi-usuario y multi-tenant.
8. **Patron Pipeline/Kanban**:
    - **Desktop**: Columnas horizontales (por etapa del pipeline).
    - **Mobile**: Vista de lista vertical agrupada por etapa, con drag-and-drop desactivado.

## Snippets de Oro (Nexus Design System)

### Glass Card (Universal)
```tsx
<div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-xl">
  ...
</div>
```

### Boton de Accion Principal (Responsive)
```tsx
<button className="w-full lg:w-auto bg-accent hover:bg-accent-hover text-white px-6 py-3 rounded-xl font-bold transition-all active:scale-95 shadow-lg shadow-accent/20">
  Accion
</button>
```

### Contenedor de Pagina Estandar
```tsx
<div className="min-h-screen bg-gray-900 text-white p-4 lg:p-8 overflow-x-hidden">
  <div className="max-w-7xl mx-auto">
     {/* Contenido */}
  </div>
</div>
```

## Protocolo de Correccion
1. **Analizar**: Abrir la vista y simular viewport mobile (375px).
2. **Identificar Roturas**: Textos cortados, scroll horizontal indeseado, botones inalcanzables.
3. **Aplicar Clases Utilitarias**: Usar `className` de Tailwind para corregir (`flex-col` en mobile, `flex-row` en desktop).
4. **Verificar**: Probar en Desktop para asegurar que no se rompio la experiencia grande.
