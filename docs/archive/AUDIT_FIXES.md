# 🔧 AUDIT FIXES — CRM VENTAS
**Fecha Audit:** 2026-02-25 | **Clarify completado:** 2026-02-25 03:21

> Documento generado por Antigravity tras audit completo + ronda de clarificación.
> Ejecutar fixes en orden de fases.

---

## ⚡ Clarificaciones Incorporadas

| # | Pregunta | Respuesta | Impacto en Plan |
|---|---|---|---|
| 1 | ¿Nombre tabla clientes? | `clients` (confirmado en routes.py) | A-01: usar `FROM clients` |
| 2 | ¿Vista Aprobaciones activa? | Sí, gestiona vendedores + aprobaciones. Bug: no se puede registrar | **Nuevo fix B-04** agregado |
| 3 | ¿CHECK constraint en `source`? | No. Columna es `TEXT` libre (patch_008) | Migración SQL es segura |
| 4 | ¿Modo crear lead desde URL? | Sí, hay botón en la página de Leads | C-03: solo bloquear URL inválida, respetar botón |
| 5 | ¿Multi-tenant en producción? | 1 tenant hoy, muchos a futuro | B-03: implementar ahora para evitar deuda |

> [!NOTE]
> **Descubrimiento post-clarify:** El endpoint `GET /crm/stats/summary` **YA EXISTE** en `routes.py` (línea ~517). El fix A-01 solo requiere corrección en el **frontend** (`CrmDashboardView.tsx`), no crear nada en el backend.

---

## ❌ CRÍTICO — Fix Inmediato

### A-01 — CrmDashboardView: URL del endpoint de stats incorrecto

**Problema:** `CrmDashboardView.tsx` llama a `/admin/core/crm/stats/summary` pero el parámetro `range` se pasa hardcodeado en la URL en vez de como query param. El endpoint existe en el backend.

**Archivo:** `frontend_react/src/views/CrmDashboardView.tsx` — línea 142

**Fix:**
```diff
- const statsRes = await api.get(`/admin/core/crm/stats/summary?range=${range}`);
+ const statsRes = await api.get('/admin/core/crm/stats/summary', { params: { range } });
```

Adaptar la UI para consumir los campos del response:
`total_leads`, `leads_nuevos`, `clientes_activos`, `reuniones_agendadas`, `conversion_rate`, `growth_data`

**Criterios:**
- [ ] Dashboard CRM carga stats sin errores
- [ ] Widget muestra números reales del DB
- [ ] `?range=weekly` y `?range=monthly` funcionan

---

## ⚠️ IMPORTANTES

### B-01 — UserApprovalView: endpoints dental inactivos → 404

**Problema:** La vista llama a `/admin/professionals/by-user/{id}`, `/admin/professionals`, etc. El módulo dental no está activo en modo CRM → 404.

**Archivos afectados:** `frontend_react/src/views/UserApprovalView.tsx`

**Fix:** Reemplazar todos los endpoints de professionals por sellers:

| Endpoint Actual | Correcto |
|---|---|
| `GET /admin/professionals/by-user/{id}` | `GET /admin/core/crm/sellers/by-user/{id}` |
| `POST /admin/professionals` | `POST /admin/core/crm/sellers` |
| `PUT /admin/professionals/{id}` | `PUT /admin/core/crm/sellers/{id}` |
| `GET /admin/professionals/{id}/analytics` | `GET /admin/core/crm/sellers/{id}/analytics` |

Renombrar tipo `ProfessionalRow` → `SellerRow` dentro de la vista. Verificar que los campos del seller response (`commission_rate`, `quota`, etc.) sean compatibles con lo que renderiza la UI.

**Criterios:**
- [ ] Página Aprobaciones carga sin errores 404
- [ ] Lista de vendedores se muestra al seleccionar un usuario
- [ ] CRUD vendedor funciona desde esta vista
- [ ] Aprobación de usuarios (cambio de status) sin regresión

---

### B-02 — Tab "Mensajes" vacía: source 'whatsapp' ≠ 'whatsapp_inbound'

**Problema:** `main.py` línea 170 crea leads con `source = 'whatsapp'`. `LeadsView.tsx` filtra tab "Mensajes" por `source === 'whatsapp_inbound'` → nunca coincide → tab vacía.

**Archivos:** `orchestrator_service/main.py` + SQL migration

**Fix backend:**
```diff
# main.py línea 170
- await db.ensure_lead_exists(tenant_id, from_number, customer_name=customer_name, source="whatsapp")
+ await db.ensure_lead_exists(tenant_id, from_number, customer_name=customer_name, source="whatsapp_inbound")
```

**SQL Migration** (ejecutar en producción **antes** del deploy):
```sql
-- Sin riesgo: columna source es TEXT sin CHECK constraint
UPDATE leads SET source = 'whatsapp_inbound', updated_at = NOW()
WHERE source = 'whatsapp';

-- Verificar resultado:
SELECT source, COUNT(*) FROM leads GROUP BY source ORDER BY source;
```

**Criterios:**
- [ ] Nuevos leads de WA se crean con `source = 'whatsapp_inbound'`
- [ ] Tab "Mensajes" muestra los leads de WhatsApp
- [ ] Migración SQL aplicada sin pérdida de datos
- [ ] Tabs "Todos" y "Apify" siguen funcionando

---

### B-03 — Chat Send: business_number hardcodeado (multi-tenant)

**Problema:** `admin_routes.py` línea 117 usa `os.getenv("YCLOUD_Phone_Number_ID")` fijo. En multi-tenant, el mensaje sale siempre desde el mismo número, ignorando el `bot_phone_number` de cada tenant.

**Archivo:** `orchestrator_service/admin_routes.py`

**Fix:**
```diff
# Función send_chat_message, antes de background_tasks.add_task(...)
- business_number = os.getenv("YCLOUD_Phone_Number_ID") or "default"
+ tenant_row = await db.pool.fetchrow(
+     "SELECT bot_phone_number FROM tenants WHERE id = $1", payload.tenant_id
+ )
+ business_number = (
+     tenant_row["bot_phone_number"]
+     if tenant_row and tenant_row["bot_phone_number"]
+     else os.getenv("YCLOUD_Phone_Number_ID") or ""
+ )
+ if not business_number:
+     raise HTTPException(status_code=400, detail="No hay número de WhatsApp configurado para este tenant.")
```

**Criterios:**
- [ ] Mensaje enviado desde el `bot_phone_number` del tenant correcto
- [ ] Error claro si el tenant no tiene número configurado
- [ ] Sin regresión en tenant único actual

---

### B-04 — Registro de usuarios falla en modo CRM *(nuevo — detectado en clarify)*

**Problema:** `auth_routes.py` línea 106: al registrarse con role `professional`, `secretary`, `setter` o `closer`, intenta `INSERT INTO professionals` (tabla del módulo dental). En producción CRM, esta tabla puede no existir o estar vacía → error 500 silencioso.

**Causa raíz:** El sistema de registro no fue adaptado al niche CRM. En CRM, los "professionals" son "sellers".

**Archivo:** `orchestrator_service/auth_routes.py`

**Fix:**
1. Cambiar los roles aceptados en `UserRegister`: en modo CRM los roles son `seller`, `ceo`, `admin`.
2. Cuando el role es `seller`: hacer `INSERT INTO sellers (tenant_id, user_id, ...)` en lugar de `INSERT INTO professionals`.
3. Agregar manejo de error con mensaje útil si falla.

```diff
# auth_routes.py — register()
- if payload.role in ("professional", "secretary", "setter", "closer"):
+ CRM_ROLES = ("seller", "closer", "setter", "secretary")
+ if payload.role in CRM_ROLES:
      if payload.tenant_id is None:
          raise HTTPException(...)
      # En vez de INSERT INTO professionals:
+     await db.pool.execute("""
+         INSERT INTO sellers (user_id, tenant_id, first_name, last_name, email, is_active, created_at, updated_at)
+         VALUES ($1, $2, $3, $4, $5, FALSE, NOW(), NOW())
+         ON CONFLICT (user_id) DO NOTHING
+     """, uid, tenant_id, first_name, last_name, payload.email)
```

> [!IMPORTANT]
> Verificar el schema exacto de la tabla `sellers` en DB antes de escribir el INSERT.

**Criterios:**
- [ ] Un usuario puede registrarse con role `seller` sin error 500
- [ ] El registro queda en estado `pending` esperando aprobación del CEO
- [ ] El CEO puede aprobar desde `/aprobaciones` y el vendor aparece en la lista de sellers

---

## 🟡 MEJORAS

### C-01 — Urgencias: lógica vacía (devuelve cualquier lead)

**Archivo:** `orchestrator_service/admin_routes.py` — `GET /chat/urgencies`

**Fix SQL:**
```sql
-- Cambiar query en get_recent_urgencies:
SELECT l.id, TRIM(COALESCE(l.first_name,'') || ' ' || COALESCE(l.last_name,'')) as lead_name,
       l.phone_number as phone, 'URGENT' as urgency_level,
       'Intervención humana activa' as reason, l.updated_at as timestamp
FROM leads l
WHERE l.tenant_id = $1 AND l.human_handoff_requested = TRUE
ORDER BY l.updated_at DESC NULLS LAST LIMIT $2
```

**Criterios:**
- [ ] Solo muestra leads con `human_handoff_requested = TRUE`
- [ ] Lista vacía cuando no hay intervenciones activas

---

### C-02 — Mark Read: no persiste en DB

**Archivo:** `orchestrator_service/admin_routes.py` — `PUT /chat/sessions/{phone}/read`

**Fix:**
```python
norm_phone = normalize_phone(phone)
await db.pool.execute("""
    UPDATE leads SET updated_at = NOW()
    WHERE tenant_id = $1 AND (phone_number = $2 OR phone_number = $3)
""", tenant_id, norm_phone, phone)
return {"status": "ok", "phone": phone, "tenant_id": tenant_id}
```

---

### C-03 — LeadDetailView: crea leads en blanco al navegar a URL inválida

**Archivo:** `frontend_react/src/modules/crm_sales/views/LeadDetailView.tsx`

**Fix:** Si el GET por ID retorna 404, mostrar pantalla "Lead no encontrado" con botón Volver. No ejecutar lógica de creación. La creación solo debe dispararse desde el botón explícito en `/crm/leads`.

---

### C-04 — Vistas legacy sin rutas (deuda técnica dental)

**Archivos:** `Logs.tsx`, `Setup.tsx`, `Stores.tsx`, `Tools.tsx`

**Fix:** Agregar en primera línea de cada archivo:
```tsx
// @legacy — Módulo dental. No montada en App.tsx (modo: crm_sales). Mantener para eventual reactivación del niche dental.
```

---

## 📋 Checklist de Ejecución

```
FASE 1 — Crítico
[ ] A-01: Fix CrmDashboardView stats URL (frontend, ~10 min)

FASE 2 — Importantes
[ ] B-01: Fix UserApprovalView professionals → sellers (frontend, ~20 min)
[ ] B-02: SQL migration + main.py source fix (backend + DB, ~15 min)
[ ] B-03: Fix chat/send business_number (backend, ~10 min)
[ ] B-04: Fix registro en modo CRM (backend, ~20 min) ← NUEVO

FASE 3 — Mejoras
[ ] C-01: Fix urgencias query (backend, ~5 min)
[ ] C-02: Fix mark-read DB persist (backend, ~5 min)
[ ] C-03: Fix LeadDetailView 404 guard (frontend, ~10 min)
[ ] C-04: Legacy comments (frontend, ~5 min)

FASE 4 — Validación
[ ] npm run build (0 errores TS)
[ ] Smoke test manual en todas las páginas
[ ] git commit + push
```

---

## 🗃️ Archivos Afectados (resumen)

| Fix | Archivo | Tipo |
|---|---|---|
| A-01 | `frontend_react/src/views/CrmDashboardView.tsx` | Frontend |
| B-01 | `frontend_react/src/views/UserApprovalView.tsx` | Frontend |
| B-02 | `orchestrator_service/main.py` + SQL | Backend + DB |
| B-03 | `orchestrator_service/admin_routes.py` | Backend |
| B-04 | `orchestrator_service/auth_routes.py` | Backend |
| C-01 | `orchestrator_service/admin_routes.py` | Backend |
| C-02 | `orchestrator_service/admin_routes.py` | Backend |
| C-03 | `frontend_react/src/modules/crm_sales/views/LeadDetailView.tsx` | Frontend |
| C-04 | `Logs.tsx`, `Setup.tsx`, `Stores.tsx`, `Tools.tsx` | Frontend |

---

*Generado por Antigravity © 2026-02-25 | Basado en audit_report.md + audit_fixes.spec.md*
