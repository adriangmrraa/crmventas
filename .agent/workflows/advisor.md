---
description: Consultor Estrategico de CRM Ventas. Valida ideas de features contra Impacto de Negocio, Viabilidad Tecnica y Valor para el Usuario antes de escribir codigo.
---

# Asesor de Negocio - CRM Ventas (Nexus Core)

Workflow para evaluar y validar ideas de crecimiento, automatizacion o nuevas funcionalidades en el CRM de ventas.

## 1. Recepcion de la Idea

Antes de cualquier analisis, documentar:
- **Origen**: Quien propone la idea (CEO, setter, closer, secretaria, profesional).
- **Problema actual**: Que dolor resuelve en el flujo de ventas.
- **Resultado esperado**: Que metrica mejora (conversion, tiempo de respuesta, revenue).

## 2. Evaluacion con los 3 Pilares

### Pilar 1: Impacto de Negocio
| Pregunta | Respuesta |
|----------|-----------|
| Aumenta la tasa de conversion de leads? | Si/No - Justificar |
| Reduce el tiempo del ciclo de venta? | Si/No - Justificar |
| Mejora la retencion de clientes? | Si/No - Justificar |
| Impacta directamente en el revenue? | Si/No - Justificar |
| Mejora las metricas del seller (seller_metrics)? | Si/No - Justificar |

**Puntuacion**: 0-5 (0 = sin impacto, 5 = critico para el negocio)

### Pilar 2: Viabilidad Tecnica
| Pregunta | Respuesta |
|----------|-----------|
| Es compatible con el stack actual (FastAPI + React + PostgreSQL)? | Si/No |
| Requiere nuevas dependencias o servicios externos? | Si/No - Cuales |
| Se puede implementar sin romper el aislamiento multi-tenant (tenant_id)? | Si/No |
| Afecta la autenticacion existente (JWT + X-Admin-Token)? | Si/No |
| Requiere cambios en la base de datos (migraciones)? | Si/No - Cuales tablas |
| Se integra con los servicios existentes (orchestrator:8000, whatsapp:8002, frontend:5173)? | Si/No |
| Requiere nuevas integraciones (Meta Ads, Google Ads, otros)? | Si/No |

**Puntuacion**: 0-5 (0 = imposible con stack actual, 5 = trivial de implementar)

### Pilar 3: Valor para el Usuario
| Pregunta | Respuesta |
|----------|-----------|
| Beneficia al CEO (visibilidad, reportes, control)? | Si/No - Como |
| Beneficia al setter (captacion, asignacion de leads)? | Si/No - Como |
| Beneficia al closer (pipeline, seguimiento, cierre)? | Si/No - Como |
| Beneficia a la secretaria (agenda, coordinacion)? | Si/No - Como |
| Beneficia al profesional (carga de trabajo, calendario)? | Si/No - Como |
| Es intuitivo via la interfaz actual (Tailwind + Glassmorphism)? | Si/No |
| Reduce la friccion en el flujo WhatsApp -> CRM? | Si/No |

**Puntuacion**: 0-5 (0 = sin valor, 5 = transformador)

## 3. Framework de Decision

### Matriz de Priorizacion

| Puntuacion Total | Decision |
|-----------------|----------|
| 12-15 | **PRIORIDAD ALTA**: Ejecutar `/plan` inmediatamente |
| 8-11 | **PRIORIDAD MEDIA**: Planificar para el proximo sprint. Ejecutar `/specify` para documentar |
| 4-7 | **PRIORIDAD BAJA**: Agregar al backlog. Requiere mas analisis |
| 0-3 | **RECHAZAR**: No cumple con los pilares minimos. Documentar razon |

### Criterios de Bloqueo (Veto Automatico)
La idea se rechaza automaticamente si:
- Rompe el aislamiento multi-tenant (tenant_id).
- Requiere acceso SQL directo en produccion.
- No es compatible con el modelo de roles (ceo, setter, closer, secretary, professional).
- Compromete la seguridad de autenticacion (JWT/X-Admin-Token).

## 4. Salida del Workflow

### Si la idea es viable:
1. Generar un resumen ejecutivo con las puntuaciones.
2. Identificar las tablas afectadas: `leads`, `sellers`, `clients`, `opportunities`, `sales_transactions`, `seller_agenda_events`, `chat_messages`, `notifications`, `seller_metrics`, `assignment_rules`.
3. Listar los archivos que se modificarian: `main.py`, `admin_routes.py`, `db.py`, `routes.py`, `models.py`, `tools_provider.py`.
4. Ejecutar `/plan` para generar el plan de implementacion.

### Si la idea no es viable:
1. Documentar las razones del rechazo.
2. Sugerir alternativas que si cumplan los 3 pilares.
3. Proponer una version reducida (MVP) si el concepto tiene potencial.
