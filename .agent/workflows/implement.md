---
description: Workflow de implementacion para CRM Ventas. Ejecucion disciplinada de cambios tecnicos siguiendo el plan generado por /plan.
---

# Implementacion - CRM Ventas (Nexus Core)

Ejecucion disciplinada de cambios tecnicos. Este workflow se ejecuta despues de que `/plan` haya generado el plan de implementacion.

## Pre-requisitos

- [ ] Existe un `.spec.md` aprobado (generado por `/specify`).
- [ ] Existe un plan de implementacion (generado por `/plan`).
- [ ] Se ha identificado los archivos a modificar y el orden de ejecucion.

## Paso 1: Leer la Especificacion

1. Leer el archivo `.spec.md` correspondiente.
2. Revisar los criterios de aceptacion (Gherkin).
3. Identificar las tablas de la BD afectadas.
4. Confirmar el alcance: que se implementa y que NO se implementa.

## Paso 2: Cambios en Backend

### 2.1. Migraciones de Base de Datos

**Archivo principal**: `orchestrator_service/db.py`

```python
# Patron para migraciones idempotentes
async def ensure_tables():
    await pool.execute("""
        CREATE TABLE IF NOT EXISTS nueva_tabla (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER NOT NULL,
            -- columnas especificas
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)
    # Agregar columnas a tablas existentes
    await pool.execute("""
        ALTER TABLE leads ADD COLUMN IF NOT EXISTS nueva_columna TEXT DEFAULT '';
    """)
```

**Tablas existentes de referencia**:
- `leads` - Leads/prospectos
- `sellers` - Vendedores (setter, closer)
- `clients` - Clientes convertidos
- `opportunities` - Oportunidades de venta (pipeline)
- `sales_transactions` - Transacciones de venta
- `seller_agenda_events` - Eventos de agenda
- `chat_messages` - Mensajes de chat/WhatsApp
- `notifications` - Notificaciones del sistema
- `seller_metrics` - Metricas de rendimiento
- `assignment_rules` - Reglas de asignacion de leads

**Regla critica**: Toda tabla y query DEBE incluir `tenant_id` para aislamiento multi-tenant.

### 2.2. Rutas API

**Archivos de rutas**:
- `orchestrator_service/admin_routes.py` - Rutas administrativas generales
- `orchestrator_service/modules/crm_sales/routes.py` - Rutas del modulo CRM

**Patron base para rutas API**:
```python
@router.get("/admin/core/crm/recurso")
async def get_recurso(request: Request):
    tenant_id = request.state.tenant_id  # Extraido del JWT
    # Logica con filtro tenant_id
    rows = await db.pool.fetch(
        "SELECT * FROM recurso WHERE tenant_id = $1", tenant_id
    )
    return {"data": rows}
```

**Convenciones de rutas**:
- Prefijo: `/admin/core/crm/`
- Recursos: `leads`, `clients`, `sellers`, `agenda/events`, `opportunities`, `notifications`
- Autenticacion: JWT en header `Authorization` o `X-Admin-Token`

### 2.3. Servicios y Logica de Negocio

**Archivos de servicios**:
- `orchestrator_service/main.py` - Punto de entrada, configuracion de servicios, APScheduler
- `orchestrator_service/gcal_service.py` - Integracion Google Calendar
- `orchestrator_service/analytics_service.py` - Metricas y analytics
- `orchestrator_service/modules/crm_sales/tools_provider.py` - Herramientas LangChain
- `orchestrator_service/modules/crm_sales/models.py` - Modelos Pydantic

**Patron para servicios**:
```python
# Siempre usar async/await
async def procesar_lead(tenant_id: int, lead_data: dict):
    # 1. Validar datos
    # 2. Ejecutar logica de negocio
    # 3. Persistir en BD con tenant_id
    # 4. Emitir evento Socket.IO si aplica
    # 5. Crear notificacion si aplica
```

### 2.4. Jobs en Background (APScheduler)

**Archivo**: `orchestrator_service/main.py`

```python
# Patron para agregar jobs programados
scheduler.add_job(
    func=mi_job_periodico,
    trigger="interval",
    minutes=30,
    id="mi_job_id",
    replace_existing=True
)
```

## Paso 3: Cambios en Frontend

### 3.1. Estructura de Archivos

```
frontend_react/src/
  views/          # Paginas/vistas principales
  components/     # Componentes reutilizables
  api/            # Llamadas a la API (axios)
    axios.ts      # Instancia configurada de axios
  i18n/           # Internacionalizacion
    locales/
      es.json     # Traducciones al espanol
      en.json     # Traducciones al ingles
  hooks/          # Custom hooks
  context/        # React Context providers
  types/          # Tipos TypeScript
```

### 3.2. Vistas y Componentes

**Patron para nueva vista**:
```tsx
import { useTranslation } from 'react-i18next';
import api from '../api/axios';

export default function NuevaVista() {
  const { t } = useTranslation();
  const [data, setData] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      const res = await api.get('/admin/core/crm/recurso');
      setData(res.data.data);
    };
    fetchData();
  }, []);

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold">{t('modulo.titulo')}</h1>
      {/* Contenido con Tailwind CSS */}
    </div>
  );
}
```

### 3.3. Llamadas a la API

**Archivo**: `frontend_react/src/api/axios.ts`

```tsx
// Usar la instancia existente de axios
import api from '../api/axios';

// GET
const response = await api.get('/admin/core/crm/leads');

// POST
await api.post('/admin/core/crm/leads', { ...leadData });

// PUT
await api.put(`/admin/core/crm/leads/${id}`, { ...updateData });

// DELETE
await api.delete(`/admin/core/crm/leads/${id}`);
```

### 3.4. Internacionalizacion (i18n)

**Siempre** agregar traducciones para textos nuevos:

```json
// frontend_react/src/i18n/locales/es.json
{
  "modulo": {
    "titulo": "Titulo del Modulo",
    "descripcion": "Descripcion en espanol"
  }
}

// frontend_react/src/i18n/locales/en.json
{
  "modulo": {
    "titulo": "Module Title",
    "descripcion": "Description in English"
  }
}
```

**Regla**: Nunca hardcodear texto visible al usuario. Siempre usar `t('clave')`.

### 3.5. Estilos

- Usar **Tailwind CSS** para todos los estilos.
- Mantener consistencia con el diseno existente (Glassmorphism donde aplique).
- Asegurar que la UI sea responsive (mobile-first).

## Paso 4: Integracion

### 4.1. Eventos Socket.IO

**Backend** (emitir evento):
```python
await sio.emit('nuevo_evento', {
    'tipo': 'lead_asignado',
    'data': { ... },
    'tenant_id': tenant_id
}, room=f"tenant_{tenant_id}")
```

**Frontend** (escuchar evento):
```tsx
useEffect(() => {
  socket.on('nuevo_evento', (data) => {
    // Actualizar estado local
  });
  return () => { socket.off('nuevo_evento'); };
}, []);
```

### 4.2. Notificaciones

```python
# Crear notificacion en la BD
await db.pool.execute("""
    INSERT INTO notifications (tenant_id, user_id, title, message, type, read)
    VALUES ($1, $2, $3, $4, $5, false)
""", tenant_id, user_id, titulo, mensaje, tipo)

# Emitir via Socket.IO para actualizacion en tiempo real
await sio.emit('notification', {...}, room=f"user_{user_id}")
```

### 4.3. WhatsApp (si aplica)

- Servicio en: `whatsapp_service/` (Puerto 8002)
- Coordinar con el orquestador via eventos o API interna.

## Paso 5: Verificacion

Ejecutar el workflow `/verify` para validacion completa:

```bash
# Backend
cd orchestrator_service && pytest tests/ -v

# Frontend - Build
cd frontend_react && npm run build

# Frontend - TypeScript
cd frontend_react && npx tsc --noEmit
```

### Checklist Final de Implementacion

- [ ] Todos los cambios de BD son idempotentes (CREATE IF NOT EXISTS, ADD COLUMN IF NOT EXISTS).
- [ ] Todas las queries incluyen filtro `tenant_id`.
- [ ] Las rutas API tienen autenticacion (JWT o X-Admin-Token).
- [ ] Los textos del frontend usan i18n (`t('clave')`).
- [ ] Los componentes son responsive (Tailwind).
- [ ] Los eventos Socket.IO estan filtrados por tenant.
- [ ] Se crearon/actualizaron tests si aplica.
- [ ] El build de frontend compila sin errores.
- [ ] Se ejecuto `/verify` exitosamente.
