from __future__ import annotations

import json
from datetime import datetime

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.core.rbac import Principal, Role, require_roles
from backend.core.settings import settings
from backend.core.rate_limit import rate_limiter_dependency
from backend.schemas.analytics import AnalyticsSummary, AnalyticsTrackRequest
from backend.services.analytics import (
    ANALYTICS_QUEUE_KEY,
    AnalyticsService,
    AnalyticsTaxonomy,
)
from backend.services.base import provide_service

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.post("/track")
async def track_events(
    payload: AnalyticsTrackRequest,
    _: None = Depends(rate_limiter_dependency("analytics:track", limit=60, window_seconds=60)),
    principal: Principal = Depends(
        require_roles(
            Role.SYSTEM_ADMIN,
            Role.ORG_ADMIN,
            Role.TEAM_MANAGER,
            Role.MEMBER,
        )
    ),
) -> dict:
    events = []
    fallback_user_id = principal.user_id
    for event in payload.events:
        raw = event.model_dump()
        if raw.get("user_id") is None and fallback_user_id is not None:
            raw["user_id"] = fallback_user_id
        normalized = AnalyticsTaxonomy.normalize_event(raw)
        created_at = raw.get("created_at")
        if isinstance(created_at, datetime):
            normalized["created_at"] = created_at.isoformat()
        elif isinstance(created_at, str):
            normalized["created_at"] = created_at
        source = normalized.get("source")
        if source is not None:
            normalized["source"] = source.value
        events.append(normalized)

    if not events:
        return {"queued": 0}

    redis = aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    try:
        for event in events:
            await redis.rpush(ANALYTICS_QUEUE_KEY, json.dumps(event, default=str))
    finally:
        await redis.aclose()
    return {"queued": len(events)}


@router.get("/summary", response_model=AnalyticsSummary)
async def get_summary(
    organization_id: int | None = Query(default=None),
    principal: Principal = Depends(require_roles(Role.SYSTEM_ADMIN, Role.ORG_ADMIN)),
    service: AnalyticsService = Depends(provide_service(AnalyticsService)),
) -> AnalyticsSummary:
    if organization_id is not None and not principal.has_org_privilege(organization_id, Role.ORG_ADMIN) and not principal.is_system_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "error_forbidden"})
    return await service.get_summary(organization_id=organization_id)
