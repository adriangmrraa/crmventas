import asyncio
import os
import asyncpg
import json

POSTGRES_DSN = os.getenv("POSTGRES_DSN")

async def diagnose():
    print(f"--- DIAGNÓSTICO DE BASE DE DATOS ---")
    if not POSTGRES_DSN:
        print("❌ ERROR: POSTGRES_DSN no está definida.")
        return

    print(f"Conectando a: {POSTGRES_DSN.split('@')[-1]}") # Mostrar host/db sin pass
    
    try:
        conn = await asyncpg.connect(POSTGRES_DSN)
        print("✅ Conexión exitosa.")
        
        # 1. Listar tablas principales
        print("\n--- Tablas en el esquema 'public' ---")
        tables = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        for t in tables:
            print(f"- {t['table_name']}")
            
        # 2. Verificar tabla credentials
        print("\n--- Columnas en tabla 'credentials' ---")
        if any(t['table_name'] == 'credentials' for t in tables):
            cols = await conn.fetch("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'credentials'")
            for c in cols:
                print(f"- {c['column_name']} ({c['data_type']})")
        else:
            print("❌ La tabla 'credentials' NO EXISTE.")
            
        # 3. Verificar tabla meta_tokens (causante del bloqueo previo)
        print("\n--- Verificación meta_tokens ---")
        if any(t['table_name'] == 'meta_tokens' for t in tables):
            print("✅ La tabla 'meta_tokens' existe.")
        else:
            print("⚠️ La tabla 'meta_tokens' NO existe (esto causa fallos en parches antiguos si no están protegidos).")

        await conn.close()
    except Exception as e:
        print(f"❌ ERROR durante el diagnóstico: {e}")

if __name__ == "__main__":
    asyncio.run(diagnose())
