from __future__ import annotations

import json
import re
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import dateparser
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from langdetect import LangDetectException, detect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from backend.adapters.openai_adapter import OpenAIAdapter
from backend.adapters.telegram import TelegramAdapter
from backend.core.i18n import (
    SUPPORTED_LOCALES,
    format_datetime,
    normalize_locale,
    prepare_telegram,
    translate,
)
from backend.core.logging import logger
from backend.core.settings import settings
from backend.core.rate_limit import rate_limiter_dependency
from backend.models import (
    AnalyticsEvent,
    AnalyticsSource,
    Reminder,
    Task,
    User,
)
from backend.services.base import get_session

router = APIRouter(prefix="/telegram", tags=["telegram"])
DEFAULT_USER_PREFERENCES = {
    "default_reminder_minutes": 15,
    "workday_start": "09:00",
    "workday_end": "17:00",
    "onboarding_complete": False,
}


def parse_timezone(value: Optional[str]) -> str:
    candidate = value or settings.default_timezone
    try:
        ZoneInfo(candidate)
        return candidate
    except ZoneInfoNotFoundError:
        logger.warning("telegram.timezone.invalid", timezone=value)
        return settings.default_timezone


def ensure_preferences(user: User) -> Dict[str, Any]:
    prefs = dict(DEFAULT_USER_PREFERENCES)
    if user.preferences:
        prefs.update(user.preferences)
    prefs.setdefault("last_task_ids", [])
    return prefs


async def ensure_user(session: AsyncSession, message_user: Dict[str, Any]) -> tuple[User, bool]:
    telegram_id = message_user.get("id")
    if not telegram_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "error_invalid_user"},
        )
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    created = False
    language = normalize_locale(message_user.get("language_code"))
    timezone_value = parse_timezone(settings.default_timezone)
    if not user:
        user = User(
            telegram_id=telegram_id,
            first_name=message_user.get("first_name"),
            last_name=message_user.get("last_name"),
            username=message_user.get("username"),
            language=language,
            timezone=timezone_value,
            preferences=dict(DEFAULT_USER_PREFERENCES),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        created = True
    else:
        updated = False
        if language and user.language != language:
            user.language = language
            updated = True
        if not user.timezone:
            user.timezone = timezone_value
            updated = True
        merged = ensure_preferences(user)
        if merged != user.preferences:
            user.preferences = merged
            updated = True
        if updated:
            session.add(user)
            await session.commit()
    return user, created


def detect_language_from_text(text: str, fallback: str) -> str:
    try:
        detected = detect(text)
        code = normalize_locale(detected)
        return code or fallback
    except (LangDetectException, TypeError):
        return fallback


def to_user_timezone(dt: datetime, timezone_name: str) -> datetime:
    try:
        tz = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo(settings.default_timezone)
    return dt.astimezone(tz)


def parse_due_date(text: str, timezone_name: str, locale: str) -> Optional[datetime]:
    if not text:
        return None
    settings_kwargs = {
        "RETURN_AS_TIMEZONE_AWARE": True,
        "PREFER_DATES_FROM": "future",
    }
    languages = [locale] if locale in SUPPORTED_LOCALES else None
    try:
        parsed = dateparser.parse(text, languages=languages, settings=settings_kwargs)
    except Exception:  # noqa: BLE001
        logger.debug("telegram.dateparser.error", text=text)
        return None
    if not parsed:
        return None
    if parsed.tzinfo is None:
        try:
            parsed = parsed.replace(tzinfo=ZoneInfo(timezone_name))
        except ZoneInfoNotFoundError:
            parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def split_tasks(text: str) -> List[str]:
    lines = [line.strip() for line in re.split(r"[\n\r]+", text) if line.strip()]
    if len(lines) == 1:
        return lines
    tasks: List[str] = []
    for line in lines:
        cleaned = re.sub(r"^[•\-\d\.\)\s]+", "", line).strip()
        if cleaned:
            tasks.append(cleaned)
    return tasks or lines


async def classify_intent(text: str, locale: str) -> Dict[str, Any]:
    adapter = OpenAIAdapter()
    if adapter.api_key:
        try:
            response = await adapter.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a productivity assistant. Return a compact JSON object with keys "
                            "intent (tasks|events|notes|mark_done|progress|report_today|report_week|settings|help|unknown), "
                            "tasks (list of objects with title and optional due), and note (optional)."
                        ),
                    },
                    {"role": "user", "content": text},
                ],
            )
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            data = json.loads(content)
            data.setdefault("tasks", [])
            data.setdefault("intent", "unknown")
            return data
        except Exception:  # noqa: BLE001
            logger.exception("telegram.intent.openai_failed")
    lowered = text.lower()
    if any(keyword in lowered for keyword in ["/today", "today report", "report today"]):
        return {"intent": "report_today", "tasks": []}
    if any(keyword in lowered for keyword in ["/week", "weekly report", "week report"]):
        return {"intent": "report_week", "tasks": []}
    if "/settings" in lowered or "settings" in lowered:
        return {"intent": "settings", "tasks": []}
    if "/help" in lowered or "help" in lowered:
        return {"intent": "help", "tasks": []}
    if "progress" in lowered:
        return {"intent": "progress", "note": text, "tasks": []}
    if "note" in lowered:
        return {"intent": "notes", "note": text, "tasks": []}
    if "done" in lowered or "complete" in lowered:
        return {"intent": "mark_done", "tasks": []}
    tasks = [{"title": title} for title in split_tasks(text)]
    return {"intent": "tasks", "tasks": tasks}


async def create_tasks(
    session: AsyncSession,
    user: User,
    task_payloads: List[Dict[str, Any]],
    origin_message_id: Optional[int],
    locale: str,
) -> List[Task]:
    created: List[Task] = []
    reminder_offset = int(
        user.preferences.get("default_reminder_minutes", DEFAULT_USER_PREFERENCES["default_reminder_minutes"])
    )
    now_utc = datetime.now(timezone.utc)
    for payload in task_payloads:
        title = payload.get("title") or payload.get("name")
        if not title:
            continue
        due_at = payload.get("due_at")
        if not due_at and (due_text := payload.get("due")):
            due_at = parse_due_date(due_text, user.timezone or settings.default_timezone, locale)
        if isinstance(due_at, str):
            parsed_due = parse_due_date(due_at, user.timezone or settings.default_timezone, locale)
            due_at = parsed_due
        task = Task(
            user_id=user.id,
            organization_id=None,
            project_id=None,
            type=payload.get("type", "task"),
            title=title[:255],
            description=payload.get("description"),
            due_at=due_at,
            status="pending",
            priority=payload.get("priority"),
            source="telegram",
            origin_message_id=str(origin_message_id) if origin_message_id else None,
        )
        session.add(task)
        created.append(task)
    if not created:
        return []
    await session.commit()
    for task in created:
        remind_at = task.due_at - timedelta(minutes=reminder_offset) if task.due_at else now_utc + timedelta(minutes=reminder_offset)
        if remind_at <= now_utc:
            remind_at = now_utc + timedelta(minutes=reminder_offset)
        session.add(Reminder(task_id=task.id, remind_at=remind_at))
    session.add(
        AnalyticsEvent(
            user_id=user.id,
            organization_id=None,
            source=AnalyticsSource.BOT,
            event_type="task_created",
            data={"count": len(created), "origin": "telegram"},
        )
    )
    user.preferences["last_task_ids"] = [task.id for task in created]
    user.preferences.setdefault("onboarding_complete", True)
    session.add(user)
    await session.commit()
    logger.info("telegram.tasks.created", count=len(created), user_id=user.id)
    return created


async def mark_latest_tasks_done(session: AsyncSession, user: User) -> int:
    task_ids = user.preferences.get("last_task_ids", []) if user.preferences else []
    if not task_ids:
        return 0
    result = await session.execute(select(Task).where(Task.id.in_(task_ids)))
    tasks = result.scalars().all()
    if not tasks:
        return 0
    for task in tasks:
        task.status = "completed"
        session.add(task)
    await session.commit()
    return len(tasks)


async def build_report(session: AsyncSession, user: User, locale: str, period: str) -> str:
    tz = user.timezone or settings.default_timezone
    now_local = to_user_timezone(datetime.now(timezone.utc), tz)
    if period == "week":
        start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        end_local = start_local + timedelta(days=7)
    else:
        start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        end_local = start_local + timedelta(days=1)
    start_utc = start_local.astimezone(timezone.utc)
    end_utc = end_local.astimezone(timezone.utc)
    query = select(Task).where(Task.user_id == user.id)
    query = query.where(Task.due_at.is_(None) | Task.due_at.between(start_utc, end_utc))
    result = await session.execute(query)
    tasks = result.scalars().all()
    if period == "week":
        header_key = "report_week_header"
    else:
        header_key = "report_today_header"
    lines = [translate(locale, header_key)]
    if not tasks:
        lines.append(translate(locale, "no_tasks_found"))
        return prepare_telegram(locale, "\n".join(lines))
    pending = sum(1 for task in tasks if task.status != "completed")
    completed = len(tasks) - pending
    lines.append(translate(locale, "report_totals", count=len(tasks)))
    lines.append(translate(locale, "report_completed", count=completed))
    lines.append(translate(locale, "report_pending", count=pending))
    for task in tasks:
        extra = ""
        if task.due_at:
            due_local = to_user_timezone(task.due_at, tz)
            due_text = format_datetime(
                due_local,
                locale,
                timezone_name=tz,
                fmt="short",
            )
            extra = translate(locale, "task_summary_due", due=due_text)
        lines.append(translate(locale, "task_summary_line", title=task.title, extra=extra))
    return prepare_telegram(locale, "\n".join(lines))


async def send_settings_summary(
    session: AsyncSession, adapter: TelegramAdapter, chat_id: str, user: User, locale: str
) -> None:
    prefs = ensure_preferences(user)
    if prefs != user.preferences:
        user.preferences = prefs
        session.add(user)
        await session.commit()
        prefs = user.preferences
    message = translate(
        locale,
        "settings_summary",
        language=locale,
        timezone=user.timezone or settings.default_timezone,
        minutes=prefs.get("default_reminder_minutes", DEFAULT_USER_PREFERENCES["default_reminder_minutes"]),
        start=prefs.get("workday_start", DEFAULT_USER_PREFERENCES["workday_start"]),
        end=prefs.get("workday_end", DEFAULT_USER_PREFERENCES["workday_end"]),
    )
    await adapter.send_message(chat_id=chat_id, text=prepare_telegram(locale, message))
    await adapter.send_message(
        chat_id=chat_id,
        text=prepare_telegram(locale, translate(locale, "settings_prompt")),
    )


async def apply_settings_updates(
    session: AsyncSession,
    adapter: TelegramAdapter,
    chat_id: str,
    user: User,
    locale: str,
    text: str,
) -> bool:
    changes: List[str] = []
    updated = False
    if match := re.search(r"language\s*[=:]\s*(\w+)", text, flags=re.IGNORECASE):
        language = normalize_locale(match.group(1))
        if language != user.language:
            user.language = language
            locale = language
            updated = True
            changes.append(translate(language, "language_confirmed", language=language))
    if match := re.search(r"timezone\s*[=:]\s*([\w/+-]+)", text, flags=re.IGNORECASE):
        timezone_value = parse_timezone(match.group(1))
        if timezone_value != user.timezone:
            user.timezone = timezone_value
            updated = True
            changes.append(translate(locale, "timezone_confirmed", timezone=timezone_value))
    if match := re.search(r"(?:reminder|reminders)\s*[=:]\s*(\d+)", text, flags=re.IGNORECASE):
        minutes = int(match.group(1))
        user.preferences["default_reminder_minutes"] = minutes
        updated = True
        changes.append(translate(locale, "reminder_confirmed", minutes=minutes))
    if match := re.search(r"(?:hours|work(?:\s*hours|_hours)?)\s*[=:]\s*(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})", text, flags=re.IGNORECASE):
        start, end = match.groups()
        user.preferences["workday_start"] = start
        user.preferences["workday_end"] = end
        updated = True
        changes.append(translate(locale, "hours_confirmed", start=start, end=end))
    if not updated:
        return False
    user.preferences.setdefault("onboarding_complete", True)
    session.add(user)
    await session.commit()
    if changes:
        await adapter.send_message(
            chat_id=chat_id,
            text=prepare_telegram(locale, "\n".join(changes)),
        )
    return True


async def ensure_onboarding(
    session: AsyncSession, adapter: TelegramAdapter, chat_id: str, user: User, locale: str
) -> None:
    prefs = ensure_preferences(user)
    if prefs.get("onboarding_complete"):
        return
    prompts: List[str] = [
        translate(locale, "onboarding_language_prompt"),
        translate(locale, "onboarding_timezone_prompt"),
        translate(locale, "onboarding_reminder_prompt", minutes=prefs.get("default_reminder_minutes", DEFAULT_USER_PREFERENCES["default_reminder_minutes"])),
        translate(locale, "onboarding_hours_prompt"),
    ]
    for prompt in prompts:
        await adapter.send_message(chat_id=chat_id, text=prepare_telegram(locale, prompt))
    user.preferences["onboarding_complete"] = True
    session.add(user)
    await session.commit()


def build_inline_keyboard(locale: str) -> Dict[str, Any]:
    return {
        "inline_keyboard": [
            [{"text": translate(locale, "button_done"), "callback_data": "tm_done"}],
            [
                {"text": translate(locale, "button_edit"), "callback_data": "tm_edit"},
                {"text": translate(locale, "button_report_today"), "callback_data": "tm_report_today"},
            ],
            [{"text": translate(locale, "button_settings"), "callback_data": "tm_settings"}],
        ]
    }


async def handle_callback(
    session: AsyncSession,
    adapter: TelegramAdapter,
    payload: Dict[str, Any],
    user: User,
    locale: str,
) -> None:
    callback_id = payload.get("id")
    data = payload.get("data", "")
    chat_id = str(payload.get("message", {}).get("chat", {}).get("id"))
    if data == "tm_done":
        completed = await mark_latest_tasks_done(session, user)
        raw_text = translate(locale, "callback_done_ack") if completed else translate(locale, "out_of_scope")
        text = prepare_telegram(locale, raw_text)
        await adapter.answer_callback_query(callback_id, text=text)
        if chat_id:
            await adapter.send_message(chat_id=chat_id, text=text)
        return
    if data == "tm_report_today":
        report = await build_report(session, user, locale, period="today")
        await adapter.answer_callback_query(callback_id)
        if chat_id:
            await adapter.send_message(chat_id=chat_id, text=report)
        return
    if data == "tm_settings":
        await adapter.answer_callback_query(callback_id)
        if chat_id:
            await send_settings_summary(session, adapter, chat_id, user, locale)
        return
    await adapter.answer_callback_query(
        callback_id,
        text=prepare_telegram(locale, translate(locale, "callback_unknown")),
    )


async def process_text_message(
    session: AsyncSession,
    adapter: TelegramAdapter,
    chat_id: str,
    user: User,
    locale: str,
    text: str,
    message_id: Optional[int],
) -> None:
    if await apply_settings_updates(session, adapter, chat_id, user, locale, text):
        return
    if text.startswith("/"):
        await handle_command(session, adapter, chat_id, user, locale, text)
        return
    intent_data = await classify_intent(text, locale)
    intent = intent_data.get("intent", "unknown")
    if intent in {"report_today", "report_week"}:
        report = await build_report(session, user, locale, period="week" if intent == "report_week" else "today")
        await adapter.send_message(chat_id=chat_id, text=report)
        return
    if intent == "settings":
        await send_settings_summary(session, adapter, chat_id, user, locale)
        return
    if intent == "help":
        await adapter.send_message(
            chat_id=chat_id,
            text=prepare_telegram(locale, translate(locale, "help_message")),
        )
        return
    if intent == "notes":
        session.add(
            AnalyticsEvent(
                user_id=user.id,
                organization_id=None,
                source=AnalyticsSource.BOT,
                event_type="note_logged",
                data={"text": intent_data.get("note", text)},
            )
        )
        await session.commit()
        await adapter.send_message(
            chat_id=chat_id,
            text=prepare_telegram(locale, translate(locale, "notes_ack")),
        )
        return
    if intent == "progress":
        session.add(
            AnalyticsEvent(
                user_id=user.id,
                organization_id=None,
                source=AnalyticsSource.BOT,
                event_type="progress_update",
                data={"text": intent_data.get("note", text)},
            )
        )
        await session.commit()
        await adapter.send_message(
            chat_id=chat_id,
            text=prepare_telegram(locale, translate(locale, "progress_ack")),
        )
        return
    if intent == "mark_done":
        completed = await mark_latest_tasks_done(session, user)
        message = (
            translate(locale, "mark_done_ack")
            if completed
            else translate(locale, "no_tasks_found")
        )
        await adapter.send_message(
            chat_id=chat_id,
            text=prepare_telegram(locale, message),
        )
        return
    tasks_payload = intent_data.get("tasks", [])
    if not tasks_payload:
        await adapter.send_message(
            chat_id=chat_id,
            text=prepare_telegram(locale, translate(locale, "out_of_scope")),
        )
        return
    tasks = await create_tasks(session, user, tasks_payload, message_id, locale)
    if not tasks:
        await adapter.send_message(
            chat_id=chat_id,
            text=prepare_telegram(locale, translate(locale, "out_of_scope")),
        )
        return
    summary_lines = [translate(locale, "tasks_created", count=len(tasks))]
    tz = user.timezone or settings.default_timezone
    for task in tasks:
        extra = ""
        if task.due_at:
            due_local = to_user_timezone(task.due_at, tz)
            due_text = format_datetime(due_local, locale, timezone_name=tz, fmt="short")
            extra = translate(locale, "task_summary_due", due=due_text)
        summary_lines.append(translate(locale, "task_summary_line", title=task.title, extra=extra))
    await adapter.send_message(
        chat_id=chat_id,
        text=prepare_telegram(locale, "\n".join(summary_lines)),
        reply_markup=build_inline_keyboard(locale),
    )


async def handle_command(
    session: AsyncSession,
    adapter: TelegramAdapter,
    chat_id: str,
    user: User,
    locale: str,
    text: str,
) -> None:
    parts = text.strip().split(maxsplit=1)
    command = parts[0].lower()
    argument = parts[1] if len(parts) > 1 else ""
    if command == "/start":
        user.preferences["onboarding_complete"] = False
        session.add(user)
        await session.commit()
        await ensure_onboarding(session, adapter, chat_id, user, locale)
        return
    if command == "/settings":
        await send_settings_summary(session, adapter, chat_id, user, locale)
        return
    if command == "/today":
        report = await build_report(session, user, locale, period="today")
        await adapter.send_message(chat_id=chat_id, text=report)
        return
    if command == "/week":
        report = await build_report(session, user, locale, period="week")
        await adapter.send_message(chat_id=chat_id, text=report)
        return
    if command == "/pay":
        await adapter.send_message(
            chat_id=chat_id,
            text=prepare_telegram(locale, translate(locale, "payment_options")),
        )
        return
    if command == "/join_org":
        await adapter.send_message(
            chat_id=chat_id,
            text=prepare_telegram(
                locale,
                translate(locale, "join_org_ack", code=argument or "-"),
            ),
        )
        return
    if command == "/help":
        await adapter.send_message(
            chat_id=chat_id,
            text=prepare_telegram(locale, translate(locale, "help_message")),
        )
        return
    await adapter.send_message(
        chat_id=chat_id,
        text=prepare_telegram(locale, translate(locale, "out_of_scope")),
    )


async def transcribe_voice(
    adapter: TelegramAdapter, message: Dict[str, Any], locale: str
) -> Optional[str]:
    voice = message.get("voice")
    if not voice:
        return None
    file_id = voice.get("file_id")
    if not file_id:
        return None
    file_meta = await adapter.get_file(file_id)
    if not file_meta or not file_meta.get("file_path"):
        return translate(locale, "voice_placeholder")
    audio_bytes = await adapter.download_file(file_meta["file_path"])
    if not audio_bytes:
        return translate(locale, "voice_placeholder")
    # Placeholder transcription logic; actual Whisper integration would go here.
    logger.info("telegram.voice.received", file_id=file_id, size=len(audio_bytes))
    return translate(locale, "voice_transcribed_placeholder")


async def process_voice_message(
    session: AsyncSession,
    adapter: TelegramAdapter,
    chat_id: str,
    user: User,
    locale: str,
    message: Dict[str, Any],
    message_id: Optional[int],
) -> None:
    transcription = await transcribe_voice(adapter, message, locale)
    if not transcription:
        await adapter.send_message(
            chat_id=chat_id,
            text=prepare_telegram(locale, translate(locale, "out_of_scope")),
        )
        return
    await process_text_message(session, adapter, chat_id, user, locale, transcription, message_id)


async def analyze_image(
    adapter: TelegramAdapter, message: Dict[str, Any], locale: str
) -> Optional[str]:
    photo = message.get("photo")
    document = message.get("document")
    file_id = None
    if photo:
        photo_sorted = sorted(photo, key=lambda item: item.get("file_size", 0), reverse=True)
        file_id = photo_sorted[0].get("file_id") if photo_sorted else None
    elif document:
        file_id = document.get("file_id")
    if not file_id:
        return message.get("caption")
    file_meta = await adapter.get_file(file_id)
    if not file_meta:
        return message.get("caption")
    file_path = file_meta.get("file_path")
    if not file_path:
        return message.get("caption")
    content = await adapter.download_file(file_path)
    if not content:
        return message.get("caption")
    logger.info("telegram.image.received", file_id=file_id, size=len(content))
    # Placeholder OCR/captioning logic.
    return message.get("caption") or translate(locale, "image_placeholder")


async def process_image_message(
    session: AsyncSession,
    adapter: TelegramAdapter,
    chat_id: str,
    user: User,
    locale: str,
    message: Dict[str, Any],
    message_id: Optional[int],
) -> None:
    extracted_text = await analyze_image(adapter, message, locale)
    if not extracted_text:
        await adapter.send_message(
            chat_id=chat_id,
            text=prepare_telegram(locale, translate(locale, "out_of_scope")),
        )
        return
    await process_text_message(session, adapter, chat_id, user, locale, extracted_text, message_id)


@router.post("/webhook/{secret}")
async def telegram_webhook(
    secret: str,
    request: Request,
    background_tasks: BackgroundTasks,  # noqa: ARG001 - reserved for future use
    _: None = Depends(rate_limiter_dependency("telegram:webhook", limit=120, window_seconds=60)),
    session: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    expected_secret = settings.telegram_webhook_secret
    if expected_secret and secret != expected_secret:
        logger.warning("telegram.webhook.invalid_secret")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "error_not_found"},
        )
    header_token = request.headers.get("x-telegram-bot-api-secret-token")
    expected_header_token = settings.telegram_webhook_secret_token
    if expected_header_token and header_token != expected_header_token:
        logger.warning("telegram.webhook.invalid_token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "error_invalid_token"},
        )

    raw_body = await request.body()
    signature = request.headers.get("x-telegram-webhook-signature")
    if signature and settings.telegram_bot_token:
        computed = hmac.new(
            settings.telegram_bot_token.encode("utf-8"),
            msg=raw_body,
            digestmod=hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, computed):
            logger.warning("telegram.webhook.invalid_signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "error_invalid_signature"},
            )

    payload: Dict[str, Any] = {}
    if raw_body:
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except ValueError:
            logger.warning("telegram.webhook.invalid_payload")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "error_invalid_payload"},
            )
    logger.info("telegram.webhook.received", payload=payload)
    adapter = TelegramAdapter()

    if callback := payload.get("callback_query"):
        telegram_user = callback.get("from", {})
        user, _ = await ensure_user(session, telegram_user)
        locale = normalize_locale(user.language)
        await handle_callback(session, adapter, callback, user, locale)
        return {"ok": True}

    message = payload.get("message") or payload.get("edited_message")
    if not message:
        return {"ok": True}
    telegram_user = message.get("from") or message.get("chat")
    if not telegram_user:
        return {"ok": True}
    user, created = await ensure_user(session, telegram_user)
    locale = normalize_locale(user.language)
    chat_id = str(message.get("chat", {}).get("id"))
    message_id = message.get("message_id")
    if created:
        try:
            detected_locale = detect_language_from_text(message.get("text", ""), locale)
            if detected_locale != user.language:
                user.language = detected_locale
                locale = detected_locale
                session.add(user)
                await session.commit()
        except Exception:  # noqa: BLE001
            pass
    await ensure_onboarding(session, adapter, chat_id, user, locale)

    if "voice" in message:
        await process_voice_message(session, adapter, chat_id, user, locale, message, message_id)
    elif "photo" in message or "document" in message:
        await process_image_message(session, adapter, chat_id, user, locale, message, message_id)
    elif text := message.get("text"):
        await process_text_message(session, adapter, chat_id, user, locale, text, message_id)
    else:
        await adapter.send_message(
            chat_id=chat_id,
            text=prepare_telegram(locale, translate(locale, "out_of_scope")),
        )
    return {"ok": True}
