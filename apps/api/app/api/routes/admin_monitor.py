from typing import Annotated
import json
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Body # Added HTTPException, status, Body
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.core.auth import require_roles
from app.db.models.user import Role, User
from app.db.session import get_db
from app.db.redis import get_redis_dep
from app.schemas.active_session import StudentSessionData, AdminActiveStudent
from app.api.routes.websockets import endpoint # Added endpoint import

router = APIRouter()


@router.get("/active-students", response_model=list[AdminActiveStudent], summary="Get list of active students")
async def get_active_students(
    user: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis_dep)],
) -> list[AdminActiveStudent]:
    active_students_data = []

    # Scan for all active student session keys
    # Use scan_iter for efficient iteration over large number of keys
    async for key in redis.scan_iter("active_student_sessions:*"):
        session_json = await redis.get(key)
        if session_json:
            student_session = StudentSessionData.model_validate_json(session_json)

            # Fetch user details from DB
            user_from_db = await db.execute(select(User).where(User.id == student_session.user_id))
            user_obj = user_from_db.scalar_one_or_none()

            if user_obj:
                active_students_data.append(
                    AdminActiveStudent(
                        user_id=student_session.user_id,
                        email=user_obj.email,
                        full_name=user_obj.full_name,
                        login_time=student_session.login_time,
                        status=student_session.status,
                        exam_id=student_session.exam_id,
                        last_activity=student_session.last_activity,
                    )
                )
    return active_students_data


@router.post("/send-popup/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Send a pop-up message to a student")
async def send_popup_message(
    user_id: UUID,
    message: Annotated[str, Body(embed=True)],
    admin_user: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
) -> None:
    """
    Sends a pop-up message to a specific student via WebSocket.
    """
    await endpoint.publish([str(user_id)], {"type": "popup_message", "message": message})
    # Optionally, check if student is online/connected and return appropriate status
    # For now, we assume publish attempts to send.

@router.post("/terminate-exam/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Terminate a student's exam")
async def terminate_student_exam(
    user_id: UUID,
    admin_user: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
) -> None:
    """
    Sends a command to terminate a student's active exam via WebSocket.
    """
    await endpoint.publish([str(user_id)], {"type": "terminate_exam", "message": "Your exam has been terminated by an administrator."})
    # Here you might also want to update the student's exam session status in the DB
    # or invalidate their exam session in Redis/DB to prevent further actions.
    # This example focuses on the WebSocket message part.
