---
name: "Template Transplant Specialist"
description: "Extrae y distribuye instrucciones de un system prompt legacy en las capas correctas (Wizard, Tool Config, Sistema Interno)."
trigger: "template, trasplante, system prompt, legacy, agente, wizard, tool config"
scope: "AI_AGENTS"
auto-invoke: false
---

# Template Transplant Specialist

## Proposito

Esta skill te permite **extraer system prompts de proyectos legacy** y distribuirlos correctamente en la arquitectura multi-capa de CRM Ventas:

1. **Wizard** (configuracion del agente en el frontend)
2. **Tool Config** (instrucciones tacticas y guias de respuesta por herramienta)
3. **Interno** (reglas de sistema no editables)

## Cuando Usar Esta Skill

- Tienes un system prompt legacy de otro proyecto (ej: Inmobiliaria Bot, Seguros Asistente, E-commerce Bot)
- Necesitas integrarlo en CRM Ventas manteniendo su esencia
- Quieres asegurar que las instrucciones esten en los lugares correctos

## Proceso de Trasplante

### Paso 1: Analisis del System Prompt

Lee el system prompt completo del proyecto legacy e identifica las 3 capas:

#### WIZARD (Editable por Usuario)
Campos que van en `orchestrator_service/app/api/agents.py` -> `AGENT_TEMPLATES`:

- **business_name**: Nombre del negocio/empresa
- **business_context**: Descripcion del rubro (inmobiliaria, seguros, servicios, etc.)
- **tone_and_personality**: Estilo de comunicacion (tono, puntuacion, voseo, etc.)
- **synonym_dictionary**: Diccionario de sinonimos (mapeo de terminos informales a categorias base)
- **business_rules**: Reglas de negocio especificas (derivaciones, politicas, calificacion de leads, etc.)
- **catalog_knowledge**: Mapa de categorias y estructura del catalogo de productos/servicios
- **store_website**: URL del negocio

#### TOOL CONFIG (Por Herramienta)
Instrucciones por tool en `orchestrator_service/main.py` -> `tactical_injections` + `response_guides`:

Para cada herramienta, extrae:
- **Tactica**: Reglas de CUANDO y COMO usar la tool (gatillos, validaciones, mapeos)
- **Guia de Respuesta**: Reglas de COMO formatear la salida (estructura, CTAs, limitaciones)

Herramientas tipicas:
- `search_specific_products`
- `browse_general_storefront`
- `search_by_category`
- `derivhumano`
- `orders`
- `cupones_list`
- `search_knowledge_base`
- `sendemail`

#### INTERNO (Sistema - Hardcoded)
Reglas que van en el core del system prompt (no editables por el usuario):

- **PRIORIDADES**: Orden de ejecucion (JSON Output, Veracidad, Anti-Repeticion, Anti-Bucle)
- **REGLA DE VERACIDAD**: Prohibiciones de inventar datos (precios, stock, links)
- **REGLAS DE CONTENIDO**: Formato de texto (prohibido markdown, URLs limpias, etc.)
- **FORMAT INSTRUCTIONS**: Esquema JSON de salida

### Paso 2: Extraccion Textual

Crea un documento `.md` con la distribucion extraida:

```markdown
# WIZARD

### business_name
[TEXTO EXTRAIDO]

### tone_and_personality
[TEXTO EXTRAIDO]

...

# TOOL CONFIG

### search_specific_products

**TACTICA:**
[TEXTO EXTRAIDO]

**GUIA DE RESPUESTA:**
[TEXTO EXTRAIDO]

...

# INTERNO

### PRIORIDADES
[TEXTO EXTRAIDO]

...
```

Guarda este documento en `docs/plantilla_[nombre_proyecto].md`.

### Paso 3: Integracion en el Codigo

#### Opcion A: Hardcoded Template (Legacy/Fallback)

Edita `orchestrator_service/app/api/agents.py`:

```python
AGENT_TEMPLATES = {
    "sales": {
        "defaultValue": {
            "agent_name": "[business_name extraido]",
            "agent_tone": "[tone_and_personality extraido]",
            "synonym_dictionary": "[synonym_dictionary extraido]",
            "business_rules": "[business_rules extraido]",
            "catalog_knowledge": "[catalog_knowledge extraido]",
            "store_website": "[store_website extraido]"
        }
    }
}
```

#### Opcion B: Database Template (Recomendado)

Inserta el template directamente en la base de datos para que sea dinamico y global:

```sql
INSERT INTO agents (
    name, role, system_prompt_template, config, enabled_tools,
    is_template, tenant_id, is_active
) VALUES (
    'Nombre del Template',
    'sales',
    'Eres un asistente virtual de...', -- Prompt Base
    '{
        "agent_name": "...",
        "agent_tone": "...",
        "business_rules": "...",
        "synonym_dictionary": "...",
        "store_description": "..."
    }'::jsonb,
    '["search_specific_products", "search_by_category", "orders"]'::jsonb,
    TRUE, -- Marcado como Template
    NULL, -- NULL = Global (Visible para todos los tenants)
    FALSE -- Inactivo por defecto
);
```

> IMPORTANTE: Los templates en DB aparecen automaticamente en el Wizard. El Orchestrator los identifica por `is_template = TRUE`. Si `tenant_id` es `NULL`, la plantilla es **Global** (visible para todos los tenants del CRM).

#### Actualizar Tool Instructions

Edita `orchestrator_service/main.py`:

```python
tactical_injections = {
    "search_specific_products": """[TACTICA EXTRAIDA COMPLETA]""",
    "derivhumano": """[TACTICA EXTRAIDA COMPLETA]""",
    # ... resto de tools
}

response_guides = {
    "search_specific_products": """[GUIA DE RESPUESTA EXTRAIDA COMPLETA]""",
    "derivhumano": """[GUIA DE RESPUESTA EXTRAIDA COMPLETA]""",
    # ... resto de tools
}
```

### Paso 4: Verificacion

1. **Frontend**: Abri el Agent Wizard y verifica que los campos esten pre-poblados
2. **Tool Modal**: Abri "Configurar Herramientas" y verifica que las instrucciones aparezcan
3. **Chat Test**: Proba el agente con consultas tipicas del dominio

## Ejemplo Completo: Inmobiliaria Premium

Ver `docs/plantilla_inmobiliaria_premium.md` para referencia completa.

### Extractos Clave

#### Wizard - Tono y Personalidad
```
**Estilo:** Habla como un asesor inmobiliario profesional y cercano. Usa "usted" en primer contacto, transiciona a "tu" cuando el lead muestra confianza.
**Puntuacion (ESTRICTO):** Usa signos de pregunta solo al final (?), nunca el de apertura.
**Naturalidad:** Usa frases puente como "Mira", "Te comento", "Fijate que tenemos", "Excelente eleccion".
```

#### Tool Config - search_specific_products

**TACTICA:**
```
BUSQUEDA INTELIGENTE: Si piden "Departamento 2 ambientes Palermo", busca "Departamento 2 ambientes" y filtra por zona internamente.

REGLA DE MAPEO: Antes de usar esta tool, compara la palabra con el Diccionario de Sinonimos (ej: "depto" -> "Departamento", "monoambiente" -> "1 ambiente").

GATE: Usa `search_specific_products` SIEMPRE que pidan algo especifico (tipo de propiedad, zona, rango de precio).
```

**GUIA DE RESPUESTA:**
```
OBJETIVO PRINCIPAL: Mostrar 3 OPCIONES si la tool devuelve suficientes resultados.

FORMATO DE PRESENTACION (WHATSAPP - LIMPIO):
Secuencia OBLIGATORIA: Intro -> Prop 1 -> Prop 2 -> Prop 3 -> CTA.

REGLA DE CALL TO ACTION:
- CASO 1 (PROPIEDADES PREMIUM): Ofrecer "Visita personalizada con asesor"
- CASO 2 (MUCHOS RESULTADOS): Link al catalogo web con filtros aplicados
- CASO 3 (POCOS RESULTADOS): Ofrecer ampliar la busqueda o contacto directo con closer
```

## Checklist de Integracion

- [ ] Documento de plantilla creado en `docs/plantilla_[proyecto].md`
- [ ] `AGENT_TEMPLATES` actualizado en `agents.py` con wizard defaults
- [ ] `tactical_injections` actualizado en `main.py` con tacticas completas
- [ ] `response_guides` actualizado en `main.py` con guias completas
- [ ] Wizard muestra campos pre-poblados
- [ ] Modal "Configurar Herramientas" muestra instrucciones
- [ ] Agente responde segun la personalidad y reglas del legacy

## Reglas de Oro

1. **COPIA TEXTUAL**: No resumas ni adaptes. Copia el texto EXACTO del legacy.
2. **RESPETA LA DISTRIBUCION**: Si una instruccion menciona "SIEMPRE" o es una regla critica, va en Tool Config o Interno, NO en Wizard.
3. **MAXIMA FIDELIDAD**: El objetivo es que el agente se comporte IDENTICAMENTE al legacy.
4. **DOCUMENTA TODO**: El archivo `.md` de plantilla es la fuente de verdad.

## Troubleshooting

### Problema: Las instrucciones no aparecen en el modal
**Causa**: El endpoint `/admin/tools` no esta retornando `prompt_injection` y `response_guide`.
**Solucion**: Verifica que `admin_routes.py` -> `get_tools` este usando `SYSTEM_TOOL_INJECTIONS` y `SYSTEM_TOOL_RESPONSE_GUIDES`.

### Problema: El agente no sigue las reglas
**Causa**: Las instrucciones estan en el lugar equivocado (ej: reglas criticas en Wizard en vez de Interno).
**Solucion**: Revisa la distribucion y muevelas a la capa correcta.

### Problema: El tono no coincide con el legacy
**Causa**: `tone_and_personality` incompleto o generico.
**Solucion**: Extrae TODO el bloque de "TONO Y PERSONALIDAD" del legacy, incluyendo puntuacion, voseo, frases puente, y prohibiciones.

## Archivos Clave

| Archivo | Proposito |
|---------|-----------|
| `docs/plantilla_[proyecto].md` | **Fuente de verdad** del trasplante |
| `orchestrator_service/app/api/agents.py` | Wizard defaults (AGENT_TEMPLATES) |
| `orchestrator_service/main.py` | Tool instructions (tactical_injections + response_guides) |
| `orchestrator_service/admin_routes.py` | Endpoint que sirve las tools con sus instructions |
| `frontend_react/src/views/Stores.tsx` | Modal "Configurar Herramientas" |
