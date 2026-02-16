Ejecuta el **workflow New Feature** (nueva funcionalidad).

**Instrucción:** Sigue `CRM VENTAS/.agent/workflows/new_feature.md`. Análisis de impacto (DB, credenciales, servicios, multi-tenancy), implementación backend first en orchestrator_service, luego frontend en frontend_react. Sovereign check: todas las queries con tenant_id, credenciales por tenant, scroll isolation. Todo dentro de CRM VENTAS.
