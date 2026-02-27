import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Force asyncpg driver
POSTGRES_DSN = os.getenv("POSTGRES_DSN").replace("postgresql://", "postgresql+asyncpg://")

async def verify_schema():
    engine = create_async_engine(POSTGRES_DSN)
    async with engine.connect() as conn:
        print("Checking tables...")
        tables = ["leads", "whatsapp_connections", "templates", "campaigns", "sellers"]
        for table in tables:
            result = await conn.execute(text(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')"))
            exists = result.scalar()
            print(f"Table '{table}': {'✅ EXISTS' if exists else '❌ MISSING'}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(verify_schema())
