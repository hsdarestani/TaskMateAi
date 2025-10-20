from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.core.rbac import Principal, Role, require_roles
from backend.schemas.projects import ProjectCreate, ProjectRead, ProjectUpdate
from backend.services.base import provide_service
from backend.services.projects import ProjectService

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("/", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    principal: Principal = Depends(require_roles(Role.SYSTEM_ADMIN, Role.ORG_ADMIN, Role.TEAM_MANAGER)),
    service: ProjectService = Depends(provide_service(ProjectService)),
) -> ProjectRead:
    if not principal.has_org_privilege(payload.organization_id, Role.TEAM_MANAGER) and not principal.is_system_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "error_forbidden"})
    project = await service.create_project(
        organization_id=payload.organization_id,
        name=payload.name,
        description=payload.description,
        team_id=payload.team_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=payload.status,
    )
    return ProjectRead.model_validate(project)


@router.get("/", response_model=list[ProjectRead])
async def list_projects(
    organization_id: int | None = Query(default=None),
    principal: Principal = Depends(require_roles(Role.SYSTEM_ADMIN, Role.ORG_ADMIN, Role.TEAM_MANAGER, Role.MEMBER)),
    service: ProjectService = Depends(provide_service(ProjectService)),
) -> list[ProjectRead]:
    if organization_id is not None and not principal.has_org_privilege(organization_id, Role.MEMBER) and not principal.is_system_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "error_forbidden"})
    if organization_id is None and not principal.is_system_admin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": "error_organization_required"})
    projects = await service.list(organization_id=organization_id)
    return [ProjectRead.model_validate(project) for project in projects]


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: int,
    payload: ProjectUpdate,
    principal: Principal = Depends(require_roles(Role.SYSTEM_ADMIN, Role.ORG_ADMIN, Role.TEAM_MANAGER)),
    service: ProjectService = Depends(provide_service(ProjectService)),
) -> ProjectRead:
    project = await service.get(project_id)
    if not principal.has_org_privilege(project.organization_id, Role.TEAM_MANAGER) and not principal.is_system_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "error_forbidden"})

    data = payload.model_dump(exclude_unset=True)
    model_fields = getattr(payload, "model_fields_set", set())
    if "team_id" in model_fields:
        await service.assign_team(project_id, payload.team_id)
        project = await service.get(project_id)
        data.pop("team_id", None)

    updated = await service.update_project(
        project_id,
        name=data.get("name"),
        description=data.get("description"),
        team_id=data.get("team_id"),
        start_date=data.get("start_date"),
        end_date=data.get("end_date"),
        status=data.get("status"),
    )
    return ProjectRead.model_validate(updated)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    principal: Principal = Depends(require_roles(Role.SYSTEM_ADMIN, Role.ORG_ADMIN)),
    service: ProjectService = Depends(provide_service(ProjectService)),
) -> None:
    project = await service.get(project_id)
    if not principal.has_org_privilege(project.organization_id, Role.ORG_ADMIN) and not principal.is_system_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "error_forbidden"})
    await service.delete(project_id)
    return None
