# Tasks F-05: Empresas / Companies Management

**Spec:** `05-empresas.spec.md`
**Design:** `design/design-F05.md`
**Fecha:** 2026-04-14

---

## Fase 1: Error Handling en Delete (MUST)

- [ ] **T01** Agregar estado `deleteError` (`string | null`) a `CompaniesView.tsx`
- [ ] **T02** Modificar `handleDelete`: capturar error, setear `deleteError` segun status (400 = mensaje backend, otro = mensaje generico), NO cerrar modal
- [ ] **T03** Resetear `deleteError` a `null` cuando se abre un nuevo modal de delete (`setDeleteTarget`)
- [ ] **T04** Renderizar `deleteError` dentro del modal de confirmacion, encima de los botones, en div rojo con icono `AlertCircle`
- [ ] **T05** Agregar texto de advertencia cascada al modal: "Esto eliminara todos los datos asociados (leads, mensajes, vendedores) de manera irreversible."

## Fase 2: Validacion Telefono (MUST)

- [ ] **T06** Definir constante `PHONE_REGEX = /^\+?[0-9]{7,15}$/` en `CompaniesView.tsx`
- [ ] **T07** Agregar estado `phoneError` (`string | null`)
- [ ] **T08** En `handleSubmit`, validar `bot_phone_number` contra `PHONE_REGEX` antes del API call. Si falla, setear `phoneError` y return
- [ ] **T09** Mostrar `phoneError` debajo del input `bot_phone_number` en texto rojo
- [ ] **T10** Limpiar `phoneError` al cambiar el valor del input (`onChange`)

## Fase 3: UX Improvements (SHOULD)

- [ ] **T11** Reemplazar `ID: {clinica.id}` en footer de tarjeta por `Creado: {new Date(clinica.created_at).toLocaleDateString('es-AR')}`
- [ ] **T12** Agregar constante `TIMEZONE_OPTIONS` con las 5 opciones definidas en la spec
- [ ] **T13** Agregar campo `timezone` al estado `formData` con default `America/Argentina/Buenos_Aires`
- [ ] **T14** Cargar timezone desde `clinica.config?.timezone` al abrir modal de edicion
- [ ] **T15** Agregar select de timezone al formulario del modal, debajo de calendar provider
- [ ] **T16** Incluir `timezone` en el body de POST y PUT al backend

## Fase 4: Busqueda Inline (SHOULD)

- [ ] **T17** Agregar estado `searchTerm` (string)
- [ ] **T18** Filtrar `companies` por `clinic_name` usando `searchTerm` (case-insensitive)
- [ ] **T19** Renderizar input de busqueda con icono `Search` solo cuando `companies.length > 5`
- [ ] **T20** Usar `filteredCompanies` en el `.map()` de la grid en vez de `companies`

## Fase 5: Backend — Timezone (SHOULD)

- [ ] **T21** Agregar campo `timezone: Optional[str]` al modelo `TenantUpdate` en `admin_routes.py`
- [ ] **T22** Validar timezone contra whitelist de 5 valores permitidos
- [ ] **T23** Persistir timezone en `config` JSONB con `jsonb_set`

## Fase 6: Tests

- [ ] **T24** Test: delete con error 400 muestra mensaje del backend en modal sin cerrar
- [ ] **T25** Test: delete con error 500 muestra mensaje generico en modal
- [ ] **T26** Test: `bot_phone_number = "abc"` no llama a `api.post/put`, muestra error inline
- [ ] **T27** Test: `bot_phone_number = "+541112345678"` pasa validacion
- [ ] **T28** Test: `bot_phone_number = "1234567"` (7 digitos, minimo) pasa validacion
- [ ] **T29** Test: footer tarjeta muestra fecha formateada, no ID
- [ ] **T30** Test: formulario incluye select de timezone con 5 opciones

---

## Dependencias entre fases

```
Fases 1, 2, 3, 4 son independientes entre si (todas en CompaniesView.tsx)
Fase 5 (backend) es independiente del frontend
Fase 6 (tests) depende de Fases 1-4
```

## Estimacion

| Fase | Esfuerzo |
|------|----------|
| Fase 1 | 0.5h |
| Fase 2 | 0.5h |
| Fase 3 | 1h |
| Fase 4 | 0.5h |
| Fase 5 | 0.5h |
| Fase 6 | 1.5h |
| **Total** | **~4.5h** |
