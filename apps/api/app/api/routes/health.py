from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter()


class DatabaseHealthStatus(BaseModel):
    status: str
    database: str


class OverallHealthStatus(BaseModel):
    status: str
    version: str
    database: str


@router.get("/health", response_model=OverallHealthStatus, summary="Service health")
async def health(
    db: AsyncSession = Depends(get_db),
) -> OverallHealthStatus:
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"

    return OverallHealthStatus(
        status="healthy" if db_status == "connected" else "unhealthy",
        version="0.1.0",
        database=db_status,
    )


@router.get("/health/database", response_model=DatabaseHealthStatus, summary="Database health check")
async def health_database(
    db: AsyncSession = Depends(get_db),
) -> DatabaseHealthStatus:
    try:
        await db.execute(text("SELECT 1"))
        return DatabaseHealthStatus(
            status="healthy",
            database="connected",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
            },
        )
