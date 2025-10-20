from datetime import datetime, timedelta, timezone

import pytest

from backend.models import SubscriptionStatus, SubscriptionSubjectType
from backend.services.subscriptions import SubscriptionService


@pytest.mark.asyncio
async def test_subscription_gating(session):
    service = SubscriptionService(session)
    start = datetime.now(timezone.utc)

    subscription = await service.start_trial(
        subject_type=SubscriptionSubjectType.USER,
        subject_id=1,
        days=1,
        start_at=start,
    )
    await session.commit()

    assert subscription.status is SubscriptionStatus.TRIAL
    assert await service.check_access(SubscriptionSubjectType.USER, 1) is True

    subscription.trial_end = datetime.now(timezone.utc) - timedelta(hours=1)
    await session.commit()
    assert await service.check_access(SubscriptionSubjectType.USER, 1) is False
    assert subscription.status is SubscriptionStatus.EXPIRED

    activated = await service.activate(
        subject_type=SubscriptionSubjectType.USER,
        subject_id=1,
        method=subscription.method,
        duration_days=10,
        start_at=start,
    )
    await session.commit()
    assert activated.status is SubscriptionStatus.ACTIVE
    assert await service.check_access(SubscriptionSubjectType.USER, 1) is True

    activated.active_until = datetime.now(timezone.utc) - timedelta(days=1)
    await session.commit()
    assert await service.check_access(SubscriptionSubjectType.USER, 1) is False
    assert activated.status is SubscriptionStatus.EXPIRED
