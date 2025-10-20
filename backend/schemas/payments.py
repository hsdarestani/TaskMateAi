from __future__ import annotations

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

from backend.models import SubscriptionSubjectType


class PaymentBase(BaseModel):
    subject_type: SubscriptionSubjectType
    subject_id: int


class ZibalPaymentCreate(PaymentBase):
    amount: int = Field(gt=0)
    callback_url: AnyHttpUrl
    order_id: str | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


class CryptoPaymentCreate(PaymentBase):
    amount: float = Field(gt=0)
    asset: str = Field(default="USDT", min_length=2, max_length=10)
    description: str | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


class ZibalVerifyPayload(BaseModel):
    track_id: str | None = Field(default=None, alias="trackId")
    order_id: str | None = Field(default=None, alias="orderId")
    success: int | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class CryptoVerifyPayload(BaseModel):
    invoice_id: int | str = Field(alias="invoice_id")
    status: str
    asset: str | None = None
    amount: float | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")
