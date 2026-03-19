---
description: Genera una especificacion tecnica (.spec.md) rigurosa a partir de requerimientos para CRM Ventas, con criterios de aceptacion Gherkin.
---

# Especificacion Tecnica - CRM Ventas (Nexus Core)

Transforma requerimientos vagos o ideas de negocio en una especificacion tecnica rigurosa y ejecutable.

## Paso 1: Entrevista Tecnica

Recopilar la informacion necesaria respondiendo estas preguntas:

### 1.1. Contexto del Requerimiento

- **Quien lo solicita**: CEO, setter, closer, secretaria, profesional.
- **Que problema resuelve**: Descripcion del dolor actual.
- **Que modulo afecta**: leads, pipeline, agenda, chat, notificaciones, metricas, prospecting.
- **Que roles interactuan**: ceo, setter, closer, secretary, professional.

### 1.2. Definir Entradas de Datos

Identificar todos los datos que el sistema recibe:

| Entrada | Origen | Formato | Ejemplo |
|---------|--------|---------|---------|
| Datos del lead | Formulario / WhatsApp / Meta Ads | JSON | `{nombre, telefono, email, fuente}` |
| Asignacion de seller | Reglas automaticas / Manual | ID | `seller_id: 5` |
| Etapa del pipeline | Accion del closer | Enum | `contactado, calificado, propuesta, cierre` |
| Evento de agenda | Formulario de agenda | ISO 8601 | `2026-03-19T10:00:00-05:00` |
| Mensaje de chat | WhatsApp webhook | Texto/Media | `{from, body, timestamp}` |
| Filtros de busqueda | UI del CRM | Query params | `?status=activo&seller_id=3` |

### 1.3. Definir Salidas Esperadas

Identificar todos los resultados que el sistema produce:

| Salida | Destino | Formato | Ejemplo |
|--------|---------|---------|---------|
| Respuesta API | Frontend | JSON | `{success: true, data: [...]}` |
| Actualizacion UI | Vista React | Estado | Re-render de tabla/cards |
| Notificacion | Panel + Socket.IO | Evento | `{tipo, titulo, mensaje}` |
| Mensaje WhatsApp | Cliente/Lead | Texto | Confirmacion de cita |
| Evento calendario | Google Calendar | API Call | Crear/actualizar evento |
| Metrica | Dashboard CEO | Agregacion | `{leads_hoy: 15, conversion: 0.23}` |

### 1.4. Definir Reglas de Negocio

- Reglas de asignacion de leads (tabla `assignment_rules`).
- Transiciones validas de etapa en el pipeline.
- Permisos por rol (que puede ver/hacer cada rol).
- Restricciones de agenda (horarios, solapamientos).
- Reglas de notificacion (cuando y a quien notificar).

## Paso 2: Generar el .spec.md

El archivo de especificacion debe seguir esta estructura:

```markdown
# Spec: [Nombre de la Feature]

## 1. Contexto
- **Problema**: [Descripcion del problema actual]
- **Solucion propuesta**: [Resumen de la solucion]
- **Modulos afectados**: [Lista de modulos]
- **Roles involucrados**: [Lista de roles]

## 2. Requerimientos Funcionales
### RF-01: [Nombre]
- Descripcion: [Que debe hacer]
- Prioridad: Alta | Media | Baja

### RF-02: [Nombre]
...

## 3. Requerimientos No Funcionales
- **Seguridad**: Aislamiento por tenant_id, autenticacion JWT.
- **Rendimiento**: Respuesta < 500ms para queries de listado.
- **Disponibilidad**: Compatible con la arquitectura Docker actual.
- **i18n**: Soporte espanol e ingles.

## 4. Esquema de Datos

### Tablas Nuevas
```sql
CREATE TABLE IF NOT EXISTS nueva_tabla (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL,
    -- campos especificos
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Modificaciones a Tablas Existentes
```sql
ALTER TABLE leads ADD COLUMN IF NOT EXISTS nuevo_campo TEXT DEFAULT '';
```

## 5. API Endpoints

### POST /admin/core/crm/recurso
- **Auth**: JWT (roles: ceo, setter)
- **Body**: `{campo1: string, campo2: number}`
- **Response 200**: `{success: true, data: {id: 1, ...}}`
- **Response 400**: `{error: "Validacion fallida"}`
- **Response 401**: `{error: "No autorizado"}`

## 6. Criterios de Aceptacion (Gherkin)

### Escenario 1: [Nombre del escenario]
```gherkin
Given un usuario con rol "setter" autenticado
And el tenant_id es 1
When crea un nuevo lead con datos validos
Then el lead se guarda en la base de datos con tenant_id = 1
And se asigna automaticamente segun assignment_rules
And se genera una notificacion para el seller asignado
And la respuesta tiene status 200
```

### Escenario 2: [Nombre del escenario]
```gherkin
Given un usuario con rol "closer"
When intenta acceder a un lead de otro tenant
Then recibe un error 403
And no se exponen datos del otro tenant
```

## 7. Consideraciones de Seguridad
- [ ] Todas las queries filtran por tenant_id
- [ ] Endpoints protegidos con JWT o X-Admin-Token
- [ ] Validacion de rol en cada endpoint
- [ ] Sin inyeccion SQL (uso de parametros $1, $2...)
- [ ] Sanitizacion de inputs del usuario
```

## Paso 3: Validacion de Soberania de Datos

Antes de aprobar la spec, verificar:

- [ ] **Aislamiento multi-tenant**: Toda query incluye `WHERE tenant_id = $X`.
- [ ] **Sin acceso cruzado**: Un tenant no puede ver datos de otro.
- [ ] **Autenticacion completa**: Todos los endpoints requieren JWT o X-Admin-Token.
- [ ] **Roles respetados**: Cada endpoint valida el rol del usuario.
- [ ] **Datos sensibles**: No se exponen passwords, tokens o datos de otros tenants en las respuestas.

## Paso 4: Regla de Oro de Ejecucion

**NUNCA ejecutar comandos SQL (`psql`, `asyncpg.connect`) directamente contra la base de datos de produccion.**

Si necesitas verificar datos o ejecutar migraciones:
1. Proporcionar el comando SQL al usuario.
2. Esperar a que el usuario ejecute el comando y comparta los resultados.
3. Continuar con el analisis basado en los resultados proporcionados.

## Siguiente Paso

Una vez aprobada la spec, ejecutar `/plan` para generar el plan de implementacion.
