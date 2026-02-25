# Variables de Entorno - Guía Completa

Este proyecto se configura completamente mediante variables de entorno. En despliegue de EasyPanel, carga estas variables para cada microservicio.

## 1. Variables Globales (Todos los Servicios)

| Variable | Descripción | Ejemplo | Requerida |
| :--- | :--- | :--- | :--- |
| `INTERNAL_API_TOKEN` | Token de seguridad entre microservicios | `compu-global-hyper-mega-net` | ✅ |
| `OPENAI_API_KEY` | Clave API de OpenAI (GPT-4o-mini + Whisper) | `sk-proj-xxxxx` | ✅ |
| `REDIS_URL` | URL de conexión a Redis | `redis://redis:6379` | ✅ |
| `POSTGRES_DSN` | URL de conexión a PostgreSQL | `postgres://user:pass@db:5432/database` | ✅ |

## 2. Orchestrator Service (8000)

### 2.1 Identidad y Branding (Whitelabel)

| Variable | Descripción | Ejemplo | Requerida |
| :--- | :--- | :--- | :--- |
| `STORE_NAME` | Nombre de la clínica (legacy/fallback) | `Dentalogic` | ❌ |
| `BOT_PHONE_NUMBER` | Número de WhatsApp del bot (fallback cuando no viene `to_number` en la petición) | `+5493756123456` | ❌ |
| `CLINIC_NAME` | Nombre de clínica usado como fallback si la sede no tiene `clinic_name` en BD | `Clínica Dental` | ❌ |
| `CLINIC_LOCATION` | Ubicación (usado en respuestas de configuración; opcional) | `República de Francia 2899, Mercedes, Buenos Aires` | ❌ |
| `STORE_LOCATION` | Ciudad/País | `Paraná, Entre Ríos, Argentina` | ❌ |
| `STORE_WEBSITE` | URL de la clínica | `https://www.odontolea.com` | ❌ |
| `STORE_DESCRIPTION` | Especialidad clínica | `Salud Bucal e Implantología` | ❌ |
| `STORE_CATALOG_KNOWLEDGE` | Categorías/marcas principales (para inyectar en prompt) | `Puntas Grishko, Bloch, Capezio...` | ❌ |
| `SHIPPING_PARTNERS` | Empresas de envío (comma-separated) | `Andreani, Correo Argentino` | ❌ |

**Multi-tenant (Dentalogic):** En este proyecto, el **número del bot** y el **nombre de la clínica** por sede son la fuente de verdad en la base de datos: `tenants.bot_phone_number` y `tenants.clinic_name`. Se configuran en **Sedes (Clinics)** en el panel. Las variables `BOT_PHONE_NUMBER` y `CLINIC_NAME` (y `CLINIC_LOCATION`) se usan solo como **respaldo** cuando no hay valor en BD o cuando la petición no trae `to_number` (ej. pruebas manuales). No es obligatorio definirlas si todas las sedes tienen ya sus datos cargados en la plataforma. `CLINIC_PHONE` no se utiliza en el orquestador y puede omitirse.
   
### 2.2 Integración Tienda Nube

| Variable | Descripción | Ejemplo | Requerida |
| :--- | :--- | :--- | :--- |
| `TIENDANUBE_STORE_ID` | ID numérico de la tienda en TN | `123456` | ✅ |
| `TIENDANUBE_ACCESS_TOKEN` | Token de API de Tienda Nube | `t_1234567890...` | ✅ |

### 2.3 Handoff / Derivación a Humanos

| Variable | Descripción | Ejemplo | Requerida |
| :--- | :--- | :--- | :--- |
| `HANDOFF_EMAIL` | Mail que recibe alertas de derivación | `soporte@tienda.com` | ✅ (si handoff activo) |
| `SMTP_HOST` | Host del servidor SMTP | `smtp.gmail.com` | ✅ (si handoff activo) |
| `SMTP_PORT` | Puerto del servidor SMTP | `465` | ✅ (si handoff activo) |
| `SMTP_USER` / `SMTP_USERNAME` | Usuario SMTP | `noreply@tienda.com` | ✅ (si handoff activo) |
| `SMTP_PASS` / `SMTP_PASSWORD` | Contraseña SMTP | (password de app) | ✅ (si handoff activo) |
| `SMTP_SECURITY` | Tipo de seguridad SMTP | `SSL` o `STARTTLS` | ✅ (si handoff activo) |

### 2.4 Seguridad y RBAC (Nexus v7.6)

| Variable | Descripción | Ejemplo | Requerida |
| :--- | :--- | :--- | :--- |
| **`ADMIN_TOKEN`** | Token maestro de protección (Infraestructura) | `admin-secret-token` | ✅ |
| **`JWT_SECRET_KEY`** | Clave secreta para firmar tokens JWT (64 bytes hex) | `python -c "import secrets; print(secrets.token_hex(64))"` | ✅ |
| **`JWT_ALGORITHM`** | Algoritmo de firma para JWT | `HS256` | `HS256` |
| **`ENVIRONMENT`** | Entorno de ejecución (`production` activa flag Secure en cookies) | `production` | `development` |
| **`CORS_ALLOWED_ORIGINS`** | Origins CORS permitidos (comma-separated). Requerido para cookies cross-domain. | `https://ui.clinic.com,http://localhost:3000` | `*` |
| **`CREDENTIALS_FERNET_KEY`** | Clave Fernet (AES-256) para encriptar/desencriptar la tabla `credentials` | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` | ✅ |
| **`GOOGLE_CREDENTIALS`** | JSON completo de credenciales de Google | (JSON string) | ❌ |

**Generar clave Fernet:** En la raíz del proyecto, con Python en el PATH: `py -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` (Windows). En Linux/macOS: `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. Guardar la salida en `CREDENTIALS_FERNET_KEY`.

## 3. WhatsApp Service (8002)

| Variable | Descripción | Ejemplo | Requerida |
| :--- | :--- | :--- | :--- |
| `YCLOUD_API_KEY` | API Key de YCloud | `api_key_xxxxx` | ✅ |
| `YCLOUD_WEBHOOK_SECRET` | Secreto para validar webhooks de YCloud | `webhook_secret_xxxxx` | ✅ |
| `ORCHESTRATOR_SERVICE_URL` | URL del Orchestrator (interna) | `http://orchestrator_service:8000` | ✅ |
| `INTERNAL_API_TOKEN` | Token para comunicarse con Orchestrator | (mismo que global) | ✅ |

## 4. Platform UI (80)

| Variable | Descripción | Ejemplo | Requerida |
| :--- | :--- | :--- | :--- |
| `ORCHESTRATOR_URL` | URL del Orchestrator (para admin panel) | (auto-detecta) | ❌ |
| `VITE_ADMIN_TOKEN` | Token de administrador (inyectado en build) | `admin-secret-token` | ✅ |
| `VITE_API_BASE_URL` | URL base para la API del orquestador | (auto-detecta) | ❌ |

## 5. Ejemplo de .env (Desarrollo Local)

```bash
# --- Globales ---
INTERNAL_API_TOKEN=super-secret-dev-token
OPENAI_API_KEY=sk-proj-xxxxx
REDIS_URL=redis://redis:6379
POSTGRES_DSN=postgres://postgres:password@localhost:5432/nexus_db

# --- Auth & Platform ---
JWT_SECRET_KEY=mi-llave-maestra-dental
PLATFORM_URL=https://dentalogic-frontend.ugwrjq.easypanel.host
ACCESS_TOKEN_EXPIRE_MINUTES=43200
ADMIN_TOKEN=admin-dev-token
# Opcional: para POST /admin/calendar/connect-sovereign (token Auth0 cifrado)
# CREDENTIALS_FERNET_KEY=<generar con: py -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">

# --- Orchestrator ---
STORE_NAME=Dentalogic
BOT_PHONE_NUMBER=+5493756123456
CORS_ALLOWED_ORIGINS=http://localhost:3000

# --- WhatsApp ---
YCLOUD_API_KEY=yc_api_xxxxx
YCLOUD_WEBHOOK_SECRET=yc_webhook_xxxxx
ORCHESTRATOR_SERVICE_URL=http://orchestrator_service:8000

# --- Frontend (Build Time) ---
VITE_ADMIN_TOKEN=admin-dev-token
VITE_API_URL=http://localhost:8000
```

---

*Guía de Variables © 2026*
泛
