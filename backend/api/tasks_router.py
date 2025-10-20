from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.core.rbac import Principal, Role, require_roles
from backend.schemas.tasks import TaskCreate, TaskRead, TaskUpdate
from backend.services.base import provide_service
from backend.services.tasks import TaskService

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/", response_model=list[TaskRead])
async def list_tasks(
    status: str | None = Query(default=None),
    organization_id: int | None = Query(default=None),
    team_id: int | None = Query(default=None),
    project_id: int | None = Query(default=None),
    principal: Principal = Depends(
        require_roles(
            Role.SYSTEM_ADMIN,
            Role.ORG_ADMIN,
            Role.TEAM_MANAGER,
            Role.MEMBER,
        )
    ),
    service: TaskService = Depends(provide_service(TaskService)),
) -> list[TaskRead]:
    user_filter = principal.user_id

    if organization_id is not None and not principal.has_org_privilege(
        organization_id, Role.MEMBER
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "error_forbidden"})

    if team_id is not None and not principal.can_manage_team(team_id, organization_id):
        if not principal.is_system_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "error_forbidden"})

    if organization_id is not None or principal.is_system_admin:
        user_filter = None

    tasks = await service.list_tasks(
        user_id=user_filter,
        organization_id=organization_id,
        team_id=team_id,
        project_id=project_id,
        status=status,
    )
    return tasks


@router.post("/", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    principal: Principal = Depends(
        require_roles(
            Role.SYSTEM_ADMIN,
            Role.ORG_ADMIN,
            Role.TEAM_MANAGER,
            Role.MEMBER,
        )
    ),
    service: TaskService = Depends(provide_service(TaskService)),
) -> TaskRead:
    if payload.organization_id is not None and not principal.has_org_privilege(
        payload.organization_id, Role.TEAM_MANAGER
    ) and not principal.is_system_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "error_forbidden"})

    if (
        payload.assigned_team_id is not None
        and not principal.can_manage_team(payload.assigned_team_id, payload.organization_id)
        and not principal.is_system_admin
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "error_forbidden"})

    owner_user_id = payload.assignee_id or principal.user_id
    if owner_user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": "error_owner_required"})

    if not principal.can_manage_task(
        owner_user_id=owner_user_id,
        organization_id=payload.organization_id,
        assigned_team_id=payload.assigned_team_id,
    ) and not principal.is_system_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "error_forbidden"})

    task = await service.create_for_principal(payload, owner_user_id=owner_user_id)
    return TaskRead.model_validate(task)


@router.patch("/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: int,
    payload: TaskUpdate,
    principal: Principal = Depends(
        require_roles(
            Role.SYSTEM_ADMIN,
            Role.ORG_ADMIN,
            Role.TEAM_MANAGER,
            Role.MEMBER,
        )
    ),
    service: TaskService = Depends(provide_service(TaskService)),
) -> TaskRead:
    task = await service.get(task_id)
    if not principal.can_manage_task(
        owner_user_id=task.user_id,
        organization_id=task.organization_id,
        assigned_team_id=None,
    ) and not principal.is_system_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "error_forbidden"})

    model_fields = getattr(payload, "model_fields_set", set())
    if (
        "assigned_team_id" in model_fields
        and payload.assigned_team_id is not None
        and not principal.can_manage_team(payload.assigned_team_id, task.organization_id)
        and not principal.is_system_admin
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "error_forbidden"})

    updated = await service.update_from_payload(task_id, payload)

    if "assigned_team_id" in model_fields and payload.assigned_team_id is None:
        await service.assign_to_team(task_id, None)
        updated = await service.get(task_id)

    return TaskRead.model_validate(updated)
