from langchain.tools import tool


@tool
async def lead_scoring(message: str) -> str:
    """
    Analiza un mensaje de un prospecto y devuelve una clasificación cualitativa del lead
    (por ejemplo: cold, warm, hot) junto con una breve explicación.

    Esta tool está pensada para el nicho CRM (vendedores/setters) y reemplaza conceptualmente
    al triage_urgency dental. La implementación actual es solo un esqueleto y deberá
    enriquecerse cuando se active el nicho crm_sales.
    """
    return (
        "Esqueleto lead_scoring activo. Aún no se ha implementado la lógica de scoring "
        "para CRM; este tool debe ser conectado cuando el nicho crm_sales esté habilitado."
    )


@tool
async def list_templates() -> str:
    """
    Devuelve (en el futuro) la lista de plantillas de mensaje aprobadas por Meta
    disponibles para el tenant actual. Por ahora es un stub seguro, sin efectos
    en base de datos ni en sistemas externos.
    """
    return (
        "Esqueleto list_templates activo. En la versión CRM, este tool listará las "
        "plantillas de WhatsApp aprobadas para el tenant, pero todavía no está implementado."
    )


@tool
async def book_sales_meeting(
    date_time: str,
    lead_reason: str,
    lead_name: str | None = None,
    preferred_agent_name: str | None = None,
) -> str:
    """
    Reserva una reunión de ventas (demo o call de cierre) para un lead.

    Parámetros (contrato preliminar):
    - date_time: string legible tipo 'miércoles 17:00' o 'tomorrow 15:30' (se alineará
      con el parser de fechas agnóstico ya existente).
    - lead_reason: motivo principal de la reunión (producto/servicio de interés).
    - lead_name: nombre del lead si está disponible.
    - preferred_agent_name: nombre del vendedor/setter preferido, si aplica.

    Implementación actual:
    Stub que documenta el contrato y evita efectos secundarios, hasta que
    el módulo CRM esté completamente cableado a la base de datos.
    """
    return (
        "Esqueleto book_sales_meeting activo. Todavía no se registra ninguna reunión "
        "en la base de datos; este tool se implementará cuando el nicho crm_sales "
        "esté listo para operar."
    )


CRM_SALES_TOOLS = [lead_scoring, list_templates, book_sales_meeting]

