from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.states import RegisterTeam
from app.services.file_handling import save_file
from app.database import crud
from app.services.notifications import notify_super_admins
from app.services.validators import validate_team_players

# Импорты клавиатур
from app.keyboards.user import (
    main_menu_kb,
    games_list_kb,  # Было переименовано из games_keyboard
    tournaments_list_kb,
    tournament_details_kb
)
from app.database.db import Game, Tournament



router = Router()

@router.message(F.text == "🔍 Турниры")
async def show_games(message: Message, session: AsyncSession):
    """Показ списка игр"""
    games = await session.scalars(select(Game))
    await message.answer(
        "🎮 Выберите игру:", 
        reply_markup=games_list_kb(games)  # Исправлено название
    )

@router.callback_query(F.data.startswith("user_select_game_"))
async def show_tournaments(call: CallbackQuery, session: AsyncSession):
    """Показ турниров для выбранной игры"""
    game_id = int(call.data.split("_")[3])
    tournaments = await session.scalars(
        select(Tournament)
        .where(Tournament.game_id == game_id)
        .where(Tournament.is_active == True)
    )
    await call.message.edit_text(
        "🏆 Активные турниры:", 
        reply_markup=tournaments_list_kb(tournaments)
    )

@router.callback_query(F.data.startswith("view_tournament_"))
async def show_tournament_info(call: CallbackQuery, session: AsyncSession):
    """Детали турнира"""
    tournament_id = int(call.data.split("_")[2])
    tournament = await session.get(Tournament, tournament_id)
    
    text = (
        f"🏅 {tournament.name}\n"
        f"🕒 Дата начала: {tournament.start_date.strftime('%d.%m.%Y %H:%M')}\n"
        f"📝 Описание: {tournament.description}"
    )
    
    await call.message.edit_text(
        text, 
        reply_markup=tournament_details_kb(tournament_id)
    )
    
@router.callback_query(F.data.startswith("user_select_game_"))
async def show_tournaments(call: CallbackQuery, session: AsyncSession):
    game_id = int(call.data.split("_")[3])
    tournaments = await session.scalars(
        select(Tournament)
        .where(Tournament.game_id == game_id)
        .where(Tournament.is_active == True)
    )
    
    if not tournaments:
        await call.answer("😞 Нет активных турниров для этой игры", show_alert=True)
        return
    
    await call.message.edit_text(
        "🏆 Активные турниры:", 
        reply_markup=tournaments_list_kb(tournaments)
    )
    
@router.callback_query(F.data.startswith("register_"))
async def start_team_registration(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Начало регистрации команды"""
    tournament_id = int(call.data.split("_")[1])
    tournament = await session.get(Tournament, tournament_id)
    
    if not tournament or not tournament.is_active:
        await call.answer("❌ Турнир недоступен для регистрации", show_alert=True)
        return
    
    await state.update_data(tournament_id=tournament_id)
    await call.message.answer("🏷 Введите название команды:")
    await state.set_state(RegisterTeam.TEAM_NAME)

@router.message(RegisterTeam.TEAM_NAME)
async def process_team_name(message: Message, state: FSMContext):
    """Обработка названия команды"""
    await state.update_data(team_name=message.text)
    await message.answer("🌄 Загрузите логотип команды (фото):")
    await state.set_state(RegisterTeam.TEAM_LOGO)

@router.message(RegisterTeam.TEAM_LOGO, F.photo)
async def process_team_logo(message: Message, state: FSMContext, bot: Bot):
    """Обработка логотипа команды"""
    file_id = message.photo[-1].file_id
    file_path = await save_file(bot, file_id, "teams/logos")
    await state.update_data(logo_path=file_path)
    await message.answer("👥 Введите ID участников через запятую (например: 123,456):")
    await state.set_state(RegisterTeam.ADD_PLAYERS)
    
@router.message(RegisterTeam.ADD_PLAYERS)
async def process_players(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    """Обработка списка игроков"""
    data = await state.get_data()
    try:
        players = list(map(int, message.text.split(",")))
        if len(players) < 1:
            raise ValueError
        
        # Проверка требований игры
        tournament = await session.get(Tournament, data['tournament_id'])
        is_valid, message = await validate_team_players(
            session=session,
            game_id=tournament.game_id,
            players_count=len(players)
        )
        
        if not is_valid:
            await message.answer(f"❌ {message}")
            return
        
        # Создание команды
        team_data = {
            "tournament_id": data['tournament_id'],
            "captain_tg_id": message.from_user.id,
            "team_name": data['team_name'],
            "logo_path": data['logo_path']
        }
        team = await crud.create_team(session, team_data)
        await crud.add_players_to_team(session, team.id, players)
        
        # Отправка подтверждения
        await message.answer(
            f"✅ Команда <b>{data['team_name']}</b> успешно зарегистрирована!\n"
            f"ID участников: {', '.join(map(str, players))}",
            parse_mode="HTML"
        )
        
        # Уведомление админов
        await notify_super_admins(
            bot=bot,
            text=f"Новая команда зарегистрирована на турнир {tournament.name}!"
        )
        
        await state.clear()
        
    except Exception as e:
        await message.answer("❌ Неверный формат ID! Введите числа через запятую.")