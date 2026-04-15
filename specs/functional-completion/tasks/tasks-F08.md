# Tasks F-08: Supervisor Dashboard (Real-Time)

**Spec:** `08-supervisor-realtime.spec.md`
**Design:** `design/design-F08.md`
**Archivo:** `frontend_react/src/modules/crm_sales/views/SupervisorDashboard.tsx`

---

## Tareas

### T-08-01: Extender LiveMessage interface y agregar estado
**Req:** Base para todos
**Esfuerzo:** XS

- [ ] Tipar `role` como union `'user' | 'assistant' | 'system'` (actualmente `string`)
- [ ] Agregar `audio_transcription?: string` a `LiveMessage`
- [ ] Agregar estados: `sessions`, `urgencies`, `channelFilter`, `interventions`, `selectedTenantId`, `tenants`, `interventionError`
- [ ] Agregar import de `api` desde `../../../api/axios`

### T-08-02: Stats reales con polling (sessions + urgencies)
**Req:** SUP-01, SUP-02
**Depende de:** T-08-01
**Esfuerzo:** M

- [ ] Crear `fetchStats()` con `Promise.allSettled` para `/chat/sessions` y `/chat/urgencies`
- [ ] `useEffect` con `setInterval(fetchStats, 60000)` y cleanup, dependency en `selectedTenantId`
- [ ] Reemplazar card "Actividad Total" por tres cards: Mensajes en sesion, Conversaciones activas, Ratio IA
- [ ] Reemplazar card "Alertas Criticas" por dos cards: Intervenciones activas (URGENT count), Esperas largas
- [ ] Ratio IA: `Math.round((assistantCount / messages.length) * 100)` con guard div/0
- [ ] Test: render con 3 assistant + 1 user messages -> ratio muestra 75%
- [ ] Test: GET /chat/sessions error -> card muestra "--" sin crash
- [ ] Test: urgencies con 2 URGENT -> card muestra "2"

### T-08-03: Calculo de esperas largas
**Req:** SUP-02
**Depende de:** T-08-01
**Esfuerzo:** S

- [ ] `useMemo` que agrupa mensajes por phone, toma el mas reciente de cada uno
- [ ] Filtrar donde `role === 'user'` y timestamp > 5 minutos de antiguedad
- [ ] Mostrar count en card "Esperas largas"
- [ ] Test: mensaje de role 'user' con timestamp hace 10 min -> incluido
- [ ] Test: mensaje de role 'assistant' hace 10 min -> NO incluido
- [ ] Test: mensaje de role 'user' hace 2 min -> NO incluido

### T-08-04: Filtro por canal
**Req:** SUP-04
**Depende de:** T-08-01
**Esfuerzo:** S

- [ ] Constante `CHANNELS = ['all', 'whatsapp', 'instagram', 'facebook']`
- [ ] Chips de filtro en el header del live feed
- [ ] `filteredMessages` derivado de `messages` + `channelFilter`
- [ ] Renderizar `filteredMessages` en lugar de `messages`
- [ ] Test: channelFilter 'whatsapp' -> solo mensajes whatsapp
- [ ] Test: channelFilter 'all' -> todos los mensajes

### T-08-05: Diferenciacion visual por role
**Req:** SUP-05
**Depende de:** T-08-01
**Esfuerzo:** S

- [ ] Crear mapa `roleConfig` con bg, text, label, Icon por role
- [ ] Reemplazar avatar hardcodeado por avatar dinamico segun `roleConfig[msg.role]`
- [ ] Agregar badge de role (Cliente/IA/Sistema) junto al badge de channel
- [ ] Test: mensaje con role 'assistant' -> avatar violeta, label "IA"
- [ ] Test: mensaje con role 'user' -> avatar azul, label "Cliente"
- [ ] Test: mensaje con role 'system' -> avatar gris, label "Sistema"

### T-08-06: Boton de intervencion
**Req:** SUP-03
**Depende de:** T-08-01
**Esfuerzo:** M

- [ ] Funcion `handleIntervention(msg)` que llama a `POST /admin/core/chat/human-intervention`
- [ ] Toggle en Set `interventions`: add phone si activate, delete si deactivate
- [ ] Boton "Tomar control" (warning) / "Liberar" (danger) en cada message card
- [ ] Badge "INTERVENIDO" amarillo cuando phone esta en interventions Set
- [ ] Error handling con `interventionError` state
- [ ] Test: click "Tomar control" -> api.post con activate: true y phone correcto
- [ ] Test: click "Liberar" -> api.post con activate: false
- [ ] Test: tras tomar control, badge INTERVENIDO visible

### T-08-07: Tenant selector para CEO
**Req:** SUP-06
**Depende de:** T-08-02
**Esfuerzo:** M

- [ ] Si `user.role === 'ceo'`, fetch de tenants via `GET /admin/core/chat/tenants` al montar
- [ ] Select de tenant en columna lateral, solo visible para CEO
- [ ] Al cambiar `selectedTenantId`: disconnect socket, limpiar messages, reconectar a nuevo room
- [ ] Cambiar dependency del useEffect de socket de `[user]` a `[user, selectedTenantId]`
- [ ] Re-fetch stats al cambiar tenant (ya cubierto por dependency en fetchStats useEffect)
- [ ] Test: role 'seller' -> selector NO visible
- [ ] Test: role 'ceo' -> selector visible, carga tenants
- [ ] Test: cambiar tenant -> messages se limpia, socket reconecta a room correcto

### T-08-08: Transcripciones de voz
**Req:** SUP-07
**Depende de:** T-08-01
**Esfuerzo:** S

- [ ] Si `msg.audio_transcription` existe, mostrar bloque `<details>` colapsable debajo del contenido
- [ ] Icono de microfono en el summary
- [ ] Estilo consistente con el resto de la card
- [ ] Test: mensaje con audio_transcription -> bloque visible
- [ ] Test: mensaje sin audio_transcription -> sin bloque adicional

### T-08-09 (SHOULD): Limite de mensajes configurable
**Req:** SUP-08
**Esfuerzo:** S

- [ ] Estado `messageLimit: 50 | 100 | 200` con valor default 50
- [ ] Selector en header del live feed
- [ ] Modificar `.slice(0, messageLimit)` en el handler de SUPERVISOR_CHAT_EVENT
- [ ] Actualizar label "Ultimos X mensajes" con valor dinamico

### T-08-10 (SHOULD): Auto-scroll con override manual
**Req:** SUP-09
**Esfuerzo:** S

- [ ] Ref al container de scroll del live feed
- [ ] Detectar si usuario scrolleo manualmente (scroll position != bottom)
- [ ] Si no scrolleo, auto-scroll al agregar nuevo mensaje
- [ ] Si scrolleo, no forzar scroll

---

## Orden de Ejecucion

```
T-08-01 (interface + estado base)
  -> T-08-02 (stats polling)         \
  -> T-08-03 (esperas largas)         |
  -> T-08-04 (filtro canal)           |-- pueden ser paralelas
  -> T-08-05 (role visual)            |
  -> T-08-06 (intervencion)          /
  -> T-08-07 (tenant selector) -- depende de T-08-02 por fetchStats
  -> T-08-08 (transcripciones)

T-08-09 y T-08-10 son SHOULD, ejecutar despues de todos los MUST.
```

T-08-02 a T-08-06 y T-08-08 son independientes entre si (solo dependen de T-08-01) y pueden ejecutarse en paralelo.
