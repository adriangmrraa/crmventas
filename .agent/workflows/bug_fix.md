---
description: Workflow para diagnosticar y solucionar bugs en CRM Ventas (Nexus Core). 4 fases sistematicas desde diagnostico hasta verificacion.
---

# Correccion de Bugs - CRM Ventas (Nexus Core)

Proceso estandarizado para diagnosticar y solucionar errores en el sistema CRM de ventas.

## Skills Recomendadas
- **Backend/Seguridad**: Backend_Sovereign (`orchestrator_service/`)
- **Frontend/UI**: Frontend_Nexus (`frontend_react/`)
- **WhatsApp/Chat**: Omnichannel_Chat_Operator (`whatsapp_service/`)

## Fase 1: Diagnostico (Evidence)

### 1.1. Revisar Logs

```bash
# Logs del orquestador principal (Puerto 8000)
docker logs orchestrator_service --tail 200

# Logs del servicio de WhatsApp (Puerto 8002)
docker logs whatsapp_service --tail 200

# Logs del frontend React (Puerto 5173)
docker logs frontend_react --tail 100
```

### 1.2. Verificar Integraciones Criticas

- [ ] **PostgreSQL**: Verificar conexion del pool en `orchestrator_service/db.py`.
- [ ] **Redis**: Verificar que el servicio de cache/sesiones este activo.
- [ ] **Socket.IO**: Verificar eventos en tiempo real (notificaciones, chat).
- [ ] **Google Calendar**: Verificar credenciales del Service Account en `gcal_service.py`.
- [ ] **WhatsApp Webhooks**: Verificar configuracion de webhook y secretos.
- [ ] **Meta/Google Ads**: Verificar tokens de acceso si el bug es de prospecting.

### 1.3. Identificar Contexto del Bug

- **Rol afectado**: ceo | setter | closer | secretary | professional
- **Modulo afectado**: leads | pipeline | agenda | chat | notificaciones | metricas | prospecting
- **Servicio afectado**: orchestrator_service (8000) | whatsapp_service (8002) | frontend_react (5173)
- **Ruta API afectada**: `/admin/core/crm/*` (leads, clients, sellers, agenda/events)

## Fase 2: Reproduccion (Isolation)

### 2.1. Aislar el Error

1. Identificar la ruta o componente exacto donde ocurre el error.
2. Verificar si el error es especifico de un `tenant_id` o es global.
3. Comprobar si el error depende del rol del usuario (permisos JWT).

### 2.2. Test de Reproduccion

Si el error es en un servicio backend, crear o ejecutar un test aislado:

```bash
# Ejecutar tests existentes
cd orchestrator_service && pytest tests/ -v

# Test especifico de un modulo
pytest tests/test_leads.py -v -k "nombre_del_test"
```

Si el error es en frontend:
```bash
cd frontend_react && npx tsc --noEmit
```

### 2.3. Verificar Datos

```bash
# Verificar estado de la base de datos (NUNCA ejecutar SQL directo en produccion)
# Proporcionar la query al usuario para que la ejecute manualmente
```

## Fase 3: Solucion (Fix)

### 3.1. Patrones Comunes de Bugs en CRM Ventas

#### Errores de Asignacion de Leads
- **Sintoma**: Leads no se asignan al seller correcto.
- **Causa comun**: Logica de `assignment_rules` mal configurada o filtros de `tenant_id` faltantes.
- **Archivos a revisar**: `orchestrator_service/admin_routes.py`, `orchestrator_service/db.py`, `modules/crm_sales/routes.py`.
- **Fix tipico**: Verificar que las queries incluyan `WHERE tenant_id = $1` y que las reglas de asignacion esten activas.

#### Errores de Notificaciones
- **Sintoma**: Notificaciones no llegan o llegan duplicadas.
- **Causa comun**: Eventos de Socket.IO mal emitidos, o registros duplicados en tabla `notifications`.
- **Archivos a revisar**: `orchestrator_service/main.py` (emision de eventos), `frontend_react/src/` (listeners de Socket.IO).
- **Fix tipico**: Verificar que el evento se emita una sola vez y que el frontend tenga el listener correcto.

#### Errores de Sincronizacion del Pipeline
- **Sintoma**: Oportunidades no avanzan de etapa o se pierden.
- **Causa comun**: Estado inconsistente entre `opportunities` y `sales_transactions`.
- **Archivos a revisar**: `modules/crm_sales/routes.py`, `orchestrator_service/db.py`.
- **Fix tipico**: Verificar transacciones atomicas en las actualizaciones de estado.

#### Errores de Webhooks de WhatsApp
- **Sintoma**: Mensajes no se reciben o no se procesan.
- **Causa comun**: Validacion HMAC fallida, formato de payload cambiado, timeout en el procesamiento.
- **Archivos a revisar**: `whatsapp_service/main.py`.
- **Fix tipico**: Verificar el secreto de webhook, parseo del payload y manejo de errores.

#### Errores de Agenda/Calendario
- **Sintoma**: Eventos no se crean o se solapan.
- **Causa comun**: Formato ISO incorrecto, conflicto de zona horaria, permisos de Google Calendar.
- **Archivos a revisar**: `orchestrator_service/gcal_service.py`, `orchestrator_service/admin_routes.py`.
- **Fix tipico**: Verificar formato de fechas ISO 8601 y permisos del Service Account.

#### Errores de Metricas del Seller
- **Sintoma**: Dashboard muestra datos incorrectos o desactualizados.
- **Causa comun**: Jobs de APScheduler no ejecutandose, queries de agregacion incorrectas.
- **Archivos a revisar**: `orchestrator_service/analytics_service.py`, `orchestrator_service/main.py` (scheduler).
- **Fix tipico**: Verificar que los jobs esten registrados y que las queries de `seller_metrics` sean correctas.

### 3.2. Reglas de Correccion

1. **Siempre** incluir filtro `tenant_id` en queries nuevas o modificadas.
2. **Nunca** modificar datos directamente en produccion via SQL.
3. **Siempre** mantener compatibilidad con los roles existentes.
4. **Siempre** preservar la internacionalizacion (i18n) en cambios de frontend.

## Fase 4: Verificacion (Verify)

### 4.1. Tests Automatizados

```bash
# Backend
cd orchestrator_service && pytest tests/ -v

# Frontend - Build completo
cd frontend_react && npm run build

# Frontend - Verificacion TypeScript
cd frontend_react && npx tsc --noEmit
```

### 4.2. Verificacion Manual

- [ ] Probar el flujo afectado con el rol especifico del usuario.
- [ ] Verificar que el fix no rompa otros modulos.
- [ ] Comprobar aislamiento multi-tenant (el fix no filtra datos entre tenants).
- [ ] Verificar que las notificaciones en tiempo real sigan funcionando (Socket.IO).
- [ ] Si el bug era de WhatsApp, enviar un mensaje de prueba y verificar el flujo completo.

### 4.3. Smoke Test

- [ ] Login con cada rol (ceo, setter, closer, secretary, professional).
- [ ] Navegacion basica por los modulos principales.
- [ ] Crear un lead de prueba y verificar asignacion.
- [ ] Verificar que el dashboard de metricas cargue correctamente.

### 4.4. Cierre

1. Documentar la causa raiz del bug.
2. Documentar la solucion aplicada.
3. Si aplica, crear un test de regresion para evitar recurrencia.
4. Ejecutar `/verify` para validacion completa del sistema.
