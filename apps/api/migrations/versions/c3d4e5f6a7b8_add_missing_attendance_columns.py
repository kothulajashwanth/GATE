"""add missing attendance columns

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-23 20:15:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: str | None = 'b2c3d4e5f6a7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # 1. Inspect and update attendance_sessions
    if 'attendance_sessions' in existing_tables:
        cols = {c['name'] for c in inspector.get_columns('attendance_sessions')}
        
        if 'title' not in cols:
            op.add_column('attendance_sessions', sa.Column('title', sa.String(length=255), nullable=True))
            op.execute("UPDATE attendance_sessions SET title = 'Attendance Session' WHERE title IS NULL")
            op.alter_column('attendance_sessions', 'title', nullable=False, server_default='Attendance Session')

        if 'subject_id' not in cols:
            op.add_column('attendance_sessions', sa.Column('subject_id', sa.Uuid(), nullable=True))

        if 'department_id' not in cols:
            op.add_column('attendance_sessions', sa.Column('department_id', sa.Uuid(), nullable=True))

        if 'semester_id' not in cols:
            op.add_column('attendance_sessions', sa.Column('semester_id', sa.Uuid(), nullable=True))

        if 'section_id' not in cols:
            op.add_column('attendance_sessions', sa.Column('section_id', sa.Uuid(), nullable=True))

        if 'date' not in cols:
            op.add_column('attendance_sessions', sa.Column('date', sa.Date(), nullable=True))
            op.execute("UPDATE attendance_sessions SET date = CURRENT_DATE WHERE date IS NULL")
            op.alter_column('attendance_sessions', 'date', nullable=False, server_default=sa.text('CURRENT_DATE'))

        if 'start_time' not in cols:
            op.add_column('attendance_sessions', sa.Column('start_time', sa.String(length=10), nullable=True))
            op.execute("UPDATE attendance_sessions SET start_time = '09:00' WHERE start_time IS NULL")
            op.alter_column('attendance_sessions', 'start_time', nullable=False, server_default='09:00')

        if 'duration_minutes' not in cols:
            op.add_column('attendance_sessions', sa.Column('duration_minutes', sa.Integer(), nullable=True))
            op.execute("UPDATE attendance_sessions SET duration_minutes = 60 WHERE duration_minutes IS NULL")
            op.alter_column('attendance_sessions', 'duration_minutes', nullable=False, server_default='60')

        if 'status' not in cols:
            op.add_column('attendance_sessions', sa.Column('status', sa.String(length=50), nullable=True))
            op.execute("UPDATE attendance_sessions SET status = 'ACTIVE' WHERE status IS NULL")
            op.alter_column('attendance_sessions', 'status', nullable=False, server_default='ACTIVE')

        if 'created_by' not in cols:
            op.add_column('attendance_sessions', sa.Column('created_by', sa.Uuid(), nullable=True))

        if 'created_at' not in cols:
            op.add_column('attendance_sessions', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))

        if 'updated_at' not in cols:
            op.add_column('attendance_sessions', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))

        if 'deleted_at' not in cols:
            op.add_column('attendance_sessions', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))

    # 2. Inspect and update attendance_records
    if 'attendance_records' in existing_tables:
        rec_cols = {c['name'] for c in inspector.get_columns('attendance_records')}

        if 'session_id' not in rec_cols:
            op.add_column('attendance_records', sa.Column('session_id', sa.Uuid(), nullable=True))

        if 'student_id' not in rec_cols:
            op.add_column('attendance_records', sa.Column('student_id', sa.Uuid(), nullable=True))

        if 'status' not in rec_cols:
            op.add_column('attendance_records', sa.Column('status', sa.String(length=50), nullable=True))
            op.execute("UPDATE attendance_records SET status = 'PRESENT' WHERE status IS NULL")
            op.alter_column('attendance_records', 'status', nullable=False, server_default='PRESENT')

        if 'remarks' not in rec_cols:
            op.add_column('attendance_records', sa.Column('remarks', sa.String(length=255), nullable=True))

        if 'marked_at' not in rec_cols:
            op.add_column('attendance_records', sa.Column('marked_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))

        if 'created_at' not in rec_cols:
            op.add_column('attendance_records', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))

        if 'updated_at' not in rec_cols:
            op.add_column('attendance_records', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))

        if 'deleted_at' not in rec_cols:
            op.add_column('attendance_records', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    pass
