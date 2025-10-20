from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel


class ReportFormat(str, Enum):
    TEXT = "text"
    PDF = "pdf"
    CSV = "csv"


class ReportScope(str, Enum):
    USER = "user"
    ORGANIZATION = "organization"
    TEAM = "team"
    PROJECT = "project"


class ReportRequest(BaseModel):
    report_type: Literal["daily", "weekly", "monthly"]
    user_id: Optional[int] = None
    organization_id: Optional[int] = None
    team_id: Optional[int] = None
    project_id: Optional[int] = None
    date: Optional[date] = None
    timezone: Optional[str] = None
    locale: Optional[str] = None
    format: ReportFormat = ReportFormat.TEXT


class ReportCounts(BaseModel):
    total: int
    completed: int
    overdue: int


class ReportTask(BaseModel):
    id: int
    title: str
    status: str | None = None
    priority: str | None = None
    due_at: datetime | None = None


class TrendPoint(BaseModel):
    period: str
    overdue: int


class OrgMetrics(BaseModel):
    throughput: int
    completion_rate: float
    overdue_trend: List[TrendPoint]
    active_users: int


class ReportResponse(BaseModel):
    report_type: Literal["daily", "weekly", "monthly"]
    scope: ReportScope
    summary: str
    counts: ReportCounts | None = None
    next_tasks: List[ReportTask] = []
    overdue_tasks: List[ReportTask] = []
    metrics: OrgMetrics | None = None
    file_url: str | None = None
    format: ReportFormat = ReportFormat.TEXT
    generated_at: datetime
