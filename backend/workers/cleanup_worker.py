from __future__ import annotations

import asyncio

from backend.core.logging import logger
from backend.services.base import SessionLocal
from backend.services.files import FileService
from .celery_app import celery_app


@celery_app.task
def cleanup_files() -> None:
    async def _run() -> None:
        async with SessionLocal() as session:
            service = FileService(session)
            removed = await service.cleanup_expired()
        logger.info("worker.cleanup", removed=removed)

    asyncio.run(_run())
