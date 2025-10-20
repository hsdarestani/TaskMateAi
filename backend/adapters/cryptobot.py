from __future__ import annotations

import hashlib
import hmac
from typing import Any, Dict, Optional

import httpx

from backend.core.logging import logger
from backend.core.settings import settings


class CryptoBotAdapter:
    base_url = "https://pay.crypt.bot/api"

    async def create_invoice(
        self, amount: float, asset: str, description: str | None = None
    ) -> Dict[str, Any]:
        if not settings.cryptobot_api_token:
            logger.warning("cryptobot.token_missing")
            return {"error": "token_missing"}
        headers = {"X-Token": settings.cryptobot_api_token}
        payload = {"amount": amount, "asset": asset}
        if description:
            payload["description"] = description
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(f"{self.base_url}/createInvoice", headers=headers, json=payload)
            response.raise_for_status()
            return response.json()

    async def get_invoice(self, invoice_id: str | int) -> Dict[str, Any]:
        if not settings.cryptobot_api_token:
            logger.warning("cryptobot.token_missing")
            return {"error": "token_missing"}
        headers = {"X-Token": settings.cryptobot_api_token}
        payload = {"invoice_id": invoice_id}
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{self.base_url}/getInvoice", headers=headers, json=payload
            )
            response.raise_for_status()
            return response.json()

    def verify_webhook(self, raw_body: bytes, signature: Optional[str]) -> bool:
        if not settings.cryptobot_api_token:
            logger.warning("cryptobot.token_missing")
            return False
        if not signature:
            logger.warning("cryptobot.signature_missing")
            return False
        secret = settings.cryptobot_api_token.encode()
        if not raw_body:
            logger.warning("cryptobot.webhook.empty_body")
            return False
        digest = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()
        if hmac.compare_digest(digest, signature):
            return True
        logger.warning("cryptobot.signature_mismatch")
        return False
