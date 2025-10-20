from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from backend.core.settings import settings

celery_app = Celery(
    "taskmate",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.default_timezone,
    enable_utc=True,
)

celery_app.conf.beat_schedule = {
    "dispatch-reminders": {
        "task": "backend.workers.reminders_worker.dispatch_due_reminders",
        "schedule": crontab(),
    },
    "consume-analytics-events": {
        "task": "backend.workers.analytics_worker.consume_analytics_events",
        "schedule": 60.0,
    },
    "analytics-daily-snapshot": {
        "task": "backend.workers.analytics_worker.generate_daily_snapshot",
        "schedule": crontab(hour=1, minute=0),
    },
    "cleanup-expired-files": {
        "task": "backend.workers.cleanup_worker.cleanup_files",
        "schedule": crontab(hour=2, minute=0),
    },
}
