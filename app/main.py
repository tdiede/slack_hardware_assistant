import logging
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request, Depends
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import init_db, close_db_connections, get_db
from app.slack import handler, client
from app import crud
from app.schemas import UserCreate, UserRead


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    await init_db()
    
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

# CRUD ENDPOINTS ###

@app.post("/user", response_model=UserRead)
async def create_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    user = await crud.create_user(db, user_in)
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

# SLACK INTEGRATION ENDPOINTS ###

@app.post("/slack/events")
async def slack_events(request: Request):
    print(f"Received Slack event: {request}")
    return await handler.handle(request)

@app.get("/slack/channels")
async def get_slack_channels():
    try:
        response = client.conversations_list()
        if response["ok"]:
            channels = response["channels"]
            return {"channels": channels}
        else:
            raise HTTPException(status_code=500, detail="Failed to fetch channels from Slack")
    except Exception as e:
        logging.error(f"Error fetching Slack channels: {e}")
        raise HTTPException(status_code=500, detail="Server error")

@app.get("/slack/messages/{channel_id}")
async def get_slack_messages(channel_id: str):
    try:
        response = client.conversations_history(channel=channel_id)
        if response["ok"]:
            messages = response["messages"]
            return {"messages": messages}
        else:
            raise HTTPException(status_code=500, detail="Failed to fetch messages from Slack")
    except Exception as e:
        logging.error(f"Error fetching Slack messages: {e}")
        raise HTTPException(status_code=500, detail="Server error")

@app.get("/slack/threads/{channel_id}/{message_ts}")
async def get_slack_messages(channel_id: str, message_ts: str):
    try:
        response = client.conversations_replies(channel=channel_id, ts=message_ts)
        if response["ok"]:
            messages = response["messages"]
            return {"messages": messages}
        else:
            raise HTTPException(status_code=500, detail="Failed to fetch messages from Slack")
    except Exception as e:
        logging.error(f"Error fetching Slack messages: {e}")
        raise HTTPException(status_code=500, detail="Server error")

@app.get("/slack/users")
async def get_slack_users():
    try:
        response = client.users_list()
        if response["ok"]:
            users = response["members"]
            return {"users": users}
        else:
            raise HTTPException(status_code=500, detail="Failed to fetch users from Slack")
    except Exception as e:
        logging.error(f"Error fetching Slack users: {e}")
        raise HTTPException(status_code=500, detail="Server error")

@app.get("/slack/users/{user_id}")
async def get_slack_user(user_id: str):
    try:
        response = client.users_info(user=user_id)
        if response["ok"]:
            user = response["user"]
            return {"user": user}
        else:
            raise HTTPException(status_code=500, detail="Failed to fetch user from Slack")
    except Exception as e:
        logging.error(f"Error fetching Slack user: {e}")
        raise HTTPException(status_code=500, detail="Server error")
