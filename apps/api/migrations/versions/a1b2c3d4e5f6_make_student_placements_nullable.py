"""make student placements nullable

Revision ID: a1b2c3d4e5f6
Revises: 33555bb095c9
Create Date: 2026-08-17 15:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: str | None = '33555bb095c9'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column('students', 'department_id', existing_type=sa.Uuid(), nullable=True)
    op.alter_column('students', 'semester_id', existing_type=sa.Uuid(), nullable=True)
    op.alter_column('students', 'section_id', existing_type=sa.Uuid(), nullable=True)


def downgrade() -> None:
    op.alter_column('students', 'department_id', existing_type=sa.Uuid(), nullable=False)
    op.alter_column('students', 'semester_id', existing_type=sa.Uuid(), nullable=False)
    op.alter_column('students', 'section_id', existing_type=sa.Uuid(), nullable=False)
