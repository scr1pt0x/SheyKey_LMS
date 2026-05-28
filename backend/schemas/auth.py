from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    phone: str = Field(..., description="Phone number used as login")
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    id: str
    name: str
    role: str


class UserMeResponse(BaseModel):
    id: str
    name: str
    role: str
    phone: str | None
    is_active: bool


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
