---
name: "Sovereign Code Auditor"
description: "Experto en ciberseguridad y cumplimiento del Protocolo de Soberanía Nexus."
trigger: "Antes de hacer commit, o cuando pida revisar seguridad o aislamiento."
scope: "SECURITY"
auto-invoke: false
---

# Auditoría de Seguridad Nexus v7.6 / v7.7

### 1. Sesión y Cookies (OWASP A02)
- [ ] Verificar que `auth_routes.py` emita `Set-Cookie` con los flags `httponly=True`, `secure=True`, `samesite="lax"`.
- [ ] Validar que el frontend use `withCredentials: true` en todas las instancias de Axios.
- [ ] Comprobar que el endpoint `/auth/logout` limpie efectivamente la cookie.

### 2. Infraestructura y Cabeceras (OWASP A01/A05)
- [ ] Confirmar que `SecurityHeadersMiddleware` esté registrado en `main.py`.
- [ ] Probar con `curl -I` que las respuestas incluyan `Content-Security-Policy`, `Strict-Transport-Security` y `X-Frame-Options`.

### 3. IA y Prompts (OWASP LLM01)
- [ ] Asegurar que los mensajes de WhatsApp pasen por `core/prompt_security.py` antes de llegar a la IA.
- [ ] Red Flag: Si se pasa el mensaje del usuario directamente a un prompt string sin validación previa.

### 4. Bóveda de Datos (OWASP A04)
- [ ] Verificar que NO existan credenciales en texto plano en la DB (tabla `credentials`).
- [ ] Validar que se use `CREDENTIALS_FERNET_KEY` y no claves estáticas en el código.

### 5. Auditoría y Límites (Nexus v7.7)
- [ ] **Rate Limiting**: Verificar bloqueo por IP (429) tras ráfagas en login.
- [ ] **Auto-Audit**: Comprobar que las rutas admin tengan el decorador `@audit_access`.
- [ ] **Audit Logs**: Validar que los eventos se graben en `system_events` y sean consultables por el CEO.

## Auditoría de Soberanía Nexus

### 1. Multi-tenancy (Aislamiento de Datos)
- [ ] **Filtro `tenant_id`**: Cada consulta SQL (`SELECT`, `UPDATE`, `DELETE`) DEBE incluir `WHERE tenant_id = :tid`.
- [ ] **Prevención de Fugado**: Comprobar que no existan joins o subconsultas que omitan el filtro de tenant.
- [ ] **Sellers Fallback**: Validar que los errores en tablas de módulos (como `sellers`) se manejen con `try/except` para no romper el flujo principal.

### 2. Sanitización de Logs
- [ ] Verifica que ningún `print()` o `logger.info()` esté imprimiendo objetos `credential` completos. Los valores deben estar enmascarados (`***`).
