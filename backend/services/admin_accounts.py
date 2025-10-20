from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext

from backend.core.logging import logger
from backend.models import AdminUser

from .base import ServiceBase

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AdminAccountService(ServiceBase):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def authenticate(self, username: str, password: str) -> AdminUser:
        result = await self.session.execute(
            select(AdminUser).where(AdminUser.username == username)
        )
        admin = result.scalar_one_or_none()
        if admin is None:
            raise ValueError("invalid_credentials")
        if not _pwd_context.verify(password, admin.password_hash):
            raise ValueError("invalid_credentials")
        logger.info("admin.authenticated", admin_id=admin.id, username=username)
        return admin
