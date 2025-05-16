from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.db import Game, User  # Убедитесь, что модель Game существует

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
    """Проверка прав администратора"""
    result = await session.execute(select(User).where(User.telegram_id == user_id))
    user = result.scalar_one_or_none()
    return user.is_admin if user else False