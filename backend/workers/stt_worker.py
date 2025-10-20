from __future__ import annotations

import asyncio
from typing import Optional

from backend.adapters.openai_adapter import OpenAIAdapter
from backend.core.logging import logger
from .celery_app import celery_app


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def transcribe_audio(self, file_path: str) -> Optional[str]:
    async def _run() -> Optional[str]:
        logger.info("worker.transcribe.start", file_path=file_path)
        adapter = OpenAIAdapter()
        try:
            text = await adapter.transcribe_audio_file(file_path)
        except Exception:  # noqa: BLE001
            logger.exception("worker.transcribe.failed", file_path=file_path)
            raise
        if text:
            preview = text[:120]
            logger.info("worker.transcribe.completed", file_path=file_path, preview=preview)
        else:
            logger.warning("worker.transcribe.empty", file_path=file_path)
        return text

    return asyncio.run(_run())
