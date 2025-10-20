from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.logging import logger
from backend.models import ActivityLog

from .base import ServiceBase


class NotificationService(ServiceBase):
    throttle_minutes: int = 5

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def broadcast(self, *, title: str, message: str, created_by: int | None) -> ActivityLog:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=self.throttle_minutes)
        result = await self.session.execute(
            select(ActivityLog)
            .where(
                ActivityLog.action == "broadcast",
                ActivityLog.created_at >= cutoff,
            )
            .order_by(ActivityLog.created_at.desc())
            .limit(1)
        )
        last = result.scalar_one_or_none()
        if last is not None:
            raise ValueError("broadcast_throttled")

        entry = ActivityLog(
            action="broadcast",
            details={"title": title, "message": message, "created_by": created_by},
            created_at=now,
        )
        self.session.add(entry)
        await self.session.commit()
        await self.session.refresh(entry)
        logger.info("notification.broadcast", title=title)
        return entry
