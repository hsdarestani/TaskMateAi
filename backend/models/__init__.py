from __future__ import annotations

import enum
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for ORM models."""


class TimestampMixin:
    """Mixin providing UTC-aware created/updated timestamps."""

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )


class CreatedAtMixin:
    """Mixin providing a created_at timestamp."""

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )


class OrganizationUserRole(str, enum.Enum):
    MEMBER = "member"
    TEAM_MANAGER = "team_manager"
    ORG_ADMIN = "org_admin"


class SubscriptionSubjectType(str, enum.Enum):
    USER = "user"
    ORG = "org"


class SubscriptionStatus(str, enum.Enum):
    TRIAL = "trial"
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELED = "canceled"


class SubscriptionMethod(str, enum.Enum):
    ZIBAL = "zibal"
    CRYPTO = "crypto"
    NONE = "none"


class AnalyticsSource(str, enum.Enum):
    BOT = "bot"
    WEB = "web"
    ADMIN = "admin"


class IntegrationProvider(str, enum.Enum):
    EIGAN = "eigan"
    CLICKUP = "clickup"


class IntegrationScope(str, enum.Enum):
    SYSTEM = "system"
    ORGANIZATION = "organization"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, unique=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(120))
    last_name: Mapped[Optional[str]] = mapped_column(String(120))
    username: Mapped[Optional[str]] = mapped_column(String(120))
    language: Mapped[Optional[str]] = mapped_column(String(16))
    timezone: Mapped[Optional[str]] = mapped_column(String(64))
    preferences: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)

    organizations: Mapped[List["OrganizationUser"]] = relationship(
        "OrganizationUser", back_populates="user"
    )
    owned_organizations: Mapped[List["Organization"]] = relationship(
        "Organization", back_populates="owner"
    )
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="user")
    analytics_events: Mapped[List["AnalyticsEvent"]] = relationship(
        "AnalyticsEvent", back_populates="user"
    )


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    owner_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    plan: Mapped[Optional[str]] = mapped_column(String(50))

    owner: Mapped[Optional[User]] = relationship(
        "User", back_populates="owned_organizations", foreign_keys=owner_user_id
    )
    members: Mapped[List["OrganizationUser"]] = relationship(
        "OrganizationUser", back_populates="organization"
    )
    teams: Mapped[List["Team"]] = relationship(
        "Team", back_populates="organization"
    )
    projects: Mapped[List["Project"]] = relationship(
        "Project", back_populates="organization"
    )
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="organization")
    analytics_events: Mapped[List["AnalyticsEvent"]] = relationship(
        "AnalyticsEvent", back_populates="organization"
    )


class Team(Base, CreatedAtMixin):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="teams"
    )
    projects: Mapped[List["Project"]] = relationship(
        "Project", back_populates="team"
    )
    task_assignments: Mapped[List["TaskAssignment"]] = relationship(
        "TaskAssignment", back_populates="assigned_team"
    )


class OrganizationUser(Base):
    __tablename__ = "organization_users"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_user_membership"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[OrganizationUserRole] = mapped_column(Enum(OrganizationUserRole), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc)
    )

    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="members"
    )
    user: Mapped["User"] = relationship("User", back_populates="organizations")


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    team_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    start_date: Mapped[Optional[date]] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[Optional[str]] = mapped_column(String(50))

    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="projects"
    )
    team: Mapped[Optional["Team"]] = relationship("Team", back_populates="projects")
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="project")


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_user_id", "user_id"),
        Index("ix_tasks_org_project", "organization_id", "project_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    organization_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True
    )
    project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    type: Mapped[Optional[str]] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    start_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[Optional[str]] = mapped_column(String(50))
    priority: Mapped[Optional[str]] = mapped_column(String(50))
    source: Mapped[Optional[str]] = mapped_column(String(50))
    origin_message_id: Mapped[Optional[str]] = mapped_column(String(255))

    user: Mapped[Optional["User"]] = relationship("User", back_populates="tasks")
    organization: Mapped[Optional["Organization"]] = relationship(
        "Organization", back_populates="tasks"
    )
    project: Mapped[Optional["Project"]] = relationship(
        "Project", back_populates="tasks"
    )
    assignments: Mapped[List["TaskAssignment"]] = relationship(
        "TaskAssignment", back_populates="task", cascade="all, delete-orphan"
    )
    reminders: Mapped[List["Reminder"]] = relationship(
        "Reminder", back_populates="task", cascade="all, delete-orphan"
    )
    attachments: Mapped[List["Attachment"]] = relationship(
        "Attachment", back_populates="task", cascade="all, delete-orphan"
    )
    external_links: Mapped[List["TaskExternalLink"]] = relationship(
        "TaskExternalLink", back_populates="task", cascade="all, delete-orphan"
    )


class TaskExternalLink(Base, TimestampMixin):
    __tablename__ = "task_external_links"
    __table_args__ = (
        UniqueConstraint(
            "task_id",
            "provider",
            name="uq_task_external_links_task_provider",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[IntegrationProvider] = mapped_column(
        Enum(IntegrationProvider), nullable=False
    )
    external_task_id: Mapped[str] = mapped_column(String(255), nullable=False)
    context: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    task: Mapped["Task"] = relationship("Task", back_populates="external_links")


class TaskAssignment(Base):
    __tablename__ = "task_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    assigned_to_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assigned_team_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"), nullable=True
    )

    task: Mapped["Task"] = relationship("Task", back_populates="assignments")
    assigned_user: Mapped[Optional["User"]] = relationship("User")
    assigned_team: Mapped[Optional["Team"]] = relationship(
        "Team", back_populates="task_assignments"
    )


class Reminder(Base):
    __tablename__ = "reminders"
    __table_args__ = (
        Index("ix_reminders_remind_at_sent", "remind_at", "sent"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    remind_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    task: Mapped["Task"] = relationship("Task", back_populates="reminders")


class Attachment(Base, CreatedAtMixin):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    meta: Mapped[Optional[dict]] = mapped_column(JSONB)

    task: Mapped["Task"] = relationship("Task", back_populates="attachments")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject_type: Mapped[SubscriptionSubjectType] = mapped_column(
        Enum(SubscriptionSubjectType), nullable=False
    )
    subject_id: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus), nullable=False
    )
    method: Mapped[SubscriptionMethod] = mapped_column(
        Enum(SubscriptionMethod), nullable=False
    )
    trial_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    trial_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    active_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (Index("ix_payments_status", "status"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject_type: Mapped[SubscriptionSubjectType] = mapped_column(
        Enum(SubscriptionSubjectType), nullable=False
    )
    subject_id: Mapped[int] = mapped_column(Integer, nullable=False)
    method: Mapped[SubscriptionMethod] = mapped_column(
        Enum(SubscriptionMethod), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    amount: Mapped[Numeric] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    ref_id: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc)
    )


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"
    __table_args__ = (
        Index(
            "ix_analytics_events_event_type_created_at",
            "event_type",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    organization_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True
    )
    source: Mapped[AnalyticsSource] = mapped_column(Enum(AnalyticsSource), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    data: Mapped[Optional[dict]] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc)
    )

    user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="analytics_events"
    )
    organization: Mapped[Optional["Organization"]] = relationship(
        "Organization", back_populates="analytics_events"
    )



class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc)
    )


class ActivitySnapshot(Base):
    __tablename__ = "activity_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    users_active: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    orgs_active: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payments_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revenue: Mapped[Numeric] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    tasks_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class BlogPost(Base, CreatedAtMixin):
    __tablename__ = "blog_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lang: Mapped[str] = mapped_column(String(8), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint("lang", "slug", name="uq_blog_posts_lang_slug"),
    )


class AdminUser(Base, CreatedAtMixin):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)


class IntegrationSetting(Base, TimestampMixin):
    __tablename__ = "integration_settings"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "scope",
            "organization_id",
            name="uq_integration_settings_scope",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[IntegrationProvider] = mapped_column(
        Enum(IntegrationProvider), nullable=False
    )
    scope: Mapped[IntegrationScope] = mapped_column(
        Enum(IntegrationScope), nullable=False
    )
    organization_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )
    config: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)

    organization: Mapped[Optional[Organization]] = relationship("Organization")


class ErrorLog(Base, CreatedAtMixin):
    __tablename__ = "error_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[Optional[dict]] = mapped_column(JSONB)


__all__ = [
    "Base",
    "User",
    "Organization",
    "Team",
    "OrganizationUser",
    "Project",
    "Task",
    "TaskAssignment",
    "Reminder",
    "Attachment",
    "Subscription",
    "Payment",
    "AnalyticsEvent",
    "ActivityLog",
    "ActivitySnapshot",
    "BlogPost",
    "AdminUser",
    "ErrorLog",
    "OrganizationUserRole",
    "SubscriptionSubjectType",
    "SubscriptionStatus",
    "SubscriptionMethod",
    "AnalyticsSource",
]
