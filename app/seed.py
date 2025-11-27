import asyncio

from app.db import AsyncSessionLocal, engine
from app.models import Base, User

async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        session.add_all([
            User(name="Test User 1", title="Engineer"),
            User(name="Test User 2", title="PCB Designer"),
        ])
        await session.commit()

if __name__ == "__main__":
    asyncio.run(seed())
