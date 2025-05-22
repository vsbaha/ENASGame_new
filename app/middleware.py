from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, ChatMemberUpdated
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.db import User, UserRole
from typing import Callable, Awaitable, Dict, Any
import logging
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from app.keyboards.user import subscription_kb
import os
from dotenv import load_dotenv
load_dotenv()
logger = logging.getLogger(__name__)
REQUIRED_CHANNELS = [ch.strip() for ch in os.getenv("REQUIRED_CHANNELS", "").split(",") if ch.strip()]
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

class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        # Пропускаем команду /start
        if isinstance(event, Message) and event.text and event.text.startswith("/start"):
            return await handler(event, data)

        bot = data.get("bot")
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        if user_id:
            not_subscribed = []
            for channel in REQUIRED_CHANNELS:
                try:
                    member = await bot.get_chat_member(channel, user_id)
                    if member.status not in ("member", "administrator", "creator"):
                        not_subscribed.append(channel)
                except Exception:
                    not_subscribed.append(channel)
            if not_subscribed:
                channels_list = "\n".join([f"• {ch}" for ch in not_subscribed])
                text = (
                    "❗ Для использования бота подпишитесь на все каналы:\n"
                    f"{channels_list}\n\n"
                    "После подписки нажмите <b>Проверить подписку</b>."
                )
                if isinstance(event, Message):
                    await event.answer(text, reply_markup=subscription_kb(), parse_mode="HTML")
                elif isinstance(event, CallbackQuery):
                    await event.message.answer(text, reply_markup=subscription_kb(), parse_mode="HTML")
                return  # Прерываем цепочку, если не подписан
        return await handler(event, data)  # <-- ВАЖНО! Пропускаем дальше, если подписан