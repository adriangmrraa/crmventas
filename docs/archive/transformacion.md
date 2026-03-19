Reporte Técnico: Ingeniería de Prompts para la Refactorización de Dentalogic a Nexus Core CRM

Este reporte técnico, elaborado por la arquitectura de soluciones de IA, define la estrategia de "Code Morphing" para la transformación del sistema clínico Dentalogic en una plataforma agnóstica de CRM y ventas denominada Nexus Core CRM. El objetivo es capitalizar la infraestructura multi-tenant y la soberanía de datos existente, inyectando una nueva lógica de negocio mediante ingeniería de prompts de alta precisión.


--------------------------------------------------------------------------------


1. ANÁLISIS DE LA ARQUITECTURA BASE (GROUND TRUTH)

La infraestructura de Dentalogic se basa en una arquitectura de microservicios robusta, diseñada para el aislamiento total de datos (SaaS). Según el Source Context, los componentes clave son:

* WhatsApp Service (Puerto 8002): Interfaz de comunicación con clientes mediante YCloud, encargada de la transcripción Whisper, deduplicación en Redis y relay de audio.
* Orchestrator Service (Puerto 8000): El núcleo del sistema basado en FastAPI y LangChain. Gestiona la lógica de agentes, el cerebro híbrido (Local/Google Calendar) y la coordinación multi-tenant.
* Frontend React (Puerto 5173/80): Centro de operaciones basado en Vite y Tailwind CSS que implementa el estándar visual Sovereign Glass.

Identidades Técnicas a Mantener

Elemento Clave	Implementación Técnica	Propósito en Nexus Core CRM
Seguridad de Triple Capa	JWT (Identidad) + X-Admin-Token (Infraestructura)	Garantizar que ninguna refactorización exponga la API a accesos externos sin tokens de bóveda.
Persistencia Evolutiva	Maintenance Robot (db.py)	Automatizar la migración del esquema mediante parches idempotentes en el arranque del servicio.
Soberanía de Datos	Aislamiento por tenant_id	Asegurar que los leads y transacciones de una empresa nunca sean visibles para otra.


--------------------------------------------------------------------------------


2. PROMPT MAESTRO 1: REESTRUCTURACIÓN DE CÓDIGO (CORE VS NICHE)

Propósito: Transformar la estructura de archivos en un esquema jerárquico que separe el núcleo agnóstico (Core) de la lógica vertical de ventas (Niche).

Prompt:

"Actúa como un Senior AI Architect. Reorganiza los directorios de orchestrator_service/ y frontend_react/ para evolucionar Dentalogic hacia Nexus Core CRM. Crea una carpeta core/ para lógica agnóstica y niche/crm_sales/ para lógica específica.

Ejecuta los siguientes movimientos de archivos y refactorizaciones críticas:

1. shared/models_dental.py -> core/models/base_models.py.
2. orchestrator_service/main.py -> core/api/main.py.
3. orchestrator_service/logic/dental_tools.py -> niche/crm_sales/sales_tools.py.

Restricciones de Ingeniería:

* Resolución de Importaciones: Refactoriza todos los imports relativos a imports absolutos partiendo de la nueva raíz del proyecto.
* Infraestructura: Actualiza el WORKDIR y las instrucciones CMD en los Dockerfiles para reflejar los nuevos puntos de entrada, garantizando compatibilidad con el despliegue en EasyPanel.
* Modelos: Asegura que la lógica en niche/ herede de las clases base en core/models/ para mantener la integridad estructural."


--------------------------------------------------------------------------------


3. PROMPT MAESTRO 2: ABSTRACCIÓN DE DATOS Y ESQUEMA SOBERANO

Propósito: Transformar el esquema relacional clínico en uno de ventas, manteniendo la compatibilidad con el sistema de parches automáticos.

Prompt:

"Redacta un script de ingeniería de datos para transformar db/init/dentalogic_schema.sql en nexus_core_schema.sql. Renombra las entidades manteniendo la integridad referencial:

* patients -> leads
* professionals -> sales_agents
* appointments -> deals_meetings
* clinical_records -> interaction_logs

Requisitos Técnicos Obligatorios:

* Soberanía: Cada tabla debe incluir la columna tenant_id y el índice crítico idx_leads_tenant_phone en (tenant_id, phone_number).
* Compatibilidad con Smart SQL Splitter: El script debe ser compatible con el divisor de SQL que utiliza ; pero respeta los bloques DO $$.
* Evolución Idempotente: Todas las migraciones deben redactarse como bloques DO $$ para el Evolution Pipeline de db.py, asegurando que el Maintenance Robot pueda ejecutarlas sin errores en reinicios."


--------------------------------------------------------------------------------


4. PROMPT MAESTRO 3: REINYECCIÓN DE PERSONA (DE CLÍNICO A SALES SETTER)

Propósito: Reconfigurar el agente LangChain para que actúe como un persuasivo "Sales Setter" argentino.

Prompt:

"Reconfigura el sys_template del agente en main.py. La nueva persona es un 'Senior Sales Setter'.

* Perfil: Persuasivo, profesional y orientado a la conversión de leads.
* Localización (Argentina): Utiliza el voseo ('fijate', 'te cuento'). Política de Puntuación: Aplica el estándar humano de WhatsApp en Argentina: usa signos de interrogación únicamente al final de la oración (?).
* Mapeo de Tools:
  * check_availability -> Ahora busca huecos para 'Demos de Venta' o 'Reuniones de Cierre'.
  * triage_urgency -> Se convierte en lead_scoring, clasificando al prospecto según interés y potencial de compra.
* Regla de Oro: Protocolo 'Service-First'. Debes definir la propuesta de valor y calificar la necesidad del lead antes de ofrecer la agenda."


--------------------------------------------------------------------------------


5. PROMPT MAESTRO 4: INTERFAZ 'SOVEREIGN GLASS' PARA VENTAS

Propósito: Refactorizar el dashboard administrativo para KPIs de ventas, respetando los estándares de visualización de alta densidad.

Prompt:

"Refactoriza DashboardView.tsx y el módulo de Analytics. Sustituye los KPIs clínicos por métricas de CRM:

1. Conversaciones IA: Calculadas mediante COUNT(DISTINCT from_number).
2. Tasa de Conversión: Porcentaje de leads que transicionan a estatus 'Deal'.
3. Ingresos Proyectados: Basados en accounting_transactions.

Lógica de Negocio (Sovereign Analytics): Solo computa ingresos si la transacción está en estatus 'completed' Y el 'deal_meeting' asociado está marcado como 'attended' o 'completed' (evitar inflación de métricas).

Estándar Sovereign Glass:

* Aplica aislamiento de scroll mediante flex-1 min-h-0.
* Nota Técnica: El uso de min-h-0 es mandatorio para asegurar que el contenedor hijo pueda contraerse y activar el scroll interno correctamente en Chrome y Safari."


--------------------------------------------------------------------------------


6. VALIDACIÓN DE SEGURIDAD Y SEGURIDAD DE TRIPLE CAPA

Es crítico que la refactorización no degrade la postura de seguridad del sistema original.

Instrucción de Validación para la IA:

"Verifica que todas las nuevas rutas de CRM en admin_routes.py estén envueltas en la dependencia verify_admin_token. Queda estrictamente prohibido el 'Vibe Coding' (hardcodear credenciales). Todas las integraciones con CRMs externos deben almacenar sus tokens en la credentials_vault utilizando el cifrado Fernet definido en CREDENTIALS_FERNET_KEY."

Checklist de Integridad Post-Refactorización

* [ ] ¿Se mantiene el filtrado explícito WHERE tenant_id = $x en todas las consultas de CRM?
* [ ] ¿El X-Admin-Token es obligatorio para todas las rutas /admin/*?
* [ ] ¿El tenant_id se resuelve desde el JWT y nunca desde parámetros de URL?
* [ ] ¿Se utiliza la clave Fernet para persistir secretos de integración?


--------------------------------------------------------------------------------


7. NOTAS DE IMPLEMENTACIÓN (MAINTENANCE ROBOT)

El "Maintenance Robot" en orchestrator_service/db.py garantiza que Nexus Core CRM sea una plataforma de auto-sanación. A continuación, el parche de migración para la entidad de leads que debe incluirse en el Evolution Pipeline:

# Ejemplo de parche en Evolution Pipeline (db.py) para Nexus Core
async def patch_016_create_leads_table(conn):
    await conn.execute("""
    DO $$ 
    BEGIN 
        IF NOT EXISTS (SELECT FROM pg_tables WHERE tablename = 'leads') THEN
            CREATE TABLE leads (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id INTEGER REFERENCES tenants(id),
                first_name TEXT,
                last_name TEXT,
                phone_number TEXT,
                status TEXT DEFAULT 'new',
                lead_score TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            -- Índice crítico para performance de WhatsApp y soberanía
            CREATE INDEX idx_leads_tenant_phone ON leads(tenant_id, phone_number);
        END IF;
    END $$;
    """)


Este enfoque de refactorización asegura que la transición de Dentalogic a Nexus Core CRM mantenga la excelencia técnica, la escalabilidad SaaS y la integridad de los datos en cada etapa del despliegue.
