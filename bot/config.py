from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


load_dotenv()


@dataclass(slots=True)
class Settings:
    telegram_bot_token: str
    trello_api_key: str
    trello_api_token: str
    trello_default_list_name: str = "Inbox"


class SettingsError(RuntimeError):
    """Raised when required environment variables are missing."""


def _read_env(name: str) -> Optional[str]:
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    return value.strip()


def load_settings() -> Settings:
    telegram_token = _read_env("TELEGRAM_BOT_TOKEN")
    trello_key = _read_env("TRELLO_API_KEY")
    trello_token = _read_env("TRELLO_API_TOKEN")
    default_list_name = _read_env("TRELLO_DEFAULT_LIST_NAME") or "Inbox"

    missing = [
        name
        for name, value in {
            "TELEGRAM_BOT_TOKEN": telegram_token,
            "TRELLO_API_KEY": trello_key,
            "TRELLO_API_TOKEN": trello_token,
        }.items()
        if value is None
    ]

    if missing:
        raise SettingsError(
            "Missing required environment variables: " + ", ".join(missing)
        )

    return Settings(
        telegram_bot_token=telegram_token,
        trello_api_key=trello_key,
        trello_api_token=trello_token,
        trello_default_list_name=default_list_name,
    )
