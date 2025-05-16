from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Импорты клавиатур
from app.keyboards.user import (
    main_menu_kb,
    games_list_kb,  # Было переименовано из games_keyboard
    tournaments_list_kb,
    tournament_details_kb
)

# Импорты из вашей базы данных
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