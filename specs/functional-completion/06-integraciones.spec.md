# SPEC F-06: Integraciones Hub

**Priority:** Media
**Complexity:** Media
**Status:** Meta parcialmente funcional (MetaConnectionPanel existe). Google Ads tiene rutas backend. YCloud tiene endpoints de config. El resto son placeholders.

---

## Intent

`IntegrationsView.tsx` actualmente solo renderiza `MetaConnectionPanel` y un único placeholder genérico "More integrations coming soon". El objetivo es convertir esta vista en un hub completo de integraciones: Meta (expandir), Google Ads (nuevo panel), YCloud/WhatsApp (nuevo panel de configuración), y placeholders estructurados para MercadoLibre y Shopify con badge "Próximamente".

---

## Current State

### Frontend

`frontend_react/src/views/IntegrationsView.tsx` (40 líneas):
- Importa y renderiza solo `MetaConnectionPanel` (líneas 1, 21).
- El segundo bloque (líneas 26-36) es un `<section>` hardcodeado con `opacity-50`, sin estructura de integración real.
- No hay panel para Google Ads, YCloud, ni placeholders con datos reales de estado.

`MetaConnectionPanel.tsx` ya implementa:
- Estado `connected/disconnected` via `GET /crm/connect/status`.
- OAuth redirect a Meta con `window.open`.
- Disconnect via API.
- Assets y bindings visualization.
- Múltiples canales (Facebook, Instagram, WhatsApp).

### Backend routes disponibles

**Meta** (`routes/meta_auth.py`, montado en `/crm/auth/meta`):
- `GET /url` → genera URL de autorización OAuth.
- `GET /callback` → procesa redirect OAuth.
- `POST /disconnect` → revoca token.

**Google Ads** (`routes/google_auth.py`, montado en `/crm/auth/google`):
- `GET /ads/url` → URL OAuth para Google Ads.
- `GET /ads/callback` → procesa OAuth.
- `POST /ads/disconnect` → desconectar.
- `GET /ads/refresh` → refrescar token.
- `GET /ads/test-connection` → verifica estado.
- `GET /login/url` y `GET /login/callback` → OAuth para Google Login (distinto a Ads).

**YCloud / WhatsApp** (`admin_routes.py`):
- `GET /admin/core/settings/integration/ycloud/{tenant_id}` → retorna `{ycloud_api_key: "***", ycloud_webhook_secret: "***"}`.
- `POST /admin/core/settings/integration/ycloud/{tenant_id}` → guarda API key y webhook secret.
- `GET /admin/core/credentials` → lista credenciales con valores enmascarados.

---

## Requirements

### MUST

- **INT-01**: Reestructurar `IntegrationsView.tsx` para renderizar paneles individuales por integración: Meta, Google Ads, YCloud, MercadoLibre (placeholder), Shopify (placeholder).
- **INT-02**: Cada panel debe mostrar: nombre de la integración, logo/ícono, estado (conectado/desconectado), botones de acción según estado, y mensaje de error si existe.
- **INT-03**: Panel **YCloud/WhatsApp**: formulario con campos `API Key` y `Webhook Secret` (siempre enmascarados al cargar, editables). Botón "Guardar" que llama a `POST /admin/core/settings/integration/ycloud/{tenant_id}`. Botón "Test Connection" que llama a `GET /ycloud/test` (ver nota backend).
- **INT-04**: Panel **Google Ads**: botón "Conectar con Google Ads" que redirige al flujo OAuth via `GET /crm/auth/google/ads/url`. Mostrar estado conectado/desconectado (detectar via `GET /crm/auth/google/ads/test-connection`). Botón "Desconectar" cuando está conectado via `POST /crm/auth/google/ads/disconnect`.
- **INT-05**: Placeholders para MercadoLibre y Shopify con badge "Próximamente" visible y botón deshabilitado.

### SHOULD

- **INT-06**: Cada panel muestra la última fecha de sincronización o verificación si está disponible en la respuesta del API.
- **INT-07**: El panel YCloud muestra la URL del webhook generada automáticamente (no editable): `{BACKEND_URL}/webhooks/ycloud/{tenant_id}`. El usuario puede copiarla al portapapeles.
- **INT-08**: Animación de estado "verificando..." cuando se llama a test connection, con spinner y luego badge verde/rojo según resultado.
- **INT-09**: Si Meta está conectado, mostrar resumen de canales activos (Facebook/Instagram/WhatsApp) como badges dentro del panel Meta (reutilizar lógica ya existente en `MetaConnectionPanel`).

### COULD

- **INT-10**: Panel de resumen global en el header: "X de Y integraciones activas".
- **INT-11**: Notificación badge en el sidebar cuando una integración requiere atención (token expirado, error de webhook).

---

## API Endpoints

| Endpoint | Método | Estado | Panel | Notas |
|----------|--------|--------|-------|-------|
| `/crm/connect/status` | GET | Existe | Meta | Retorna estado de conexión Meta |
| `/crm/auth/meta/url` | GET | Existe | Meta | OAuth URL |
| `/crm/connect/disconnect` | POST | Existe | Meta | Desconectar Meta |
| `/crm/auth/google/ads/url` | GET | Existe | Google Ads | OAuth URL |
| `/crm/auth/google/ads/test-connection` | GET | Existe | Google Ads | Verifica token activo |
| `/crm/auth/google/ads/disconnect` | POST | Existe | Google Ads | Desconectar |
| `/crm/auth/google/ads/refresh` | GET | Existe | Google Ads | Refrescar token |
| `/admin/core/settings/integration/ycloud/{tenant_id}` | GET | Existe | YCloud | Carga config (valores enmascarados) |
| `/admin/core/settings/integration/ycloud/{tenant_id}` | POST | Existe | YCloud | Guarda API key y secret |
| `/ycloud/test` | GET | Por crear | YCloud | Ping a YCloud para verificar API key |

### Endpoint por crear: Test YCloud

```python
# En ycloud_client.py o admin_routes.py
@router.get("/ycloud/test", dependencies=[Depends(verify_admin_token)])
async def test_ycloud_connection(tenant_id: int = Depends(get_resolved_tenant_id)):
    api_key = await get_tenant_credential(tenant_id, YCLOUD_API_KEY)
    if not api_key:
        return {"connected": False, "error": "No API key configured"}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                "https://api.ycloud.com/v2/whatsapp/phoneNumbers",
                headers={"X-API-Key": api_key},
                timeout=10.0
            )
            return {"connected": resp.status_code == 200}
        except Exception as e:
            return {"connected": False, "error": str(e)}
```

---

## Files to Modify / Create

| File | Action | Motivo |
|------|--------|--------|
| `frontend_react/src/views/IntegrationsView.tsx` | Rewrite | Agregar todos los paneles (INT-01, INT-02) |
| `frontend_react/src/components/integrations/GoogleAdsPanel.tsx` | Create | Panel de Google Ads (INT-04) |
| `frontend_react/src/components/integrations/YCloudPanel.tsx` | Create | Panel de YCloud (INT-03, INT-07) |
| `frontend_react/src/components/integrations/IntegrationCard.tsx` | Create | Componente base reutilizable para paneles (INT-02) |
| `orchestrator_service/admin_routes.py` | Modify | Endpoint `/ycloud/test` (por crear, INT-03) |

---

## Solution

### Estructura de IntegrationsView

```tsx
export default function IntegrationsView() {
  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <PageHeader title="Integraciones" subtitle="..." icon={<Plug />} />

      {/* Integraciones activas */}
      <section className="space-y-4">
        <h2 className="text-sm font-bold text-white/40 uppercase tracking-wider">Canales activos</h2>
        <MetaConnectionPanel />
        <GoogleAdsPanel />
        <YCloudPanel />
      </section>

      {/* Próximamente */}
      <section className="space-y-4">
        <h2 className="text-sm font-bold text-white/40 uppercase tracking-wider">Próximamente</h2>
        <IntegrationCard name="MercadoLibre" icon={<ShoppingCart />} comingSoon />
        <IntegrationCard name="Shopify" icon={<Store />} comingSoon />
      </section>
    </div>
  );
}
```

### Componente base IntegrationCard

```tsx
interface IntegrationCardProps {
  name: string;
  icon: React.ReactNode;
  connected?: boolean;
  lastSync?: string;
  error?: string;
  comingSoon?: boolean;
  children?: React.ReactNode;
}
```

El badge de estado usa clases: `bg-green-500/10 text-green-400` cuando conectado, `bg-red-500/10 text-red-400` cuando desconectado.

### YCloudPanel — comportamiento

1. Al montar: `GET /admin/core/settings/integration/ycloud/{tenant_id}` → setea `hasApiKey` si `ycloud_api_key !== ""`.
2. Los inputs de API Key y Secret siempre arrancan vacíos. El placeholder dice "Configurado (ingresá el nuevo valor para cambiar)" si `hasApiKey = true`.
3. Guardar: solo envía campos no vacíos — si el usuario deja un campo vacío, no lo sobreescribe.
4. Webhook URL: `${BACKEND_URL}/webhooks/ycloud/{tenant_id}` mostrada como `<code>` con botón de copiar.
5. "Test Connection": deshabilitar si `!hasApiKey`, spinner durante la llamada, badge resultante.

---

## Acceptance Criteria

- [ ] IntegrationsView renderiza 3 paneles activos (Meta, Google Ads, YCloud) y 2 placeholders.
- [ ] Placeholders de MercadoLibre y Shopify muestran badge "Próximamente" y botón deshabilitado.
- [ ] Panel YCloud carga el estado del API Key (configurado/no configurado) al montar.
- [ ] Guardar API Key de YCloud llama a `POST /admin/core/settings/integration/ycloud/{tenant_id}` y muestra toast de éxito.
- [ ] La URL del webhook de YCloud se muestra en un campo de solo lectura con botón de copiar.
- [ ] Botón "Test Connection" de YCloud muestra spinner durante la llamada y badge verde/rojo según resultado.
- [ ] Panel Google Ads muestra "Conectado" si el token es válido (según `/crm/auth/google/ads/test-connection`).
- [ ] Botón "Conectar" de Google Ads redirige al flujo OAuth.
- [ ] Botón "Desconectar" de Google Ads hace `POST /crm/auth/google/ads/disconnect`.
- [ ] Panel Meta sigue funcionando sin regresiones (MetaConnectionPanel no se toca).
- [ ] Ningún panel crashea si el backend retorna error — muestra mensaje de error inline.

---

## Testing Strategy

- **Unit**: Renderizar YCloudPanel con `hasApiKey = true` → verificar que el placeholder del input dice "Configurado".
- **Unit**: Click en "Test Connection" con `hasApiKey = false` → botón deshabilitado, no hace API call.
- **Unit**: Renderizar IntegrationCard con `comingSoon = true` → botón deshabilitado, badge "Próximamente" visible.
- **Integration**: Guardar API Key vacío → verificar que el campo no se sobreescribe en backend.
- **Edge case**: Backend retorna 403 en `/settings/integration/ycloud` (rol no CEO) → panel muestra "Sin permisos".
