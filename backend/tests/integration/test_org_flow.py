from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import select

from backend.core.rbac import Principal, Role
from backend.models import OrganizationUserRole, Task
from backend.schemas.reports import ReportFormat, ReportRequest
from backend.services.orgs import OrganizationService
from backend.services.projects import ProjectService
from backend.services.reports import ReportService
from backend.services.tasks import TaskService
from backend.services.teams import TeamService


@pytest.mark.asyncio
async def test_org_flow_creates_report(monkeypatch, session, tmp_path, user_factory):
    owner = await user_factory(telegram_id=321, preferences={"default_reminder_minutes": 15, "last_task_ids": []})
    member = await user_factory(telegram_id=654, preferences={"default_reminder_minutes": 15, "last_task_ids": []})

    org_service = OrganizationService(session)
    org = await org_service.create(name="TaskMate Org", owner_user_id=owner.id)

    team_service = TeamService(session)
    team = await team_service.create_team(org.id, "Velocity")

    invite = await org_service.generate_invite_code(org.id, OrganizationUserRole.MEMBER)
    await org_service.join_with_invite(invite, member.id)

    project_service = ProjectService(session)
    project = await project_service.create_project(
        organization_id=org.id,
        name="Launch",
        description="Go-live",
        team_id=team.id,
    )

    task_service = TaskService(session)
    task = await task_service.create_task(
        title="Prep brief",
        user_id=owner.id,
        organization_id=org.id,
        project_id=project.id,
        due_at=datetime.now(timezone.utc),
    )
    task.created_at = datetime.now(timezone.utc)
    await session.commit()
    await task_service.assign_to_user(task.id, member.id)
    await task_service.assign_to_team(task.id, team.id)

    principal = Principal(subject=str(owner.id), org_roles={org.id: Role.ORG_ADMIN})
    report_service = ReportService(session)
    report_service.reports_dir = Path(tmp_path)

    task_rows = await session.execute(select(Task))
    for item in task_rows.scalars():
        if item.due_at and item.due_at.tzinfo is None:
            item.due_at = item.due_at.replace(tzinfo=timezone.utc)
    await session.commit()

    payload = ReportRequest(
        report_type="daily",
        organization_id=org.id,
        locale="en",
        format=ReportFormat.CSV,
    )

    response = await report_service.generate(payload, principal)
    assert response.scope.value == "organization"
    assert response.metrics is not None
    assert response.metrics.throughput >= 1
    assert response.file_url is not None
    assert Path(response.file_url).exists()
