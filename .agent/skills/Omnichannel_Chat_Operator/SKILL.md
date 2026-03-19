---
name: "Omnichannel Chat Operator"
description: "Especialista en gestion de conversaciones via WhatsApp (YCloud) para CRM Ventas."
trigger: "chats, conversaciones, mensajes, whatsapp, human override, handoff"
scope: "CHATS"
auto-invoke: true
---

# Omnichannel Chat Operator - CRM Ventas

## 1. Arquitectura de Comunicacion (WhatsApp via YCloud)
CRM Ventas centraliza toda la comunicacion con leads y clientes en WhatsApp utilizando el proveedor **YCloud**.

### Flujo de Recepcion:
1. **YCloud**: Envia Webhook a `whatsapp_service/webhook/ycloud` (puerto 8002).
2. **Validacion**: HMAC-SHA256 usando `YCLOUD_WEBHOOK_SECRET`.
3. **Forwarding**: El `whatsapp_service` limpia el payload y lo envia al orquestador (puerto 8000).

## 2. Gestion de Human Handoff (Intervencion Humana)
La IA detecta automaticamente cuando un lead o cliente pide hablar con una persona o si la situacion requiere intervencion humana (consultas de precio complejas, quejas, negociacion avanzada).

### Token de Activacion:
`HUMAN_HANDOFF_REQUESTED`

Cuando el orquestador detecta este token en la respuesta de la IA:
1. Activa el "Chat Lock" (bloqueo de IA) por 24 horas.
2. Envia una notificacion via email/notificacion administrativa al seller o closer asignado.
3. El dashboard resalta la conversacion en rojo.

## 3. Seguridad de Webhooks
**REGLA DE ORO**: Nunca procesar un mensaje de WhatsApp sin validar su firma.

### Protocolo de Verificacion:
```python
# whatsapp_service/main.py
signed_payload = f"{timestamp}.{raw_body}"
expected = hmac.new(secret, signed_payload, hashlib.sha256).hexdigest()
if not hmac.compare_digest(expected, signature):
    raise HTTPException(401, "Invalid signature")
```

## 4. Envio de Mensajes
Todas las respuestas de gestion manual desde el Dashboard deben enviarse via:
`POST /admin/whatsapp/send`

El orquestador se encarga de llamar al `ycloud_client.py` en el `whatsapp_service` para el envio final.

## 5. Estandares de Interfaz para el Operador (UX)
Para garantizar la eficiencia del operador humano (setter, closer o secretary) en CRM Ventas:
- **Vista Rigida**: La cabecera del chat y el area de composicion de mensajes deben permanecer fijos.
- **Scroll de Mensajes**: El historial debe tener scroll propio e independiente (Caja de mensajes).
- **Carga de Historial**: Usar el boton de "Cargar mas" para acceder a mensajes antiguos sin perder el contexto de la conversacion actual.

## 6. Protocolos Tecnicos (Criticos)
Para evitar fallos de tipo y bucles de reintentos ("Mensajes Fantasma"):
- **Tipado de Tenant**: El `tenant_id` **DEBE** ser tratado siempre como `int` en la comunicacion entre Orquestador y WhatsApp Service.
- **Registro de HSM**: Todo mensaje enviado mediante plantilla (HSM) debe registrarse en `chat_messages` mediante `db.append_chat_message` inmediatamente despues del envio exitoso.
- **Credenciales Soberanas**: Las API Keys y Webhook Secrets de YCloud deben leerse preferentemente de la tabla `credentials` ("The Vault") para permitir aislamiento por tenant.

## 7. Calificacion de Leads via Chat
Cuando la IA interactua con un lead nuevo, debe seguir el flujo de calificacion de ventas:
1. **Identificacion**: Capturar nombre, telefono y fuente del lead.
2. **Calificacion**: Determinar interes, presupuesto y urgencia.
3. **Asignacion**: Derivar al seller/closer apropiado segun `assignment_rules`.
4. **Seguimiento**: Registrar la interaccion en `chat_messages` y actualizar el estado del lead.

## 8. Checklist de Operacion
- [x] El `YCLOUD_WEBHOOK_SECRET` esta configurado en **The Vault** (tabla `credentials`).
- [x] El `tenant_id` se esta pasando como entero (`int`) en las peticiones internas.
- [ ] La calificacion automatica de leads esta activada en el orquestador.
- [ ] Las notificaciones de handoff estan configuradas para alertar al seller/closer asignado.
- [x] Los mensajes automaticos (HSM) aparecen en el historial de chat del Dashboard.
- [ ] Las `assignment_rules` estan configuradas para la derivacion automatica.
