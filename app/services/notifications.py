from aiogram import Bot
from app.database.db import async_session_maker, User, UserRole
from sqlalchemy import select
import os

async def notify_super_admins(bot: Bot, text: str):
    """Уведомления супер-админов с использованием UserRole"""
    async with async_session_maker() as session:
        super_admins = await session.scalars(
            select(User.telegram_id)
            .where(User.role == UserRole.SUPER_ADMIN)  # Исправлено
        )
        for admin_id in super_admins:
            await bot.send_message(admin_id, text)