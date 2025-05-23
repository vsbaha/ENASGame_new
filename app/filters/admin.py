from aiogram.filters import BaseFilter
from aiogram.types import Message
from app.services.validators import is_admin
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.db import User, UserRole  # Добавляем импорт моделей
from sqlalchemy import select

class AdminFilter(BaseFilter):
    async def __call__(self, message: Message, session: AsyncSession) -> bool:
        user = await session.scalar(select(User).where(User.telegram_id == message.from_user.id))
        return user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN] if user else False

class SuperAdminFilter(BaseFilter):
    async def __call__(self, message: Message, session: AsyncSession) -> bool:
        user = await session.scalar(select(User).where(User.telegram_id == message.from_user.id))
        return user.role == UserRole.SUPER_ADMIN if user else False