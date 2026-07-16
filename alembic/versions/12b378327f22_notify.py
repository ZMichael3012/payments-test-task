"""notify

Revision ID: 12b378327f22
Revises: 03a23c501cbf
Create Date: 2026-04-05 13:29:39.269250

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "12b378327f22"
down_revision: str | Sequence[str] | None = "03a23c501cbf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text("""
        CREATE OR REPLACE FUNCTION notify_outbox_insert()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            PERFORM pg_notify('payments_outbox', NEW.id::text);
            RETURN NEW;
        END;
        $$;
    """)
    )

    op.execute(
        sa.text("""
        CREATE TRIGGER outbox_notify_trigger
            AFTER INSERT ON outbox
            FOR EACH ROW EXECUTE FUNCTION notify_outbox_insert();
    """)
    )


def downgrade() -> None:
    op.execute(sa.text("DROP TRIGGER IF EXISTS outbox_notify_trigger ON outbox;"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS notify_outbox_insert();"))
