from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from backend.core.logging import logger
from backend.core.settings import settings
from backend.models import IntegrationProvider, Task
from backend.services.integrations import IntegrationService


def is_enabled() -> bool:
    return settings.enable_eigan_sync


def _map_task_payload(task: Task) -> Dict[str, Any]:
    return {
        "title": task.title,
        "description": task.description or "",
        "due_at": task.due_at.isoformat() if task.due_at else None,
        "priority": task.priority or "normal",
        "status": task.status or "pending",
        "source": task.source or "internal",
    }


async def push_task(task: Task, integration_service: IntegrationService) -> None:
    if not is_enabled():
        logger.debug("eigan.sync.disabled")
        return
    if task.organization_id is None:
        logger.debug("eigan.sync.skipped_no_org", task_id=task.id)
        return

    config = await integration_service.resolve_config(
        IntegrationProvider.EIGAN,
        organization_id=task.organization_id,
    )
    if not config:
        logger.debug(
            "eigan.sync.missing_config",
            task_id=task.id,
            organization_id=task.organization_id,
        )
        return

    payload = _map_task_payload(task)
    external_id = f"eigan-{task.id}"
    await integration_service.link_task(
        task.id,
        IntegrationProvider.EIGAN,
        external_id=external_id,
        context={"payload": payload, "config": config},
    )
    logger.info(
        "eigan.sync.pushed",
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
        IntegrationProvider.EIGAN,
        organization_id=organization_id,
    )
    if not config:
        return []

    logger.debug(
        "eigan.sync.pull_stub",
        since=since.isoformat(),
        organization_id=organization_id,
    )
    return []
