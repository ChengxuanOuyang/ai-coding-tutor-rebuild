from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StrictInt,
    StringConstraints,
    field_validator,
)

from backend.app.domain.models import MessageRole

Username = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_.-]{3,32}$")]
Password = Annotated[str, StringConstraints(min_length=12, max_length=128)]
Level = Annotated[StrictInt, Field(ge=1, le=5)]


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class ValidationIssue(BaseModel):
    loc: list[str | int]
    msg: str
    type: str


class ValidationErrorResponse(ErrorResponse):
    details: list[ValidationIssue]


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    username: Username
    password: Password
    self_programming_level: Level
    self_maths_level: Level


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: Password


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    username: str
    self_programming_level: int
    self_maths_level: int
    created_at: datetime
    updated_at: datetime


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_at: datetime


class CreateSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if len(value.strip()) > 120:
            raise ValueError("String should have at most 120 characters")
        return value


class SessionResponse(BaseModel):
    id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    id: UUID
    session_id: UUID
    role: MessageRole
    content: str
    created_at: datetime
