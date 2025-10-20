from __future__ import annotations

from enum import Enum
from typing import Dict, Iterable, Mapping, Optional, Set

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .security import decode_token


definition_error = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail={"code": "error_forbidden"},
)

auth_scheme = HTTPBearer(auto_error=False)


class Role(str, Enum):
    SYSTEM_ADMIN = "system_admin"
    ORG_ADMIN = "org_admin"
    TEAM_MANAGER = "team_manager"
    MEMBER = "member"


class Principal:
    """Security principal resolved from authentication credentials."""

    _ROLE_RANK = {
        Role.MEMBER: 0,
        Role.TEAM_MANAGER: 1,
        Role.ORG_ADMIN: 2,
        Role.SYSTEM_ADMIN: 3,
    }

    def __init__(
        self,
        *,
        subject: str,
        global_roles: Iterable[Role] | None = None,
        org_roles: Mapping[int, Role] | None = None,
        team_roles: Mapping[int, Role] | None = None,
        telegram_id: int | None = None,
        telegram_verified: bool = False,
    ) -> None:
        self.subject = subject
        self._global_roles: Set[Role] = {Role(role) for role in (global_roles or [])}
        self._org_roles: Dict[int, Role] = {
            int(org_id): Role(role) for org_id, role in (org_roles or {}).items()
        }
        self._team_roles: Dict[int, Role] = {
            int(team_id): Role(role) for team_id, role in (team_roles or {}).items()
        }
        self.telegram_id = telegram_id
        self.telegram_verified = telegram_verified

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------
    @property
    def roles(self) -> Set[Role]:
        """Return the flattened set of roles associated with the principal."""

        roles = set(self._global_roles)
        roles.update(self._org_roles.values())
        roles.update(self._team_roles.values())
        if self.is_system_admin:
            roles.add(Role.SYSTEM_ADMIN)
        return roles

    @property
    def user_id(self) -> Optional[int]:
        try:
            return int(self.subject)
        except (TypeError, ValueError):
            return None

    @property
    def is_system_admin(self) -> bool:
        return Role.SYSTEM_ADMIN in self._global_roles

    def is_self(self, user_id: int | str | None) -> bool:
        if user_id is None:
            return False
        try:
            return int(user_id) == self.user_id
        except (TypeError, ValueError):
            return False

    # ------------------------------------------------------------------
    # Role evaluation helpers
    # ------------------------------------------------------------------
    @classmethod
    def _rank(cls, role: Role) -> int:
        return cls._ROLE_RANK.get(role, -1)

    @staticmethod
    def _normalize_role_mapping(raw: Mapping[str, str] | Mapping[int, str] | None) -> Dict[int, Role]:
        if not raw:
            return {}
        normalized: Dict[int, Role] = {}
        for key, value in raw.items():
            try:
                normalized[int(key)] = Role(value)
            except (ValueError, TypeError):
                continue
        return normalized

    def has_any_role(self, *required: Role) -> bool:
        if not required:
            return True
        for role in required:
            if role == Role.SYSTEM_ADMIN and self.is_system_admin:
                return True
            if role in self._global_roles:
                return True
            if any(self._role_satisfies(held, role) for held in self._org_roles.values()):
                return True
            if any(self._role_satisfies(held, role) for held in self._team_roles.values()):
                return True
        return False

    def has_org_privilege(self, organization_id: int, required: Role) -> bool:
        if self.is_system_admin:
            return True
        held = self._org_roles.get(int(organization_id))
        if held is None:
            return False
        return self._role_satisfies(held, required)

    def has_team_privilege(self, team_id: int, required: Role) -> bool:
        if self.is_system_admin:
            return True
        held = self._team_roles.get(int(team_id))
        if held is None:
            return False
        return self._role_satisfies(held, required)

    def can_manage_organization(self, organization_id: int) -> bool:
        return self.has_org_privilege(organization_id, Role.ORG_ADMIN)

    def can_manage_team(self, team_id: int, organization_id: int | None = None) -> bool:
        if organization_id is not None and self.has_org_privilege(organization_id, Role.ORG_ADMIN):
            return True
        return self.has_team_privilege(team_id, Role.TEAM_MANAGER)

    def can_manage_billing(self, organization_id: int) -> bool:
        return self.can_manage_organization(organization_id)

    def can_manage_members(self, organization_id: int) -> bool:
        return self.can_manage_organization(organization_id)

    def can_manage_assignments(self, *, organization_id: int | None, team_id: int | None) -> bool:
        if organization_id is not None and self.has_org_privilege(organization_id, Role.ORG_ADMIN):
            return True
        if team_id is not None and self.has_team_privilege(team_id, Role.TEAM_MANAGER):
            return True
        return False

    def can_manage_task(
        self,
        *,
        owner_user_id: int | None,
        organization_id: int | None,
        assigned_team_id: int | None,
    ) -> bool:
        if self.is_system_admin:
            return True
        if organization_id is not None and self.has_org_privilege(organization_id, Role.ORG_ADMIN):
            return True
        if assigned_team_id is not None and self.has_team_privilege(assigned_team_id, Role.TEAM_MANAGER):
            return True
        return self.is_self(owner_user_id)

    @classmethod
    def _role_satisfies(cls, held: Role, required: Role) -> bool:
        return cls._rank(held) >= cls._rank(required)


async def get_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(auth_scheme),
) -> Principal:
    """Resolve the authenticated principal.

    Priority is given to JWT credentials. When no Authorization header is present,
    a verified Telegram identity can be provided via the ``X-Telegram-Id`` and
    ``X-Telegram-Verified`` headers.
    """

    if credentials is not None:
        payload = decode_token(credentials.credentials)
        subject = payload.get("sub")
        if subject is None:
            raise definition_error
        roles = _parse_roles(payload.get("roles", []))
        org_roles = Principal._normalize_role_mapping(payload.get("org_roles"))
        team_roles = Principal._normalize_role_mapping(payload.get("team_roles"))
        telegram_id = payload.get("telegram_id")
        telegram_verified = bool(payload.get("telegram_verified"))
        return Principal(
            subject=str(subject),
            global_roles=roles,
            org_roles=org_roles,
            team_roles=team_roles,
            telegram_id=_safe_int(telegram_id),
            telegram_verified=telegram_verified,
        )

    principal = _principal_from_telegram_headers(request.headers)
    if principal is not None:
        return principal

    raise definition_error


def require_roles(*roles: Role):
    async def dependency(principal: Principal = Depends(get_principal)) -> Principal:
        if not principal.has_any_role(*roles):
            raise definition_error
        return principal

    return dependency


async def require_system_admin(principal: Principal = Depends(get_principal)) -> Principal:
    if not principal.is_system_admin:
        raise definition_error
    return principal


def require_org_role(required_role: Role, org_id_param: str = "org_id"):
    if required_role not in (Role.ORG_ADMIN, Role.TEAM_MANAGER, Role.MEMBER):
        raise ValueError("Organization roles must be one of org_admin, team_manager, or member")

    async def dependency(
        request: Request, principal: Principal = Depends(get_principal)
    ) -> Principal:
        org_id_raw = request.path_params.get(org_id_param) or request.query_params.get(org_id_param)
        if org_id_raw is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "error_org_context_required"},
            )
        try:
            org_id = int(org_id_raw)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "error_invalid_organization"},
            ) from None
        if not principal.has_org_privilege(org_id, required_role):
            raise definition_error
        return principal

    return dependency


def require_team_role(required_role: Role, team_id_param: str = "team_id"):
    if required_role not in (Role.TEAM_MANAGER, Role.MEMBER):
        raise ValueError("Team roles must be team_manager or member")

    async def dependency(
        request: Request, principal: Principal = Depends(get_principal)
    ) -> Principal:
        team_id_raw = request.path_params.get(team_id_param) or request.query_params.get(team_id_param)
        if team_id_raw is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "error_team_context_required"},
            )
        try:
            team_id = int(team_id_raw)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "error_invalid_team"},
            ) from None
        if not principal.has_team_privilege(team_id, required_role):
            raise definition_error
        return principal

    return dependency


def _parse_roles(raw_roles: Iterable[str] | None) -> Set[Role]:
    parsed: Set[Role] = set()
    if not raw_roles:
        return parsed
    for value in raw_roles:
        try:
            parsed.add(Role(value))
        except ValueError:
            continue
    return parsed


def _safe_int(value: object) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _principal_from_telegram_headers(headers: Mapping[str, str]) -> Optional[Principal]:
    telegram_id_raw = headers.get("X-Telegram-Id")
    if not telegram_id_raw:
        return None
    verified_header = headers.get("X-Telegram-Verified", "false").lower()
    if verified_header not in {"true", "1", "yes"}:
        raise definition_error
    telegram_id = _safe_int(telegram_id_raw)
    if telegram_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "error_invalid_telegram"},
        )
    return Principal(
        subject=str(telegram_id),
        global_roles=[Role.MEMBER],
        org_roles={},
        team_roles={},
        telegram_id=telegram_id,
        telegram_verified=True,
    )
