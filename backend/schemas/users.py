from __future__ import annotations

from typing import List

from pydantic import BaseModel, EmailStr, Field, field_validator

from backend.core.rbac import Role


class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None
    roles: List[Role] = Field(default_factory=lambda: [Role.MEMBER])
    organization_id: int | None = None


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

    @field_validator("roles", mode="before")
    @classmethod
    def split_roles(cls, value):
        if isinstance(value, str):
            return [Role(role) for role in value.split(",") if role]
        return value
