from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, String, Text, DateTime, Boolean, BigInteger, CheckConstraint
from datetime import datetime
from typing import Optional, List
from enum import Enum

import os

class Base(DeclarativeBase):
    pass

DATABASE_URL = os.getenv("DB_URL", "sqlite+aiosqlite:///./admin.db")
engine = create_async_engine(DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"
    
class TournamentStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(150))
    username: Mapped[Optional[str]] = mapped_column(String(32))
    registered_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    role: Mapped[UserRole] = mapped_column(default=UserRole.USER)
    added_by: Mapped[Optional[int]] = mapped_column(BigInteger)



class Game(Base):
    __tablename__ = "games"
    __table_args__ = (
        CheckConstraint('min_players <= max_players', name='min_max_players_check'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    min_players: Mapped[int]
    max_players: Mapped[int]
    tournaments: Mapped[List["Tournament"]] = relationship(back_populates="game")

class Tournament(Base):
    __tablename__ = "tournaments"
    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    logo_path: Mapped[str] = mapped_column(String(200))
    start_date: Mapped[datetime]
    description: Mapped[str] = mapped_column(Text)
    regulations_path: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(default=True)
    game: Mapped["Game"] = relationship(back_populates="tournaments")
    teams: Mapped[List["Team"]] = relationship(back_populates="tournament", cascade="all, delete-orphan")
    status: Mapped[TournamentStatus] = mapped_column(default=TournamentStatus.PENDING)
    created_by: Mapped[int] = mapped_column(BigInteger)  # ID создателя

class Team(Base):
    __tablename__ = "teams"
    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"), index=True)
    captain_tg_id: Mapped[int] = mapped_column(BigInteger, index=True)
    team_name: Mapped[str] = mapped_column(String(50))
    logo_path: Mapped[str] = mapped_column(String(200))
    is_approved: Mapped[bool] = mapped_column(default=False)
    tournament: Mapped["Tournament"] = relationship(back_populates="teams")
    players: Mapped[List["Player"]] = relationship(back_populates="team")

class Player(Base):
    __tablename__ = "players"
    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    is_substitute: Mapped[bool] = mapped_column(default=False)
    team: Mapped["Team"] = relationship(back_populates="players")
    
class Broadcast(Base):
    __tablename__ = "broadcasts"
    id: Mapped[int] = mapped_column(primary_key=True)
    message: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # Пример




async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)