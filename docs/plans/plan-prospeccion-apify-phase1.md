# Plan tecnico: Prospeccion Apify (Fase 1)

## Goal
Implementar flujo de prospeccion CRM (scrape + guardado + estado de outreach) sin envio real por YCloud todavia.

## Cambios propuestos

1. **Backend - schema**
   - Agregar parche idempotente en `db.py` con columnas de Apify y outreach en `leads`.

2. **Backend - API**
   - `POST /prospecting/scrape`: llama Apify con `APIFY_API_TOKEN` y upsert por `(tenant_id, phone_number)`.
   - `GET /prospecting/leads`: lista leads de prospeccion por tenant.
   - `POST /prospecting/request-send`: marca solicitud de envio (placeholder).

3. **Frontend - UI**
   - Nueva vista `ProspectingView` (`/crm/prospeccion`).
   - Selector de entidad + nicho + ubicacion.
   - Tabla de leads scrapeados.
   - Botones de solicitar envio (todos pendientes / seleccionados).
   - Nuevo item de menu lateral.

4. **i18n**
   - Clave nueva de navegacion: `nav.prospecting` en `es/en/fr`.

## Riesgos

- Falta de `APIFY_API_TOKEN` en entorno bloquea el scrape.
- Datos incompletos de Apify (sin telefono) se descartan.
- El envio real queda diferido a Fase 2 (intencional).

## Gate de confianza

- **Confianza estimada: 92%**.
- Riesgos acotados y sin dependencia de YCloud en esta fase.
- Se procede con implementacion.

## Verificacion

- Backend: endpoint scrape responde 200 y devuelve contadores.
- Backend: listado de prospeccion devuelve filas por tenant.
- Backend: request-send marca `outreach_send_requested`.
- Frontend: la pagina carga, scrapea y muestra/actualiza estados.

