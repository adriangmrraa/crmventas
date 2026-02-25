# Spec: Atribución de Meta Ads (Real-time & Referral)

## Objetivo
Implementar la captura y atribución automática de leads provenientes de Meta Ads (Facebook/Instagram), cubriendo dos flujos críticos:
1.  **Click-to-WhatsApp**: Atribución inmediata vía objeto `referral` en mensajes entrantes.
2.  **Meta Lead Forms**: Ingesta en tiempo real vía webhook directo de Meta.

## Requerimientos Funcionales

### 1. Flujo Click-to-WhatsApp (Referral)
- **Captura**: El `whatsapp_service` debe extraer el objeto `referral` (si existe) del webhook de YCloud.
- **Propagación**: Enviar el objeto `referral` al Orchestrator (`/chat`).
- **Atribución**: 
    - Si el lead es nuevo o tiene `lead_source` 'ORGANIC', actualizar a 'META_ADS'.
    - Guardar `meta_ad_id`, `meta_ad_headline` y `meta_ad_body`.
    - Establecer `source = 'whatsapp_inbound'`.

### 2. Flujo Lead Forms (Webhook Directo)
- **Endpoint**: Implementar `POST /webhooks/meta` para recibir notificaciones de `leadgen`.
- **Procesamiento**:
    - Verificar el webhook de Meta (Hub Challenge).
    - Consultar el Graph API de Meta para obtener los detalles del lead (nombre, teléfono, email, ad_id).
    - Crear el lead en la tabla `leads` con `lead_source = 'META_ADS'` y `source = 'meta_lead_form'`.

## Esquema de Datos (Referencia patch_009)
Las columnas ya existen en la tabla `leads`:
- `lead_source` (META_ADS, ORGANIC)
- `meta_ad_id`
- `meta_ad_headline`
- `meta_ad_body`
- `meta_campaign_id`

## Clarificaciones (Workflow /clarify) - ACTUALIZADO

1.  **¿Política de Atribución?**: Se usará **Last Click**. Si un lead orgánico llega vía anuncio, se actualizan sus metadatos de atribución (`meta_ad_id`, etc.) y se cambia su `lead_source` a 'META_ADS'.
2.  **¿Mapeo de Tenants?**: El `tenant_id` se identifica por el **número de teléfono de destino** (el número del negocio que recibe el mensaje). Cada conexión de Meta está vinculada a una única entidad.
3.  **¿Deduplicación?**: Si un lead ya existe (ej. por Apify) y entra por Meta, se **actualiza** el registro existente en lugar de crear uno nuevo.
4.  **¿Notificaciones?**: Se implementará una notificación interna vía **Socket.IO** (evento `META_LEAD_RECEIVED`) que será visible para el CEO en cualquier página de la app.
5.  **¿Lead Forms?**: Se requiere un webhook específico en CRM Ventas para configurar en Meta (`/webhooks/meta`) que procese las respuestas de formularios.
