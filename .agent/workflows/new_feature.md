---
description: Workflow completo para implementar nuevas funcionalidades en CRM Ventas (Nexus Core). Desde analisis hasta verificacion.
---

# Nueva Feature - CRM Ventas (Nexus Core)

Proceso completo para implementar nuevas funcionalidades siguiendo la arquitectura del CRM de ventas.

## Skills Recomendadas
- **Backend/Seguridad**: Backend_Sovereign - Para cambios en `orchestrator_service/`
- **Frontend/UI**: Frontend_Nexus - Para cambios en `frontend_react/`
- **WhatsApp/Chat**: Omnichannel_Chat_Operator - Para integraciones de mensajeria

## 1. Analisis Tecnico (Checklist)

Antes de escribir codigo, validar cada punto:

### Base de Datos
- [ ] Requiere nuevas tablas en PostgreSQL?
  - Si: Definir esquema con `tenant_id` obligatorio.
  - Archivo: `orchestrator_service/db.py`
- [ ] Requiere nuevas columnas en tablas existentes?
  - Si: Usar `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`.
- [ ] Requiere nuevos indices?
  - Si: Definir indices para consultas frecuentes.

### Rutas API
- [ ] Requiere nuevos endpoints?
  - Si: Definir en `orchestrator_service/admin_routes.py` o `modules/crm_sales/routes.py`.
  - Prefijo: `/admin/core/crm/`
- [ ] Requiere modificar endpoints existentes?
  - Si: Verificar compatibilidad hacia atras.
- [ ] Requiere autenticacion especial?
  - JWT para usuarios, X-Admin-Token para administracion.

### Vistas de UI
- [ ] Requiere nuevas paginas/vistas?
  - Si: Crear en `frontend_react/src/views/`.
- [ ] Requiere nuevos componentes?
  - Si: Crear en `frontend_react/src/components/`.
- [ ] Requiere modificar vistas existentes?
  - Si: Identificar archivos afectados.

### Internacionalizacion (i18n)
- [ ] Hay textos nuevos visibles al usuario?
  - Si: Agregar en `frontend_react/src/i18n/locales/es.json` y `en.json`.
  - Usar `t('clave')` en los componentes.

### Notificaciones
- [ ] El feature genera notificaciones?
  - Si: Definir tipo, titulo y mensaje.
  - Tabla: `notifications`
  - Emision en tiempo real: Socket.IO
- [ ] Requiere notificaciones push o WhatsApp?
  - Si: Coordinar con `whatsapp_service/`.

### Roles y Permisos
- [ ] Que roles tienen acceso a esta feature?
  - Opciones: ceo, setter, closer, secretary, professional
- [ ] Requiere validacion de rol en el backend?
- [ ] Requiere ocultar/mostrar elementos en el frontend segun rol?

### Integraciones
- [ ] Involucra Google Calendar? -> `gcal_service.py`
- [ ] Involucra WhatsApp? -> `whatsapp_service/`
- [ ] Involucra Meta/Google Ads? -> Modulo de prospecting
- [ ] Involucra metricas? -> `analytics_service.py`
- [ ] Involucra jobs programados? -> APScheduler en `main.py`

## 2. Implementacion Backend

### 2.1. Migraciones de Base de Datos

Todas las migraciones deben ser **idempotentes**:

```python
# orchestrator_service/db.py - dentro de ensure_tables()
await pool.execute("""
    CREATE TABLE IF NOT EXISTS nueva_feature (
        id SERIAL PRIMARY KEY,
        tenant_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_nueva_feature_tenant
    ON nueva_feature(tenant_id);
""")
```

### 2.2. Rutas API

```python
# orchestrator_service/admin_routes.py o modules/crm_sales/routes.py

@router.post("/admin/core/crm/nueva-feature")
async def crear_nueva_feature(request: Request):
    tenant_id = request.state.tenant_id
    body = await request.json()

    # Validar datos de entrada
    # Ejecutar logica de negocio
    # Persistir con tenant_id
    # Emitir notificacion si aplica
    # Retornar respuesta

    return {"success": True, "data": resultado}
```

### 2.3. Servicios

Si la logica es compleja, crear funciones de servicio separadas:

```python
# Patron: funcion async con tenant_id como primer parametro
async def mi_servicio(tenant_id: int, datos: dict) -> dict:
    # Logica de negocio
    # Interaccion con BD
    # Retornar resultado
    pass
```

### 2.4. Modelos (si aplica)

```python
# orchestrator_service/modules/crm_sales/models.py
from pydantic import BaseModel

class NuevaFeatureCreate(BaseModel):
    campo1: str
    campo2: int
    # tenant_id se extrae del JWT, no del body
```

## 3. Implementacion Frontend

### 3.1. Vista Principal

```tsx
// frontend_react/src/views/NuevaFeatureView.tsx
import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import api from '../api/axios';

export default function NuevaFeatureView() {
  const { t } = useTranslation();
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await api.get('/admin/core/crm/nueva-feature');
        setData(res.data.data);
      } catch (error) {
        console.error('Error:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) return <div className="p-6">{t('common.loading')}</div>;

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-bold text-white">
        {t('nuevaFeature.titulo')}
      </h1>
      {/* Componentes con Tailwind CSS */}
    </div>
  );
}
```

### 3.2. Estilos con Tailwind CSS

- Usar clases de Tailwind directamente en JSX.
- Mantener consistencia con el diseno existente.
- Asegurar responsive: `sm:`, `md:`, `lg:` breakpoints.
- Usar Glassmorphism donde sea consistente con el resto de la app.

### 3.3. Llamadas API con Axios

- Usar la instancia configurada en `frontend_react/src/api/axios.ts`.
- Manejar errores con try/catch.
- Mostrar estados de carga al usuario.
- Usar tipos TypeScript para las respuestas.

### 3.4. Traducciones i18n

Agregar todas las cadenas de texto en ambos archivos de idioma:

- `frontend_react/src/i18n/locales/es.json`
- `frontend_react/src/i18n/locales/en.json`

## 4. Integracion

### 4.1. Socket.IO (Tiempo Real)

Si la feature necesita actualizaciones en tiempo real:

**Backend**: Emitir evento tras la accion.
**Frontend**: Escuchar evento y actualizar estado.

### 4.2. Notificaciones

Si la feature genera notificaciones:
1. Insertar en tabla `notifications` con `tenant_id`.
2. Emitir via Socket.IO para actualizacion inmediata.
3. Si es urgente, considerar notificacion WhatsApp.

### 4.3. Jobs Programados

Si la feature requiere procesamiento periodico:
- Registrar job en APScheduler (`orchestrator_service/main.py`).
- Definir intervalo apropiado.
- Asegurar idempotencia del job.

## 5. Verificacion

### 5.1. Verificacion Automatizada

```bash
# Tests backend
cd orchestrator_service && pytest tests/ -v

# Build frontend
cd frontend_react && npm run build

# Verificacion TypeScript
cd frontend_react && npx tsc --noEmit
```

### 5.2. Checklist de Verificacion Sovereign

- [ ] **Aislamiento**: Todas las queries filtran por `tenant_id`.
- [ ] **Autenticacion**: Endpoints protegidos con JWT o X-Admin-Token.
- [ ] **Roles**: Feature respeta los permisos del rol del usuario.
- [ ] **i18n**: Todos los textos usan traducciones.
- [ ] **Responsive**: UI funciona en mobile y desktop.
- [ ] **Idempotencia**: Migraciones de BD son re-ejecutables sin errores.
- [ ] **Notificaciones**: Se generan correctamente si aplica.
- [ ] **Socket.IO**: Eventos en tiempo real funcionan si aplica.
- [ ] **Sin regresion**: Features existentes siguen funcionando.

### 5.3. Cierre

1. Ejecutar `/verify` para validacion completa del sistema.
2. Documentar la feature implementada.
3. Crear commit descriptivo con los cambios.
