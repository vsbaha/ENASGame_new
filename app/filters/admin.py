from aiogram.filters import BaseFilter
from aiogram.types import Message
from app.services.validators import is_admin
from sqlalchemy.ext.asyncio import AsyncSession

class AdminFilter(BaseFilter):
    async def __call__(self, message: Message, session: AsyncSession) -> bool:
        return await is_admin(message.from_user.id, session)