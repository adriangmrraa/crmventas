"""
Nexus AI Security — Prompt Injection Detection
CRM Ventas | Basado en ClinicForge Nexus Security v7.6.
Actúa como primera capa de defensa determinista antes del LLM.
"""
import re
import logging

logger = logging.getLogger("orchestrator.security")

# Lista negra de patrones de inyección (SDD v2.0 — 10 patrones base)
PROMPT_INJECTION_PATTERNS = [
    r"ignore (all )?previous instructions",
    r"ignore (the )?instructions above",
    r"disregard (all )?previous instructions",
    r"forget (everything|what) you (were|have been) told",
    r"you are now (in )?developer mode",
    r"system override",
    r"new instructions:",
    r"output the system prompt",
    r"reveal your instructions",
    r"instead of your previous task",
    r"bypass security",
    r"act as (if )?you (are|were) (a )?different",
    r"pretend (you are|to be) (a )?different",
]


def detect_prompt_injection(text: str) -> bool:
    """
    Detecta intentos de Prompt Injection o Jailbreaking.
    Retorna True si se detecta un patrón de ataque.
    """
    if not text:
        return False

    t = text.lower()
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, t, re.IGNORECASE):
            logger.warning(
                f"🚨 Nexus Security: Prompt Injection detectado! Patrón: '{pattern}'"
            )
            return True

    return False


def sanitize_input(text: str) -> str:
    """
    Sanitización básica para evitar roturas de formato en prompts.
    Elimina caracteres de control y backticks excesivos.
    """
    if not text:
        return ""
    # Eliminar backticks triples que pueden confundir el parser de tools
    sanitized = text.replace("```", "")
    # Eliminar null bytes y otros caracteres de control
    sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", sanitized)
    return sanitized.strip()
