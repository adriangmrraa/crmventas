# Histórico de Problemas y Soluciones

Este documento registra problemas encontrados y sus soluciones para referencia futura.

## Startup, Routing y Persistencia (v4)

**Problema (2026-02-05):**
- **401 Unauthorized**: Frontend fallaba al conectar con Orchestrator por falta de token en build.
- **404 Not Found**: YCloud enviaba webhooks a `/webhook` pero el servicio esperaba `/webhook/ycloud`.
- **422 Unprocessable**: Mismatch de nombres en JSON entre WhatsApp de entrada (`from_number`/`text`) y Orchestrator (`phone`/`message`).
- **500 Internal Error (Bcrypt)**: `passlib` fallaba al chocar con `bcrypt 4.x` en Linux. Esto se manifestaba como un error de CORS en el navegador porque el servidor moría antes de inyectar los headers.
- **Pantalla en Blanco (Navigation)**: Al navegar a `/agenda` o `/pacientes`, la aplicación desaparecía.

**Solución Aplicada:**
- **Frontend (CORS/Auth)**: Se inyectó `VITE_ADMIN_TOKEN` en el Dockerfile y se agregó un `@app.exception_handler(Exception)` global en `main.py` para devolver JSON siempre, asegurando que los headers de CORS estén presentes incluso en errores 500.
- **Bcrypt Fix**: Se fijó `bcrypt==3.2.0` en `requirements.txt` y se agregó truncado de 72 bytes en las contraseñas para evitar el límite físico de la librería.
- **Navigation Fix**: Se cambió `path="/"` por `path="/*"` en `App.tsx` para permitir el matching de rutas anidadas en React Router 6.
- **Maintenance Robot (db.py)**: 
  - Se implementó un **Smart SQL Splitter** que divide el schema por `;` (respetando bloques `$$`).
  - Se creó un sistema de **Evolución por Parches** con auto-activación de CEO (Omega Prime).

**Estado:**
- ✅ Completamente estabilizado en v7.6 "Sovereign Platinum".

---

## Calendario e IA: "La IA no puede ver disponibilidad" (v7.6+)

**Problema:** El asistente por WhatsApp responde que no puede consultar disponibilidad o que no hay huecos, cuando la clínica espera usar Google Calendar o tiene turnos en la agenda.

**Causas típicas y qué revisar:**

1. **Clínica con `calendar_provider = 'local'`**  
   Si en BD la sede tiene `tenants.config.calendar_provider = 'local'`, la IA **no** llama a Google; solo usa la tabla `appointments` y horarios de profesionales. Si no hay turnos cargados o los profesionales no tienen `working_hours` configurados, puede devolver "no hay huecos".  
   **Solución:** Confirmar en Gestión de Clínicas que la sede tenga guardado **Google** como proveedor de calendario si se quiere usar GCal.

2. **`calendar_provider` no se persiste al guardar**  
   Si al guardar en el modal de sedes el valor Google no se escribe en `tenants.config`, la clínica sigue en local.  
   **Solución:** Revisar que el frontend/backend persistan correctamente `calendar_provider` al actualizar la sede.

3. **Clínica en Google pero profesionales sin `google_calendar_id`**  
   Para cada profesional con `calendar_provider == 'google'`, la tool `check_availability` necesita su `google_calendar_id`. Si **ningún** profesional del tenant tiene ese ID, no se consulta ningún calendario de Google.  
   **Solución:** En Perfil o en la gestión de profesionales, asignar a cada profesional el ID del calendario de Google creado en la cuenta de la clínica.

4. **Credenciales de Google**  
   Si `GOOGLE_CREDENTIALS` (o la integración connect-sovereign con Auth0) no está definida o es inválida, `gcal_service` no puede llamar a la API.  
   **Solución:** Verificar variables de entorno y/o flujo connect-sovereign en docs/03_deployment_guide.md y docs/API_REFERENCE.md (POST /admin/calendar/connect-sovereign).

5. **Excepciones en `check_availability`**  
   Si falla el parseo de fecha, la consulta a BD o la llamada a GCal, la tool devuelve un mensaje genérico y la IA repite que no pudo consultar.  
   **Solución:** Revisar logs del orchestrator en el momento de la petición del paciente para ver el traceback.

**Resumen:** Para que la IA "vea" disponibilidad con Google hace falta: (a) `calendar_provider = 'google'` persistido para la sede; (b) cada profesional con `google_calendar_id`; (c) credenciales correctas; (d) que no falle parseo ni consulta.

---

*Histórico de Problemas y Soluciones Nexus v3 © 2026*

---

## LeadsView: Pantalla en Blanco + Error React #31 (2026-02-24)

**Problema:**
- La página `/crm/leads` mostraba una pantalla en blanco en producción.
- Error React #31: un objeto (array de detalles 422) se pasaba como children de un nodo React.
- El backend retornaba `422 Unprocessable Entity` al llamar `GET /admin/core/crm/leads`.

**Causa Raíz:**
1. `LeadsView.tsx` llamaba al endpoint **equivocado**: `GET /admin/core/crm/leads` (que existía pero tenía `le=100` y no filtraba por source).
2. En un refactor intermedio se cambió a `GET /admin/core/crm/prospecting/leads`, que **requiere `tenant_id_override` obligatorio** — sin este param el backend responde 422.
3. El array `detail` del 422 era pasado directamente a `setError()` y luego renderizado como nodo React.

**Solución Aplicada:**
- **Frontend**: `LeadsView.tsx` vuelve a usar `GET /admin/core/crm/leads` (endpoint genérico, todo sources, JWT-based).
- **Backend**: Se aumentó el límite de `le=100` → `le=500` en `list_leads` para soportar carga completa.
- **Error #31**: Se agregó un guard `typeof error === 'string' ? error : JSON.stringify(error)` en el setter de error del componente.

**Diferencia clave entre endpoints:**

| Endpoint | Source filter | tenant_id | Usar para |
|----------|--------------|-----------|-----------|
| `GET /admin/core/crm/leads` | Ninguno (todos) | JWT automático | Vista de Leads (todas las pestañas) |
| `GET /admin/core/crm/prospecting/leads` | Solo `apify_scrape` | `tenant_id_override` obligatorio | Vista de Prospección |

**Estado:** ✅ Resuelto en commit `4c857ca`.

---

## Error 500 en Login: Tabla Sellers Inexistente / Índices Duplicados (2026-02-25)

**Problema:**
- Tras implementar Seguridad Nexus v7.6, el login devolvía **500 Internal Server Error** para cuentas CEO.
- El log indicaba `column "tenant_id" of relation "sellers" does not exist` o errores de duplicación de índices.
- La tabla `sellers` se había creado previamente fuera del pipeline de evolución sin la columna `tenant_id`.

**Causa Raíz:**
1. El parche de evolución 32 usaba `CREATE TABLE IF NOT EXISTS`, lo cual no reparaba la tabla si ya existía pero con esquema incompleto.
2. El código de login intentaba consultar `sellers` para resolver el `tenant_id` del usuario sin manejar la posible ausencia de la tabla o columna.

**Solución Aplicada:**
- **Backend (db.py)**: Se refactorizó el parche 32 para ser **idempotente y reparador**. Ahora crea la tabla si no existe, y luego usa `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` para asegurar que `tenant_id` esté presente. También usa bloques `EXCEPTION` para ignorar errores de índices duplicados.
- **Backend (auth_routes.py)**: Se envolvió la consulta a `sellers` en un bloque `try/except`. Si la tabla falla (p. ej. en medio de una migración), el sistema cae a un fallback seguro usando la tabla `professionals` o el `tenant_id` directo del usuario.

**Lección**: Nunca confiar en `CREATE TABLE IF NOT EXISTS` para integridad de columnas si la tabla pudo ser creada manualmente. Usar siempre `ALTER TABLE` reparadores.

**Estado:** ✅ Resuelto en commit `5cb58e1`.

---

## Error 429: Too Many Requests (Rate Limiting v7.7)

**Problema:**
- El frontend o integraciones automatizadas reciben un error **429** al intentar loguearse repetidamente.

**Causa Raíz:**
- Se implementó `slowapi` con un límite de 5 intentos por minuto por IP para prevenir ataques de fuerza bruta.

**Solución:**
- El usuario debe esperar 60 segundos antes de reintentar. 
- En entornos de prueba (CI/CD), se puede considerar aumentar el límite o usar IPs blancas si es necesario.

**Estado:** ✅ Comportamiento de diseño Nexus v7.7.

## Error de Build Frontend: Tags JSX Mal Cerrados (2026-02-25)

**Problema:**
- La aplicación fallaba al compilar en producción con errores de sintaxis en `CrmDashboardView.tsx`.
- Síntomas: `Unterminated regular expression literal` o `Expected corresponding JSX closing tag for 'main'`.

**Causa Raíz:**
- Un tag `<ResponsiveContainer>` de apertura faltaba en el gráfico `PieChart`.
- Desequilibrio en el cierre de tags `div` y `main` tras un refactor de layout.

**Solución Aplicada:**
- Se restauró la simetría de tags en `CrmDashboardView.tsx`.
- Se eliminaron imports no utilizados que generaban warnings de build.
- Se agregó tipado `any` y guards de nulidad en los formateadores de `recharts` para prevenir fallos de `tsc`.

**Estado:** ✅ Resuelto y verificado en commit `7750617`.

## Consolidación de Base de Datos: Fuente Única de Verdad (2026-02-25)

**Problema:**
- Existencia de múltiples archivos de esquema (`init.sql`, `migrations.sql`, `dentalogic_schema.sql`) y parches manuales.
- Riesgo de inconsistencia al desplegar nuevos tenants o actualizar existentes.

**Causa Raíz:**
- El crecimiento orgánico del proyecto (módulo CRM, Meta Ads) generó fragmentación en la definición de la base de datos.

**Solución Aplicada:**
- **Master Schema**: Se consolidaron todos los parches (001-040) y tablas de Marketing Hub en `dentalogic_schema.sql` (v2.0).
- **Maintenance Robot**: Se sincronizó `db.py` para incluir todos los parches de forma idempotente, permitiendo que cualquier DB antigua se actualice automáticamente al arrancar.
- **Validación de Tipos**: Se corrigieron errores de Pyre2 en `db.py` mediante el uso de `Dict[str, Any]` y casts para permitir la inyección dinámica de datos de atribución.

**Estado:** ✅ Arquitectura unificada y verificada.

---

---

## Visibilidad de Leads: "No name" en Conversaciones (2026-02-26)

**Problema:**
- La lista de conversaciones mostraba "No name" para contactos que sí tenían nombre en la base de datos.
- El contexto clínico funcionaba bien, pero la cabecera y lista de chats fallaban.

**Causa Raíz:**
- Desajuste de llaves entre Backend y Frontend. El Backend devolvía `contact_name` / `contact_id`, mientras que el Frontend (`ChatsView.tsx`) esperaba `patient_name` / `patient_id`.

**Solución Aplicada:**
- **Backend (chat_service.py)**: Se modificó `_get_crm_sessions` para devolver ambas llaves (`patient_name` y `patient_id` como alias de los campos de contacto), garantizando compatibilidad retroactiva.

**Estado:** ✅ Resuelto y verificado.

---

## Mensajes Fantasma: Bucle de Repetición del Bot (2026-02-26)

**Problema:**
- El usuario recibía mensajes del bot ("Hola de nuevo", etc.) de forma repetitiva cada 15-20 minutos.
- Estos mensajes **no aparecían** en el historial de chat de la plataforma.

**Causa Raíz:**
1. **TypeError en WhatsApp Service**: La firma de `send_template` en `ycloud_client.py` no aceptaba el argumento opcional `tenant_id`, causando que el proceso fallara *después* de enviar el mensaje a YCloud pero *antes* de marcar el éxito en la base de datos del Orchestrator.
2. **Missing Logging**: El `AutomationService` registraba la acción en `automation_logs` pero no en `chat_messages`.
3. **Loop de Reintentos**: Al no registrarse el éxito debido al error de firma, el trigger (p. ej. Lead Recovery) volvía a dispararse en el siguiente ciclo.

**Solución Aplicada:**
- **WhatsApp Service**: Se sincronizaron las firmas de `YCloudClient` para aceptar `tenant_id`.
- **Orchestrator (automation_service.py)**: Se agregó una llamada a `db.append_chat_message` dentro de `send_hsm`. Ahora los mensajes automáticos son visibles en el CRM y el flujo se completa correctamente sin reintentos infinitos.

**Estado:** ✅ Resuelto en v7.8.

---

## Herramientas de Diagnóstico Implementadas (Febrero 2026)

### Problema: Debugging Complejo de Marketing Hub
- Dificultad para diagnosticar problemas en estadísticas marketing
- Falta de visibilidad en automatización HSM
- Verificación manual tediosa de leads y datos

### Solución: Scripts de Diagnóstico Automatizados

#### **1. debug_marketing_stats.py**
```bash
# Uso: python debug_marketing_stats.py
# Propósito: Debugging estadísticas marketing tenant 1
# Funcionalidad: Consulta stats campañas, creativos, account total spend
```

#### **2. check_automation.py**
```bash
# Uso: python check_automation.py
# Propósito: Diagnóstico automatización
# Funcionalidad: Verifica reglas activas, logs recientes, status leads específicos
```

#### **3. check_leads.py**
```bash
# Uso: python check_leads.py
# Propósito: Verificación leads base datos
# Funcionalidad: Lista leads tenant 1 + números chat para cross-reference
```

### Casos de Uso Comunes:

#### **Caso 1: Estadísticas Marketing No Muestran Datos**
```bash
python debug_marketing_stats.py
# Verifica: Conexión DB, tenant_id 1, consultas MarketingService
```

#### **Caso 2: Automatización HSM No Funciona**
```bash
python check_automation.py
# Verifica: Reglas activas, logs recientes, status leads target
```

#### **Caso 3: Leads No Sincronizados con Chat**
```bash
python check_leads.py
# Verifica: Leads en DB vs números en chat_messages
```

### Mejoras en Frontend (Febrero 2026)

#### **Problema: UI Scroll Issues en Marketing Hub**
- Modales con contenido extenso no scrolleaban en móviles
- Tablas de creativos sin paginación adecuada
- Wizard conexión Meta con UX mejorable

#### **Solución:**
- **MetaConnectionWizard.tsx**: Refactorizado con mejor UX, flujo paso a paso
- **MarketingHubView.tsx**: Scroll optimizado, tablas con filtros mejorados
- **ConfigView.tsx**: Gestión credenciales CRUD completa
- **Responsive Design**: `overflow-y-auto`, `max-h-[60vh]` para modales

#### **Problema: Endpoints Incorrectos en Producción**
- Frontend usando endpoints `/admin/marketing/` en lugar de `/crm/marketing/`
- OAuth popup no funcionando por URLs incorrectas

#### **Solución:**
- **Corrección Endpoints**: Todos los componentes actualizados para usar `/crm/marketing/` y `/crm/auth/meta/`
- **Data Structure Compatibility**: Soporte para `data.data || data` en API responses
- **Commit Fix**: `02853aa` - Corrección endpoints producción

### Webhook Configuration Issues

#### **Problema: URLs Webhook No Disponibles en Configuración**
- Dashboard marketing no mostraba URLs webhook copiables
- Configuración Meta Developers requería URLs manuales

#### **Solución:**
- **API Deployment Config**: Nuevo endpoint `GET /admin/config/deployment`
- **Inclusión Webhook Meta**: `webhook_meta_url` agregada a respuesta
- **Frontend Integration**: URLs disponibles en dashboard marketing

### Páginas Legales para Meta OAuth

#### **Problema: Meta OAuth Requiere Privacy Policy y Terms URLs**
- Aprobación Meta Developers necesita URLs públicas
- Proyecto sin páginas legales implementadas

#### **Solución:**
- **PrivacyTermsView.tsx**: Vista única para páginas legales
- **Rutas Implementadas**: `/legal`, `/privacy`, `/terms`
- **i18n Completo**: Español e inglés con contenido específico
- **Commit**: `ce4bfc5` - Implementación completa páginas legales

### Estado Actual:
- ✅ **Herramientas Debug**: Implementadas y documentadas
- ✅ **UI/UX Mejorado**: Scroll, endpoints, responsive design
- ✅ **Webhooks Config**: URLs disponibles via API
- ✅ **Páginas Legales**: Implementadas para Meta OAuth
- ✅ **Documentación**: Actualizada con todas las mejoras

**Recomendación:** Usar herramientas diagnóstico antes de reportar problemas en producción.

---

*Histórico de Problemas y Soluciones Nexus v7.8 + Marketing Hub v1.0 © 2026*
