import pytest

from backend.core.settings import settings
from backend.models import IntegrationProvider, IntegrationScope
from backend.services.integrations import IntegrationService
from backend.services.orgs import OrganizationService
from backend.services.tasks import TaskService


@pytest.mark.asyncio
async def test_task_sync_creates_external_links(monkeypatch, session, user_factory):
    monkeypatch.setattr(settings, "enable_eigan_sync", True)
    monkeypatch.setattr(settings, "enable_clickup_sync", True)

    org_service = OrganizationService(session)
    user = await user_factory()
    organization = await org_service.create(
        name="Test Org",
        owner_user_id=user.id,
        plan="pro",
    )

    integration_service = IntegrationService(session)
    for provider in (IntegrationProvider.EIGAN, IntegrationProvider.CLICKUP):
        await integration_service.upsert_setting(
            provider,
            scope=IntegrationScope.ORGANIZATION,
            organization_id=organization.id,
            config={
                "base_url": "https://api.example.com",
                "api_token": f"token-{provider.value}",
            },
        )

    task_service = TaskService(session)
    task = await task_service.create_task(
        title="Sync task",
        description="Ensure sync works",
        user_id=user.id,
        organization_id=organization.id,
    )

    for provider in (IntegrationProvider.EIGAN, IntegrationProvider.CLICKUP):
        link = await integration_service.get_task_link(task.id, provider)
        assert link is not None
        assert link.external_task_id.startswith(provider.value)
        assert link.context["config"]["api_token"] == f"token-{provider.value}"
        payload = link.context["payload"]
        assert payload.get("title", payload.get("name")) == "Sync task"
