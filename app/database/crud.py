from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from .db import User, Game, Tournament, Team, Player, UserRole
from sqlalchemy import func

async def get_user(session: AsyncSession, tg_id: int) -> User | None:
    return await session.scalar(select(User).where(User.telegram_id == tg_id))

async def create_user(session: AsyncSession, tg_id: int, full_name: str, username: str = None) -> User:
    user = User(telegram_id=tg_id, full_name=full_name, username=username)
    session.add(user)
    await session.commit()
    return user

async def create_tournament(session: AsyncSession, data: dict) -> Tournament:
    tournament = Tournament(**data)
    session.add(tournament)
    await session.commit()
    return tournament

async def delete_tournament(session: AsyncSession, tournament_id: int) -> None:
    await session.execute(delete(Tournament).where(Tournament.id == tournament_id))
    await session.commit()

async def create_team(session: AsyncSession, data: dict) -> Team:
    team = Team(**data)
    session.add(team)
    await session.commit()
    return team

async def add_players_to_team(session: AsyncSession, team_id: int, players: list[int], is_substitute: bool = False):
    for user_id in players:
        player = Player(team_id=team_id, user_id=user_id, is_substitute=is_substitute)
        session.add(player)
    await session.commit()
    
async def get_statistics(session: AsyncSession) -> dict:
    """Сбор статистики"""
    users_count = await session.scalar(select(func.count(User.id)))
    active_tournaments = await session.scalar(
        select(func.count(Tournament.id))
        .where(Tournament.is_active == True)
    )
    teams_count = await session.scalar(select(func.count(Team.id)))
    return {
        "users": users_count,
        "active_tournaments": active_tournaments,
        "teams": teams_count
    }
    
async def update_user_role(
    session: AsyncSession, 
    username: str,  # Используем юзернейм вместо ID
    new_role: UserRole
) -> bool:
    """Обновление роли пользователя по юзернейму"""
    user = await session.scalar(
        select(User).where(User.username == username))
    
    if not user:
        return False
    user.role = new_role
    await session.commit()
    return True