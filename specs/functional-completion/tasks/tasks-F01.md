# Tasks F-01: Client 360° Tabs — Notes, Calls, WhatsApp

**Spec:** `01-client-360-tabs.spec.md`
**Design:** `design/design-F01.md`
**Fecha:** 2026-04-14

---

## Fase 1: Infraestructura y Types

- [ ] **T01** Crear directorio `frontend_react/src/modules/crm_sales/components/client360/`
- [ ] **T02** Crear archivo de tipos compartidos `client360/types.ts` con interfaces `Note`, `ChatMessage`, `TabState<T>`, `CallFormData`
- [ ] **T03** Crear constantes compartidas `client360/constants.ts`: `ROLE_COLORS`, `RESULT_LABELS`, `NOTE_TYPES`, `VISIBILITY_OPTIONS`

## Fase 2: Componentes Presentacionales

- [ ] **T04** Crear `NoteItem.tsx` — renderiza una nota con: author badge (color por rol), contenido, timestamp, boton edit (si autor + ventana 15min), boton delete (si autor o CEO), countdown de edicion
- [ ] **T05** Crear `CallResultBadge.tsx` — chip de resultado de llamada con color segun `RESULT_LABELS` (connected=green, no_answer=yellow, voicemail=orange, rescheduled=violet)
- [ ] **T06** Crear `WhatsAppBubble.tsx` — burbuja de mensaje: `role=user` alineada izquierda (inbound), `role=assistant` alineada derecha (outbound), timestamp debajo

## Fase 3: NotesTab

- [ ] **T07** Crear `NotesTab.tsx` — recibe props `leadId`, `notes`, `loading`, `error`, `onRetry`
- [ ] **T08** Implementar timeline cronologico ASC con `NoteItem` por cada nota
- [ ] **T09** Implementar formulario de creacion: textarea + selector `note_type` (internal/post_call/follow_up/handoff) + selector `visibility` (setter_closer/all/private) + submit
- [ ] **T10** POST a `/admin/core/crm/leads/{id}/notes` al submit, agregar nota al state on success
- [ ] **T11** Implementar soft-delete: DELETE al backend, quitar nota del state, modal de confirmacion
- [ ] **T12** Implementar edit inline: PUT al backend, reemplazar nota en state, ventana 15min con countdown
- [ ] **T13** Implementar Socket.IO: `join_lead` al montar, listener `LEAD_NOTE_CREATED` con dedup por id, `leave_lead` + cleanup al desmontar
- [ ] **T14** Loading skeleton mientras carga, error state con boton reintentar

## Fase 4: CallsTab

- [ ] **T15** Crear `CallsTab.tsx` — recibe props `leadId`, `calls` (notas filtradas `post_call`), `loading`, `error`, `onRetry`
- [ ] **T16** Renderizar historial de llamadas usando `NoteItem` + `CallResultBadge` para `structured_data.call_result`
- [ ] **T17** Implementar formulario "Registrar llamada": datetime-local, select resultado (connected/no_answer/voicemail/rescheduled), duracion (minutos), textarea notas
- [ ] **T18** Campo reagenda condicional: mostrar datetime-local extra cuando resultado = `rescheduled`
- [ ] **T19** POST nota `post_call` con `structured_data: { call_result, duration_minutes, scheduled_at? }`, agregar al historial on success

## Fase 5: WhatsAppTab

- [ ] **T20** Crear `WhatsAppTab.tsx` — recibe props `phone`, `tenantId`, `messages`, `loading`, `error`, `onRetry`
- [ ] **T21** Renderizar burbujas con `WhatsAppBubble` — scroll container con auto-scroll al bottom
- [ ] **T22** Estado vacio si `phone` es null/undefined: mostrar mensaje "Este cliente no tiene numero de WhatsApp registrado", sin formulario
- [ ] **T23** Formulario de envio: textarea + boton enviar. POST a `/admin/core/chat/send` con `{ phone, message, channel: "whatsapp" }`
- [ ] **T24** Optimistic update: agregar burbuja outbound inmediatamente, marcar con error si POST falla
- [ ] **T25** Socket.IO: listener `NEW_MESSAGE`, filtrar por phone, agregar burbuja, auto-scroll

## Fase 6: Integracion en ClientDetailView

- [ ] **T26** Modificar `ClientDetailView.tsx`: importar los 3 tab components
- [ ] **T27** Agregar state independiente por tab: `notesState`, `callsState`, `whatsappState` usando `TabState<T>`
- [ ] **T28** Implementar `Promise.allSettled` en `useEffect` al montar `client` — precarga paralela de los 3 tabs
- [ ] **T29** Reemplazar los 3 bloques placeholder por los componentes reales, pasando props correspondientes
- [ ] **T30** Implementar retry on tab click: si el tab tenia error previo, re-fetch al activar

## Fase 7: Tests

- [ ] **T31** Test `NoteItem.test.tsx`: render con datos, boton edit visible/disabled segun ventana, boton delete visible solo para autor/CEO
- [ ] **T32** Test `NotesTab.test.tsx`: render con notas, render sin notas, crear nota (mock POST), delete nota, error state con retry
- [ ] **T33** Test `WhatsAppTab.test.tsx`: render burbujas inbound/outbound, envio de mensaje (mock POST), estado sin telefono
- [ ] **T34** Test `CallsTab.test.tsx`: filtrado post_call, formulario registro llamada, campo reagenda condicional
- [ ] **T35** Test integracion: `Promise.allSettled` hace 3 requests, error en un tab no afecta otros

---

## Dependencias entre fases

```
Fase 1 (types) -> Fase 2 (presentacionales) -> Fases 3,4,5 (tabs, paralelas) -> Fase 6 (integracion) -> Fase 7 (tests)
```

## Estimacion

| Fase | Esfuerzo |
|------|----------|
| Fase 1 | 0.5h |
| Fase 2 | 1.5h |
| Fase 3 | 2h |
| Fase 4 | 1.5h |
| Fase 5 | 2h |
| Fase 6 | 1h |
| Fase 7 | 2.5h |
| **Total** | **~11h** |
