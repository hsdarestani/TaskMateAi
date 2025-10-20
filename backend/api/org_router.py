from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.core.rbac import Principal, Role, require_roles
from backend.models import IntegrationProvider, IntegrationScope, OrganizationUserRole
from backend.schemas.orgs import (
    OrganizationCreate,
    OrganizationInviteRequest,
    OrganizationInviteResponse,
    OrganizationJoinRequest,
    OrganizationRead,
)
from backend.schemas.integrations import (
    IntegrationSettingsPayload,
    IntegrationSettingsRead,
)
from backend.schemas.reports import ReportFormat, ReportRequest, ReportResponse
from backend.services.base import provide_service
from backend.services.integrations import IntegrationService
from backend.services.orgs import OrganizationService
from backend.services.reports import ReportService

router = APIRouter(prefix="/api/orgs", tags=["organizations"])


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


@router.post("/", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
async def create_org(
    payload: OrganizationCreate,
    principal: Principal = Depends(
        require_roles(
            Role.SYSTEM_ADMIN,
            Role.ORG_ADMIN,
            Role.TEAM_MANAGER,
            Role.MEMBER,
        )
    ),
    service: OrganizationService = Depends(provide_service(OrganizationService)),
) -> OrganizationRead:
    owner_user_id = payload.owner_user_id or principal.user_id
    if owner_user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": "error_owner_required"})

    if (
        payload.owner_user_id is not None
        and payload.owner_user_id != principal.user_id
        and not principal.is_system_admin
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "error_forbidden"})

    organization = await service.create(
        name=payload.name,
        owner_user_id=owner_user_id,
        plan=payload.plan,
    )
    return OrganizationRead.model_validate(organization)


@router.get(
    "/{organization_id}/integrations/{provider}",
    response_model=IntegrationSettingsRead,
)
async def get_org_integration_settings(
    organization_id: int,
    provider: IntegrationProvider,
    principal: Principal = Depends(require_roles(Role.SYSTEM_ADMIN, Role.ORG_ADMIN)),
    service: IntegrationService = Depends(provide_service(IntegrationService)),
) -> IntegrationSettingsRead:
    if not principal.has_org_privilege(organization_id, Role.ORG_ADMIN) and not principal.is_system_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "error_forbidden"})

    entry = await service.get_setting(
        provider,
        scope=IntegrationScope.ORGANIZATION,
        organization_id=organization_id,
    )
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "error_not_found"})
    return _integration_response(entry)


@router.post(
    "/{organization_id}/integrations/{provider}",
    response_model=IntegrationSettingsRead,
)
async def configure_org_integration(
    organization_id: int,
    provider: IntegrationProvider,
    payload: IntegrationSettingsPayload,
    principal: Principal = Depends(require_roles(Role.SYSTEM_ADMIN, Role.ORG_ADMIN)),
    service: IntegrationService = Depends(provide_service(IntegrationService)),
) -> IntegrationSettingsRead:
    if not principal.has_org_privilege(organization_id, Role.ORG_ADMIN) and not principal.is_system_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "error_forbidden"})

    existing = await service.get_setting(
        provider,
        scope=IntegrationScope.ORGANIZATION,
        organization_id=organization_id,
    )
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
        scope=IntegrationScope.ORGANIZATION,
        organization_id=organization_id,
        config=config_payload,
    )
    return _integration_response(entry)


@router.get("/{org_id}", response_model=OrganizationRead)
async def get_org(
    org_id: int, service: OrganizationService = Depends(provide_service(OrganizationService))
) -> OrganizationRead:
    return await service.get(org_id)


@router.post("/invite", response_model=OrganizationInviteResponse)
async def create_invite(
    payload: OrganizationInviteRequest,
    principal: Principal = Depends(require_roles(Role.SYSTEM_ADMIN, Role.ORG_ADMIN)),
    service: OrganizationService = Depends(provide_service(OrganizationService)),
) -> OrganizationInviteResponse:
    if not principal.has_org_privilege(payload.organization_id, Role.ORG_ADMIN) and not principal.is_system_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "error_forbidden"})

    role = OrganizationUserRole(payload.role)
    invite_code = await service.generate_invite_code(
        organization_id=payload.organization_id,
        role=role,
    )
    return OrganizationInviteResponse(
        organization_id=payload.organization_id,
        role=payload.role,
        invite_code=invite_code,
    )


@router.post("/join", response_model=OrganizationRead)
async def join_organization(
    payload: OrganizationJoinRequest,
    principal: Principal = Depends(
        require_roles(
            Role.SYSTEM_ADMIN,
            Role.ORG_ADMIN,
            Role.TEAM_MANAGER,
            Role.MEMBER,
        )
    ),
    service: OrganizationService = Depends(provide_service(OrganizationService)),
) -> OrganizationRead:
    if principal.user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": "error_user_required"})

    membership = await service.join_with_invite(payload.invite_code, principal.user_id)
    organization = await service.get(membership.organization_id)
    return OrganizationRead.model_validate(organization)


@router.get("/{organization_id}/reports/{period}", response_model=ReportResponse)
async def organization_report(
    organization_id: int,
    period: Literal["daily", "weekly", "monthly"],
    report_date: date | None = Query(default=None),
    timezone: str | None = Query(default=None),
    team_id: int | None = Query(default=None),
    project_id: int | None = Query(default=None),
    locale: str | None = Query(default=None),
    format: ReportFormat = Query(default=ReportFormat.CSV),
    principal: Principal = Depends(require_roles(Role.SYSTEM_ADMIN, Role.ORG_ADMIN, Role.TEAM_MANAGER)),
    report_service: ReportService = Depends(provide_service(ReportService)),
) -> ReportResponse:
    if not principal.has_org_privilege(organization_id, Role.TEAM_MANAGER) and not principal.is_system_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "error_forbidden"})

    if team_id is not None and project_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "error_ambiguous_scope"},
        )

    if format is ReportFormat.PDF:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": "error_unsupported_format"})

    payload = ReportRequest(
        report_type=period,
        user_id=None,
        organization_id=organization_id,
        team_id=team_id,
        project_id=project_id,
        date=report_date,
        timezone=timezone,
        locale=locale,
        format=format,
    )
    return await report_service.generate(payload, principal)
