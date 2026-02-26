    setLoading(true);
    
    // Para cada lead, cambiar estado individualmente
    const results = [];
    for (const leadId of selectedLeadIds) {
      try {
        await api.post(`/admin/core/crm/leads/${leadId}/status`, {
          status: selectedStatus,
          comment: comment || undefined
        });
        results.push({ leadId, success: true });
      } catch (error) {
        results.push({ leadId, success: false, error: error.message });
      }
    }
    
    const successful = results.filter(r => r.success).length;
    const failed = results.filter(r => !r.success).length;
    
    showToast(
      t('leads.bulk_update_result', { successful, failed, total: selectedLeadIds.length }),
      failed === 0 ? 'success' : 'warning'
    );
    
    if (onComplete) onComplete();
  } catch (error) {
    console.error('Error in bulk update:', error);
    showToast(t('alerts.bulk_update_error'), 'error');
  } finally {
    setLoading(false);
  }
};
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-md animate-in fade-in zoom-in">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 text-blue-600 rounded-xl">
              <Users size={20} />
            </div>
            <div>
              <h3 className="font-bold text-gray-900">
                {t('leads.bulk_update_title')}
              </h3>
              <p className="text-sm text-gray-500 mt-1">
                {t('leads.bulk_update_subtitle', { count: selectedLeadIds.length })}
              </p>
            </div>
          </div>
        </div>
        
        <div className="p-6 space-y-4">
          {/* Selector de estado */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {t('leads.select_new_status')}
            </label>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-xl 
                       focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              disabled={loading}
            >
              <option value="">{t('leads.select_status_placeholder')}</option>
              {availableStatuses.map((status) => (
                <option key={status.code} value={status.code}>
                  {status.name}
                </option>
              ))}
            </select>
          </div>
          
          {/* Comentario opcional */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {t('leads.comment_optional')}
              <span className="text-gray-400 text-xs ml-1">
                ({t('leads.comment_applied_to_all')})
              </span>
            </label>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-xl 
                       focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              rows={3}
              placeholder={t('leads.comment_placeholder')}
              disabled={loading}
            />
          </div>
          
          {/* Advertencia */}
          <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-yellow-800">
                <p className="font-medium">{t('leads.bulk_update_warning_title')}</p>
                <p className="mt-1">{t('leads.bulk_update_warning_message')}</p>
              </div>
            </div>
          </div>
        </div>
        
        <div className="p-6 border-t border-gray-200 flex justify-end gap-3">
          <button
            onClick={onCancel}
            disabled={loading}
            className="px-5 py-2.5 text-gray-700 font-medium rounded-lg 
                     hover:bg-gray-100 transition disabled:opacity-50"
          >
            {t('common.cancel')}
          </button>
          <button
            onClick={handleBulkUpdate}
            disabled={!selectedStatus || loading}
            className="px-5 py-2.5 bg-blue-600 text-white font-medium rounded-lg 
                     hover:bg-blue-700 transition disabled:opacity-50 
                     disabled:cursor-not-allowed flex items-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                {t('common.processing')}...
              </>
            ) : (
              <>
                <Check className="w-4 h-4" />
                {t('leads.update_statuses', { count: selectedLeadIds.length })}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default BulkStatusUpdate;
```

### **FASE 4: AUTOMATIZACIÓN Y POLISH (2 días)**

#### **Día 10: Sistema de Triggers (Opcional - se puede implementar después)**
```python
# orchestrator_service/services/lead_automation_service.py
import asyncio
import json
from typing import Dict, List
from uuid import UUID
import asyncpg
from datetime import datetime

class LeadAutomationService:
    """Servicio para ejecución de triggers automáticos"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
    
    async def execute_triggers_for_transition(self, tenant_id: int, lead_id: UUID,
                                              from_status: str, to_status: str) -> List[Dict]:
        """Ejecuta triggers para una transición de estado"""
        
        async with self.db_pool.acquire() as conn:
            # 1. Obtener triggers activos para esta transición
            triggers = await conn.fetch("""
                SELECT id, action_type, action_config, delay_minutes
                FROM lead_status_triggers
                WHERE tenant_id = $1 
                AND (from_status_code = $2 OR from_status_code IS NULL)
                AND to_status_code = $3
                AND is_active = true
                ORDER BY delay_minutes ASC
            """, tenant_id, from_status, to_status)
            
            if not triggers:
                return []
            
            # 2. Obtener información del lead
            lead = await conn.fetchrow("""
                SELECT l.*, u.email as assigned_email,
                       u.first_name as assigned_first_name,
                       u.last_name as assigned_last_name
                FROM leads l
                LEFT JOIN users u ON l.assigned_to = u.id
                WHERE l.id = $1 AND l.tenant_id = $2
            """, lead_id, tenant_id)
            
            if not lead:
                return []
            
            lead_data = dict(lead)
            
            # 3. Ejecutar cada trigger
            results = []
            for trigger in triggers:
                try:
                    result = await self._execute_trigger(
                        trigger=dict(trigger),
                        lead_data=lead_data,
                        from_status=from_status,
                        to_status=to_status
                    )
                    results.append({
                        'trigger_id': trigger['id'],
                        'action_type': trigger['action_type'],
                        'status': 'success',
                        'result': result
                    })
                    
                    # Registrar en logs
                    await conn.execute("""
                        INSERT INTO lead_status_trigger_logs
                        (trigger_id, tenant_id, lead_id, from_status_code,
                         to_status_code, execution_status, result_data)
                        VALUES ($1, $2, $3, $4, $5, 'success', $6)
                    """, trigger['id'], tenant_id, lead_id, 
                       from_status, to_status, json.dumps(result))
                    
                except Exception as e:
                    results.append({
                        'trigger_id': trigger['id'],
                        'action_type': trigger['action_type'],
                        'status': 'failed',
                        'error': str(e)
                    })
                    
                    # Registrar error en logs
                    await conn.execute("""
                        INSERT INTO lead_status_trigger_logs
                        (trigger_id, tenant_id, lead_id, from_status_code,
                         to_status_code, execution_status, error_message)
                        VALUES ($1, $2, $3, $4, $5, 'failed', $6)
                    """, trigger['id'], tenant_id, lead_id,
                       from_status, to_status, str(e))
            
            return results
    
    async def _execute_trigger(self, trigger: Dict, lead_data: Dict,
                               from_status: str, to_status: str) -> Dict:
        """Ejecuta un trigger específico"""
        
        action_type = trigger['action_type']
        config = trigger['action_config']
        
        if action_type == 'email':
            return await self._send_email_trigger(config, lead_data, from_status, to_status)
        elif action_type == 'whatsapp':
            return await self._send_whatsapp_trigger(config, lead_data, from_status, to_status)
        elif action_type == 'task':
            return await self._create_task_trigger(config, lead_data, from_status, to_status)
        elif action_type == 'notification':
            return await self._send_notification_trigger(config, lead_data, from_status, to_status)
        elif action_type == 'webhook':
            return await self._call_webhook_trigger(config, lead_data, from_status, to_status)
        else:
            raise ValueError(f"Unknown action type: {action_type}")
    
    async def _send_email_trigger(self, config: Dict, lead_data: Dict,
                                  from_status: str, to_status: str) -> Dict:
        """Envía email automático"""
        # Implementar usando sistema de email existente
        # Mantener compatibilidad con templates actuales
        pass
    
    async def _send_whatsapp_trigger(self, config: Dict, lead_data: Dict,
                                     from_status: str, to_status: str) -> Dict:
        """Envía mensaje WhatsApp automático"""
        # Integrar con WhatsApp Service existente
        # Usar templates HSM aprobados
        pass
    
    async def _create_task_trigger(self, config: Dict, lead_data: Dict,
                                   from_status: str, to_status: str) -> Dict:
        """Crea tarea automática"""
        # Integrar con sistema de tareas existente
        pass
```

#### **Día 11: Testing y Documentación**
```bash
# 1. Testing de migración
python3 test_migration_safety.py

# 2. Testing de endpoints nuevos
python3 test_lead_status_endpoints.py

# 3. Testing de compatibilidad con prospección
python3 test_prospecting_compatibility.py

# 4. Testing de UI
npm run test:lead-status-components

# 5. Crear documentación de usuario
mkdir -p docs/user/lead-status-system
```

---

## 🚨 **PROTOCOLO DE MIGRACIÓN SEGURA**

### **Paso 1: Backup Completo**
```bash
# Backup de base de datos
pg_dump -h localhost -U postgres crmventas > backup_pre_status_migration.sql

# Backup de código
git checkout -b feature/lead-status-system
git add .
git commit -m "Backup antes de implementar sistema de estados"
```

### **Paso 2: Migración en Entorno de Desarrollo**
```bash
# 1. Aplicar migración
psql -h localhost -U postgres -d crmventas_dev -f migrations/patch_018_lead_status_system.sql

# 2. Ejecutar script de migración de datos
python3 scripts/migrate_existing_statuses.py

# 3. Verificar que todo funciona
python3 scripts/verify_migration_success.py
```

### **Paso 3: Testing Exhaustivo**
```bash
# 1. Probar prospección Apify
python3 test_apify_integration.py

# 2. Probar página de leads existente
python3 test_existing_leads_page.py

# 3. Probar nuevos endpoints
python3 test_new_status_endpoints.py

# 4. Probar UI mejorada
npm run test:integration-lead-status
```

### **Paso 4: Rollback Plan (por si algo falla)**
```sql
-- Script de rollback
BEGIN;

-- 1. Eliminar foreign key constraint
ALTER TABLE leads DROP CONSTRAINT IF EXISTS fk_leads_status;

-- 2. Eliminar columnas agregadas
ALTER TABLE leads DROP COLUMN IF EXISTS status_changed_at;
ALTER TABLE leads DROP COLUMN IF EXISTS status_changed_by;
ALTER TABLE leads DROP COLUMN IF EXISTS status_metadata;

-- 3. Eliminar tablas nuevas
DROP TABLE IF EXISTS lead_status_trigger_logs;
DROP TABLE IF EXISTS lead_status_triggers;
DROP TABLE IF EXISTS lead_status_history;
DROP TABLE IF EXISTS lead_status_transitions;
DROP TABLE IF EXISTS lead_statuses;

COMMIT;
```

---

## 📊 **VERIFICACIÓN DE COMPATIBILIDAD**

### **Funcionalidades que DEBEN seguir funcionando:**
1. ✅ **Prospección Apify** - Creación de leads con status 'new'
2. ✅ **Página de leads** - Listado, filtrado, edición básica
3. ✅ **API existente** - PUT /leads/{id} para actualizar status
4. ✅ **Multi-tenant** - Aislamiento de datos por tenant_id
5. ✅ **Sistema de auditoría** - Logging automático de cambios

### **Nuevas funcionalidades (opcionales):**
1. 🔧 **UI mejorada** - Badges coloreados, selector inteligente
2. 🔧 **Histórico visual** - Timeline de cambios de estado
3. 🔧 **Bulk actions** - Cambio masivo de estados
4. 🔧 **Automatización** - Triggers para acciones automáticas
5. 🔧 **Workflow configurable** - Estados y transiciones personalizables

---

## 🎯 **CHECKLIST DE IMPLEMENTACIÓN SEGURA**

### **Antes de comenzar:**
- [ ] **Backup completo** de base de datos
- [ ] **Comunicación** al equipo sobre cambios
- [ ] **Plan de rollback** documentado
- [ ] **Testing environment** configurado

### **Durante implementación:**
- [ ] **Migración incremental** - Paso a paso
- [ ] **Testing después de cada paso**
- [ ] **Verificación de compatibilidad**
- [ ] **Documentación de cambios**

### **Después de implementar:**
- [ ] **Monitoring** de errores y performance
- [ ] **Feedback** de usuarios
- [ ] **Ajustes** basados en uso real
- [ ] **Training** para equipo de ventas

---

## 🔗 **INTEGRACIÓN CON SISTEMA ACTUAL**

### **Endpoints existentes que NO se modifican:**
```
GET    /admin/core/crm/leads           # Sigue funcionando igual
POST   /admin/core/crm/leads           # Sigue funcionando igual  
PUT    /admin/core/crm/leads/{id}      # Compatible con nuevo sistema
DELETE /admin/core/crm/leads/{id}      # Sigue funcionando igual
```

### **Nuevos endpoints (agregados, no reemplazan):**
```
GET    /admin/core/crm/lead-statuses           # Lista estados disponibles
GET    /admin/core/crm/leads/{id}/available-transitions  # Transiciones posibles
POST   /admin/core/crm/leads/{id}/status       # Cambiar estado con validación
GET    /admin/core/crm/leads/{id}/status-history  # Histórico de cambios
```

### **Compatibilidad garantizada:**
- **Código existente** que usa `leads.status` sigue funcionando
- **Prospección Apify** sigue creando leads con status 'new'
- **UI actual** muestra status como texto (igual que antes)
- **Filtros existentes** por status siguen funcionando

---

## 📈 **PLAN DE ROLLOUT GRADUAL**

### **Fase A: Solo Backend (Semana 1)**
- Migración de base de datos
- Servicios y endpoints nuevos
- **UI existente sin cambios**

### **Fase B: UI Mejorada Opcional (Semana 2)**
- Componentes nuevos disponibles
- **Toggle para activar/desactivar** en UI
- Feedback de usuarios tempranos

### **Fase C: UI Mejorada por Defecto (Semana 3)**
- UI mejorada activada por defecto
- **Fallback a UI simple** si hay problemas
- Training para equipo de ventas

### **Fase D: Automatización (Semana 4)**
- Sistema de triggers
- Configuración por UI
- Monitoring y ajustes

---

## ✅ **CONCLUSIÓN**

Esta guía proporciona un plan **completo y seguro** para implementar un sistema avanzado de estados para leads **sin romper** las funcionalidades existentes de prospección y página de leads.

### **Beneficios clave:**
1. **✅ Compatibilidad total** con sistema existente
2. **✅ Migración gradual** sin downtime
3. **✅ UI mejorada opcional** (no obligatoria)
4. **✅ Sistema de estados configurable** por tenant
5. **✅ Histórico completo** de cambios
6. **✅ Automatización** con triggers
7. **✅ Bulk actions** para cambio masivo

### **Riesgos mitigados:**
1