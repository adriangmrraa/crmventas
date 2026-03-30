# SPEC: Leads — Blacklist de números y emails con bloqueo automático

**Ticket:** DEV-55
**Fecha:** 2026-03-29
**Prioridad:** Media
**Esfuerzo:** Bajo-Medio (2 días)
**Confidence:** 95%

---

## 2. Requerimientos Técnicos

### 2.1 Backend: Sistema de Bloqueo

1. **Modelo Blacklist:**
   - Tabla `blacklist`: `id, tenant_id, value (phone/email), type, reason, created_at`.

2. **Lógica Preventiva:**
   - Integrar chequeo en `ensure_lead_exists`.
   - Si un entrada está en blacklist:
     - Registrar intento en `blacklist_attempts`.
     - NO crear lead ni procesar mensajes de la IA.
     - Responder con status `blocked` al webhook.

### 2.2 Frontend: Gestión de Blacklist

1. **CRUD Simple:**
   - Vista en Configuración para añadir/quitar números o emails de la lista negra.
   - Historial de intentos de contacto bloqueados.

---

## 3. Acceptance Criteria

- [ ] Los números bloqueados no generan notificaciones ni consumen tokens de IA.
- [ ] El administrador puede ver cuándo y quién intentó contactar desde un origen bloqueado.
- [ ] Se puede bloquear por patrón (ej: *@spam.com) usando wildcards si se desea (v2).
