# Spec: Prospeccion Apify + YCloud (Fase 1)

## Objetivo

Crear una nueva pagina de prospeccion en CRM Ventas para:
- Elegir entidad (tenant), nicho y ubicacion.
- Ejecutar scrape con Apify y guardar leads en `leads`.
- Persistir datos enriquecidos de Apify por lead.
- Marcar estado de outreach (`enviado`, `solicitado`, `pendiente`).
- Dejar preparado el boton de envio de plantilla, sin integrar YCloud en esta fase.

> [!NOTE]
> **ESTADO: IMPLEMENTADO (Fase 1 completada - 2026-02-24)**
> Se han implementado los endpoints de scrape, listado y solicitud. La UI soporta pestañas y enriquecimiento de datos sociales.

## Requisitos funcionales

1. **UI de prospeccion**
   - Ruta nueva: `/crm/prospeccion`.
   - Solo CEO.
   - Selector de entidad.
   - Inputs de nicho y ubicacion.
   - Boton `Ejecutar scrape`.
   - Tabla con leads scrapeados y estados de outreach.
   - Boton para solicitar envio de plantilla a pendientes (`outreach_message_sent = false`).

2. **Backend de scrape**
   - Endpoint: `POST /admin/core/crm/prospecting/scrape`.
   - Usa `APIFY_API_TOKEN` desde entorno.
   - Llama al actor de Apify (Google Places).
   - Upsert en `leads` con unicidad `(tenant_id, phone_number)`.

3. **Backend de listado y solicitud de envio**
   - Endpoint: `GET /admin/core/crm/prospecting/leads`.
   - Endpoint: `POST /admin/core/crm/prospecting/request-send` (placeholder).
   - `request-send` no envia WhatsApp aun; solo marca `outreach_send_requested = true`.

## Esquema de datos (nuevas columnas en `leads`)

- `source`: Ahora se usará para diferenciar el origen (`apify_scrape`, `whatsapp_inbound`).
- `apify_title`, `apify_category_name`, `apify_address`, `apify_city`, `apify_state`, `apify_country_code`
- `apify_website`, `apify_place_id`, `apify_total_score`, `apify_reviews_count`, `apify_scraped_at`
- `apify_raw` (JSONB)
- `prospecting_niche`, `prospecting_location_query`
- `outreach_message_sent` (bool, default false)
- `outreach_send_requested` (bool, default false)
- `outreach_last_requested_at`, `outreach_last_sent_at`
- **Nuevas sugeridas**: `social_links` (JSONB para IG, FB, LinkedIn extraídos).

## Clarificaciones (Workflow /clarify)

1. **Origen y Diferenciación**: Se usará la columna `source`. Los leads de mensajes entrantes se marcarán como `whatsapp_inbound`. Los de Apify como `apify_scrape`.
2. **UI en Página de Leads**: Se implementarán dos pestañas:
   - **Mensajes**: Muestra leads con `source = 'whatsapp_inbound'`.
   - **Prospección**: Muestra leads con `source = 'apify_scrape'`. Incluye un botón "Enviar mensajes masivos" que redirige a `/crm/prospeccion`.
3. **Columnas en Prospección**: Se mostrarán `Website`, `Outreach Status`, y enlaces sociales si están disponibles.
4. **Enriquecimiento de Datos**: 
   - Si un lead ya existe por WhatsApp (inbound), el scrape de Apify **actualizará** los campos faltantes (dirección, website, etc.) pero preservará el nombre y teléfono original de WhatsApp.
   - Si ya existe por otra prospección, se ignora el duplicado.
5. **Normalización y Ubicación**: La normalización del país (CC) se infiere de la ubicación elegida en la UI.

