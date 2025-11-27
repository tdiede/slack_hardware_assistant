from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User

async def create_user(session: AsyncSession, name: str, title: str) -> User:
    user = User(name=name, title=title)
    session.add(user)
    await session.commit()
    await session.refresh(user)  # load auto-generated fields
    return user

async def get_user_by_id(session: AsyncSession, user_id: UUID) -> User | None:
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def get_users(session: AsyncSession) -> list[User]:
    stmt = select(User)
    result = await session.execute(stmt)
    return result.scalars().all()

