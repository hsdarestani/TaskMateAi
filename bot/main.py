from __future__ import annotations

import logging
from pathlib import Path
from tempfile import NamedTemporaryFile
from textwrap import dedent
from typing import Optional

from telegram import File, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .config import SettingsError, load_settings
from .storage import WorkspaceStorage
from .trello_client import TrelloClient, TrelloError
from .workspace import Workspace, WorkspaceManager


logging.basicConfig(
    format="%(asctime)s %(name)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
LOGGER = logging.getLogger(__name__)


class BotHandlers:
    def __init__(self, workspace_manager: WorkspaceManager, trello: TrelloClient) -> None:
        self._workspace_manager = workspace_manager
        self._trello = trello

    def _ensure_workspace(self, user_id: int) -> Workspace:
        return self._workspace_manager.ensure_workspace(user_id)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user:
            return
        workspace = self._ensure_workspace(user.id)
        intro = dedent(
            f"""
            سلام {user.first_name or user.username or "دوست عزیز"} 👋

            برایت یک برد خصوصی در Trello ساختم تا پیام‌هایت را به تسک تبدیل کنم.
            از این به بعد هر پیام متنی، عکس یا ویسی که بفرستی را به عنوان تسک جدید در لیست Inbox همان برد ذخیره می‌کنم.
            می‌توانی پیام را با این ساختار بفرستی تا توضیحات بیشتری به کارت اضافه شود:

            عنوان تسک
            ---
            توضیحات تکمیلی

            اگر فقط یک خط بفرستی همان خط عنوان خواهد شد.
            برای مشاهده کارت‌ها وارد Trello شو و برد «{workspace.board_name}» را باز کن.
            """
        ).strip()
        await update.message.reply_text(intro)

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.message
        user = update.effective_user
        if not message or not user:
            return
        text = message.text or ""
        if not text.strip():
            await message.reply_text("پیام متنی خالی بود و به کارت تبدیل نشد.")
            return
        workspace = self._ensure_workspace(user.id)
        card_name, card_description = _split_card_content(text)
        try:
            card = self._trello.create_card(
                workspace.inbox_list_id, name=card_name, desc=card_description
            )
        except TrelloError:
            LOGGER.exception("Could not create card for text message")
            await message.reply_text(
                "در اتصال به Trello خطایی رخ داد. لطفاً بعداً دوباره تلاش کن."
            )
            return
        await message.reply_text(
            f"تسک جدید با شناسه {card.get('idShort', card.get('id'))} ثبت شد."
        )

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.message
        user = update.effective_user
        if not message or not user or not message.photo:
            return
        photo = message.photo[-1]
        telegram_file = await photo.get_file()
        temp_path = await _download_temp(telegram_file, suffix=".jpg")
        if temp_path is None:
            await message.reply_text("دریافت فایل از تلگرام ناموفق بود.")
            return
        workspace = self._ensure_workspace(user.id)
        card_title = message.caption or "عکس جدید"
        card_name, card_description = _split_card_content(card_title)
        try:
            card = self._trello.create_card(
                workspace.inbox_list_id,
                name=f"📸 {card_name}",
                desc=card_description,
            )
            self._trello.attach_file(card["id"], temp_path, temp_path.name)
        except TrelloError:
            LOGGER.exception("Could not create card for photo")
            await message.reply_text(
                "خطا در ذخیره عکس داخل Trello. لطفاً کمی بعد دوباره تلاش کن."
            )
            return
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink(missing_ok=True)
        await message.reply_text(
            f"عکس در کارت شماره {card.get('idShort', card.get('id'))} ذخیره شد."
        )

    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.message
        user = update.effective_user
        if not message or not user or not message.voice:
            return
        telegram_file = await message.voice.get_file()
        temp_path = await _download_temp(telegram_file, suffix=".ogg")
        if temp_path is None:
            await message.reply_text("نتوانستم فایل ویس را دریافت کنم.")
            return
        workspace = self._ensure_workspace(user.id)
        title = message.caption or "ویس جدید"
        card_name, card_description = _split_card_content(title)
        try:
            card = self._trello.create_card(
                workspace.inbox_list_id,
                name=f"🎤 {card_name}",
                desc=card_description or "فایل صوتی پیوست شده است.",
            )
            self._trello.attach_file(
                card["id"], temp_path, temp_path.name
            )
        except TrelloError:
            LOGGER.exception("Could not create card for voice message")
            await message.reply_text(
                "در ذخیره ویس در Trello به مشکل خوردیم. بعداً امتحان کن."
            )
            return
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink(missing_ok=True)
        await message.reply_text(
            f"ویس به کارت شماره {card.get('idShort', card.get('id'))} اضافه شد."
        )


async def _download_temp(file: File, suffix: str = "") -> Optional[Path]:
    if not file:
        return None
    with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        await file.download_to_drive(tmp.name)
        return Path(tmp.name)


def _split_card_content(text: str) -> tuple[str, Optional[str]]:
    cleaned = [line.strip() for line in text.strip().splitlines() if line.strip()]
    if not cleaned:
        return "پیام بدون متن", None
    title = cleaned[0][:256]
    description = "\n".join(cleaned[1:]).strip()
    return title, description or None


def build_application() -> Application:
    try:
        settings = load_settings()
    except SettingsError as exc:
        raise SystemExit(str(exc)) from exc

    trello = TrelloClient(settings.trello_api_key, settings.trello_api_token)
    storage = WorkspaceStorage()
    workspace_manager = WorkspaceManager(
        storage, trello, default_list_name=settings.trello_default_list_name
    )
    handlers = BotHandlers(workspace_manager, trello)

    application = Application.builder().token(settings.telegram_bot_token).build()

    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(MessageHandler(filters.PHOTO, handlers.handle_photo))
    application.add_handler(MessageHandler(filters.VOICE, handlers.handle_voice))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_text)
    )

    return application


def main() -> None:
    application = build_application()
    LOGGER.info("Bot is starting. Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
