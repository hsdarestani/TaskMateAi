from __future__ import annotations

import asyncio
import json
from datetime import date, datetime
from typing import List

import redis.asyncio as aioredis

from backend.core.logging import logger
from backend.core.settings import settings
from backend.services.analytics import ANALYTICS_QUEUE_KEY, AnalyticsService
from backend.services.base import SessionLocal
from .celery_app import celery_app

@celery_app.task
def refresh_analytics() -> None:
    async def _run() -> None:
        async with SessionLocal() as session:
            service = AnalyticsService(session)
            summary = await service.get_summary()
        logger.info("worker.analytics", summary=summary.model_dump())

    asyncio.run(_run())


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def consume_analytics_events(self, batch_size: int = 200) -> int:
    async def _run() -> int:
        redis = aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        events: List[dict] = []
        try:
            for _ in range(batch_size):
                payload = await redis.lpop(ANALYTICS_QUEUE_KEY)
                if payload is None:
                    break
                try:
                    event = json.loads(payload)
                except json.JSONDecodeError:
                    logger.warning("worker.analytics.invalid_event", payload=payload)
                    continue
                events.append(event)
        finally:
            await redis.aclose()

        if not events:
            logger.debug("worker.analytics.no_events")
            return 0

        async with SessionLocal() as session:
            service = AnalyticsService(session)
            processed = await service.record_events(events)
        logger.info("worker.analytics.events_consumed", count=processed)
        return processed

    return asyncio.run(_run())


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def generate_daily_snapshot(self, target_date: str | None = None) -> dict:
    async def _run() -> dict:
        target: date | None = None
        if target_date:
            try:
                parsed = datetime.fromisoformat(target_date)
                target = parsed.date()
            except ValueError:
                logger.warning("worker.analytics.snapshot_date_invalid", value=target_date)
        async with SessionLocal() as session:
            service = AnalyticsService(session)
            snapshot = await service.create_daily_snapshot(target_date=target)
        payload = {
            "date": snapshot.date.isoformat(),
            "users_active": snapshot.users_active,
            "orgs_active": snapshot.orgs_active,
            "payments_count": snapshot.payments_count,
            "revenue": str(snapshot.revenue),
            "tasks_created": snapshot.tasks_created,
        }
        logger.info("worker.analytics.snapshot", snapshot=payload)
        return payload

    return asyncio.run(_run())
