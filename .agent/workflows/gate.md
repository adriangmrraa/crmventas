---
description: Umbral de Calidad basado en Confianza. Evalúa la viabilidad de la implementación antes de ejecutar.
---

# 🚪 Antigravity Gate

Punto de control crítico para evitar el "Vibe Coding" de alto riesgo.

1.  **Evaluación de Complejidad**: Analiza el Plan y la Spec.
2.  **Cálculo de Confianza**:
    - **Alta (90-100%)**: Spec clara, herramientas probadas, ruta conocida.
    - **Media (70-89%)**: Spec buena pero con riesgos técnicos menores.
    - **Baja (< 70%)**: Spec vaga, herramientas experimentales o lógica contradictoria.
3.  **Acción**:
    - Si es **Baja**: El agente se bloquea y sugiere ejecutar `/clarify` o `/refine`.
    - Si es **Media/Alta**: Presenta los riesgos y pide un "Go" explícito del usuario para `/implement`.
4.  **Habilitación de Skill**: Consulta las skills disponibles en `.agent/agents.md` y valida que la estrategia de ejecución cuenta con las capacidades necesarias (Backend_Sovereign, Frontend_Nexus, DB_Evolution, etc.).
