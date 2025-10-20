from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncEngine, async_engine_from_config

from alembic import context

from backend.core.settings import settings
from backend.models import Base

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_dsn)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    if isinstance(connectable, AsyncEngine):
        async def async_run() -> None:
            async with connectable.connect() as connection:
                await connection.run_sync(
                    lambda conn: context.configure(connection=conn, target_metadata=target_metadata)
                )
                await connection.run_sync(lambda conn: context.run_migrations())

        import asyncio

        asyncio.run(async_run())
    else:
        with connectable.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
