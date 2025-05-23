from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.database import crud
from app.services.validators import is_admin
from app.filters.admin import AdminFilter
from aiogram.filters import StateFilter
from app.states import CreateTournament
from app.services.file_handling import save_file
from app.services.notifications import notify_super_admins
import logging
import os

from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from app.database.db import Tournament, Game, TournamentStatus, UserRole, User, Tournament, GameFormat, Team, User, Player, TeamStatus
from app.keyboards.admin import (
    admin_main_menu,
    tournaments_management_kb,
    tournament_actions_kb,
    back_to_admin_kb,
    team_request_kb,
    tournament_status_kb,
    team_request_preview_kb
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


@router.callback_query(F.data == "manage_tournaments")
async def manage_tournaments(call: CallbackQuery, session: AsyncSession):
    """Управление турнирами (только одобренные для обычных админов)"""
    user = await session.scalar(
        select(User).where(User.telegram_id == call.from_user.id)
    )
    
    # Для супер-админа показываем все турниры
    if user.role == UserRole.SUPER_ADMIN:
        tournaments = await session.scalars(select(Tournament))
    # Для обычного админа — только одобренные или созданные им
    else:
        tournaments = await session.scalars(
            select(Tournament)
            .where(Tournament.status == TournamentStatus.APPROVED)
            .where(Tournament.created_by == user.id)
        )
    
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

@router.callback_query(
    StateFilter(CreateTournament.SELECT_GAME),
    F.data.startswith("admin_select_game_")
)
async def select_game(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    game_id = int(call.data.split("_")[3])
    game = await session.get(Game, game_id)
    if not game:
        await call.answer("❌ Игра не найдена!", show_alert=True)
        return

    # Получаем форматы для выбранной игры
    formats = await session.scalars(
        select(GameFormat).where(GameFormat.game_id == game_id)
    )
    formats = list(formats)
    if not formats:
        await call.answer("❌ Нет форматов для этой игры!", show_alert=True)
        return

    # Клавиатура с форматами
    builder = InlineKeyboardBuilder()
    for fmt in formats:
        builder.button(
            text=f"{fmt.format_name} (до {fmt.max_players_per_team})",
            callback_data=f"admin_select_format_{fmt.id}"
        )
    builder.adjust(1)
    await call.message.edit_text(
        f"🎮 Игра: <b>{game.name}</b>\nВыберите формат:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await state.update_data(game_id=game_id)
    await state.set_state(CreateTournament.SELECT_FORMAT)

# Обработка выбора формата
@router.callback_query(F.data.startswith("admin_select_format_"))
async def select_format(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    format_id = int(call.data.split("_")[3])
    fmt = await session.get(GameFormat, format_id)
    if not fmt:
        await call.answer("❌ Формат не найден!", show_alert=True)
        return

    await state.update_data(format_id=format_id)
    await call.message.edit_text(
        f"Формат выбран: <b>{fmt.format_name}</b>\n🏷 Введите название турнира:",
        parse_mode="HTML"
    )
    await state.set_state(CreateTournament.NAME)

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
    
    user = await session.scalar(
        select(User).where(User.telegram_id == message.from_user.id))
    
    if not user:
        await message.answer("❌ Пользователь не найден! Вызовите /start")
        await state.clear()
        return
    
    file_path = await save_file(bot, message.document.file_id, "tournaments/regulations")
    data = await state.get_data()

    status = (
        TournamentStatus.APPROVED 
        if user.role == UserRole.SUPER_ADMIN 
        else TournamentStatus.PENDING
    )
    
    tournament = Tournament(
        game_id=data['game_id'],
        format_id=data['format_id'],  # <--- добавьте это!
        name=data['name'],
        logo_path=data['logo_path'],
        start_date=data['start_date'],
        description=data['description'],
        regulations_path=file_path,
        is_active=True,
        status=status,
        created_by=user.id
    )
    
    session.add(tournament)
    await session.commit()
    
    if status == TournamentStatus.PENDING:
        # Передаем session в функцию
        await notify_super_admins(
            bot=bot,
            text=f"Новый турнир на модерации: {data['name']}",
            session=session 
        )
    
    await message.answer(
        f"✅ Турнир <b>{data['name']}</b> успешно создан, и был отправлен на модерацию!\n"
        f"Дата старта: {data['start_date'].strftime('%d.%m.%Y %H:%M')}",
        parse_mode="HTML"
    )
    await state.clear()

    
@router.callback_query(F.data.startswith("edit_tournament_"))
async def show_tournament_details(call: CallbackQuery, session: AsyncSession):
    """Просмотр турнира (только если он одобрен или пользователь — супер-админ)"""
    tournament_id = int(call.data.split("_")[2])
    tournament = await session.get(Tournament, tournament_id)
    user = await session.scalar(
        select(User).where(User.telegram_id == call.from_user.id)
    )

    if not tournament:
        await call.answer("❌ Турнир не найден!", show_alert=True)
        return

    # Обычный админ может редактировать только свои одобренные турниры
    if user.role == UserRole.ADMIN and (
        tournament.status != TournamentStatus.APPROVED 
        or tournament.created_by != user.id
    ):
        await call.answer("🚫 Нет прав для редактирования!", show_alert=True)
        return

    # Получаем связанную игру
    game = await session.get(Game, tournament.game_id)

    # 1. Отправляем логотип, если есть
    if tournament.logo_path and os.path.exists(tournament.logo_path):
        try:
            logo = FSInputFile(tournament.logo_path)
            await call.message.answer_photo(
                photo=logo,
                caption=f"🏆 {tournament.name}"
            )
        except Exception:
            await call.message.answer("⚠️ Логотип не найден!")

    # 2. Отправляем регламент, если есть
    if tournament.regulations_path and os.path.exists(tournament.regulations_path):
        try:
            regulations = FSInputFile(tournament.regulations_path)
            await call.message.answer_document(
                document=regulations,
                caption="📄 Регламент турнира"
            )
        except Exception:
            await call.message.answer("⚠️ Регламент не найден!")

    # 3. Описание и кнопки — последним сообщением (кнопки будут внизу)
    text = (
        f"🏆 <b>{tournament.name}</b>\n\n"
        f"🎮 Игра: {game.name if game else 'Не указана'}\n"
        f"🕒 Дата старта: {tournament.start_date.strftime('%d.%m.%Y %H:%M')}\n"
        f"📝 Описание: {tournament.description}\n"
        f"🔄 Статус: {'Активен ✅' if tournament.is_active else 'Неактивен ❌'}"
    )
    await call.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=tournament_actions_kb(tournament_id, tournament.is_active)
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



@router.callback_query(F.data == "team_requests")
async def show_team_requests(call: CallbackQuery, session: AsyncSession):
    """Показать заявки команд на участие в турнире"""
    user = await session.scalar(
        select(User).where(User.telegram_id == call.from_user.id)
    )
    
    if user.role != UserRole.SUPER_ADMIN:
        await call.answer("🚫 Доступ запрещен!", show_alert=True)
        return
    
    # Получаем все турниры
    tournaments = await session.scalars(select(Tournament))
    
    # Формируем список заявок
    requests = []
    for tournament in tournaments:
        teams = await tournament.teams  # Загрузка связанных команд
        for team in teams:
            if getattr(team, "status", None) == TeamStatus.PENDING:
                requests.append((tournament, team))
    
    if not requests:
        await call.answer("📭 Нет новых заявок на участие в турнирах.")
        return

    # Формируем сообщение с заявками
    for tournament, team in requests:
        creator = await session.get(User, tournament.created_by)
        await call.message.bot.send_message(
            creator.telegram_id,
            f"📝 Новая команда хочет зарегистрироваться на ваш турнир: {tournament.name}\n"
            f"Команда: {team.team_name}\n",
            reply_markup=team_request_preview_kb(team.id)
        )
    
    await call.answer("📬 Уведомления отправлены создателям турниров.")

@router.callback_query(F.data == "moderate_teams")
async def show_pending_teams(call: CallbackQuery, session: AsyncSession):
    """Список команд на модерации"""
    # Для супер-админа — все команды, для админа — только свои турниры
    user = await session.scalar(select(User).where(User.telegram_id == call.from_user.id))
    if user.role == UserRole.SUPER_ADMIN:
        teams = await session.scalars(
            select(Team).where(Team.status == TeamStatus.PENDING)
        )
    else:
        # Только команды в турнирах, созданных этим админом
        tournaments = await session.scalars(
            select(Tournament.id).where(Tournament.created_by == user.id)
        )
        teams = await session.scalars(
            select(Team).where(
                Team.status == TeamStatus.PENDING,
                Team.tournament_id.in_(tournaments)
            )
        )
    teams = list(teams)
    if not teams:
        await call.message.edit_text("📭 Нет новых заявок на участие в турнирах.", reply_markup=back_to_admin_kb())
        return

    builder = InlineKeyboardBuilder()
    for team in teams:
        builder.button(
            text=f"{team.team_name} (турнир ID: {team.tournament_id})",
            callback_data=f"moderate_team_{team.id}"
        )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin"))
    await call.message.edit_text(
        "📝 Заявки команд на модерации:",
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data.startswith("moderate_team_"))
async def moderate_team(call: CallbackQuery, session: AsyncSession):
    team_id = int(call.data.split("_")[2])
    team = await session.get(Team, team_id)
    if not team:
        await call.answer("Команда не найдена", show_alert=True)
        return
    tournament = await session.get(Tournament, team.tournament_id)
    players = await session.scalars(select(Player).where(Player.team_id == team.id))
    players = list(players)
    player_usernames = []
    for player in players:
        user = await session.scalar(select(User).where(User.telegram_id == player.user_id))
        if user:
            player_usernames.append(f"@{user.username or user.telegram_id}")
    text = (
        f"Команда: <b>{team.team_name}</b>\n"
        f"Турнир: {tournament.name if tournament else team.tournament_id}\n"
        f"Капитан: <a href='tg://user?id={team.captain_tg_id}'>{team.captain_tg_id}</a>\n"
        f"Участники: {', '.join(player_usernames)}"
    )
    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=team_request_kb(team.id)
    )
    
@router.callback_query(F.data.regexp(r"^(de)?activate_tournament_\d+$"))
async def toggle_tournament_status(call: CallbackQuery, session: AsyncSession):
    data = call.data
    tournament_id = int(data.split("_")[-1])
    tournament = await session.get(Tournament, tournament_id)
    user = await session.scalar(
        select(User).where(User.telegram_id == call.from_user.id)
    )
    # Только супер-админ или создатель турнира
    if not tournament or not (
        user.role == UserRole.SUPER_ADMIN or tournament.created_by == user.id
    ):
        await call.answer("Нет прав для изменения статуса!", show_alert=True)
        return

    if data.startswith("deactivate"):
        tournament.is_active = False
        await session.commit()
        await call.answer("Турнир деактивирован!", show_alert=True)
    else:
        tournament.is_active = True
        await session.commit()
        await call.answer("Турнир активирован!", show_alert=True)

    # Обновить клавиатуру
    await call.message.edit_reply_markup(
        reply_markup=tournament_status_kb(tournament_id, tournament.is_active)
    )
    
@router.callback_query(F.data.startswith("preview_team_"))
async def preview_team(call: CallbackQuery, session: AsyncSession):
    team_id = int(call.data.split("_")[2])
    team = await session.get(Team, team_id)
    if not team:
        await call.answer("Команда не найдена", show_alert=True)
        return
    tournament = await session.get(Tournament, team.tournament_id)
    players = await session.scalars(select(Player).where(Player.team_id == team.id))
    players = list(players)
    player_usernames = []
    captain = await session.scalar(select(User).where(User.telegram_id == team.captain_tg_id))
    if captain and captain.username:
        captain_info = f"@{captain.username}"
    elif captain and captain.full_name:
        captain_info = captain.full_name
    else:
        captain_info = str(team.captain_tg_id)
    for player in players:
        user = await session.scalar(select(User).where(User.telegram_id == player.user_id))
        if user:
            player_usernames.append(f"@{user.username or user.telegram_id}")
    text = (
        f"Команда: <b>{team.team_name}</b>\n"
        f"Турнир: {tournament.name if tournament else team.tournament_id}\n"
        f"Капитан: {captain_info}\n"
        f"Участники: {', '.join(player_usernames)}"
    )
    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=team_request_kb(team.id)
    )