from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.logging import logger
from backend.models import Reminder, Task, User

from .base import ServiceBase


class ReminderService(ServiceBase):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def schedule(self, task_id: int, when: datetime) -> Reminder:
        existing = await self.session.execute(
            select(Reminder)
            .where(Reminder.task_id == task_id, Reminder.remind_at == when)
            .limit(1)
        )
        reminder = existing.scalar_one_or_none()
        if reminder is None:
            reminder = Reminder(task_id=task_id, remind_at=when, sent=False)
            self.session.add(reminder)
            await self.session.commit()
            await self.session.refresh(reminder)
        logger.info("reminder.schedule", task_id=task_id, remind_at=when.isoformat())
        return reminder

    async def cancel(self, reminder_id: int) -> None:
        await self.session.execute(delete(Reminder).where(Reminder.id == reminder_id))
        await self.session.commit()
        logger.info("reminder.cancel", reminder_id=reminder_id)

    async def mark_sent(self, reminder_id: int) -> None:
        reminder = await self.session.get(Reminder, reminder_id)
        if not reminder:
            return
        reminder.sent = True
        await self.session.commit()
        logger.info("reminder.sent", reminder_id=reminder_id)

    async def get_due_reminders(self, *, limit: int = 100) -> List[Reminder]:
        now = datetime.now(timezone.utc)
        result = await self.session.scalars(
            select(Reminder)
            .options(
                selectinload(Reminder.task).selectinload(Task.user),
            )
            .where(Reminder.sent.is_(False), Reminder.remind_at <= now)
            .order_by(Reminder.remind_at)
            .limit(limit)
        )
        reminders = list(result)
        logger.debug(
            "reminder.due_fetched",
            count=len(reminders),
            cutoff=now.isoformat(),
        )
        return reminders

    def compute_default_times(
        self, due_at: datetime | None, user: User | None = None
    ) -> List[datetime]:
        if due_at is None:
            return []

        if due_at.tzinfo is None:
            due_at = due_at.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        preferences = user.preferences if user else {}
        offsets = preferences.get("default_reminder_minutes", [30])
        if isinstance(offsets, (int, float)):
            offsets = [int(offsets)]

        reminders: List[datetime] = []
        for offset in offsets:
            try:
                delta = timedelta(minutes=int(offset))
            except (TypeError, ValueError):
                continue
            remind_at = due_at - delta
            if remind_at > now:
                reminders.append(remind_at)

        reminders.sort()
        return reminders

    async def schedule_default_reminders(
        self, task: Task, user: User | None = None
    ) -> List[Reminder]:
        reminders: List[Reminder] = []
        for remind_at in self.compute_default_times(task.due_at, user):
            reminders.append(await self.schedule(task.id, remind_at))
        return reminders
