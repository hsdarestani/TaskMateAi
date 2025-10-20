from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.adapters import clickup as clickup_adapter
from backend.adapters import eigan as eigan_adapter
from backend.core.logging import logger
from backend.models import Task, TaskAssignment, Team
from backend.schemas.tasks import TaskCreate, TaskUpdate

from .base import ServiceBase
from .integrations import IntegrationService


class TaskService(ServiceBase):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self._integration_service = IntegrationService(session)

    async def create_task(
        self,
        *,
        title: str,
        description: str | None = None,
        user_id: int | None = None,
        organization_id: int | None = None,
        project_id: int | None = None,
        type: str | None = None,
        due_at: datetime | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        status: str = "pending",
        priority: str | None = None,
        source: str | None = None,
        origin_message_id: str | None = None,
    ) -> Task:
        task = Task(
            title=title,
            description=description,
            user_id=user_id,
            organization_id=organization_id,
            project_id=project_id,
            type=type,
            due_at=due_at,
            start_at=start_at,
            end_at=end_at,
            status=status,
            priority=priority,
            source=source,
            origin_message_id=origin_message_id,
        )
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        logger.info("task.created", task_id=task.id, title=title)
        await self._sync_integrations(task)
        return task

    async def create_for_principal(
        self,
        payload: TaskCreate,
        *,
        owner_user_id: int | None,
    ) -> Task:
        task = await self.create_task(
            title=payload.title,
            description=payload.description,
            user_id=owner_user_id,
            organization_id=payload.organization_id,
            project_id=payload.project_id,
            type=payload.type,
            due_at=payload.due_at,
            start_at=payload.start_at,
            end_at=payload.end_at,
            status=payload.status or "pending",
            priority=payload.priority,
            source=payload.source,
            origin_message_id=payload.origin_message_id,
        )

        if payload.assignee_id and payload.assignee_id != owner_user_id:
            await self.assign_to_user(task.id, payload.assignee_id)
        if payload.assigned_team_id is not None:
            await self.assign_to_team(task.id, payload.assigned_team_id)
        await self.session.refresh(task)
        return task

    async def get(self, task_id: int) -> Task:
        task = await self.session.get(Task, task_id)
        if not task:
            raise LookupError("task_not_found")
        return task

    async def update_task(self, task_id: int, **changes: Any) -> Task:
        task = await self.get(task_id)
        allowed_fields = {
            "title",
            "description",
            "organization_id",
            "project_id",
            "type",
            "due_at",
            "start_at",
            "end_at",
            "status",
            "priority",
            "source",
            "origin_message_id",
        }
        for field, value in changes.items():
            if field in allowed_fields:
                setattr(task, field, value)
        await self.session.commit()
        await self.session.refresh(task)
        logger.info("task.updated", task_id=task_id, fields=list(changes.keys()))
        await self._sync_integrations(task)
        return task

    async def update_from_payload(self, task_id: int, payload: TaskUpdate) -> Task:
        data = payload.model_dump(exclude_unset=True)
        assignee_id = data.pop("assignee_id", None)
        assigned_team_id = data.pop("assigned_team_id", None)
        task = await self.update_task(task_id, **data)
        if assignee_id is not None:
            await self.assign_to_user(task_id, assignee_id)
            await self.session.refresh(task)
        if assigned_team_id is not None:
            await self.assign_to_team(task_id, assigned_team_id)
            await self.session.refresh(task)
        return task

    async def assign_to_user(self, task_id: int, user_id: int) -> Task:
        task = await self.get(task_id)
        task.user_id = user_id
        await self._ensure_assignment(task_id, user_id=user_id)
        await self.session.commit()
        await self.session.refresh(task)
        logger.info("task.assigned_user", task_id=task_id, user_id=user_id)
        return task

    async def assign_to_team(self, task_id: int, team_id: int) -> Task:
        task = await self.get(task_id)
        team = await self.session.get(Team, team_id)
        if not team:
            raise LookupError("team_not_found")
        if task.organization_id and team.organization_id != task.organization_id:
            raise ValueError("team_outside_organization")
        if task.organization_id is None:
            task.organization_id = team.organization_id
        await self._ensure_assignment(task_id, team_id=team_id)
        await self.session.commit()
        await self.session.refresh(task)
        logger.info("task.assigned_team", task_id=task_id, team_id=team_id)
        return task

    async def mark_done(self, task_id: int) -> Task:
        task = await self.get(task_id)
        task.status = "done"
        task.end_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(task)
        logger.info("task.completed", task_id=task_id)
        await self._sync_integrations(task)
        return task

    async def list_tasks(
        self,
        *,
        user_id: int | None = None,
        organization_id: int | None = None,
        team_id: int | None = None,
        project_id: int | None = None,
        status: str | None = None,
    ) -> List[Task]:
        query = select(Task).distinct().outerjoin(TaskAssignment)

        filters: list[Any] = []
        if user_id is not None:
            filters.append(
                or_(
                    Task.user_id == user_id,
                    TaskAssignment.assigned_to_user_id == user_id,
                )
            )
        if organization_id is not None:
            filters.append(Task.organization_id == organization_id)
        if project_id is not None:
            filters.append(Task.project_id == project_id)
        if team_id is not None:
            query = query.where(TaskAssignment.assigned_team_id == team_id)
        if status is not None:
            filters.append(Task.status == status)

        if filters:
            query = query.where(and_(*filters))

        result = await self.session.execute(
            query.order_by(Task.due_at, Task.id).execution_options(populate_existing=True)
        )
        tasks = list(result.scalars().unique().all())
        logger.debug(
            "task.list",
            user_id=user_id,
            organization_id=organization_id,
            team_id=team_id,
            project_id=project_id,
            count=len(tasks),
        )
        return tasks

    async def _sync_integrations(self, task: Task) -> None:
        if task.organization_id is None:
            return
        if eigan_adapter.is_enabled():
            await eigan_adapter.push_task(task, self._integration_service)
        if clickup_adapter.is_enabled():
            await clickup_adapter.push_task(task, self._integration_service)

    async def _ensure_assignment(
        self,
        task_id: int,
        *,
        user_id: int | None = None,
        team_id: int | None = None,
    ) -> TaskAssignment:
        if user_id is None and team_id is None:
            raise ValueError("assignment_target_required")
        conditions: list[Any] = [TaskAssignment.task_id == task_id]
        if user_id is not None:
            conditions.append(TaskAssignment.assigned_to_user_id == user_id)
        if team_id is not None:
            conditions.append(TaskAssignment.assigned_team_id == team_id)

        result = await self.session.execute(select(TaskAssignment).where(*conditions))
        assignment = result.scalar_one_or_none()
        if assignment is None:
            assignment = TaskAssignment(
                task_id=task_id,
                assigned_to_user_id=user_id,
                assigned_team_id=team_id,
            )
            self.session.add(assignment)
        else:
            if user_id is not None:
                assignment.assigned_to_user_id = user_id
            if team_id is not None:
                assignment.assigned_team_id = team_id
        return assignment
