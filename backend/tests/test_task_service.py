import pytest

from sqlalchemy import select

from backend.models import OrganizationUserRole, TaskAssignment
from backend.services.orgs import OrganizationService
from backend.services.tasks import TaskService
from backend.services.teams import TeamService


@pytest.mark.asyncio
async def test_task_creation_and_assignment_rules(session, user_factory):
    owner = await user_factory(telegram_id=111)
    assignee = await user_factory(telegram_id=222)

    org_service = OrganizationService(session)
    org = await org_service.create(name="Acme", owner_user_id=owner.id)
    await org_service.add_member(org.id, assignee.id, role=OrganizationUserRole.TEAM_MANAGER)

    team_service = TeamService(session)
    team = await team_service.create_team(org.id, "Core Team")
    await team_service.add_member(team.id, assignee.id, role=OrganizationUserRole.TEAM_MANAGER)

    task_service = TaskService(session)
    task = await task_service.create_task(
        title="Draft proposal",
        user_id=owner.id,
        organization_id=org.id,
    )

    task = await task_service.assign_to_user(task.id, assignee.id)
    task = await task_service.assign_to_team(task.id, team.id)

    assert task.user_id == assignee.id
    assert task.organization_id == org.id
    assignment_result = await session.execute(
        select(TaskAssignment.assigned_team_id).where(TaskAssignment.task_id == task.id)
    )
    team_ids = {value for value in assignment_result.scalars() if value is not None}
    assert team_ids == {team.id}

    other_org = await org_service.create(name="Other", owner_user_id=None)
    other_team = await team_service.create_team(other_org.id, "Rogue Team")

    with pytest.raises(ValueError):
        await task_service.assign_to_team(task.id, other_team.id)
