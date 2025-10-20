from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Iterable, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import (
    ActivitySnapshot,
    AnalyticsEvent,
    AnalyticsSource,
    Payment,
    Project,
    Task,
    User,
    OrganizationUser,
)
from backend.schemas.analytics import AnalyticsSummary

from .base import ServiceBase


ANALYTICS_QUEUE_KEY = "analytics:events"


class AnalyticsTaxonomy:
    """Utility helpers for enforcing analytics event taxonomy."""

    DEFAULT_EVENT_TYPE = "unknown"

    EVENT_TYPES: set[str] = {
        "page_view",
        "cta_click",
        "start_bot",
        "set_language",
        "create_task",
        "complete_task",
        "create_project",
        "reminder_sent",
        "reminder_clicked",
        "payment_start",
        "payment_success",
        "payment_failed",
        "trial_start",
        "trial_expire",
        "subscription_active",
        "subscription_expired",
        "voice_to_text",
        "image_to_task",
        "report_generated_daily",
        "report_generated_weekly",
        "org_invite_sent",
        "org_member_joined",
        DEFAULT_EVENT_TYPE,
    }

    EVENT_ALIASES: dict[str, str] = {
        "report_daily": "report_generated_daily",
        "report_weekly": "report_generated_weekly",
        "reminder_triggered": "reminder_sent",
        "reminder_clicked_button": "reminder_clicked",
    }

    SOURCES: set[str] = {member.value for member in AnalyticsSource}

    @classmethod
    def normalize_event(cls, payload: dict) -> dict:
        normalized: dict[str, Any] = dict(payload)
        normalized["event_type"] = cls._normalize_event_type(
            normalized.get("event_type")
        )
        normalized["source"] = cls._normalize_source(normalized.get("source"))
        normalized["metadata"] = cls._normalize_metadata(normalized.get("metadata"))
        normalized["user_id"] = cls._normalize_int(normalized.get("user_id"))
        normalized["organization_id"] = cls._normalize_int(
            normalized.get("organization_id")
        )
        return normalized

    @classmethod
    def _normalize_event_type(cls, value: Any) -> str:
        if isinstance(value, str):
            slug = value.strip().lower().replace(" ", "_").replace("-", "_")
        else:
            slug = ""
        slug = cls.EVENT_ALIASES.get(slug, slug)
        if slug not in cls.EVENT_TYPES:
            return cls.DEFAULT_EVENT_TYPE
        return slug

    @classmethod
    def _normalize_source(cls, value: Any) -> AnalyticsSource:
        if isinstance(value, AnalyticsSource):
            return value
        if isinstance(value, str):
            candidate = value.strip().lower()
            if candidate in cls.SOURCES:
                return AnalyticsSource(candidate)
        return AnalyticsSource.BOT

    @staticmethod
    def _normalize_metadata(value: Any) -> Optional[dict]:
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    return parsed
                return {"value": parsed}
            except json.JSONDecodeError:
                return {"value": value}
        return {"value": value}

    @staticmethod
    def _normalize_int(value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None


class AnalyticsService(ServiceBase):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_summary(self, organization_id: int | None = None) -> AnalyticsSummary:
        if organization_id is not None:
            result = await self.session.execute(
                select(func.count())
                .select_from(OrganizationUser)
                .where(OrganizationUser.organization_id == organization_id)
            )
            total_users = int(result.scalar_one())
            project_filters = [Project.organization_id == organization_id]
            task_filters = [Task.organization_id == organization_id]
        else:
            total_users = await self._count(User)
            project_filters: list[Any] = []
            task_filters: list[Any] = []

        active_projects = await self._count(Project, *project_filters)
        completed_tasks = await self._count(
            Task, Task.status == "completed", *task_filters
        )
        overdue_tasks = await self._count(
            Task, Task.status == "overdue", *task_filters
        )
        return AnalyticsSummary(
            total_users=total_users,
            active_projects=active_projects,
            completed_tasks=completed_tasks,
            overdue_tasks=overdue_tasks,
        )

    async def _count(self, model, *filters) -> int:
        query = select(func.count()).select_from(model)
        if filters:
            query = query.where(*filters)
        result = await self.session.execute(query)
        return int(result.scalar_one())

    async def record_events(self, events: Iterable[dict]) -> int:
        saved = 0
        now = datetime.now(timezone.utc)
        for payload in events:
            normalized = AnalyticsTaxonomy.normalize_event(payload)
            source = normalized.get("source", AnalyticsSource.BOT)
            created_at_raw = payload.get("created_at")
            created_at = self._parse_datetime(created_at_raw) if created_at_raw else now
            event = AnalyticsEvent(
                user_id=normalized.get("user_id"),
                organization_id=normalized.get("organization_id"),
                source=source,
                event_type=normalized.get("event_type", AnalyticsTaxonomy.DEFAULT_EVENT_TYPE),
                data=normalized.get("metadata"),
                created_at=created_at,
            )
            self.session.add(event)
            saved += 1
        if saved:
            await self.session.commit()
        return saved

    async def track_events(self, events: Iterable[dict]) -> int:
        return await self.record_events(events)

    async def create_daily_snapshot(self, *, target_date: Optional[date] = None) -> ActivitySnapshot:
        target = target_date or datetime.now(timezone.utc).date()
        start = datetime.combine(target, time.min, tzinfo=timezone.utc)
        end = start + timedelta(days=1)

        users_active = await self._distinct_count(
            AnalyticsEvent.user_id,
            AnalyticsEvent.created_at >= start,
            AnalyticsEvent.created_at < end,
            AnalyticsEvent.user_id.is_not(None),
        )
        orgs_active = await self._distinct_count(
            AnalyticsEvent.organization_id,
            AnalyticsEvent.created_at >= start,
            AnalyticsEvent.created_at < end,
            AnalyticsEvent.organization_id.is_not(None),
        )
        payments_count = await self._count(
            Payment,
            Payment.created_at >= start,
            Payment.created_at < end,
        )
        revenue_result = await self.session.execute(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.created_at >= start,
                Payment.created_at < end,
            )
        )
        revenue = revenue_result.scalar_one()
        tasks_created = await self._count(
            Task,
            Task.created_at >= start,
            Task.created_at < end,
        )

        result = await self.session.execute(
            select(ActivitySnapshot).where(ActivitySnapshot.date == target)
        )
        snapshot = result.scalar_one_or_none()
        if snapshot is None:
            snapshot = ActivitySnapshot(
                date=target,
                users_active=users_active,
                orgs_active=orgs_active,
                payments_count=payments_count,
                revenue=revenue,
                tasks_created=tasks_created,
            )
            self.session.add(snapshot)
        else:
            snapshot.users_active = users_active
            snapshot.orgs_active = orgs_active
            snapshot.payments_count = payments_count
            snapshot.revenue = revenue
            snapshot.tasks_created = tasks_created
        await self.session.commit()
        await self.session.refresh(snapshot)
        return snapshot

    async def _distinct_count(self, column, *filters) -> int:
        query = select(func.count(func.distinct(column))).where(*filters)
        result = await self.session.execute(query)
        return int(result.scalar_one())

    def _parse_datetime(self, value: object) -> datetime:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value)
                if parsed.tzinfo is None:
                    return parsed.replace(tzinfo=timezone.utc)
                return parsed
            except ValueError:
                return datetime.now(timezone.utc)
        return datetime.now(timezone.utc)
