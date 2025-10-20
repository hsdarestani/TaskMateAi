from __future__ import annotations

from typing import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.settings import settings

_engine = create_async_engine(str(settings.database_dsn), echo=False, future=True)
SessionLocal = async_sessionmaker(bind=_engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


class ServiceBase:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session


def provide_service(service_cls):
    async def dependency(session: AsyncSession = Depends(get_session)):
        return service_cls(session)

    return dependency
