# Modelo de Datos: CRM de Ventas

Este documento define las entidades y la estructura de datos necesaria para soportar el nicho de "CRM para Vendedores/Setters".

## 1. Entidades de Base de Datos (PostgreSQL)

Estas tablas deben ser creadas vía migración (`patch_xxx`) y respetar la soberanía del tenant.

### 1.1 `leads` (Prospectos)
Reemplaza conceptualmente a `patients`.

```sql
CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    
    -- Datos de Contacto
    phone_number TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    
    -- Estado del Pipeline
    status TEXT DEFAULT 'new', -- new, contacted, interested, negotiation, closed_won, closed_lost
    stage_id UUID, -- Futuro: pipelines custommizables
    
    -- Asignación
    assigned_seller_id INTEGER REFERENCES users(id), -- Vendedor asignado
    
    -- Metadatos
    source TEXT, -- 'meta_ads', 'website', 'referral'
    meta_lead_id TEXT, -- ID si viene de Lead Ads
    tags JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_leads_tenant_phone ON leads(tenant_id, phone_number);
CREATE INDEX idx_leads_seller ON leads(tenant_id, assigned_seller_id);
```

### 1.2 `whatsapp_connections` (Conexión Meta)
Permite que cada vendedor (o el tenant) conecte múltiples números.

```sql
CREATE TABLE whatsapp_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    seller_id INTEGER REFERENCES users(id), -- Opcional: si la conexión es personal del vendedor
    
    phonenumber_id TEXT NOT NULL,
    waba_id TEXT NOT NULL,
    access_token_vault_id TEXT NOT NULL, -- Referencia a Vault (encriptado)
    
    status TEXT DEFAULT 'active',
    friendly_name TEXT
);
```

### 1.3 `templates` (Plantillas Meta)
Sincronizadas desde Meta.

```sql
CREATE TABLE templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    
    meta_template_id TEXT NOT NULL,
    name TEXT NOT NULL,
    language TEXT DEFAULT 'es',
    category TEXT, -- MARKETING, UTILITY, AUTH
    
    components JSONB NOT NULL, -- Estructura de header, body, footer, buttons
    status TEXT -- APPROVED, REJECTED, PAUSED
);
```

### 1.4 `campaigns` (Envíos Masivos)

```sql
CREATE TABLE campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    
    name TEXT NOT NULL,
    template_id UUID REFERENCES templates(id),
    target_segment JSONB, -- Filtros de leads (ej. tags=['interesado'])
    
    status TEXT DEFAULT 'draft', -- draft, scheduled, sending, completed
    stats JSONB DEFAULT '{}', -- {sent: 100, delivered: 90, read: 50, replied: 10}
    
    scheduled_at TIMESTAMP
);
```

## 2. API Endpoints (Diseño)

Namespace: `/admin/niche` (cuando `niche_type='crm_sales'`)

### Leads
*   `GET /leads`: Listado con filtros y paginación.
*   `POST /leads`: Crear lead manual o vía webhook.
*   `PUT /leads/{id}/stage`: Mover de etapa.
*   `POST /leads/{id}/assign`: Asignar vendedor.

### Templates
*   `GET /templates`: Listar plantillas aprobadas.
*   `POST /templates/sync`: Forzar sincro con Meta API.

### Campaigns
*   `POST /campaigns`: Crear campaña.
*   `POST /campaigns/{id}/launch`: Iniciar envío.

## 3. Integración con Core
*   **Usuarios**: Los vendedores son `users` con rol `seller`.
*   **Chat**: Los mensajes de WhatsApp se guardan en la tabla Core `chat_messages`. Se vinculan al `lead` mediante `phone_number`.
