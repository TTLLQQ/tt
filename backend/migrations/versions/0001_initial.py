"""Create the initial ten-table application schema."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    from app.database import Base
    from app import models

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade():
    for table in ("tool_call_logs", "digital_employees", "ai_tools", "ai_models", "messages", "room_employees", "room_members", "chat_rooms", "friends", "users"):
        op.drop_table(table)
