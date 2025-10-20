from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError

from backend.core.rate_limit import rate_limiter_dependency
from backend.core.rbac import Principal, Role, require_roles
from backend.schemas.payments import (
    CryptoPaymentCreate,
    CryptoVerifyPayload,
    ZibalPaymentCreate,
    ZibalVerifyPayload,
)
from backend.services.base import provide_service
from backend.services.payments import PaymentService

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.post("/zibal/create")
async def create_zibal_payment(
    payload: ZibalPaymentCreate,
    _: Principal = Depends(require_roles(Role.SYSTEM_ADMIN, Role.ORG_ADMIN)),
    service: PaymentService = Depends(provide_service(PaymentService)),
) -> dict:
    result = await service.create_zibal_payment(
        subject_type=payload.subject_type,
        subject_id=payload.subject_id,
        amount=payload.amount,
        callback_url=str(payload.callback_url),
        order_id=payload.order_id,
    )
    if not result.get("ok", False):
        raw_error = str(result.get("error", "gateway"))
        if raw_error.startswith("error_"):
            error_code = raw_error
        else:
            error_code = raw_error[:-6] if raw_error.endswith("_error") else raw_error
            error_code = f"error_{error_code}"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": error_code},
        )
    return result


@router.post("/zibal/verify")
async def verify_zibal_payment(
    payload: ZibalVerifyPayload,
    _: None = Depends(rate_limiter_dependency("payments:zibal", limit=120, window_seconds=60)),
    service: PaymentService = Depends(provide_service(PaymentService)),
) -> dict:
    return await service.verify_zibal_callback(
        track_id=payload.track_id,
        order_id=payload.order_id,
    )


@router.post("/crypto/create")
async def create_crypto_payment(
    payload: CryptoPaymentCreate,
    _: Principal = Depends(require_roles(Role.SYSTEM_ADMIN, Role.ORG_ADMIN)),
    service: PaymentService = Depends(provide_service(PaymentService)),
) -> dict:
    result = await service.create_crypto_invoice(
        subject_type=payload.subject_type,
        subject_id=payload.subject_id,
        amount=payload.amount,
        asset=payload.asset,
        description=payload.description,
    )
    if not result.get("ok", False):
        raw_error = str(result.get("error", "gateway"))
        if raw_error.startswith("error_"):
            error_code = raw_error
        else:
            error_code = raw_error[:-6] if raw_error.endswith("_error") else raw_error
            error_code = f"error_{error_code}"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": error_code},
        )
    return result


@router.post("/crypto/verify")
async def verify_crypto_payment(
    request: Request,
    _: None = Depends(rate_limiter_dependency("payments:crypto", limit=120, window_seconds=60)),
    service: PaymentService = Depends(provide_service(PaymentService)),
) -> dict:
    raw_body = await request.body()
    try:
        payload_raw = raw_body.decode("utf-8") or "{}"
        payload_dict = json.loads(payload_raw)
    except json.JSONDecodeError:
        return {"ok": False, "error": "invalid_json"}

    try:
        payload_model = CryptoVerifyPayload.model_validate(payload_dict)
    except ValidationError:
        return {"ok": False, "error": "invalid_payload"}

    signature = request.headers.get("X-Signature")
    result = await service.verify_crypto_callback(
        payload=payload_model.model_dump(),
        raw_body=raw_body,
        signature=signature,
    )
    return result
