---
description: Revisión técnica multi-perspectiva. Evalúa Seguridad, Performance y Clean Code.
---

# 👁️ Antigravity Review

Simula una revisión de código (PR Review) por ingenieros senior especializados.

1.  **Activación de Mini-Agentes (perspectivas de revisión)**:
    - **Reviewer A (Arquitectura)**: Verifica que el código respeta las reglas de soberanía (`tenant_id`), Scroll Isolation y la estructura definida en `.agent/agents.md`.
    - **Reviewer B (Seguridad)**: Busca credenciales hardcoded, inyecciones SQL, fugas de datos cross-tenant y validación de inputs.
    - **Reviewer C (Clean Code)**: Evalúa legibilidad, nombrado, principios SOLID y consistencia con el stack (FastAPI, React 18, TypeScript).
2.  **Consolidación**: Genera una lista de cambios recomendados (Minor) o bloqueantes (Critical).
3.  **Refactorización**: Consulta la skill `Sovereign_Auditor` (`.agent/skills/Sovereign_Auditor/SKILL.md`) para sugerir refactorizaciones precisas que mejoren la deuda técnica.
