from sqlalchemy import select

from app.db.models.user import Role, User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        stmt = self._live_filter(select(User).where(User.email == email))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_clerk_id(self, clerk_id: str) -> User | None:
        stmt = self._live_filter(select(User).where(User.clerk_id == clerk_id))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create_system(self, role: Role = Role.SUPER_ADMIN) -> User:
        user = await self.get_by_email("system@internal.examshield")
        if user is None:
            user = await self.create(
                email="system@internal.examshield",
                first_name="System",
                role=role,
                is_active=True,
            )
        return user
