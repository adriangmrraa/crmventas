# 🔧 CONFIGURACIÓN DE VARIABLES DE ENTORNO - CRM VENTAS META ADS

## 📋 ARCHIVOS DE CONFIGURACIÓN REQUERIDOS

### **1. Producción (.env.production):**

```bash
# ============================================
# META OAUTH CONFIGURATION (REQUERIDO)
# ============================================

# App ID de Meta Developers (obligatorio)
META_APP_ID=123456789012345

# App Secret de Meta Developers (obligatorio)
META_APP_SECRET=abcdef1234567890abcdef1234567890

# Redirect URI configurado en Meta Developers (obligatorio)
META_REDIRECT_URI=https://tu-crm.com/crm/auth/meta/callback

# Versión Graph API (opcional, default v21.0)
META_GRAPH_API_VERSION=v21.0

# Token para verificación webhooks (opcional)
META_VERIFY_TOKEN=token_aleatorio_seguro_para_webhooks


# ============================================
# DATABASE CONFIGURATION (REQUERIDO)
# ============================================

# PostgreSQL connection string
POSTGRES_DSN=postgresql://usuario:contraseña@servidor:5432/crmventas_prod

# Pool configuration
DB_POOL_MIN=5
DB_POOL_MAX=20
DB_POOL_TIMEOUT=30


# ============================================
# SECURITY CONFIGURATION (REQUERIDO)
# ============================================

# JWT Secret Key (mínimo 32 caracteres)
JWT_SECRET_KEY=tu_jwt_secret_key_minimo_32_caracteres_aqui

# Encryption Key para tokens (exactamente 32 bytes)
ENCRYPTION_KEY=tu_encryption_key_32_bytes_exactos_aqui

# CORS origins permitidos
CORS_ORIGINS=https://app.tu-crm.com,https://tu-crm.com


# ============================================
# APPLICATION CONFIGURATION
# ============================================

# Base URL API
API_BASE_URL=https://api.tu-crm.com

# Base URL Frontend
FRONTEND_URL=https://app.tu-crm.com

# Environment
ENVIRONMENT=production

# Log level
LOG_LEVEL=INFO

# Port
PORT=8000
```

### **2. Desarrollo (.env.development):**

```bash
# ============================================
# META OAUTH CONFIGURATION (DESARROLLO)
# ============================================

# App ID de desarrollo (puede ser sandbox)
META_APP_ID=987654321098765

# App Secret de desarrollo
META_APP_SECRET=development_secret_abcdef1234567890

# Redirect URI local
META_REDIRECT_URI=http://localhost:8000/crm/auth/meta/callback

# Versión Graph API
META_GRAPH_API_VERSION=v21.0


# ============================================
# DATABASE CONFIGURATION (DESARROLLO)
# ============================================

# PostgreSQL local
POSTGRES_DSN=postgresql://postgres:postgres@localhost:5432/crmventas_dev

# Pool configuration
DB_POOL_MIN=2
DB_POOL_MAX=10


# ============================================
# SECURITY CONFIGURATION (DESARROLLO)
# ============================================

# JWT Secret Key development
JWT_SECRET_KEY=development_secret_key_change_in_production

# Encryption Key development
ENCRYPTION_KEY=development_encryption_key_32_bytes_here

# CORS origins desarrollo
CORS_ORIGINS=http://localhost:3000,http://localhost:8000


# ============================================
# APPLICATION CONFIGURATION
# ============================================

# Base URL API local
API_BASE_URL=http://localhost:8000

# Base URL Frontend local
FRONTEND_URL=http://localhost:3000

# Environment
ENVIRONMENT=development

# Log level detallado
LOG_LEVEL=DEBUG

# Port
PORT=8000
```

### **3. Testing (.env.test):**

```bash
# ============================================
# META OAUTH CONFIGURATION (TESTING)
# ============================================

# Mock credentials para testing
META_APP_ID=test_app_id_123
META_APP_SECRET=test_app_secret_456
META_REDIRECT_URI=http://localhost:8000/crm/auth/meta/callback


# ============================================
# DATABASE CONFIGURATION (TESTING)
# ============================================

# PostgreSQL test database
POSTGRES_DSN=postgresql://postgres:postgres@localhost:5432/crmventas_test


# ============================================
# SECURITY CONFIGURATION (TESTING)
# ============================================

JWT_SECRET_KEY=test_jwt_secret_key_for_testing_only
ENCRYPTION_KEY=test_encryption_key_32_bytes_for_test


# ============================================
# APPLICATION CONFIGURATION
# ============================================

API_BASE_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
ENVIRONMENT=test
LOG_LEVEL=WARNING
```

---

## 🔧 PASOS DE CONFIGURACIÓN

### **Paso 1: Configurar Meta Developers App**

1. **Ir a:** https://developers.facebook.com/
2. **Crear nueva App:** Business → Otro
3. **Nombre:** "CRM Ventas Marketing Hub"
4. **Contact Email:** tu_email@empresa.com

### **Paso 2: Agregar Productos**

En el dashboard de la App, agregar:
```
1. WhatsApp → Business Management API
2. Facebook Login → OAuth 2.0
3. Marketing API → Ads Management
```

### **Paso 3: Configurar Facebook Login**

1. **Settings → Basic:**
   - App Domains: `tu-crm.com`, `app.tu-crm.com`
   - Privacy Policy URL: `https://tu-crm.com/privacy`
   - Terms of Service URL: `https://tu-crm.com/terms`

2. **Facebook Login → Settings:**
   - Valid OAuth Redirect URIs:
     ```
     https://tu-crm.com/crm/auth/meta/callback
     https://app.tu-crm.com/crm/auth/meta/callback
     http://localhost:8000/crm/auth/meta/callback (development)
     ```
   - Client OAuth Settings: ✅ Enable web OAuth login

### **Paso 4: Solicitar Permisos de API**

En "App Review → Permissions and Features", solicitar:
```
Permisos estándar:
- ads_management
- ads_read
- business_management

Permisos avanzados:
- whatsapp_business_management
- whatsapp_business_messaging
- pages_read_engagement
- read_insights
```

**Nota:** La revisión de Meta puede tomar 1-3 días.

### **Paso 5: Obtener Credenciales**

1. **Settings → Basic:**
   - App ID: Copiar al `META_APP_ID`
   - App Secret: Click "Show" y copiar al `META_APP_SECRET`

2. **Verificar:** App Status debe ser "Live" para producción.

---

## 🚀 CONFIGURACIÓN RÁPIDA PARA PRUEBAS

### **Script de configuración inicial:**

```bash
#!/bin/bash
# setup_env.sh

echo "🔧 Configurando entorno CRM Ventas..."

# Crear archivos .env
cat > .env.production << 'EOF'
META_APP_ID=REPLACE_WITH_YOUR_APP_ID
META_APP_SECRET=REPLACE_WITH_YOUR_APP_SECRET
META_REDIRECT_URI=https://your-domain.com/crm/auth/meta/callback
POSTGRES_DSN=postgresql://user:password@host:5432/crmventas
JWT_SECRET_KEY=$(openssl rand -hex 32)
ENCRYPTION_KEY=$(openssl rand -hex 32)
API_BASE_URL=https://api.your-domain.com
FRONTEND_URL=https://app.your-domain.com
EOF

cat > .env.development << 'EOF'
META_APP_ID=development_app_id_placeholder
META_APP_SECRET=development_app_secret_placeholder
META_REDIRECT_URI=http://localhost:8000/crm/auth/meta/callback
POSTGRES_DSN=postgresql://postgres:postgres@localhost:5432/crmventas_dev
JWT_SECRET_KEY=development_secret_key_change_in_production
ENCRYPTION_KEY=development_encryption_key_32_bytes_here
API_BASE_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
ENVIRONMENT=development
EOF

echo "✅ Archivos .env creados"
echo "📋 Siguientes pasos:"
echo "   1. Configurar Meta Developers App"
echo "   2. Reemplazar valores en .env.production"
echo "   3. Ejecutar migraciones: python3 run_meta_ads_migrations.py"
```

---

## 🔍 VERIFICACIÓN DE CONFIGURACIÓN

### **Comando de verificación:**

```bash
#!/bin/bash
# verify_config.sh

echo "🔍 Verificando configuración..."

# Verificar variables requeridas
required_vars=("META_APP_ID" "META_APP_SECRET" "META_REDIRECT_URI" "POSTGRES_DSN")

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Variable faltante: $var"
        exit 1
    else
        echo "✅ $var está configurada"
    fi
done

# Verificar formatos
if [[ ! "$META_APP_ID" =~ ^[0-9]+$ ]]; then
    echo "❌ META_APP_ID debe ser numérico"
    exit 1
fi

if [[ ! "$META_REDIRECT_URI" =~ ^https?:// ]]; then
    echo "❌ META_REDIRECT_URI debe comenzar con http:// o https://"
    exit 1
fi

if [[ ! "$POSTGRES_DSN" =~ ^postgresql:// ]]; then
    echo "❌ POSTGRES_DSN debe comenzar con postgresql://"
    exit 1
fi

echo "🎉 Configuración verificada correctamente"
```

### **Test de conexión OAuth:**

```python
# test_oauth_config.py
import os

def test_configuration():
    """Test básico de configuración OAuth"""
    
    print("🧪 Testing OAuth configuration...")
    
    # Variables requeridas
    required = ['META_APP_ID', 'META_APP_SECRET', 'META_REDIRECT_URI']
    
    for var in required:
        value = os.getenv(var)
        if not value:
            print(f"❌ {var} no está configurada")
            return False
        elif var == 'META_APP_ID' and not value.isdigit():
            print(f"❌ {var} debe ser numérico")
            return False
        elif var == 'META_REDIRECT_URI' and not value.startswith(('http://', 'https://')):
            print(f"❌ {var} debe comenzar con http:// o https://")
            return False
        else:
            print(f"✅ {var}: {value[:20]}...")
    
    print("🎉 Configuración OAuth OK")
    return True

if __name__ == "__main__":
    success = test_configuration()
    exit(0 if success else 1)
```

---

## 🚨 TROUBLESHOOTING

### **Problema: "Invalid redirect_uri"**
```bash
# Causa: META_REDIRECT_URI no coincide exactamente con Meta Developers
# Solución:
1. Copiar exactamente la URI de .env a Meta Developers
2. Incluir protocolo completo (https://)
3. Verificar que no haya espacios extras
4. Para localhost: usar http://localhost:8000/crm/auth/meta/callback
```

### **Problema: "App not approved for permissions"**
```bash
# Causa: Permisos no aprobados por Meta
# Solución:
1. Solicitar revisión en Meta Developers
2. Proporcionar video demostrando uso
3. Usar sandbox mode mientras se aprueba
4. Puede tomar 1-3 días
```

### **Problema: "Can't load URL" en OAuth flow**
```bash
# Causa: App Domains no configurados
# Solución:
1. En Meta Developers → Settings → Basic
2. Agregar App Domains: tu-crm.com, app.tu-crm.com
3. Guardar cambios
```

### **Problema: "Database connection failed"**
```bash
# Causa: POSTGRES_DSN incorrecto
# Solución:
1. Verificar formato: postgresql://user:password@host:5432/database
2. Verificar credenciales
3. Verificar que PostgreSQL esté corriendo
4. Verificar firewall/network access
```

---

## 📊 MONITORING CONFIGURATION

### **Health Check Endpoint:**

```python
# Endpoint: GET /health
{
  "status": "healthy",
  "timestamp": "2026-02-25T12:00:00",
  "services": {
    "database": "connected",
    "meta_oauth": "configured",
    "redis": "connected"
  },
  "version": "1.0.0",
  "environment": "production"
}
```

### **Environment Info Endpoint:**

```python
# Endpoint: GET /crm/auth/meta/debug/env (solo desarrollo)
{
  "meta_app_id_configured": true,
  "meta_redirect_uri": "https://tu-crm.com/crm/auth/meta/callback",
  "environment": "production",
  "api_base_url": "https://api.tu-crm.com"
}
```

---

## 🎯 RESUMEN

### **Configuración mínima para funcionar:**
```bash
# 4 variables REQUERIDAS:
META_APP_ID=123456789012345
META_APP_SECRET=abcdef1234567890abcdef1234567890
META_REDIRECT_URI=https://tu-crm.com/crm/auth/meta/callback
POSTGRES_DSN=postgresql://user:password@host:5432/crmventas
```

### **Pasos completos:**
1. ✅ Crear Meta Developers App
2. ✅ Configurar OAuth settings
3. ✅ Solicitar permisos de API
4. ✅ Configurar variables entorno
5. ✅ Ejecutar migraciones database
6. ✅ Testear OAuth flow

### **Tiempo estimado:**
- **Configuración inicial:** 30-60 minutos
- **Aprobación permisos Meta:** 1-3 días (puede usar sandbox)
- **Testing completo:** 60 minutos
- **Deployment producción:** 30 minutos

---

**Documentación generada:** 25 Feb 2026  
**Estado:** ✅ **LISTO PARA CONFIGURACIÓN**  
**Siguiente paso:** Configurar Meta Developers App y variables entorno