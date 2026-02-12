# Diseño de Contrato de API: Agnóstico vs Nicho

Este documento define la separación de rutas y recursos de la API para soportar múltiples nichos bajo un mismo núcleo.

## 1. Estrategia de Rutas

Se propone una separación estricta basada en namespaces URL:

### 1.1 Rutas Core (`/admin/core/*`)
Disponibles para todos los tenants, independientemente del nicho.

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/v1/auth/token` | Login y obtención de JWT. |
| GET | `/admin/core/users` | Gestión de usuarios (staff). |
| GET | `/admin/core/tenants/me` | Configuración del tenant actual. |
| GET | `/admin/core/chat/sessions` | Listado de conversaciones (agnóstico). |
| POST | `/admin/core/chat/send` | Envío de mensajes (agnóstico). |

### 1.2 Rutas de Nicho (`/admin/niche/*`)
Estas rutas cambian dinámicamente según la configuración del tenant (`niche_type`).

#### Caso: Nicho Dental (`niche_type="dental"`)
El router cargado en `/admin/niche` expone:

| Método | Ruta Relativa | Ruta Completa | Recurso |
|--------|---------------|---------------|---------|
| GET | `/patients` | `/admin/niche/patients` | Pacientes |
| GET | `/appointments` | `/admin/niche/appointments` | Turnos |
| POST | `/book` | `/admin/niche/book` | Agendar Turno |
| GET | `/treatments` | `/admin/niche/treatments` | Tratamientos |
| GET | `/calendar` | `/admin/niche/calendar` | Agenda Visual |

#### Caso: Nicho CRM Ventas (`niche_type="crm_sales"`)
El router cargado en `/admin/niche` expone:

| Método | Ruta Relativa | Ruta Completa | Recurso |
|--------|---------------|---------------|---------|
| GET | `/leads` | `/admin/niche/leads` | Prospectos/Leads |
| GET | `/templates` | `/admin/niche/templates` | Plantillas Meta |
| POST | `/campaigns` | `/admin/niche/campaigns` | Envíos masivos |
| GET | `/metrics` | `/admin/niche/metrics` | KPIs de Venta |

## 2. Convenciones de Diseño

1.  **Prefijo `/niche` opaco**: El frontend no necesita hardcodear `/dental` o `/crm`. Simplemente llama a `/admin/niche/resource`.
    *   *Ventaja*: Si mañana el tenant cambia de nicho (o migra), la URL base es la misma, solo cambian los recursos disponibles.
    *   *Desventaja*: El frontend debe saber qué recursos pedir. Esto se soluciona con el "Módulo de UI" que sabe qué rutas llamar.
2.  **Payloads Dinámicos**:
    *   Un `POST /admin/niche/settings` podría recibir parámetros distintos según el nicho. Validado por Pydantic models específicos del módulo.

## 3. Versionado

Se recomienda mantener el versionado global `/api/v1/`. Si un nicho evoluciona drásticamente, se puede manejar internamente en el módulo o crear `/api/v2/`.

## 4. Implementación Técnica

En `main.py`:

```python
# Carga condicional (pseudocódigo)
core_router = get_core_router()
app.include_router(core_router, prefix="/admin/core")

# Middleware o Dependencia para rutas de nicho
# Opción A: Router dinámico (complejo en tiempo de ejecución)
# Opción B: Montar TODOS los routers pero con prefijos distintos (/admin/dental, /admin/crm) y que el frontend decida.
# Recomendación: Opción B es más fácil de mantener y debuggear en Swagger UI.

app.include_router(dental_module.router, prefix="/admin/dental", tags=["Dental"])
app.include_router(crm_module.router, prefix="/admin/crm", tags=["CRM"])
```

**Nota sobre la propuesta de URL**: Aunque `/admin/niche` es elegante, para Swagger y tipado estático es mejor `/admin/dental` explícito. El Frontend usará una variable base `API_NICHE_BASE` que será `/admin/dental` o `/admin/crm` según la config del tenant al loguearse.
