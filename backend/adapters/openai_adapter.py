from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from backend.core.logging import logger
from backend.core.settings import settings


class OpenAIAdapter:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.openai_api_key
        self.base_url = "https://api.openai.com/v1"

    async def chat_completion(self, *, messages: List[Dict[str, str]], model: str = "gpt-4o-mini") -> Dict[str, Any]:
        if not self.api_key:
            logger.warning("OpenAI API key missing")
            return {"error": "api_key_missing"}
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json={"model": model, "messages": messages},
            )
            response.raise_for_status()
            return response.json()

    async def transcribe_audio_file(
        self, file_path: str, *, model: str = "gpt-4o-transcribe"
    ) -> Optional[str]:
        if not self.api_key:
            logger.warning("OpenAI API key missing for transcription")
            return None
        path = Path(file_path)
        if not path.exists():
            logger.warning("openai.transcribe.file_missing", file=file_path)
            return None
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=90) as client:
            with path.open("rb") as handle:
                files = {"file": (path.name, handle, "application/octet-stream")}
                data = {"model": model}
                response = await client.post(
                    f"{self.base_url}/audio/transcriptions",
                    headers=headers,
                    files=files,
                    data=data,
                )
            response.raise_for_status()
            payload = response.json()
            text = payload.get("text")
            if not text:
                logger.warning("openai.transcribe.empty", file=file_path, payload=payload)
            return text

    async def extract_tasks_from_image(
        self,
        file_path: str,
        *,
        model: str = "gpt-4o-mini",
        prompt: str = "Extract actionable task bullet points from this screenshot.",
    ) -> Optional[str]:
        if not self.api_key:
            logger.warning("OpenAI API key missing for vision analysis")
            return None
        path = Path(file_path)
        if not path.exists():
            logger.warning("openai.vision.file_missing", file=file_path)
            return None
        try:
            encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
        except Exception:  # noqa: BLE001
            logger.exception("openai.vision.read_failed", file=file_path)
            return None
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload: Dict[str, Any] = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a productivity assistant that extracts structured tasks.",
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{encoded}",
                            },
                        },
                    ],
                },
            ],
        }
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            try:
                content = data["choices"][0]["message"]["content"].strip()
            except (KeyError, IndexError):
                logger.warning("openai.vision.unexpected_response", response=data)
                return None
            return content or None
