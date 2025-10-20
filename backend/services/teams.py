from __future__ import annotations

from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.logging import logger
from backend.models import OrganizationUser, OrganizationUserRole, Team, User

from .base import ServiceBase


class TeamService(ServiceBase):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create_team(self, organization_id: int, name: str) -> Team:
        team = Team(organization_id=organization_id, name=name)
        self.session.add(team)
        await self.session.commit()
        await self.session.refresh(team)
        logger.info("team.created", team_id=team.id, organization_id=organization_id)
        return team

    async def list(self, organization_id: int) -> List[Team]:
        result = await self.session.execute(
            select(Team).where(Team.organization_id == organization_id).order_by(Team.id)
        )
        teams = list(result.scalars().all())
        logger.debug("team.list", organization_id=organization_id, count=len(teams))
        return teams

    async def get(self, team_id: int) -> Team:
        team = await self.session.get(Team, team_id)
        if not team:
            raise LookupError("team_not_found")
        return team

    async def add_member(
        self,
        team_id: int,
        user_id: int,
        *,
        role: OrganizationUserRole = OrganizationUserRole.MEMBER,
    ) -> None:
        team = await self.get(team_id)
        membership = await self._get_membership(team.organization_id, user_id)
        if membership is None:
            raise ValueError("user_not_in_organization")
        if role and membership.role != role:
            membership.role = role

        user = membership.user or await self.session.get(User, user_id)
        preferences = dict(user.preferences or {})
        team_ids = set(preferences.get("team_ids", []))
        if team_id not in team_ids:
            team_ids.add(team_id)
            preferences["team_ids"] = sorted(team_ids)
            user.preferences = preferences

        await self.session.commit()
        logger.info("team.member_added", team_id=team_id, user_id=user_id, role=role.value)

    async def remove_member(self, team_id: int, user_id: int) -> None:
        team = await self.get(team_id)
        membership = await self._get_membership(team.organization_id, user_id)
        if membership is None:
            return

        user = membership.user or await self.session.get(User, user_id)
        preferences = dict(user.preferences or {})
        team_ids = set(preferences.get("team_ids", []))
        if team_id in team_ids:
            team_ids.remove(team_id)
            preferences["team_ids"] = sorted(team_ids)
            user.preferences = preferences
            await self.session.commit()
            logger.info("team.member_removed", team_id=team_id, user_id=user_id)

    async def update_team(self, team_id: int, *, name: str | None = None) -> Team:
        team = await self.get(team_id)
        if name is not None:
            team.name = name
        await self.session.commit()
        await self.session.refresh(team)
        logger.info("team.updated", team_id=team_id, name=name)
        return team

    async def delete(self, team_id: int) -> None:
        team = await self.get(team_id)
        await self.session.delete(team)
        await self.session.commit()
        logger.info("team.deleted", team_id=team_id)

    async def list_members(self, team_id: int) -> List[User]:
        team = await self.get(team_id)
        result = await self.session.execute(
            select(User)
            .join(OrganizationUser, OrganizationUser.user_id == User.id)
            .where(OrganizationUser.organization_id == team.organization_id)
            .order_by(User.id)
        )
        members: List[User] = []
        for user in result.scalars().all():
            team_ids = set((user.preferences or {}).get("team_ids", []))
            if team_id in team_ids:
                members.append(user)
        logger.debug("team.members_listed", team_id=team_id, count=len(members))
        return members

    async def _get_membership(
        self, organization_id: int, user_id: int
    ) -> OrganizationUser | None:
        result = await self.session.execute(
            select(OrganizationUser)
            .where(
                OrganizationUser.organization_id == organization_id,
                OrganizationUser.user_id == user_id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()
