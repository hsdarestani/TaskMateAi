from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    organization_id: int | None = None
    project_id: int | None = None
    type: str | None = None
    due_at: datetime | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    status: str | None = Field(default="pending")
    priority: str | None = None
    source: str | None = None
    origin_message_id: str | None = None
    assignee_id: int | None = None
    assigned_team_id: int | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    organization_id: int | None = None
    project_id: int | None = None
    type: str | None = None
    due_at: datetime | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    status: str | None = None
    priority: str | None = None
    source: str | None = None
    origin_message_id: str | None = None
    assignee_id: int | None = None
    assigned_team_id: int | None = None


class TaskRead(BaseModel):
    id: int
    title: str
    description: str | None = None
    status: str | None = None
    organization_id: int | None = None
    project_id: int | None = None
    type: str | None = None
    due_at: datetime | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    priority: str | None = None
    source: str | None = None
    origin_message_id: str | None = None
    user_id: int | None = None

    class Config:
        from_attributes = True
