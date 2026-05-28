import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from backend.models.user import UserRole


class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    phone: str = Field(..., min_length=7, max_length=20)
    role: UserRole
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    phone: str | None = Field(None, min_length=7, max_length=20)
    is_active: bool | None = None


class UserResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    phone: str | None
    role: UserRole
    is_active: bool
    last_login: datetime | None
    created_at: datetime


class UserListResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    phone: str | None
    role: UserRole
    is_active: bool
    last_login: datetime | None
