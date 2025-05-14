from aiogram import  F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext


import app.keyboards as kb

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await message.answer(f"Привет {message.from_user.first_name}", reply_markup=kb.main_menu)
    
@router.message(F.text == "🔍  турниры")
async def cmd_tournaments(message: Message):
    await message.answer("Турниры")
    
@router.message(F.text == "ℹ️ Помощь")
async def cmd_help(message: Message):
    await message.answer("Помощь")