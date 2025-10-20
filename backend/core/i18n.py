"""Localization utilities for TaskMate AI services."""

from __future__ import annotations

import json
from datetime import date, datetime, time
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable

from babel.dates import format_date as babel_format_date
from babel.dates import format_datetime as babel_format_datetime
from babel.dates import format_time as babel_format_time
from fastapi import Request
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .logging import logger
from .settings import settings

SUPPORTED_LOCALES: set[str] = {"en", "fa", "ar"}
RTL_LOCALES: set[str] = {"fa", "ar"}
LOCALES_DIR = Path(__file__).resolve().parents[1] / "locales"


def _ensure_locale(locale: str | None) -> str:
    if not locale:
        return settings.default_locale
    code = locale.split("-")[0].lower()
    if code not in SUPPORTED_LOCALES:
        return settings.default_locale
    return code


normalize_locale = _ensure_locale


@lru_cache()
def _load_catalog(locale: str) -> Dict[str, str]:
    catalog_path = LOCALES_DIR / f"{locale}.json"
    try:
        with catalog_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
            if not isinstance(data, dict):
                raise ValueError("Locale catalog must be a dictionary")
            return {str(key): str(value) for key, value in data.items()}
    except FileNotFoundError:
        logger.warning("i18n.catalog_missing", locale=locale, path=str(catalog_path))
    except (json.JSONDecodeError, ValueError):
        logger.exception("i18n.catalog_invalid", locale=locale, path=str(catalog_path))
    return {}


def reload_catalogs(locales: Iterable[str] | None = None) -> None:
    """Invalidate cached catalogs to pick up updated locale files."""

    targets = tuple(locales or SUPPORTED_LOCALES)
    _load_catalog.cache_clear()
    for locale in targets:
        _load_catalog(locale)  # Reload into cache immediately


def translate(locale: str, key: str, **kwargs: Any) -> str:
    """Translate a message key using the requested locale."""

    locale_code = _ensure_locale(locale)
    base_catalog = _load_catalog(settings.default_locale)
    catalog = _load_catalog(locale_code) or base_catalog
    template = catalog.get(key) or base_catalog.get(key) or key
    try:
        return template.format(**kwargs)
    except Exception:  # noqa: BLE001
        logger.debug("i18n.format_error", key=key, locale=locale_code, kwargs=kwargs)
        return template


def apply_direction(locale: str, text: str) -> str:
    """Wrap RTL languages with directional marks for correct rendering."""

    if not text:
        return text
    locale_code = _ensure_locale(locale)
    if locale_code in RTL_LOCALES:
        return f"\u202B{text}\u202C"
    return text


def prepare_telegram(locale: str, text: str) -> str:
    """Prepare Telegram-safe text respecting RTL locales."""

    return apply_direction(locale, text.replace("\r\n", "\n"))


def _ensure_timezone(timezone_name: str | ZoneInfo | None) -> ZoneInfo:
    if isinstance(timezone_name, ZoneInfo):
        return timezone_name
    candidate = timezone_name or settings.default_timezone
    try:
        return ZoneInfo(candidate)
    except ZoneInfoNotFoundError:
        logger.warning("i18n.timezone_invalid", timezone=candidate)
        try:
            return ZoneInfo(settings.default_timezone)
        except ZoneInfoNotFoundError:
            return ZoneInfo("UTC")


def format_datetime(
    value: datetime,
    locale: str,
    timezone_name: str | ZoneInfo | None = None,
    fmt: str = "medium",
) -> str:
    tzinfo = _ensure_timezone(timezone_name)
    localized = value if value.tzinfo else value.replace(tzinfo=ZoneInfo("UTC"))
    localized = localized.astimezone(tzinfo)
    return babel_format_datetime(localized, format=fmt, locale=_ensure_locale(locale), tzinfo=tzinfo)


def format_date(
    value: date | datetime,
    locale: str,
    timezone_name: str | ZoneInfo | None = None,
    fmt: str = "medium",
) -> str:
    if isinstance(value, datetime):
        tzinfo = _ensure_timezone(timezone_name)
        localized = value if value.tzinfo else value.replace(tzinfo=ZoneInfo("UTC"))
        localized = localized.astimezone(tzinfo)
    else:
        localized = value
    return babel_format_date(localized, format=fmt, locale=_ensure_locale(locale))


def format_time(
    value: time | datetime,
    locale: str,
    timezone_name: str | ZoneInfo | None = None,
    fmt: str = "short",
) -> str:
    if isinstance(value, datetime):
        tzinfo = _ensure_timezone(timezone_name)
        localized = value if value.tzinfo else value.replace(tzinfo=ZoneInfo("UTC"))
        localized = localized.astimezone(tzinfo)
    else:
        localized = datetime.combine(date.today(), value, tzinfo=_ensure_timezone(timezone_name))
    return babel_format_time(localized, format=fmt, locale=_ensure_locale(locale))


def get_locale_from_request(request: Request) -> str:
    explicit = request.headers.get("x-locale")
    if explicit:
        return _ensure_locale(explicit)

    accept = request.headers.get("accept-language", "")
    for part in accept.split(","):
        code = part.split(";")[0].strip()
        if code:
            normalized = _ensure_locale(code)
            if normalized:
                return normalized
    return settings.default_locale


__all__ = [
    "SUPPORTED_LOCALES",
    "RTL_LOCALES",
    "normalize_locale",
    "translate",
    "apply_direction",
    "prepare_telegram",
    "format_datetime",
    "format_date",
    "format_time",
    "get_locale_from_request",
    "reload_catalogs",
]

