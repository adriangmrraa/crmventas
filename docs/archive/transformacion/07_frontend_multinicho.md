# Diseño Frontend Multi-Nicho

Este documento define la reestructuración del Frontend (React) para soportar múltiples nichos operando bajo un mismo "Shell" agnóstico.

## 1. Arquitectura de Shell vs Módulos

### 1.1 Shell (Core)
Responsable de lo que es común a todos los tenants:
*   **Enrutamiento Principal**: `App.tsx` y `ProtectedRoutes`.
*   **Layout**: `Sidebar`, `Header` (TopBar), `MainContainer`.
*   **Autenticación**: Login, Recupero de clave, Logout.
*   **Configuración**: Settings de idioma, perfil de usuario.
*   **Chat UI**: La interfaz de chat es agnóstica; lo que cambia es la información lateral (Context Panel).

### 1.2 Módulos (Niche)
Paquetes de vistas y componentes que se cargan según la configuración:
*   **Dental**: Agenda, Pacientes, Tratamientos, Odontograma.
*   **CRM**: Leads, Plantillas, Campañas, Métricas de Venta.

## 2. Estructura de Directorios Propuesta

```text
src/
├── core/                   # SHELL
│   ├── layout/             # Sidebar, Header
│   ├── auth/               # Login, AuthContext
│   ├── api/                # Cliente HTTP base
│   └── components/         # UI Kit genérico
├── modules/                # MÓDULOS DE NICHO
│   ├── dental/
│   │   ├── routes.tsx      # Definición de rutas dentales
│   │   ├── views/          # AgendaView, PatientsView
│   │   └── components/     # Odontogram
│   └── crm_sales/
│       ├── routes.tsx      # Definición de rutas CRM
│       ├── views/          # LeadsView, CampaignsView
│       └── components/     # TemplateEditor
└── App.tsx                 # Router dinámico
```

## 3. Enrutamiento Dinámico

El `App.tsx` deberá leer el `niche_type` del usuario y cargar las rutas correspodientes.

```typescript
// src/App.tsx (Simplificado)
import { DentalRoutes } from './modules/dental/routes';
import { CrmRoutes } from './modules/crm_sales/routes';

const App = () => {
  const { user } = useAuth();
  
  if (!user) return <Login />;

  const nicheRoutes = user.tenant.niche_type === 'dental' 
    ? DentalRoutes 
    : CrmRoutes;

  return (
    <Routes>
       <Route path="/" element={<Layout />}>
          {/* Rutas Core */}
          <Route path="settings" element={<SettingsView />} />
          <Route path="chat" element={<ChatView />} />
          
          {/* Rutas de Nicho Inyectadas */}
          {nicheRoutes.map(route => (
            <Route key={route.path} path={route.path} element={route.element} />
          ))}
       </Route>
    </Routes>
  );
};
```

## 4. Configuración del Sidebar

El Sidebar no debe tener links hardcodeados. Debe leer una configuración.

**Configuración por Nicho (JSON)**:
```json
{
  "sidebar_items": [
    { "label": "Agenda", "path": "/agenda", "icon": "CalendarIcon" },
    { "label": "Pacientes", "path": "/patients", "icon": "UserIcon" }
  ]
}
```

El componente `Sidebar` itera sobre esta lista.
