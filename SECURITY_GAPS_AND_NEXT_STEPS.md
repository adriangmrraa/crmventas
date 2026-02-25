# 🔴 GAPS DE SEGURIDAD Y PRÓXIMOS PASOS - CRM VENTAS

**Fecha:** 25 de Febrero 2026  
**Estado:** Implementación Nexus Security v7.6 - 70% completada  
**Urgencia:** ALTA - Variables críticas faltantes comprometen seguridad

---

## 📊 RESUMEN DE ESTADO ACTUAL

### ✅ **IMPLEMENTADO CORRECTAMENTE:**

1. **HttpOnly Cookies** - JWT en cookies seguras (mitigación XSS)
2. **Security Headers Middleware** - CSP, HSTS, X-Frame-Options
3. **Fernet Encryption Code** - Código para encriptación de credenciales
4. **Prompt Security** - Detección de injection para IA
5. **RBAC Granular** - Sistema de permisos por rol
6. **AuthContext Frontend** - Compatibilidad con cookies
7. **Documentación OWASP** - Auditoría completa documentada

### 🔴 **FALTANTE CRÍTICO (URGENTE):**

1. **Variables de entorno de seguridad** - Sin ellas, el sistema es vulnerable
2. **Tablas de base de datos** - `credentials` y `system_events` no creadas
3. **Auditoría de accesos** - Sin logging de seguridad
4. **Rate limiting** - Sin protección contra brute force
5. **Validación completa multi-tenant** - Algunas queries sin `tenant_id`

---

## 🚨 PASO 1: VARIABLES DE ENTORNO CRÍTICAS (URGENTE - 5 MINUTOS)

### **Variables FALTANTES en `.env`:**

```bash
# 🔴 GENERAR INMEDIATAMENTE (ejecutar en terminal):

# 1. JWT_SECRET_KEY (mínimo 64 caracteres)
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(64))"

# 2. CREDENTIALS_FERNET_KEY (clave Fernet para encriptación)
python3 -c "from cryptography.fernet import Fernet; print('CREDENTIALS_FERNET_KEY=' + Fernet.generate_key().decode())"

# 3. ADMIN_TOKEN (token estático de infraestructura)
openssl rand -hex 32 | awk '{print "ADMIN_TOKEN="$1}'

# 4. CORS_ALLOWED_ORIGINS (orígenes permitidos)
echo "CORS_ALLOWED_ORIGINS=https://tu-crm.com,https://app.tu-crm.com"

# 5. CSP_EXTRA_DOMAINS (dominios extra para CSP)
echo "CSP_EXTRA_DOMAINS=*.openai.com,*.facebook.com,*.ycloud.com"
```

### **Archivo `.env` COMPLETO requerido:**

```bash
# 🔐 SEGURIDAD - VARIABLES CRÍTICAS
JWT_SECRET_KEY=tu_jwt_secret_key_de_64_caracteres_minimo_generado_aleatoriamente
CREDENTIALS_FERNET_KEY=tu_clave_fernet_generada_automaticamente_32_bytes_base64
ADMIN_TOKEN=tu_token_estatico_infraestructura_hex_64_caracteres

# 🌐 NETWORK & CORS
CORS_ALLOWED_ORIGINS=https://tu-crm.com,https://app.tu-crm.com,http://localhost:5173
CSP_EXTRA_DOMAINS=*.openai.com,*.facebook.com,*.messenger.com,*.fbcdn.net,*.ycloud.com,api.apify.com

# 🗄️ DATABASE
POSTGRES_DSN=postgresql://user:password@localhost:5432/crmventas

# 🤖 IA SERVICES
OPENAI_API_KEY=sk-...

# 📱 WHATSAPP / YCLOUD
YCLOUD_API_KEY=tu_ycloud_api_key
YCLOUD_WEBHOOK_SECRET=tu_webhook_secret
YCLOUD_WHATSAPP_NUMBER=5491100000000

# 🏢 META ADS (opcional para Marketing Hub)
META_APP_ID=tu_meta_app_id
META_APP_SECRET=tu_meta_app_secret
META_REDIRECT_URI=https://tu-crm.com/auth/meta/callback

# ⚙️ CONFIGURACIÓN
LOG_LEVEL=INFO
IS_PRODUCTION=true
PLATFORM_URL=https://tu-crm.com
```

### **Verificación de variables:**
```bash
# Verificar que todas las variables críticas estén configuradas
python3 -c "
import os
required = ['JWT_SECRET_KEY', 'CREDENTIALS_FERNET_KEY', 'ADMIN_TOKEN', 'POSTGRES_DSN']
missing = [var for var in required if not os.getenv(var)]
if missing:
    print(f'🚨 VARIABLES FALTANTES: {missing}')
else:
    print('✅ Todas las variables críticas configuradas')
"
```

---

## 🗄️ PASO 2: MIGRACIONES DE BASE DE DATOS (15 MINUTOS)

### **2.1. Crear tabla `credentials` (Encriptación Fernet):**

```sql
-- Ejecutar en PostgreSQL CRM Ventas
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

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_credentials_tenant ON credentials(tenant_id);
CREATE INDEX IF NOT EXISTS idx_credentials_name ON credentials(name);
CREATE INDEX IF NOT EXISTS idx_credentials_category ON credentials(category);
```

### **2.2. Crear tabla `system_events` (Auditoría):**

```sql
CREATE TABLE IF NOT EXISTS system_events (
    id BIGSERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,
    severity TEXT DEFAULT 'info' CHECK (severity IN ('info', 'warning', 'critical')),
    message TEXT,
    payload JSONB,
    occurred_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para queries de auditoría
CREATE INDEX IF NOT EXISTS idx_system_events_type ON system_events(event_type);
CREATE INDEX IF NOT EXISTS idx_system_events_severity ON system_events(severity);
CREATE INDEX IF NOT EXISTS idx_system_events_occurred ON system_events(occurred_at DESC);

-- Índice para búsqueda en payload JSON
CREATE INDEX IF NOT EXISTS idx_system_events_payload ON system_events USING gin(payload);
```

### **2.3. Script de migración de credenciales existentes:**

```python
# save_as: migrate_credentials.py
import asyncio
import os
import sys
sys.path.append('orchestrator_service')

from core.credentials import encrypt_value
from db import get_pool

async def migrate_existing_credentials():
    """Migra credenciales existentes de texto plano a encriptadas."""
    pool = get_pool()
    
    # 1. Verificar si CREDENTIALS_FERNET_KEY está configurada
    fernet_key = os.getenv("CREDENTIALS_FERNET_KEY")
    if not fernet_key:
        print("🚨 ERROR: CREDENTIALS_FERNET_KEY no configurada")
        return False
    
    # 2. Obtener todas las credenciales en texto plano
    rows = await pool.fetch("""
        SELECT id, tenant_id, name, value, category 
        FROM credentials 
        WHERE value NOT LIKE 'g%'  -- Los valores Fernet empiezan con 'g'
    """)
    
    if not rows:
        print("✅ No hay credenciales para migrar (ya encriptadas o vacías)")
        return True
    
    print(f"🔧 Migrando {len(rows)} credenciales a encriptación Fernet...")
    
    # 3. Encriptar cada credencial
    migrated = 0
    for row in rows:
        try:
            encrypted = encrypt_value(row['value'])
            await pool.execute(
                "UPDATE credentials SET value = $1, updated_at = NOW() WHERE id = $2",
                encrypted, row['id']
            )
            migrated += 1
            print(f"  ✓ {row['name']} (tenant {row['tenant_id']})")
        except Exception as e:
            print(f"  ✗ Error migrando {row['name']}: {e}")
    
    print(f"✅ Migración completada: {migrated}/{len(rows)} credenciales")
    return True

if __name__ == "__main__":
    asyncio.run(migrate_existing_credentials())
```

**Ejecutar migración:**
```bash
cd /home/node/.openclaw/workspace/projects/crmventas
python3 migrate_credentials.py
```

---

## 🔍 PASO 3: AUDITORÍA DE QUERIES MULTI-TENANT (30 MINUTOS)

### **3.1. Endpoints a revisar (prioridad alta):**

| Archivo | Líneas aproximadas | Estado |
|---------|-------------------|--------|
| `orchestrator_service/admin_routes.py` | 1-800 | ⚠️ Revisar |
| `orchestrator_service/modules/crm_sales/routes.py` | 1-600 | ⚠️ Revisar |
| `orchestrator_service/modules/dental/routes.py` | 1-400 | ⚠️ Revisar |
| `orchestrator_service/auth_routes.py` | 1-300 | ✅ OK |

### **3.2. Script de auditoría automática:**

```python
# save_as: audit_tenant_queries.py
import re
import os
import sys

def audit_file(filepath):
    """Audita un archivo Python para queries sin tenant_id."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Patrones de queries SQL
    patterns = [
        r'await db\.pool\.fetch\([^)]*\)',
        r'await db\.pool\.fetchrow\([^)]*\)',
        r'await db\.pool\.fetchval\([^)]*\)',
        r'await db\.pool\.execute\([^)]*\)',
    ]
    
    issues = []
    lines = content.split('\n')
    
    for i, line in enumerate(lines, 1):
        # Buscar queries SQL
        for pattern in patterns:
            if re.search(pattern, line):
                # Verificar si incluye tenant_id en WHERE
                if 'tenant_id' not in line.lower() and 'where' in line.lower():
                    # Excepciones permitidas (queries globales)
                    exceptions = [
                        'SELECT id FROM tenants',
                        'FROM tenants',
                        'FROM users',
                        'FROM credentials WHERE name',
                        'FROM system_events',
                    ]
                    
                    if not any(exc in line for exc in exceptions):
                        issues.append({
                            'line': i,
                            'content': line.strip(),
                            'file': filepath
                        })
    
    return issues

def main():
    base_dir = 'orchestrator_service'
    files_to_audit = [
        f'{base_dir}/admin_routes.py',
        f'{base_dir}/modules/crm_sales/routes.py',
        f'{base_dir}/modules/dental/routes.py',
        f'{base_dir}/auth_routes.py',
    ]
    
    all_issues = []
    for filepath in files_to_audit:
        if os.path.exists(filepath):
            issues = audit_file(filepath)
            all_issues.extend(issues)
    
    if all_issues:
        print("🚨 QUERIES SIN tenant_id ENCONTRADAS:\n")
        for issue in all_issues:
            print(f"📄 {issue['file']}:{issue['line']}")
            print(f"   {issue['content']}")
            print()
        
        print(f"📊 Total: {len(all_issues)} issues encontradas")
        return False
    else:
        print("✅ Todas las queries incluyen tenant_id correctamente")
        return True

if __name__ == "__main__":
    main()
```

### **3.3. Patrón CORRECTO a seguir:**

```python
# ❌ INCORRECTO (vulnerable):
leads = await db.pool.fetch("SELECT * FROM leads")

# ✅ CORRECTO (seguro):
leads = await db.pool.fetch("""
    SELECT * FROM leads 
    WHERE tenant_id = $1
    ORDER BY created_at DESC
""", tenant_id)

# ✅ CORRECTO para CEOs (pueden ver múltiples tenants):
allowed_tenant_ids = await get_allowed_tenant_ids(user_data)
leads = await db.pool.fetch("""
    SELECT * FROM leads 
    WHERE tenant_id = ANY($1::int[])
    ORDER BY created_at DESC
""", allowed_tenant_ids)
```

---

## 📝 PASO 4: IMPLEMENTAR SISTEMA DE AUDITORÍA (1 HORA)

### **4.1. Extender security.py con auditoría:**

```python
# Agregar al final de orchestrator_service/core/security.py

async def log_security_event(
    request: Request,
    user_data,
    event_type: str,
    severity: str = "info",
    resource_id: Any = None,
    details: str = ""
):
    """
    Registra evento de seguridad en system_events.
    """
    from db import db
    
    payload = {
        "user_id": user_data.user_id,
        "user_email": user_data.email,
        "user_role": user_data.role,
        "resource_id": resource_id,
        "details": details,
        "ip_address": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", ""),
        "path": request.url.path,
        "method": request.method,
    }
    
    try:
        await db.pool.execute("""
            INSERT INTO system_events (event_type, severity, message, payload)
            VALUES ($1, $2, $3, $4::jsonb)
        """, event_type, severity, f"{user_data.role}@{user_data.email}: {event_type}", json.dumps(payload))
    except Exception as e:
        logger.error(f"Error logging security event: {e}")

def audit_access(event_type: str, resource_param: str = "id"):
    """
    Decorator para auditoría automática de accesos.
    
    Uso:
        @router.get("/leads/{lead_id}")
        @audit_access("read_lead", resource_param="lead_id")
        async def get_lead(lead_id: int, ...):
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Encontrar request y user_data en args/kwargs
            request = None
            user_data = None
            
            for arg in args:
                if hasattr(arg, 'state') and hasattr(arg.state, 'user'):
                    request = arg
                    user_data = arg.state.user
                    break
            
            if not request:
                for key, value in kwargs.items():
                    if hasattr(value, 'state') and hasattr(value.state, 'user'):
                        request = value
                        user_data = value.state.user
                        break
            
            if request and user_data:
                # Obtener ID del recurso
                resource_id = kwargs.get(resource_param) or "unknown"
                
                await log_security_event(
                    request=request,
                    user_data=user_data,
                    event_type=event_type,
                    severity="info",
                    resource_id=resource_id,
                    details=f"Accessed via {func.__name__}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

### **4.2. Agregar imports necesarios:**

```python
# Al inicio de security.py, agregar:
import json
```

### **4.3. Aplicar auditoría a endpoints críticos:**

```python
# Ejemplo en admin_routes.py
from core.security import audit_access

@router.get("/leads/{lead_id}")
@audit_access("read_lead", resource_param="lead_id")
async def get_lead(lead_id: int, user_data, tenant_id):
    # ... código existente

@router.put("/leads/{lead_id}")
@audit_access("update_lead", resource_param="lead_id")
async def update_lead(lead_id: int, data: dict, user_data, tenant_id):
    # ... código existente

@router.delete("/leads/{lead_id}")
@audit_access("delete_lead", resource_param="lead_id")
async def delete_lead(lead_id: int, user_data, tenant_id):
    # ... código existente
```

### **4.4. Endpoint para consultar logs de auditoría:**

```python
# Agregar en admin_routes.py
@router.get("/audit/logs")
async def get_audit_logs(
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Obtiene logs de auditoría (solo CEO).
    """
    if user_data.role != 'ceo':
        raise HTTPException(status_code=403, detail="Solo CEOs pueden ver logs de auditoría")
    
    query = """
        SELECT id, event_type, severity, message, payload, occurred_at
        FROM system_events
        WHERE 1=1
    """
    params = []
    
    if event_type:
        query += " AND event_type = $1"
        params.append(event_type)
    
    if severity:
        query += " AND severity = $2"
        params.append(severity)
    
    query += " ORDER BY occurred_at DESC LIMIT $3 OFFSET $4"
    params.extend([limit, offset])
    
    logs = await db.pool.fetch(query, *params)
    
    return {
        "logs": [
            {
                "id": log["id"],
                "event_type": log["event_type"],
                "severity": log["severity"],
                "message": log["message"],
                "payload": log["payload"],
                "occurred_at": log["occurred_at"].isoformat() if log["occurred_at"] else None
            }
            for log in logs
        ],
        "total": await db.pool.fetchval("SELECT COUNT(*) FROM system_events")
    }
```

---

## ⚡ PASO 5: RATE LIMITING (30 MINUTOS)

### **5.1. Instalar dependencias:**

```bash
pip install slowapi
```

### **5.2. Configurar rate limiting en main.py:**

```python
# Agregar al inicio de orchestrator_service/main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Configurar rate limiter
limiter = Limiter(key_func=get_remote_address)

# Agregar a la app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

### **5.3. Aplicar rate limits a endpoints críticos:**

```python
# En auth_routes.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/login")
@limiter.limit("5/minute")  # 5 intentos por minuto por IP
async def login(request: Request, credentials: dict):
    # ... código existente

@router.post("/register")
@limiter.limit("3/minute")  # 3 registros por minuto por IP
async def register(request: Request, user_data: dict):
    # ... código existente

# En admin_routes.py (proteger endpoints sensibles)
@router.get("/leads")
@limiter.limit("100/minute")  # 100 requests por minuto
async def get_leads(request: Request, user_data, tenant_id):
    # ... código existente
```

### **5.4. Configuración por entorno:**

```python
# En main.py, después de crear la app
if os.getenv("IS_PRODUCTION", "false").lower() == "true":
    # Límites más estrictos en producción
    app.state.limiter.default_limits = ["100/minute", "1000/hour"]
else:
    # Límites más flexibles en desarrollo
    app.state.limiter.default_limits = ["1000/minute"]
```

---

## 🧪 PASO 6: TESTING DE SEGURIDAD (30 MINUTOS)

### **6.1. Script de testing automatizado:**

```python
# save_as: test_security.py
import requests
import json
import sys

def test_http_only_cookies():
    """Test que verifica HttpOnly cookies."""
    print("🧪 Testing HttpOnly Cookies...")
    
    # Simular login
    response = requests.post(
        "http://localhost:8000/auth/login",
        json={"email": "test@example.com", "password": "test123"},
        allow_redirects=False
    )
    
    cookies = response.cookies
    access_token_cookie = cookies.get('access_token')
    
    if access_token_cookie:
        print("✅ Cookie 'access_token' encontrada")
        
        # Verificar que sea HttpOnly
        cookie_info = cookies.get_dict('access_token')
        if 'HttpOnly' in str(cookies):
            print("✅ Cookie marcada como HttpOnly")
        else:
            print("❌ Cookie NO es HttpOnly")
            return False
    else:
        print("❌ No se encontró cookie 'access_token'")
        return False
    
    return True

def test_security_headers():
    """Test que verifica headers de seguridad."""
    print("\n🧪 Testing Security Headers...")
    
    response = requests.get("http://localhost:8000/")
    headers = response.headers
    
    required_headers = {
        'X-Frame-Options': 'DENY',
        'X-Content-Type-Options': 'nosniff',
        'Strict-Transport-Security': lambda x: 'max-age=' in x,
        'Content-Security-Policy': lambda x: 'default-src' in x,
    }
    
    all_passed = True
    for header, expected in required_headers.items():
        if header in headers:
            if callable(expected):
                if expected(headers[header]):
                    print(f"✅ {header}: {headers[header][:50]}...")
                else:
                    print(f"❌ {header}: Valor incorrecto")
                    all_passed = False
            elif headers[header] == expected:
                print(f"✅ {header}: {headers[header]}")
            else:
                print(f"❌ {header}: Esperado '{expected}', obtenido '{headers[header]}'")
                all_passed = False
        else:
            print(f"❌ {header}: Header faltante")
            all_passed = False
    
    return all_passed

def test_jwt_validation():
    """Test que verifica validación JWT."""
    print("\n🧪 Testing JWT Validation...")
    
    # Intentar acceder sin token
    response = requests.get("http://localhost:8000/admin/leads")
    if response.status_code in [401, 403]:
        print("✅ Endpoint protegido rechaza acceso sin token")
    else:
        print(f"❌ Endpoint debería rechazar acceso, status: {response.status_code}")
        return False
    
    # Intentar con token inválido
    headers = {'Authorization': 'Bearer invalid_token'}
    response = requests.get("http://localhost:8000/admin/leads", headers=headers)
    if response.status_code in [401, 403]:
        print("✅ Endpoint rechaza token inválido")
    else:
        print(f"❌ Endpoint debería rechazar token inválido, status: {response.status_code}")
        return False
    
    return True

def main():
    print("🔒 SECURITY TEST SUITE - CRM VENTAS\n")
    
    tests = [
        test_http_only_cookies,
        test_security_headers,
        test_jwt_validation,
    ]
    
    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Error en test: {e}")
    
    print(f"\n📊 Resultados: {passed}/{len(tests)} tests pasados")
    
    if passed == len(tests):
        print("🎉 TODOS LOS TESTS DE SEGURIDAD PASARON")
        return 0
    else:
        print("🚨 ALGUNOS TESTS FALLARON - Revisar implementación")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

### **6.2. Ejecutar tests:**

```bash
cd /home/node/.openclaw/workspace/projects/crmventas
python3 test_security.py
```

---

## 📋 CHECKLIST FINAL DE IMPLEMENTACIÓN

### **🔐 VARIABLES DE ENTORNO:**
- [ ] `JWT_SECRET_KEY` configurada (64+ caracteres)
- [ ] `CREDENTIALS_FERNET_KEY` configurada (Fernet key)
- [ ] `ADMIN_TOKEN` configurado (hex 64 caracteres)
- [ ] `CORS_ALLOWED_ORIGINS` configurado
- [ ] `CSP_EXTRA_DOMAINS` configurado

### **🗄️ BASE DE DATOS:**
- [ ] Tabla `credentials` creada
- [ ] Tabla `system_events` creada
- [ ] Índices creados para performance
- [ ] Credenciales existentes migradas a encriptación

### **🔍 AUDITORÍA DE QUERIES:**
- [ ] Script de auditoría ejecutado
- [ ] Todas las queries incluyen `tenant_id`
- [ ] CEOs pueden ver múltiples tenants correctamente
- [ ] Staff solo puede ver su tenant asignado

### **📝 SISTEMA DE AUDITORÍA:**
- [ ] Función `log_security_event()` implementada
- [ ] Decorator `@audit_access()` implementado
- [ ] Endpoint `/admin/audit/logs` creado
- [ ] Auditoría aplicada a endpoints críticos

### **⚡ RATE LIMITING:**
- [ ] Dependencia `slowapi` instalada
- [ ] Rate limiter configurado en `main.py`
- [ ] Límites aplicados a `/auth/login`
- [ ] Límites aplicados a endpoints admin sensibles

### **🧪 TESTING:**
- [ ] Script `test_security.py` ejecutado
- [ ] Todos los tests pasan
- [ ] HttpOnly cookies funcionando
- [ ] Security headers presentes
- [ ] JWT validation funcionando

---

## 🚀 PLAN DE EJECUCIÓN RÁPIDO

### **HOY (Día 0):**
1. **✅ 17:00-17:05** - Generar variables de entorno críticas
2. **✅ 17:05-17:20** - Crear tablas de BD (`credentials`, `system_events`)
3. **✅ 17:20-17:50** - Ejecutar auditoría de queries y corregir issues

### **MAÑANA (Día 1):**
4. **08:00-09:00** - Implementar sistema de auditoría
5. **09:00-09:30** - Configurar rate limiting
6. **09:30-10:00** - Ejecutar tests de seguridad
7. **10:00-10:30** - Revisión final y deploy

---

## 📞 SOPORTE Y TROUBLESHOOTING

### **Problemas comunes:**

1. **"JWT_SECRET_KEY must be 32 url-safe base64-encoded bytes"**
   ```bash
   # Solución: Generar clave correcta
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **"Fernet key must be 32 url-safe base64-encoded bytes"**
   ```bash
   # Solución: Usar generate_key() de Fernet
   python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

3. **CORS errors con HttpOnly cookies**
   ```python
   # En main.py, configurar CORS con credentials:
   app.add_middleware(
       CORSMiddleware,
       allow_origins=origins,
       allow_credentials=True,  # ← IMPORTANTE
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

4. **Rate limiting bloqueando requests legítimas**
   ```python
   # Ajustar límites en desarrollo:
   if not IS_PRODUCTION:
       app.state.limiter.enabled = False
   ```

### **Verificación post-implementación:**

```bash
# 1. Verificar cookies HttpOnly
curl -I http://localhost:8000/auth/login

# 2. Verificar security headers
curl -I http://localhost:8000/

# 3. Verificar JWT validation
curl -H "Authorization: Bearer invalid" http://localhost:8000/admin/leads

# 4. Verificar rate limiting
for i in {1..6}; do curl -X POST http://localhost:8000/auth/login -d '{}'; echo; done
```

---

## 🎯 CONCLUSIÓN

La implementación de seguridad Nexus v7.6 está **70% completada**. Los componentes críticos faltantes son:

1. **🚨 VARIABLES DE ENTORNO** - Sin ellas, todo el sistema es vulnerable
2. **🗄️ TABLAS DE BD** - Sin `credentials` y `system_events`, no hay encriptación ni auditoría
3. **🔍 VALIDACIÓN MULTI-TENANT** - Algunas queries pueden estar exponiendo datos entre tenants
4. **📝 AUDITORÍA** - Sin logging de seguridad, no hay trazabilidad
5. **⚡ RATE LIMITING** - Sin protección contra ataques de fuerza bruta

**Prioridad:** Implementar en este orden:
1. Variables de entorno (URGENTE)
2. Tablas de BD
3. Auditoría de queries
4. Sistema de auditoría
5. Rate limiting

**Tiempo estimado total:** 2.5 horas
**Riesgo de no implementar:** ALTO - Vulnerabilidades críticas de seguridad

---

**Documentación creada por:** DevFusa  
**Fecha:** 25 de Febrero 2026  
**Repositorio:** CRM Ventas  
**Estado:** Guía de implementación para gaps de seguridad  
**Urgencia:** ALTA - Completar implementación Nexus v7.6