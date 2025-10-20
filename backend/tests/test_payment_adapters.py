import hashlib
import hmac

import pytest

from backend.adapters.cryptobot import CryptoBotAdapter
from backend.adapters.zibal import ZibalAdapter
from backend.core.settings import settings


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self) -> None:  # pragma: no cover
        return None

    def json(self):
        return self._payload


@pytest.mark.asyncio
async def test_zibal_adapter_create_and_verify(monkeypatch):
    responses = [
        {"result": 100, "trackId": "555"},
        {"result": 100, "orderId": "order-1", "trackId": "555"},
    ]

    def fake_client(*args, **kwargs):
        class _Client:
            async def __aenter__(self_inner):
                return self_inner

            async def __aexit__(self_inner, exc_type, exc, tb):
                return False

            async def post(self_inner, url, json=None):
                return DummyResponse(responses.pop(0))

        return _Client()

    monkeypatch.setattr("backend.adapters.zibal.httpx.AsyncClient", fake_client)

    adapter = ZibalAdapter()
    create = await adapter.create_payment(amount=1000, callback_url="https://cb", order_id="order-1")
    assert create["paymentUrl"].endswith("/555")

    verify = await adapter.verify_payment(track_id="555", order_id="order-1")
    assert verify["trackId"] == "555"


@pytest.mark.asyncio
async def test_cryptobot_adapter_invoice_and_webhook(monkeypatch):
    responses = [{"ok": True, "result": {"invoice_id": 123, "pay_url": "https://crypto"}}]

    def fake_client(*args, **kwargs):
        class _Client:
            async def __aenter__(self_inner):
                return self_inner

            async def __aexit__(self_inner, exc_type, exc, tb):
                return False

            async def post(self_inner, url, json=None, headers=None):
                return DummyResponse(responses.pop(0))

        return _Client()

    monkeypatch.setattr("backend.adapters.cryptobot.httpx.AsyncClient", fake_client)

    adapter = CryptoBotAdapter()
    invoice = await adapter.create_invoice(amount=10, asset="USDT")
    assert invoice["result"]["invoice_id"] == 123

    body = b"{\"invoice_id\":123,\"status\":\"paid\"}"
    valid_signature = hmac.new(
        settings.cryptobot_api_token.encode(), body, hashlib.sha256
    ).hexdigest()
    assert adapter.verify_webhook(body, valid_signature) is True
    assert adapter.verify_webhook(body, "invalid") is False
