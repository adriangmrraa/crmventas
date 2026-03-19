# 🔐 PLAN DE IMPLEMENTACIÓN: SEGURIDAD CLINICFORGE → CRM SALES

## 📊 RESUMEN EJECUTIVO

**Objetivo:** Implementar el **mismo nivel de seguridad de ClinicForge** en CRM Sales, incluyendo todos los sistemas de autenticación, autorización, aislamiento multi-tenant, encriptación y defensas en profundidad.

**Estado Actual:**
- ✅ **ClinicForge:** Sistema de seguridad empresarial completo (Nexus Security v7.6)
- ⚠️ **CRM Sales:** Seguridad básica con vulnerabilidades críticas
- 🔄 **Migración:** Transferir arquitectura de seguridad completa

---

## 🏗️ ARQUITECTURA DE SEGURIDAD CLINICFORGE (NEXUS v7.6)

### **1. SISTEMA DE AUTENTICACIÓN DE DOBLE FACTOR**

#### **Capa 1: Infraestructura (X-Admin-Token)**
```python
# ClinicForge: auth.py - Validación estricta
if x_admin_token != ADMIN_TOKEN:
    logger.warning(f"❌ 401: X-Admin-Token mismatch. IP: {request.client.host}")
    raise HTTPException(status_code=401, detail="Token de infraestructura inválido.")
```

#### **Capa 2: Identidad (JWT + Cookies HttpOnly)**
```python
# Soporta múltiples métodos de entrega:
# 1. Bearer Token (Authorization header)
# 2. HttpOnly Cookie (anti-XSS)
# 3. Fallback automático si uno falla
```

#### **CRM Sales Actual (VULNERABLE):**
```typescript
// ❌ Token almacenado en localStorage (vulnerable a XSS)
localStorage.setItem('JWT_TOKEN', newToken);
```

### **2. SISTEMA DE AUTORIZACIÓN RBAC GRANULAR**

#### **Roles y Permisos ClinicForge:**
```python
ROLES = {
    'ceo': ['*'],  # Acceso completo a todas las sedes
    'professional': ['read_patients', 'write_appointments', 'read_chats'],
    'secretary': ['read_patients', 'write_appointments', 'manage_chats']
}

# Factory para RBAC granular
def require_role(allowed_roles: List[str]):
    async def role_dependency(user_data=Depends(verify_admin_token)):
        if user_data.role not in allowed_roles:
            raise HTTPException(status_code=403, detail=f"Permisos insuficientes.")
        return user_data
    return role_dependency
```

#### **Frontend ProtectedRoute:**
```typescript
// ClinicForge: ProtectedRoute.tsx
if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    return <Navigate to="/" replace />;
}
```

### **3. AISLAMIENTO MULTI-TENANT (NEXUS PROTOCOL)**

#### **Resolución Estricta de Tenant ID:**
```python
async def get_resolved_tenant_id(request: Request, user_data) -> int:
    """
    Nexus Protocol: Aislamiento estricto de datos
    1. CEOs: Pueden alternar sedes usando X-Tenant-ID header
    2. Staff: Bloqueados a su tenant de registro
    3. Auditoría de intentos de acceso cruzado
    """
    if user_data.role == 'ceo':
        # CEO: Confía en el header si existe
        if header_tid and header_tid.isdigit():
            return int(header_tid)
    else:
        # STAFF: Aislamiento estricto
        if header_tid and header_tid.isdigit() and int(header_tid) != real_tenant_id:
            logger.warning(f"🛡️ BLOQUEO NEXUS: Intento de Tenant Mismatch")
            # Forzamos tenant real (no error para no romper UI)
    
    return real_tenant_id
```

#### **Todas las Queries Incluyen tenant_id:**
```python
# ClinicForge: Patrón obligatorio
await db.pool.fetch("""
    SELECT * FROM patients 
    WHERE tenant_id = $1 AND id = $2
""", tenant_id, patient_id)
```

### **4. SISTEMA DE CREDENCIALES ENCRIPTADAS**

#### **Vault de Credenciales:**
```python
# ClinicForge: credentials.py - Encriptación Fernet
def encrypt_value(value: str) -> str:
    if not CREDENTIALS_FERNET_KEY:
        return value
    f = Fernet(CREDENTIALS_FERNET_KEY.encode("utf-8"))
    return f.encrypt(value.encode("utf-8")).decode("ascii")

async def save_tenant_credential(tenant_id: int, name: str, value: str, category: str = "general"):
    final_value = encrypt_value(value)
    await db.pool.execute("""
        INSERT INTO credentials (tenant_id, name, value, category)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (tenant_id, name) DO UPDATE SET value = $3
    """, tenant_id, name, final_value, category)
```

#### **Tabla `credentials`:**
```sql
CREATE TABLE credentials (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
    name TEXT NOT NULL,  -- Ej: 'META_USER_LONG_TOKEN', 'CHATWOOT_API_TOKEN'
    value TEXT NOT NULL, -- Encriptado con Fernet
    category TEXT,       -- 'meta_ads', 'chatwoot', 'whatsapp'
    UNIQUE (tenant_id, name)
);
```

### **5. MIDDLEWARE DE SEGURIDAD HTTP**

#### **SecurityHeadersMiddleware:**
```python
# ClinicForge: security_middleware.py
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # 1. Anti-clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # 2. Anti-MIME-sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # 3. HSTS (HTTP Strict Transport Security)
        response.headers["Strict-Transport-Security"] = "max-age=15768000"
        
        # 4. CSP Dinámico
        csp_policy = (
            f"default-src 'self'; "
            f"script-src 'self' 'unsafe-inline'; "
            f"style-src 'self' 'unsafe-inline' fonts.googleapis.com; "
            f"font-src 'self' fonts.gstatic.com; "
            f"img-src 'self' data:; "
            f"connect-src 'self' *.openai.com *.facebook.com; "
            f"frame-ancestors 'none'; "
            f"object-src 'none';"
        )
        response.headers["Content-Security-Policy"] = csp_policy
        
        return response
```

### **6. DETECCIÓN DE PROMPT INJECTION (IA SECURITY)**

#### **Prompt Security Service:**
```python
# ClinicForge: prompt_security.py
PROMPT_INJECTION_PATTERNS = [
    r"ignore (all )?previous instructions",
    r"disregard (all )?previous instructions",
    r"you are now (in )?developer mode",
    r"system override",
    r"bypass security",
]

def detect_prompt_injection(text: str) -> bool:
    """Detecta intentos de 'Prompt Injection' o 'Jailbreaking'."""
    t = text.lower()
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, t, re.IGNORECASE):
            logger.warning(f"🚨 Nexus Security: Prompt Injection detectado!")
            return True
    return False
```

### **7. AUDITORÍA Y LOGGING**

#### **Logs de Seguridad:**
```python
# ClinicForge: Auditoría de acceso a datos sensibles
async def log_pii_access(request: Request, user_data, patient_id: Any, action: str):
    """
    Registra auditoría de acceso a datos sensibles (Nexus Protocol v7.6).
    """
    logger.info(f"🛡️ AUDIT: User {user_data.email} ({user_data.role}) "
                f"accessed PII for Patient {patient_id}. "
                f"Action: {action}. IP: {request.client.host}")
```

#### **System Events Table:**
```sql
CREATE TABLE system_events (
    id BIGSERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,  -- 'auth_failure', 'pii_access', 'tenant_violation'
    severity TEXT DEFAULT 'info',  -- 'info', 'warning', 'critical'
    message TEXT,
    payload JSONB,  -- Datos completos del evento
    occurred_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 🔍 ANÁLISIS DE VULNERABILIDADES CRM SALES ACTUAL

### **VULNERABILIDADES CRÍTICAS:**

#### **1. Almacenamiento de Tokens en localStorage (XSS)**
```typescript
// ❌ VULNERABLE: Token accesible por JavaScript
localStorage.setItem('JWT_TOKEN', newToken);
const token = localStorage.getItem('JWT_TOKEN'); // ❌

// ✅ SOLUCIÓN: HttpOnly Cookies
// Backend envía Set-Cookie: access_token=xxx; HttpOnly; Secure; SameSite=Strict
// Frontend: withCredentials: true en axios
```

#### **2. Falta de Validación de Tenant ID**
```python
# ❌ VULNERABLE: No verifica tenant_id en queries
async def get_leads():
    leads = await db.pool.fetch("SELECT * FROM leads")  # ❌ Sin tenant_id
    
# ✅ SOLUCIÓN: Todas las queries deben incluir tenant_id
async def get_leads(tenant_id: int):
    leads = await db.pool.fetch("SELECT * FROM leads WHERE tenant_id = $1", tenant_id)
```

#### **3. Sin Encriptación de Credenciales**
```python
# ❌ VULNERABLE: Credenciales en texto plano
await db.pool.execute("INSERT INTO credentials VALUES ($1, $2, $3)", 
                     tenant_id, 'META_TOKEN', 'plain_text_token')  # ❌

# ✅ SOLUCIÓN: Encriptación Fernet
encrypted = encrypt_value('plain_text_token')
await db.pool.execute("INSERT INTO credentials VALUES ($1, $2, $3)",
                     tenant_id, 'META_TOKEN', encrypted)
```

#### **4. Falta de Headers de Seguridad HTTP**
```python
# ❌ VULNERABLE: Sin CSP, HSTS, X-Frame-Options
# ✅ SOLUCIÓN: Implementar SecurityHeadersMiddleware
```

#### **5. RBAC Básico sin Granularidad**
```python
# ❌ VULNERABLE: Solo verifica rol básico
if user.role != 'ceo':
    raise HTTPException(403)
    
# ✅ SOLUCIÓN: Factory de permisos granular
@router.get("/admin/data", dependencies=[Depends(require_role(['ceo', 'admin']))])
```

#### **6. Sin Auditoría de Accesos**
```python
# ❌ VULNERABLE: No se registra quién accede a qué
# ✅ SOLUCIÓN: Implementar log_pii_access() en todos los endpoints sensibles
```

---

## 🚀 PLAN DE IMPLEMENTACIÓN - FASE POR FASE

### **FASE 1: INFRAESTRUCTURA DE SEGURIDAD BACKEND**

#### **1.1. Migrar Componentes de Seguridad ClinicForge:**
```bash
# Copiar archivos de seguridad
cp clinicforge/orchestrator_service/core/auth.py crmventas/orchestrator_service/core/
cp clinicforge/orchestrator_service/core/security_middleware.py crmventas/orchestrator_service/core/
cp clinicforge/orchestrator_service/core/credentials.py crmventas/orchestrator_service/core/
cp clinicforge/orchestrator_service/core/prompt_security.py crmventas/orchestrator_service/core/
```

#### **1.2. Actualizar auth_service.py CRM:**
```python
# Actualizar para soportar JWT_SECRET_KEY (estándar) y mantener compatibilidad
SECRET_KEY = os.getenv("JWT_SECRET_KEY") or os.getenv("INTERNAL_SECRET_KEY")
if not SECRET_KEY:
    logger.critical("🛑 NO SECRET KEY DEFINED! Set JWT_SECRET_KEY immediately.")
    SECRET_KEY = "temporary-insecure-key"  # Solo para desarrollo
```

#### **1.3. Reemplazar security.py CRM con auth.py ClinicForge:**
```python
# Reemplazar crmventas/orchestrator_service/core/security.py
# con la versión completa de ClinicForge (auth.py)
# Mantener compatibilidad con roles CRM ('setter', 'closer')
```

#### **1.4. Configurar Middleware en main.py:**
```python
# En crmventas/orchestrator_service/main.py
from core.security_middleware import SecurityHeadersMiddleware

app = FastAPI()
app.add_middleware(SecurityHeadersMiddleware)
```

### **FASE 2: SISTEMA DE AUTENTICACIÓN FRONTEND**

#### **2.1. Migrar AuthContext ClinicForge:**
```typescript
// Reemplazar crmventas/frontend_react/src/context/AuthContext.tsx
// con la versión de ClinicForge que usa HttpOnly Cookies

// ClinicForge AuthContext (seguro):
const login = (_newToken: string, profile: User) => {
    // El token viene en Cookie HttpOnly, no se almacena en localStorage
    localStorage.setItem('USER_PROFILE', JSON.stringify(profile));
    localStorage.setItem('X-Tenant-ID', profile.tenant_id?.toString() || '1');
    setUser(profile);
};
```

#### **2.2. Actualizar axios.ts para HttpOnly Cookies:**
```typescript
// En crmventas/frontend_react/src/api/axios.ts
const api: AxiosInstance = axios.create({
    baseURL: API_URL,
    withCredentials: true,  // ✅ Envía cookies automáticamente
});

// Eliminar almacenamiento de JWT en localStorage
// El backend debe enviar Set-Cookie con HttpOnly flag
```

#### **2.3. Implementar ProtectedRoute ClinicForge:**
```typescript
// Copiar crmventas/frontend_react/src/components/ProtectedRoute.tsx
// desde ClinicForge (ya incluye validación de roles)
```

### **FASE 3: AISLAMIENTO MULTI-TENANT**

#### **3.1. Implementar Resolución de Tenant ID:**
```python
# En todas las rutas CRM, reemplazar:
# user_data = Depends(verify_admin_token)
# con:
# user_data, tenant_id = Depends(get_ceo_user_and_tenant)

# O para staff:
# user_data = Depends(verify_admin_token)
# tenant_id = Depends(get_resolved_tenant_id)
```

#### **3.2. Actualizar Todas las Queries:**
```python
# Patrón obligatorio para TODAS las queries:
async def get_leads(user_data, tenant_id):
    leads = await db.pool.fetch("""
        SELECT * FROM leads 
        WHERE tenant_id = $1
        ORDER BY created_at DESC
    """, tenant_id)
    return leads
```

#### **3.3. Crear Middleware de Validación de Tenant:**
```python
# Middleware que valida que todas las queries incluyan tenant_id
# (Puede ser un decorator o validación en runtime)
```

### **FASE 4: ENCRIPTACIÓN DE CREDENCIALES**

#### **4.1. Configurar Fernet Key:**
```bash
# Generar clave Fernet
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Agregar al .env
CREDENTIALS_FERNET_KEY="generated_key_here"
```

#### **4.2. Crear Tabla credentials:**
```sql
-- Ejecutar en base de datos CRM
CREATE TABLE IF NOT EXISTS credentials (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    value TEXT NOT NULL,
    category TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (tenant_id, name)
);
```

#### **4.3. Migrar Credenciales Existentes:**
```python
# Script para encriptar credenciales existentes
async def migrate_existing_credentials():
    plain_creds = await db.pool.fetch("SELECT * FROM credentials WHERE value NOT LIKE 'g%'")
    for cred in plain_creds:
        encrypted = encrypt_value(cred['value'])
        await db.pool.execute(
            "UPDATE credentials SET value = $1 WHERE id = $2",
            encrypted, cred['id']
        )
```

### **FASE 5: AUDITORÍA Y MONITORING**

#### **5.1. Crear Tabla system_events:**
```sql
CREATE TABLE IF NOT EXISTS system_events (
    id BIGSERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,
    severity TEXT DEFAULT 'info',
    message TEXT,
    payload JSONB,
    occurred_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_system_events_type ON system_events(event_type);
CREATE INDEX idx_system_events_severity ON system_events(severity);
CREATE INDEX idx_system_events_occurred ON system_events(occurred_at DESC);
```

#### **5.2. Implementar Logging de Seguridad:**
```python
# Decorator para auditoría automática
def audit_access(action: str):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            request = kwargs.get('request') or args[0] if args else None
            user_data = getattr(request.state, 'user', None) if request else None
            
            if user_data and hasattr(func, '__name__'):
                # Extraer ID del recurso accedido
                resource_id = kwargs.get('lead_id') or kwargs.get('client_id') or 'unknown'
                
                await log_pii_access(
                    request=request,
                    user_data=user_data,
                    resource_id=resource_id,
                    action=f"{func.__name__}:{action}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Uso en endpoints
@router.get("/leads/{lead_id}")
@audit_access("read_lead")
async def get_lead(lead_id: int, user_data, tenant_id):
    # ... código existente
```

#### **5.3. Panel de Auditoría (Opcional):**
```typescript
// Vista de auditoría para CEOs
const AuditLogView = () => {
    const [logs, setLogs] = useState([]);
    
    useEffect(() => {
        loadAuditLogs();
    }, []);
    
    const loadAuditLogs = async () => {
        const response = await api.get('/admin/audit/logs');
        setLogs(response.data);
    };
    
    return (
        <div className="p-6">
            <h1 className="text-2xl font-bold mb-6">Auditoría de Seguridad</h1>
            <table className="w-full">
                <thead>
                    <tr>
                        <th>Usuario</th>
                        <th>Acción</th>
                        <th>Recurso</th>
                        <th>IP</th>
                        <th>Fecha</th>
                    </tr>
                </thead>
                <tbody>
                    {logs.map(log => (
                        <tr key={log.id}>
                            <td>{log.user_email}</td>
                            <td>{log.action}</td>
                            <td>{log.resource_id}</td>
                            <td>{log.ip_address}</td>
                            <td>{new Date(log.occurred_at).toLocaleString()}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};
```

### **FASE 6: HARDENING Y CONFIGURACIÓN**

#### **6.1. Variables de Entorno Obligatorias:**
```bash
# .env.production
JWT_SECRET_KEY=minimo_64_caracteres_aleatorios_complejos_seguros
ADMIN_TOKEN=token_infraestructura_estatico_seguro
CREDENTIALS_FERNET_KEY=clave_fernet_generada_automaticamente
CORS_ALLOWED_ORIGINS=https://tu-crm.com,https://app.tu-crm.com
```

#### **6.2. Configuración de Cookies Seguras:**
```python
# En endpoints de login
response.set_cookie(
    key="access_token",
    value=token,
    httponly=True,
    secure=True,  # Solo HTTPS
    samesite="strict",
    max_age=60*60*24*7  # 1 semana
)
```

#### **6.3. Rate Limiting (Opcional pero recomendado):**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

@router.get("/api/data")
@limiter.limit("100/minute")
async def get_data(request: Request):
    return {"data": "protegido por rate limiting"}
```

---

## 🔧 ESTRUCTURA DE ARCHIVOS FINAL

### **BACKEND CRM (Seguro):**
```
crmventas/orchestrator_service/
├── core/
│   ├── auth.py                    # ✅ Sistema completo ClinicForge
│   ├── security_middleware.py     # ✅ Headers de seguridad
│   ├── credentials.py             # ✅ Encriptación Fernet
│   ├── prompt_security.py         # ✅ Detección prompt injection
│   └── security.py → auth.py      # ❌ Reemplazar por auth.py ClinicForge
├── auth_service.py                # ✅ Actualizado con JWT_SECRET_KEY
└── main.py                        # ✅ Con middleware de seguridad
```

### **FRONTEND CRM (Seguro):**
```
crmventas/frontend_react/
├── src/
│   ├── context/
│   │   └── AuthContext.tsx        # ✅ HttpOnly Cookies (ClinicForge)
│   ├── api/
│   │   └── axios.ts               # ✅ withCredentials: true
│   └── components/
│       └── ProtectedRoute.tsx     # ✅ Validación roles completa
```

### **BASE DE DATOS (Seguro):**
```sql
-- Tablas de seguridad
credentials          -- Credenciales encriptadas
system_events        -- Auditoría
users                -- RBAC con bcrypt
professionals        -- Vinculación user-tenant

-- Todas las tablas de negocio deben tener:
-- tenant_id INTEGER NOT NULL REFERENCES tenants(id)
-- created_at/updated_at TIMESTAMPTZ
```

---

## 📋 CHECKLIST DE IMPLEMENTACIÓN

### **BACKEND (FastAPI)**
- [ ] Migrar `auth.py` completo de ClinicForge
- [ ] Implementar `SecurityHeadersMiddleware`
- [ ] Configurar sistema de credenciales encriptadas
- [ ] Actualizar `auth_service.py` con `JWT_SECRET_KEY`
- [ ] Implementar `prompt_security.py` para IA
- [ ] Crear tabla `system_events` para auditoría
- [ ] Actualizar TODAS las queries para incluir `tenant_id`
- [ ] Implementar cookies HttpOnly en login
- [ ] Crear decorator `@audit_access` para endpoints sensibles
- [ ] Configurar rate limiting (opcional)

### **FRONTEND (React)**
- [ ] Migrar `AuthContext.tsx` de ClinicForge (HttpOnly Cookies)
- [ ] Actualizar `axios.ts` con `withCredentials: true`
- [ ] Eliminar almacenamiento de JWT en `localStorage`
- [ ] Migrar `ProtectedRoute.tsx` de ClinicForge
- [ ] Actualizar manejo de `X-Tenant-ID` header
- [ ] Implementar redirección automática en 401

### **BASE DE DATOS**
- [ ] Crear tabla `credentials` con encriptación
- [ ] Crear tabla `system_events` para auditoría
- [ ] Verificar que todas las tablas tengan `tenant_id`
- [ ] Migrar credenciales existentes a formato encriptado
- [ ] Crear índices para performance de seguridad

### **CONFIGURACIÓN**
- [ ] Configurar `JWT_SECRET_KEY` en producción
- [ ] Configurar `ADMIN_TOKEN` estático
- [ ] Generar y configurar `CREDENTIALS_FERNET_KEY`
- [ ] Configurar `CORS_ALLOWED_ORIGINS` estrictos
- [ ] Configurar cookies `Secure`, `HttpOnly`, `SameSite=Strict`

### **DEPLOYMENT**
- [ ] Forzar HTTPS en producción
- [ ] Configurar headers de seguridad en proxy (nginx)
- [ ] Implementar WAF (Web Application Firewall)
- [ ] Configurar logging centralizado
- [ ] Plan de rotación de tokens/credenciales

---

## ⚡ PLAN DE EJECUCIÓN RÁPIDO (7 DÍAS)

### **DÍA 1: Infraestructura Backend**
1. Migrar `auth.py`, `security_middleware.py`, `credentials.py`
2. Configurar variables de entorno de seguridad
3. Actualizar `auth_service.py`

### **DÍA 2: Frontend Security**
1. Migrar `AuthContext.tsx` (HttpOnly Cookies)
2. Actualizar `axios.ts` (`withCredentials: true`)
3. Migrar `ProtectedRoute.tsx`

### **DÍA 3: Aislamiento Multi-Tenant**
1. Implementar `get_resolved_tenant_id()`
2. Actualizar TODAS las queries con `tenant_id`
3. Crear middleware de validación

### **DÍA 4: Encriptación de Credenciales**
1. Crear tabla `credentials`
2. Implementar encriptación Fernet
3. Migrar credenciales existentes

### **DÍA 5: Auditoría y Logging**
1. Crear tabla `system_events`
2. Implementar `@audit_access` decorator
3. Crear endpoints de auditoría

### **DÍA 6: Hardening y Configuración**
1. Configurar cookies seguras
2. Implementar rate limiting
3. Configurar CORS estrictos

### **DÍA 7: Testing y Depuración**
1. Probar flujos de autenticación
2. Verificar aislamiento de datos
3. Auditar vulnerabilidades restantes

---

## 🚨 RIESGOS Y MITIGACIONES

### **Riesgos Técnicos:**
1. **Breaking changes:** Cambios en autenticación pueden romper clientes existentes
   - **Mitigación:** Mantener compatibilidad con tokens Bearer durante transición

2. **Performance:** Encriptación/desencriptación puede afectar performance
   - **Mitigación:** Caching de credenciales frecuentes, optimizar Fernet

3. **Complexity:** Sistema de seguridad complejo puede tener bugs
   - **Mitigación:** Testing exhaustivo, gradual rollout

### **Riesgos de Negocio:**
1. **Downtime:** Migración puede causar interrupciones
   - **Mitigación:** Realizar en horario de baja actividad, backup completo

2. **Data Loss:** Migración de credenciales puede fallar
   - **Mitigación:** Backup de tabla credentials antes de migrar

3. **User Experience:** HttpOnly Cookies pueden romper algunos flujos
   - **Mitigación:** Testing cross-browser, fallback a Bearer token

### **Mitigaciones Específicas:**
- **Rollback Plan:** Poder revertir a sistema anterior rápidamente
- **Monitoring:** Alertas para fallos de autenticación
- **Documentación:** Guías para troubleshooting

---

## 📈 MÉTRICAS DE ÉXITO

### **Técnicas:**
- ✅ 0 tokens JWT en `localStorage`
- ✅ 100% de queries incluyen `tenant_id`
- ✅ 100% de credenciales encriptadas
- ✅ Headers de seguridad presentes en todas las respuestas
- ✅ Auditoría de todos los accesos a datos sensibles

### **De Seguridad:**
- 🔒 Resistente a XSS (HttpOnly Cookies)
- 🔒 Aislamiento completo multi-tenant
- 🔒 Credenciales encriptadas en reposo
- 🔒 Detección de prompt injection
- 🔒 Rate limiting en endpoints críticos

### **De Negocio:**
- 📊 Compliance con regulaciones de privacidad
- 📊 Auditoría completa de accesos
- 📊 Confianza de clientes en seguridad
- 📊 Reducción de riesgo de brechas de datos

---

## 🎯 CONCLUSIÓN

La implementación del **sistema de seguridad de ClinicForge en CRM Sales** es **crítica y urgente** debido a las vulnerabilidades actuales:

### **🚨 VULNERABILIDADES CRÍTICAS ACTUALES:**
1. **XSS:** Tokens en localStorage
2. **Data Leakage:** Sin aislamiento multi-tenant
3. **Credential Exposure:** Credenciales en texto plano
4. **Lack of Auditing:** Sin registro de accesos

### **✅ BENEFICIOS DE LA MIGRACIÓN:**
1. **Seguridad Empresarial:** Nivel ClinicForge (probado en producción)
2. **Compliance:** Cumple con mejores prácticas de seguridad
3. **Escalabilidad:** Arquitectura lista para multi-tenant masivo
4. **Confianza:** Clientes pueden confiar en la plataforma

### **⏱️ ESFUERZO ESTIMADO: 7 días**
### **📊 COMPLEJIDAD: Alta** (cambios arquitectónicos profundos)
### **⚠️ RIESGO: Medio-Alto** (pero necesario por vulnerabilidades críticas)

**RECOMENDACIÓN:** Proceder **INMEDIATAMENTE** con la implementación, comenzando por las vulnerabilidades más críticas (XSS y aislamiento multi-tenant).

---

## 📞 SOPORTE Y DEBUGGING

### **Problemas comunes esperados:**
1. **CORS errors:** Verificar `withCredentials: true` y `CORS_ALLOWED_ORIGINS`
2. **Cookie not sent:** Verificar `Secure` flag en desarrollo HTTP
3. **Tenant isolation failures:** Verificar `X-Tenant-ID` header y resolución
4. **Encryption/decryption failures:** Verificar `CREDENTIALS_FERNET_KEY`

### **Herramientas de debugging:**
- **Browser DevTools:** Network tab para ver cookies/headers
- **Postman/Insomnia:** Testing de endpoints con diferentes auth methods
- **Database queries:** Verificar tenant_id en queries
- **Logs de auditoría:** Tabla `system_events` para troubleshooting

### **Procedimiento de Rollback:**
1. Revertir cambios en `AuthContext.tsx` y `axios.ts`
2. Restaurar `security.py` original
3. Deshabilitar middleware de seguridad
4. Revertir migraciones de base de datos

---

**Documentación creada por:** DevFusa  
**Fecha:** 25 de Febrero 2026  
**Repositorio:** CRM Ventas  
**Urgencia:** CRÍTICA (vulnerabilidades de seguridad)  
**Estado:** Listo para implementación inmediata  

*"La seguridad no es un feature, es el foundation."*