from aiogram import Bot
from app.database.db import async_session_maker, User
from sqlalchemy import select
import os

async def notify_super_admins(bot: Bot, text: str):
    """Отправка уведомлений всем супер-админам"""
    async with async_session_maker() as session:
        result = await session.execute(
            select(User.telegram_id)
            .where(User.role == "super_admin")
        )
        super_admins = result.scalars().all()
        
    for admin_id in super_admins:
        await bot.send_message(admin_id, text)