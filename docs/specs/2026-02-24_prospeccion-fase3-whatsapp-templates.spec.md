# Spec: Prospección Fase 3 - Integración de Plantillas WhatsApp (YCloud/Meta)

## 1. Objetivo
Permitir el envío de mensajes proactivos a leads de prospección utilizando plantillas oficiales aprobadas por Meta a través de la API de YCloud.

## 2. Contexto
Meta prohíbe el envío de texto libre fuera de la ventana de 24 horas. Para leads obtenidos vía scraping (prospección), el primer contacto **debe** ser una plantilla.

## 3. Requerimientos Funcionales

### Backend (whatsapp_service)
- **Fetch de Plantillas**: Endpoint para obtener la lista de plantillas disponibles en la WABA (WhatsApp Business Account) del tenant.
- **Envío Estructurado**: Capacidad de enviar mensajes tipo `template` inyectando variables dinámicas (posicionales `{{1}}`, `{{2}}`).

### Backend (orchestrator_service)
- **Proxy de Plantillas**: El orquestador debe consultar al `whatsapp_service` y entregar las plantillas al CRM.
- **Mapeo de Variables**: Lógica para mapear campos del lead (ej: `first_name`) a las variables de la plantilla.

### Frontend (CRM)
- **Selector de Plantillas**: En la vista de prospección o edición de lead, permitir elegir una plantilla de la lista de aprobadas.
- **Preview**: Mostrar cómo quedaría el mensaje antes de enviar (opcional pero deseado).

## 4. Requerimientos Técnicos

### API YCloud (Templates)
- Endpoint: `GET https://api.ycloud.com/v2/whatsapp/templates`
- Filtros: Estado `APPROVED`.

### Payload de Envío
```json
{
  "from": "number_id",
  "to": "phone",
  "type": "template",
  "template": {
    "name": "nombre_plantilla",
    "language": { "code": "es_AR" },
    "components": [
      {
        "type": "body",
        "parameters": [
          { "type": "text", "text": "Valor variable 1" }
        ]
      }
    ]
  }
}
```

## 5. Clarificaciones (Acordadas con el Usuario)
- **Multi-tenancy**: Soportado. Cada tenant usa su propia `API_KEY` y `WABA_ID`.
- **Variables**: `{{1}}` mapea a `first_name` del lead, `{{2}}` mapea a `apify_city` o `apify_state`.
- **Fallback**: Si no hay plantillas aprobadas, el CRM mostrará un mensaje descriptivo ("No se detectaron plantillas aprobadas en YCloud").
- **Auditoría**: Se registrará en la tabla `leads` (o logs específicos) el nombre de la plantilla enviada y los parámetros inyectados.
- **Formato**: Solo texto inicialmente, estructurado para extender a Multimedia (Headers de Imagen/Video) en el futuro.
