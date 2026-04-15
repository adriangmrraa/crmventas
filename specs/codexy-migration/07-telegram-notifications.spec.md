# SPEC-07: Telegram Bot Notifications

**Priority:** Baja
**Complexity:** Baja
**Source:** crmcodexy — `POST /api/telegram/notify`
**Target:** CRM VENTAS — FastAPI backend, nuevo servicio `TelegramService`
**Estado:** Draft
**Fecha:** 2026-04-14

---

## Contexto y Motivación

crmcodexy tiene un endpoint funcional de notificaciones Telegram con rate limiting, validación de webhook secret, sanitización HTML y límite de caracteres. CRM VENTAS necesita esta capacidad para enviar alertas de asignación de llamadas frías (agrupadas por vendedor) y alertas al CEO. En lugar de un endpoint HTTP expuesto, se implementa como un servicio interno de FastAPI que otros servicios pueden invocar directamente.

---

## Alcance

### Incluido

- Servicio interno `TelegramService` con método `send_message(text: str, chat_id: str | None)`
- Sanitización HTML: solo permitir tags `<b>`, `<i>`, `<u>`, `<s>`, `<code>`, `<pre>`, `<a>`
- Límite de 4000 caracteres por mensaje (Telegram API constraint)
- Rate limiting: 10 mensajes/minuto por chat_id (en memoria, usando sliding window)
- Validación de WEBHOOK_SECRET para el endpoint HTTP de disparo externo
- Comparación timing-safe del secret (evitar timing attacks)
- Variables de entorno: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` (default)
- Endpoint opcional `POST /internal/telegram/notify` para disparo externo autenticado
- Integración con el sistema de asignación de llamadas frías: notificación agrupada por vendedor
- Integración con alertas CEO (eventos críticos del negocio)

### Excluido

- Bot interactivo (respuestas a mensajes del usuario en Telegram)
- Múltiples canales/grupos simultáneos en una sola llamada
- Persistencia de historial de mensajes enviados (fuera de scope v1)
- Retry automático con backoff exponencial (v2)

---

## Modelo de Datos

No requiere tabla propia. Configuración via variables de entorno.

```
TELEGRAM_BOT_TOKEN=bot{token}
TELEGRAM_CHAT_ID=-100{chat_id}          # chat por defecto (canal CEO / general)
TELEGRAM_WEBHOOK_SECRET={secret_32+}   # para el endpoint HTTP externo
```

---

## Interfaz del Servicio

```python
class TelegramService:
    async def send_message(
        self,
        text: str,
        chat_id: str | None = None,  # None → usa TELEGRAM_CHAT_ID del env
        parse_mode: Literal["HTML"] = "HTML",
    ) -> TelegramSendResult:
        ...

    async def send_cold_call_assignment(
        self,
        vendedor: str,
        clientes: list[str],
        chat_id: str | None = None,
    ) -> TelegramSendResult:
        """Formatea y envía notificación agrupada de asignación de llamadas frías."""
        ...

    async def send_ceo_alert(
        self,
        titulo: str,
        detalle: str,
    ) -> TelegramSendResult:
        """Envía alerta crítica al chat CEO."""
        ...
```

```python
class TelegramSendResult(BaseModel):
    ok: bool
    message_id: int | None
    error: str | None
```

---

## Endpoint HTTP Externo (opcional, autenticado)

```
POST /internal/telegram/notify
Authorization: X-Webhook-Secret: {secret}

Body:
{
  "text": "...",           # requerido
  "chat_id": "..."         # opcional, default al env
}

Responses:
200 → { "ok": true, "message_id": 123 }
400 → { "detail": "Mensaje excede 4000 caracteres" }
401 → { "detail": "Unauthorized" }
429 → { "detail": "Rate limit exceeded. Retry after 60s" }
```

---

## Escenarios (BDD)

### SC-07-01: Mensaje válido enviado correctamente

```
DADO que TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID están configurados
  Y el texto tiene menos de 4000 caracteres
  Y no se superó el rate limit
CUANDO se llama a TelegramService.send_message(text)
ENTONCES se hace POST a https://api.telegram.org/bot{token}/sendMessage
  Y la respuesta contiene ok=True y message_id válido
```

### SC-07-02: Sanitización HTML — tags no permitidos son removidos

```
DADO un texto con <script>alert('xss')</script> y texto normal con <b>bold</b>
CUANDO se llama a send_message
ENTONCES el texto enviado a Telegram NO contiene <script>
  Y SÍ contiene <b>bold</b>
  Y el resto del texto plano queda intacto
```

### SC-07-03: Mensaje excede 4000 caracteres

```
DADO un texto de 4001+ caracteres
CUANDO se llama a send_message
ENTONCES se lanza TelegramMessageTooLongError
  Y NO se hace ninguna llamada a la API de Telegram
```

### SC-07-04: Rate limit alcanzado

```
DADO que se enviaron 10 mensajes al mismo chat_id en el último minuto
CUANDO se intenta enviar el mensaje número 11
ENTONCES se lanza TelegramRateLimitError
  Y la respuesta HTTP del endpoint externo es 429
```

### SC-07-05: Webhook secret inválido en endpoint externo

```
DADO una request a POST /internal/telegram/notify
  CON X-Webhook-Secret incorrecto
CUANDO se procesa la request
ENTONCES la respuesta es 401 Unauthorized
  Y la comparación se hace en tiempo constante (timing-safe)
```

### SC-07-06: Notificación de asignación de llamadas frías

```
DADO vendedor="Juan Pérez" y clientes=["ACME S.A.", "Beta Corp", "Gamma Ltd"]
CUANDO se llama a send_cold_call_assignment
ENTONCES el mensaje enviado incluye el nombre del vendedor
  Y lista los 3 clientes asignados
  Y usa formato HTML válido para Telegram
```

### SC-07-07: Alerta CEO

```
DADO titulo="Pipeline en riesgo" y detalle="3 deals sin actividad > 15 días"
CUANDO se llama a send_ceo_alert
ENTONCES el mensaje se envía al TELEGRAM_CEO_CHAT_ID (o TELEGRAM_CHAT_ID si no configurado)
  Y incluye emoji de alerta y formato destacado
```

---

## Implementación — Estructura de Archivos

```
app/
  services/
    telegram/
      __init__.py
      service.py          # TelegramService
      sanitizer.py        # HTML sanitization logic
      rate_limiter.py     # In-memory sliding window rate limiter
      schemas.py          # TelegramSendResult, TelegramNotifyRequest
      exceptions.py       # TelegramMessageTooLongError, TelegramRateLimitError
  routers/
    internal/
      telegram.py         # POST /internal/telegram/notify
  tests/
    services/
      telegram/
        test_service.py
        test_sanitizer.py
        test_rate_limiter.py
    routers/
      internal/
        test_telegram_router.py
```

---

## Dependencias

```
# requirements.txt additions
httpx>=0.27           # async HTTP client para llamar Telegram API
bleach>=6.1           # HTML sanitization (permite allowlist de tags)
```

`bleach` se usa para sanitización porque ya maneja edge cases (tags anidados, atributos, entidades HTML). No reinventar.

---

## Variables de Entorno Requeridas

| Variable | Requerida | Default | Descripción |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Si | — | Token del bot (formato: `bot{id}:{hash}`) |
| `TELEGRAM_CHAT_ID` | Si | — | Chat ID por defecto para mensajes generales |
| `TELEGRAM_CEO_CHAT_ID` | No | `TELEGRAM_CHAT_ID` | Chat ID específico para alertas CEO |
| `TELEGRAM_WEBHOOK_SECRET` | Si* | — | Secret para endpoint externo (*requerido si el router está habilitado) |
| `TELEGRAM_RATE_LIMIT_PER_MIN` | No | `10` | Mensajes máximos por minuto por chat_id |

---

## Tests Requeridos (TDD)

Todos los escenarios BDD deben tener test correspondiente antes de implementar.

- `test_service.py`: mockear `httpx.AsyncClient`, cubrir SC-07-01, SC-07-03, SC-07-04, SC-07-06, SC-07-07
- `test_sanitizer.py`: cubrir SC-07-02 con múltiples variantes de HTML malicioso
- `test_rate_limiter.py`: cubrir SC-07-04, sliding window correctness, reset después de 1 min
- `test_telegram_router.py`: cubrir SC-07-05 (timing-safe), 200, 400, 429

---

## Criterios de Aceptación

- [ ] `TelegramService.send_message` funciona end-to-end en entorno staging con bot real
- [ ] Tags HTML no permitidos son eliminados (no escapados ni rechazados — solo removidos)
- [ ] Mensajes > 4000 chars son rechazados antes de llamar a Telegram API
- [ ] Rate limit de 10/min por chat_id funciona correctamente bajo carga concurrente
- [ ] Comparación de WEBHOOK_SECRET es timing-safe (usar `hmac.compare_digest`)
- [ ] Cobertura de tests >= 90% en el módulo `telegram/`
- [ ] El servicio se puede inyectar via FastAPI Depends en cualquier router

---

## Notas de Migración desde crmcodexy

| crmcodexy | CRM VENTAS |
|---|---|
| Endpoint HTTP `POST /api/telegram/notify` | Servicio interno + endpoint opcional `/internal/telegram/notify` |
| Rate limiting por IP | Rate limiting por `chat_id` (más semántico para el dominio) |
| `express-rate-limit` in-memory | Sliding window custom en Python (o `slowapi` si ya está como dep) |
| `sanitize-html` npm package | `bleach` Python package |
| `crypto.timingSafeEqual` | `hmac.compare_digest` |

La lógica de negocio es idéntica. El cambio es solo de runtime (Node → Python/FastAPI).
