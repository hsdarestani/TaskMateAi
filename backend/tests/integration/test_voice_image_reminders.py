from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from backend.api.telegram_router import process_image_message, process_voice_message
from backend.models import Reminder, Task, User
from backend.services.reminders import ReminderService


class DummyAdapter:
    def __init__(self):
        self.messages: list[tuple[str, str]] = []

    async def send_message(self, chat_id: str, text: str, **kwargs):
        self.messages.append((chat_id, text))

    async def answer_callback_query(self, *args, **kwargs):  # pragma: no cover - not used
        return {"ok": True}


@pytest.mark.asyncio
async def test_voice_pipeline_creates_task(monkeypatch, session, user_factory):
    user = await user_factory(telegram_id=999, preferences={"default_reminder_minutes": 15, "last_task_ids": []})
    adapter = DummyAdapter()

    async def fake_transcribe(adapter_instance, message, locale):  # noqa: ANN001
        return "Voice captured task"

    async def fake_classify(text, locale):  # noqa: ANN001
        return {"intent": "tasks", "tasks": [{"title": "Voice Task", "due": "today 6pm"}]}

    monkeypatch.setattr("backend.api.telegram_router.transcribe_voice", fake_transcribe)
    monkeypatch.setattr("backend.api.telegram_router.classify_intent", fake_classify)

    message = {"voice": {"file_id": "abc"}}
    await process_voice_message(session, adapter, "999", user, "en", message, 42)

    result = await session.execute(select(Task))
    tasks = result.scalars().all()
    assert len(tasks) == 1
    assert tasks[0].title == "Voice Task"
    assert adapter.messages


@pytest.mark.asyncio
async def test_image_pipeline_creates_multiple_tasks(monkeypatch, session, user_factory):
    user = await user_factory(telegram_id=1000, preferences={"default_reminder_minutes": 10, "last_task_ids": []})
    adapter = DummyAdapter()

    async def fake_analyze(adapter_instance, message, locale):  # noqa: ANN001
        return "- First item\n- Second item"

    async def fake_classify(text, locale):  # noqa: ANN001
        return {
            "intent": "tasks",
            "tasks": [
                {"title": "First extracted"},
                {"title": "Second extracted", "due": "tomorrow 9"},
            ],
        }

    monkeypatch.setattr("backend.api.telegram_router.analyze_image", fake_analyze)
    monkeypatch.setattr("backend.api.telegram_router.classify_intent", fake_classify)

    message = {"photo": [{"file_id": "img", "file_size": 10}]}
    await process_image_message(session, adapter, "1000", user, "en", message, 77)

    result = await session.execute(select(Task).order_by(Task.id))
    tasks = result.scalars().all()
    assert [task.title for task in tasks] == ["First extracted", "Second extracted"]
    assert adapter.messages


class ReminderAdapter(DummyAdapter):
    async def send_message(self, chat_id: str, text: str, **kwargs):
        await super().send_message(chat_id, text, **kwargs)
        return {"ok": True}


@pytest.mark.asyncio
async def test_reminder_dispatch_sends_message(monkeypatch, session):
    user = User(
        telegram_id=555,
        first_name="Remind",
        language="en",
        timezone="Europe/Stockholm",
        preferences={"default_reminder_minutes": 15},
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    task = Task(
        title="Reminder Task",
        user_id=user.id,
        due_at=datetime.now(timezone.utc),
        status="pending",
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)

    reminder = Reminder(
        task_id=task.id,
        remind_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        sent=False,
    )
    session.add(reminder)
    await session.commit()

    adapter = ReminderAdapter()
    service = ReminderService(session)
    due = await service.get_due_reminders()
    processed = 0
    for entry in due:
        task = entry.task
        user = task.user if task else None
        if not task or not user or not user.telegram_id:
            continue
        await adapter.send_message(str(user.telegram_id), task.title)
        entry.sent = True
        processed += 1
    await session.commit()

    assert processed == 1
    assert adapter.messages

    updated = await session.get(Reminder, reminder.id)
    assert updated.sent is True
