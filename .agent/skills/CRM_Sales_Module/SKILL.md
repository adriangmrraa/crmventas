---
name: "CRM Sales Module"
description: "Módulo CRM: leads, pipeline, vendedores, agenda híbrida y tools de reserva para CRM VENTAS."
trigger: "leads, pipeline, deals, sellers, agenda, calendar, crm_sales"
scope: "DOMAIN"
---

# CRM Sales Module – CRM VENTAS

Módulo de ventas (leads, pipeline, vendedores, agenda) dentro de **CRM VENTAS**. Referencia: modules/crm_sales, niches/crm_sales, gcal_service. Proyecto single-niche: solo CRM (no dental).

---

## Entidades

- **Leads:** phone_number, first_name, last_name, email, status (new → contacted → interested → negotiation → closed_won → closed_lost), assigned_seller_id, source, tags, **social_links** (JSONB).
- **Atribución Meta Ads**: Campos `lead_source` (ORGANIC, META_ADS, META_LEAD_FORM), `meta_ad_id`, `meta_campaign_id`, `meta_ad_headline`, `meta_ad_body`.
- **Pipeline / stages:** Etapas configurables por tenant (o fijas según spec).
- **Sellers (vendedores):** Usuarios con rol seller; asignación a leads.
- **Appointments:** Agenda híbrida (local BD o Google Calendar por tenant); campos source, google_calendar_event_id cuando aplique.
- **Prospecting:** Workflow de extracción masiva vía Apify con filtrado por nicho y locación. Utiliza **polling asíncrono** en el backend para manejar ejecuciones largas (>60s).

---

## API (rutas)

- CRUD leads: list, get, create, update, delete; asignación a seller; cambio de stage. Prefijo coherente (p. ej. `/niche/crm_sales/leads` o `/admin/core/crm/...`).
- **Prospecting:** Scrape de Google Places (`/prospecting/scrape`) y gestión de leads de prospección. Soporta `max_places` configurable (default 30) y polling de estado hasta 300s.
- Agenda: slots, crear/actualizar/cancelar citas; integración con gcal_service si `tenants.config.calendar_provider == 'google'`.

---

## Tools del agente (CRM)

Registrar en el provider del nicho `crm_sales` las tools que el agente pueda usar: pipeline, leads, asignación; check_availability, book_appointment, list_my_appointments, cancel_appointment, reschedule_appointment, list_professionals, list_services, derivhumano (según diseño). Todas las tools deben recibir `tenant_id` y usar credenciales del tenant (Vault).

---

## Frontend

Vistas: Leads (lista con pestañas Mensajes/Prospección), Lead detail (con guardia 404), Pipeline, Sellers, Agenda (calendario con Socket.IO para eventos en tiempo real), **Prospecting (scraping tool)**, **Dashboard (con métricas reales de conversión y tendencias)**.
Sidebar con ítems para nicho crm_sales. Referencia: **CRM VENTAS/frontend_react/src/modules/crm_sales/**.

Todo el código en **CRM VENTAS**.
