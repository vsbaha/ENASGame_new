from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.db import User, UserRole, Tournament, TournamentStatus, Game
from app.database.crud import update_user_role
from app.keyboards.admin import super_admin_menu, manage_admins_kb, admin_main_menu, moderation_actions_kb
from app.filters.admin import SuperAdminFilter
from app.states import AdminActions
from aiogram.fsm.context import FSMContext

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
    
@router.callback_query(F.data == "switch_to_admin_menu")
async def switch_to_admin_menu(call: CallbackQuery):
    """Переключение на обычное админ-меню"""
    await call.message.edit_text(
        "⚙️ Админ-панель:",
        reply_markup=admin_main_menu()  # Используем клавиатуру из admin.py
    )
    
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
    
@router.callback_query(F.data == "back_to_super_admin")
async def switch_to_admin_menu(call: CallbackQuery):
    await call.message.edit_text(
        "⚙️ Админ-панель:",
        reply_markup=super_admin_menu()  # Используем клавиатуру из admin.py
    )
    
@router.callback_query(F.data == "moderate_tournaments")
async def show_pending_tournaments(call: CallbackQuery, session: AsyncSession):
    """Список турниров на модерации"""
    tournaments = await session.scalars(
        select(Tournament)
        .where(Tournament.status == TournamentStatus.PENDING)
    )
    
    builder = InlineKeyboardBuilder()
    
    # Кнопки турниров (по одной в ряд)
    for tournament in tournaments:
        builder.button(
            text=f"{tournament.name}",
            callback_data=f"view_pending_tournament_{tournament.id}"
        )
    builder.adjust(1)  # По одному в ряд
    
    # Кнопка "Назад" отдельным рядом
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад", 
            callback_data="back_to_super_admin"
        )
    )
    
    await call.message.edit_text(
        "📋 Турниры на модерации:",
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data.startswith("view_pending_tournament_"))
async def view_pending_tournament(call: CallbackQuery, session: AsyncSession, bot: Bot):
    """Детали турнира для модерации"""
    tournament_id = int(call.data.split("_")[3])
    tournament = await session.get(Tournament, tournament_id)
    game = await session.get(Game, tournament.game_id)
    
    # Формируем сообщение
    text = (
        f"🏆 {tournament.name}\n\n"
        f"🎮 Игра: {game.name if game else 'Не указана'}\n"
        f"📅 Дата старта: {tournament.start_date.strftime('%d.%m.%Y %H:%M')}\n"
        f"📝 Описание: {tournament.description}"
    )
    
    # Отправляем логотип
    try:
        logo = FSInputFile(tournament.logo_path)
        await bot.send_photo(call.from_user.id, photo=logo, caption=text)
    except Exception as e:
        await call.message.answer("⚠️ Логотип не найден!")
    
    # Отправляем регламент
    try:
        regulations = FSInputFile(tournament.regulations_path)
        await bot.send_document(
            call.from_user.id,
            document=regulations,
            caption="📄 Регламент турнира",
        )
        await call.message.answer(
        "Выберите действие:",
        reply_markup=moderation_actions_kb(tournament_id)
        )
    except Exception as e:
        await call.message.answer("⚠️ Регламент не найден!")

@router.callback_query(F.data.startswith("approve_tournament_"))
async def approve_tournament(call: CallbackQuery, session: AsyncSession):
    tournament_id = int(call.data.split("_")[2])
    tournament = await session.get(Tournament, tournament_id)
    
    # Обновляем статус
    tournament.status = TournamentStatus.APPROVED
    await session.commit()
    
    # Уведомляем создателя
    creator = await session.get(User, tournament.created_by)
    await call.message.bot.send_message(
        creator.telegram_id,
        f"🎉 Ваш турнир «{tournament.name}» одобрен!"
    )
    
    # Удаляем сообщение с кнопками и показываем уведомление
    await call.message.delete()  # Удаляем сообщение с кнопками
    await call.answer("✅ Турнир одобрен!", show_alert=True)

@router.callback_query(F.data.startswith("reject_tournament_"))
async def reject_tournament(call: CallbackQuery, session: AsyncSession):
    tournament_id = int(call.data.split("_")[2])
    tournament = await session.get(Tournament, tournament_id)
    
    tournament.status = TournamentStatus.REJECTED
    await session.commit()
    
    creator = await session.get(User, tournament.created_by)
    await call.message.bot.send_message(
        creator.telegram_id,
        f"❌ Ваш турнир «{tournament.name}» отклонен!"
    )
    
    await call.message.delete()  # Удаляем сообщение с кнопками
    await call.answer("❌ Турнир отклонен!", show_alert=True)