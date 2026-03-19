---
name: "Nexus UI Developer"
description: "Especialista en React 18, TypeScript, Tailwind CSS y conexión con API multi-tenant para CRM de Ventas."
trigger: "frontend, react, tsx, componentes, UI, vistas, hooks, dashboard, leads, sellers"
scope: "FRONTEND"
auto-invoke: true
---

# Nexus UI Developer - CRM Ventas (Nexus Core)

## 1. Arquitectura Frontend
El frontend en `frontend_react/` es una SPA moderna basada en:
- **React 18** + TypeScript + Vite.
- **TailwindCSS** para el layout y **Vanilla CSS** para el diseño premium (Glassmorphism).
- **Lucide Icons** para la iconografía del CRM.
- **i18n**: Internacionalización con `useTranslation()` y archivos `es.json`, `en.json`, `fr.json`.

### Gestión de Sesión (Nexus Security v7.6)
- **Zero LocalStorage para JWT**: El token JWT NO debe guardarse en `localStorage`. La sesión se maneja mediante una **Cookie HttpOnly** emitida por el backend.
- **Axios Configuration**: Es MANDATORIO el uso de `withCredentials: true` en todas las peticiones para que el navegador incluya automáticamente la cookie HttpOnly.
- **Persistencia de Sesión**: Al cargar la app, el `AuthContext` debe llamar a `GET /auth/me`. Si el backend responde 200, el usuario está activo (la cookie es válida).
- **Logout**: Se debe llamar al endpoint `POST /auth/logout` para que el servidor limpie la cookie del lado del cliente.

### Cliente Axios (`src/api/axios.ts`):
```typescript
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  headers: {
    'X-Admin-Token': localStorage.getItem('admin_token')
  }
});
```

## 2. Vistas Críticas (Business Logic)

### CrmDashboardView.tsx (Centro de Mando)
- Panel principal con KPIs de ventas: leads nuevos, conversiones, oportunidades activas, ingresos del periodo.
- Escucha eventos de Socket.IO (`NEW_LEAD`, `LEAD_UPDATED`, `NOTIFICATION_CREATED`).
- Gráficos de rendimiento por seller y pipeline de oportunidades.
- Controla el estado global del Bot IA (activo/inactivo).

### LeadsView.tsx (Gestión de Prospectos)
- Listado de leads con filtros por estado, temperatura (hot/warm/cold), source y seller asignado.
- Acciones rápidas: asignar seller, cambiar estado, agendar seguimiento.
- Indicadores visuales de temperatura y tiempo sin contacto.
- Búsqueda por nombre, teléfono o email.

### LeadDetailView.tsx (Ficha del Lead)
- Vista completa del lead: datos de contacto, historial de interacciones, conversaciones WhatsApp.
- Timeline de actividad (cambios de estado, asignaciones, notas).
- Formulario de edición de datos y metadata del lead.
- Acciones: convertir a cliente, crear oportunidad, agendar reunión.

### SellersView.tsx (Equipo Comercial)
- Listado de vendedores con métricas de rendimiento (`seller_metrics`).
- Configuración de `working_hours` y capacidad máxima de leads.
- Visualización de carga de trabajo actual vs. capacidad.

### ClientsView.tsx (Cartera de Clientes)
- Leads convertidos exitosamente. Historial de compras/transacciones.
- Vinculación con `sales_transactions` y `opportunities` cerradas.

### CrmAgendaView.tsx (Agenda Comercial)
- Muestra eventos de sellers desde la BD y bloqueos de Google Calendar.
- Permite agendar reuniones, demos y llamadas de seguimiento.
- Vista por día/semana con filtro por seller.

### ProspectingView.tsx (Prospección Automatizada)
- Integración con Apify para captura automática de leads.
- Configuración de fuentes de prospección y reglas de importación.
- Preview y aprobación de leads antes de ingresarlos al pipeline.

### ChatsView.tsx (Centro de Mensajería WhatsApp)
- **Re-ordenamiento en Tiempo Real**: Al recibir `NEW_MESSAGE`, la sesión correspondiente debe moverse al principio del array `sessions` tras actualizar su `last_message_time`.
- **Ventana de 24hs**:
  - Mostrar banner de advertencia si `is_window_open` es false.
  - Deshabilitar input y botón de envío si la ventana está cerrada.
- **Jerarquía Rígida y Scroll Interno**:
  - Utilizar `min-h-0` en contenedores `flex-1` para forzar el scroll únicamente en la sección de mensajes.
  - El header del chat y el área de input deben permanecer fuera del área de scroll.
- **Carga Incremental**: Implementar `limit` y `offset` para el fetching cronológico inverso de mensajes.
- **Sincronización de Estado**: Escuchar `HUMAN_OVERRIDE_CHANGED` para actualizar la cabecera del chat sin refrescar.

### MarketingHubView.tsx (Centro de Marketing)
- Dashboard unificado de campañas Meta Ads y Google Ads.
- Métricas de ROI por campaña: costo por lead, tasa de conversión, gasto total.

### MetaLeadsView.tsx (Leads de Meta)
- Leads capturados desde formularios de Facebook/Instagram Ads.
- Mapeo automático a la tabla `leads` con source `meta_ads`.
- Visualización de qué campaña/anuncio generó cada lead.

### Credentials.tsx (The Vault UI)
- Gestión de `GOOGLE_CREDENTIALS`, `YCLOUD_API_KEY`, `META_ACCESS_TOKEN`.
- Muestra la URL dinámica para el Webhook de YCloud con opción de copiado.

### AuditLogsView.tsx (Nexus v7.7)
- Solo visible para usuarios con rol `ceo`.
- Consume `GET /admin/core/audit/logs`.
- Permite filtrar eventos por severidad y tipo para trazabilidad de seguridad.

## 3. Estilos y UX (Premium CRM)
- **Glassmorphism**: Usar clase `.glass` para tarjetas e inputs.
- **Micro-animaciones**: Usar `animate-pulse` para notificaciones nuevas y leads hot recién ingresados.
- **Espaciado**: Márgenes laterales (`px-4` o `px-6`) para que el contenido no pegue al borde. Se recomienda aplicar el padding a nivel de vista maestra, no en el Layout global.
- **Aislamiento de Scroll**: Evitar el scroll global de la página (`body`). Usar `h-screen overflow-hidden` en el root Layout y habilitar `overflow-y-auto` + `min-h-0` solo en los paneles de contenido.
- **Interacción**: Estados `:hover` solo en desktop. `:active` para feedback táctil en mobile.
- **Responsive**: Mobile-first para que los vendedores puedan gestionar leads desde el celular.
- **Colores de Estado**: Convención de colores consistente para temperatura de leads (rojo=hot, naranja=warm, azul=cold) y estados del pipeline.

## 4. Producción y Dockerización
**CRÍTICO**: El frontend inyecta variables `VITE_` durante el **BUILD TIME**.
- **Regla**: El `Dockerfile` debe usar `ARG` y `ENV` para capturar `VITE_ADMIN_TOKEN` y `VITE_API_URL` durante el comando `npm run build`.
- **Verificación**: Si el frontend da 401 en producción, lo primero es verificar que las variables están presentes en el panel de EasyPanel ANTES del build.

## 5. Checklist de UI
- [ ] ¿El componente maneja `isLoading` con un spinner o esqueleto?
- [ ] ¿Los errores se muestran vía Toasts o alertas `check-fail`? (Manejar específicamente el error **429 Rate Limit** con mensaje de "esperar 60s").
- [ ] ¿Se usa `Lucide` para coherencia visual?
- [ ] ¿La tabla/lista tiene `key` único (IDs de la BD)?
- [ ] ¿Los textos visibles usan `useTranslation()` con claves de i18n (`es.json`, `en.json`, `fr.json`)?
- [ ] ¿Los datos se filtran correctamente por `tenant_id` desde el backend?
- [ ] ¿Los eventos de Socket.IO actualizan la UI sin necesidad de refresh manual?

---
*Nexus v8.0 - Nexus UI Developer Protocol - CRM Ventas*
