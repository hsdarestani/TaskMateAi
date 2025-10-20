from __future__ import annotations

from typing import Awaitable, Callable

import redis.asyncio as aioredis
from fastapi import HTTPException, Request, status

from backend.core.logging import logger
from backend.core.settings import settings


async def enforce_rate_limit(request: Request, key_prefix: str, limit: int, window_seconds: int) -> None:
    client_host = request.client.host if request.client else "unknown"
    key = f"ratelimit:{key_prefix}:{client_host}"
    redis = None
    try:
        redis = aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        current = await redis.incr(key)
        if current == 1:
            await redis.expire(key, window_seconds)
        if current > limit:
            logger.warning("rate_limit.exceeded", key=key, count=current)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"code": "error_rate_limited"},
            )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning("rate_limit.degraded", error=str(exc))
    finally:
        if redis is not None:
            await redis.aclose()


def rate_limiter_dependency(key_prefix: str, limit: int, window_seconds: int) -> Callable[[Request], Awaitable[None]]:
    async def dependency(request: Request) -> None:
        await enforce_rate_limit(request, key_prefix, limit, window_seconds)

    return dependency

