from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from backend.core.logging import logger
from backend.core.settings import settings


class ZibalAdapter:
    base_url = "https://gateway.zibal.ir/v1"

    async def create_payment(
        self, amount: int, callback_url: str, order_id: str
    ) -> Dict[str, Any]:
        if not settings.zibal_merchant_id:
            logger.warning("zibal.merchant_id_missing")
            return {"error": "merchant_id_missing"}
        payload = {
            "merchant": settings.zibal_merchant_id,
            "amount": amount,
            "callbackUrl": callback_url,
            "orderId": order_id,
        }
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(f"{self.base_url}/request", json=payload)
            response.raise_for_status()
            data: Dict[str, Any] = response.json()
            if data.get("result") == 100 and data.get("trackId"):
                data.setdefault(
                    "paymentUrl", f"https://gateway.zibal.ir/start/{data['trackId']}"
                )
            return data

    async def verify_payment(
        self, *, track_id: Optional[str] = None, order_id: Optional[str] = None
    ) -> Dict[str, Any]:
        if not settings.zibal_merchant_id:
            logger.warning("zibal.merchant_id_missing")
            return {"error": "merchant_id_missing"}
        payload: Dict[str, Any] = {"merchant": settings.zibal_merchant_id}
        if track_id:
            payload["trackId"] = track_id
        if order_id:
            payload["orderId"] = order_id
        if len(payload) == 1:
            logger.warning("zibal.verify.missing_reference")
            return {"error": "missing_reference"}
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(f"{self.base_url}/verify", json=payload)
            response.raise_for_status()
            return response.json()
