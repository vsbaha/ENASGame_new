from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.validators import is_admin
from app.keyboards.user import main_menu_kb
from app.keyboards.admin import admin_main_menu
from app.database.db import User
from sqlalchemy import select
from datetime import datetime

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession):
    """Обработка команды /start"""
    # Проверяем существование пользователя
    result = await session.execute(
        select(User).where(User.telegram_id == message.from_user.id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        # Регистрация нового пользователя
        new_user = User(
            telegram_id=message.from_user.id,
            full_name=message.from_user.full_name,
            username=message.from_user.username,
            registered_at=datetime.utcnow()
        )
        session.add(new_user)
        await session.commit()
        await message.answer("🎉 Добро пожаловать! Вы зарегистрированы.")
    else:
        await message.answer("👋 С возвращением!")

    await message.answer("Главное меню:", reply_markup=main_menu_kb())

@router.message(Command("admin"))
async def cmd_admin(message: Message, session: AsyncSession):
    """Проверка прав администратора"""
    if await is_admin(message.from_user.id, session):  # Передаем session
        await message.answer("Админ-панель", reply_markup=admin_main_menu())
    else:
        await message.answer("❌ У вас нет доступа!")

@router.message(Command("cancel"))
async def cancel_action(message: Message, state: FSMContext):
    """Отмена текущего действия"""
    await state.clear()
    await message.answer("❌ Действие отменено")