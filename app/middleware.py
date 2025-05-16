from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Awaitable, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from .database.db import async_session_maker
from .services.validators import is_admin
import logging

# app/middleware.py
class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, session_pool):
        self.session_pool = session_pool

    async def __call__(self, handler, event, data):
        async with self.session_pool() as session:
            data["session"] = session  # Добавляем сессию в data
            return await handler(event, data)

class AdminCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, dict], Awaitable[Any]],
        event: Any,
        data: dict,
    ) -> Any:
        # Проверяем наличие from_user
        if not hasattr(event, 'from_user') or not event.from_user:
            return await handler(event, data)

        # Получаем сессию из data
        session: AsyncSession = data.get("session")
        if not session:
            logging.error("Session not found in data!")
            return

        # Проверяем права
        if not await is_admin(event.from_user.id, session):  # Передаем session
            if isinstance(event, Message):
                await event.answer("❌ У вас нет прав администратора!")
            elif isinstance(event, CallbackQuery):
                await event.answer("❌ Доступ запрещен!", show_alert=True)
            return

        return await handler(event, data)

class ErrorHandlerMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        try:
            return await handler(event, data)
        except Exception as e:
            logging.error(f"Error: {e}", exc_info=True)
            bot = data.get("bot")
            chat_id = event.from_user.id if hasattr(event, 'from_user') else None
            if bot and chat_id:
                await bot.send_message(chat_id, "⚠️ Произошла ошибка!")
