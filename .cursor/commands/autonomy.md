Ejecuta el **workflow Autonomy** (motor autónomo).

**Instrucción:** Sigue `CRM VENTAS/.agent/workflows/autonomy.md`. Encadena: specify → (clarify si hay ambigüedades) → plan → (gate: umbral de confianza) → implement → verify → update-docs (y opcionalmente advisor, audit, review, push, finish según el flujo SDD). Respeta spec-first, soberanía multi-tenant y no ejecutar SQL directo. Condiciones de parada: confianza < 70%, drift respecto a spec, o tests fallan 3 veces. Usa skills y reglas de `CRM VENTAS/.agent/agents.md`.
