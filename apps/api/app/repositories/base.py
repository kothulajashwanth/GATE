from datetime import UTC
from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.db.models.base import Base, SoftDeleteMixin

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository[ModelT: Base]:
    """Thin data-access layer. Services own transactions; repos own queries."""

    model: type[ModelT]

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _live_filter(self, stmt: Any) -> Any:
        """Exclude soft-deleted rows when the model supports soft delete."""
        if issubclass(self.model, SoftDeleteMixin):
            stmt = stmt.where(self.model.deleted_at.is_(None))
        return stmt

    async def get(self, entity_id: Any) -> ModelT:
        stmt = self._live_filter(select(self.model).where(self.model.id == entity_id))
        result = await self.db.execute(stmt)
        entity = result.scalar_one_or_none()
        if entity is None:
            raise NotFoundError(f"{self.model.__name__} not found")
        return entity

    async def list(self, *, limit: int = 50, offset: int = 0) -> list[ModelT]:
        stmt = self._live_filter(select(self.model).order_by(self.model.created_at.desc()))
        stmt = stmt.limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count(self) -> int:
        from sqlalchemy import func

        stmt = self._live_filter(select(func.count()).select_from(self.model))
        result = await self.db.execute(stmt)
        return int(result.scalar_one())

    async def create(self, **values: Any) -> ModelT:
        entity = self.model(**values)
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def soft_delete(self, entity_id: Any) -> None:
        from datetime import datetime

        entity = await self.get(entity_id)
        entity.deleted_at = datetime.now(UTC)
