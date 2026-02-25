# 📋 SPRINT 1 - DÍA 3: DATABASE MIGRATIONS & BACKEND TESTING

## ✅ DÍAS 1-2 COMPLETADOS

### **Día 1: Service Migration** ✅
- Servicios copiados y adaptados de ClinicForge
- Adaptación terminológica completa
- Estructura de directorios creada

### **Día 2: Endpoints & Routes** ✅
- 16 endpoints implementados (marketing + OAuth)
- Rutas integradas en main.py
- Testing suite creada
- Verificación 94.4% completada

## 🎯 DÍA 3: OBJETIVOS

### **1. Database Migrations Execution**
- [ ] Configurar conexión PostgreSQL
- [ ] Ejecutar migraciones SQL
- [ ] Verificar creación de tablas
- [ ] Crear datos de prueba

### **2. Backend Testing**
- [ ] Configurar entorno de testing
- [ ] Ejecutar tests unitarios
- [ ] Probar endpoints con base de datos real
- [ ] Verificar cálculos de ROI

### **3. Integration Testing**
- [ ] Probar integración con seguridad Nexus v7.7.1
- [ ] Verificar rate limiting
- [ ] Probar auditoría de acceso
- [ ] Validar multi-tenant isolation

## 🔧 PASOS PARA EJECUTAR MIGRACIONES

### **Opción A: Con PostgreSQL local**
```bash
# 1. Configurar variable de entorno
export POSTGRES_DSN="postgresql://postgres:password@localhost:5432/crmventas"

# 2. Ejecutar migraciones
cd orchestrator_service
python run_meta_ads_migrations.py

# 3. Verificar
python run_meta_ads_migrations.py --verify
```

### **Opción B: Con Docker (recomendado)**
```bash
# 1. Iniciar servicios
cd /home/node/.openclaw/workspace/projects/crmventas
docker-compose up -d postgres

# 2. Configurar DSN
export POSTGRES_DSN="postgresql://postgres:password@localhost:5432/crmventas"

# 3. Ejecutar migraciones
cd orchestrator_service
python run_meta_ads_migrations.py
```

### **Opción C: Testing sin base de datos real**
```bash
# Usar SQLite para testing rápido
export POSTGRES_DSN="sqlite:///test.db"
# Nota: Requiere adaptaciones en el script de migración
```

## 🧪 PASOS PARA BACKEND TESTING

### **1. Instalar dependencias de testing**
```bash
cd orchestrator_service

# Instalar requirements mínimos
pip install pytest pytest-asyncio httpx

# O instalar todos los requirements
pip install -r requirements.txt
```

### **2. Ejecutar tests unitarios**
```bash
# Ejecutar todos los tests
python -m pytest tests/ -v

# Ejecutar tests específicos
python -m pytest tests/test_marketing_backend.py -v

# Ejecutar con cobertura
python -m pytest tests/ --cov=services.marketing --cov-report=html
```

### **3. Probar endpoints manualmente**
```bash
# Iniciar servidor de desarrollo
uvicorn main:app --reload --port 8000

# Probar endpoints con curl
curl -X GET "http://localhost:8000/crm/marketing/stats" \
  -H "Authorization: Bearer test" \
  -H "X-Admin-Token: test"

# Probar con Postman/Insomnia
# Colección disponible en: docs/postman_collection.json
```

## 📊 TABLAS A VERIFICAR

Después de ejecutar migraciones, verificar:

```sql
-- 1. Tablas principales
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN (
    'meta_ads_campaigns',
    'meta_ads_insights',
    'meta_templates',
    'automation_rules',
    'automation_logs',
    'opportunities',
    'sales_transactions'
);

-- 2. Columnas en leads
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'leads' 
AND column_name IN (
    'lead_source',
    'meta_campaign_id',
    'meta_ad_id',
    'meta_ad_headline',
    'meta_ad_body',
    'external_ids'
);

-- 3. Función ROI
SELECT proname, prosrc 
FROM pg_proc 
WHERE proname = 'calculate_campaign_roi';
```

## 🚨 CASOS DE TEST CRÍTICOS

### **1. Multi-tenant Isolation**
```python
# Verificar que todas las queries incluyen tenant_id
# Ejemplo en marketing_service.py:
"SELECT COUNT(*) FROM leads WHERE tenant_id = $1 AND lead_source = 'META_ADS'"
```

### **2. Rate Limiting**
- Endpoints sensibles: 10-100 requests/minuto
- OAuth endpoints: 5-20 requests/minuto
- Verificar headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`

### **3. Audit Logging**
- Todos los endpoints deben tener `@audit_access`
- Verificar tabla `system_events` después de cada request
- Incluir user_id, tenant_id, action, timestamp

### **4. Error Handling**
- HTTP 401: Token inválido
- HTTP 403: Permisos insuficientes
- HTTP 429: Rate limit excedido
- HTTP 500: Error interno (con logging)

## 📈 MÉTRICAS DE CALIDAD

### **Cobertura de código objetivo:**
- ✅ Unit tests: 80%+ cobertura
- ✅ Integration tests: 100% endpoints
- ✅ Error handling: 100% casos
- ✅ Security: 100% verificaciones

### **Performance objetivos:**
- ⏱️ Response time: < 500ms (P95)
- 🗄️ Database queries: < 10 por request
- 📊 Memory usage: < 100MB por instancia
- 🔄 Concurrent users: 50+ simultáneos

## 🔄 ROLLBACK PLAN

Si las migraciones fallan:

```bash
# 1. Verificar estado actual
python run_meta_ads_migrations.py --verify

# 2. Ejecutar rollback
python run_meta_ads_migrations.py --rollback

# 3. Verificar rollback
python run_meta_ads_migrations.py --verify
```

## 📞 SOPORTE Y TROUBLESHOOTING

### **Problemas comunes:**

1. **Conexión a PostgreSQL falla**
   - Verificar `POSTGRES_DSN`
   - Verificar que PostgreSQL esté corriendo
   - Verificar credenciales

2. **Migraciones SQL con errores**
   - Verificar sintaxis SQL
   - Verificar permisos de usuario
   - Verificar que no haya tablas duplicadas

3. **Tests fallan**
   - Verificar imports
   - Verificar mocking
   - Verificar configuración de testing

### **Recursos:**
- `docs/`: Documentación técnica
- `tests/`: Suite de testing
- `migrations/`: Scripts SQL
- `SPRINT1_DAY1_SUMMARY.md`: Resumen Día 1

## 🎯 CRITERIOS DE COMPLETITUD

El **Día 3 se considera completado** cuando:

1. ✅ Migraciones ejecutadas exitosamente
2. ✅ 80%+ de tests unitarios pasan
3. ✅ Endpoints responden con status codes correctos
4. ✅ Multi-tenant isolation verificada
5. ✅ Audit logging funcionando
6. ✅ Rate limiting implementado

## 📅 PRÓXIMOS PASOS

### **Después de completar Día 3:**
1. **Documentar** resultados de testing
2. **Crear** datos de prueba realistas
3. **Optimizar** queries lentas
4. **Preparar** para Sprint 2 (Frontend)

### **Sprint 2 (Frontend) - Vista previa:**
- Día 4: Migración de componentes React
- Día 5: Integración en Sidebar y routing
- Día 6: Testing y optimización frontend

---

**Estado actual:** ✅ Días 1-2 completados | ⏳ Día 3 en progreso  
**Próxima acción:** Ejecutar migraciones de base de datos