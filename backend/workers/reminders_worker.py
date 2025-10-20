from __future__ import annotations
import asyncio
from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError

from backend.adapters.telegram import TelegramAdapter
from backend.core.i18n import format_datetime, normalize_locale, prepare_telegram, translate
from backend.core.logging import logger
from backend.core.settings import settings
from backend.services.base import SessionLocal
from backend.services.reminders import ReminderService
from .celery_app import celery_app


@celery_app.task
def schedule_reminder(task_id: int, when: str) -> None:
    async def _run() -> None:
        async with SessionLocal() as session:
            service = ReminderService(session)
            await service.schedule(task_id, datetime.fromisoformat(when))

    asyncio.run(_run())
    logger.info("worker.reminder_scheduled", task_id=task_id)


@celery_app.task
def dispatch_due_reminders(batch_size: int = 100) -> int:
    async def _run() -> int:
        async with SessionLocal() as session:
            service = ReminderService(session)
            reminders = await service.get_due_reminders(limit=batch_size)
            if not reminders:
                return 0
            adapter = TelegramAdapter()
            processed = 0
            for reminder in reminders:
                task = reminder.task
                user = task.user if task else None
                if not task or not user or not user.telegram_id:
                    reminder.sent = True
                    continue
                locale = normalize_locale(user.language or settings.default_locale)
                due_extra = ""
                if task.due_at:
                    user_timezone = user.timezone or settings.default_timezone
                    due_extra = translate(
                        locale,
                        "task_summary_due",
                        due=format_datetime(task.due_at, locale, user_timezone, fmt="short"),
                    )
                message = translate(
                    locale,
                    "reminder_due_message",
                    title=task.title,
                    extra=due_extra,
                )
                try:
                    await adapter.send_message(
                        str(user.telegram_id),
                        prepare_telegram(locale, message),
                    )
                    reminder.sent = True
                    processed += 1
                except Exception:  # noqa: BLE001
                    logger.exception(
                        "worker.reminder.delivery_failed",
                        reminder_id=reminder.id,
                        user_id=user.id,
                    )
            try:
                await session.commit()
            except SQLAlchemyError:
                logger.exception("worker.reminder.commit_failed")
                await session.rollback()
            logger.info(
                "worker.reminder_dispatched",
                processed=processed,
                batch=len(reminders),
            )
            return processed

    return asyncio.run(_run())
