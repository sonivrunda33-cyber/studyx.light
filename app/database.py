import sqlite3
from contextlib import closing
from sqlalchemy import event
from pathlib import Path

from flask import current_app, g

from .extensions import db

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _ensure_user_columns(db):
    """Add account ownership columns when opening an older local prototype DB."""
    for table in ("tasks", "exams", "study_sessions", "interaction_events", "survey_responses", "usability_tests"):
        columns = {row[1] for row in db.execute(f"PRAGMA table_info({table})").fetchall()}
        if "user_id" not in columns:
            db.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE")
            columns.add("user_id")
        additions = {
            "survey_responses": {
                "sus_answers": "TEXT NOT NULL DEFAULT '[]'",
                "sus_score": "REAL NOT NULL DEFAULT 0",
                "consent_confirmed": "INTEGER NOT NULL DEFAULT 0",
            },
            "usability_tests": {
                "sus_answers": "TEXT NOT NULL DEFAULT '[]'",
                "sus_score": "REAL NOT NULL DEFAULT 0",
                "consent_confirmed": "INTEGER NOT NULL DEFAULT 0",
            },
        }.get(table, {})
        for column, declaration in additions.items():
            if column not in columns:
                db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")


def init_db(app):
    with app.app_context():
        if db.engine.dialect.name == "sqlite":
            schema_path = Path(__file__).with_name("schema.sql")
            with closing(sqlite3.connect(app.config["DATABASE"])) as connection:
                with connection:
                    connection.execute("PRAGMA foreign_keys = ON")
                    connection.executescript(schema_path.read_text(encoding="utf-8"))
                    _ensure_user_columns(connection)

            @event.listens_for(db.engine, "connect")
            def enable_sqlite_foreign_keys(connection, _record):
                cursor = connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA busy_timeout=5000")
                cursor.close()

        # Creates only missing tables; all existing records remain in place.
        db.create_all()
    app.teardown_appcontext(close_db)


def seed_account_data(db, user_id, claim_legacy=False):
    """Assign old unowned records to the first account without adding demo data."""
    if claim_legacy:
        for table in ("tasks", "exams", "study_sessions", "interaction_events", "survey_responses", "usability_tests"):
            db.execute(f"UPDATE {table} SET user_id=? WHERE user_id IS NULL", (user_id,))
        db.commit()
