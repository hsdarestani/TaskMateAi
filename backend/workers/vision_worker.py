from __future__ import annotations

import asyncio
from typing import List

from backend.adapters.openai_adapter import OpenAIAdapter
from backend.core.logging import logger
from .celery_app import celery_app


def _parse_tasks(text: str) -> List[str]:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        stripped = stripped.lstrip("-••")
        stripped = stripped.strip()
        if stripped:
            lines.append(stripped)
    return lines


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def analyze_image(self, file_path: str) -> List[str]:
    async def _run() -> List[str]:
        logger.info("worker.vision.start", file_path=file_path)
        adapter = OpenAIAdapter()
        try:
            response = await adapter.extract_tasks_from_image(file_path)
        except Exception:  # noqa: BLE001
            logger.exception("worker.vision.failed", file_path=file_path)
            raise
        if not response:
            logger.warning("worker.vision.empty", file_path=file_path)
            return []
        tasks = _parse_tasks(response)
        logger.info("worker.vision.completed", file_path=file_path, tasks=len(tasks))
        return tasks

    return asyncio.run(_run())
