---
name: "Platform AI Fusion"
description: "Vault, RAG, agentes polimórficos e integraciones opcionales (Meta, Tienda Nube, Chatwoot) para CRM VENTAS."
trigger: "vault, rag, agents, roi, magic, onboarding, credentials"
scope: "AI"
---

# Platform AI Fusion – CRM VENTAS

Capacidades de plataforma IA integradas en **CRM VENTAS**: Vault, RAG, agentes configurables, integraciones opcionales.

---

## The Vault (credenciales por tenant)

- Credenciales cifradas (AES-256/Fernet) en BD por tenant.
- Categorías: openai, google, meta, tiendanube, whatsapp_cloud, chatwoot, etc.
- Nunca usar env global para lógica de agentes; siempre `get_tenant_credential(tenant_id, category)`.
- UI: máscara tipo `Nexus_Key_*****`; gestión en Settings/Credentials.

---

## RAG (opcional)

- Shadow RAG: aprendizaje pasivo desde conversaciones.
- Ingestión: PDF, DOCX, TXT; metadata en PostgreSQL, embeddings en pgvector/Supabase.
- Colecciones por tenant; búsqueda semántica aislada.

---

## Agentes

- Factory polimórfica (Sales, Support, etc.); agente por nicho (crm_sales) con tools y prompt por nicho.
- Temperatura, herramientas habilitadas por agente, modelos (OpenAI, Google, etc.) desde configuración por tenant.

---

## Integraciones opcionales (fase 2)

- **Meta:** OAuth, WhatsApp Cloud API, Instagram/Facebook Messenger.
- **Tienda Nube:** OAuth, catálogo, pedidos.
- **Chatwoot:** Inbox humano, handoff con contexto.
- **Magic Onboarding:** Wizard de configuración inicial (SSE, múltiples agentes).

Implementar solo cuando esté en el alcance; documentar en docs del proyecto.

Todo el código en **CRM VENTAS**.
