# FIX-01: Client 360 Tabs — Notas, Llamadas, WhatsApp

## Intent

Activar los 3 tabs placeholder en la vista Client 360 (`ClientDetailView.tsx`) para que sean funcionales. Actualmente muestran texto placeholder estático y no cargan datos reales.

## Requirements

### MUST

- **Tab Notas**: Crear componente `ClientNotesTab` que busque el `lead_id` vinculado al cliente via API, luego cargue y muestre las notas usando el patrón existente de `LeadNotesThread`. Si no hay lead vinculado, mostrar mensaje "No hay lead vinculado a este cliente".
- **Tab Llamadas**: Crear componente `ClientCallsTab` que obtenga eventos de agenda filtrados por `client_id`. Mostrar lista de llamadas con fecha, vendedor, estado y notas. Permitir agregar nueva llamada reutilizando `AgendaEventForm`.
- **Tab WhatsApp**: Crear componente `ClientWhatsAppTab` que haga polling a `/admin/core/chat/messages/{phone}` usando `client.phone_number`. Mostrar mensajes en orden cronologico (solo lectura, sin envio). Mostrar "Sin conversaciones" si no hay mensajes.
- Cada tab DEBE cargar independientemente (fault-tolerant): un tab fallando NO debe afectar a los otros.
- Todos los componentes DEBEN seguir el tema dark existente (bg-white/[0.03], text-white, border-white/[0.06]).

### SHOULD

- Usar `Promise.allSettled` para carga inicial si se pre-cargan datos de multiples tabs.
- Mostrar skeleton/loading state por tab individual.
- Cachear el `lead_id` vinculado para evitar buscarlo en cada cambio de tab.

## Current State (lo que esta roto)

En `ClientDetailView.tsx`:

- **Linea 196-199** (Tab Notas): Renderiza `<p>{t('client360.notes_placeholder')}</p>` — texto estatico, sin funcionalidad.
- **Linea 200-203** (Tab Llamadas): Renderiza `<p>{t('client360.calls_placeholder')}</p>` — texto estatico, sin funcionalidad.
- **Linea 204-207** (Tab WhatsApp): Renderiza `<p>{t('client360.whatsapp_placeholder')}</p>` — texto estatico, sin funcionalidad.

Existen estados `clientNotes` y `clientCalls` declarados en lineas 20-21 pero NUNCA se usan ni se cargan.

## Solution

### 1. ClientNotesTab.tsx

```
Props: { clientId: string; clientPhone: string }

1. Al montar, buscar lead vinculado: GET /admin/core/crm/leads?phone={clientPhone}
2. Si encuentra lead → renderizar <LeadNotesThread leadId={lead.id} />
3. Si NO encuentra lead → mostrar mensaje "No hay lead vinculado a este cliente"
4. Manejar error de API con mensaje generico
```

### 2. ClientCallsTab.tsx

```
Props: { clientId: string }

1. Al montar, fetch: GET /admin/core/crm/agenda/events?client_id={clientId}
2. Renderizar lista de llamadas: fecha, vendedor (seller_name), estado, notas
3. Boton "Nueva llamada" que abre AgendaEventForm en modal/inline con client_id pre-seteado
4. Tras crear llamada, refrescar la lista
```

### 3. ClientWhatsAppTab.tsx

```
Props: { phoneNumber: string }

1. Al montar, fetch: GET /admin/core/chat/messages/{phoneNumber}
2. Renderizar mensajes en orden cronologico (burbuja estilo chat, solo lectura)
3. Polling cada 30s para mensajes nuevos (useEffect + setInterval)
4. Si no hay mensajes o error 404 → "Sin conversaciones"
```

### 4. Modificar ClientDetailView.tsx

- Reemplazar los 3 bloques placeholder (lineas 196-207) con los nuevos componentes.
- Pasar props necesarios: `clientId={client.id}`, `clientPhone={client.phone_number}`.
- Eliminar estados no usados `clientNotes`, `clientCalls`, `tabLoading` (lineas 20-22).

## Files to Modify

| File | Action |
|------|--------|
| `frontend_react/src/modules/crm_sales/views/ClientDetailView.tsx` | Modify — reemplazar placeholders con componentes, limpiar estados muertos |
| `frontend_react/src/modules/crm_sales/components/client360/ClientNotesTab.tsx` | Create |
| `frontend_react/src/modules/crm_sales/components/client360/ClientCallsTab.tsx` | Create |
| `frontend_react/src/modules/crm_sales/components/client360/ClientWhatsAppTab.tsx` | Create |

## API Endpoints (ya existentes)

| Endpoint | Uso |
|----------|-----|
| `GET /admin/core/crm/leads?phone={phone}` | Buscar lead vinculado al cliente |
| `GET /admin/core/crm/leads/{id}/notes` | Notas del lead (usado internamente por LeadNotesThread) |
| `POST /admin/core/crm/leads/{id}/notes` | Agregar nota (usado internamente por LeadNotesThread) |
| `GET /admin/core/crm/agenda/events?client_id={id}` | Eventos de agenda del cliente |
| `GET /admin/core/chat/messages/{phone}` | Mensajes WhatsApp por telefono |

## Acceptance Criteria

- [ ] Tab Notas muestra notas reales del lead vinculado, o mensaje "No hay lead vinculado" si no existe relacion.
- [ ] Tab Notas permite agregar nuevas notas (via LeadNotesThread).
- [ ] Tab Llamadas muestra lista de llamadas con fecha, vendedor, estado y notas.
- [ ] Tab Llamadas permite agregar nueva llamada via AgendaEventForm.
- [ ] Tab WhatsApp muestra mensajes reales en orden cronologico.
- [ ] Tab WhatsApp hace polling cada 30s para mensajes nuevos.
- [ ] Tab WhatsApp muestra "Sin conversaciones" cuando no hay mensajes.
- [ ] Fallo en un tab NO rompe los otros tabs (fault-tolerant).
- [ ] Cada tab tiene su propio loading state.
- [ ] Los estados muertos (`clientNotes`, `clientCalls`, `tabLoading`) fueron eliminados de ClientDetailView.
- [ ] UI consistente con el tema dark del CRM.

## Testing Strategy

- **Unit tests**: Cada componente de tab con mocks de API (msw o vi.mock).
  - ClientNotesTab: test con lead encontrado, sin lead, error de API.
  - ClientCallsTab: test con llamadas, sin llamadas, crear nueva llamada.
  - ClientWhatsAppTab: test con mensajes, sin mensajes, polling.
- **Integration test**: ClientDetailView renderiza correctamente cada tab al hacer click.
- **Error boundary test**: Simular fallo de API en un tab, verificar que los otros tabs siguen funcionando.
