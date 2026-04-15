# MASTER PROPOSAL: Frontend Gaps — Hacer funcional lo que es placeholder

**Estado**: DRAFT v2 — Análisis profundo completado, pendiente review
**Fecha**: 2026-04-15
**Scope**: 8 gaps funcionales (7 frontend + 1 backend)

---

## Análisis completo

Se analizaron **35 páginas** del frontend y **200+ endpoints** del backend con 3 agentes en paralelo:
- Agent 1: Verificó que TODOS los endpoints del backend existen y tienen implementación real
- Agent 2: Mapeó RBAC por rol (CEO/setter/closer/secretary/professional) — bien implementado
- Agent 3: Verificó data flows (selectors, modals, auth headers) — 95% funcional

**Resultado**: 27 páginas COMPLETAMENTE funcionales, 8 gaps puntuales.

**Hallazgo crítico**: 1 feature del frontend (CSV Import) tiene UI completa pero los 3 endpoints de backend NO EXISTEN.

---

## Spec List

| # | Spec | Página | Problema | Esfuerzo | Tipo |
|---|------|--------|----------|----------|------|
| FIX-01 | Client 360° Tabs | ClientDetailView | 3 tabs son placeholder text | ALTO | Frontend |
| FIX-02 | Dashboard Chart CRM | DashboardView | Chart "coming soon", botones rotos | MEDIO | Frontend |
| FIX-03 | Kanban Filters + Pagination | KanbanPipelineView | Sin filtros, carga 500 leads | MEDIO | Frontend |
| FIX-04 | Supervisor Alerts | SupervisorDashboard | Alertas hardcoded | MEDIO | Frontend+API |
| FIX-05 | Internal Chat Media | InternalChatView | Sin upload de archivos | MEDIO | Frontend |
| FIX-06 | Meta Leads Cleanup | MetaLeadsView | Demo data fallback confuso | BAJO | Frontend |
| FIX-07 | HSM Stats Fix | MetaTemplatesView | Conversion 85% hardcoded | BAJO | Frontend |
| FIX-08 | CSV Import Backend | LeadsView/LeadImportModal | Frontend listo, 3 endpoints 404 | ALTO | Backend |

---

## Detalle por Spec

### FIX-01: Client 360° Tabs (ALTA prioridad)

**Problema**: ClientDetailView tiene 5 tabs pero solo 2 funcionan (Data, Drive). Los tabs Notas, Llamadas y WhatsApp muestran texto placeholder.

**Solución**:
- Tab Notas: Reutilizar `LeadNotesThread` existente adaptado para clients (misma API `/admin/core/crm/leads/{id}/notes` usando el lead vinculado al client)
- Tab Llamadas: Listar eventos de CrmAgenda filtrados por client_id + mini-form para registrar llamada
- Tab WhatsApp: Polling a `/admin/core/chat/messages/{phone}` usando el phone del client, render de mensajes (read-only)

**Backend necesario**: El backend de notas y chat YA EXISTE. Solo falta wiring en frontend.

**Archivos**: `ClientDetailView.tsx` (modificar tabs), posiblemente crear `ClientNotesTab.tsx`, `ClientCallsTab.tsx`, `ClientWhatsAppTab.tsx`

---

### FIX-02: Dashboard Chart CRM (MEDIA prioridad)

**Problema**: DashboardView (la versión unificada) muestra "Chart coming soon" para CRM mode. Dos botones ("Ver todos" y "Ver lead") no tienen onClick.

**Solución**:
- Implementar chart real usando Recharts (como ya se hace en dental mode del mismo archivo)
- Agregar `onClick={() => navigate('/crm/leads')}` al botón "Ver todos"
- Agregar `onClick={() => navigate(`/crm/leads/${lead.id}`)}` al botón "Ver lead"
- Calcular trends reales desde la API en vez de hardcodear "+12%"

**Backend necesario**: Endpoint `/admin/core/crm/stats/summary` YA retorna `revenue_leads_trend`. Solo falta usarlo.

**Archivos**: `DashboardView.tsx` (líneas 343-349 chart, 385 y 436 botones)

---

### FIX-03: Kanban Filters + Pagination (MEDIA prioridad)

**Problema**: Pipeline carga 500 leads sin filtros ni paginación. En producción con muchos leads es lento.

**Solución**:
- Agregar filtro por seller (dropdown)
- Agregar filtro por valor mínimo
- Agregar search por nombre/teléfono
- Implementar virtual scrolling o paginación por columna
- Reducir límite inicial a 100 leads

**Backend necesario**: El endpoint `/admin/core/crm/leads` YA soporta filtros (`assigned_seller_id`, `status`, `search`). Solo falta usarlos.

**Archivos**: `KanbanPipelineView.tsx`

---

### FIX-04: Supervisor Alerts (MEDIA prioridad)

**Problema**: Las 3 cards de alertas están hardcoded: "0 Intervenciones req.", "Buscando patrones...", sin lógica real.

**Solución**:
- Card 1: Contar intervenciones humanas reales del día via API
- Card 2: Detectar conversaciones con sentiment negativo o keywords de alarma
- Card 3: Mostrar métricas de respuesta (tiempo promedio, tasa de resolución)
- Agregar filtro por canal y por fecha

**Backend necesario**: Endpoint nuevo `GET /admin/core/supervisor/alerts` que agrupe métricas de intervención.

**Archivos**: `SupervisorDashboard.tsx`, nuevo endpoint en backend

---

### FIX-05: Internal Chat Media (MEDIA prioridad)

**Problema**: InternalChatView solo soporta texto. Las notification cards de llamadas y tareas son stubs visuales sin integración.

**Solución**:
- Agregar botón de adjuntar archivo (reutilizar DriveExplorer upload pattern)
- Conectar notification cards a datos reales (cuando se agenda una llamada o se asigna una tarea, el servicio ya publica en el chat)
- Agregar preview de imágenes inline

**Backend necesario**: Endpoint upload ya existe en Drive. Para chat, agregar tipo de mensaje `file` con `metadata.file_url`.

**Archivos**: `InternalChatView.tsx`, `internal_chat_service.py` (agregar tipo file)

---

### FIX-06: Meta Leads Cleanup (BAJA prioridad)

**Problema**: Cuando no hay leads reales de Meta, muestra 3 demo leads hardcoded sin indicar que son demo. Confunde al usuario.

**Solución**:
- Eliminar demo data fallback
- Mostrar empty state claro: "No hay leads de Meta Ads. Conectá tu cuenta desde Integraciones."
- Agregar link directo a IntegrationsView

**Backend necesario**: Ninguno.

**Archivos**: `MetaLeadsView.tsx` (líneas 35-75 eliminar, línea 151-157 cambiar)

---

### FIX-07: HSM Stats Fix (BAJA prioridad)

**Problema**: Conversion rate muestra 85% hardcoded. Timezone selector está disabled.

**Solución**:
- Calcular conversion rate real desde los logs (sent vs delivered/read)
- Habilitar timezone selector o eliminarlo de la UI
- Motor status debería verificar realmente si el motor está corriendo

**Backend necesario**: El endpoint `/crm/marketing/automation-logs` ya retorna los datos. Solo falta calcular en frontend.

**Archivos**: `MetaTemplatesView.tsx` (líneas 116-130 stats cards)

---

## Orden de implementación recomendado

```
1. FIX-02 (Dashboard) — rápido, alto impacto visual
2. FIX-06 (Meta Leads) — rápido, eliminar confusión
3. FIX-07 (HSM Stats) — rápido, calcular en frontend
4. FIX-01 (Client 360°) — el más grande, alto valor
5. FIX-03 (Kanban) — performance improvement
6. FIX-05 (Chat Media) — nice to have
7. FIX-04 (Supervisor) — requiere backend nuevo
```

---

## Lo que NO se toca

- 28 páginas funcionales — no se modifican
- Backend (orchestrator_service/) — ya está correcto
- Tests existentes — ya pasan (106)
- Design system — ya migrado a violeta #8F3DFF
