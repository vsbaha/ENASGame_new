from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.database.db import UserRole

def admin_menu() -> InlineKeyboardMarkup:
    """Клавиатура обычного админа"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏆 Управление турнирами", callback_data="manage_tournaments"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
        width=1
    )
    return builder.as_markup()

def admin_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏆 Управление турнирами", callback_data="manage_tournaments"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
        width=1
    )
    return builder.as_markup()

def admin_tournaments_kb(tournaments: list) -> InlineKeyboardMarkup:
    """Клавиатура управления турнирами для администратора"""
    builder = InlineKeyboardBuilder()
    
    for tournament in tournaments:
        status = "✅" if tournament.is_active else "❌"
        builder.button(
            text=f"{tournament.name} {status}",
            callback_data=f"admin_tournament_{tournament.id}"
        )
    
    builder.adjust(1)
    builder.row(
        InlineKeyboardButton(text="➕ Создать турнир", callback_data="create_tournament"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin"),
        width=2
    )
    return builder.as_markup()

def tournament_actions_kb(tournament_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_tournament_{tournament_id}"),
        InlineKeyboardButton(text="◀️ Назад к списку", callback_data="back_to_tournaments"),  # Обновленная кнопка
        width=2
    )
    return builder.as_markup()

def tournaments_management_kb(tournaments) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for t in tournaments:
        builder.button(
            text=f"{t.name} {'✅' if t.is_active else '❌'}",
            callback_data=f"edit_tournament_{t.id}"
        )
    builder.row(
        InlineKeyboardButton(text="➕ Создать", callback_data="create_tournament"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin"),
        width=2
    )
    builder.adjust(1)
    return builder.as_markup()

def back_to_admin_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ В админ-панель", callback_data="back_to_admin")
    return builder.as_markup()

def games_select_kb(games):
    builder = InlineKeyboardBuilder()
    for game in games:
        builder.button(
            text=game.name, 
            callback_data=f"admin_select_game_{game.id}"  # Новый префикс
        )
    return builder.as_markup()

def confirm_action_kb(tournament_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действия"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Подтвердить", 
            callback_data=f"confirm_delete_{tournament_id}"
        ),
        InlineKeyboardButton(
            text="❌ Отменить", 
            callback_data="cancel_action"
        ),
        width=2
    )
    return builder.as_markup()

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def super_admin_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👥 Управление админами", callback_data="manage_admins"),
        InlineKeyboardButton(text="🔧 Обычное админ-меню", callback_data="admin_menu"),
        width=1
    )
    return builder.as_markup()

def manage_admins_kb(admins) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for admin in admins:
        status = "✅" if admin.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN] else "❌"
        builder.button(
            text=f"{admin.full_name} {status}",
            callback_data=f"toggle_admin_{admin.id}"
        )
    builder.button(text="◀️ Назад", callback_data="back_to_super_admin")
    builder.adjust(1)
    return builder.as_markup()