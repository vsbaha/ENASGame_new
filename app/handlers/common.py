from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.validators import is_admin
from app.keyboards.user import main_menu_kb
from app.keyboards.admin import admin_main_menu
from app.database.db import User, UserRole
from sqlalchemy import select
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app.keyboards.admin import super_admin_menu
import logging
import os

SUPER_ADMINS = list(map(int, os.getenv("SUPER_ADMINS", "").split(",")))

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession):
    try:
        user = await session.get(User, message.from_user.id)
        
        if not user:
            # Создаем пользователя
            new_user = User(
                telegram_id=message.from_user.id,
                full_name=message.from_user.full_name,
                username=message.from_user.username,
                registered_at=datetime.utcnow(),
                role=UserRole.SUPER_ADMIN if message.from_user.id in SUPER_ADMINS else UserRole.USER
            )
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            await message.answer("🎉 Добро пожаловать!")
        else:
            # Обновляем роль, если пользователь в SUPER_ADMINS
            if message.from_user.id in SUPER_ADMINS and user.role != UserRole.SUPER_ADMIN:
                user.role = UserRole.SUPER_ADMIN
                await session.commit()
                await session.refresh(user)
            await message.answer("👋 С возвращением!")
            
    except IntegrityError:
        await session.rollback()
        await message.answer("👋 С возвращением!")
        
    await message.answer("Главное меню:", reply_markup=main_menu_kb())

@router.message(Command("cancel"))
async def cancel_action(message: Message, state: FSMContext):
    """Отмена текущего действия"""
    await state.clear()
    await message.answer("❌ Действие отменено")
    
@router.message(Command("admin"))
async def cmd_admin(message: Message, session: AsyncSession):
    user = await session.get(User, message.from_user.id)  # Используется message.from_user.id
    print(f"[DEBUG] User: {user}")
    
    if not user:
        await message.answer("❌ Сначала вызовите /start")
        return
    
    if user.role == UserRole.SUPER_ADMIN:
        await message.answer("⚡️ Супер-админ панель:", reply_markup=super_admin_menu())
    elif user.role == UserRole.ADMIN:
        await message.answer("⚙️ Админ-панель:", reply_markup=admin_main_menu())
    else:
        await message.answer("❌ У вас нет доступа!")