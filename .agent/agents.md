# CRM VENTAS: Knowledge & Skills Map

Este archivo actúa como el índice maestro de capacidades para los Agentes Autónomos. Define qué Skill utilizar para cada tipo de tarea. **Todo el trabajo se realiza dentro de CRM VENTAS.**

> **Comandos de workflows y skills:** Ver [COMMANDS.md](COMMANDS.md) para la lista completa de comandos (`/specify`, `/plan`, `/autonomy`, `/fusion_stable`, etc.) y triggers de skills. La IA debe usar ese documento en coordinación contigo cuando invoques un comando.

## 🌟 Core Skills (Infraestructura)
| Skill | Trigger Keywords | Uso Principal |
|-------|------------------|---------------|
| **[Backend_Sovereign](skills/Backend_Sovereign/SKILL.md)** | `backend`, `fastapi`, `db`, `auth` | Arquitectura, endpoints, seguridad y base de datos. |
| **[Frontend_Nexus](skills/Frontend_Nexus/SKILL.md)** | `frontend`, `react`, `ui`, `hooks` | Componentes React, llamadas API, estado y estilos. |
| **[DB_Evolution](skills/DB_Evolution/SKILL.md)** | `schema`, `migration`, `sql`, `rag` | Cambios en DB, gestión de vectores y migraciones. |

## 📊 Dominio CRM y fusión
| Skill | Trigger Keywords | Uso Principal |
|-------|------------------|---------------|
| **[CRM_Sales_Module](skills/CRM_Sales_Module/SKILL.md)** | `leads`, `pipeline`, `deals`, `sellers`, `agenda`, `calendar`, `crm_sales` | Módulo CRM: leads, pipeline, vendedores, agenda híbrida, tools de reserva. |
| **[Platform_AI_Fusion](skills/Platform_AI_Fusion/SKILL.md)** | `vault`, `rag`, `agents`, `roi`, `magic`, `onboarding`, `credentials` | Vault, RAG, agentes polimórficos, integraciones opcionales. |
| **[Fusion_Architect](skills/Fusion_Architect/SKILL.md)** | `fusión`, `estable`, `migrar`, `decidir`, `CRM vs Platform` | Decidir de qué proyecto tomar cada pieza; guiar integraciones. |

## 💬 Communication & Integrations
| Skill | Trigger Keywords | Uso Principal |
|-------|------------------|---------------|
| **[Omnichannel_Chat_Operator](skills/Omnichannel_Chat_Operator/SKILL.md)** | `chats`, `whatsapp`, `meta`, `msg` | Lógica de mensajería, polling y human handoff. |
| **[Meta_Integration_Diplomat](skills/Meta_Integration_Diplomat/SKILL.md)** | `oauth`, `facebook`, `instagram` | Vinculación de cuentas Meta y gestión de tokens. |
| **[TiendaNube_Commerce_Bridge](skills/TiendaNube_Commerce_Bridge/SKILL.md)** | `tiendanube`, `products`, `orders` | Sincronización de catálogo y OAuth de e-commerce. |

## 🤖 AI & Onboarding
| Skill | Trigger Keywords | Uso Principal |
|-------|------------------|---------------|
| **[Agent_Configuration_Architect](skills/Agent_Configuration_Architect/SKILL.md)** | `agents`, `prompts`, `tools` | Creación y configuración de agentes IA. |
| **[Magic_Onboarding_Orchestrator](skills/Magic_Onboarding_Orchestrator/SKILL.md)** | `magic`, `wizard`, `onboarding` | Proceso de "Hacer Magia" y generación de assets. |
| **[Business_Forge_Engineer](skills/Business_Forge_Engineer/SKILL.md)** | `forge`, `canvas`, `visuals` | Gestión de assets generados y Fusion Engine. |
| **[Skill_Forge_Master](skills/Skill_Forge_Master/SKILL.md)** | `crear skill`, `skill architect` | Generador y arquitecto de nuevas capacidades. |

## 🔒 Security
| Skill | Trigger Keywords | Uso Principal |
|-------|------------------|---------------|
| **[Credential_Vault_Specialist](skills/Credential_Vault_Specialist/SKILL.md)** | `credentials`, `vault`, `keys` | Gestión segura de secretos y encriptación. |

---

# 🏗 Sovereign Architecture Context

## 1. Project Identity
**CRM VENTAS** es un sistema SaaS de CRM de ventas (leads, pipeline, vendedores, agenda, chats) con orquestación de IA. **Un solo nicho:** solo CRM de ventas (no dental, no multi-nicho). Multi-tenancy por sedes/entidades.

Cada tenant posee sus propias credenciales de IA encriptadas en la base de datos y su propia integración con Google Calendar cuando aplique.

**Regla de Oro (Datos):** NUNCA usar `os.getenv("OPENAI_API_KEY")` para lógica de agentes en producción. Siempre usar la credencial correspondiente de la base de datos.

> [!IMPORTANT]
> **REGLA DE SOBERANÍA (BACKEND)**: Es obligatorio incluir el filtro `tenant_id` en todas las consultas (SELECT/INSERT/UPDATE/DELETE). El aislamiento de datos es la barrera legal y técnica inviolable del sistema.

> [!IMPORTANT]
> **REGLA DE SOBERANÍA (FRONTEND)**: Implementar siempre "Aislamiento de Scroll" (`h-screen`, `overflow-hidden` global y `overflow-y-auto` interno) para garantizar que los datos densos no rompan la experiencia de usuario ni se fuguen visualmente fuera de sus contenedores.

## 2. Tech Stack & Standards

### Backend
- **Python 3.10+**: Lenguaje principal
- **FastAPI**: Framework web asíncrono
- **PostgreSQL 14**: Base de datos relacional
- **SQLAlchemy 2.0 / asyncpg**: Acceso asíncrono a datos
- **Google Calendar API**: Sincronización de turnos
- **Redis**: Cache y buffers de mensajes

### Frontend
- **React 18**: Framework UI
- **TypeScript**: Tipado estricto obligatorio
- **Tailwind CSS**: Sistema de estilos
- **Lucide Icons**: Iconografía

### Infrastructure
- **Docker Compose**: Orquestación local
- **EasyPanel**: Deployment cloud
- **WhatsApp Business API (via YCloud)**: Canal de comunicación oficial

## 3. Architecture Map

### Core Services

#### `/orchestrator_service` - API Principal
- **Responsabilidad**: Gestión de leads, pipeline, agenda, integración con Google Calendar, herramientas de IA.
- **Archivos Críticos**:
  - `main.py`: FastAPI app y herramientas de la IA (CRM tools).
  - `admin_routes.py`: Gestión de usuarios, vendedores y configuración de despliegue.
  - `gcal_service.py`: Integración con Google Calendar (Service Account) cuando aplique.
  - `db.py`: Conector de base de datos asíncrono (Maintenance Robot).

#### `/whatsapp_service` - Canal WhatsApp (si aplica)
- **Responsabilidad**: Recepción de webhooks de YCloud, validación de firmas y forwarding al orquestador.
- **Características**: Buffer/Debounce de mensajes en Redis.

#### `/frontend_react` - Dashboard SPA
- **Responsabilidad**: Interfaz para CRM (Leads, Pipeline, Agenda, Chats, Config).
- **Vistas Críticas**: Leads, Lead detail, Pipeline, Sellers, Agenda (calendario con Socket.IO), Config.

## 4. Workflows Disponibles

| Workflow | Descripción |
|----------|-------------|
| [autonomy](workflows/autonomy.md) | Motor completo SDD: specify → clarify → plan → gate → implement → verify → update-docs (y opc. advisor, audit, review, push, finish). |
| [fusion_stable](workflows/fusion_stable.md) | Guía para construir/validar la versión estable del CRM. |
| [specify](workflows/specify.md) | Genera especificaciones técnicas .spec.md. |
| [clarify](workflows/clarify.md) | Clarificación de la spec; hasta 5 preguntas. |
| [plan](workflows/plan.md) | Transforma especificaciones en un plan técnico. |
| [gate](workflows/gate.md) | Umbral de confianza antes de implementar. |
| [implement](workflows/implement.md) | Ejecución del plan de implementación. |
| [verify](workflows/verify.md) | Ciclo de verificación y corrección. |
| [bug_fix](workflows/bug_fix.md) | Proceso para solucionar bugs con aislamiento multi-tenant. |
| [new_feature](workflows/new_feature.md) | Nueva funcionalidad (backend first, sovereign check). |
| [update-docs](workflows/update-docs.md) | Actualizar documentación con Non-Destructive Fusion. |
| [newproject](workflows/newproject.md) | Scaffolding del proyecto. |
| [advisor](workflows/advisor.md) | Consultor estratégico (3 pilares). |
| [tasks](workflows/tasks.md) | Desglose en tickets atómicos. |
| [audit](workflows/audit.md) | Comparar código vs .spec.md (drift). |
| [review](workflows/review.md) | Revisión multi-perspectiva. |
| [push](workflows/push.md) | Sincronizar con GitHub. |
| [finish](workflows/finish.md) | Cierre de hito. |
| [mobile-adapt](workflows/mobile-adapt.md) | Adaptar vista a mobile. |

## 5. Available Skills Index

Ver también la tabla de skills en [COMMANDS.md](COMMANDS.md). Todas las skills están en `.agent/skills/<NombreSkill>/SKILL.md`:

- **Backend_Sovereign**, **Frontend_Nexus**, **DB_Evolution** (Core)
- **CRM_Sales_Module**, **Platform_AI_Fusion**, **Fusion_Architect** (Dominio CRM y fusión)
- **Omnichannel_Chat_Operator**, **Meta_Integration_Diplomat**, **TiendaNube_Commerce_Bridge**
- **Agent_Configuration_Architect**, **Magic_Onboarding_Orchestrator**, **Business_Forge_Engineer**, **Skill_Forge_Master**, **Prompt_Architect**, **Spec_Architect**
- **Credential_Vault_Specialist**, **Sovereign_Auditor**, **Testing_Quality**
- **Doc_Keeper**, **Skill_Sync**, **Maintenance_Robot_Architect**
- **Nexus_UI_Architect**, **Mobile_Adaptation_Architect**
- **Deep_Research**, **DevOps_EasyPanel**, **Template_Transplant_Specialist**

---
