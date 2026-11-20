"""Create the StudyX AI learning data tables without removing existing records."""
from alembic import op

from app import models  # noqa: F401 - registers all ORM tables.
from app.extensions import db


revision = "20261120_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Idempotent baseline: useful for existing planner databases and fresh installs.
    db.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade():
    # Keep user data intact. Remove tables only through an explicit data-retention plan.
    pass
