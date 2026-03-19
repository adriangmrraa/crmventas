# 🧪 SETUP PARA TESTING - SISTEMA DE VENDEDORES

## 🚀 **PASOS PARA CONFIGURAR EL ENTORNO DE TESTING**

### **1. INICIAR SERVICIOS BACKEND**

```bash
cd /home/node/.openclaw/workspace/projects/crmventas

# Opción A: Usar Docker Compose (recomendado)
docker-compose up -d postgres redis

# Opción B: Iniciar servicios manualmente
# Asegurarse que PostgreSQL y Redis estén corriendo
```

### **2. CONFIGURAR VARIABLES DE ENTORNO**

```bash
# Copiar archivo de ejemplo
cp .env.temp .env

# Verificar variables críticas
cat .env | grep -E "POSTGRES|REDIS|BACKEND_URL"
```

### **3. INICIAR BACKEND SERVER**

```bash
cd orchestrator_service

# Instalar dependencias (si no están instaladas)
pip install -r requirements.txt

# Iniciar servidor FastAPI
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### **4. INICIAR FRONTEND SERVER**

```bash
cd frontend_react

# Instalar dependencias
npm install

# Iniciar servidor de desarrollo
npm run dev
```

### **5. VERIFICAR QUE TODO FUNCIONE**

```bash
# Backend API
curl http://localhost:8000/docs

# Frontend
# Abrir http://localhost:5173 en el navegador
```

---

## 🧪 **ESCENARIOS DE TESTING A EJECUTAR**

### **TEST 1: MIGRACIÓN DE BASE DE DATOS**
```bash
# Ejecutar script de verificación
python3 verify_seller_tables.py

# Resultado esperado:
# ✅ seller_metrics: Tabla de métricas de vendedores - EXISTE
# ✅ assignment_rules: Tabla de reglas de asignación - EXISTE
# ✅ assigned_seller_id: AGREGADA en chat_messages
# ✅ Reglas creadas: 1+
```

### **TEST 2: API ENDPOINTS**
```bash
# Usar el script de testing
python3 test_seller_system.py

# O probar manualmente:
curl -X GET "http://localhost:8000/admin/core/sellers/available?tenant_id=1"
curl -X POST "http://localhost:8000/admin/core/sellers/conversations/assign" \
  -H "Content-Type: application/json" \
  -d '{"phone": "+5491100000000", "seller_id": "UUID", "source": "manual"}'
```

### **TEST 3: COMPONENTES REACT**
1. **Abrir** http://localhost:5173/chats
2. **Seleccionar** una conversación
3. **Verificar** que aparece el badge "AGENTE IA"
4. **Clickear** en "Asignar" → Debe abrir el modal SellerSelector
5. **Probar** "Asignarme a mí" y "Auto asignar"
6. **Verificar** que el badge se actualiza

### **TEST 4: PERMISOS POR ROL**
```bash
# Crear usuarios de prueba con diferentes roles:
# - CEO: Puede asignar a cualquier vendedor
# - Setter: Solo puede asignarse a sí mismo
# - Secretary: Solo puede ver, no asignar

# Probar con diferentes usuarios en el frontend
```

### **TEST 5: MÉTRICAS EN TIEMPO REAL**
1. **Enviar mensajes** en una conversación asignada
2. **Verificar** que las métricas se actualizan
3. **Abrir** dashboard de métricas
4. **Confirmar** que los números son correctos

---

## 🐛 **SOLUCIÓN DE PROBLEMAS COMUNES**

### **PROBLEMA: "No se ven los vendedores"**
```sql
-- Verificar que hay usuarios con roles correctos
SELECT id, first_name, last_name, role, status 
FROM users 
WHERE tenant_id = 1 
AND role IN ('setter', 'closer', 'professional', 'ceo')
AND status = 'active';
```

### **PROBLEMA: "Error de permisos"**
```python
# Verificar middleware de autenticación
# Asegurarse que el token JWT incluya el rol correcto
```

### **PROBLEMA: "Componentes no se renderizan"**
```bash
# Verificar errores en consola del navegador
# Verificar que TypeScript compile correctamente
npm run build
```

### **PROBLEMA: "Socket.IO no funciona"**
```javascript
// Verificar conexión en frontend
console.log(socketRef.current.connected);
// Verificar eventos en backend
logger.info("Emitting SELLER_ASSIGNMENT_UPDATED");
```

---

## 📊 **DATOS DE PRUEBA RECOMENDADOS**

### **USUARIOS DE PRUEBA:**
```sql
INSERT INTO users (tenant_id, first_name, last_name, email, role, status) VALUES
(1, 'Juan', 'Pérez', 'juan@empresa.com', 'setter', 'active'),
(1, 'María', 'Gómez', 'maria@empresa.com', 'closer', 'active'),
(1, 'Carlos', 'CEO', 'carlos@empresa.com', 'ceo', 'active'),
(1, 'Ana', 'Secretaria', 'ana@empresa.com', 'secretary', 'active');
```

### **CONVERSACIONES DE PRUEBA:**
```sql
INSERT INTO chat_messages (tenant_id, from_number, role, content) VALUES
(1, '+5491100000001', 'user', 'Hola, me interesa el servicio'),
(1, '+5491100000002', 'user', 'Quiero información de precios'),
(1, '+5491100000003', 'user', 'Necesito ayuda con mi cuenta');
```

### **LEADS DE PRUEBA:**
```sql
INSERT INTO leads (tenant_id, first_name, phone_number, lead_source) VALUES
(1, 'Cliente 1', '+5491100000001', 'META_ADS'),
(1, 'Cliente 2', '+5491100000002', 'WEBSITE'),
(1, 'Cliente 3', '+5491100000003', 'REFERRAL');
```

---

## 🎯 **CRITERIOS DE ACEPTACIÓN**

### **DEBE FUNCIONAR:**
- [ ] CEO puede ver todos los vendedores
- [ ] CEO puede asignar cualquier conversación a cualquier vendedor
- [ ] Vendedores pueden asignarse conversaciones a sí mismos
- [ ] Badge "AGENTE IA" aparece en conversaciones sin asignar
- [ ] Modal SellerSelector se abre correctamente
- [ ] Auto-asignación funciona según reglas
- [ ] Historial de asignaciones se muestra
- [ ] Métricas se calculan en tiempo real
- [ ] Socket.IO actualiza en tiempo real

### **NO DEBE:**
- [ ] Romper funcionalidad existente de chats
- [ ] Permitir que secretaries asignen conversaciones
- [ ] Mostrar vendedores de otros tenants
- [ ] Perder asignaciones al recargar la página
- [ ] Tener errores en consola del navegador

---

## 📈 **MÉTRICAS DE CALIDAD**

### **PERFORMANCE:**
- ✅ < 100ms para endpoints de asignación
- ✅ < 500ms para cálculo de métricas
- ✅ < 1s para carga inicial de componentes

### **USABILIDAD:**
- ✅ UI intuitiva y fácil de usar
- ✅ Feedback visual inmediato
- ✅ Mensajes de error claros
- ✅ Responsive design

### **CÓDIGO:**
- ✅ 0 errores TypeScript
- ✅ 0 warnings en build
- ✅ Cobertura de tests > 80%
- ✅ Documentación completa

---

## 🚨 **PROTOCOLO DE FALLBACK**

### **SI ALGO FALLA:**
1. **Revisar logs** del backend y frontend
2. **Verificar** conexión a base de datos
3. **Probar** endpoints API manualmente
4. **Reiniciar** servicios si es necesario
5. **Rollback** a versión anterior si hay problemas críticos

### **CONTACTOS:**
- **Backend issues**: Revisar `orchestrator_service/logs/`
- **Frontend issues**: Consola del navegador
- **Database issues**: `verify_seller_tables.py`
- **API issues**: `test_seller_system.py`

---

## 🎉 **CELEBRACIÓN DE ÉXITO**

### **CUANDO TODO FUNCIONE:**
1. **Documentar** los resultados del testing
2. **Crear** demo para el CEO
3. **Capacitar** a los vendedores
4. **Planificar** rollout a producción
5. **Celebrar** 🎊

### **ENTREGABLES FINALES:**
- ✅ Sistema funcionando en staging
- ✅ Documentación de testing completa
- ✅ Plan de rollout a producción
- ✅ Guía de usuario para vendedores
- ✅ Dashboard de métricas para CEO

---

**¡BUENA SUERTE CON EL TESTING!** 🚀

*Última actualización: 25 de Febrero 2026*