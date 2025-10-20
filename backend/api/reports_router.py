from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.core.rbac import Principal, Role, require_roles
from backend.schemas.reports import ReportFormat, ReportRequest, ReportResponse
from backend.services.base import provide_service
from backend.services.reports import ReportService

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/daily", response_model=ReportResponse)
async def get_daily_report(
    report_date: date | None = Query(default=None),
    timezone: str | None = Query(default=None),
    organization_id: int | None = Query(default=None),
    locale: str | None = Query(default=None),
    format: ReportFormat = Query(default=ReportFormat.TEXT),
    principal: Principal = Depends(
        require_roles(
            Role.SYSTEM_ADMIN,
            Role.ORG_ADMIN,
            Role.TEAM_MANAGER,
            Role.MEMBER,
        )
    ),
    service: ReportService = Depends(provide_service(ReportService)),
) -> ReportResponse:
    if format not in {ReportFormat.TEXT, ReportFormat.PDF}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": "error_unsupported_format"})

    return await _generate_user_report(
        service=service,
        principal=principal,
        report_type="daily",
        organization_id=organization_id,
        report_date=report_date,
        timezone=timezone,
        locale=locale,
        format=format,
    )


@router.get("/weekly", response_model=ReportResponse)
async def get_weekly_report(
    report_date: date | None = Query(default=None),
    timezone: str | None = Query(default=None),
    organization_id: int | None = Query(default=None),
    locale: str | None = Query(default=None),
    format: ReportFormat = Query(default=ReportFormat.TEXT),
    principal: Principal = Depends(
        require_roles(
            Role.SYSTEM_ADMIN,
            Role.ORG_ADMIN,
            Role.TEAM_MANAGER,
            Role.MEMBER,
        )
    ),
    service: ReportService = Depends(provide_service(ReportService)),
) -> ReportResponse:
    if format not in {ReportFormat.TEXT, ReportFormat.PDF}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": "error_unsupported_format"})

    return await _generate_user_report(
        service=service,
        principal=principal,
        report_type="weekly",
        organization_id=organization_id,
        report_date=report_date,
        timezone=timezone,
        locale=locale,
        format=format,
    )


async def _generate_user_report(
    *,
    service: ReportService,
    principal: Principal,
    report_type: Literal["daily", "weekly"],
    organization_id: int | None,
    report_date: date | None,
    timezone: str | None,
    locale: str | None,
    format: ReportFormat,
) -> ReportResponse:
    if organization_id is not None and not principal.has_org_privilege(
        organization_id, Role.TEAM_MANAGER
    ) and not principal.is_system_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "error_forbidden"})

    user_id = None
    if organization_id is None:
        user_id = principal.user_id
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": "error_user_required"})

    payload = ReportRequest(
        report_type=report_type,
        user_id=user_id,
        organization_id=organization_id,
        date=report_date,
        timezone=timezone,
        locale=locale,
        format=format,
    )
    return await service.generate(payload, principal)
