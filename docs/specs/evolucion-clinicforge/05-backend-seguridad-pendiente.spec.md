# SPEC: Backend, Database & Seguridad — Pendientes vs ClinicForge

**Fecha:** 2026-03-28
**Status:** DOCUMENTADO — pendiente de implementación
**Prioridad:** Alta (infraestructura crítica)

---

## 1. Database — SQLAlchemy Models (NO EXISTE)

### Estado actual
- CRM VENTAS usa **patches idempotentes en db.py** (16 patches)
- No existe `models.py` con clases SQLAlchemy ORM
- Alembic configurado pero solo tiene baseline vacía

### Lo que ClinicForge tiene
- `orchestrator_service/models.py` con 31 clases SQLAlchemy 2.0
- Alembic con 6 migrations reales (001→006)
- `alembic upgrade head` automático en startup via `start.sh`

### Qué implementar
1. Crear `orchestrator_service/models.py` con ~34 modelos ORM:
   - CRM Core: leads, lead_statuses, lead_status_transitions, lead_status_history, lead_tasks, sellers, seller_metrics_cache, seller_agenda_events, opportunities, sales_transactions
   - Infrastructure: tenants, users, credentials, meta_tokens, automation_rules, notification_settings, notifications, inbound_messages
   - Chat: chat_conversations, chat_messages
   - Marketing: meta_ad_insights, attributed_sales, utm_tracking_events
2. Crear migration Alembic real para formalizar schema
3. Agregar auto-run `alembic upgrade head` en startup

---

## 2. Seguridad — Fernet Encryption (NO EXISTE)

### Estado actual
- Credenciales (API keys, tokens) se guardan en tabla `credentials` pero **sin encriptación**
- No hay `CREDENTIALS_FERNET_KEY` en environment variables

### Lo que ClinicForge tiene
- `core/credentials.py` con Fernet symmetric encryption
- `get_tenant_credential()` y `set_tenant_credential()` con encrypt/decrypt
- Variable `CREDENTIALS_FERNET_KEY` requerida

### Qué implementar
1. Crear `orchestrator_service/core/credentials.py`
2. Funciones: `encrypt_credential(value)`, `decrypt_credential(value)`
3. Migrar credenciales existentes a encrypted
4. Agregar `CREDENTIALS_FERNET_KEY` a `.env`

---

## 3. Security Headers Middleware (PARCIAL)

### Estado actual
- CORS configurado
- Rate limiting básico con slowapi
- JWT + X-Admin-Token auth

### Lo que ClinicForge tiene
- CSP (Content-Security-Policy)
- HSTS (Strict-Transport-Security)
- X-Frame-Options
- X-Content-Type-Options
- Referrer-Policy
- Global exception handler para CORS stability

### Qué implementar
1. Middleware de security headers en `main.py`
2. Global exception handler que no rompa CORS
3. Rate limiting más granular por endpoint

---

## 4. Nova WebSocket Handler (NO EXISTE)

### Estado actual
- `NovaWidget.tsx` frontend creado (conecta a `/public/nova/voice`)
- `nova_tools_crm.py` con 20 tools implementadas
- **No existe el endpoint WebSocket** en main.py

### Lo que ClinicForge tiene
- WebSocket handler en `main.py` (~line 4713)
- Conecta a OpenAI Realtime API
- Bidireccional: browser ↔ backend ↔ OpenAI
- Session management con Redis
- Tool dispatch via `execute_nova_tool()`

### Qué implementar
1. Ruta WebSocket `@app.websocket("/public/nova/voice")`
2. Validar JWT del query param
3. Conectar a OpenAI Realtime API
4. Relay audio bidireccional
5. Dispatch tool calls a `execute_nova_crm_tool()`
6. System prompt de ventas (Spanish voseo, execute-first)

---

## 5. ROI Attribution System (NO EXISTE — Spec 07)

### Estado actual
- Meta OAuth funciona (connect/disconnect)
- Campos meta_lead_id, meta_campaign_id en leads
- No hay sync de campañas ni cálculo de ROI

### Qué implementar
- Ver spec completa: `docs/specs/07-roi-attribution-rag.spec.md`
- `attributed_sales` table
- `MetaAdsClient.sync_campaigns()`
- Background job de enrichment cada 12h
- Frontend: Marketing Hub con ROI dashboard

---

## 6. Knowledge Base RAG (NO EXISTE — Spec 07)

### Estado actual
- No hay pgvector, no hay embeddings, no hay document upload

### Qué implementar
- Ver spec completa: `docs/specs/07-roi-attribution-rag.spec.md`
- pgvector extension en PostgreSQL
- `kb_collections`, `kb_documents`, `kb_chunks` tables
- `EmbeddingService` con text-embedding-3-small
- `RAGService` para inyectar contexto en el agente
- Shadow RAG: indexar conversaciones exitosas
- Frontend: KnowledgeBaseView.tsx

---

## 7. Socket.IO en Agenda (NO EXISTE en CRM)

### Estado actual
- La agenda CRM no tiene real-time updates
- ClinicForge emite: NEW_APPOINTMENT, APPOINTMENT_UPDATED, APPOINTMENT_DELETED, PAYMENT_CONFIRMED

### Qué implementar
1. Agregar Socket.IO listeners en CrmAgendaView
2. Emitir eventos desde endpoints de agenda
3. Auto-refresh al recibir evento

---

## 8. Google Calendar Sync (PARCIAL)

### Estado actual
- Service account auth existe
- Sync básica funciona
- No hay bloques de GCal en la agenda

### Qué implementar
1. Fetch Google Calendar blocks
2. Render en FullCalendar como eventos bloqueados
3. Sync bidireccional completa

---

## Orden de implementación sugerido

| Prioridad | Feature | Esfuerzo | Impacto |
|-----------|---------|----------|---------|
| 1 | Nova WebSocket handler | 1 día | Activa Nova Voice |
| 2 | Socket.IO en agenda | 2h | Real-time updates |
| 3 | Fernet encryption | 3h | Seguridad |
| 4 | Security headers | 1h | Seguridad |
| 5 | SQLAlchemy models.py | 1 día | Mantenibilidad |
| 6 | ROI Attribution | 3 días | Marketing intelligence |
| 7 | Knowledge Base RAG | 5 días | IA avanzada |
| 8 | Google Calendar blocks | 3h | UX |
