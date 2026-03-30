# SPEC: Agenda — Integración nativa con Cal.com para agendado automático

**Ticket:** DEV-53
**Fecha:** 2026-03-29
**Prioridad:** Alta
**Esfuerzo:** Medio (4 días)
**Confidence:** 80%

---

## 2. Requerimientos Técnicos

### 2.1 Backend: Integración Cal.com

1. **Módulo de Calendario:**
   - Extender `calendar_provider` para soportar `calcom`.
   - Guardar `calcom_api_key` y `event_type_id` en la tabla `credentials`.

2. **Webhooks de Cal.com:**
   - Endpoint: `POST /webhooks/calcom/{tenant_id}`.
   - Acciones:
     - `BOOKING_CREATED`: Crear `appointment` en la BD local, asociar con el lead (vía email/teléfono).
     - `BOOKING_CANCELLED`: Marcar turno como cancelado.
     - `BOOKING_RESCHEDULED`: Actualizar fecha/hora.

3. **Inyección en AI Agent:**
   - El agente debe poder dar el link de Cal.com si el lead está calificado.

### 2.2 Frontend: Configuración

1. **Panel de Conexión:**
   - Vista en `ConfigView` para conectar Cal.com.
   - Input para API Key y selector de Event Types disponibles (vía GET API de Cal.com).

---

## 3. Acceptance Criteria

- [ ] Las reservas hechas en Cal.com se sincronizan instantáneamente con la agenda de Nexus.
- [ ] Se identifica al lead por su email o teléfono durante la sincronización del webhook.
- [ ] El sistema envía recordatorios automáticos si están configurados en Cal.com pero Nexus los registra para el timeline.
- [ ] Si el turno se cancela en Cal.com, el estado del lead cambia a "re-agendar" (opcional/configurable).
