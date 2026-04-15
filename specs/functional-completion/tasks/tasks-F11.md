# TASKS F-11: Migration Pages Backend Verification

## Verification Tasks (no code changes unless bugs found)

### Chat Interno
- [ ] 1. Verify GET /admin/core/internal-chat/canales returns real channels from DB
- [ ] 2. Verify POST /admin/core/internal-chat/mensajes inserts in chat_mensajes table
- [ ] 3. Verify DM access control (vendedor cant read others DMs, CEO can)
- [ ] 4. Verify tenant isolation (tenant A cant see tenant B messages)

### Daily Check-in
- [ ] 5. Verify POST /admin/core/checkin/ creates record in daily_checkins
- [ ] 6. Verify duplicate check-in same day returns 409
- [ ] 7. Verify GET /admin/core/checkin/ceo/today returns all sellers with LEFT JOIN

### Vendor Tasks
- [ ] 8. Verify GET /admin/core/crm/vendor-tasks/mine returns 3 sections
- [ ] 9. Verify PATCH completar only works for own tasks (403 for others)
- [ ] 10. Verify pending-count only counts admin-assigned incomplete tasks

### Manuales
- [ ] 11. Verify CRUD respects role restrictions (only CEO/secretary can write)
- [ ] 12. Verify FTS search with plainto_tsquery works

### Plantillas
- [ ] 13. Verify variable extraction regex works with edge cases
- [ ] 14. Verify uso_count atomic increment

### Drive
- [ ] 15. Verify file upload writes to disk and registers in DB
- [ ] 16. Verify cascade delete removes physical files
- [ ] 17. Verify tenant isolation on file access

## Fix Tasks (only if verification finds bugs)
- [ ] 18. Fix any endpoint that returns mock/hardcoded data
- [ ] 19. Fix any missing tenant_id filter
- [ ] 20. Add missing error handling
