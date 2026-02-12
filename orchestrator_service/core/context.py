from contextvars import ContextVar
from typing import Optional

# ContextVars para rastrear el usuario en la sesión de LangChain
current_customer_phone: ContextVar[Optional[str]] = ContextVar("current_customer_phone", default=None)
current_patient_id: ContextVar[Optional[int]] = ContextVar("current_patient_id", default=None)
current_tenant_id: ContextVar[int] = ContextVar("current_tenant_id", default=1)
