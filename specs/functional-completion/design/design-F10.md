# DESIGN F-10: HSM Automation CRUD

## Decisiones Arquitectónicas
- MetaTemplatesView muestra logs de automatización pero NO tiene CRUD de reglas
- Backend tiene: GET /crm/marketing/automation/rules y POST /crm/marketing/automation/rules
- Faltan: PUT y DELETE endpoints para reglas — necesitan crearse en backend
- Frontend necesita: tabla de reglas + modal crear/editar + botón eliminar

## Backend Nuevo
- `PUT /crm/marketing/automation/rules/{rule_id}` — actualizar regla
- `DELETE /crm/marketing/automation/rules/{rule_id}` — eliminar regla
- Agregar en routes/marketing.py

## Componentes React
- MetaTemplatesView.tsx — agregar tab "Reglas" con tabla
- AutomationRuleModal — modal crear/editar regla (trigger, conditions, actions, active toggle)
- Cada regla: name, trigger_type, conditions JSONB, is_active, created_at

## API Contract
```typescript
interface AutomationRule {
  id: string;
  name: string;
  trigger_type: string; // 'new_lead' | 'status_changed' | 'follow_up_due'
  conditions: Record<string, any>;
  actions: Record<string, any>;
  is_active: boolean;
  created_at: string;
}
```

## Stats Fix (de spec)
- Card "Conversion": calcular real = delivered/total * 100 desde logs
- Card "Motor": verificar si hay logs en últimas 24h
- Eliminar timezone selector disabled
