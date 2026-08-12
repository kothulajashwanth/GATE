"""initial schema

Revision ID: 33555bb095c9
Revises: 
Create Date: 2026-08-05 10:44:48.526881

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '33555bb095c9'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. departments
    op.create_table(
        'departments',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=160), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index(op.f('ix_departments_deleted_at'), 'departments', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_departments_name'), 'departments', ['name'], unique=True)

    # 2. users
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('clerk_id', sa.String(length=255), nullable=True),
        sa.Column('email', sa.String(length=320), nullable=False),
        sa.Column('first_name', sa.String(length=120), nullable=True),
        sa.Column('last_name', sa.String(length=120), nullable=True),
        sa.Column('password_hash', sa.String(length=255), nullable=True),
        sa.Column('role', sa.Enum('SUPER_ADMIN', 'ADMIN', 'STUDENT', 'FACULTY', name='user_role'), nullable=False),
        sa.Column('avatar_url', sa.Text(), nullable=True),
        sa.Column('phone', sa.String(length=30), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_clerk_id'), 'users', ['clerk_id'], unique=True)
    op.create_index(op.f('ix_users_deleted_at'), 'users', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)

    # 3. audit_logs
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('actor_id', sa.Uuid(), nullable=True),
        sa.Column('action', sa.String(length=120), nullable=False),
        sa.Column('entity_type', sa.String(length=80), nullable=True),
        sa.Column('entity_id', sa.String(length=80), nullable=True),
        sa.Column('old_value', sa.JSON(), nullable=True),
        sa.Column('new_value', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.Column('user_agent', sa.String(length=512), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_actor_id'), 'audit_logs', ['actor_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'], unique=False)

    # 4. notifications
    op.create_table(
        'notifications',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('type', sa.Enum('EXAM_SCHEDULED', 'EXAM_CANCELLED', 'RESULT_PUBLISHED', 'PASSWORD_RESET', 'ANNOUNCEMENT', name='notification_type'), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False),
        sa.Column('sent_via_email', sa.Boolean(), nullable=False),
        sa.Column('link', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_created_at'), 'notifications', ['created_at'], unique=False)
    op.create_index(op.f('ix_notifications_is_read'), 'notifications', ['is_read'], unique=False)
    op.create_index(op.f('ix_notifications_type'), 'notifications', ['type'], unique=False)
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)

    # 5. question_bank_folders
    op.create_table(
        'question_bank_folders',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=160), nullable=False),
        sa.Column('parent_id', sa.Uuid(), nullable=True),
        sa.Column('created_by', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['parent_id'], ['question_bank_folders.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_question_bank_folders_deleted_at'), 'question_bank_folders', ['deleted_at'], unique=False)

    # 6. semesters
    op.create_table(
        'semesters',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('department_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=60), nullable=False),
        sa.Column('ordinal', sa.Integer(), nullable=False),
        sa.Column('academic_year', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_semesters_deleted_at'), 'semesters', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_semesters_department_id'), 'semesters', ['department_id'], unique=False)

    # 7. subjects
    op.create_table(
        'subjects',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=160), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('department_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index(op.f('ix_subjects_deleted_at'), 'subjects', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_subjects_name'), 'subjects', ['name'], unique=True)

    # 8. topics
    op.create_table(
        'topics',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('subject_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=160), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['subject_id'], ['subjects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_topics_deleted_at'), 'topics', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_topics_name'), 'topics', ['name'], unique=False)
    op.create_index(op.f('ix_topics_subject_id'), 'topics', ['subject_id'], unique=False)

    # 9. uploaded_files
    op.create_table(
        'uploaded_files',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('original_name', sa.String(length=255), nullable=False),
        sa.Column('file_type', sa.String(length=50), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('storage_url', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('uploaded_by', sa.Uuid(), nullable=False),
        sa.Column('questions_found', sa.Integer(), nullable=False),
        sa.Column('ocr_used', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 10. failed_questions
    op.create_table(
        'failed_questions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('source_file_id', sa.Uuid(), nullable=False),
        sa.Column('raw_data', sa.JSON(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['source_file_id'], ['uploaded_files.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 11. exams
    op.create_table(
        'exams',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('subject_id', sa.Uuid(), nullable=True),
        sa.Column('created_by', sa.Uuid(), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('start_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('passing_marks', sa.Integer(), nullable=False),
        sa.Column('negative_marks_enabled', sa.Boolean(), nullable=False),
        sa.Column('negative_marks_value', sa.Float(), nullable=False),
        sa.Column('randomize_questions', sa.Boolean(), nullable=False),
        sa.Column('shuffle_options', sa.Boolean(), nullable=False),
        sa.Column('attempt_limit', sa.Integer(), nullable=False),
        sa.Column('question_mode', sa.Enum('ALL_AT_ONCE', 'ONE_AT_A_TIME', name='exam_question_mode'), nullable=False),
        sa.Column('instructions', sa.Text(), nullable=True),
        sa.Column('visibility', sa.String(length=20), nullable=False),
        sa.Column('status', sa.Enum('DRAFT', 'PUBLISHED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', name='exam_status'), nullable=False),
        sa.Column('total_marks', sa.Integer(), nullable=False),
        sa.Column('security_mode', sa.Boolean(), nullable=False),
        sa.Column('camera_proctoring_enabled', sa.Boolean(), nullable=False),
        sa.Column('auto_submit', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['subject_id'], ['subjects.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_exams_deleted_at'), 'exams', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_exams_end_at'), 'exams', ['end_at'], unique=False)
    op.create_index(op.f('ix_exams_start_at'), 'exams', ['start_at'], unique=False)
    op.create_index(op.f('ix_exams_status'), 'exams', ['status'], unique=False)
    op.create_index(op.f('ix_exams_subject_id'), 'exams', ['subject_id'], unique=False)

    # 12. questions
    op.create_table(
        'questions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('folder_id', sa.Uuid(), nullable=True),
        sa.Column('subject_id', sa.Uuid(), nullable=True),
        sa.Column('topic_id', sa.Uuid(), nullable=True),
        sa.Column('source_file_id', sa.Uuid(), nullable=True),
        sa.Column('created_by', sa.Uuid(), nullable=False),
        sa.Column('type', sa.Enum('MCQ', 'TRUE_FALSE', 'FILL_BLANK', 'PARAGRAPH', 'CODING', 'IMAGE_BASED', 'MULTI_SELECT', name='question_type'), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('image_url', sa.Text(), nullable=True),
        sa.Column('options', sa.JSON(), nullable=True),
        sa.Column('correct_answers', sa.JSON(), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('hint', sa.Text(), nullable=True),
        sa.Column('difficulty', sa.Enum('EASY', 'MEDIUM', 'HARD', name='question_difficulty'), nullable=False),
        sa.Column('bloom_level', sa.Enum('REMEMBER', 'UNDERSTAND', 'APPLY', 'ANALYZE', 'EVALUATE', 'CREATE', name='bloom_level'), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=False),
        sa.Column('marks', sa.Integer(), nullable=False),
        sa.Column('negative_marks', sa.Float(), nullable=False),
        sa.Column('topic', sa.String(length=200), nullable=True),
        sa.Column('learning_outcome', sa.Text(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False),
        sa.Column('is_ai_generated', sa.Boolean(), nullable=False),
        sa.Column('is_public', sa.Boolean(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('derived_from_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['derived_from_id'], ['questions.id'], ),
        sa.ForeignKeyConstraint(['folder_id'], ['question_bank_folders.id'], ),
        sa.ForeignKeyConstraint(['source_file_id'], ['uploaded_files.id'], ),
        sa.ForeignKeyConstraint(['subject_id'], ['subjects.id'], ),
        sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_questions_deleted_at'), 'questions', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_questions_folder_id'), 'questions', ['folder_id'], unique=False)
    op.create_index('ix_questions_subject_difficulty', 'questions', ['subject_id', 'difficulty'], unique=False)
    op.create_index(op.f('ix_questions_subject_id'), 'questions', ['subject_id'], unique=False)
    op.create_index('ix_questions_topic_id', 'questions', ['topic_id'], unique=False)
    op.create_index(op.f('ix_questions_type'), 'questions', ['type'], unique=False)
    op.create_index('ix_questions_type_bloom', 'questions', ['type', 'bloom_level'], unique=False)

    # 13. question_options
    op.create_table(
        'question_options',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('question_id', sa.Uuid(), nullable=False),
        sa.Column('option_text', sa.Text(), nullable=False),
        sa.Column('is_correct', sa.Boolean(), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_question_options_question_id'), 'question_options', ['question_id'], unique=False)

    # 14. question_versions
    op.create_table(
        'question_versions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('question_id', sa.Uuid(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('snapshot', sa.JSON(), nullable=False),
        sa.Column('change_summary', sa.Text(), nullable=True),
        sa.Column('changed_by', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['changed_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_question_versions_question_id'), 'question_versions', ['question_id'], unique=False)

    # 15. sections
    op.create_table(
        'sections',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('department_id', sa.Uuid(), nullable=False),
        sa.Column('semester_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=60), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['semester_id'], ['semesters.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sections_deleted_at'), 'sections', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_sections_department_id'), 'sections', ['department_id'], unique=False)
    op.create_index(op.f('ix_sections_semester_id'), 'sections', ['semester_id'], unique=False)

    # 16. students
    op.create_table(
        'students',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('roll_number', sa.String(length=40), nullable=False),
        sa.Column('department_id', sa.Uuid(), nullable=False),
        sa.Column('semester_id', sa.Uuid(), nullable=False),
        sa.Column('section_id', sa.Uuid(), nullable=False),
        sa.Column('phone', sa.String(length=30), nullable=True),
        sa.Column('parent_name', sa.String(length=160), nullable=True),
        sa.Column('parent_phone', sa.String(length=30), nullable=True),
        sa.Column('enrollment_year', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
        sa.ForeignKeyConstraint(['section_id'], ['sections.id'], ),
        sa.ForeignKeyConstraint(['semester_id'], ['semesters.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('roll_number'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_students_deleted_at'), 'students', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_students_department_id'), 'students', ['department_id'], unique=False)
    op.create_index(op.f('ix_students_roll_number'), 'students', ['roll_number'], unique=True)
    op.create_index(op.f('ix_students_section_id'), 'students', ['section_id'], unique=False)
    op.create_index(op.f('ix_students_semester_id'), 'students', ['semester_id'], unique=False)

    # 17. exam_questions
    op.create_table(
        'exam_questions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('exam_id', sa.Uuid(), nullable=False),
        sa.Column('question_id', sa.Uuid(), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.Column('marks', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['exam_id'], ['exams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_exam_questions_exam_id'), 'exam_questions', ['exam_id'], unique=False)
    op.create_index(op.f('ix_exam_questions_question_id'), 'exam_questions', ['question_id'], unique=False)

    # 18. exam_schedules
    op.create_table(
        'exam_schedules',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('exam_id', sa.Uuid(), nullable=False),
        sa.Column('department_id', sa.Uuid(), nullable=True),
        sa.Column('semester_id', sa.Uuid(), nullable=True),
        sa.Column('section_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
        sa.ForeignKeyConstraint(['exam_id'], ['exams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['section_id'], ['sections.id'], ),
        sa.ForeignKeyConstraint(['semester_id'], ['semesters.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_exam_schedules_exam_id'), 'exam_schedules', ['exam_id'], unique=False)

    # 19. exam_sessions
    op.create_table(
        'exam_sessions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('exam_id', sa.Uuid(), nullable=False),
        sa.Column('student_id', sa.Uuid(), nullable=False),
        sa.Column('status', sa.Enum('ACTIVE', 'SUBMITTED', 'TERMINATED', 'EXPIRED', name='session_status'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deadline_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('warning_count', sa.Integer(), nullable=False),
        sa.Column('terminated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('terminate_reason', sa.String(length=500), nullable=True),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.Column('user_agent', sa.String(length=512), nullable=True),
        sa.Column('device_fingerprint', sa.String(length=255), nullable=True),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('time_spent_seconds', sa.Integer(), nullable=True),
        sa.Column('is_locked', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['exam_id'], ['exams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_exam_sessions_exam_id'), 'exam_sessions', ['exam_id'], unique=False)
    op.create_index(op.f('ix_exam_sessions_status'), 'exam_sessions', ['status'], unique=False)
    op.create_index(op.f('ix_exam_sessions_student_id'), 'exam_sessions', ['student_id'], unique=False)
    op.create_index('ix_sessions_student_exam_active', 'exam_sessions', ['student_id', 'exam_id', 'status'], unique=False)

    # 20. session_answers
    op.create_table(
        'session_answers',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('session_id', sa.Uuid(), nullable=False),
        sa.Column('question_id', sa.Uuid(), nullable=False),
        sa.Column('selected_option_id', sa.Uuid(), nullable=True),
        sa.Column('answer', sa.JSON(), nullable=False),
        sa.Column('is_answered', sa.Boolean(), nullable=False),
        sa.Column('is_correct', sa.Boolean(), nullable=True),
        sa.Column('marks_awarded', sa.Float(), nullable=True),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('time_taken_seconds', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['selected_option_id'], ['question_options.id'], ),
        sa.ForeignKeyConstraint(['session_id'], ['exam_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_session_answers_question_id'), 'session_answers', ['question_id'], unique=False)
    op.create_index(op.f('ix_session_answers_selected_option_id'), 'session_answers', ['selected_option_id'], unique=False)
    op.create_index(op.f('ix_session_answers_session_id'), 'session_answers', ['session_id'], unique=False)

    # 21. violation_records
    op.create_table(
        'violation_records',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('session_id', sa.Uuid(), nullable=False),
        sa.Column('violation_type', sa.Enum('TAB_SWITCH', 'TAB_CHANGE', 'WINDOW_BLUR', 'FULLSCREEN_EXIT', 'COPY_ATTEMPT', 'PASTE_ATTEMPT', 'RIGHT_CLICK', 'KEYBOARD_SHORTCUT', 'VISIBILITY_CHANGE', 'WINDOW_MINIMIZE', 'REFRESH', 'BACK_NAVIGATION', 'COPY', 'PASTE', 'TEXT_SELECTION', 'DEVTOOLS', 'MOUSE_LEAVE', 'NETWORK_DISCONNECT', 'RESIZE', name='violation_type'), nullable=False),
        sa.Column('warning_number', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(length=500), nullable=True),
        sa.Column('action_taken', sa.String(length=200), nullable=True),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.Column('user_agent', sa.String(length=512), nullable=True),
        sa.Column('device_fingerprint', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['exam_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_violation_records_session_id'), 'violation_records', ['session_id'], unique=False)
    op.create_index(op.f('ix_violation_records_violation_type'), 'violation_records', ['violation_type'], unique=False)

    # 22. exam_results
    op.create_table(
        'exam_results',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('session_id', sa.Uuid(), nullable=False),
        sa.Column('exam_id', sa.Uuid(), nullable=False),
        sa.Column('student_id', sa.Uuid(), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'AUTO', 'MANUAL', 'PUBLISHED', name='result_status'), nullable=False),
        sa.Column('total_marks', sa.Float(), nullable=False),
        sa.Column('obtained_marks', sa.Float(), nullable=False),
        sa.Column('percentage', sa.Float(), nullable=True),
        sa.Column('rank', sa.Integer(), nullable=True),
        sa.Column('is_passed', sa.Boolean(), nullable=True),
        sa.Column('evaluated_by', sa.String(length=20), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('question_analysis', sa.JSON(), nullable=True),
        sa.Column('time_analysis', sa.JSON(), nullable=True),
        sa.Column('feedback', sa.String(length=2000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['exam_id'], ['exams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['exam_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id')
    )
    op.create_index(op.f('ix_exam_results_exam_id'), 'exam_results', ['exam_id'], unique=False)
    op.create_index(op.f('ix_exam_results_session_id'), 'exam_results', ['session_id'], unique=True)
    op.create_index(op.f('ix_exam_results_status'), 'exam_results', ['status'], unique=False)
    op.create_index(op.f('ix_exam_results_student_id'), 'exam_results', ['student_id'], unique=False)


def downgrade() -> None:
    op.drop_table('exam_results')
    op.drop_table('violation_records')
    op.drop_table('session_answers')
    op.drop_table('exam_sessions')
    op.drop_table('exam_schedules')
    op.drop_table('exam_questions')
    op.drop_table('students')
    op.drop_table('sections')
    op.drop_table('question_versions')
    op.drop_table('question_options')
    op.drop_table('questions')
    op.drop_table('exams')
    op.drop_table('failed_questions')
    op.drop_table('uploaded_files')
    op.drop_table('topics')
    op.drop_table('subjects')
    op.drop_table('semesters')
    op.drop_table('question_bank_folders')
    op.drop_table('notifications')
    op.drop_table('audit_logs')
    op.drop_table('users')
    op.drop_table('departments')
