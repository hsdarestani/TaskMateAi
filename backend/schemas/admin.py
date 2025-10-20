from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AdminUserSummary(BaseModel):
    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    language: str | None = None
    timezone: str | None = None

    class Config:
        from_attributes = True


class AdminOrganizationSummary(BaseModel):
    id: int
    name: str
    plan: str | None = None
    owner_user_id: int | None = None

    class Config:
        from_attributes = True


class BlogPostCreate(BaseModel):
    lang: str
    slug: str
    title: str
    content_markdown: str
    author: str
    published: bool = False


class BlogPostUpdate(BaseModel):
    lang: str | None = None
    slug: str | None = None
    title: str | None = None
    content_markdown: str | None = None
    author: str | None = None
    published: bool | None = None


class BlogPostRead(BaseModel):
    id: int
    lang: str
    slug: str
    title: str
    content_markdown: str
    author: str
    published: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationRequest(BaseModel):
    title: str
    message: str


class AdminLoginRequest(BaseModel):
    username: str
    password: str
