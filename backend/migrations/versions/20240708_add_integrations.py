"""add integration settings and task links

Revision ID: 20240708_add_integrations
Revises: 20240705_implement_models
Create Date: 2024-07-08 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20240708_add_integrations"
down_revision = "20240705_implement_models"
branch_labels = None
depends_on = None

integration_provider_enum = sa.Enum(
    "eigan", "clickup", name="integrationprovider"
)
integration_scope_enum = sa.Enum("system", "organization", name="integrationscope")


def upgrade() -> None:
    bind = op.get_bind()
    integration_provider_enum.create(bind, checkfirst=True)
    integration_scope_enum.create(bind, checkfirst=True)

    op.create_table(
        "integration_settings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("provider", integration_provider_enum, nullable=False),
        sa.Column("scope", integration_scope_enum, nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "provider",
            "scope",
            "organization_id",
            name="uq_integration_settings_scope",
        ),
    )

    op.create_table(
        "task_external_links",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("provider", integration_provider_enum, nullable=False),
        sa.Column("external_task_id", sa.String(length=255), nullable=False),
        sa.Column(
            "context",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "task_id",
            "provider",
            name="uq_task_external_links_task_provider",
        ),
    )


def downgrade() -> None:
    op.drop_table("task_external_links")
    op.drop_table("integration_settings")

    bind = op.get_bind()
    integration_provider_enum.drop(bind, checkfirst=True)
    integration_scope_enum.drop(bind, checkfirst=True)
