from fastapi import APIRouter

from app.api.routes import academic, auth, exam_engine, exams, health, question_bank, questions, results, sessions, student_exams, students, users, webhooks

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(students.router, prefix="/students", tags=["students"])
api_router.include_router(academic.router, prefix="/academic", tags=["academic"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(exams.router, prefix="/exams", tags=["exams"])
api_router.include_router(exam_engine.router, prefix="/exam-session", tags=["exam-engine"])
api_router.include_router(student_exams.router, prefix="/student/exams", tags=["student-exams"])
api_router.include_router(results.router, prefix="/student/results", tags=["student-results"])
api_router.include_router(question_bank.router, prefix="/question-bank", tags=["question-bank"])
api_router.include_router(questions.router, prefix="/questions", tags=["questions"])
api_router.include_router(sessions.router, prefix="/exam-sessions", tags=["exam-sessions"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
