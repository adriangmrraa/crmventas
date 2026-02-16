---
description: Guía paso a paso para construir y validar la versión estable del CRM VENTAS (núcleo, módulo CRM, agenda, chats, frontend).
---

# Workflow: Construir versión estable (Fusion Stable) – CRM VENTAS

Este workflow orienta el desarrollo y validación del **CRM VENTAS**. Todo el trabajo es dentro de la carpeta **CRM VENTAS**. Usar junto con la skill [Fusion_Architect](../skills/Fusion_Architect/SKILL.md) cuando se integren piezas de otros proyectos.

---

## 1. Antes de empezar

- [ ] Revisar la documentación del proyecto en **CRM VENTAS/docs/**.
- [ ] El código estable se desarrolla dentro de **CRM VENTAS** (frontend_react, orchestrator_service, etc.).

---

## 2. Fases recomendadas

### Fase 1: Núcleo backend (Orchestrator + DB + Auth)

1. **Base de código**
   - Orchestrator_service con **Maintenance Robot** (db.py) y parches idempotentes.

2. **Multi-tenancy y auth**
   - JWT + X-Admin-Token.
   - Resolución de `tenant_id` desde usuario/BD en todas las rutas.

3. **Credenciales (Vault)**
   - Credenciales por tenant (OpenAI, Google Calendar) en BD cifradas.
   - No usar env global para agentes.

4. **Checklist Fase 1**
   - [ ] Login/registro con tenant.
   - [ ] Todas las queries filtran por `tenant_id`.
   - [ ] Credenciales por tenant para IA y calendar.

---

### Fase 2: Módulo CRM (Leads, Pipeline, Sellers)

1. **Modelos y rutas**
   - modules/crm_sales/ (models, routes), tabla leads, stages, assigned_seller_id.

2. **Tools del agente**
   - Registrar tools de CRM; agente usando credenciales del tenant (Vault).

3. **Checklist Fase 2**
   - [ ] CRUD leads por tenant.
   - [ ] Pipeline con etapas.
   - [ ] Asignación a vendedores.
   - [ ] Agente con herramientas de CRM registradas.

---

### Fase 3: Agenda y calendario

- Híbrido por tenant (local | google), Socket.IO, tools de reserva.
- **Checklist:** Agenda local y/o Google, tools de agenda, Socket.IO en frontend.

---

### Fase 4: Chats y omnichannel

- Sesiones por tenant, human override 24h, WhatsApp (YCloud/relay), handoff humano.
- **Checklist:** Listado chats, envío/recepción, human handoff.

---

### Fase 5: Frontend unificado

- Shell React 18 + Vite + Tailwind, AuthContext, Sidebar por nicho, scroll isolation.
- Vistas: Dashboard, Leads, Lead detail, Pipeline, Chats, Agenda, Config, Analytics, Staff.
- i18n es/en/fr.

---

## 3. Criterios de “estable”

- Todas las consultas filtran por `tenant_id`.
- No uso de `os.getenv("OPENAI_API_KEY")` para agentes (solo Vault/tenant).
- Frontend con scroll isolation e i18n.
- Documentación actualizada (README, API_REFERENCE) dentro de CRM VENTAS.
- Workflows new_feature, bug_fix, specify, plan utilizables.

---

## 4. Comandos útiles

| Acción | Referencia |
|--------|-------------|
| Especificar feature | Workflow [specify](specify.md) |
| Planificar | Workflow [plan](plan.md) |
| Implementar feature | Workflow [new_feature](new_feature.md) |
| Corregir bug | Workflow [bug_fix](bug_fix.md) |
| Actualizar docs | Workflow [update-docs](update-docs.md) |

---

*Workflow para CRM VENTAS. Todo el desarrollo dentro de CRM VENTAS.*
