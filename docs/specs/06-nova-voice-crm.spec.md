# SPEC: Nova Voice Assistant para CRM de Ventas

**Fecha:** 2026-03-27
**Prioridad:** Alta (diferenciador de producto)
**Esfuerzo:** Medio (adaptar arquitectura probada de ClinicForge)
**Confidence:** 90%
**Referencia:** ClinicForge Nova (47 tools, OpenAI Realtime API, WebSocket)

---

## 1. Contexto y Objetivos

### Por que voz es un game-changer para ventas

Los vendedores viven en llamadas. Mientras hablan con un prospecto, necesitan:

- **Registrar datos sin soltar el telefono.** "Nova, registra lead Juan Perez, empresa TechCorp, interesado en plan Enterprise." El vendedor sigue hablando con el cliente mientras Nova carga el CRM.
- **Consultar pipeline sin abrir pestanas.** "Nova, cuantos leads tengo en negociacion?" La respuesta llega en 2 segundos por audio, sin interrumpir la llamada.
- **Agendar follow-ups al instante.** "Nova, agenda llamada con Maria Lopez para manana a las 10." Sin abrir calendario, sin tipear.
- **Revisar metricas antes de una reunion.** "Nova, dame el resumen de ventas de esta semana." El vendedor entra a la reunion con datos frescos.

El problema real: los vendedores odian cargar el CRM. El 40-60% de las interacciones no se registran porque requieren abrir formularios, buscar campos, tipear. Nova elimina esa friccion: **hablas y el CRM se actualiza solo**.

### Objetivo

Implementar Nova Voice Assistant adaptada al contexto de ventas con 20 herramientas que cubren el ciclo completo: leads, pipeline, agenda, analytics, navegacion y comunicacion. Misma arquitectura probada de ClinicForge (OpenAI Realtime API + WebSocket + React widget).

---

## 2. Arquitectura

### Diagrama general

```
NovaWidget (React)  -->  WebSocket  -->  Nova Handler (main.py)  -->  OpenAI Realtime API
                                              |
                                        Nova Tools (20 tools)  -->  PostgreSQL
                                              |
                                        Socket.IO  -->  Frontend (real-time UI sync)
```

### Flujo de audio

```
1. Usuario presiona boton Nova (o hotkey)
2. NovaWidget abre WebSocket a /ws/nova
3. Backend abre sesion con OpenAI Realtime API
4. Audio del microfono --> WebSocket --> OpenAI Realtime --> transcripcion + intent
5. OpenAI invoca function call --> backend ejecuta tool --> resultado texto
6. OpenAI genera respuesta de audio --> WebSocket --> NovaWidget reproduce audio
7. Si el tool modifica datos, emite Socket.IO event para sync de UI
```

### Componentes

| Componente | Archivo | Responsabilidad |
|------------|---------|-----------------|
| **NovaWidget** | `frontend_react/src/components/NovaWidget.tsx` | UI flotante, captura de audio, WebSocket client, reproduccion de respuesta |
| **WebSocket Handler** | `backend/main.py` (~handler `/ws/nova`) | Bridge entre WebSocket del cliente y OpenAI Realtime API session |
| **Nova Tools** | `backend/services/nova_tools.py` | 20 tool schemas + implementaciones async contra PostgreSQL |
| **Nova Routes** | `backend/routes/nova_routes.py` | REST endpoints auxiliares: contexto, health, historial de sesiones |
| **Socket.IO Emitter** | Helper `_nova_emit()` en `nova_tools.py` | Emite eventos para que el frontend refleje cambios en tiempo real |

### Formato de tool schema (CRITICO)

OpenAI Realtime API requiere formato **flat**, NO el wrapper de Chat Completions:

```json
// CORRECTO para Realtime API
{
  "type": "function",
  "name": "buscar_lead",
  "description": "Busca leads por nombre, empresa o telefono",
  "parameters": {
    "type": "object",
    "properties": { ... },
    "required": [ ... ]
  }
}
```

```json
// INCORRECTO para Realtime API (esto es Chat Completions format)
{
  "type": "function",
  "function": {
    "name": "buscar_lead",
    ...
  }
}
```

---

## 3. Tools (20 herramientas)

### A. LEADS (5 tools)

#### `buscar_lead`
Busca leads por nombre, empresa, telefono o email. Retorna hasta 5 resultados con etapa actual del pipeline.

```json
{
  "type": "function",
  "name": "buscar_lead",
  "description": "Busca leads por nombre, empresa, telefono o email. Retorna hasta 5 resultados.",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Nombre, empresa, telefono o email del lead"
      }
    },
    "required": ["query"]
  }
}
```

**SQL:** `SELECT id, first_name, last_name, company, phone, email, pipeline_stage, assigned_seller_id FROM leads WHERE tenant_id = $1 AND (first_name ILIKE $2 OR last_name ILIKE $2 OR company ILIKE $2 OR phone ILIKE $2 OR email ILIKE $2) ORDER BY updated_at DESC LIMIT 5`

**Respuesta de voz (ejemplo):** "Encontre 2 leads: Juan Perez de TechCorp en etapa Negociacion, y Juan Martinez de DataSoft en etapa Contacto Inicial."

---

#### `ver_lead`
Muestra ficha completa de un lead: datos de contacto, empresa, etapa, historial de interacciones, proxima actividad agendada, vendedor asignado.

```json
{
  "type": "function",
  "name": "ver_lead",
  "description": "Ver ficha completa de un lead: datos, empresa, etapa, historial de interacciones, proxima actividad.",
  "parameters": {
    "type": "object",
    "properties": {
      "lead_id": {
        "type": "integer",
        "description": "ID del lead"
      }
    },
    "required": ["lead_id"]
  }
}
```

**SQL:** JOIN entre `leads`, `lead_interactions` (ultimas 5), `events` (proxima actividad). Incluye `days_in_stage` calculado.

---

#### `registrar_lead`
Crea un lead nuevo con datos basicos. Asigna al vendedor actual por defecto.

```json
{
  "type": "function",
  "name": "registrar_lead",
  "description": "Crea un lead nuevo con datos basicos. Se asigna automaticamente al vendedor actual.",
  "parameters": {
    "type": "object",
    "properties": {
      "first_name": { "type": "string", "description": "Nombre del lead" },
      "last_name": { "type": "string", "description": "Apellido del lead" },
      "phone": { "type": "string", "description": "Telefono del lead" },
      "email": { "type": "string", "description": "Email del lead" },
      "company": { "type": "string", "description": "Empresa del lead" },
      "source": {
        "type": "string",
        "enum": ["whatsapp", "instagram", "facebook", "meta_ads", "referido", "web", "llamada", "otro"],
        "description": "Canal de origen del lead"
      },
      "notes": { "type": "string", "description": "Notas iniciales sobre el lead" }
    },
    "required": ["first_name", "last_name", "phone"]
  }
}
```

**Post-insert:** Emite Socket.IO `NEW_LEAD` para actualizar la vista de leads en tiempo real.

---

#### `actualizar_lead`
Actualiza un campo especifico de un lead existente.

```json
{
  "type": "function",
  "name": "actualizar_lead",
  "description": "Actualiza un campo especifico de un lead existente.",
  "parameters": {
    "type": "object",
    "properties": {
      "lead_id": { "type": "integer", "description": "ID del lead" },
      "field": {
        "type": "string",
        "enum": ["phone", "email", "company", "notes", "estimated_value", "source", "assigned_seller_id"],
        "description": "Campo a actualizar"
      },
      "value": { "type": "string", "description": "Nuevo valor del campo" }
    },
    "required": ["lead_id", "field", "value"]
  }
}
```

**Post-update:** Emite Socket.IO `LEAD_UPDATED`.

---

#### `cambiar_estado_lead`
Cambia el estado de un lead (activo, ganado, perdido, pausado). Diferente de `mover_lead_etapa` que mueve dentro del pipeline.

```json
{
  "type": "function",
  "name": "cambiar_estado_lead",
  "description": "Cambia el estado de un lead: activo, ganado, perdido, pausado. Registra motivo si es perdido.",
  "parameters": {
    "type": "object",
    "properties": {
      "lead_id": { "type": "integer", "description": "ID del lead" },
      "status": {
        "type": "string",
        "enum": ["active", "won", "lost", "paused"],
        "description": "Nuevo estado"
      },
      "reason": {
        "type": "string",
        "description": "Motivo del cambio (obligatorio si es 'lost')"
      }
    },
    "required": ["lead_id", "status"]
  }
}
```

**Post-update:** Emite Socket.IO `LEAD_STATUS_CHANGED`. Si es `won`, registra en `sales` con `estimated_value` del lead.

---

### B. PIPELINE (4 tools)

#### `ver_pipeline`
Muestra resumen del pipeline completo: cantidad de leads por etapa, valor total estimado, leads estancados (>7 dias sin movimiento).

```json
{
  "type": "function",
  "name": "ver_pipeline",
  "description": "Resumen del pipeline: leads por etapa, valor total, leads estancados (>7 dias sin movimiento).",
  "parameters": {
    "type": "object",
    "properties": {
      "seller_id": {
        "type": "integer",
        "description": "ID del vendedor. Default: usuario actual. Usar 0 para ver todo el equipo."
      }
    },
    "required": []
  }
}
```

**Respuesta (ejemplo):** "Tu pipeline tiene 23 leads activos. 8 en Contacto Inicial, 6 en Reunion Agendada, 5 en Propuesta Enviada, 4 en Negociacion. Valor total estimado: $45.000. Ojo: 3 leads llevan mas de 7 dias sin movimiento."

---

#### `mover_lead_etapa`
Mueve un lead a una etapa diferente del pipeline. Registra la transicion con timestamp.

```json
{
  "type": "function",
  "name": "mover_lead_etapa",
  "description": "Mueve un lead a otra etapa del pipeline. Registra la transicion.",
  "parameters": {
    "type": "object",
    "properties": {
      "lead_id": { "type": "integer", "description": "ID del lead" },
      "stage": {
        "type": "string",
        "enum": ["new", "contacted", "meeting_scheduled", "proposal_sent", "negotiation", "closed_won", "closed_lost"],
        "description": "Nueva etapa del pipeline"
      },
      "note": { "type": "string", "description": "Nota sobre el cambio de etapa" }
    },
    "required": ["lead_id", "stage"]
  }
}
```

**Post-update:** INSERT en `lead_stage_transitions` + emite Socket.IO `PIPELINE_UPDATED`.

---

#### `resumen_pipeline`
Metricas agregadas del pipeline: conversion rate por etapa, tiempo promedio en cada etapa, forecast de cierre.

```json
{
  "type": "function",
  "name": "resumen_pipeline",
  "description": "Metricas del pipeline: conversion por etapa, tiempo promedio, forecast de cierre del mes.",
  "parameters": {
    "type": "object",
    "properties": {
      "period": {
        "type": "string",
        "enum": ["week", "month", "quarter"],
        "description": "Periodo de analisis. Default: month"
      }
    },
    "required": []
  }
}
```

---

#### `leads_por_etapa`
Lista los leads de una etapa especifica con detalle: nombre, empresa, valor estimado, dias en la etapa, vendedor.

```json
{
  "type": "function",
  "name": "leads_por_etapa",
  "description": "Lista los leads de una etapa especifica del pipeline con detalle.",
  "parameters": {
    "type": "object",
    "properties": {
      "stage": {
        "type": "string",
        "enum": ["new", "contacted", "meeting_scheduled", "proposal_sent", "negotiation", "closed_won", "closed_lost"],
        "description": "Etapa del pipeline"
      },
      "limit": {
        "type": "integer",
        "description": "Cantidad maxima de resultados. Default: 10"
      }
    },
    "required": ["stage"]
  }
}
```

---

### C. AGENDA (4 tools)

#### `ver_agenda_hoy`
Muestra las actividades del dia (llamadas, reuniones, follow-ups) con hora, lead asociado y tipo.

```json
{
  "type": "function",
  "name": "ver_agenda_hoy",
  "description": "Ver actividades del dia: llamadas, reuniones, follow-ups. Muestra hora, lead y tipo.",
  "parameters": {
    "type": "object",
    "properties": {
      "date": {
        "type": "string",
        "description": "Fecha en formato YYYY-MM-DD. Default: hoy"
      },
      "seller_id": {
        "type": "integer",
        "description": "ID del vendedor. Default: usuario actual"
      }
    },
    "required": []
  }
}
```

**Respuesta (ejemplo):** "Hoy tenes 5 actividades. A las 9:00 llamada con Juan Perez de TechCorp, a las 10:30 reunion con Maria Lopez, a las 14:00 follow-up con Pedro Garcia..."

---

#### `agendar_llamada`
Agenda una llamada, reunion o follow-up con un lead. Crea evento en la agenda del vendedor.

```json
{
  "type": "function",
  "name": "agendar_llamada",
  "description": "Agenda una llamada, reunion o follow-up con un lead.",
  "parameters": {
    "type": "object",
    "properties": {
      "lead_id": { "type": "integer", "description": "ID del lead" },
      "event_type": {
        "type": "string",
        "enum": ["call", "meeting", "follow_up", "demo", "proposal_review"],
        "description": "Tipo de evento"
      },
      "datetime": {
        "type": "string",
        "description": "Fecha y hora en formato YYYY-MM-DD HH:MM"
      },
      "duration_minutes": {
        "type": "integer",
        "description": "Duracion en minutos. Default: 30"
      },
      "notes": { "type": "string", "description": "Notas para el evento" }
    },
    "required": ["lead_id", "event_type", "datetime"]
  }
}
```

**Post-insert:** Emite Socket.IO `NEW_EVENT`.

---

#### `cancelar_evento`
Cancela un evento agendado por ID. Registra motivo.

```json
{
  "type": "function",
  "name": "cancelar_evento",
  "description": "Cancela un evento agendado. Registra motivo de cancelacion.",
  "parameters": {
    "type": "object",
    "properties": {
      "event_id": { "type": "integer", "description": "ID del evento" },
      "reason": { "type": "string", "description": "Motivo de cancelacion" }
    },
    "required": ["event_id"]
  }
}
```

**Post-update:** Emite Socket.IO `EVENT_CANCELLED`.

---

#### `proxima_llamada`
Retorna la proxima actividad agendada del vendedor con detalle del lead.

```json
{
  "type": "function",
  "name": "proxima_llamada",
  "description": "Muestra la proxima actividad agendada del vendedor: hora, lead, tipo y notas.",
  "parameters": {
    "type": "object",
    "properties": {},
    "required": []
  }
}
```

**Respuesta (ejemplo):** "Tu proxima actividad es una llamada con Juan Perez de TechCorp a las 14:00. Notas: segundo contacto, interesado en plan Enterprise."

---

### D. ANALYTICS (3 tools)

#### `resumen_ventas`
Resumen de ventas del periodo: total cerrado, cantidad de deals, ticket promedio, comparacion vs periodo anterior.

```json
{
  "type": "function",
  "name": "resumen_ventas",
  "description": "Resumen de ventas: total cerrado, cantidad de deals, ticket promedio, comparacion vs periodo anterior.",
  "parameters": {
    "type": "object",
    "properties": {
      "period": {
        "type": "string",
        "enum": ["today", "week", "month", "quarter"],
        "description": "Periodo de analisis. Default: week"
      }
    },
    "required": []
  }
}
```

**Respuesta (ejemplo):** "Esta semana cerraste 3 ventas por un total de $12.500. Ticket promedio: $4.166. Estas un 20% arriba comparado con la semana pasada."

---

#### `rendimiento_vendedor`
Metricas de rendimiento individual o del equipo: leads contactados, reuniones realizadas, propuestas enviadas, deals cerrados, conversion rate.

```json
{
  "type": "function",
  "name": "rendimiento_vendedor",
  "description": "Metricas de rendimiento: leads contactados, reuniones, propuestas, deals cerrados, conversion rate.",
  "parameters": {
    "type": "object",
    "properties": {
      "seller_id": {
        "type": "integer",
        "description": "ID del vendedor. Default: usuario actual. Usar 0 para ver equipo."
      },
      "period": {
        "type": "string",
        "enum": ["week", "month", "quarter"],
        "description": "Periodo. Default: month"
      }
    },
    "required": []
  }
}
```

---

#### `conversion_rate`
Tasa de conversion del funnel completo: leads nuevos -> contactados -> reunion -> propuesta -> negociacion -> cierre. Desglosado por fuente y vendedor.

```json
{
  "type": "function",
  "name": "conversion_rate",
  "description": "Tasa de conversion del funnel completo, desglosado por fuente y vendedor.",
  "parameters": {
    "type": "object",
    "properties": {
      "period": {
        "type": "string",
        "enum": ["month", "quarter", "year"],
        "description": "Periodo. Default: month"
      },
      "group_by": {
        "type": "string",
        "enum": ["source", "seller", "none"],
        "description": "Agrupar por fuente, vendedor, o sin agrupar. Default: none"
      }
    },
    "required": []
  }
}
```

---

### E. NAVEGACION (2 tools)

#### `ir_a_pagina`
Navega a una pagina del CRM. Retorna JSON con `type: "navigation"` que el frontend interpreta.

```json
{
  "type": "function",
  "name": "ir_a_pagina",
  "description": "Navega a una pagina del CRM: dashboard, leads, clientes, agenda, chats, vendedores, marketing, prospeccion, config.",
  "parameters": {
    "type": "object",
    "properties": {
      "page": {
        "type": "string",
        "enum": ["dashboard", "leads", "clients", "agenda", "chats", "sellers", "marketing", "prospecting", "config"],
        "description": "Pagina destino"
      }
    },
    "required": ["page"]
  }
}
```

**Retorno:** `{"type": "navigation", "route": "/leads"}` -- El frontend escucha este JSON y ejecuta `navigate()`.

---

#### `ir_a_lead`
Navega directamente a la ficha de un lead especifico.

```json
{
  "type": "function",
  "name": "ir_a_lead",
  "description": "Navega a la ficha de un lead especifico.",
  "parameters": {
    "type": "object",
    "properties": {
      "lead_id": { "type": "integer", "description": "ID del lead" }
    },
    "required": ["lead_id"]
  }
}
```

**Retorno:** `{"type": "navigation", "route": "/leads/42"}`

---

### F. COMUNICACION (2 tools)

#### `ver_chats_recientes`
Muestra las ultimas conversaciones de WhatsApp/Instagram con leads, con preview del ultimo mensaje.

```json
{
  "type": "function",
  "name": "ver_chats_recientes",
  "description": "Muestra las ultimas conversaciones con leads: canal, ultimo mensaje, timestamp.",
  "parameters": {
    "type": "object",
    "properties": {
      "limit": {
        "type": "integer",
        "description": "Cantidad de chats a mostrar. Default: 5"
      },
      "channel": {
        "type": "string",
        "enum": ["whatsapp", "instagram", "all"],
        "description": "Filtrar por canal. Default: all"
      }
    },
    "required": []
  }
}
```

---

#### `enviar_whatsapp`
Envia un mensaje de WhatsApp a un lead. Usa la integracion YCloud existente.

```json
{
  "type": "function",
  "name": "enviar_whatsapp",
  "description": "Envia un mensaje de WhatsApp a un lead.",
  "parameters": {
    "type": "object",
    "properties": {
      "lead_id": { "type": "integer", "description": "ID del lead" },
      "message": { "type": "string", "description": "Texto del mensaje a enviar" }
    },
    "required": ["lead_id", "message"]
  }
}
```

**Post-send:** Registra en `lead_interactions` + emite Socket.IO `NEW_MESSAGE`.

---

### Resumen de tools

| Categoria | Tools | Count |
|-----------|-------|-------|
| **A. Leads** | buscar_lead, ver_lead, registrar_lead, actualizar_lead, cambiar_estado_lead | 5 |
| **B. Pipeline** | ver_pipeline, mover_lead_etapa, resumen_pipeline, leads_por_etapa | 4 |
| **C. Agenda** | ver_agenda_hoy, agendar_llamada, cancelar_evento, proxima_llamada | 4 |
| **D. Analytics** | resumen_ventas, rendimiento_vendedor, conversion_rate | 3 |
| **E. Navegacion** | ir_a_pagina, ir_a_lead | 2 |
| **F. Comunicacion** | ver_chats_recientes, enviar_whatsapp | 2 |
| **TOTAL** | | **20** |

---

## 4. System Prompt

```python
NOVA_CRM_SYSTEM_PROMPT = """
Sos Nova, la asistente de voz del CRM de ventas. Sos como Jarvis para vendedores.

## Personalidad
- Directa, eficiente, sin rodeos
- Voseo argentino ("vos tenes", "sos", "podes")
- Respuestas cortas para voz (max 2-3 oraciones)
- Datos concretos, nunca respuestas vagas

## Regla de oro: EJECUTA PRIMERO, HABLA DESPUES
- Si el vendedor pide algo que un tool resuelve, ejecuta el tool INMEDIATAMENTE
- NO pidas confirmacion salvo para acciones destructivas (cancelar, eliminar)
- Si faltan datos, inferi lo que puedas y pregunta SOLO lo estrictamente necesario (1 dato por vez)
- Encadena 2-3 tools sin preguntar si el flujo lo permite

## Ejemplos de encadenamiento
- "Registra a Juan Perez de TechCorp y agenda llamada para manana a las 10"
  → registrar_lead + agendar_llamada (sin preguntar nada intermedio)
- "Busca a Maria Lopez y movela a Propuesta Enviada"
  → buscar_lead + mover_lead_etapa (sin confirmacion)
- "Como viene la semana?"
  → resumen_ventas + ver_pipeline (2 tools, 1 respuesta consolidada)

## Formato de respuesta por voz
- Numeros: decir el valor, no porcentajes largos ("un 20% arriba" no "un 20.3456%")
- Listas: maximo 3-4 items, despues "y {N} mas"
- Siempre cerrar con accion sugerida si aplica ("Queres que lo llame?", "Lo agendo?")

## Contexto del usuario
- Tenant: {tenant_name}
- Vendedor: {seller_name} (ID: {seller_id})
- Rol: {role}
- Fecha/hora actual: {current_datetime}
- Pagina actual: {current_page}

## NUNCA decir "no puedo" si un tool puede resolverlo.
"""
```

---

## 5. Voice Model Configuration

### Modelo por defecto
- **Economico:** `gpt-4o-mini-realtime-preview` (para uso diario de vendedores)
- **Premium:** `gpt-4o-realtime-preview` (para demos y usuarios premium)

### Configuracion en base de datos
Almacenado en la tabla `system_config`:

```sql
INSERT INTO system_config (key, value, tenant_id)
VALUES ('MODEL_NOVA_VOICE', 'gpt-4o-realtime-preview', $tenant_id);
```

### Seleccion desde UI
El administrador selecciona el modelo desde la pagina de Configuracion > Tokens & Metricas. Dropdown con las dos opciones + indicador de costo estimado por minuto.

### Lectura en el handler

```python
async def get_nova_voice_model(tenant_id: int) -> str:
    row = await db.fetchrow(
        "SELECT value FROM system_config WHERE key = 'MODEL_NOVA_VOICE' AND tenant_id = $1",
        tenant_id
    )
    return row["value"] if row else "gpt-4o-mini-realtime-preview"
```

---

## 6. Frontend: NovaWidget

### Source
Copiar de `clinicforge/frontend_react/src/components/NovaWidget.tsx` y adaptar.

### Diseno visual

- **Boton flotante:** esquina inferior derecha, `fixed bottom-6 right-6 z-50`
- **Gradiente:** `bg-gradient-to-br from-violet-600 to-purple-700` (mantener violeta de ClinicForge)
- **Tamano:** `w-14 h-14 rounded-full`
- **Animaciones:** `novaWobble` (idle), `novaPing` (escuchando), `novaPulse` (procesando)
- **Tooltip:** "Nova - Asistente de voz" en hover
- **Panel expandido:** fondo `bg-[#0d1117]/95 backdrop-blur-xl`, bordes `border-white/[0.06]`

### Estados del widget

| Estado | Visual | Audio |
|--------|--------|-------|
| **Idle** | Icono microfono, wobble suave | -- |
| **Listening** | Icono animado, ping ring violeta | Capturando microfono |
| **Processing** | Spinner, pulse | Enviando a OpenAI |
| **Speaking** | Ondas de audio animadas | Reproduciendo respuesta |
| **Error** | Icono rojo, shake | Beep de error |

### Integracion con navegacion

Cuando un tool retorna `{"type": "navigation", ...}`, el widget ejecuta:

```tsx
const handleToolResult = (result: string) => {
  try {
    const parsed = JSON.parse(result);
    if (parsed.type === "navigation") {
      navigate(parsed.route);
    }
  } catch {
    // No es JSON, es respuesta de voz normal
  }
};
```

### Hotkey
`Ctrl + Shift + N` para toggle del widget (configurable).

---

## 7. Acceptance Criteria (Gherkin)

### Escenario 1: Registrar lead por voz

```gherkin
Feature: Nova Voice - Registrar lead

  Scenario: Vendedor registra un lead nuevo hablando
    Given el vendedor esta logueado en el CRM
    And el widget Nova esta activo
    When el vendedor dice "Nova, registra lead Juan Perez, empresa TechCorp, telefono 11-2345-6789"
    Then Nova ejecuta el tool "registrar_lead" con first_name="Juan", last_name="Perez", company="TechCorp", phone="11-2345-6789"
    And el lead se crea en la base de datos con tenant_id del vendedor
    And se emite Socket.IO "NEW_LEAD" para actualizar la vista
    And Nova responde por voz "Listo, registre a Juan Perez de TechCorp. Queres que le agende una llamada?"
```

### Escenario 2: Consultar pipeline por voz

```gherkin
Feature: Nova Voice - Consultar pipeline

  Scenario: Vendedor pregunta por su pipeline
    Given el vendedor tiene 15 leads activos en distintas etapas
    When el vendedor dice "Nova, como esta mi pipeline?"
    Then Nova ejecuta el tool "ver_pipeline" con seller_id del usuario actual
    And Nova responde por voz con cantidad por etapa, valor total y leads estancados
    And la respuesta no supera 4 oraciones
```

### Escenario 3: Agendar llamada encadenando tools

```gherkin
Feature: Nova Voice - Encadenamiento de tools

  Scenario: Vendedor busca lead y agenda llamada en un solo comando
    Given existe un lead "Maria Lopez" con ID 42
    When el vendedor dice "Nova, busca a Maria Lopez y agendame una llamada para manana a las 10"
    Then Nova ejecuta "buscar_lead" con query="Maria Lopez"
    And Nova ejecuta "agendar_llamada" con lead_id=42, event_type="call", datetime del dia siguiente a las 10:00
    And se emite Socket.IO "NEW_EVENT"
    And Nova responde "Listo, llamada con Maria Lopez agendada para manana a las 10."
```

### Escenario 4: Navegacion por voz

```gherkin
Feature: Nova Voice - Navegacion

  Scenario: Vendedor navega a la vista de leads por voz
    Given el vendedor esta en el Dashboard
    When el vendedor dice "Nova, llename a leads"
    Then Nova ejecuta "ir_a_pagina" con page="leads"
    And el tool retorna {"type": "navigation", "route": "/leads"}
    And el frontend ejecuta navigate("/leads")
    And la vista de Leads se renderiza
    And Nova responde "Listo, estas en Leads."
```

### Escenario 5: Resumen de ventas antes de reunion

```gherkin
Feature: Nova Voice - Resumen rapido

  Scenario: Vendedor pide resumen semanal
    Given el vendedor cerro 3 ventas esta semana por $12.500 total
    When el vendedor dice "Nova, dame el resumen de la semana"
    Then Nova ejecuta "resumen_ventas" con period="week"
    And Nova responde "Esta semana cerraste 3 ventas por $12.500. Ticket promedio $4.166. Estas un 20% arriba comparado con la semana pasada."
    And la respuesta incluye comparacion con periodo anterior
```

---

## 8. Archivos a crear/modificar

### Archivos nuevos

| Archivo | Descripcion |
|---------|-------------|
| `frontend_react/src/components/NovaWidget.tsx` | Widget flotante de voz, WebSocket client, audio capture/playback |
| `backend/services/nova_tools.py` | 20 tool schemas (NOVA_TOOLS_SCHEMA) + implementaciones async |
| `backend/routes/nova_routes.py` | REST endpoints: `/nova/context`, `/nova/health`, `/nova/sessions` |
| `frontend_react/src/index.css` | Agregar keyframes: `novaWobble`, `novaPing`, `novaPulse` (si no existen) |

### Archivos a modificar

| Archivo | Cambio |
|---------|--------|
| `backend/main.py` | Agregar WebSocket handler `/ws/nova`, importar `nova_tools`, system prompt, bridge con OpenAI Realtime API |
| `backend/main.py` | Registrar `nova_routes` como router de FastAPI |
| `frontend_react/src/App.tsx` | Importar y renderizar `<NovaWidget />` dentro del layout autenticado |
| `backend/models.py` | Verificar que `system_config` tenga soporte para `MODEL_NOVA_VOICE` key |
| `backend/requirements.txt` | Agregar `openai>=1.40.0` (si no esta, para Realtime API support) |
| `frontend_react/package.json` | Verificar dependencia de WebSocket (nativa del browser, no requiere paquete extra) |

### Estructura final

```
backend/
  main.py                          # + WebSocket /ws/nova handler
  services/
    nova_tools.py                  # NEW: 20 tools
  routes/
    nova_routes.py                 # NEW: REST endpoints

frontend_react/src/
  components/
    NovaWidget.tsx                 # NEW: voice widget
  index.css                        # + nova animations
  App.tsx                          # + <NovaWidget />
```

---

## 9. Dependencias

### Backend

| Dependencia | Version | Proposito |
|-------------|---------|-----------|
| `openai` | >= 1.40.0 | OpenAI Realtime API client (WebSocket bidireccional) |
| `websockets` | >= 12.0 | WebSocket server para FastAPI |
| `asyncpg` | (existente) | Queries a PostgreSQL |
| `python-socketio` | (existente) | Emision de eventos real-time al frontend |

### Frontend

| Dependencia | Version | Proposito |
|-------------|---------|-----------|
| Browser WebSocket API | nativa | Conexion al backend Nova |
| Browser MediaRecorder API | nativa | Captura de audio del microfono |
| Browser AudioContext API | nativa | Reproduccion de audio de respuesta |

### Servicios externos

| Servicio | Variable de entorno | Proposito |
|----------|---------------------|-----------|
| OpenAI Realtime API | `OPENAI_API_KEY` | Transcripcion de voz, intent detection, function calling, generacion de respuesta de audio |
| YCloud | `YCLOUD_API_KEY` | (existente) Para el tool `enviar_whatsapp` |

### Configuracion requerida

```env
# En .env
OPENAI_API_KEY=sk-...          # Debe tener acceso a Realtime API
```

**Nota:** El Realtime API de OpenAI se factura por minuto de audio (input + output). Costo estimado: ~$0.06/min con `gpt-4o-mini-realtime-preview`, ~$0.20/min con `gpt-4o-realtime-preview`. El modelo economico es suficiente para uso diario; el premium se reserva para demos o clientes enterprise.

---

## 10. Consideraciones de implementacion

### Multi-tenant (CRITICO)
Cada query en `nova_tools.py` DEBE incluir `WHERE tenant_id = $x`. El `tenant_id` se extrae del JWT/WebSocket auth, nunca del request del usuario. Esto aplica identico a ClinicForge.

### Date handling
Todos los argumentos de tools llegan como strings desde OpenAI. Usar helpers `_parse_date_str()` y `_parse_datetime_str()` para convertir antes de pasar a asyncpg. Copiar de ClinicForge `nova_tools.py`.

### Socket.IO events para sync

| Evento | Emitido por | UI que actualiza |
|--------|-------------|------------------|
| `NEW_LEAD` | registrar_lead | LeadsView |
| `LEAD_UPDATED` | actualizar_lead, mover_lead_etapa | LeadsView, PipelineView |
| `LEAD_STATUS_CHANGED` | cambiar_estado_lead | LeadsView, PipelineView, DashboardView |
| `PIPELINE_UPDATED` | mover_lead_etapa | PipelineView |
| `NEW_EVENT` | agendar_llamada | AgendaView |
| `EVENT_CANCELLED` | cancelar_evento | AgendaView |
| `NEW_MESSAGE` | enviar_whatsapp | ChatsView |

### Error handling
Si un tool falla, Nova debe decir que algo del contexto no es lo que deberia de ser ("No encontre a ese lead", "Esa fecha ya paso") en lugar de errores tecnicos. Nunca exponer stack traces ni mensajes de error de la base de datos al usuario.

### Permisos por rol
- **Vendedor:** ve solo sus leads, su agenda, sus metricas
- **Manager:** ve todo el equipo, puede filtrar por vendedor con `seller_id`
- **Admin:** acceso completo, puede cambiar configuracion de Nova

El filtro se aplica en cada tool: `AND (assigned_seller_id = $seller_id OR $role IN ('manager', 'admin'))`.
