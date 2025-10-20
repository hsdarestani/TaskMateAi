from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from backend.core.logging import logger
from backend.core.settings import settings


class TelegramAdapter:
    def __init__(self, token: str | None = None) -> None:
        self.token = token or settings.telegram_bot_token
        self.base_url = f"https://api.telegram.org/bot{self.token}" if self.token else None
        self.file_url = f"https://api.telegram.org/file/bot{self.token}" if self.token else None

    async def send_message(self, chat_id: str, text: str, **kwargs: Any) -> Dict[str, Any]:
        if not self.base_url:
            logger.warning("Telegram token missing, skipping message delivery")
            return {"ok": False, "description": "Token missing"}
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{self.base_url}/sendMessage",
                json={"chat_id": chat_id, "text": text, **kwargs},
            )
            response.raise_for_status()
            return response.json()

    async def answer_callback_query(
        self, callback_query_id: str, text: str | None = None, show_alert: bool = False
    ) -> Dict[str, Any]:
        if not self.base_url:
            logger.warning("Telegram token missing, skipping callback answer")
            return {"ok": False, "description": "Token missing"}
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{self.base_url}/answerCallbackQuery",
                json={
                    "callback_query_id": callback_query_id,
                    **({"text": text} if text else {}),
                    "show_alert": show_alert,
                },
            )
            response.raise_for_status()
            return response.json()

    async def get_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        if not self.base_url:
            logger.warning("Telegram token missing, cannot fetch file metadata")
            return None
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{self.base_url}/getFile",
                json={"file_id": file_id},
            )
            response.raise_for_status()
            payload = response.json()
            if not payload.get("ok"):
                logger.warning("telegram.get_file.failed", file_id=file_id, response=payload)
                return None
            return payload.get("result")

    async def download_file(self, file_path: str) -> Optional[bytes]:
        if not self.file_url:
            logger.warning("Telegram token missing, cannot download file")
            return None
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{self.file_url}/{file_path}")
            response.raise_for_status()
            return response.content
