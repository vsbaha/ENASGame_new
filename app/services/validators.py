from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.db import Game, User, UserRole  # Убедитесь, что модель Game существует

async def validate_players_count(
    session: AsyncSession, 
    game_id: int, 
    players_count: int
) -> bool:
    """Проверка количества игроков"""
    result = await session.execute(
        select(Game).where(Game.id == game_id))  # Закрывающая скобка для select
    game = result.scalar_one()
    return game.min_players <= players_count <= game.max_players

def validate_date(date_str: str) -> datetime | None:
    """Проверка формата даты"""
    try:
        return datetime.strptime(date_str, "%d.%m.%Y %H:%M")
    except ValueError:
        return None
    
async def is_admin(user_id: int, session: AsyncSession) -> bool:
    """Проверка прав администратора через роль"""
    user = await session.scalar(
        select(User).where(User.telegram_id == user_id))
    return user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN] if user else False

async def validate_team_players(
    session: AsyncSession,
    game_id: int,
    players_count: int
) -> tuple[bool, str]:
    """Проверка соответствия количества игроков требованиям игры"""
    game = await session.get(Game, game_id)
    
    if not game:
        return False, "Игра не найдена"
    
    if players_count < game.min_players:
        return False, f"Минимальное количество игроков: {game.min_players}"
    
    if players_count > game.max_players:
        return False, f"Максимальное количество игроков: {game.max_players}"
    
    return True, ""