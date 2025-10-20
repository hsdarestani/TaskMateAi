from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError

from backend.core.logging import logger
from backend.models import (
    IntegrationProvider,
    IntegrationScope,
    IntegrationSetting,
    TaskExternalLink,
)

from .base import ServiceBase


class IntegrationService(ServiceBase):
    async def get_setting(
        self,
        provider: IntegrationProvider,
        *,
        scope: IntegrationScope | None = None,
        organization_id: int | None = None,
    ) -> IntegrationSetting | None:
        """Fetch a persisted integration configuration."""

        stmt = select(IntegrationSetting).where(
            IntegrationSetting.provider == provider
        )

        if scope is IntegrationScope.ORGANIZATION or (
            scope is None and organization_id is not None
        ):
            scoped_stmt = stmt.where(
                and_(
                    IntegrationSetting.scope == IntegrationScope.ORGANIZATION,
                    IntegrationSetting.organization_id == organization_id,
                )
            )
            result = await self.session.execute(scoped_stmt.limit(1))
            entry = result.scalar_one_or_none()
            if entry is not None:
                return entry

        if scope is IntegrationScope.SYSTEM or scope is None:
            system_stmt = stmt.where(
                IntegrationSetting.scope == IntegrationScope.SYSTEM
            )
            result = await self.session.execute(system_stmt.limit(1))
            return result.scalar_one_or_none()

        return None

    async def upsert_setting(
        self,
        provider: IntegrationProvider,
        *,
        scope: IntegrationScope,
        organization_id: int | None = None,
        config: dict[str, Any],
    ) -> IntegrationSetting:
        if scope is IntegrationScope.ORGANIZATION and organization_id is None:
            raise ValueError("organization_id_required")
        if scope is IntegrationScope.SYSTEM:
            organization_id = None

        existing = await self.get_setting(
            provider,
            scope=scope,
            organization_id=organization_id,
        )

        if existing is None:
            entry = IntegrationSetting(
                provider=provider,
                scope=scope,
                organization_id=organization_id,
                config=config,
            )
            self.session.add(entry)
        else:
            entry = existing
            entry.config = config

        try:
            await self.session.commit()
        except IntegrityError as exc:  # pragma: no cover - defensive
            await self.session.rollback()
            raise exc

        await self.session.refresh(entry)
        logger.info(
            "integration.settings.upsert",
            provider=provider.value,
            scope=scope.value,
            organization_id=organization_id,
        )
        return entry

    async def resolve_config(
        self,
        provider: IntegrationProvider,
        *,
        organization_id: int | None = None,
    ) -> dict[str, Any] | None:
        entry = await self.get_setting(provider, organization_id=organization_id)
        return entry.config if entry else None

    async def link_task(
        self,
        task_id: int,
        provider: IntegrationProvider,
        *,
        external_id: str,
        context: dict[str, Any] | None = None,
    ) -> TaskExternalLink:
        stmt = select(TaskExternalLink).where(
            and_(
                TaskExternalLink.task_id == task_id,
                TaskExternalLink.provider == provider,
            )
        )
        result = await self.session.execute(stmt.limit(1))
        link = result.scalar_one_or_none()

        if link is None:
            link = TaskExternalLink(
                task_id=task_id,
                provider=provider,
                external_task_id=external_id,
                context=context or {},
                synced_at=datetime.now(timezone.utc),
            )
            self.session.add(link)
        else:
            link.external_task_id = external_id
            link.context = context or link.context
            link.synced_at = datetime.now(timezone.utc)

        await self.session.commit()
        await self.session.refresh(link)
        logger.debug(
            "integration.task.linked",
            task_id=task_id,
            provider=provider.value,
            external_task_id=external_id,
        )
        return link

    async def get_task_link(
        self, task_id: int, provider: IntegrationProvider
    ) -> TaskExternalLink | None:
        stmt = select(TaskExternalLink).where(
            and_(
                TaskExternalLink.task_id == task_id,
                TaskExternalLink.provider == provider,
            )
        )
        result = await self.session.execute(stmt.limit(1))
        return result.scalar_one_or_none()
