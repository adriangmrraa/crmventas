# Diseño de System Prompt por Nicho

Este documento define cómo gestionar la "personalidad" del agente (System Prompt) de forma dinámica, permitiendo que un tenant dental tenga un asistente clínico y un tenant CRM tenga un setter de ventas.

## 1. Estrategia de Almacenamiento

Se propone almacenar los prompts como archivos de texto plano (templates Jinja2) dentro del módulo de cada nicho. Esto facilita la edición y el control de versiones (Git) frente a tenerlos en base de datos.

### Estructura de Archivos
```text
orchestrator_service/
├── modules/
│   ├── dental/
│   │   ├── prompts/
│   │   │   ├── base_assistant.txt   # Prompt principal dental
│   │   │   └── triage_rules.txt     # Reglas de triaje
│   └── crm_sales/
│       ├── prompts/
│       │   ├── setter_v1.txt        # Prompt de ventas agresivo
│       │   └── setter_soft.txt      # Prompt de ventas consultivo
```

## 2. Inyección de Contexto (Templating)

Usaremos **Jinja2** para inyectar variables dinámicas en tiempo de ejecución (al inicio de la conversación o al refrescar el prompt).

### Ejemplo de Template (`base_assistant.txt`)
```jinja2
Sos el asistente virtual de {{ clinic_name }}, ubicado en {{ clinic_location }}.
Tu objetivo es ayudar a los pacientes a agendar turnos y responder dudas.

Horarios de atención:
{% for day, hours in working_hours.items() %}
- {{ day }}: {{ hours }}
{% endfor %}

Reglas de Negocio:
1. Siempre saludá con el nombre del paciente si lo sabés.
2. Usá los siguientes tratmientos disponibles: {{ treatment_list }}.
```

## 3. Implementación del Loader

**`orchestrator_service/core/agent/prompt_loader.py`**:

```python
from jinja2 import Environment, FileSystemLoader

class PromptLoader:
    def __init__(self, modules_path="modules"):
        self.env = Environment(loader=FileSystemLoader(modules_path))

    def load_prompt(self, niche_type, template_name, context_data):
        """
        Carga un template y lo renderiza con los datos del tenant.
        """
        template_path = f"{niche_type}/prompts/{template_name}"
        template = self.env.get_template(template_path)
        return template.render(**context_data)
```

## 4. Obtención del Contexto

Cada nicho debe definir qué datos necesita inyectar.

**`orchestrator_service/modules/dental/context.py`**:

```python
async def get_dental_context(tenant_id):
    # Obtener datos de la DB
    treatments = await db.get_active_treatments(tenant_id)
    clinic_info = await db.get_tenant_info(tenant_id)
    
    return {
        "clinic_name": clinic_info.name,
        "clinic_location": clinic_info.location,
        "treatment_list": ", ".join([t.name for t in treatments]),
        "working_hours": clinic_info.working_hours
    }
```

## 5. Integración en `main.py`

```python
# Al crear el agente
context_data = await niche_module.get_context(tenant_id)
system_prompt_text = prompt_loader.load_prompt(
    niche_type="dental", 
    template_name="base_assistant.txt", 
    context_data=context_data
)

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt_text),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])
```
