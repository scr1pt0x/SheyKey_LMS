import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ClientCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    phone: str = Field(..., min_length=7, max_length=20)
    passport: str | None = Field(None, max_length=50)
    address: str | None = None
    notes: str | None = None
    tags: list[str] | None = None


class ClientUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=2, max_length=255)
    phone: str | None = Field(None, min_length=7, max_length=20)
    passport: str | None = Field(None, max_length=50)
    address: str | None = None
    notes: str | None = None
    tags: list[str] | None = None


class ClientResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    manager_id: uuid.UUID
    full_name: str
    phone: str
    passport: str | None
    address: str | None
    is_archived: bool
    notes: str | None
    tags: list | None
    manager_name: str | None = None
    created_at: datetime
    updated_at: datetime


class ClientListItem(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    full_name: str
    phone: str
    passport: str | None
    is_archived: bool
    manager_id: uuid.UUID
    created_at: datetime


class NoteAddRequest(BaseModel):
    note: str = Field(..., min_length=1)
