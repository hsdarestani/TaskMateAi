import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import asyncio
from datetime import datetime
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool

from backend.core.settings import settings
from backend.models import Base


@compiles(JSONB, "sqlite")
def compile_jsonb(element, compiler, **_kw):  # pragma: no cover - test setup helper
    return "JSON"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def async_engine(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("db") / "test.db"
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        echo=False,
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
def session_maker(async_engine):
    return async_sessionmaker(bind=async_engine, expire_on_commit=False, class_=AsyncSession)


@pytest.fixture(autouse=True, scope="session")
def configure_settings(tmp_path_factory):
    tmp_uploads = tmp_path_factory.mktemp("uploads")
    settings.files_storage_dir = Path(tmp_uploads)
    settings.files_signing_secret = "test-secret"
    settings.telegram_bot_token = "test-token"
    settings.zibal_merchant_id = "merchant"
    settings.cryptobot_api_token = "crypto-token"
    return settings


@pytest.fixture(autouse=True)
def patch_sessionlocal(monkeypatch, session_maker):
    monkeypatch.setattr("backend.services.base.SessionLocal", session_maker)
    monkeypatch.setattr("backend.workers.reminders_worker.SessionLocal", session_maker)
    return session_maker


@pytest_asyncio.fixture
async def session(async_engine, session_maker):
    async with session_maker() as session:
        yield session
        await session.rollback()
    async with async_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest_asyncio.fixture
async def user_factory(session):
    from backend.models import User

    created = []

    async def factory(**kwargs):
        user = User(
            first_name=kwargs.get("first_name", "Test"),
            language=kwargs.get("language", "en"),
            timezone=kwargs.get("timezone", settings.default_timezone),
            telegram_id=kwargs.get("telegram_id"),
            preferences=kwargs.get("preferences", {"default_reminder_minutes": 15}),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        created.append(user)
        return user

    return factory
