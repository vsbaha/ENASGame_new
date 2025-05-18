from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, ChatMemberUpdated
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.db import User, UserRole
from typing import Callable, Awaitable, Dict, Any
import logging

logger = logging.getLogger(__name__)

class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, session_maker):
        self.session_maker = session_maker

    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any]
    ) -> Any:
        async with self.session_maker() as session:
            data["session"] = session
            return await handler(event, data)

class AdminCheckMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        session = data["session"]
        bot = data["bot"]
        user_id = None

        # Пропускаем команду /start
        if isinstance(event, Message) and event.text == "/start":
            return await handler(event, data)

        # Получаем user_id
        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id
        
        if not user_id:
            return await handler(event, data)  # Пропускаем события без user_id

        # Проверка пользователя
        try:
            user = await session.scalar(
                select(User).where(User.telegram_id == user_id))
            
            if not user or user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
                await bot.send_message(user_id, "🚫 Недостаточно прав!")
                return
        except Exception as e:
            logger.error(f"AdminCheck error: {e}")
            return

        return await handler(event, data)

class ErrorHandlerMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        try:
            return await handler(event, data)
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            bot = data.get("bot")
            if isinstance(event, (Message, CallbackQuery)):
                await bot.send_message(event.from_user.id, "⚠️ Произошла ошибка!")
            return