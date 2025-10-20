from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from backend.core.logging import logger
from backend.core.settings import settings
from backend.models import IntegrationProvider, Task
from backend.services.integrations import IntegrationService


def is_enabled() -> bool:
    return settings.enable_clickup_sync


def _map_task_payload(task: Task) -> Dict[str, Any]:
    return {
        "name": task.title,
        "description": task.description or "",
        "due_date": int(task.due_at.timestamp() * 1000) if task.due_at else None,
        "priority": task.priority or "normal",
        "status": task.status or "open",
    }


async def push_task(task: Task, integration_service: IntegrationService) -> None:
    if not is_enabled():
        logger.debug("clickup.sync.disabled")
        return
    if task.organization_id is None:
        logger.debug("clickup.sync.skipped_no_org", task_id=task.id)
        return

    config = await integration_service.resolve_config(
        IntegrationProvider.CLICKUP,
        organization_id=task.organization_id,
    )
    if not config:
        logger.debug(
            "clickup.sync.missing_config",
            task_id=task.id,
            organization_id=task.organization_id,
        )
        return

    payload = _map_task_payload(task)
    external_id = f"clickup-{task.id}"
    await integration_service.link_task(
        task.id,
        IntegrationProvider.CLICKUP,
        external_id=external_id,
        context={"payload": payload, "config": config},
    )
    logger.info(
        "clickup.sync.pushed",
        task_id=task.id,
        external_task_id=external_id,
    )


async def pull_updates(
    since: datetime,
    integration_service: IntegrationService,
    *,
    organization_id: int | None,
) -> list[Dict[str, Any]]:
    if not is_enabled() or organization_id is None:
        return []

    config = await integration_service.resolve_config(
        IntegrationProvider.CLICKUP,
        organization_id=organization_id,
    )
    if not config:
        return []

    logger.debug(
        "clickup.sync.pull_stub",
        since=since.isoformat(),
        organization_id=organization_id,
    )
    return []
