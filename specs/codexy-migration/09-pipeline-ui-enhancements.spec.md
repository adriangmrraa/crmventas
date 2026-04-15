# SPEC-09: Pipeline & UI Enhancements

**Priority:** Baja
**Complexity:** Baja-Media
**Source:** crmcodexy — stale deal indicator, CSV import robusto, design system oklch, llamadas con resolver
**Target:** CRM VENTAS — extender pipeline existente, mejorar CSV import, adaptar design tokens
**Estado:** Draft
**Fecha:** 2026-04-14

---

## Contexto y Motivación

CRM VENTAS tiene pipeline Kanban pero carece de:
1. **Stale deal detection**: sin indicador visual de deals sin actividad reciente
2. **CSV import con preview**: import básico sin validación previa ni preview de filas
3. **Design system coherente**: dark theme propio pero sin tokens oklch ni efectos glassmorphism del sistema crmcodexy
4. **Resolver de llamadas**: sin dialog de resolución con auto-nota y sync de agenda

Estas mejoras son incrementales — no rompen lo existente, agregan capas encima.

---

## Alcance

### Incluido

**Stale Deal Indicator**
- Punto rojo pulsante (`animate-ping`) en tarjeta de pipeline si `fecha_ultima_actividad > 7 días`
- Tooltip con "Sin actividad hace X días"
- Threshold configurable (default 7 días)
- Columna de filtro "Solo stale" en la vista pipeline

**CSV Import Robusto**
- Parser que maneja: campos con comas dentro de comillas, comillas escapadas (`""`), saltos de línea en campos, encodings UTF-8 y latin-1
- Template descargable con columnas esperadas y filas de ejemplo
- Preview de las primeras 5 filas antes de confirmar import
- Validación por fila con reporte de errores (fila N: campo X inválido)
- Import parcial: importar las filas válidas, reportar las inválidas

**Design System — Tokens oklch**
- Migrar CSS custom properties a espacio de color oklch
- Color primario: `oklch(55% 0.22 290)` ≈ `#8F3DFF` violet
- Glow effects: `box-shadow` con color primario en variantes 30%/50% opacity
- Glassmorphism: `backdrop-filter: blur(12px)` + `background: oklch(... / 0.1)`
- Custom scrollbars: thumb oklch primary, track transparente
- Los tokens reemplazan los actuales sin cambiar nombres de componentes

**Llamadas con Resolver Dialog** (si no está ya en SPEC-08)
- Dialog de 3 opciones: Completada / No contestó / Reagendada
- Auto-nota con prefijo según resultado
- Sync bidireccional con agenda (marcar evento como completado o reagendar)
- Este sub-feature puede implementarse como parte de SPEC-08 Tab Llamadas o aquí

### Excluido

- Migración completa del design system (solo tokens y efectos clave)
- Import de otros formatos (Excel, JSON)
- Detección automática de duplicados en CSV import (v2)
- WebSocket en tiempo real para stale detection (polling manual o refresh es suficiente)
- Personalización del threshold de stale por usuario (solo global en config)

---

## Stale Deal Indicator — Detalle

### Lógica de negocio

Un deal está "stale" cuando:
```
fecha_actual - deal.fecha_ultima_actividad > STALE_THRESHOLD_DAYS (default: 7)
```

`fecha_ultima_actividad` se actualiza cuando:
- Se crea o edita una nota en el deal
- Se registra o resuelve una llamada
- Se mueve el deal de columna en el pipeline
- Se agrega un archivo al deal

### Componente

```tsx
// StaleDealIndicator — punto pulsante rojo
interface StaleDealIndicatorProps {
  fechaUltimaActividad: Date;
  thresholdDays?: number; // default 7
}

// Si es stale:
<span className="relative flex h-3 w-3">
  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
  <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500" />
</span>
// Con Tooltip: "Sin actividad hace {N} días"
```

### Filtro en Pipeline

```
Botón toggle "Mostrar solo stale" en toolbar del pipeline
→ filtra tarjetas client-side (no requiere llamada al backend)
→ el estado del filtro se persiste en URL (?stale=1)
```

---

## CSV Import Robusto — Detalle

### Parser

El parser debe manejar el RFC 4180 completo:

```python
# app/services/csv_import/parser.py
class RobustCSVParser:
    def parse(self, content: bytes | str) -> ParseResult:
        """
        Maneja:
        - Campos con comas: "Empresa, S.A.",Juan
        - Comillas escapadas: "Dijo ""hola"""
        - Saltos de línea en campos: "Línea 1\nLínea 2"
        - BOM UTF-8
        - Encoding latin-1 con fallback
        """
        ...

class ParseResult(BaseModel):
    headers: list[str]
    rows: list[dict[str, str]]
    errors: list[ParseError]
    total_rows: int
    valid_rows: int
    invalid_rows: int

class ParseError(BaseModel):
    row_number: int
    column: str | None
    message: str
```

### Flujo de Import (3 pasos)

```
Paso 1 — Upload
  POST /api/clientes/csv/preview
  Body: multipart/form-data { file: File }
  Response: { headers, preview_rows (max 5), total_rows, errors_preview }

Paso 2 — Preview y confirmación
  UI muestra tabla con primeras 5 filas
  UI muestra conteo: "X filas válidas, Y con errores"
  Usuario puede descargar reporte de errores antes de confirmar

Paso 3 — Import
  POST /api/clientes/csv/import
  Body: { import_id, skip_invalid: bool }
  Response: { imported, skipped, errors: list[ParseError] }
```

### Template Descargable

```
GET /api/clientes/csv/template
Response: archivo CSV con:
  - Headers en primera fila
  - 2-3 filas de ejemplo con datos ficticios realistas
  - Comentario en primera celda explicando el formato (opcional)
```

### Columnas del Template (CRM VENTAS)

```csv
nombre,empresa,email,telefono,estado,notas
Juan Pérez,ACME S.A.,juan@acme.com,+5491112345678,prospecto,Cliente referido por...
```

---

## Design System — Tokens oklch

### Variables CSS a reemplazar/agregar

```css
/* Antes (hsl o hex) → Después (oklch) */
:root {
  /* Primary */
  --color-primary:         oklch(55% 0.22 290);    /* #8F3DFF violet */
  --color-primary-hover:   oklch(50% 0.22 290);
  --color-primary-muted:   oklch(55% 0.22 290 / 0.15);

  /* Glow effects */
  --glow-primary:          0 0 20px oklch(55% 0.22 290 / 0.3);
  --glow-primary-strong:   0 0 40px oklch(55% 0.22 290 / 0.5);

  /* Glassmorphism */
  --glass-bg:              oklch(20% 0.01 290 / 0.6);
  --glass-border:          oklch(55% 0.22 290 / 0.2);
  --glass-blur:            blur(12px);

  /* Scrollbar */
  --scrollbar-thumb:       oklch(55% 0.22 290 / 0.4);
  --scrollbar-thumb-hover: oklch(55% 0.22 290 / 0.7);
  --scrollbar-track:       transparent;
}
```

### Custom Scrollbars

```css
/* Webkit */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--scrollbar-track); }
::-webkit-scrollbar-thumb {
  background: var(--scrollbar-thumb);
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover { background: var(--scrollbar-thumb-hover); }

/* Firefox */
* { scrollbar-width: thin; scrollbar-color: var(--scrollbar-thumb) var(--scrollbar-track); }
```

### Clases de Utilidad

```css
.glass {
  background: var(--glass-bg);
  backdrop-filter: var(--glass-blur);
  border: 1px solid var(--glass-border);
}

.glow-primary { box-shadow: var(--glow-primary); }
.glow-primary-strong { box-shadow: var(--glow-primary-strong); }
```

---

## Escenarios (BDD)

### SC-09-01: Stale deal indicator — deal sin actividad > 7 días

```
DADO un deal con fecha_ultima_actividad = hace 10 días
CUANDO se renderiza la tarjeta en el pipeline
ENTONCES aparece un punto rojo pulsante (animate-ping) en la esquina superior derecha
  Y el tooltip muestra "Sin actividad hace 10 días"
```

### SC-09-02: Stale deal indicator — deal con actividad reciente

```
DADO un deal con fecha_ultima_actividad = hace 3 días
CUANDO se renderiza la tarjeta en el pipeline
ENTONCES NO aparece el punto rojo pulsante
```

### SC-09-03: Stale deal indicator — threshold configurable

```
DADO que STALE_THRESHOLD_DAYS está configurado en 14
  Y un deal con fecha_ultima_actividad = hace 10 días
CUANDO se renderiza la tarjeta
ENTONCES NO aparece el punto pulsante (10 < 14)
```

### SC-09-04: Filtro "solo stale" en pipeline

```
DADO que hay 10 deals en el pipeline: 3 stale y 7 activos
CUANDO activo el toggle "Mostrar solo stale"
ENTONCES solo se muestran las 3 tarjetas stale
  Y la URL cambia a incluir ?stale=1
CUANDO desactivo el toggle
ENTONCES se muestran las 10 tarjetas
  Y la URL vuelve a no tener ?stale=1
```

### SC-09-05: CSV import — campos con comillas y comas

```
DADO un archivo CSV con la fila: "Empresa, S.A.","Juan ""El Jefe"" Pérez",email@test.com
CUANDO se hace upload para preview
ENTONCES el parser extrae correctamente:
  empresa = "Empresa, S.A."
  nombre  = 'Juan "El Jefe" Pérez'
  email   = "email@test.com"
  Y NO hay errores de parsing para esta fila
```

### SC-09-06: CSV import — preview de 5 filas

```
DADO un CSV con 100 filas válidas
CUANDO se hace upload
ENTONCES la UI muestra una tabla con exactamente 5 filas de preview
  Y muestra "100 filas detectadas, 0 errores"
  Y hay un botón "Confirmar import" y uno "Cancelar"
```

### SC-09-07: CSV import — import parcial con errores

```
DADO un CSV con 10 filas: 8 válidas y 2 con email inválido
CUANDO confirmo el import con "Importar válidas, ignorar errores"
ENTONCES se importan 8 clientes
  Y la respuesta incluye lista de 2 errores con número de fila y motivo
  Y la UI muestra resumen: "8 importados, 2 ignorados"
```

### SC-09-08: CSV import — template descargable

```
DADO que estoy en la pantalla de CSV import
CUANDO hago click en "Descargar template"
ENTONCES se descarga un archivo CSV con los headers correctos
  Y tiene al menos 2 filas de ejemplo con datos ficticios
```

### SC-09-09: Design tokens — color oklch primario

```
DADO que los tokens oklch están aplicados
CUANDO inspecciono un botón primario
ENTONCES su color de fondo es oklch(55% 0.22 290)
  Y su glow es box-shadow con oklch(55% 0.22 290 / 0.3)
```

### SC-09-10: Glassmorphism — card con backdrop-filter

```
DADO una card con clase .glass
CUANDO se renderiza sobre un fondo con imagen o color
ENTONCES tiene backdrop-filter: blur(12px)
  Y background semi-transparente (oklch con alpha < 1)
  Y borde sutil con color primary transparente
```

---

## Implementación — Estructura de Archivos

```
# Backend
app/
  services/
    csv_import/
      parser.py           # RobustCSVParser (RFC 4180 compliant)
      validator.py        # Validación de columnas requeridas y formatos
      importer.py         # Lógica de import con manejo de duplicados
      schemas.py          # ParseResult, ParseError, ImportResult
  routers/
    clientes/
      csv.py              # POST /csv/preview, POST /csv/import, GET /csv/template
  tests/
    services/
      csv_import/
        test_parser.py    # Casos edge: comillas, comas, saltos, encodings
        test_importer.py  # Import parcial, duplicados, errores
    routers/
      clientes/
        test_csv_router.py

# Frontend
src/
  features/
    pipeline/
      components/
        PipelineCard/
          PipelineCard.tsx
          StaleDealIndicator.tsx    # punto pulsante
        PipelineToolbar/
          PipelineToolbar.tsx
          StaleFilter.tsx           # toggle + URL sync
      hooks/
        useStaleDeal.ts             # lógica: fecha_ultima_actividad > threshold
    csv-import/
      pages/
        CSVImportPage.tsx
      components/
        FileUploadZone.tsx
        CSVPreviewTable.tsx
        ImportSummary.tsx
        ErrorReport.tsx
      hooks/
        useCSVImport.ts
  design-system/
    tokens.css                      # Variables oklch
    utilities.css                   # .glass, .glow-primary, scrollbars
```

---

## Tests Requeridos (TDD)

### Backend — CSV Parser (crítico, muchos edge cases)

```python
# test_parser.py — casos obligatorios
def test_handles_comma_inside_quoted_field(): ...
def test_handles_escaped_quotes(): ...
def test_handles_newline_inside_quoted_field(): ...
def test_handles_utf8_bom(): ...
def test_handles_latin1_encoding(): ...
def test_partial_import_reports_invalid_rows(): ...
def test_empty_file_returns_error(): ...
def test_missing_required_columns_returns_error(): ...
```

### Frontend — Stale Indicator

```tsx
// useStaleDeal.test.ts
test('returns stale=true when activity > 7 days ago')
test('returns stale=false when activity <= 7 days ago')
test('respects custom threshold')

// StaleDealIndicator.test.tsx
test('renders pulsing dot when stale')
test('does not render when not stale')
test('tooltip shows correct days count')

// StaleFilter.test.tsx
test('filters cards to only stale when toggled')
test('syncs filter state to URL params')
```

### Frontend — Design Tokens

- No unit tests (CSS visual). Usar Storybook stories para validación visual.
- Story para cada token/utilidad: `.glass`, `.glow-primary`, `StaleDealIndicator`

---

## Criterios de Aceptación

- [ ] `StaleDealIndicator` aparece SOLO en deals con inactividad > threshold configurable
- [ ] El filtro "solo stale" no hace llamadas al backend (client-side filter)
- [ ] El estado del filtro stale persiste en URL al refrescar
- [ ] CSV parser maneja todos los casos RFC 4180 (tests pasan)
- [ ] Preview muestra exactamente las primeras 5 filas antes del import
- [ ] Import parcial importa las filas válidas y reporta las inválidas con número de fila
- [ ] Template CSV descargable tiene headers correctos y filas de ejemplo
- [ ] Tokens oklch reemplazan colores anteriores sin romper componentes existentes
- [ ] `.glass` y `.glow-primary` son clases de utilidad reutilizables en toda la app
- [ ] Scrollbars custom aplican globalmente sin afectar scrollbars de terceros embebidos

---

## Notas de Migración desde crmcodexy

| crmcodexy | CRM VENTAS |
|---|---|
| `animate-ping` de Tailwind CSS | Mismo — verificar que Tailwind esté configurado con animaciones |
| `fecha_ultima_actividad` calculada en frontend | Calcular en backend o en hook client-side según performance |
| Parser CSV custom con regex | Usar `csv` module de Python stdlib + manejo manual de edge cases, O librería `unicodecsv` |
| oklch en CSS nativo | Verificar soporte de browsers objetivo (oklch es baseline 2023+) |
| Glassmorphism con `backdrop-filter` | Mismo — Safari puede requerir prefijo `-webkit-` |
| Design tokens en `:root` global | Integrar con sistema de theming existente en CRM VENTAS sin romper dark theme actual |

### Compatibilidad oklch

oklch es soportado por Chrome 111+, Firefox 113+, Safari 16.4+. Si el target incluye browsers más viejos, usar `@supports`:

```css
@supports (color: oklch(0% 0 0)) {
  :root { --color-primary: oklch(55% 0.22 290); }
}
/* fallback para browsers sin soporte */
:root { --color-primary: #8F3DFF; }
```
