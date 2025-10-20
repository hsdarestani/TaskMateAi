from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.core.rbac import Principal, Role, require_system_admin
from backend.core.security import create_access_token
from backend.schemas.admin import (
    AdminLoginRequest,
    AdminOrganizationSummary,
    AdminUserSummary,
    BlogPostCreate,
    BlogPostRead,
    BlogPostUpdate,
    NotificationRequest,
)
from backend.schemas.analytics import AnalyticsSummary
from backend.schemas.integrations import (
    IntegrationSettingsPayload,
    IntegrationSettingsRead,
)
from backend.schemas.auth import LoginResponse
from backend.services.base import provide_service
from backend.services.admin_accounts import AdminAccountService
from backend.services.analytics import AnalyticsService
from backend.services.blog import BlogService
from backend.services.notifications import NotificationService
from backend.services.integrations import IntegrationService
from backend.services.orgs import OrganizationService
from backend.services.users import UserService
from backend.models import IntegrationProvider, IntegrationScope

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _integration_response(entry) -> IntegrationSettingsRead:
    config = dict(entry.config or {})
    base_url = config.pop("base_url", None)
    api_token = config.pop("api_token", None)
    return IntegrationSettingsRead(
        provider=entry.provider.value,
        scope=entry.scope.value,
        organization_id=entry.organization_id,
        base_url=base_url,
        api_token=api_token,
        config=config,
        updated_at=entry.updated_at,
    )


@router.post("/login", response_model=LoginResponse)
async def admin_login(
    payload: AdminLoginRequest,
    service: AdminAccountService = Depends(provide_service(AdminAccountService)),
) -> LoginResponse:
    try:
        admin = await service.authenticate(payload.username, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "error_invalid_credentials"}) from exc
    token = create_access_token(
        str(admin.id),
        extra={"roles": [Role.SYSTEM_ADMIN.value]},
    )
    return LoginResponse(access_token=token)


@router.get(
    "/integrations/{provider}",
    response_model=IntegrationSettingsRead,
)
async def get_system_integration_settings(
    provider: IntegrationProvider,
    _: Principal = Depends(require_system_admin),
    service: IntegrationService = Depends(provide_service(IntegrationService)),
) -> IntegrationSettingsRead:
    entry = await service.get_setting(provider, scope=IntegrationScope.SYSTEM)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "error_not_found"})
    return _integration_response(entry)


@router.post(
    "/integrations/{provider}",
    response_model=IntegrationSettingsRead,
)
async def configure_system_integration(
    provider: IntegrationProvider,
    payload: IntegrationSettingsPayload,
    _: Principal = Depends(require_system_admin),
    service: IntegrationService = Depends(provide_service(IntegrationService)),
) -> IntegrationSettingsRead:
    existing = await service.get_setting(provider, scope=IntegrationScope.SYSTEM)
    config_payload: dict[str, object] = dict(existing.config if existing else {})
    data = payload.model_dump(exclude_unset=True)
    extras = data.get("config") or {}
    if extras:
        config_payload.update(extras)
    if "base_url" in data:
        if data["base_url"] is None:
            config_payload.pop("base_url", None)
        else:
            config_payload["base_url"] = str(data["base_url"])
    if "api_token" in data:
        if data["api_token"] is None:
            config_payload.pop("api_token", None)
        else:
            config_payload["api_token"] = data["api_token"]

    entry = await service.upsert_setting(
        provider,
        scope=IntegrationScope.SYSTEM,
        config=config_payload,
    )
    return _integration_response(entry)


@router.get("/users", response_model=list[AdminUserSummary])
async def list_users(
    organization_id: int | None = Query(default=None),
    _: Principal = Depends(require_system_admin),
    service: UserService = Depends(provide_service(UserService)),
) -> list[AdminUserSummary]:
    users = await service.list(organization_id=organization_id)
    return [AdminUserSummary.model_validate(user) for user in users]


@router.get("/orgs", response_model=list[AdminOrganizationSummary])
async def list_organizations(
    _: Principal = Depends(require_system_admin),
    service: OrganizationService = Depends(provide_service(OrganizationService)),
) -> list[AdminOrganizationSummary]:
    organizations = await service.list()
    return [AdminOrganizationSummary.model_validate(org) for org in organizations]


@router.get("/analytics/summary", response_model=AnalyticsSummary)
async def admin_analytics_summary(
    _: Principal = Depends(require_system_admin),
    service: AnalyticsService = Depends(provide_service(AnalyticsService)),
) -> AnalyticsSummary:
    return await service.get_summary()


@router.get("/blog", response_model=list[BlogPostRead])
async def list_blog_posts(
    _: Principal = Depends(require_system_admin),
    service: BlogService = Depends(provide_service(BlogService)),
) -> list[BlogPostRead]:
    posts = await service.list_posts()
    return [BlogPostRead.model_validate(post) for post in posts]


@router.post("/blog", response_model=BlogPostRead, status_code=status.HTTP_201_CREATED)
async def create_blog_post(
    payload: BlogPostCreate,
    _: Principal = Depends(require_system_admin),
    service: BlogService = Depends(provide_service(BlogService)),
) -> BlogPostRead:
    post = await service.create_post(payload)
    return BlogPostRead.model_validate(post)


@router.patch("/blog/{post_id}", response_model=BlogPostRead)
async def update_blog_post(
    post_id: int,
    payload: BlogPostUpdate,
    _: Principal = Depends(require_system_admin),
    service: BlogService = Depends(provide_service(BlogService)),
) -> BlogPostRead:
    try:
        post = await service.update_post(post_id, payload)
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "error_not_found"}) from None
    return BlogPostRead.model_validate(post)


@router.delete("/blog/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_blog_post(
    post_id: int,
    _: Principal = Depends(require_system_admin),
    service: BlogService = Depends(provide_service(BlogService)),
) -> None:
    await service.delete_post(post_id)
    return None


@router.post("/notifications", status_code=status.HTTP_202_ACCEPTED)
async def broadcast_notification(
    payload: NotificationRequest,
    principal: Principal = Depends(require_system_admin),
    service: NotificationService = Depends(provide_service(NotificationService)),
) -> dict:
    try:
        entry = await service.broadcast(
            title=payload.title,
            message=payload.message,
            created_by=principal.user_id,
        )
    except ValueError as exc:  # throttled
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    return {"id": entry.id, "created_at": entry.created_at.isoformat()}
