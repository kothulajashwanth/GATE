"""create attendance tables

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-23 19:10:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: str | None = 'a1b2c3d4e5f6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # 1. attendance_sessions
    if 'attendance_sessions' not in existing_tables:
        op.create_table(
            'attendance_sessions',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('subject_id', sa.Uuid(), nullable=False),
            sa.Column('department_id', sa.Uuid(), nullable=True),
            sa.Column('semester_id', sa.Uuid(), nullable=True),
            sa.Column('section_id', sa.Uuid(), nullable=True),
            sa.Column('date', sa.Date(), nullable=False),
            sa.Column('start_time', sa.String(length=10), nullable=False, server_default='09:00'),
            sa.Column('duration_minutes', sa.Integer(), nullable=False, server_default='60'),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='ACTIVE'),
            sa.Column('created_by', sa.Uuid(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['created_by'], ['users.id']),
            sa.ForeignKeyConstraint(['department_id'], ['departments.id']),
            sa.ForeignKeyConstraint(['section_id'], ['sections.id']),
            sa.ForeignKeyConstraint(['semester_id'], ['semesters.id']),
            sa.ForeignKeyConstraint(['subject_id'], ['subjects.id']),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_attendance_sessions_deleted_at'), 'attendance_sessions', ['deleted_at'], unique=False)
        op.create_index(op.f('ix_attendance_sessions_department_id'), 'attendance_sessions', ['department_id'], unique=False)
        op.create_index(op.f('ix_attendance_sessions_section_id'), 'attendance_sessions', ['section_id'], unique=False)
        op.create_index(op.f('ix_attendance_sessions_semester_id'), 'attendance_sessions', ['semester_id'], unique=False)
        op.create_index(op.f('ix_attendance_sessions_subject_id'), 'attendance_sessions', ['subject_id'], unique=False)

    # 2. attendance_records
    if 'attendance_records' not in existing_tables:
        op.create_table(
            'attendance_records',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('session_id', sa.Uuid(), nullable=False),
            sa.Column('student_id', sa.Uuid(), nullable=False),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='PRESENT'),
            sa.Column('remarks', sa.String(length=255), nullable=True),
            sa.Column('marked_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['session_id'], ['attendance_sessions.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('session_id', 'student_id', name='uq_attendance_session_student')
        )
        op.create_index(op.f('ix_attendance_records_deleted_at'), 'attendance_records', ['deleted_at'], unique=False)
        op.create_index(op.f('ix_attendance_records_session_id'), 'attendance_records', ['session_id'], unique=False)
        op.create_index(op.f('ix_attendance_records_student_id'), 'attendance_records', ['student_id'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if 'attendance_records' in existing_tables:
        op.drop_table('attendance_records')
    if 'attendance_sessions' in existing_tables:
        op.drop_table('attendance_sessions')
