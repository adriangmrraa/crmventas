---
name: "Nexus UI Developer"
description: "Especialista en React 18, TypeScript, Tailwind CSS y conexión con API multi-tenant."
trigger: "frontend, react, tsx, componentes, UI, vistas, hooks"
scope: "FRONTEND"
auto-invoke: true
---

# Nexus UI Developer - Dentalogic

# Nexus UI Developer - Dentalogic

## 1. Arquitectura Frontend
El frontend en `frontend_react/` es una SPA moderna basada en:
- **React 18** + TypeScript + Vite.
- **TailwindCSS** para el layout y **Vanilla CSS** para el diseño premium (Glassmorphism).
- **Lucide Icons** para la iconografía dental.
### 1. Gestión de Sesión (Nexus Security v7.6)
- **Zero LocalStorage**: El token JWT NO debe guardarse en `localStorage`. La sesión se maneja mediante una **Cookie HttpOnly** emitida por el backend.
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

## 3. Vistas Críticas (Business Logic)

### AgendaView.tsx
- La pieza central de Dentalogic.
- Muestra turnos desde la BD y bloqueos de Google Calendar.
- Permite agendar "Sobreturnos" forzados.

### DashboardView.tsx (Triage Center)
- Escucha eventos de Socket.IO (`HIGH_URGENCY_TRIAGE`, `CRITICAL_TRIAGE`).
- Muestra métricas de hoy: Turnos, Pendientes, Urgencias.
- Controla el estado global del Bot IA.

### ChatsView.tsx (Centro de Mensajería)
- **Re-ordenamiento en Tiempo Real**: Al recibir `NEW_MESSAGE`, la sesión correspondiente debe moverse al principio del array `sessions` tras actualizar su `last_message_time`.
- **Ventana de 24hs**: 
  - Mostrar banner de advertencia si `is_window_open` es false.
  - Deshabilitar input y botón de envío si la ventana está cerrada.
- **Jerarquía Rígida y Scroll Interno**:
  - Utilizar `min-h-0` en contenedores `flex-1` para forzar el scroll únicamente en la sección de mensajes.
  - El header del chat y el área de input deben permanecer fuera del área de scroll.
- **Carga Incremental**: Implementar `limit` y `offset` para el fetching cronológico inverso de mensajes.
- **Sincronización de Estado**: Escuchar `HUMAN_OVERRIDE_CHANGED` para actualizar la cabecera del chat sin refrescar.

### Credentials.tsx (The Vault UI)
- Gestión de `GOOGLE_CREDENTIALS` y `YCLOUD_API_KEY`.
- Muestra la URL dinámica para el Webhook de YCloud con opción de copiado.

### AuditLogsView.tsx (Nexus v7.7)
- Solo visible para usuarios con rol `ceo`.
- Consume `GET /admin/core/audit/logs`.
- Permite filtrar eventos por severidad y tipo para trazabilidad de seguridad.

## 4. Estilos y UX (Premium Dental)
- **Glassmorphism**: Usar clase `.glass` para tarjetas e inputs.
- **Micro-animaciones**: Usar `animate-pulse` para estados de triaje crítico.
- **Espaciado**: Márgenes laterales (`px-4` o `px-6`) para que el contenido no pegue al borde. Se recomienda aplicar el padding a nivel de vista maestra, no en el Layout global.
- **Aislamiento de Scroll**: Evitar el scroll global de la página (`body`). Usar `h-screen overflow-hidden` en el root Layout y habilitar `overflow-y-auto` + `min-h-0` solo en los paneles de contenido.
- **Interacción**: Estados `:hover` solo en desktop. `:active` para feedback táctil en mobile.
- **Responsive**: Mobile-first para que los odontólogos puedan ver su agenda desde el celular.

## 5. Producción y Dockerización
**CRÍTICO**: El frontend inyecta variables `VITE_` durante el **BUILD TIME**.
- **Regla**: El `Dockerfile` debe usar `ARG` y `ENV` para capturar `VITE_ADMIN_TOKEN` y `VITE_API_URL` durante el comando `npm run build`.
- **Verificación**: Si el frontend da 401 en producción, lo primero es verificar que las variables están presentes en el panel de EasyPanel ANTES del build.

## 7. Checklist de UI
- [ ] ¿El componente maneja `isLoading` con un spinner o esqueleto?
- [ ] ¿Los errores se muestran vía Toasts o alertas `check-fail`? (Manejar específicamente el error **429 Rate Limit** con mensaje de "esperar 60s").
- [ ] ¿Se usa `Lucide` para coherencia visual?
- [ ] ¿La tabla/lista tiene `key` único (IDs de la BD)?
