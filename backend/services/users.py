from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.logging import logger
from backend.core.settings import settings
from backend.models import (
    OrganizationUser,
    SubscriptionSubjectType,
    User,
)

from .base import ServiceBase
from .subscriptions import SubscriptionService


class UserService(ServiceBase):
    """Domain operations for end users interacting with the assistant."""

    trial_days: int = 10

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self._subscription_service = SubscriptionService(session)

    async def list(self, organization_id: int | None = None) -> List[User]:
        query = select(User)
        if organization_id is not None:
            query = (
                query.join(OrganizationUser)
                .where(OrganizationUser.organization_id == organization_id)
            )
        result = await self.session.execute(query.order_by(User.id))
        return list(result.scalars().all())

    async def get(self, user_id: int) -> User:
        user = await self.session.get(User, user_id)
        if not user:
            raise LookupError("user_not_found")
        return user

    async def get_by_telegram(self, telegram_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def create_user(
        self,
        *,
        telegram_id: int | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        username: str | None = None,
        language: str | None = None,
        timezone_name: str | None = None,
        preferences: Dict[str, Any] | None = None,
    ) -> User:
        """Create a user and provision a 10-day trial subscription."""

        if telegram_id is not None:
            existing = await self.get_by_telegram(telegram_id)
            if existing:
                raise ValueError("user_already_exists")

        user = User(
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            language=language or settings.default_locale,
            timezone=timezone_name or settings.default_timezone,
            preferences=preferences or {},
        )
        self.session.add(user)
        await self.session.flush()
        await self._start_trial_for(user)
        await self.session.commit()
        await self.session.refresh(user)
        logger.info("user.created", user_id=user.id, telegram_id=telegram_id)
        return user

    async def update_user(
        self,
        user_id: int,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        username: str | None = None,
        language: str | None = None,
        timezone_name: str | None = None,
        preferences: Dict[str, Any] | None = None,
    ) -> User:
        user = await self.get(user_id)

        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if username is not None:
            user.username = username
        if language is not None:
            user.language = language
        if timezone_name is not None:
            user.timezone = timezone_name
        if preferences is not None:
            merged = dict(user.preferences or {})
            merged.update(preferences)
            user.preferences = merged

        await self.session.commit()
        await self.session.refresh(user)
        logger.info("user.updated", user_id=user.id)
        return user

    async def delete_user(self, user_id: int) -> None:
        await self.get(user_id)
        await self.session.execute(delete(User).where(User.id == user_id))
        await self.session.commit()
        logger.info("user.deleted", user_id=user_id)

    async def set_language(self, user_id: int, language: str) -> User:
        return await self.update_user(user_id, language=language)

    async def set_timezone(self, user_id: int, timezone_name: str) -> User:
        return await self.update_user(user_id, timezone_name=timezone_name)

    async def update_preferences(
        self, user_id: int, *, preferences: Dict[str, Any]
    ) -> User:
        return await self.update_user(user_id, preferences=preferences)

    async def touch_trial(self, user_id: int) -> None:
        """Ensure a user has an active trial period."""

        user = await self.get(user_id)
        await self._start_trial_for(user)
        await self.session.commit()

    async def _start_trial_for(self, user: User) -> None:
        now = datetime.now(timezone.utc)
        await self._subscription_service.start_trial(
            subject_type=SubscriptionSubjectType.USER,
            subject_id=user.id,
            days=self.trial_days,
            start_at=now,
        )

    async def set_default_preferences(
        self, user_id: int, *, default_reminders: Iterable[int] | None = None, work_hours: Dict[str, Any] | None = None
    ) -> User:
        prefs: Dict[str, Any] = {}
        if default_reminders is not None:
            prefs["default_reminder_minutes"] = list(default_reminders)
        if work_hours is not None:
            prefs["work_hours"] = work_hours
        if not prefs:
            return await self.get(user_id)
        return await self.update_user(user_id, preferences=prefs)
