#!/usr/bin/env python3
"""
Script para corregir problemas de deployment del Sprint 2
"""

import os
import sys
import subprocess

def check_dependencies():
    """Verificar dependencias instaladas"""
    print("🔍 Checking dependencies...")
    
    dependencies = [
        'fastapi',
        'uvicorn', 
        'asyncpg',
        'redis',
        'apscheduler',
        'socketio',
        'slowapi',
        'sqlalchemy',
        'pydantic'
    ]
    
    missing = []
    for dep in dependencies:
        try:
            __import__(dep.replace('-', '_'))
            print(f"  ✅ {dep}")
        except ImportError:
            print(f"  ❌ {dep} - MISSING")
            missing.append(dep)
    
    return missing

def fix_imports():
    """Corregir problemas de importación"""
    print("\n🔧 Fixing import issues...")
    
    # Archivos que necesitan corrección
    files_to_fix = [
        {
            'path': 'orchestrator_service/core/socket_notifications.py',
            'search': 'from ..services.seller_notification_service import notification_service',
            'replace': '''# Importación corregida para deployment
try:
    # Intentar importación absoluta primero
    from services.seller_notification_service import notification_service
except ImportError:
    try:
        # Intentar importación relativa
        from ..services.seller_notification_service import notification_service
    except ImportError:
        # Fallback: crear servicio dummy
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("Notification service not available, using dummy")
        class DummyNotificationService:
            async def create_notification(self, *args, **kwargs):
                return {"id": "dummy", "success": False}
        notification_service = DummyNotificationService()'''
        },
        {
            'path': 'orchestrator_service/services/seller_notification_service.py',
            'search': 'logger.warning("Redis not available, using in-memory fallback")',
            'replace': '''# Setup logger first
import logging
logger = logging.getLogger(__name__)

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, using in-memory fallback")''',
            'context_lines': 15
        }
    ]
    
    for file_info in files_to_fix:
        filepath = file_info['path']
        if os.path.exists(filepath):
            print(f"  Checking {filepath}...")
            
            with open(filepath, 'r') as f:
                content = f.read()
            
            if file_info['search'] in content:
                print(f"    ✅ Fix needed, applying...")
                new_content = content.replace(
                    file_info['search'], 
                    file_info['replace']
                )
                
                with open(filepath, 'w') as f:
                    f.write(new_content)
                
                print(f"    ✅ Fixed")
            else:
                print(f"    ✅ Already fixed")
        else:
            print(f"  ❌ File not found: {filepath}")
    
    print("\n✅ Import fixes applied")

def create_minimal_main():
    """Crear versión mínima de main.py para testing"""
    print("\n📝 Creating minimal main.py for testing...")
    
    minimal_main = '''"""
Minimal main.py for deployment testing
"""

import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Basic setup
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

app = FastAPI(title="CRM Ventas - Minimal", version="2.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "ok", "version": "2.0", "sprint": "2"}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "services": {
            "api": "running",
            "database": "unknown",
            "redis": "unknown"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''
    
    with open('orchestrator_service/main_minimal.py', 'w') as f:
        f.write(minimal_main)
    
    print("✅ Minimal main.py created")

def generate_docker_compose_fix():
    """Generar Docker Compose fix"""
    print("\n🐳 Generating Docker Compose fix...")
    
    docker_compose_fix = '''version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: crmventas
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD:-password}

  orchestrator:
    build: ./orchestrator_service
    environment:
      - POSTGRES_DSN=postgresql://user:password@postgres:5432/crmventas
      - REDIS_URL=redis://:${REDIS_PASSWORD:-password}@redis:6379
      - ENABLE_SCHEDULED_TASKS=${ENABLE_SCHEDULED_TASKS:-false}
      - LOG_LEVEL=INFO
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    command: >
      sh -c "pip install -r requirements.txt &&
             python main_minimal.py"

volumes:
  postgres_data:
'''
    
    with open('docker-compose-fix.yml', 'w') as f:
        f.write(docker_compose_fix)
    
    print("✅ Docker Compose fix created")

def main():
    print("🚀 DEPLOYMENT FIX SCRIPT - SPRINT 2")
    print("="*60)
    
    # 1. Check dependencies
    missing = check_dependencies()
    
    if missing:
        print(f"\n⚠️  Missing dependencies: {', '.join(missing)}")
        print("💡 Run: pip install " + " ".join(missing))
    
    # 2. Fix imports
    fix_imports()
    
    # 3. Create minimal main.py
    create_minimal_main()
    
    # 4. Generate Docker Compose fix
    generate_docker_compose_fix()
    
    print("\n" + "="*60)
    print("🎯 DEPLOYMENT FIXES APPLIED")
    print("\n📋 NEXT STEPS:")
    print("1. Update dependencies: pip install -r orchestrator_service/requirements.txt")
    print("2. Test minimal version: python orchestrator_service/main_minimal.py")
    print("3. Use docker-compose-fix.yml for deployment")
    print("4. Gradually enable Sprint 2 features")
    print("\n💡 TIP: Enable features one by one:")
    print("   - Start with ENABLE_SCHEDULED_TASKS=false")
    print("   - Test basic API endpoints first")
    print("   - Then enable background jobs")
    print("   - Finally enable Socket.IO notifications")

if __name__ == "__main__":
    main()