---
name: "Fusion Architect"
description: "Decidir de qué proyecto tomar cada pieza al integrar con CRM VENTAS (fusiones o migraciones)."
trigger: "fusión, estable, migrar, decidir, CRM vs Platform, qué conservar"
scope: "PROCESS"
---

# Fusion Architect – CRM VENTAS

Guía decisiones de fusión o integración para que el resultado viva en **CRM VENTAS**. Cuando se integren piezas de Version Estable, Platform AI Solutions u otros proyectos, consultar documentación de fusión si existe (ej. FUSION_ANALYSIS en Version Estable).

---

## Cuándo usar esta skill

- Al añadir una funcionalidad y dudar si basarse en otro proyecto (Version Estable, Platform AI Solutions).
- Al migrar código: decidir qué archivos/carpetas copiar y cómo adaptarlos a CRM VENTAS.
- Al definir arquitectura (auth, credenciales, RAG, integraciones): qué patrón seguir.

---

## Reglas de decisión (resumen)

| Área | Origen preferente | Nota |
|------|-------------------|------|
| Auth / seguridad | Unificar | JWT + X-Admin-Token + Vault por tenant. |
| Multi-tenancy | Siempre | tenant_id en todas las queries. |
| Agenda / calendario | CRM VENTAS | Híbrido local/Google, Socket.IO, tools de reserva. |
| Leads / pipeline | CRM VENTAS | Módulo crm_sales, rutas, modelos. |
| Credenciales IA/calendar | Vault | Por tenant; no env global para agentes. |
| Chats / WhatsApp | YCloud + relay/buffer + human override 24h. |
| RAG, Meta, Tienda Nube, etc. | Opcional | Según prioridad del proyecto. |
| Frontend / i18n | React 18, Vite, Tailwind, es/en/fr, scroll isolation. |
| Docs y .agent | CRM VENTAS | Workflows y skills dentro de CRM VENTAS. |

---

## Protocolo

1. Si existe documentación de fusión (ej. FUSION_ANALYSIS en otro repo), consultarla para el área en cuestión.
2. Si hay conflicto entre dos implementaciones: elegir el que mejor cumpla soberanía (tenant_id, Vault), mantenibilidad y coherencia con el resto del diseño.
3. Documentar la decisión en el código o en docs si es relevante para futuras decisiones.
4. Asegurar que el código resultante se integre **solo** en CRM VENTAS.

---

*Todo el proyecto estable es parte de CRM VENTAS.*
