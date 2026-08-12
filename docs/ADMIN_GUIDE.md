# GATE IGNITE - Administrator Operations Guide

Welcome to the **GATE IGNITE** administration portal. This guide details operational workflows for managing college students, building question banks, generating AI questions, scheduling proctored examinations, monitoring live sessions, publishing results, and exporting analytical reports.

---

## 1. Student Management (`/admin/students`)
- **Single Student Creation**: Click **Add Student**, enter roll number, full name, email, department, semester, and section.
- **Bulk Excel Import**: Click **Import Students (XLSX)**, select Excel file matching the template columns (`roll_number`, `full_name`, `email`, `department`, `semester`, `section`), review preview table, and confirm import.
- **Bulk Excel Export**: Click **Export XLSX** to download the complete student directory.

---

## 2. Question Repository & AI Generator (`/admin/question-bank`, `/admin/ai-generator`)
- **Document Import Pipeline**: Upload PDF, DOCX, TXT, or XLSX question documents. The pipeline extracts questions, detects options/correct answers, logs invalid questions in `FailedQuestion`, and stores verified questions.
- **AI Question Generation**:
  1. Navigate to `/admin/ai-generator`.
  2. Select Subject, Topic, Subtopic, Question Count, Question Type, Bloom's Taxonomy Level (`remember`, `understand`, `apply`, `analyze`, `evaluate`, `create`), and Difficulty Distribution (`easy`, `medium`, `hard`).
  3. Click **Generate Questions**.
  4. Review generated questions in the Human Review Queue, edit text/options if needed, and click **Approve Question** to persist into PostgreSQL.

---

## 3. Exam Builder & Scheduling (`/admin/exams`, `/admin/exams/create`)
- **Multi-Step Exam Wizard**:
  - **Step 1 Basic Info**: Exam title, subject, duration, active start/end window.
  - **Step 2 Questions**: Pick approved questions from Question Bank, override marks per question.
  - **Step 3 Rules & Cohort**: Configure negative marking, proctoring security mode, camera monitoring, and target Department/Semester/Section cohorts.
  - **Step 4 Publish Execution**: Run publish readiness checklist and publish exam schedule to student portals.

---

## 4. Live Exam Monitoring (`/admin/exams/live`)
- Real-time tracking of active proctored exam sessions.
- View warning counters (e.g. 1/3 Warnings), security risk statuses (`NORMAL`, `WARNING`, `HIGH_RISK`, `TERMINATED`).
- Click **Timeline** to view chronological proctoring violation event logs.
- Click **Force Terminate** to immediately lock an attempt suspected of cheating.

---

## 5. Results & Analytics (`/admin/results`, `/admin/analytics`)
- **Batch Publishing**: Click **Publish All Results** to release evaluated scores to student dashboards.
- **Recalculation**: Click **Recalculate** on any result to refresh score snapshots after question answer key updates.
- **CSV Report Export**: Click **Export CSV Report** on `/admin/analytics` to download complete institutional grade sheets.
