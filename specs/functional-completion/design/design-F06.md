# DESIGN F-06: Integraciones

## Decisiones Arquitectónicas
- IntegrationsView ya tiene estructura de tabs (WhatsApp/Instagram/Facebook/Meta) y carga datos desde `/admin/core/integrations/channel-bindings` y `/admin/core/integrations/ycloud-status`
- Agregar: Google Ads panel con connection status, test-connection button, sync button
- Agregar: YCloud test-connection que verifica API key validity
- Reutilizar MetaConnectionWizard y GoogleConnectionWizard existentes

## Componentes React
- `IntegrationsView.tsx` — modificar tabs existentes
- Agregar card "Google Ads" con status badge + botón connect/disconnect
- Agregar botón "Test Connection" en tab WhatsApp que llama `GET /crm/auth/google/ads/test-connection`
- Agregar botón "Test YCloud" que llama `GET /admin/core/integrations/ycloud-status`

## API Endpoints (ya existen)
- `GET /admin/core/integrations/channel-bindings` — status de canales
- `GET /admin/core/integrations/ycloud-status` — YCloud connection info
- `GET /crm/auth/google/ads/test-connection` — test Google connection
- `GET /crm/auth/meta/test-connection` — test Meta connection
- `POST /crm/meta/disconnect` — disconnect Meta

## Riesgos
- Test-connection puede tardar — necesita loading state por botón
