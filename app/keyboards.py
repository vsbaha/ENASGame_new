from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔍  турниры")],
        [KeyboardButton(text="ℹ️ Помощь")]
    ],

    resize_keyboard=True,    # подгоняет кнопки по ширине
)

admin_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📨 Рассылка", callback_data="broadcast")],
        [InlineKeyboardButton(text="👤 Статистика", callback_data="stats")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")]
    ]
)

edit_tournament = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📝 Редактировать", callback_data="edit")],
        [InlineKeyboardButton(text="❌ Удалить", callback_data="delete")]
    ]
)


back_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
    ]
)