from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.core.rbac import Principal, Role, require_roles
from backend.schemas.teams import TeamCreate, TeamRead, TeamUpdate
from backend.services.base import provide_service
from backend.services.teams import TeamService

router = APIRouter(prefix="/api/teams", tags=["teams"])


@router.post("/", response_model=TeamRead, status_code=status.HTTP_201_CREATED)
async def create_team(
    payload: TeamCreate,
    principal: Principal = Depends(require_roles(Role.SYSTEM_ADMIN, Role.ORG_ADMIN, Role.TEAM_MANAGER)),
    service: TeamService = Depends(provide_service(TeamService)),
) -> TeamRead:
    if not principal.has_org_privilege(payload.organization_id, Role.TEAM_MANAGER) and not principal.is_system_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "error_forbidden"})
    team = await service.create_team(payload.organization_id, payload.name)
    return TeamRead.model_validate(team)


@router.get("/", response_model=list[TeamRead])
async def list_teams(
    organization_id: int = Query(...),
    principal: Principal = Depends(require_roles(Role.SYSTEM_ADMIN, Role.ORG_ADMIN, Role.TEAM_MANAGER, Role.MEMBER)),
    service: TeamService = Depends(provide_service(TeamService)),
) -> list[TeamRead]:
    if not principal.has_org_privilege(organization_id, Role.MEMBER) and not principal.is_system_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "error_forbidden"})
    teams = await service.list(organization_id)
    return [TeamRead.model_validate(team) for team in teams]


@router.patch("/{team_id}", response_model=TeamRead)
async def update_team(
    team_id: int,
    payload: TeamUpdate,
    principal: Principal = Depends(require_roles(Role.SYSTEM_ADMIN, Role.ORG_ADMIN, Role.TEAM_MANAGER)),
    service: TeamService = Depends(provide_service(TeamService)),
) -> TeamRead:
    team = await service.get(team_id)
    if not principal.can_manage_team(team_id, team.organization_id) and not principal.is_system_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "error_forbidden"})
    updated = await service.update_team(team_id, name=payload.name)
    return TeamRead.model_validate(updated)


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: int,
    principal: Principal = Depends(require_roles(Role.SYSTEM_ADMIN, Role.ORG_ADMIN)),
    service: TeamService = Depends(provide_service(TeamService)),
) -> None:
    team = await service.get(team_id)
    if not principal.has_org_privilege(team.organization_id, Role.ORG_ADMIN) and not principal.is_system_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "error_forbidden"})
    await service.delete(team_id)
    return None
