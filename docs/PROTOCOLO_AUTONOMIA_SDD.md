# 📜 Protocolo de Autonomía SDD (v2.0)
## Lógica de Decisión Transversal del Agente Antigravity

Este documento establece las reglas de gobernanza y autonomía para el Agente Antigravity dentro del ecosistema **CRM Ventas**. Define cuándo el agente debe actuar, cuándo debe detenerse y cómo debe garantizar la integridad de la arquitectura.

---

### 1. El Ciclo de Retroalimentación de Diseño (El Salto Automático)
Para garantizar que cada línea de código responda a una necesidad de negocio validada, se establece el siguiente flujo obligatorio:

- **Trigger**: Toda nueva propuesta o feature debe iniciar con el comando `/advisor`.
- **El Salto**: La salida del `/advisor` (que analiza Ciencia, Mercado y Comunidad) debe alimentar **directamente** el proceso de `/specify`.
- **Regla**: No se permite iniciar un `/plan` sin una especificación (documento en docs/ o .spec.md) que herede las protecciones y validaciones del Advisor. Para features ya implementados, la trazabilidad está en **docs/SPECS_IMPLEMENTADOS_INDICE.md**. Si el Advisor detecta un riesgo alto, el agente tiene prohibido generar la especificación hasta que el usuario resuelva el bloqueo.

---

### 2. Criterios de Autogestión y Umbrales de Seguridad
El agente tiene autonomía delegada, pero debe ejecutar paradas técnicas obligatorias bajo estas condiciones:

#### 2.1 Detención para `/audit` (Drift Detection)
El agente debe detenerse y ejecutar un `/audit` cuando:
- Se detecten más de 3 inconsistencias entre la documentación de referencia (docs/, AGENTS.md, SPECS_IMPLEMENTADOS_INDICE) y la implementación actual en el backend.
- Se detecten cambios en los nombres de las Tools (`check_availability`, etc.) que no fueron reflejados en la documentación maestra.

#### 2.2 Detención para `/review` (Security Gate)
El agente debe bloquear la ejecución e invocar `/review` cuando:
- **Cambios en el Esquema**: Cualquier modificación en `db/init/` o parches en `db.py` que afecten a tablas críticas (`patients`, `clinical_records`).
- **Nuevas Integraciones**: Implementación de nuevos endpoints que consuman APIs externas (Meta, Google, TiendaNube) o que gestionen credenciales.
- **Flujos de Auth**: Modificaciones en el `auth_routes.py` o en la lógica de permisos de roles.

---

### 3. Garantía de Soberanía de Datos (Multi-tenancy)
La barrera técnica entre clínicas es inviolable. El agente debe verificar la presencia de `tenant_id` en cada paso:

#### 3.1 Backend Checkpoints
- **Queries SQL**: Toda sentencia SELECT, INSERT, UPDATE o DELETE debe incluir explícitamente el filtro `WHERE tenant_id = $x`.
- **Validación de Contexto**: Antes de proponer un endpoint, el agente debe verificar que el `tenant_id` se extraiga de un token validado (JWT) y no de un parámetro de URL fácilmente manipulable.

#### 3.2 Frontend Checkpoints
- **Aislamiento de Estado**: Los datos en el estado global de React deben estar segmentados por contexto de sesión.
- **Scroll Isolation**: La skill de UI debe forzar el aislamiento de scroll (`overflow-hidden` en body) para evitar fugas visuales de datos densos entre contenedores.

---

### 4. Protocolo Omega Prime (Emergencias)
En situaciones de error crítico (ej. caída de servicio SMTP o fallos de sincronización JIT):
1. **Atención Proactiva**: El agente debe imprimir los datos críticos (links de activación, logs de reserva) en la consola del Orquestador.
2. **Derivación**: Si la confianza técnica cae por debajo del 70% durante la resolución, se debe invocar `/clarify` inmediatamente.

---
*Protocolo de Autonomía SDD © 2026 - Soberanía Nexus v8.0*
