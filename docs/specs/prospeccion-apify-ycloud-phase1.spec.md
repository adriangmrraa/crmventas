# Spec: Prospeccion Apify + YCloud (Fase 1)

## Objetivo

Crear una nueva pagina de prospeccion en CRM Ventas para:
- Elegir entidad (tenant), nicho y ubicacion.
- Ejecutar scrape con Apify y guardar leads en `leads`.
- Persistir datos enriquecidos de Apify por lead.
- Marcar estado de outreach (`enviado`, `solicitado`, `pendiente`).
- Dejar preparado el boton de envio de plantilla, sin integrar YCloud en esta fase.

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

- `apify_title`, `apify_category_name`, `apify_address`, `apify_city`, `apify_state`, `apify_country_code`
- `apify_website`, `apify_place_id`, `apify_total_score`, `apify_reviews_count`, `apify_scraped_at`
- `apify_raw` (JSONB)
- `prospecting_niche`, `prospecting_location_query`
- `outreach_message_sent` (bool, default false)
- `outreach_send_requested` (bool, default false)
- `outreach_last_requested_at`, `outreach_last_sent_at`

## Variables de entorno

- `APIFY_API_TOKEN` (obligatoria para scrape).

## Soberania multi-tenant

- Todas las operaciones usan `tenant_id` validado contra `get_allowed_tenant_ids`.
- No se permite escribir/leer sobre entidades fuera del alcance del usuario.

## Criterios de aceptacion

- Al scrapear, se guardan/actualizan leads por entidad + telefono.
- La tabla muestra leads de prospeccion y su estado de outreach.
- El boton de solicitar envio actualiza los flags sin enviar mensajes reales.
- Sin SQL manual; migracion idempotente via `db.py`.

## Clarificaciones (Workflow /clarify)

1. **Unicidad e Identidad**: Se mantiene **un lead por negocio**. Si Apify no devuelve teléfono pero sí una URL web, el sistema debe intentar scrapear la web (siguiendo la lógica del workflow de n8n) para extraer el número. Si se encuentra en la web, se usa ese.
2. **Preservación de Datos**: Si un número de teléfono ya existe en la base de datos de `leads`, **se preservan los datos existentes** y se salta la actualización de ese registro con datos del scrape actual.
3. **Normalización y Ubicación**: La normalización del país (CC) se infiere de la ubicación elegida en la UI. Si se busca "Medellín, Colombia", se asume el prefijo de Colombia para la normalización E.164.
4. **Validación de Outreach**: El sistema validará el formato del teléfono antes de permitir activar el flag `outreach_send_requested`.
5. **Visibilidad**: Los nuevos prospectos son visibles para **todos los vendedores** inmediatamente después del scrape.

