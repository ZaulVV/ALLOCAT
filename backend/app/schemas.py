from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: EmailStr
    role: str
    is_active: bool


class ResourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    category: str = Field(min_length=1, max_length=80)


class ResourceUpdate(ResourceCreate):
    status: str = Field(default="DISPONIBLE", max_length=30)
    version: int = Field(ge=1)


class ResourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    category: str
    status: str
    version: int


class ReservationCreate(BaseModel):
    resource_id: int
    start_date: datetime
    end_date: datetime


class ReservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    resource_id: int
    requester_id: int
    start_date: datetime
    end_date: datetime
    status: str
    approved_by: int | None


class ReservationDecision(BaseModel):
    status: str = Field(pattern="^(APROBADA|RECHAZADA)$")
