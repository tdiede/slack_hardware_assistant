from pydantic import BaseModel
from uuid import UUID

class UserBase(BaseModel):
    name: str
    title: str | None = None

class UserCreate(UserBase):
    pass

class UserRead(UserBase):
    id: UUID

    class Config:
        from_attributes = True
