from __future__ import annotations

from pydantic import BaseModel


class TeamCreate(BaseModel):
    organization_id: int
    name: str


class TeamUpdate(BaseModel):
    name: str | None = None


class TeamRead(BaseModel):
    id: int
    organization_id: int
    name: str

    class Config:
        from_attributes = True
