---
name: "Sovereign Code Auditor"
description: "Experto en ciberseguridad y cumplimiento del Protocolo de Soberania Nexus para CRM Ventas."
trigger: "seguridad, auditoria, security, owasp, tenant, aislamiento, vulnerabilidad, commit"
scope: "SECURITY"
auto-invoke: false
---

# Auditoria de Seguridad Nexus - CRM Ventas

### 1. Sesion y Cookies (OWASP A02)
- [ ] Verificar que `auth_routes.py` emita `Set-Cookie` con los flags `httponly=True`, `secure=True`, `samesite="lax"`.
- [ ] Validar que el frontend use `withCredentials: true` en todas las instancias de Axios.
- [ ] Comprobar que el endpoint `/auth/logout` limpie efectivamente la cookie.

### 2. Infraestructura y Cabeceras (OWASP A01/A05)
- [ ] Confirmar que `SecurityHeadersMiddleware` este registrado en `main.py`.
- [ ] Probar con `curl -I` que las respuestas incluyan `Content-Security-Policy`, `Strict-Transport-Security` y `X-Frame-Options`.

### 3. IA y Prompts (OWASP LLM01)
- [ ] Asegurar que los mensajes de WhatsApp pasen por `core/prompt_security.py` antes de llegar a la IA (LangChain).
- [ ] Red Flag: Si se pasa el mensaje del lead/cliente directamente a un prompt string sin validacion previa.

### 4. Boveda de Datos (OWASP A04)
- [ ] Verificar que NO existan credenciales en texto plano en la DB (tabla `credentials`).
- [ ] Validar que se use `CREDENTIALS_FERNET_KEY` y no claves estaticas en el codigo.
- [ ] Confirmar que `meta_tokens` almacene tokens de Meta/Google Ads de forma cifrada.

### 5. Auditoria y Limites (Rate Limiting)
- [ ] **Rate Limiting**:
    - [ ] `/auth/login`: 5/min (Brute Force).
    - [ ] `/auth/register`: 3/min (Spam/Account creation).
    - [ ] `/leads`, `/clients`, `/opportunities`: 100/min (Scraping protection).
    - [ ] `/admin/whatsapp/send`: 30/min (Spam de mensajes).
- [ ] **Auto-Audit**: Comprobar que las rutas admin y CRM tengan el decorador `@audit_access`.
- [ ] **Audit Isolation**: Validar que los eventos grabados en `system_events` incluyan la columna `tenant_id` vinculada al inquilino correspondiente.
- [ ] **Audit Logs**: Validar que los eventos sean consultables por el CEO filtrados por su `allowed_tenant_ids`.

## Auditoria de Soberania Nexus

### 1. Multi-tenancy (Aislamiento de Datos)
- [ ] **Filtro `tenant_id`**: Cada consulta SQL (`SELECT`, `UPDATE`, `DELETE`) DEBE incluir `WHERE tenant_id = :tid`. Aplica a todas las tablas: `leads`, `sellers`, `clients`, `opportunities`, `sales_transactions`, `seller_agenda_events`, `chat_messages`, `notifications`, `seller_metrics`, `assignment_rules`, `meta_tokens`, `meta_ads_campaigns`, `google_calendar_blocks`.
- [ ] **Prevencion de Fugado**: Comprobar que no existan joins o subconsultas que omitan el filtro de tenant.
- [ ] **Roles y Permisos**: Validar que los roles (`ceo`, `professional`, `secretary`, `setter`, `closer`) solo accedan a datos de sus tenants autorizados.
- [ ] **Sellers Fallback**: Validar que los errores en tablas de modulos (como `sellers`, `seller_metrics`) se manejen con `try/except` para no romper el flujo principal.

### 2. Autenticacion y Autorizacion
- [ ] **JWT**: Verificar que el token JWT incluya `tenant_id` y `role` en el payload.
- [ ] **X-Admin-Token**: Validar que las rutas administrativas verifiquen el header `X-Admin-Token` ademas del JWT.
- [ ] **Aislamiento de Servicios**: Confirmar que la comunicacion entre `orchestrator_service` (8000) y `whatsapp_service` (8002) valide tokens internos.

### 3. Sanitizacion de Logs
- [ ] Verifica que ningun `print()` o `logger.info()` este imprimiendo objetos `credential` completos. Los valores deben estar enmascarados (`***`).
- [ ] Validar que los datos sensibles de leads/clientes (telefono, email) no se expongan en logs de debug.
