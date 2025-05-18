from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, PollAnswer, ChatMemberUpdated
from typing import Callable, Awaitable, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from .database.db import async_session_maker
from app.database.db import UserRole, User
from .services.validators import is_admin
import logging
from sqlalchemy.exc import IntegrityError
from datetime import datetime

# app/middleware.py
class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, session_pool):
        self.session_pool = session_pool

    async def __call__(self, handler, event, data):
        async with self.session_pool() as session:
            data["session"] = session
            try:
                return await handler(event, data)
            finally:
                await session.close()  # Закрываем сессию после обработки
    
class AdminCheckMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        session = data["session"]
        
        # Получаем user_id из события
        user_id = None
        if event.message:
            user_id = event.message.from_user.id
        elif event.callback_query:
            user_id = event.callback_query.from_user.id
        
        if not user_id:
            await event.answer("🚫 Доступ запрещен!")
            return

        user = await session.get(User, user_id)
        
        if not user or user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            await event.answer("🚫 Недостаточно прав!")
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
