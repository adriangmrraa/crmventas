# DESIGN F-12: Dashboard Enhancements

## Decisiones Arquitectónicas
- CrmDashboardView ya funciona con KPIs reales y charts
- Bug fix de trends hardcoded ya aplicado (ahora usa stats.total_leads_trend del API)
- Backend necesita retornar trend fields — o calcularlos en frontend comparando periodos
- Quick Actions: modales inline, NO navegación
- Activity Feed: Socket.IO event `crm_activity` — nuevo event a emitir desde backend
- Checkin Widget: reutilizar lógica de DailyCheckinView en formato compacto

## Quick Actions (4 botones)
- Nuevo Lead → modal con: phone, first_name, source → POST /admin/core/crm/leads
- Nueva Llamada → modal con: lead selector, duración, resultado → POST /admin/core/crm/agenda/events
- Nuevo Deal → modal con: lead selector, monto, etapa → POST /admin/core/crm/leads/{id}/status (move to deal stage)
- Nueva Cita → modal con: lead, fecha/hora → POST /admin/core/crm/agenda/events

## Activity Feed
- Suscribir a Socket.IO event `crm_activity` al montar
- Fallback: GET /admin/core/team-activity/feed?limit=20 al mount
- Mostrar últimos 20 eventos con icon + actor + target + timestamp relativo

## Checkin Widget
- GET /admin/core/checkin/today al montar
- Si no hay checkin: botón "Iniciar jornada"
- Si activo: badge "En jornada" + llamadas planeadas
- Si completado: badge "Jornada cerrada" + cumplimiento %

## Backend
- Emitir `crm_activity` event desde admin_routes.py en: create lead, change status, create appointment
- O: reutilizar team-activity feed endpoint como source
