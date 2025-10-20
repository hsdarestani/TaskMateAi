from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.core.rbac import Principal, Role, require_roles
from backend.schemas.users import UserCreate, UserRead
from backend.services.base import provide_service
from backend.services.users import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserRead)
async def create_user(
    payload: UserCreate,
    principal: Principal = Depends(require_roles(Role.SYSTEM_ADMIN, Role.ORG_ADMIN)),
    service: UserService = Depends(provide_service(UserService)),
) -> UserRead:
    return await service.create(payload, principal)


@router.get("/me", response_model=UserRead)
async def read_profile(
    principal: Principal = Depends(
        require_roles(Role.MEMBER, Role.TEAM_MANAGER, Role.ORG_ADMIN, Role.SYSTEM_ADMIN)
    ),
    service: UserService = Depends(provide_service(UserService)),
) -> UserRead:
    return await service.get_by_id(int(principal.subject))
