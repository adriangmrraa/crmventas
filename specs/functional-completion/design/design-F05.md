# Design F-05: Empresas / Companies Management

**Spec:** `05-empresas.spec.md`
**Fecha:** 2026-04-14

---

## Archivo a modificar

Un solo archivo: `frontend_react/src/views/CompaniesView.tsx`

Cambios menores de backend en `admin_routes.py` solo para COMP-06 (timezone).

---

## COMP-03: Validacion de Telefono

### Regex

```typescript
const PHONE_REGEX = /^\+?[0-9]{7,15}$/;
```

**Reglas:**
- Prefijo `+` opcional (una sola vez, al inicio)
- Solo digitos despues del prefijo
- Minimo 7 digitos, maximo 15 (estandar E.164)
- No permite espacios, guiones ni parentesis

### Flujo de validacion

```
handleSubmit()
  |-- si !PHONE_REGEX.test(formData.bot_phone_number)
  |     |-- setPhoneError('El numero debe tener entre 7 y 15 digitos...')
  |     |-- setSaving(false)
  |     |-- return (NO hace API call)
  |-- else
  |     |-- setPhoneError(null)
  |     |-- continua con api.post/put
```

### Estado nuevo

```typescript
const [phoneError, setPhoneError] = useState<string | null>(null);
```

Se muestra debajo del input `bot_phone_number` en rojo, solo cuando hay error. Se limpia al cambiar el valor del input.

---

## COMP-01 y COMP-02: Error en Delete

### Estado nuevo

```typescript
const [deleteError, setDeleteError] = useState<string | null>(null);
```

### handleDelete modificado

```typescript
const handleDelete = async (id: number) => {
  try {
    await api.delete(`/admin/core/tenants/${id}`);
    fetchCompanies();
    setDeleteTarget(null);
    setDeleteError(null);
  } catch (err: any) {
    const detail = err.response?.data?.detail;
    if (err.response?.status === 400) {
      // COMP-01: ultimo tenant u otra validacion del backend
      setDeleteError(detail || 'No se puede eliminar este tenant.');
    } else {
      // COMP-02: error 500 o constraint violation
      setDeleteError('No se pudo eliminar. Puede haber datos asociados.');
    }
    // NO cerrar el modal — dejar error visible
  }
};
```

### UI del error en modal

El `deleteError` se renderiza DENTRO del modal de confirmacion, encima de los botones, en un div rojo. Se resetea al abrir un nuevo modal de delete (`setDeleteError(null)` en `setDeleteTarget()`).

---

## COMP-04: Advertencia de Cascada en Modal Delete

Agregar texto fijo al modal de confirmacion, debajo del nombre de la empresa:

```
"Esto eliminara todos los datos asociados (leads, mensajes, vendedores) de manera irreversible."
```

Se muestra siempre, independientemente de si hay error o no.

---

## COMP-05: Reemplazar ID por Fecha Creacion

En el footer de la tarjeta, cambiar:

```tsx
// Antes:
<span>ID: {clinica.id}</span>

// Despues:
<span>Creado: {new Date(clinica.created_at).toLocaleDateString('es-AR')}</span>
```

Formato `es-AR` para consistencia con la UI en espanol (DD/MM/YYYY).

---

## COMP-06: Campo Timezone

### Opciones

```typescript
const TIMEZONE_OPTIONS = [
  { value: 'America/Argentina/Buenos_Aires', label: 'Buenos Aires (GMT-3)' },
  { value: 'America/Bogota', label: 'Bogota (GMT-5)' },
  { value: 'America/Mexico_City', label: 'Ciudad de Mexico (GMT-6)' },
  { value: 'America/New_York', label: 'Nueva York (GMT-5)' },
  { value: 'Europe/Madrid', label: 'Madrid (GMT+1)' },
];
```

### Cambios en formData

```typescript
const [formData, setFormData] = useState({
  clinic_name: '',
  bot_phone_number: '',
  calendar_provider: 'local' as 'local' | 'google',
  timezone: 'America/Argentina/Buenos_Aires',  // NUEVO
});
```

### Lectura al editar

```typescript
// En handleOpenModal, al cargar empresa existente:
timezone: clinica.config?.timezone || 'America/Argentina/Buenos_Aires',
```

### Envio al backend

Incluir `timezone` en el body de POST y PUT. El backend lo guarda en `config.timezone` (JSONB).

### Cambio backend requerido (SHOULD)

En `admin_routes.py`, agregar `timezone: Optional[str]` al modelo `TenantUpdate` y persistir en `config` JSONB con validacion de whitelist.

---

## COMP-07: Busqueda/Filtro Inline

### Implementacion

```typescript
const [searchTerm, setSearchTerm] = useState('');

const filteredCompanies = companies.filter(c =>
  c.clinic_name.toLowerCase().includes(searchTerm.toLowerCase())
);
```

### UI

- Solo mostrar el input de busqueda cuando `companies.length > 5`
- Input con icono `Search`, placeholder "Buscar empresa..."
- Posicion: debajo del `PageHeader`, arriba de la grid
- Filtrado client-side, sin API call

---

## Resumen de cambios por requirement

| Req | Tipo | Cambio |
|-----|------|--------|
| COMP-01 | MUST | `deleteError` state + mostrar en modal + no cerrar modal en error 400 |
| COMP-02 | MUST | Mensaje generico en modal para errores no-400 |
| COMP-03 | MUST | `PHONE_REGEX` + `phoneError` state + validacion en `handleSubmit` |
| COMP-04 | MUST | Texto advertencia cascada en modal delete |
| COMP-05 | SHOULD | Reemplazar `ID: {id}` por `Creado: DD/MM/YYYY` en footer tarjeta |
| COMP-06 | SHOULD | Select timezone en form + envio al backend |
| COMP-07 | SHOULD | Input busqueda condicional + filtro client-side |
