from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔍  турниры")],
        [KeyboardButton(text="ℹ️ Помощь")]
    ],

    resize_keyboard=True,    # подгоняет кнопки по ширине
    one_time_keyboard=True   # скрывает клавиатуру после нажатия
)

admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👑 Админ-панель")]
    ]
)