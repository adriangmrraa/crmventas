# SPEC F-05: Empresas / Companies Management

**Priority:** Media
**Complexity:** Baja
**Status:** Parcialmente implementada — CRUD completo en frontend y backend, gaps menores en UX y validación.

---

## Intent

`CompaniesView.tsx` ya expone CRUD completo contra `GET/POST/PUT/DELETE /admin/core/tenants`, con modal de creación/edición, confirmación de eliminación y soporte de `calendar_provider`. El objetivo de esta spec es documentar el estado real, cerrar los gaps de UX que quedan abiertos, y definir el comportamiento de error para cascada en eliminación.

---

## Current State

### Lo que ya funciona

- `GET /admin/core/tenants` → lista de tenants en tarjetas con `clinic_name`, `bot_phone_number`, `calendar_provider`, `created_at`. (líneas 45-55, `CompaniesView.tsx`)
- `POST /admin/core/tenants` → crea tenant con `clinic_name`, `bot_phone_number`, `calendar_provider`. (línea 87)
- `PUT /admin/core/tenants/:id` → edita los mismos campos. (línea 79)
- `DELETE /admin/core/tenants/:id` → elimina con modal de confirmación. (líneas 103-112)
- Backend en `admin_routes.py` valida `calendar_provider` en `("local", "google")`, valida unicidad de `bot_phone_number`, y bloquea eliminar el último tenant. (líneas 310-336)
- Rol `ceo` requerido para todas las operaciones (backend lo valida con `verify_admin_token`).

### Gaps identificados

1. **No hay feedback de error en `handleDelete`**: el bloque `catch` solo hace `console.error`. Si el backend retorna 400 (último tenant) o 403, el usuario no ve ningún mensaje.
2. **El campo `updated_at`** existe en el modelo `Company` (línea 14) pero no se muestra en la tarjeta.
3. **Validación client-side de `bot_phone_number`**: ningún regex/formato mínimo — cualquier string pasa.
4. **La tarjeta muestra `ID: {id}`** en el footer (línea 189) — puede ser un data leak en pantallas compartidas.
5. **Sin paginación ni búsqueda**: si hay muchos tenants, la grid crece sin control.
6. **`timezone`** no está implementado: el modelo de DB puede tener un campo `timezone` en `config` JSONB pero el formulario no lo expone.

---

## Requirements

### MUST

- **COMP-01**: Si `DELETE /admin/core/tenants/:id` retorna 400 (último tenant), mostrar el mensaje de error del backend en el modal de confirmación (`err.response?.data?.detail`). No cerrar el modal.
- **COMP-02**: Si `DELETE /admin/core/tenants/:id` retorna 500, mostrar toast de error genérico con mensaje "No se pudo eliminar. Puede haber datos asociados."
- **COMP-03**: Validar `bot_phone_number` con regex básico antes de enviar: mínimo 7 dígitos, solo números, `+` al inicio permitido. Mostrar error inline bajo el input.
- **COMP-04**: El modal de confirmación de eliminación debe indicar explícitamente: "Esto eliminará todos los datos asociados (leads, mensajes, vendedores) de manera irreversible."

### SHOULD

- **COMP-05**: Reemplazar `ID: {id}` en el footer de la tarjeta por `Creado: {created_at formatted}` (ya disponible). El ID no agrega valor visual al usuario final.
- **COMP-06**: Agregar campo `timezone` al formulario de creación/edición. Opciones: `America/Argentina/Buenos_Aires` (default), `America/Bogota`, `America/Mexico_City`, `America/New_York`, `Europe/Madrid`. Guardar como `config.timezone`.
- **COMP-07**: Agregar búsqueda/filtro inline por nombre (client-side, sin API call adicional) cuando hay más de 5 empresas.

### COULD

- **COMP-08**: Mostrar badge de estado de integración Meta en cada tarjeta (conectado/desconectado) consultando `GET /admin/core/credentials` filtrado por tenant.
- **COMP-09**: Ordenamiento por nombre o fecha en la grid.

---

## API Endpoints

| Endpoint | Método | Estado | Auth | Notas |
|----------|--------|--------|------|-------|
| `/admin/core/tenants` | GET | Existe | `ceo` | Retorna `id, clinic_name, bot_phone_number, config, created_at` |
| `/admin/core/tenants` | POST | Existe | `ceo` | Body: `clinic_name, bot_phone_number, calendar_provider?` |
| `/admin/core/tenants/:id` | PUT | Existe | `ceo` | Body: campos opcionales |
| `/admin/core/tenants/:id` | DELETE | Existe | `ceo` | 400 si último tenant; cascada en DB |

### Comportamiento de cascada en DELETE

El backend elimina el tenant directamente con `DELETE FROM tenants WHERE id = $1`. La cascada real depende de las FK de la DB. Si hay leads u otros registros sin `ON DELETE CASCADE`, el backend retornará 500 con error de constraint. El frontend debe manejar este caso mostrando el mensaje del backend.

---

## Files to Modify

| File | Action | Motivo |
|------|--------|--------|
| `frontend_react/src/views/CompaniesView.tsx` | Modify | COMP-01, COMP-02, COMP-03, COMP-04, COMP-05, COMP-06 |

No se requieren cambios de backend para los MUST.

---

## Solution

### COMP-01 y COMP-02: Error handling en handleDelete

```tsx
const handleDelete = async (id: number) => {
  try {
    await api.delete(`/admin/core/tenants/${id}`);
    fetchCompanies();
    setDeleteTarget(null);
  } catch (err: any) {
    const detail = err.response?.data?.detail;
    if (err.response?.status === 400) {
      setDeleteError(detail || 'No se puede eliminar este tenant.');
    } else {
      setDeleteError('No se pudo eliminar. Puede haber datos asociados.');
    }
    // NO cerrar el modal — dejar el error visible
  }
};
```

Agregar `const [deleteError, setDeleteError] = useState<string | null>(null)` y mostrar el error dentro del modal de confirmación, encima de los botones.

### COMP-03: Validación de bot_phone_number

```tsx
const PHONE_REGEX = /^\+?[0-9]{7,15}$/;

// En handleSubmit, antes del api call:
if (!PHONE_REGEX.test(formData.bot_phone_number)) {
  setError('El número de teléfono debe tener entre 7 y 15 dígitos. Se permite el prefijo "+".');
  setSaving(false);
  return;
}
```

### COMP-06: Campo timezone

Agregar al estado del formulario:

```tsx
const [formData, setFormData] = useState({
  clinic_name: '',
  bot_phone_number: '',
  calendar_provider: 'local' as 'local' | 'google',
  timezone: 'America/Argentina/Buenos_Aires',
});
```

Y al hacer PUT, incluir `timezone` en el payload (requiere backend: agregar `timezone` al `TenantUpdate` model y actualizarlo en `config` JSONB igual que `calendar_provider`).

**Backend change needed (mínimo):**

```python
# En admin_routes.py → TenantUpdate model
class TenantUpdate(BaseModel):
    clinic_name: Optional[str] = None
    bot_phone_number: Optional[str] = None
    calendar_provider: Optional[str] = None
    timezone: Optional[str] = None  # NUEVO

# En update_tenant route, agregar:
VALID_TIMEZONES = {
    "America/Argentina/Buenos_Aires", "America/Bogota",
    "America/Mexico_City", "America/New_York", "Europe/Madrid"
}
if payload.timezone and payload.timezone in VALID_TIMEZONES:
    updates.append("config = jsonb_set(COALESCE(config, '{}'), '{timezone}', to_jsonb($%s::text))" % pos)
    params.append(payload.timezone); pos += 1
```

---

## Acceptance Criteria

- [ ] Intentar eliminar el único tenant muestra el mensaje del backend "Cannot delete the last tenant" dentro del modal (sin cerrar el modal).
- [ ] Error 500 en DELETE muestra toast "No se pudo eliminar. Puede haber datos asociados."
- [ ] Ingresar `abc` en bot_phone_number y guardar muestra error inline "entre 7 y 15 dígitos" sin hacer API call.
- [ ] El modal de confirmación incluye el texto de advertencia de cascada.
- [ ] El footer de las tarjetas muestra `Creado: DD/MM/YYYY` en lugar de `ID: {id}`.
- [ ] El formulario incluye selector de timezone con las 5 opciones definidas.
- [ ] Cambiar timezone de un tenant y guardar persiste el valor (verificar en DB: `config->>'timezone'`).

---

## Testing Strategy

- **Unit**: Renderizar modal de eliminación con `deleteError` seteado → verificar que el mensaje aparece sin cerrar el modal.
- **Unit**: Input con `bot_phone_number = "abc"` → submit → verificar que `api.put` NO fue llamado.
- **Unit**: Input con `bot_phone_number = "+541112345678"` → verificar que pasa validación.
- **Integration**: POST a `/admin/core/tenants` con `bot_phone_number` duplicado → backend retorna 400 → frontend muestra detail.
- **Edge case**: Grid vacía (0 tenants) → verificar que no hay crash y se muestra empty state.
