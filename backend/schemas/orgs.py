from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class OrganizationBase(BaseModel):
    name: str
    plan: str | None = None


class OrganizationCreate(OrganizationBase):
    owner_user_id: int | None = None


class OrganizationRead(OrganizationBase):
    id: int
    owner_user_id: int | None = None

    class Config:
        from_attributes = True


class OrganizationInviteRequest(BaseModel):
    organization_id: int
    role: Literal["member", "team_manager", "org_admin"] = "member"


class OrganizationInviteResponse(BaseModel):
    organization_id: int
    role: Literal["member", "team_manager", "org_admin"]
    invite_code: str


class OrganizationJoinRequest(BaseModel):
    invite_code: str
