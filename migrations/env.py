from alembic import context
from flask import current_app

from app import models  # noqa: F401 - registers all ORM tables.
from app.extensions import db


config = context.config
target_metadata = db.metadata


def database_engine():
    return current_app.extensions["migrate"].db.engine


def run_migrations_offline():
    url = database_engine().url.render_as_string(hide_password=False)
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True,
                      dialect_opts={"paramstyle": "named"}, compare_type=True, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    with database_engine().connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata,
                          compare_type=True, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
