from __future__ import annotations

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from uuid import uuid4

import structlog

try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    sentry_sdk = None


from backend.api import (
    admin_router,
    analytics_router,
    org_router,
    payments_router,
    projects_router,
    reports_router,
    tasks_router,
    teams_router,
    telegram_router,
    users_router,
)
from backend.core.i18n import get_locale_from_request, translate
from backend.core.logging import configure_logging
from backend.core.settings import settings
from backend.core.rate_limit import rate_limiter_dependency

configure_logging()

if settings.sentry_dsn and sentry_sdk:
    sentry_sdk.init(  # type: ignore[call-arg]
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        integrations=[FastApiIntegration()],
        traces_sample_rate=0.1,
    )

app = FastAPI(title=settings.app_name)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        request_id = request.headers.get("x-request-id") or uuid4().hex
        structlog.contextvars.bind_contextvars(request_id=request_id)
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.clear_contextvars()
        response.headers.setdefault("X-Request-ID", request_id)
        return response


class LocalizationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        locale = get_locale_from_request(request)
        request.state.locale = locale
        response = await call_next(request)
        response.headers.setdefault("Content-Language", locale)
        return response


app.add_middleware(RequestContextMiddleware)
app.add_middleware(LocalizationMiddleware)

app.include_router(admin_router.router)
app.include_router(analytics_router.router)
app.include_router(org_router.router)
app.include_router(payments_router.router)
app.include_router(projects_router.router)
app.include_router(reports_router.router)
app.include_router(tasks_router.router)
app.include_router(teams_router.router)
app.include_router(telegram_router.router)
app.include_router(users_router.router)


@app.get("/healthz", tags=["system"])
async def health(_: None = Depends(rate_limiter_dependency("healthz", limit=30, window_seconds=60))) -> dict:
    return {"status": "ok"}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    locale = getattr(request.state, "locale", settings.default_locale)
    detail = exc.detail
    code = None
    message = None
    if isinstance(detail, dict):
        code = detail.get("code")
        params = detail.get("params", {})
        template = detail.get("message")
        if code:
            message = translate(locale, code, **params)
        elif template:
            message = translate(locale, template, **params)
    elif isinstance(detail, str):
        code = detail
        message = translate(locale, detail)
    else:
        message = str(detail)
    body = {"detail": message}
    if code:
        body["code"] = code
    logger = structlog.get_logger()
    logger.error(
        "http_exception",
        status=exc.status_code,
        code=code,
        detail=body.get("detail"),
        path=str(request.url),
    )
    return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers)
