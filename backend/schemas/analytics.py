from __future__ import annotations

from datetime import datetime
from typing import Iterable

from pydantic import BaseModel, Field, field_validator


class AnalyticsSummary(BaseModel):
    total_users: int
    active_projects: int
    completed_tasks: int
    overdue_tasks: int


class AnalyticsEventPayload(BaseModel):
    event_type: str = Field(..., min_length=1)
    source: str | None = None
    metadata: dict | None = None
    user_id: int | None = None
    organization_id: int | None = None
    created_at: datetime | None = None

    @field_validator("event_type")
    @classmethod
    def _strip_event_type(cls, value: str) -> str:
        return value.strip()

    @field_validator("source")
    @classmethod
    def _normalize_source(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().lower()


class AnalyticsTrackRequest(BaseModel):
    events: Iterable[AnalyticsEventPayload]
