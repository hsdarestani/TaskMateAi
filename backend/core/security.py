from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import jwt
from passlib.context import CryptContext

from .settings import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)


def create_access_token(subject: str, *, expires_hours: int | None = None, extra: Dict[str, Any] | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=expires_hours or settings.jwt_admin_expires_hours)
    payload: Dict[str, Any] = {"sub": subject, "exp": expire}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
