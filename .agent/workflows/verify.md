---
description: Ciclo de auto-verificacion y correccion para CRM Ventas. Valida backend, frontend, integraciones y seguridad.
---

# Verificacion - CRM Ventas (Nexus Core)

Ciclo completo de auto-verificacion tecnica, funcional y de seguridad para el sistema CRM de ventas.

## Cuando Ejecutar Este Workflow

- Despues de cada implementacion (`/implement`).
- Despues de corregir un bug (`/bug_fix`).
- Antes de hacer deploy o merge a la rama principal.
- Como validacion periodica de integridad del sistema.

## Paso 1: Verificacion Backend

### 1.1. Tests Automatizados

```bash
# Ejecutar suite completa de tests
cd orchestrator_service && pytest tests/ -v

# Ejecutar tests de un modulo especifico
cd orchestrator_service && pytest tests/test_leads.py -v

# Ejecutar con cobertura (si esta configurado)
cd orchestrator_service && pytest tests/ -v --cov=.
```

### 1.2. Verificacion de Endpoints API

Verificar que los endpoints principales respondan correctamente:

```bash
# Health check del orquestador (Puerto 8000)
curl -s http://localhost:8000/health

# Health check del servicio WhatsApp (Puerto 8002)
curl -s http://localhost:8002/health

# Verificar endpoint de leads (con autenticacion)
curl -s -H "Authorization: Bearer <TOKEN>" http://localhost:8000/admin/core/crm/leads
```

### 1.3. Verificacion de Servicios Backend

- [ ] `main.py` inicia sin errores.
- [ ] `db.py` conecta al pool de PostgreSQL correctamente.
- [ ] `gcal_service.py` puede autenticarse con Google Calendar.
- [ ] `analytics_service.py` genera metricas sin errores.
- [ ] Jobs de APScheduler estan registrados y activos.
- [ ] `modules/crm_sales/routes.py` responde en las rutas `/admin/core/crm/*`.

## Paso 2: Verificacion Frontend

### 2.1. Build de Produccion

```bash
# Build completo - debe compilar sin errores ni warnings criticos
cd frontend_react && npm run build
```

### 2.2. Verificacion TypeScript

```bash
# Verificar tipos - debe pasar sin errores
cd frontend_react && npx tsc --noEmit
```

### 2.3. Checklist de Frontend

- [ ] Todas las vistas cargan sin errores en consola.
- [ ] Los componentes renderizan correctamente en mobile y desktop.
- [ ] Las llamadas API usan la instancia de axios configurada (`src/api/axios.ts`).
- [ ] Los textos usan traducciones i18n (`t('clave')`), no strings hardcodeados.
- [ ] Archivos `es.json` y `en.json` tienen las mismas claves.
- [ ] Los estilos usan Tailwind CSS de forma consistente.
- [ ] No hay `console.log` de debug en codigo de produccion.

## Paso 3: Verificacion de Integraciones

### 3.1. PostgreSQL

```bash
# Verificar conexion a la base de datos
docker exec orchestrator_service python -c "
import asyncio, asyncpg
async def test():
    pool = await asyncpg.create_pool('postgresql://...')
    result = await pool.fetchval('SELECT 1')
    print(f'PostgreSQL OK: {result}')
    await pool.close()
asyncio.run(test())
"
```

Verificar tablas criticas existen:
- [ ] `leads`
- [ ] `sellers`
- [ ] `clients`
- [ ] `opportunities`
- [ ] `sales_transactions`
- [ ] `seller_agenda_events`
- [ ] `chat_messages`
- [ ] `notifications`
- [ ] `seller_metrics`
- [ ] `assignment_rules`

### 3.2. Redis

```bash
# Verificar que Redis esta activo y accesible
docker exec redis redis-cli ping
# Respuesta esperada: PONG
```

### 3.3. Socket.IO

- [ ] El servidor Socket.IO esta activo en el orquestador.
- [ ] Los clientes frontend pueden conectarse.
- [ ] Los eventos se emiten y reciben correctamente.
- [ ] Los eventos estan filtrados por `tenant_id` (no hay fuga entre tenants).

### 3.4. Google Calendar (si aplica)

- [ ] Service Account tiene permisos sobre los calendarios configurados.
- [ ] Se pueden crear eventos de prueba.
- [ ] Se pueden consultar disponibilidad.
- [ ] Los eventos tienen zona horaria correcta.

### 3.5. WhatsApp (si aplica)

- [ ] Webhook esta configurado y accesible.
- [ ] Los mensajes entrantes se procesan correctamente.
- [ ] Las respuestas se envian sin errores.
- [ ] La validacion de firma/secreto funciona.

## Paso 4: Auditoria de Seguridad

### 4.1. Aislamiento Multi-Tenant

- [ ] **CRITICO**: Todas las queries SQL incluyen filtro `WHERE tenant_id = $X`.
- [ ] Ningun endpoint expone datos de otros tenants.
- [ ] Los resultados de listados solo muestran datos del tenant actual.
- [ ] Las operaciones de escritura asignan el `tenant_id` correcto.

### 4.2. Autenticacion y Autorizacion

- [ ] Todos los endpoints requieren JWT o X-Admin-Token.
- [ ] Los tokens JWT se validan correctamente.
- [ ] Los tokens expirados son rechazados.
- [ ] X-Admin-Token solo funciona para rutas administrativas.
- [ ] No hay endpoints publicos no intencionados.

### 4.3. Validacion de Roles

- [ ] Endpoints de CEO solo accesibles por rol `ceo`.
- [ ] Setters solo ven leads asignados a ellos (o leads sin asignar).
- [ ] Closers solo ven oportunidades en su pipeline.
- [ ] Secretarias tienen acceso a agenda pero no a metricas financieras.
- [ ] Profesionales ven su propio calendario y citas.

### 4.4. Proteccion de Datos

- [ ] No se exponen passwords en respuestas API.
- [ ] No se exponen tokens de integracion en el frontend.
- [ ] Los inputs del usuario estan sanitizados (prevencion de SQL injection).
- [ ] Los parametros SQL usan placeholders (`$1`, `$2`), nunca concatenacion de strings.

### 4.5. Rate Limiting

- [ ] Los endpoints publicos (webhooks) tienen rate limiting configurado.
- [ ] Los endpoints de autenticacion tienen proteccion contra fuerza bruta.

## Paso 5: Verificacion Cruzada contra Spec

Si existe un archivo `.spec.md` asociado:

1. **Leer los criterios de aceptacion** (escenarios Gherkin).
2. **Verificar cada escenario**:
   - Ejecutar manualmente el flujo descrito en el Given/When/Then.
   - Verificar que la respuesta coincide con lo esperado.
   - Documentar cualquier discrepancia.
3. **Verificar requerimientos no funcionales**:
   - Tiempos de respuesta dentro de los limites.
   - i18n completo (espanol e ingles).
   - Responsive en mobile.

## Resumen de Comandos de Verificacion

```bash
# 1. Backend tests
cd orchestrator_service && pytest tests/ -v

# 2. Frontend build
cd frontend_react && npm run build

# 3. Frontend TypeScript
cd frontend_react && npx tsc --noEmit

# 4. Docker services status
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 5. Redis
docker exec redis redis-cli ping

# 6. Logs recientes (buscar errores)
docker logs orchestrator_service --tail 50 2>&1 | grep -i error
docker logs whatsapp_service --tail 50 2>&1 | grep -i error
```

## Resultado de la Verificacion

Al finalizar, reportar:

| Area | Estado | Notas |
|------|--------|-------|
| Tests backend | PASS/FAIL | Detalles |
| Build frontend | PASS/FAIL | Detalles |
| TypeScript | PASS/FAIL | Detalles |
| PostgreSQL | PASS/FAIL | Detalles |
| Redis | PASS/FAIL | Detalles |
| Socket.IO | PASS/FAIL | Detalles |
| Seguridad tenant | PASS/FAIL | Detalles |
| Autenticacion | PASS/FAIL | Detalles |
| Spec compliance | PASS/FAIL | Detalles |

**Si algun area falla**: Ejecutar `/bug_fix` para diagnosticar y resolver el problema antes de continuar.
