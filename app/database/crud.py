from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from .db import User, Tournament, Team, Player, UserRole, BlackList, TeamStatus
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
    users = await session.scalar(select(func.count(User.id)))
    active_tournaments = await session.scalar(
        select(func.count(Tournament.id))
        .where(Tournament.is_active == True)
    )
    # Считаем только команды со статусом APPROVED
    teams = await session.scalar(
        select(func.count(Team.id)).where(Team.status == TeamStatus.APPROVED)
    )
    return {
        "users": users,
        "active_tournaments": active_tournaments,
        "teams": teams
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

async def add_to_blacklist(session, user_id: int, banned_by: int, reason: str = None):
    session.add(BlackList(user_id=user_id, banned_by=banned_by, reason=reason))
    await session.commit()

async def remove_from_blacklist(session, user_id: int):
    await session.execute(
        BlackList.__table__.delete().where(BlackList.user_id == user_id)
    )
    await session.commit()

async def is_blacklisted(session, user_id: int) -> bool:
    res = await session.get(BlackList, user_id)
    return res is not None

async def get_blacklist_entry(session, user_id: int):
    return await session.get(BlackList, user_id)