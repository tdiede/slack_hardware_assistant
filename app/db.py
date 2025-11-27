import os
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

from app.models import Base

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_NAME = os.getenv('POSTGRES_DB', 'postgres')
DB_USER = os.getenv('POSTGRES_USER', 'postgres')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'mypassword')

DATABASE_URL = os.getenv("DATABASE_URL", f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}")

engine = create_async_engine(DATABASE_URL, echo=True)

AsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession
)

async def init_db():
    print("Initializing database...")

    # IMPORTANT: import models so they are registered with Base.metadata
    # from app import models  # uncomment when you have models

    async with engine.connect() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.commit()

async def close_db_connections():
    # Dispose the engine and close all connections
    await engine.dispose()

async def get_db():
    session: AsyncSession = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()
