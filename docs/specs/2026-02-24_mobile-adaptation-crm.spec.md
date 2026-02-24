# Spec: Mobile Adaptation (Nexus Standard) - CRM Leads & Prospección

## 1. Objetivo
Transformar la experiencia de escritorio de las vistas de Leads y Prospección en una interfaz "Mobile Premium", utilizando el patrón de tarjetas para listas/tablas y asegurando la usabilidad de los modales en pantallas pequeñas.

## 2. Requerimientos UI/UX

### 2.1. ProspectingView.tsx (Mobile Adapt)
- **Tabla -> Tarjetas**: En resoluciones `< 1024px` (pre-lg), la tabla desaparece y se muestra una lista vertical de tarjetas.
- **Card Layout**:
    - **Header**: Nombre del negocio (`apify_title`) + Rating (Icono estrella).
    - **Body**: Categoría, Ubicación (Ciudad), Link a Website (icono globo).
    - **Footer**: Estado de envío (`outreach_message_sent`) con badge de color + Botón de acción rápida.
- **Filtros**: El panel superior (Search, Select, Scrape Button) debe apilarse verticalmente en mobile.

### 2.2. LeadsView.tsx (Mobile Adapt)
- **Items de Lista**: Ajustar el `padding` y el tamaño de las fuentes para mobile.
- **Acciones**: Los botones de acción (Convertir, Chat) deben tener targets táctiles de al menos `44px`.
- **Tabs**: Asegurar que el contenedor de pestañas sea scrolleable horizontalmente si las etiquetas son largas.

### 2.3. Modals (Universal Adapt)
- **Aislamiento de Scroll**: El modal debe ser `max-h-[95vh]` con `overflow-y-auto` interno.
- **Botones de Acción**: En mobile, los botones de guardar/cancelar deben ocupar el 100% del ancho (flex-col).
- **Layout de Prospecting Modal**: La vista de 2 columnas en desktop debe pasar a 1 columna en mobile.

## 3. Requerimientos Técnicos

- **Tailwind Strategy**: Usar `hidden lg:block` y `block lg:hidden` para alternar entre Tabla y Tarjetas donde la estructura sea muy diferente.
- **Scroll Isolation**: Aplicar `flex flex-col h-full overflow-hidden` en los contenedores raíz para evitar el scroll del body.
- **Touch Utility**: Utilizar clases `active:bg-gray-100` para feedback táctil en cards.

## 4. Criterios de Aceptación (Verificación)
- [ ] La tabla de Prospección no es visible en 375px; en su lugar hay tarjetas legibles.
- [ ] El modal de detalle de lead no se corta en la parte inferior en mobile.
- [ ] El input de búsqueda es fácil de usar en mobile.
- [ ] Se mantiene el filtrado dinámico por `tenant_id` y otros parámetros existentes.
