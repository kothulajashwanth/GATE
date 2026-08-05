from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, guid, guid_pk


class NotificationType(StrEnum):
    EXAM_SCHEDULED = "exam_scheduled"
    EXAM_CANCELLED = "exam_cancelled"
    RESULT_PUBLISHED = "result_published"
    PASSWORD_RESET = "password_reset"
    ANNOUNCEMENT = "announcement"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[object] = guid_pk()
    user_id: Mapped[object] = mapped_column(
        guid(), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    type: Mapped[NotificationType] = mapped_column(
        SAEnum(NotificationType, name="notification_type"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    sent_via_email: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
