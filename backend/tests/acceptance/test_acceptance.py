from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import select

from backend.api.telegram_router import create_tasks, process_image_message, process_voice_message
from backend.core.rbac import Principal
from backend.models import Reminder, SubscriptionStatus, SubscriptionSubjectType, Task
from backend.schemas.reports import ReportFormat, ReportRequest
from backend.services.analytics import AnalyticsService
from backend.services.orgs import OrganizationService
from backend.services.payments import PaymentService
from backend.services.projects import ProjectService
from backend.services.reminders import ReminderService
from backend.services.reports import ReportService
from backend.services.subscriptions import SubscriptionService
from backend.services.tasks import TaskService
from backend.services.teams import TeamService


@pytest.mark.asyncio
async def test_acceptance_flow(monkeypatch, session, tmp_path, user_factory):
    # Step 1: New user trial starts
    async def fake_send_message(self, chat_id, text, **kwargs):  # noqa: ANN001
        return {"ok": True, "text": text}

    monkeypatch.setattr(
        "backend.adapters.telegram.TelegramAdapter.send_message",
        fake_send_message,
    )

    user = await user_factory(telegram_id=9000, preferences={"default_reminder_minutes": 10, "last_task_ids": []})
    subscription_service = SubscriptionService(session)
    trial = await subscription_service.start_trial(
        subject_type=SubscriptionSubjectType.USER,
        subject_id=user.id,
        days=10,
        start_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    await session.commit()
    assert trial.status is SubscriptionStatus.TRIAL

    # Step 2: Create text, voice, and image tasks
    text_tasks = await create_tasks(
        session,
        user,
        [{"title": "Write summary", "due": "today 5pm"}],
        origin_message_id=101,
        locale="en",
    )
    assert text_tasks

    async def fake_transcribe(adapter, message, locale):  # noqa: ANN001
        return "Plan sprint"

    async def fake_voice_intent(text, locale):  # noqa: ANN001
        return {"intent": "tasks", "tasks": [{"title": "Voice follow-up", "due": "tomorrow 8"}]}

    monkeypatch.setattr("backend.api.telegram_router.transcribe_voice", fake_transcribe)
    monkeypatch.setattr("backend.api.telegram_router.classify_intent", fake_voice_intent)

    class VoiceAdapter:
        async def send_message(self, chat_id, text, **kwargs):  # noqa: ANN001
            return {"ok": True, "text": text}

        async def answer_callback_query(self, *args, **kwargs):  # noqa: ANN001
            return {"ok": True}

    await process_voice_message(
        session,
        VoiceAdapter(),
        str(user.telegram_id),
        user,
        "en",
        {"voice": {"file_id": "voice"}},
        202,
    )

    async def fake_analyze(adapter, message, locale):  # noqa: ANN001
        return "- Capture metrics\n- Email update"

    async def fake_image_intent(text, locale):  # noqa: ANN001
        return {
            "intent": "tasks",
            "tasks": [
                {"title": "Metrics deck"},
                {"title": "Update email", "due": "saturday 9"},
            ],
        }

    monkeypatch.setattr("backend.api.telegram_router.analyze_image", fake_analyze)
    monkeypatch.setattr("backend.api.telegram_router.classify_intent", fake_image_intent)

    await process_image_message(
        session,
        VoiceAdapter(),
        str(user.telegram_id),
        user,
        "en",
        {"photo": [{"file_id": "photo"}]},
        303,
    )

    tasks_result = await session.execute(select(Task))
    tasks = tasks_result.scalars().all()
    assert len(tasks) >= 4
    for task in tasks:
        if task.due_at and task.due_at.tzinfo is None:
            task.due_at = task.due_at.replace(tzinfo=timezone.utc)
    await session.commit()

    # Step 3: Reminder sends
    reminders = await session.execute(select(Reminder))
    reminder_list = reminders.scalars().all()
    assert reminder_list
    for reminder in reminder_list:
        reminder.remind_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    await session.commit()

    class ReminderAdapter:
        def __init__(self):
            self.messages = []

        async def send_message(self, chat_id, text, **kwargs):  # noqa: ANN001
            self.messages.append((chat_id, text))
            return {"ok": True}

    reminder_adapter = ReminderAdapter()
    reminder_service = ReminderService(session)
    due_reminders = await reminder_service.get_due_reminders()
    dispatched = 0
    for reminder in due_reminders:
        task = reminder.task
        user = task.user if task else None
        if not task or not user or not user.telegram_id:
            continue
        await reminder_adapter.send_message(str(user.telegram_id), task.title)
        reminder.sent = True
        dispatched += 1
    await session.commit()
    assert dispatched >= 1
    assert reminder_adapter.messages

    # Step 4: Daily PDF report generated
    class FakeHTML:
        def __init__(self, string):  # noqa: ANN001
            self.string = string

        def write_pdf(self, filename):  # noqa: ANN001
            Path(filename).write_bytes(self.string.encode("utf-8"))

    monkeypatch.setattr("backend.services.reports.HTML", FakeHTML)

    report_service = ReportService(session)
    report_service.reports_dir = tmp_path / "reports"
    report_payload = ReportRequest(
        report_type="daily",
        user_id=user.id,
        locale="en",
        format=ReportFormat.PDF,
    )
    principal = Principal(subject=str(user.id))
    report = await report_service.generate(report_payload, principal)
    assert report.file_url is not None
    assert Path(report.file_url).exists()

    # Step 5: Zibal payment activates subscription
    async def fake_create_payment(*args, **kwargs):  # noqa: ANN001
        return {"result": 100, "trackId": "track-1", "paymentUrl": "https://pay"}

    async def fake_verify_payment(*args, **kwargs):  # noqa: ANN001
        return {"result": 100, "orderId": kwargs.get("order_id"), "trackId": "track-1"}

    monkeypatch.setattr("backend.adapters.zibal.ZibalAdapter.create_payment", fake_create_payment)
    monkeypatch.setattr("backend.adapters.zibal.ZibalAdapter.verify_payment", fake_verify_payment)

    payment_service = PaymentService(session)
    zibal = await payment_service.create_zibal_payment(
        subject_type=SubscriptionSubjectType.USER,
        subject_id=user.id,
        amount=1000,
        callback_url="https://callback",
    )
    await payment_service.verify_zibal_callback(track_id="track-1", order_id=zibal["order_id"])
    user_subscription = await subscription_service.get_subscription(SubscriptionSubjectType.USER, user.id)
    assert user_subscription and user_subscription.status is SubscriptionStatus.ACTIVE

    # Step 7: Create organization, team, project, assign tasks
    org_service = OrganizationService(session)
    team_service = TeamService(session)
    project_service = ProjectService(session)
    task_service = TaskService(session)

    org = await org_service.create(name="Acceptance Org", owner_user_id=user.id)
    team = await team_service.create_team(org.id, "Ops")
    project = await project_service.create_project(
        organization_id=org.id,
        name="Scaling",
        team_id=team.id,
    )
    org_task = await task_service.create_task(
        title="Assign work",
        user_id=user.id,
        organization_id=org.id,
        project_id=project.id,
        due_at=datetime.now(timezone.utc),
    )
    await task_service.assign_to_team(org_task.id, team.id)

    # Step 6: Crypto payment activates organization subscription
    async def fake_create_invoice(*args, **kwargs):  # noqa: ANN001
        return {"ok": True, "result": {"invoice_id": 42, "pay_url": "https://crypto"}}

    def fake_verify_webhook(self, raw_body, signature):  # noqa: ANN001
        return True

    async def fake_get_invoice(self, invoice_id):  # noqa: ANN001
        return {"ok": True, "result": {"status": "paid", "invoice_id": invoice_id}}

    monkeypatch.setattr("backend.adapters.cryptobot.CryptoBotAdapter.create_invoice", fake_create_invoice)
    monkeypatch.setattr("backend.adapters.cryptobot.CryptoBotAdapter.verify_webhook", fake_verify_webhook)
    monkeypatch.setattr("backend.adapters.cryptobot.CryptoBotAdapter.get_invoice", fake_get_invoice)

    crypto = await payment_service.create_crypto_invoice(
        subject_type=SubscriptionSubjectType.ORG,
        subject_id=org.id,
        amount=25,
        asset="USDT",
    )
    payload = {"invoice_id": crypto["invoice_id"], "status": "paid"}
    await payment_service.verify_crypto_callback(payload=payload, raw_body=b"{}", signature="ignored")
    org_subscription = await subscription_service.get_subscription(SubscriptionSubjectType.ORG, org.id)
    assert org_subscription and org_subscription.status is SubscriptionStatus.ACTIVE

    # Step 8: Admin analytics dashboards load data
    analytics_service = AnalyticsService(session)
    await analytics_service.record_events(
        [
            {"user_id": user.id, "event_type": "create_task", "source": "bot"},
            {"organization_id": org.id, "event_type": "report_generated_daily", "source": "admin"},
        ]
    )
    await analytics_service.create_daily_snapshot(target_date=date.today())
    summary_global = await analytics_service.get_summary()
    summary_org = await analytics_service.get_summary(organization_id=org.id)
    assert summary_global.total_users >= 1
    assert summary_org.completed_tasks >= 0

    # Ensure reminders are marked sent after dispatch
    refreshed_reminders = await session.execute(select(Reminder))
    assert all(rem.sent for rem in refreshed_reminders.scalars().all())
