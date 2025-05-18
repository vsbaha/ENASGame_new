from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.db import User, UserRole
from app.database.crud import update_user_role
from app.keyboards.admin import super_admin_menu, manage_admins_kb, admin_main_menu
from app.filters.admin import SuperAdminFilter
from app.states import AdminActions
from aiogram.fsm.context import FSMContext
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
    await call.message.edit_text("👥 Нажмите на Ник админа чтоб удалить его:", reply_markup=manage_admins_kb(admins))

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
    
@router.callback_query(F.data == "back_to_super_admin")
async def back_to_super_admin(call: CallbackQuery):
    await call.message.edit_text("⚙️ Супер Админ-панель:", reply_markup=super_admin_menu())
    
@router.callback_query(F.data == "admin_main_menu")
async def admin_main_menu(call: CallbackQuery):
    await call.message.edit_text("⚙️ Админ-панель:", reply_markup=admin_main_menu())
    
@router.callback_query(F.data == "manage_admins")
async def manage_admins(call: CallbackQuery, session: AsyncSession):
    """Показать список админов"""
    admins = await session.scalars(
        select(User).where(User.role.in_([UserRole.ADMIN, UserRole.SUPER_ADMIN]))
    )
    await call.message.edit_text("👥 Список администраторов:", reply_markup=manage_admins_kb(admins))

# Начало добавления админа
@router.callback_query(F.data == "add_admin")
async def start_add_admin(call: CallbackQuery, state: FSMContext):
    """Запрос юзернейма пользователя"""
    await call.message.answer("📝 Введите юзернейм пользователя (например, @username):")
    await state.set_state(AdminActions.WAITING_ADMIN_USERNAME)

@router.message(AdminActions.WAITING_ADMIN_USERNAME)
async def process_admin_username(message: Message, session: AsyncSession, state: FSMContext):
    username = message.text.strip().replace("@", "")  # Удаляем @, если пользователь его ввел
    
    if not username:
        await message.answer("❌ Юзернейм не может быть пустым!")
        return
    
    target_user = await session.scalar(
        select(User).where(User.username == username))
    
    if not target_user:
        await message.answer("❌ Пользователь не найден!")
    elif target_user.role == UserRole.SUPER_ADMIN:
        await message.answer("🚫 Нельзя изменить статус супер-админа!")
    else:
        success = await update_user_role(
            session=session,
            username=username,
            new_role=UserRole.ADMIN
        )
        if success:
            await message.answer(f"✅ Пользователь @{username} стал администратором!")
        else:
            await message.answer("⚠️ Произошла ошибка!")
    
    await state.clear()