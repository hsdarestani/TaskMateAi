from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.logging import logger
from backend.models import (
    Subscription,
    SubscriptionMethod,
    SubscriptionStatus,
    SubscriptionSubjectType,
)

from .base import ServiceBase


class SubscriptionService(ServiceBase):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_subscription(
        self, subject_type: SubscriptionSubjectType, subject_id: int
    ) -> Subscription | None:
        result = await self.session.execute(
            select(Subscription)
            .where(
                Subscription.subject_type == subject_type,
                Subscription.subject_id == subject_id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def start_trial(
        self,
        *,
        subject_type: SubscriptionSubjectType,
        subject_id: int,
        days: int = 10,
        start_at: datetime | None = None,
    ) -> Subscription:
        start_at = start_at or datetime.now(timezone.utc)
        trial_end = start_at + timedelta(days=days)
        subscription = await self.get_subscription(subject_type, subject_id)
        if subscription is None:
            subscription = Subscription(
                subject_type=subject_type,
                subject_id=subject_id,
                status=SubscriptionStatus.TRIAL,
                method=SubscriptionMethod.NONE,
                trial_start=start_at,
                trial_end=trial_end,
                active_until=trial_end,
            )
            self.session.add(subscription)
        else:
            subscription.status = SubscriptionStatus.TRIAL
            subscription.method = SubscriptionMethod.NONE
            subscription.trial_start = start_at
            subscription.trial_end = trial_end
            subscription.active_until = trial_end
        logger.info(
            "subscription.trial_started",
            subject_type=subscription.subject_type.value,
            subject_id=subscription.subject_id,
            trial_end=trial_end.isoformat(),
        )
        return subscription

    async def activate(
        self,
        *,
        subject_type: SubscriptionSubjectType,
        subject_id: int,
        method: SubscriptionMethod,
        duration_days: int = 30,
        start_at: datetime | None = None,
    ) -> Subscription:
        start_at = start_at or datetime.now(timezone.utc)
        subscription = await self.get_subscription(subject_type, subject_id)
        if subscription is None:
            subscription = Subscription(
                subject_type=subject_type,
                subject_id=subject_id,
            )
            self.session.add(subscription)

        baseline = subscription.active_until or start_at
        if baseline < start_at:
            baseline = start_at
        active_until = baseline + timedelta(days=duration_days)

        subscription.status = SubscriptionStatus.ACTIVE
        subscription.method = method
        subscription.active_until = active_until
        if subscription.trial_start is None:
            subscription.trial_start = start_at
        logger.info(
            "subscription.activated",
            subject_type=subscription.subject_type.value,
            subject_id=subscription.subject_id,
            active_until=active_until.isoformat(),
        )
        return subscription

    async def cancel(
        self, subject_type: SubscriptionSubjectType, subject_id: int
    ) -> Subscription | None:
        subscription = await self.get_subscription(subject_type, subject_id)
        if subscription is None:
            return None
        subscription.status = SubscriptionStatus.CANCELED
        logger.info(
            "subscription.canceled",
            subject_type=subscription.subject_type.value,
            subject_id=subscription.subject_id,
        )
        await self.session.commit()
        return subscription

    async def check_access(
        self, subject_type: SubscriptionSubjectType, subject_id: int
    ) -> bool:
        subscription = await self.get_subscription(subject_type, subject_id)
        if subscription is None:
            return False
        if await self._expire_if_needed(subscription):
            await self.session.commit()
            return subscription.status in (SubscriptionStatus.TRIAL, SubscriptionStatus.ACTIVE)
        return subscription.status in (SubscriptionStatus.TRIAL, SubscriptionStatus.ACTIVE)

    async def _expire_if_needed(self, subscription: Subscription) -> bool:
        now = datetime.now(timezone.utc)
        changed = False
        if (
            subscription.status == SubscriptionStatus.TRIAL
            and subscription.trial_end
            and subscription.trial_end < now
        ):
            subscription.status = SubscriptionStatus.EXPIRED
            changed = True
        if (
            subscription.status == SubscriptionStatus.ACTIVE
            and subscription.active_until
            and subscription.active_until < now
        ):
            subscription.status = SubscriptionStatus.EXPIRED
            changed = True
        if changed:
            logger.info(
                "subscription.expired",
                subject_type=subscription.subject_type.value,
                subject_id=subscription.subject_id,
            )
        return changed
