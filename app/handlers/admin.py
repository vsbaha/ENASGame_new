from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
import uuid
from app.database import crud
from app.services.validators import is_admin
from app.filters.admin import AdminFilter
from app.states import CreateTournament
from app.services.file_handling import save_file
import logging
import os

from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.database.db import Tournament, Game
from app.keyboards.admin import (
    admin_main_menu,
    tournaments_management_kb,
    tournament_actions_kb,
    confirm_action_kb,
    back_to_admin_kb
)

router = Router()
logger = logging.getLogger(__name__)

# Главное админ-меню
@router.message(F.text == "Админ-панель")
async def admin_panel(message: Message):
    await message.answer("⚙️ Админ-панель:", reply_markup=admin_main_menu())
    
@router.callback_query(F.data == "stats")
async def show_stats(call: CallbackQuery, session: AsyncSession):
    """Показ статистики"""
    stats = await crud.get_statistics(session)
    text = (
        "📊 Статистика:\n"
        f"👥 Пользователей: {stats['users']}\n"
        f"🏆 Активных турниров: {stats['active_tournaments']}\n"
        f"👥 Зарегистрированных команд: {stats['teams']}"
    )
    await call.message.edit_text(text, reply_markup=back_to_admin_kb())
    
@router.callback_query(F.data == "back_to_admin")
async def back_to_admin(call: CallbackQuery):
    await call.message.edit_text("⚙️ Админ-панель:", reply_markup=admin_main_menu())

# Управление турнирами
@router.callback_query(F.data == "manage_tournaments")
async def manage_tournaments(call: CallbackQuery, session: AsyncSession):
    tournaments = await session.scalars(select(Tournament))
    await call.message.edit_text(
        "Управление турнирами:", 
        reply_markup=tournaments_management_kb(tournaments)
    )


    
# Начало создания турнира
@router.callback_query(F.data == "create_tournament")
async def start_creation(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Начало создания турнира - выбор игры"""
    try:
        # Получаем список всех игр
        games = await session.scalars(select(Game))
        if not games:
            await call.answer("❌ Нет доступных игр! Сначала добавьте игры.", show_alert=True)
            return

        # Создаем клавиатуру с играми
        builder = InlineKeyboardBuilder()
        for game in games:
            builder.button(
                text=game.name, 
                callback_data=f"admin_select_game_{game.id}"  # Исправленный префикс
            )
        builder.adjust(1)
        
        await call.message.answer("🎮 Выберите игру:", reply_markup=builder.as_markup())
        await state.set_state(CreateTournament.SELECT_GAME)
        logger.info(f"User {call.from_user.id} started tournament creation")

    except Exception as e:
        logger.error(f"Error in start_creation: {e}")
        await call.answer("⚠️ Произошла ошибка!", show_alert=True)

@router.callback_query(F.data.startswith("admin_select_game_"), CreateTournament.SELECT_GAME)
async def select_game(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Обработка выбора игры"""
    try:
        # Извлекаем ID игры из callback_data
        game_id = int(call.data.split("_")[3])
        logger.debug(f"Selected game ID: {game_id}")
        
        # Проверяем существование игры
        game = await session.get(Game, game_id)
        if not game:
            await call.answer("❌ Игра не найдена!", show_alert=True)
            return

        # Обновляем состояние и запрашиваем название
        await state.update_data(game_id=game_id)
        await call.message.delete()
        await call.message.answer(
            f"🎮 Игра: <b>{game.name}</b>\n🏷 Введите название турнира:", 
            parse_mode="HTML"
        )
        await state.set_state(CreateTournament.NAME)
        logger.info(f"Game {game_id} selected, waiting for name")

    except Exception as e:
        logger.error(f"Error in select_game: {e}")
        await call.answer("⚠️ Ошибка выбора игры!", show_alert=True)

# Обработка названия
@router.message(CreateTournament.NAME)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("🌄 Загрузите логотип (фото):")
    await state.set_state(CreateTournament.LOGO)

# Обработка логотипа
@router.message(CreateTournament.LOGO, F.photo)
async def process_logo(message: Message, state: FSMContext, bot: Bot):
    file_id = message.photo[-1].file_id
    file_path = await save_file(bot, file_id, "tournaments/logos")
    await state.update_data(logo_path=file_path)
    await message.answer("📅 Введите дату начала (ДД.ММ.ГГГГ ЧЧ:ММ):")
    await state.set_state(CreateTournament.START_DATE)

# Обработка даты
@router.message(CreateTournament.START_DATE)
async def process_date(message: Message, state: FSMContext):
    try:
        date = datetime.strptime(message.text, "%d.%m.%Y %H:%M")
        await state.update_data(start_date=date)
        await message.answer("📝 Введите описание:")
        await state.set_state(CreateTournament.DESCRIPTION)
    except ValueError:
        await message.answer("❌ Неверный формат даты! Пример: 01.01.2025 14:00")

# Обработка описания
@router.message(CreateTournament.DESCRIPTION)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("📄 Загрузите регламент (PDF):")
    await state.set_state(CreateTournament.REGULATIONS)

# Обработка регламента
@router.message(CreateTournament.REGULATIONS, F.document)
async def finish_creation(message: Message, state: FSMContext, bot: Bot, session: AsyncSession):
    if message.document.mime_type != "application/pdf":
        return await message.answer("❌ Только PDF-файлы!")
    
    file_path = await save_file(bot, message.document.file_id, "tournaments/regulations")
    data = await state.get_data()
    
    # Создаем турнир
    tournament = Tournament(
        game_id=data['game_id'],
        name=data['name'],
        logo_path=data['logo_path'],
        start_date=data['start_date'],
        description=data['description'],
        regulations_path=file_path,
        is_active=True
    )
    
    session.add(tournament)
    await session.commit()
    
    await message.answer(
        f"✅ Турнир <b>{data['name']}</b> успешно создан!\n"
        f"Дата старта: {data['start_date'].strftime('%d.%m.%Y %H:%M')}",
        parse_mode="HTML"
    )
    await state.clear()
    
@router.callback_query(F.data.startswith("edit_tournament_"))
async def show_tournament_details(call: CallbackQuery, session: AsyncSession):
    """Детальная информация о турнире"""
    tournament_id = int(call.data.split("_")[2])
    tournament = await session.get(Tournament, tournament_id)
    
    if not tournament:
        await call.answer("❌ Турнир не найден!", show_alert=True)
        return

    # Получаем связанную игру
    game = await session.get(Game, tournament.game_id)
    
    # Формируем текст
    text = (
        f"🏆 <b>{tournament.name}</b>\n\n"
        f"🎮 Игра: {game.name if game else 'Не указана'}\n"
        f"🕒 Дата старта: {tournament.start_date.strftime('%d.%m.%Y %H:%M')}\n"
        f"📝 Описание: {tournament.description}\n"
        f"🔄 Статус: {'Активен ✅' if tournament.is_active else 'Неактивен ❌'}"
    )

    try:
        # Отправляем логотип
        logo = FSInputFile(tournament.logo_path)
        await call.message.answer_photo(
            photo=logo,
            caption=text,
            parse_mode="HTML"
        )
    except Exception as e:
        await call.message.answer("⚠️ Логотип не найден!")
        await call.message.answer(text, parse_mode="HTML")

    try:
        # Отправляем регламент
        regulations = FSInputFile(tournament.regulations_path)
        await call.message.answer_document(
            document=regulations,
            caption="📄 Регламент турнира"
        )
    except Exception as e:
        await call.message.answer("⚠️ Регламент не найден!")

    # Кнопки управления
    await call.message.answer(
        "Действия с турниром:",
        reply_markup=tournament_actions_kb(tournament_id)
    )
    
@router.callback_query(F.data.startswith("delete_tournament_"))
async def delete_tournament(call: CallbackQuery, session: AsyncSession):
    """Удаление турнира с файлами"""
    tournament_id = int(call.data.split("_")[2])
    tournament = await session.get(Tournament, tournament_id)
    
    if not tournament:
        await call.answer("❌ Турнир не найден!", show_alert=True)
        return

    # Удаляем файлы
    import os
    if os.path.exists(tournament.logo_path):
        os.remove(tournament.logo_path)
    if os.path.exists(tournament.regulations_path):
        os.remove(tournament.regulations_path)
    
    # Удаляем из БД
    await session.delete(tournament)
    await session.commit()
    
    await call.message.edit_text("✅ Турнир и все файлы удалены")
    
@router.callback_query(F.data == "back_to_tournaments")
async def back_to_tournaments_list(call: CallbackQuery, session: AsyncSession):
    try:
        # Удаляем сообщение с действиями
        await call.message.delete()
        
        # Получаем обновленный список турниров
        tournaments = await session.scalars(select(Tournament))
        
        # Отправляем новый список
        await call.message.answer(
            "Управление турнирами:",
            reply_markup=tournaments_management_kb(tournaments)
        )
    except Exception as e:
        logging.error(f"Back error: {e}")
        await call.answer("⚠️ Ошибка возврата!")