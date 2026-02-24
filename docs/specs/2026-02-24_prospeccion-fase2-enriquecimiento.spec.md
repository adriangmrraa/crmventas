# Spec: Prospección CRM (Fase 2) - Enriquecimiento y Visualización Total

## 1. Contexto y Objetivos
- **Problema:** Los leads capturados por Apify contienen mucha información valiosa (emails, ratings, reviews, horarios, descripciones detalladas) que actualmente está oculta en la base de datos (`apify_raw`) y no se visualiza en el frontend. El modal de edición de leads es genérico y no permite ver/editar la ficha técnica completa del negocio prospectado.
- **Solución:** 
  - Expandir la tabla de `ProspectingView` para incluir columnas críticas (Email, Rating, Reviews, Niche).
  - Adaptar el modal de "Edit Lead" en `LeadsView` para que, cuando el lead sea de tipo `apify_scrape`, muestre una sección de "Ficha de Prospección" con toda la data enriquecida.
  - Asegurar la extracción de emails desde los resultados de Apify.
- **KPIs:** 100% de visibilidad de los datos de Apify en el frontend. Reducción de la necesidad de abrir el sitio web del cliente para ver detalles básicos.

## 2. Esquemas de Datos

### Backend (Data Extraction)
- **Emails:** Se deben extraer de `webResults` o campos directos de Apify y guardarse en la columna `email` de la tabla `leads`.
- **Auditoría de Outreach:** Para garantizar la coherencia del "Send status", se debe persistir:
  - `outreach_message_content`: El texto o nombre de la plantilla enviada.
  - `outreach_last_sent_at`: Timestamp preciso del envío exitoso.
- **Persistencia:** Se requieren nuevas columnas en `leads`:
  - `outreach_message_content` (TEXT)
  - `apify_rating` (FLOAT)
  - `apify_reviews` (INTEGER)

### Frontend (Interfaces)
```typescript
interface ProspectLead extends Lead {
  email?: string;
  apify_total_score?: number;
  apify_reviews_count?: number;
  apify_address?: string;
  apify_city?: string;
  apify_state?: string;
  apify_website?: string;
  social_links?: Record<string, string>;
  apify_raw?: any; // Para mostrar detalles dinámicos
}
```

## 3. Lógica de Negocio (Invariantes)

- **Prioridad de Email:** Si el lead ya tiene un email manual, **NO** sobrescribir con el de Apify a menos que esté vacío.
- **Aislamiento de UI:** El modal de "Edit Lead" debe detectar dinámicamente el `source`.
  - SI `source === 'apify_scrape'` ENTONCES mostrar layout "Business Insight" (dos columnas: Datos de contacto + Info de negocio).
  - SI `source === 'whatsapp_inbound'` ENTONCES mostrar layout "Chat Context" (simple).
- **Extracción de Email:** Buscar en `apify_item.get("emails")` y, si falla, intentar extraer de `webResults`.

## 4. Stack y Restricciones
- **Tecnología:** React (Tailwind CSS), Lucide Icons para indicadores de rating.
- **Performance:** Debido al alto número de columnas, implementar `sticky` en la columna del nombre del negocio en la tabla de `ProspectingView`.

## 5. Criterios de Aceptación (Gherkin)

### Escenario 1: Visualización Completa en Tabla
- **DADO** que he ejecutado un scrape exitoso.
- **CUANDO** entro a la vista de `Prospecting`.
- **ENTONCES** veo columnas para: Negocio, Teléfono, Email, Website, Social, Rating (estrellas), Reviews y Ubicación.

### Escenario 2: Modal Adaptativo e Historial
- **DADO** que estoy en la pestaña "Prospección" de la vista de Leads.
- **CUANDO** hago clic en "Editar" un lead que ya tiene estado "Sent".
- **ENTONCES** veo una sección de "Historial de Outreach" que muestra el mensaje enviado y la fecha/hora exacta del envío.

### Escenario 3: Coherencia de Estado
- **DADO** que un lead tiene `outreach_message_sent = true`.
- **CUANDO** se visualiza en la tabla.
- **ENTONCES** el badge muestra "Enviado" y un tooltip con la fecha del envío.
