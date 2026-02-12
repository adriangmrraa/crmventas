# Propuesta de Núcleo Agnóstico vs Módulo Dental

Basado en el inventario del dominio (Prompt 1), esta propuesta define la arquitectura de separación entre el "Nexus Core" (Agnóstico) y el "Módulo Dental".

## 1. Núcleo Agnóstico (Nexus Core)

El núcleo gestiona la infraestructura base, la seguridad y la comunicación. Debe ser totalmente independiente del negocio vertical.

### Componentes de Backend (`orchestrator_service`)
*   **Auth & Seguridad**: `auth_routes.py`, `auth_service.py`, `verify_admin_token` (Middleware).
*   **Gestión de Tenants**: Tablas `tenants`, `credentials` (Vault), rutas de configuración global.
*   **Usuarios y Roles**: Tabla `users`. El rol `professional` se renombrará a `agent` o `staff_member` en el futuro, pero la gestión de usuarios base es core.
*   **Motor de Chat (Omnichannel)**:
    *   `inbound_messages`, `chat_messages` (Tablas).
    *   Conexión con YCloud/WhatsApp.
    *   Lógica de envío/recepción y eventos Socket.IO (`NEW_MESSAGE`).
*   **Sistema de Archivos / Logs**: `system_events`, manejo de logs.
*   **Infraestructura Base**: `db.py` (Pool, Migraciones del Core), `main.py` (Server setup, CORS, Static files).

### Componentes de Frontend (`frontend_react`)
*   **Shell de Aplicación**: `Layout`, `Sidebar` (menú dinámico), `Topbar`.
*   **Autenticación**: `LoginView`, `AuthContext`.
*   **Configuración**: `ConfigView` (Idiomas, datos del tenant), `Credentials` (API Keys).
*   **Vista de Chats**: `ChatsView` (La interfaz de chat es agnóstica; el contexto del paciente/lead es inyectado).
*   **Gestión de Usuarios**: `UserApprovalView` (Base), `ProfileView`.

### Base de Datos (Tablas Core)
*   `tenants`
*   `users`
*   `credentials`
*   `inbound_messages`
*   `chat_messages`
*   `system_events`
*   `calendar_sync_log` (Log genérico, aunque la lógica de sync puede ser módulo).

---

## 2. Módulo de Nicho: Dental

Este módulo encapsula toda la lógica clínica y de agendamiento médico.

### Archivos y Rutas a Extraer
Se propone mover las siguientes rutas de `admin_routes.py` a un nuevo router `modules/dental/routes.py`:
*   `/patients/*` (CRUD de pacientes, Historia Clínica).
*   `/appointments/*` (Gestión de turnos, lógica de colisiones horarios).
*   `/professionals/*` (Gestión de staff médico, matrículas, especialidades).
*   `/treatments/*` (Configuración de prestaciones y precios).
*   `/calendar/*` (Vista de agenda médica).

### Entidades de Base de Datos (A migrar a esquema del módulo)
*   `patients` (Específico por `medical_history`, `insurance`).
*   `professionals` (Específico por `specialty`, `registration_id`).
*   `appointments` (Específico por `chair_id`, `urgency_level`).
*   `clinical_records` (Totalmente específico: odontograma).
*   `treatment_types` (Catálogo médico).
*   `daily_cash_flow` (Si la lógica de caja es específica de copagos médicos).

### Lógica del Agente (A extraer)
*   Tools: `check_availability` (Lógica de horarios médicos), `book_appointment` (Lógica de obra social), `list_services`.
*   Prompt: El texto del system prompt actual es 100% dental.

---

## 3. Propuesta de Estructura de Directorios

```text
orchestrator_service/
├── core/                   # NÚCLEO AGNÓSTICO
│   ├── auth/
│   ├── chat/
│   ├── database/           # db.py, migraciones core
│   └── api/                # auth_routes.py, admin_routes_core.py
├── modules/                # MÓDULOS PLUGGABLES
│   ├── dental/             # NICHO ACTUAL
│   │   ├── routes.py       # Endpoints dentales
│   │   ├── models.py       # Modelos Pydantic dentales
│   │   ├── services.py     # Lógica (check_availability, etc.)
│   │   └── tools.py        # Tools de LangChain dentales
│   └── crm_sales/          # FUTURO NICHO
└── main.py                 # Entrypoint (carga módulos según config)
```

```text
frontend_react/src/
├── core/                   # UI BASE
│   ├── layout/
│   ├── auth/
│   └── components/         # UI Kit genérico (Button, Input)
├── modules/
│   ├── dental/             # VISTAS DENTALES
│   │   ├── AgendaView.tsx
│   │   ├── PatientsView.tsx
│   │   └── components/     # Odontogram, TeethMap
│   └── crm_sales/
└── App.tsx                 # Router dinámico (carga rutas del módulo activo)
```

## 4. Estrategia de Interacción
*   **Inyección de Dependencias**: El Core define interfaces (ej. `ICalendarProvider`, `IProfileProvider`). El módulo Dental implementa `DentalCalendar` y `DentalProfile`.
*   **Configuración por Tenant**: La tabla `tenants` tendrá un campo `active_module: "dental"`. El backend cargará las rutas correspondientes al iniciar (o filtrará requests).
*   **Frontend Dinámico**: El `Sidebar` leerá la configuración del tenant y renderizará los links del módulo activo ("Agenda" vs "Leads").
