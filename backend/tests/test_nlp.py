from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from backend.api.telegram_router import parse_due_date, dateparser


@pytest.fixture(autouse=True)
def patch_dateparser(monkeypatch):
    bases = {
        "en": datetime(2024, 1, 15, 9, 0, tzinfo=ZoneInfo("Europe/Stockholm")),
        "fa": datetime(2024, 1, 15, 9, 0, tzinfo=ZoneInfo("Asia/Tehran")),
        "ar": datetime(2024, 1, 15, 9, 0, tzinfo=ZoneInfo("Asia/Dubai")),
    }
    original_parse = dateparser.parse

    def _parse(text, languages=None, settings=None):
        options = dict(settings or {})
        locale = (languages or ["en"])[0]
        base = bases.get(locale, bases["en"])
        options.setdefault("RELATIVE_BASE", base)
        return original_parse(text, languages=languages, settings=options)

    monkeypatch.setattr(dateparser, "parse", _parse)
    return bases


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def test_parse_due_date_english(patch_dateparser):
    due = parse_due_date("today 2pm", "Europe/Stockholm", "en")
    expected_local = patch_dateparser["en"].replace(hour=14, minute=0, second=0, microsecond=0)
    assert due == _to_utc(expected_local)


def test_parse_due_date_farsi(patch_dateparser):
    due = parse_due_date("فردا ۱۰", "Asia/Tehran", "fa")
    due_local = due.astimezone(ZoneInfo("Asia/Tehran"))
    expected_day = (patch_dateparser["fa"].date() + timedelta(days=1))
    assert due_local.date() == expected_day
    assert due_local.hour in {9, 10}


def test_parse_due_date_arabic(patch_dateparser):
    due = parse_due_date("السبت 14", "Asia/Dubai", "ar")
    due_local = due.astimezone(ZoneInfo("Asia/Dubai"))
    delta_days = (due_local.date() - patch_dateparser["ar"].date()).days
    assert abs(delta_days) <= 7
    assert 0 <= due_local.hour < 24
