import logging
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request, Depends
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import init_db, close_db_connections, get_db
from app.vector_db import init_weaviate
from app.slack import handler, client
from app import crud
from app.schemas import UserCreate, UserRead


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    await init_db()
    init_weaviate()
    
    yield  # Application runs here

    print("Closing database connections...")
    await close_db_connections()   # Shutdown

app = FastAPI(lifespan=lifespan)


@app.get("/")
async def read_root():
    return {"message": "Hello, FastAPI with PostgreSQL!"}


@app.get("/health")
async def health_check():
    try:
        async with get_db() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except OperationalError as e:
        logging.error(f"Database connection failed: {e}")
        raise HTTPException(status_code=500, detail="Server error")
    except Exception as e:
        logging.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Server error")


@app.post("/slack/events")
async def slack_events(request: Request):
    print(f"Received Slack event: {request}")
    return await handler.handle(request)

# CRUD ENDPOINTS ###

@app.post("/user", response_model=UserRead)
async def create_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    user = await crud.create_user(db, user_in.name, user_in.title)
    return user

@app.get("/users", response_model=list[UserRead])
async def list_users(
    db: AsyncSession = Depends(get_db),
):
    users = await crud.get_users(db)
    return users

@app.get("/users/{user_id}", response_model=UserRead)
async def read_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    user = await crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
