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

| Skill Name | Trigger | Descripción |
| :--- | :--- | :--- |
| **[AI Behavior Architect](file:///E:/Antigravity Projects/estabilizacion/CRM VENTAS/.agent/skills/Prompt_Architect/SKILL.md)** | `Cuando edite system prompts, plantillas de agentes o lógica de RAG.` | Ingeniería de prompts para los Agentes de Ventas, Soporte y Business Forge. |
| **[Agent Configuration Architect](file:///E:/Antigravity Projects/estabilizacion/CRM VENTAS/.agent/skills/Agent_Configuration_Architect/SKILL.md)** | `agents, agentes, AI, tools, templates, models, prompts, system prompt, wizard` | Especialista en configuración de agentes de IA: templates, tools, models, prompts y seed data. |
| **[Business Forge Engineer](file:///E:/Antigravity Projects/estabilizacion/CRM VENTAS/.agent/skills/Business_Forge_Engineer/SKILL.md)** | `forge, business forge, assets, fusion, canvas, catalog, visuals, images` | Especialista en Business Forge: gestión de assets post-magia, Fusion Engine y generación de visuales. |
| **[CRM Sales Module](file:///E:/Antigravity Projects/estabilizacion/CRM VENTAS/.agent/skills/CRM_Sales_Module/SKILL.md)** | `leads, pipeline, deals, sellers, agenda, calendar, crm_sales` | Módulo CRM: leads, pipeline, vendedores, agenda híbrida y tools de reserva para CRM VENTAS. |
| **[Credential Vault Specialist](file:///E:/Antigravity Projects/estabilizacion/CRM VENTAS/.agent/skills/Credential_Vault_Specialist/SKILL.md)** | `credentials, credenciales, vault, api keys, tokens, encriptación, settings, sovereign` | Especialista en gestión segura de credenciales multi-tenant: encriptación, scope, categorías y The Vault. |
| **[DB Schema Surgeon](file:///E:/Antigravity Projects/estabilizacion/CRM VENTAS/.agent/skills/DB_Evolution/SKILL.md)** | `v8.0, sql, idempotent, schema, migration, database` | v8.0: Database & Persistence Master. Gestión de evolución segura, parches idempotentes y JSONB clínico. |
| **[Deep Researcher](file:///E:/Antigravity Projects/estabilizacion/CRM VENTAS/.agent/skills/Deep_Research/SKILL.md)** | `Antes de usar una librería nueva, al enfrentar un error desconocido, o cuando el usuario diga 'investiga esto'.` | Investiga documentación oficial y valida soluciones en internet antes de implementar. |
| **[EasyPanel DevOps](file:///E:/Antigravity Projects/estabilizacion/CRM VENTAS/.agent/skills/DevOps_EasyPanel/SKILL.md)** | `Cuando toque Dockerfile, docker-compose.yml o variables de entorno.` | Experto en Dockerización, Docker Compose y despliegue en EasyPanel. |
| **[Fusion Architect](file:///E:/Antigravity Projects/estabilizacion/CRM VENTAS/.agent/skills/Fusion_Architect/SKILL.md)** | `fusión, estable, migrar, decidir, CRM vs Platform, qué conservar` | Decidir de qué proyecto tomar cada pieza al integrar con CRM VENTAS (fusiones o migraciones). |
| **[Magic Onboarding Orchestrator](file:///E:/Antigravity Projects/estabilizacion/CRM VENTAS/.agent/skills/Magic_Onboarding_Orchestrator/SKILL.md)** | `magia, magic, onboarding, hacer magia, wizard, sse, stream, assets, branding` | Especialista en el proceso 'Hacer Magia': orquestación de agentes IA, SSE streaming y generación de assets de negocio. |
| **[Maintenance Robot Architect](file:///E:/Antigravity Projects/estabilizacion/CRM VENTAS/.agent/skills/Maintenance_Robot_Architect/SKILL.md)** | `N/A` | Especialista en la actualización del sistema de auto-migración "Maintenance Robot" en orchestrator_service/db.py. |
| **[Meta Integration Diplomat](file:///E:/Antigravity Projects/estabilizacion/CRM VENTAS/.agent/skills/Meta_Integration_Diplomat/SKILL.md)** | `meta, facebook, instagram, whatsapp, oauth, integration, waba, pages` | Especialista en OAuth Meta (Facebook, Instagram, WhatsApp Business) y gestión de activos de negocio. |
| **[Mobile_Adaptation_Architect](file:///E:/Antigravity Projects/estabilizacion/CRM VENTAS/.agent/skills/Mobile_Adaptation_Architect/SKILL.md)** | `v8.0, mobile, responsive, isolation, DKG, adaptive` | v8.0: Senior UI/UX Architect. Especialista en Blueprint Universal, DKG y Scroll Isolation. |
| **[Nexus QA Engineer](file:///E:/Antigravity Projects/estabilizacion/CRM VENTAS/.agent/skills/Testing_Quality/SKILL.md)** | `Cuando pida crear tests, probar una feature o corregir bugs.` | Especialista en Pytest Asyncio y Vitest para arquitecturas aisladas. |
| **[Nexus UI Architect](file:///E:/Antigravity Projects/estabilizacion/CRM VENTAS/.agent/skills/Nexus_UI_Architect/SKILL.md)** | `N/A` | Especialista en Diseño Responsivo (Mobile First / Desktop Adaptive) y UX para Dentalogic. Define el estándar visual y estructural. |
| **[Nexus UI Developer](file:///E:/Antigravity Projects/estabilizacion/CRM VENTAS/.agent/skills/Frontend_Nexus/SKILL.md)** | `frontend, react, tsx, componentes, UI, vistas, hooks` | Especialista en React 18, TypeScript, Tailwind CSS y conexión con API multi-tenant. |
| **[Omnichannel Chat Operator](file:///E:/Antigravity Projects/estabilizacion/CRM VENTAS/.agent/skills/Omnichannel_Chat_Operator/SKILL.md)** | `chats, conversaciones, mensajes, whatsapp, human override, handoff` | Especialista en gestión de conversaciones vía WhatsApp (YCloud) para Dentalogic. |
| **[Platform AI Fusion](file:///E:/Antigravity Projects/estabilizacion/CRM VENTAS/.agent/skills/Platform_AI_Fusion/SKILL.md)** | `vault, rag, agents, roi, magic, onboarding, credentials` | Vault, RAG, agentes polimórficos e integraciones opcionales (Meta, Tienda Nube, Chatwoot) para CRM VENTAS. |
| **[Skill Synchronizer](file:///E:/Antigravity Projects/estabilizacion/CRM VENTAS/.agent/skills/Skill_Sync/SKILL.md)** | `Después de crear o modificar una skill, o cuando el usuario diga 'sincronizar skills'.` | Lee los metadatos de todas las skills y actualiza el índice en AGENTS.md. |
| **[Skill_Forge_Master](file:///E:/Antigravity Projects/estabilizacion/CRM VENTAS/.agent/skills/Skill_Forge_Master/SKILL.md)** | `crear skill, nueva habilidad, skill architect, forge skill, capability, nueva skill` | Arquitecto y generador de Skills. Define, estructura y registra nuevas capacidades para el agente Antigravity. |
| **[Smart Doc Keeper](file:///E:/Antigravity Projects/estabilizacion/CRM VENTAS/.agent/skills/Doc_Keeper/SKILL.md)** | `Cuando el usuario diga 'actualiza la doc', 'documenta este cambio' o tras editar código importante.` | Actualiza documentación y skills usando el protocolo 'Non-Destructive Fusion'. Garantiza que el contenido previo se preserve. |
| **[Sovereign Backend Engineer](file:///E:/Antigravity Projects/estabilizacion/CRM VENTAS/.agent/skills/Backend_Sovereign/SKILL.md)** | `v8.0, backend, JIT, tenancy, idempotencia, tools` | v8.0: Senior Backend Architect & Python Expert. Lógica JIT v2, multi-tenancy y evolución idempotente. |
| **[Sovereign Code Auditor](file:///E:/Antigravity Projects/estabilizacion/CRM VENTAS/.agent/skills/Sovereign_Auditor/SKILL.md)** | `Antes de hacer commit, o cuando pida revisar seguridad o aislamiento.` | Experto en ciberseguridad y cumplimiento del Protocolo de Soberanía Nexus. |
| **[Spec Architect](file:///E:/Antigravity Projects/estabilizacion/CRM VENTAS/.agent/skills/Spec_Architect/SKILL.md)** | `Cuando el usuario diga 'crea una especificación', 'planifica esta feature' o use el comando '/specify'.` | Genera y valida archivos de especificación (.spec.md) siguiendo el estándar SDD v2.0. |
| **[Template Transplant Specialist](file:///E:/Antigravity Projects/estabilizacion/CRM VENTAS/.agent/skills/Template_Transplant_Specialist/SKILL.md)** | `N/A` | Extrae y distribuye instrucciones de un system prompt legacy en las capas correctas (Wizard, Tool Config, Sistema Interno). |
| **[TiendaNube Commerce Bridge](file:///E:/Antigravity Projects/estabilizacion/CRM VENTAS/.agent/skills/TiendaNube_Commerce_Bridge/SKILL.md)** | `tiendanube, tienda nube, e-commerce, products, orders, oauth, catalog, store` | Especialista en integración con Tienda Nube: OAuth, sincronización de catálogo, órdenes y gestión de productos. |

---
