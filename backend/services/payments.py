from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.adapters.cryptobot import CryptoBotAdapter
from backend.adapters.telegram import TelegramAdapter
from backend.adapters.zibal import ZibalAdapter
from backend.core.i18n import format_date, normalize_locale, prepare_telegram, translate
from backend.core.logging import logger
from backend.core.settings import settings
from backend.models import (
    Organization,
    Payment,
    Subscription,
    SubscriptionMethod,
    SubscriptionSubjectType,
    User,
)

from .base import ServiceBase
from .subscriptions import SubscriptionService


class PaymentService(ServiceBase):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self._subscription_service = SubscriptionService(session)

    async def _find_payment_by_reference(
        self,
        *,
        method: SubscriptionMethod,
        references: list[str | None],
    ) -> Optional[Payment]:
        refs = [ref for ref in references if ref]
        if not refs:
            return None
        stmt = (
            select(Payment)
            .where(Payment.method == method, Payment.ref_id.in_(refs))
            .order_by(Payment.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def _format_amount(amount: Decimal) -> str:
        quantized = amount.quantize(Decimal("0.01"))
        if quantized == quantized.to_integral():
            return str(int(quantized))
        return f"{quantized:.2f}"

    async def _notify_via_telegram(
        self,
        payment: Payment,
        subscription: Optional[Subscription],
        success: bool,
    ) -> None:
        adapter = TelegramAdapter()
        if not adapter.base_url:
            return

        chat_id: Optional[str] = None
        locale = normalize_locale(None)
        if payment.subject_type == SubscriptionSubjectType.USER:
            user = await self.session.get(User, payment.subject_id)
            if not user or not user.telegram_id:
                return
            chat_id = str(user.telegram_id)
            locale = normalize_locale(user.language)
            message_key = "payment_success_user" if success else "payment_failed_user"
        else:
            organization = await self.session.get(Organization, payment.subject_id)
            if not organization or not organization.owner_user_id:
                return
            owner = await self.session.get(User, organization.owner_user_id)
            if not owner or not owner.telegram_id:
                return
            chat_id = str(owner.telegram_id)
            locale = normalize_locale(owner.language)
            message_key = "payment_success_org" if success else "payment_failed_org"

        active_until = "-"
        if subscription and subscription.active_until:
            active_until = format_date(
                subscription.active_until,
                locale,
                timezone_name=settings.default_timezone,
                fmt="medium",
            )

        message = translate(
            locale,
            message_key,
            amount=self._format_amount(payment.amount),
            currency=payment.currency,
            active_until=active_until,
        )

        try:
            await adapter.send_message(chat_id=chat_id, text=prepare_telegram(locale, message))
        except Exception:  # noqa: BLE001
            logger.exception("payment.telegram_notification_failed", payment_id=payment.id)

    async def create_payment_record(
        self,
        *,
        subject_type: SubscriptionSubjectType,
        subject_id: int,
        method: SubscriptionMethod,
        currency: str,
        amount: float | Decimal,
        status: str = "pending",
        ref_id: str | None = None,
    ) -> Payment:
        payment = Payment(
            subject_type=subject_type,
            subject_id=subject_id,
            method=method,
            currency=currency,
            amount=Decimal(str(amount)),
            status=status,
            ref_id=ref_id,
        )
        self.session.add(payment)
        await self.session.commit()
        await self.session.refresh(payment)
        logger.info(
            "payment.created",
            payment_id=payment.id,
            subject_type=subject_type.value,
            subject_id=subject_id,
            method=method.value,
        )
        return payment

    async def get_payment(self, payment_id: int) -> Payment:
        payment = await self.session.get(Payment, payment_id)
        if not payment:
            raise LookupError("payment_not_found")
        return payment

    async def verify_payment(
        self,
        payment_id: int,
        *,
        status: str,
        ref_id: str | None = None,
        activation_days: int = 30,
    ) -> Payment:
        payment = await self.get_payment(payment_id)
        payment.status = status
        if ref_id:
            payment.ref_id = ref_id

        lowered = status.lower()
        if lowered in {"paid", "success", "successful", "completed"}:
            await self._subscription_service.activate(
                subject_type=payment.subject_type,
                subject_id=payment.subject_id,
                method=payment.method,
                duration_days=activation_days,
            )
        elif lowered in {"failed", "canceled"}:
            logger.warning(
                "payment.failed",
                payment_id=payment.id,
                status=status,
            )

        await self.session.commit()
        await self.session.refresh(payment)
        logger.info("payment.verified", payment_id=payment.id, status=status)
        return payment

    async def create_crypto_invoice(
        self,
        *,
        subject_type: SubscriptionSubjectType,
        subject_id: int,
        amount: float,
        asset: str,
        description: str | None = None,
    ) -> Dict[str, Any]:
        adapter = CryptoBotAdapter()
        response = await adapter.create_invoice(
            amount=amount, asset=asset, description=description
        )
        if not isinstance(response, dict):
            logger.error("payment.crypto_invoice_invalid_response")
            return {"error": "invalid_response"}
        if response.get("error"):
            logger.error("payment.crypto_invoice_error", error=response["error"])
            return response

        result = response.get("result") or {}
        invoice_id = result.get("invoice_id") or result.get("id")
        if invoice_id is None:
            logger.error("payment.crypto_invoice_missing_id", response=response)
            return {"error": "missing_invoice_id"}

        payment = await self.create_payment_record(
            subject_type=subject_type,
            subject_id=subject_id,
            method=SubscriptionMethod.CRYPTO,
            currency=asset,
            amount=amount,
            ref_id=str(invoice_id),
        )

        return {
            "ok": True,
            "payment_id": payment.id,
            "invoice_id": str(invoice_id),
            "invoice_url": result.get("pay_url") or result.get("url"),
            "response": response,
        }

    async def create_zibal_payment(
        self,
        *,
        subject_type: SubscriptionSubjectType,
        subject_id: int,
        amount: int,
        callback_url: str,
        order_id: str | None = None,
    ) -> Dict[str, Any]:
        adapter = ZibalAdapter()
        resolved_order_id = order_id or uuid4().hex
        response = await adapter.create_payment(
            amount=amount, callback_url=callback_url, order_id=resolved_order_id
        )
        if not isinstance(response, dict):
            logger.error("payment.zibal_invalid_response")
            return {"error": "invalid_response"}
        if response.get("error"):
            logger.error("payment.zibal_error", error=response["error"])
            return response
        if response.get("result") != 100:
            logger.error("payment.zibal_unexpected_result", response=response)
            return {"error": "gateway_error", "response": response}

        payment = await self.create_payment_record(
            subject_type=subject_type,
            subject_id=subject_id,
            method=SubscriptionMethod.ZIBAL,
            currency="IRR",
            amount=Decimal(str(amount)),
            ref_id=resolved_order_id,
        )

        track_id = response.get("trackId")
        payment_url = response.get("paymentUrl")
        if not payment_url and track_id:
            payment_url = f"https://gateway.zibal.ir/start/{track_id}"

        return {
            "ok": True,
            "payment_id": payment.id,
            "order_id": resolved_order_id,
            "track_id": str(track_id) if track_id else None,
            "payment_url": payment_url,
            "response": response,
        }

    async def verify_zibal_callback(
        self,
        *,
        track_id: Optional[str],
        order_id: Optional[str],
    ) -> Dict[str, Any]:
        adapter = ZibalAdapter()
        response = await adapter.verify_payment(track_id=track_id, order_id=order_id)
        if not isinstance(response, dict):
            logger.error("payment.zibal_verify_invalid_response")
            return {"ok": False, "error": "invalid_response"}
        if response.get("error"):
            logger.error("payment.zibal_verify_error", error=response["error"])
            return {"ok": False, "error": response["error"]}

        resolved_order = order_id or response.get("orderId")
        payment = await self._find_payment_by_reference(
            method=SubscriptionMethod.ZIBAL,
            references=[resolved_order, track_id],
        )
        if not payment:
            logger.error(
                "payment.zibal_payment_missing",
                order_id=resolved_order,
                track_id=track_id,
            )
            return {"ok": False, "error": "payment_not_found"}

        success = response.get("result") == 100
        status = "paid" if success else "failed"
        ref_value = response.get("trackId") or track_id or payment.ref_id
        verified_payment = await self.verify_payment(
            payment.id,
            status=status,
            ref_id=str(ref_value) if ref_value else payment.ref_id,
        )
        subscription = await self._subscription_service.get_subscription(
            verified_payment.subject_type, verified_payment.subject_id
        )
        await self._notify_via_telegram(verified_payment, subscription, success)

        return {
            "ok": success,
            "status": status,
            "payment_id": verified_payment.id,
            "order_id": resolved_order,
            "track_id": response.get("trackId") or track_id,
            "response": response,
        }

    async def verify_crypto_callback(
        self,
        *,
        payload: Dict[str, Any],
        raw_body: bytes,
        signature: Optional[str],
    ) -> Dict[str, Any]:
        adapter = CryptoBotAdapter()
        if not adapter.verify_webhook(raw_body, signature):
            return {"ok": False, "error": "invalid_signature"}

        invoice_id = payload.get("invoice_id") or payload.get("id")
        if invoice_id is None and "payload" in payload:
            invoice_id = payload["payload"].get("invoice_id")
        if invoice_id is None:
            logger.error("payment.crypto_verify_missing_invoice_id", payload=payload)
            return {"ok": False, "error": "missing_invoice_id"}

        payment = await self._find_payment_by_reference(
            method=SubscriptionMethod.CRYPTO,
            references=[str(invoice_id)],
        )
        if not payment:
            logger.error("payment.crypto_payment_missing", invoice_id=invoice_id)
            return {"ok": False, "error": "payment_not_found"}

        status_raw = str(payload.get("status", "")).lower()
        success = status_raw in {"paid", "completed", "success"}
        status = "paid" if success else "failed"

        verified_payment = await self.verify_payment(
            payment.id,
            status=status,
            ref_id=str(invoice_id),
        )
        subscription = await self._subscription_service.get_subscription(
            verified_payment.subject_type, verified_payment.subject_id
        )
        await self._notify_via_telegram(verified_payment, subscription, success)

        invoice_details = await adapter.get_invoice(invoice_id)
        if not isinstance(invoice_details, dict):
            invoice_details = {"error": "invalid_response"}

        return {
            "ok": success,
            "status": status,
            "payment_id": verified_payment.id,
            "invoice_id": str(invoice_id),
            "gateway_status": status_raw,
            "response": invoice_details,
        }
