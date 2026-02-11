"""Add company_name and company_linkedin_url to messages_sent table.

Revision ID: 001
Revises:
Create Date: 2025-02-04

This migration adds company tracking to the messages_sent table,
enabling queries for which companies have been contacted.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use batch mode for SQLite compatibility (ALTER TABLE limitations)
    with op.batch_alter_table("messages_sent", schema=None) as batch_op:
        batch_op.add_column(sa.Column("company_name", sa.String(), nullable=True))
        batch_op.add_column(
            sa.Column("company_linkedin_url", sa.String(), nullable=True)
        )
        batch_op.create_index(
            "ix_messages_sent_company_linkedin_url", ["company_linkedin_url"]
        )


def downgrade() -> None:
    with op.batch_alter_table("messages_sent", schema=None) as batch_op:
        batch_op.drop_index("ix_messages_sent_company_linkedin_url")
        batch_op.drop_column("company_linkedin_url")
        batch_op.drop_column("company_name")
