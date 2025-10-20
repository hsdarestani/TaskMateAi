from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    organization_id: int
    name: str
    description: str | None = None
    team_id: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    team_id: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: str | None = None


class ProjectRead(BaseModel):
    id: int
    organization_id: int
    name: str
    description: str | None = None
    team_id: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: str | None = None

    class Config:
        from_attributes = True
