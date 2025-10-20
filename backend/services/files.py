from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from itsdangerous import BadSignature, SignatureExpired, TimestampSigner
from uuid import uuid4
import re

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.logging import logger
from backend.core.settings import settings

from .base import ServiceBase


SAFE_EXTENSION_RE = re.compile(r"^[.a-zA-Z0-9_-]+$")


class FileService(ServiceBase):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.storage_dir = Path(settings.files_storage_dir).resolve()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        secret = settings.files_signing_secret or settings.jwt_secret
        self._signer = TimestampSigner(secret)

    @staticmethod
    def _generate_safe_name(original_name: str) -> str:
        original_suffix = Path(original_name).suffix.lower()
        if not SAFE_EXTENSION_RE.match(original_suffix):
            original_suffix = ""
        return f"{uuid4().hex}{original_suffix}"

    def _resolve_relative_path(self, stored_path: str) -> Path:
        path_obj = Path(stored_path)
        if not path_obj.is_absolute():
            path_obj = self.storage_dir / path_obj
        resolved = path_obj.resolve()
        if not str(resolved).startswith(str(self.storage_dir)):
            raise ValueError("Attempted access outside storage directory")
        return resolved

    async def save(self, name: str, content: bytes) -> str:
        safe_name = self._generate_safe_name(name)
        path = self.storage_dir / safe_name
        path.write_bytes(content)
        logger.info("file.save", path=str(path))
        return safe_name

    def generate_signed_token(self, stored_path: str) -> str:
        relative = Path(stored_path).name
        token = self._signer.sign(relative.encode()).decode()
        logger.info("file.sign", path=relative)
        return token

    def resolve_signed_token(self, token: str, max_age: Optional[int] = 3600) -> Path:
        try:
            if max_age is None:
                raw = self._signer.unsign(token)
            else:
                raw = self._signer.unsign(token, max_age=max_age)
            unsigned = raw.decode()
        except SignatureExpired as exc:
            logger.warning("file.sign.expired", error=str(exc))
            raise
        except BadSignature as exc:
            logger.warning("file.sign.invalid", error=str(exc))
            raise
        resolved = self._resolve_relative_path(unsigned)
        if not resolved.exists():
            raise FileNotFoundError(unsigned)
        return resolved

    async def cleanup_expired(self) -> int:
        if not self.storage_dir.exists():
            return 0
        removed = 0
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.file_retention_days)
        for file in self.storage_dir.iterdir():
            try:
                stat = file.stat()
            except FileNotFoundError:
                continue
            if file.is_dir():
                continue
            modified = datetime.fromtimestamp(stat.st_mtime, timezone.utc)
            if modified > cutoff:
                continue
            try:
                file.unlink()
                removed += 1
            except FileNotFoundError:
                continue
        logger.info("file.cleanup", removed=removed)
        return removed
