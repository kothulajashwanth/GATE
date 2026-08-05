from fastapi import APIRouter

from app.api.routes import academic, auth, health, students, users, webhooks

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(students.router, prefix="/students", tags=["students"])
api_router.include_router(academic.router, prefix="/academic", tags=["academic"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
