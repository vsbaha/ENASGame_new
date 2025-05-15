from aiogram import  F, Router, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv
import os

from app.database.db import SessionLocal, Broadcast, User, Admin
import app.keyboards as kb

load_dotenv()
admin_ids_raw = os.getenv("ADMIN_IDS", "")
ADMIN_ID = set(map(int, admin_ids_raw.split(",")))


SUPER_ADMIN_ID = 1189473577

router = Router()

class BroadcastState(StatesGroup):
    waiting_for_broadcast_text = State()

@router.message(CommandStart())
async def cmd_start(message: Message):
    print(message.from_user.id)
    db = SessionLocal()
    existing = db.query(User).filter(User.telegram_id == message.from_user.id).first()
    if not existing:
        new_user = User(telegram_id=message.from_user.id, name=message.from_user.full_name)
        db.add(new_user)
        db.commit()
    db.close()
    await message.answer("Привет!", reply_markup=kb.main_menu)
    
@router.message(F.text == "🔍  турниры")
async def cmd_tournaments(message: Message):
    await message.answer("Турниры")
    
@router.message(F.text == "ℹ️ Помощь")
async def cmd_help(message: Message):
    await message.answer("Помощь")
    
@router.message(Command("admin"))
async def cmd_admin(message: Message):
    with SessionLocal() as session:
        is_admin = session.query(Admin).filter_by(telegram_id=message.from_user.id).first()

    if is_admin:
        await message.answer('✅ Добро пожаловать в админ-панель', reply_markup=kb.admin_menu)
    else:
        await message.answer('❌ Вы не являетесь администратором')
    
@router.message(Command("add_admin"))
async def add_admin(message: Message):
    if message.from_user.id != SUPER_ADMIN_ID:
        return await message.answer("❌ У тебя нет доступа.")

    try:
        user_id = int(message.text.strip().split()[1])
    except (IndexError, ValueError):
        return await message.answer("Используй: /add_admin <telegram_id>")

    with SessionLocal() as session:
        if session.query(Admin).filter_by(telegram_id=user_id).first():
            return await message.answer("⚠️ Этот пользователь уже админ.")

        session.add(Admin(
            telegram_id=user_id,
            username=message.from_user.username,
            full_name=message.from_user.full_name
        ))
        session.commit()

    await message.answer(f"✅ Админ {user_id} добавлен.")

        
@router.message(Command("remove_admin"))
async def remove_admin(message: Message):
    if message.from_user.id != SUPER_ADMIN_ID:
        return await message.answer("❌ У тебя нет доступа.")

    try:
        user_id = int(message.text.strip().split()[1])
    except (IndexError, ValueError):
        return await message.answer("Используй: /remove_admin <telegram_id>")

    with SessionLocal() as session:
        admin = session.query(Admin).filter_by(telegram_id=user_id).first()
        if not admin:
            return await message.answer("⚠️ Такого админа нет.")
        session.delete(admin)
        session.commit()
        await message.answer(f"❌ Админ {user_id} удалён.")

@router.message(Command("admins"))
async def list_admins(message: Message):
    with SessionLocal() as session:
        admins = session.query(Admin).all()

    if not admins:
        return await message.answer("⚠️ Админов пока нет.")

    text = "👥 Список админов:\n\n"
    for admin in admins:
        line = f"{admin.full_name or 'Имя неизвестно'}"
        if admin.username:
            line += f" (@{admin.username})"
        line += f" — {admin.telegram_id}"
        text += line + "\n"

    await message.answer(text)

        

@router.callback_query(F.data == "back")
async def callback_back(call: CallbackQuery):
    await call.message.edit_text("Админ панель", reply_markup=kb.admin_menu)
    await call.answer()
    
@router.callback_query(F.data == "stats")
async def process_stats(call: CallbackQuery):
    db = SessionLocal()
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.active == True).count()
    db.close()
    await call.message.delete()
    await call.message.answer(f'Всего пользователей: {total_users}\nАктивных пользователей: {active_users}', reply_markup=kb.back_menu)
    await call.answer()
    
@router.callback_query(F.data == "broadcast")
async def process_broadcast(call: CallbackQuery, state: FSMContext):
    await call.message.delete()  # удаляем сообщение с кнопкой "broadcast"
    await call.message.answer("Введите текст рассылки", reply_markup=kb.back_menu)
    await state.set_state(BroadcastState.waiting_for_broadcast_text)
    await call.answer()
    
@router.message(BroadcastState.waiting_for_broadcast_text)
async def handle_broadcast_text(message: Message, state: FSMContext, bot: Bot):
    Broadcast_text = message.text
    db = SessionLocal()
    users_list = db.query(User).filter(User.active == True).all()
    count = 0
    for user in users_list:
        try:
            await bot.send_message(user.telegram_id, Broadcast_text)
            count += 1
        except Exception as e:
            print(f"Error sending message to user {user.telegram_id}: {e}")
    new_broadcast = Broadcast(message=Broadcast_text)
    db.add(new_broadcast)
    db.commit()
    db.close()
    await message.answer(f"Рассылка отправлена {count} пользователям")
    await state.clear()
    
@router.message(F.text)
async def echo(message: Message):
    await message.answer("Я тебя не понимаю чел")