from __future__ import annotations

from datetime import date
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.logging import logger
from backend.models import Project, Team

from .base import ServiceBase


class ProjectService(ServiceBase):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create_project(
        self,
        *,
        organization_id: int,
        name: str,
        description: str | None = None,
        team_id: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        status: str | None = None,
    ) -> Project:
        if team_id is not None:
            team = await self.session.get(Team, team_id)
            if not team:
                raise LookupError("team_not_found")
            if team.organization_id != organization_id:
                raise ValueError("team_outside_organization")

        project = Project(
            organization_id=organization_id,
            name=name,
            description=description,
            team_id=team_id,
            start_date=start_date,
            end_date=end_date,
            status=status,
        )
        self.session.add(project)
        await self.session.commit()
        await self.session.refresh(project)
        logger.info("project.created", project_id=project.id, organization_id=organization_id)
        return project

    async def list(self, organization_id: int | None = None) -> List[Project]:
        query = select(Project)
        if organization_id is not None:
            query = query.where(Project.organization_id == organization_id)
        result = await self.session.execute(query.order_by(Project.id))
        projects = list(result.scalars().all())
        logger.debug(
            "project.list", organization_id=organization_id, count=len(projects)
        )
        return projects

    async def get(self, project_id: int) -> Project:
        project = await self.session.get(Project, project_id)
        if not project:
            raise LookupError("project_not_found")
        return project

    async def set_status(self, project_id: int, status: str | None) -> Project:
        project = await self.get(project_id)
        project.status = status
        await self.session.commit()
        await self.session.refresh(project)
        logger.info("project.status_updated", project_id=project_id, status=status)
        return project

    async def assign_team(self, project_id: int, team_id: int | None) -> Project:
        project = await self.get(project_id)
        if team_id is not None:
            team = await self.session.get(Team, team_id)
            if not team:
                raise LookupError("team_not_found")
            if team.organization_id != project.organization_id:
                raise ValueError("team_outside_organization")
        project.team_id = team_id
        await self.session.commit()
        await self.session.refresh(project)
        logger.info("project.team_assigned", project_id=project_id, team_id=team_id)
        return project

    async def update_dates(
        self, project_id: int, *, start_date: date | None, end_date: date | None
    ) -> Project:
        project = await self.get(project_id)
        project.start_date = start_date
        project.end_date = end_date
        await self.session.commit()
        await self.session.refresh(project)
        logger.info(
            "project.dates_updated",
            project_id=project_id,
            start_date=start_date.isoformat() if start_date else None,
            end_date=end_date.isoformat() if end_date else None,
        )
        return project

    async def update_project(
        self,
        project_id: int,
        *,
        name: str | None = None,
        description: str | None = None,
        team_id: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        status: str | None = None,
    ) -> Project:
        project = await self.get(project_id)
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        if team_id is not None:
            await self.assign_team(project_id, team_id)
            project = await self.get(project_id)
        if start_date is not None or end_date is not None:
            project.start_date = start_date
            project.end_date = end_date
        if status is not None:
            project.status = status
        await self.session.commit()
        await self.session.refresh(project)
        logger.info("project.updated", project_id=project_id)
        return project

    async def delete(self, project_id: int) -> None:
        project = await self.get(project_id)
        await self.session.delete(project)
        await self.session.commit()
        logger.info("project.deleted", project_id=project_id)
