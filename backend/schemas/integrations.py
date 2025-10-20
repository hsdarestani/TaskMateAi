from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import AnyHttpUrl, BaseModel, Field


class IntegrationSettingsPayload(BaseModel):
    base_url: AnyHttpUrl | None = None
    api_token: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class IntegrationSettingsRead(IntegrationSettingsPayload):
    provider: Literal["eigan", "clickup"]
    scope: Literal["system", "organization"]
    organization_id: int | None = None
    updated_at: datetime

    class Config:
        from_attributes = True
