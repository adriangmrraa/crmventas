# TASKS F-12: Dashboard Enhancements

## Backend Tasks
- [ ] 1. Agregar fields trend al response de GET /admin/core/crm/stats/summary (total_leads_trend, active_leads_trend, etc.) — calcular comparando periodo actual vs anterior
- [ ] 2. Emitir Socket.IO event `crm_activity` desde endpoints de leads y agenda

## Frontend Tasks
- [ ] 3. Quick Action buttons bar (4 botones) en CrmDashboardView header
- [ ] 4. Modal "Nuevo Lead" (phone, name, source) → POST /admin/core/crm/leads + invalidar stats
- [ ] 5. Modal "Nueva Llamada" (lead selector, resultado) → POST agenda events
- [ ] 6. Modal "Nueva Cita" (lead, fecha/hora) → POST agenda events
- [ ] 7. Activity Feed section: Socket.IO listener + fallback a team-activity/feed
- [ ] 8. Checkin Widget compacto: GET /admin/core/checkin/today + inline status
- [ ] 9. i18n keys para quick actions y feed

## Verification
- [ ] 10. Quick actions crean registros reales en DB
- [ ] 11. Activity feed se actualiza en tiempo real
- [ ] 12. Trends muestran datos del API (no hardcoded)
