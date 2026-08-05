# ExamShield ER Diagram

```mermaid
erDiagram
    users ||--o| students : "has profile"
    departments ||--o{ semesters : contains
    departments ||--o{ sections : contains
    semesters ||--o{ sections : contains
    users ||--o{ questions : "created by"
    question_bank_folders ||--o{ questions : contains
    subjects ||--o{ questions : classifies
    questions ||--o{ question_versions : history
    users ||--o{ exams : "created by"
    exams ||--o{ exam_questions : contains
    questions ||--o{ exam_questions : "appears in"
    exams ||--o{ exam_schedules : targets
    exams ||--o{ exam_sessions : runs
    students ||--o{ exam_sessions : attempts
    exam_sessions ||--o{ session_answers : answers
    exam_sessions ||--o{ violation_records : violations
    exam_sessions ||--o| exam_results : yields
    users ||--o{ audit_logs : "acted by"
    users ||--o{ notifications : receives

    users {
        uuid id PK
        string clerk_id UK
        string email UK
        string first_name
        string last_name
        string password_hash
        enum role "super_admin|admin|student|faculty"
        string avatar_url
        string phone
        boolean is_active
        timestamp created_at
        timestamp updated_at
        timestamp deleted_at
    }
    students {
        uuid id PK
        uuid user_id FK,UK
        string roll_number UK
        uuid department_id FK
        uuid semester_id FK
        uuid section_id FK
        string phone
        string parent_name
        string parent_phone
        int enrollment_year
    }
    departments {
        uuid id PK
        string name UK
        string code UK
        text description
    }
    semesters {
        uuid id PK
        uuid department_id FK
        string name
        int ordinal
        string academic_year
    }
    sections {
        uuid id PK
        uuid department_id FK
        uuid semester_id FK
        string name
        string code
    }
    question_bank_folders {
        uuid id PK
        string name
        uuid parent_id FK
        uuid created_by FK
    }
    subjects {
        uuid id PK
        string name UK
        string code UK
        text description
        uuid department_id FK
    }
    questions {
        uuid id PK
        uuid folder_id FK
        uuid subject_id FK
        uuid created_by FK
        enum type "mcq|true_false|fill_blank|paragraph|coding|image_based|multi_select"
        text text
        string image_url
        json options
        json correct_answers
        text explanation
        text hint
        enum difficulty "easy|medium|hard"
        enum bloom_level "remember|understand|apply|analyze|evaluate|create"
        json tags
        int marks
        float negative_marks
        string topic
        text learning_outcome
        boolean is_verified
        boolean is_ai_generated
        boolean is_public
        uuid derived_from_id FK
    }
    question_versions {
        uuid id PK
        uuid question_id FK
        int version
        json snapshot
        text change_summary
        uuid changed_by FK
    }
    exams {
        uuid id PK
        string title
        text description
        uuid subject_id FK
        uuid created_by FK
        int duration_minutes
        timestamp start_at
        timestamp end_at
        int passing_marks
        boolean negative_marks_enabled
        float negative_marks_value
        boolean randomize_questions
        boolean shuffle_options
        int attempt_limit
        enum question_mode "all_at_once|one_at_a_time"
        text instructions
        string visibility
        enum status "draft|published|in_progress|completed|cancelled"
        int total_marks
        boolean security_mode
        boolean camera_proctoring_enabled
        boolean auto_submit
    }
    exam_questions {
        uuid id PK
        uuid exam_id FK
        uuid question_id FK
        int order_index
        int marks
    }
    exam_schedules {
        uuid id PK
        uuid exam_id FK
        uuid department_id FK
        uuid semester_id FK
        uuid section_id FK
    }
    exam_sessions {
        uuid id PK
        uuid exam_id FK
        uuid student_id FK
        enum status "active|submitted|terminated|expired"
        timestamp started_at
        timestamp submitted_at
        timestamp deadline_at
        int warning_count
        timestamp terminated_at
        string terminate_reason
        string ip_address
        string user_agent
        string device_fingerprint
        float score
        int time_spent_seconds
        boolean is_locked
    }
    session_answers {
        uuid id PK
        uuid session_id FK
        uuid question_id FK
        json answer
        boolean is_answered
        boolean is_correct
        float marks_awarded
        timestamp evaluated_at
        int time_taken_seconds
    }
    violation_records {
        uuid id PK
        uuid session_id FK
        enum violation_type "fullscreen_exit|tab_change|visibility_change|window_blur|window_minimize|refresh|back_navigation|right_click|copy|paste|text_selection|devtools|keyboard_shortcut|mouse_leave|network_disconnect|resize"
        int warning_number
        string reason
        string ip_address
        string user_agent
        string device_fingerprint
    }
    exam_results {
        uuid id PK
        uuid session_id FK,UK
        uuid exam_id FK
        uuid student_id FK
        enum status "pending|auto|manual|published"
        float total_marks
        float obtained_marks
        float percentage
        int rank
        boolean is_passed
        string evaluated_by
        timestamp evaluated_at
        timestamp published_at
        json question_analysis
        json time_analysis
        string feedback
    }
    audit_logs {
        uuid id PK
        uuid actor_id FK
        string action
        string entity_type
        string entity_id
        json old_value
        json new_value
        string ip_address
        string user_agent
        text details
        timestamp created_at
    }
    notifications {
        uuid id PK
        uuid user_id FK
        enum type "exam_scheduled|exam_cancelled|result_published|password_reset|announcement"
        string title
        text body
        boolean is_read
        boolean sent_via_email
        string link
        timestamp created_at
        timestamp read_at
    }
```

## Conventions

- All primary keys: UUID v4, generated client-side.
- `created_at` / `updated_at` on all entities (server defaults).
- Soft deletes via nullable `deleted_at` (indexed) on user-facing entities.
- Audit logs: append-only, never mutated.
- Indexed foreign keys + composite indexes on hot paths:
  - `(student_id, exam_id, status)` — active session lookup
  - `(subject_id, difficulty)` — question paper selection
  - `(type, bloom_level)` — question bank filters
- Enum values stored as native Postgres enums (migration-managed).
