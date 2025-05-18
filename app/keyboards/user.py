from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    ReplyKeyboardMarkup, 
    KeyboardButton
)

def main_menu_kb() -> ReplyKeyboardMarkup:
    """Главное меню пользователя"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🔍 Активные турниры"),
        KeyboardButton(text="👥 Мои команды")
    )
    builder.row(KeyboardButton(text="ℹ️ Помощь"))
    return builder.as_markup(resize_keyboard=True)

# Для выбора игры пользователем
def games_list_kb(games):
    builder = InlineKeyboardBuilder()
    for game in games:
        builder.button(
            text=game.name,
            callback_data=f"user_select_game_{game.id}"  # Новый префикс
        )
    return builder.as_markup()

def tournaments_list_kb(tournaments: list) -> InlineKeyboardMarkup:
    """Список турниров для выбранной игры"""
    builder = InlineKeyboardBuilder()
    for tournament in tournaments:
        builder.button(
            text=f"{tournament.name} 🏆",
            callback_data=f"view_tournament_{tournament.id}"
        )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_games"),
        width=1
    )
    return builder.as_markup()

def tournament_details_kb(tournament_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📜 Регламент", callback_data=f"rules_{tournament_id}"),
        InlineKeyboardButton(text="✅ Зарегистрироваться", callback_data=f"register_{tournament_id}"),  # Добавлено
        width=1
    )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_tournaments"))
    return builder.as_markup()

def cancel_registration_kb() -> InlineKeyboardMarkup:
    """Кнопка отмены регистрации"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить регистрацию", callback_data="cancel_registration")
    return builder.as_markup()

