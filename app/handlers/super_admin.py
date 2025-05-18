from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.db import User, UserRole
from app.keyboards.admin import super_admin_menu, manage_admins_kb
from app.filters.admin import SuperAdminFilter
import os

router = Router()
router.message.filter(SuperAdminFilter())

@router.message(Command("admin"))
async def super_admin_panel(message: Message, session: AsyncSession):
    """Панель супер-администратора"""
    await message.answer("⚡️ Супер-админ панель:", reply_markup=super_admin_menu())

@router.callback_query(F.data == "manage_admins")
async def manage_admins(call: CallbackQuery, session: AsyncSession):
    """Управление администраторами"""
    admins = await session.scalars(
        select(User).where(User.role.in_([UserRole.ADMIN, UserRole.SUPER_ADMIN])))
    await call.message.edit_text("👥 Список администраторов:", reply_markup=manage_admins_kb(admins))

@router.callback_query(F.data.startswith("toggle_admin_"))
async def toggle_admin(call: CallbackQuery, session: AsyncSession):
    """Изменение статуса администратора"""
    user_id = int(call.data.split("_")[2])
    target_user = await session.get(User, user_id)
    
    if target_user.role == UserRole.SUPER_ADMIN:
        await call.answer("❌ Нельзя изменить статус супер-админа!", show_alert=True)
        return
        
    new_role = UserRole.USER if target_user.role == UserRole.ADMIN else UserRole.ADMIN
    target_user.role = new_role
    await session.commit()
    
    await call.answer(f"✅ Статус {target_user.full_name} изменен!")
    await manage_admins(call, session)  # Обновляем список