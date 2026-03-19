---
description: Convierte un .spec.md en un plan tecnico detallado paso a paso para la implementacion en CRM Ventas.
---

# Plan de Implementacion - CRM Ventas (Nexus Core)

Convierte la especificacion tecnica (.spec.md) en una hoja de ruta ejecutable con tareas ordenadas y verificables.

## Entrada Requerida

- Archivo `.spec.md` generado por el workflow `/specify`.
- Contexto del modulo afectado dentro del CRM.

## Paso 1: Analizar la Especificacion

1. **Leer el .spec.md completo**.
2. **Extraer objetivos**: Que debe lograr la implementacion.
3. **Extraer criterios de aceptacion**: Condiciones Gherkin que definen "hecho".
4. **Identificar restricciones**: Limitaciones tecnicas, de seguridad o de negocio.
5. **Identificar dependencias**: Otros modulos o servicios que se ven afectados.

## Paso 2: Identificar Archivos Afectados

### Backend (orchestrator_service/)
| Tipo | Archivo | Cuando se modifica |
|------|---------|-------------------|
| Punto de entrada | `main.py` | Nuevos jobs APScheduler, configuracion Socket.IO |
| Base de datos | `db.py` | Nuevas tablas, columnas, migraciones |
| Rutas admin | `admin_routes.py` | Nuevos endpoints administrativos |
| Google Calendar | `gcal_service.py` | Cambios en agenda/eventos |
| Analytics | `analytics_service.py` | Nuevas metricas o reportes |
| Rutas CRM | `modules/crm_sales/routes.py` | Endpoints del modulo CRM |
| Modelos | `modules/crm_sales/models.py` | Nuevos schemas Pydantic |
| Tools IA | `modules/crm_sales/tools_provider.py` | Nuevas herramientas LangChain |

### Frontend (frontend_react/src/)
| Tipo | Directorio | Cuando se modifica |
|------|-----------|-------------------|
| Vistas | `views/` | Nuevas paginas o modificacion de existentes |
| Componentes | `components/` | Nuevos componentes reutilizables |
| API | `api/axios.ts` | Rara vez (instancia ya configurada) |
| i18n ES | `i18n/locales/es.json` | Cualquier texto nuevo en espanol |
| i18n EN | `i18n/locales/en.json` | Cualquier texto nuevo en ingles |
| Hooks | `hooks/` | Logica reutilizable de React |
| Tipos | `types/` | Nuevos tipos TypeScript |
| Context | `context/` | Nuevos providers de estado |

### Servicios Externos
| Servicio | Puerto | Cuando se modifica |
|----------|--------|-------------------|
| orchestrator_service | 8000 | Cambios en API o logica de negocio |
| whatsapp_service | 8002 | Cambios en mensajeria/webhooks |
| frontend_react | 5173 | Cambios en la interfaz de usuario |

## Paso 3: Plan de Migracion de Base de Datos

Si la spec requiere cambios en la BD, definir:

1. **Nuevas tablas**: Esquema completo con `tenant_id`, indices.
2. **Nuevas columnas**: Sentencias `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`.
3. **Nuevos indices**: Para optimizar consultas frecuentes.
4. **Datos iniciales**: Si se necesitan datos seed.
5. **Orden de ejecucion**: Dependencias entre migraciones.

**Regla critica**: Todas las migraciones deben ser idempotentes.

**Tablas de referencia del sistema**:
`leads`, `sellers`, `clients`, `opportunities`, `sales_transactions`, `seller_agenda_events`, `chat_messages`, `notifications`, `seller_metrics`, `assignment_rules`

## Paso 4: Desglose en Tareas Ordenadas

Cada tarea debe ser ejecutable en **5-15 minutos**. Seguir este orden:

### Fase A: Base de Datos (si aplica)
```
Tarea A1: Crear migracion de nuevas tablas/columnas en db.py
Tarea A2: Agregar indices necesarios
Tarea A3: Verificar migracion (ejecutar ensure_tables)
```

### Fase B: Backend - Logica de Negocio
```
Tarea B1: Crear/modificar modelos Pydantic (models.py)
Tarea B2: Implementar funciones de servicio (logica de negocio)
Tarea B3: Crear/modificar rutas API (routes.py o admin_routes.py)
Tarea B4: Agregar validaciones de autenticacion y roles
Tarea B5: Agregar filtros tenant_id a todas las queries
```

### Fase C: Backend - Integraciones (si aplica)
```
Tarea C1: Integrar con Google Calendar (gcal_service.py)
Tarea C2: Integrar con WhatsApp (whatsapp_service)
Tarea C3: Agregar eventos Socket.IO
Tarea C4: Agregar notificaciones
Tarea C5: Configurar jobs APScheduler (main.py)
```

### Fase D: Frontend - UI
```
Tarea D1: Agregar traducciones i18n (es.json, en.json)
Tarea D2: Crear/modificar tipos TypeScript
Tarea D3: Crear/modificar componentes
Tarea D4: Crear/modificar vistas
Tarea D5: Conectar con API (axios)
Tarea D6: Integrar Socket.IO en frontend (si aplica)
```

### Fase E: Tests y Verificacion
```
Tarea E1: Crear/actualizar tests backend (pytest)
Tarea E2: Verificar build frontend (npm run build)
Tarea E3: Verificar TypeScript (npx tsc --noEmit)
Tarea E4: Ejecutar /verify completo
```

## Paso 5: Definir Comandos de Verificacion

Para cada fase, definir los comandos que validan el exito:

```bash
# Fase A - Base de datos
# Verificar que las tablas se crearon correctamente
cd orchestrator_service && python -c "import asyncio; from db import ensure_tables; asyncio.run(ensure_tables())"

# Fase B - Backend
cd orchestrator_service && pytest tests/ -v

# Fase D - Frontend
cd frontend_react && npx tsc --noEmit
cd frontend_react && npm run build

# Fase E - Verificacion completa
# Ejecutar /verify
```

## Formato de Salida del Plan

El plan generado debe seguir esta estructura:

```markdown
# Plan de Implementacion: [Nombre de la Feature]

## Resumen
- **Spec**: [ruta al .spec.md]
- **Modulos afectados**: [lista]
- **Archivos a modificar**: [lista]
- **Estimacion total**: [X tareas, ~Y minutos]

## Tareas

### A1: [Descripcion] (~X min)
- **Archivo**: [ruta]
- **Accion**: [que hacer]
- **Verificacion**: [comando]

### A2: [Descripcion] (~X min)
...

## Criterios de Exito
- [ ] Todos los criterios de aceptacion del .spec.md se cumplen
- [ ] pytest pasa sin errores
- [ ] npm run build compila sin errores
- [ ] Aislamiento tenant_id verificado
- [ ] i18n completo (es + en)
```

## Siguiente Paso

Una vez generado el plan, ejecutar `/implement` para comenzar la implementacion tarea por tarea.
