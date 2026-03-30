# SPEC: UX — Buscador global con Full-Text Search (FTS)

**Ticket:** DEV-54
**Fecha:** 2026-03-29
**Prioridad:** Media
**Esfuerzo:** Medio (3 días)
**Confidence:** 95%

---

## 2. Requerimientos Técnicos

### 2.1 Backend: Motor de Búsqueda

1. **Postgres FTS:**
   - Crear un índice `GIN` sobre una columna calculada o vista que combine:
     - Leads: nombre, apellido, email, teléfono, notas.
     - Mensajes: contenido (truncado).
   - Uso de `to_tsvector('spanish', ...)` para soporte multilingüe.

2. **Endpoint de Búsqueda:**
   - `GET /admin/core/crm/search?q=termino`
   - Búsqueda "fuzzy" y por rankings de relevancia.

### 2.2 Frontend: Interfaz de Búsqueda

1. **Global Search Bar:**
   - Ubicada en el header superior accesible desde cualquier vista.
   - Resultados rápidos (popover) divididos por categorías: Leads, Conversaciones, Tareas.

---

## 3. Acceptance Criteria

- [ ] La búsqueda devuelve resultados relevantes en menos de 300ms.
- [ ] Se puede buscar por fragmentos de conversaciones antiguas.
- [ ] Al hacer clic en un resultado, navega directamente a la vista correspondiente con el contexto cargado.
- [ ] Respeta el aislamiento por `tenant_id` (crucial).
