import sys
sys.stdout.reconfigure(encoding='utf-8')
import asyncio
import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from app.handlers import common, user, admin, super_admin
from app.database.db import create_db, async_session_maker
from app.middleware import DatabaseMiddleware, AdminCheckMiddleware, ErrorHandlerMiddleware
from logging.handlers import RotatingFileHandler
from app.filters.admin import AdminFilter

load_dotenv()

async def main():
    await create_db()
    
    bot = Bot(token=os.getenv("BOT_TOKEN"))
    dp = Dispatcher()

    # Порядок ВАЖЕН: DatabaseMiddleware должен быть первым
    dp.update.middleware(DatabaseMiddleware(async_session_maker))
    dp.update.middleware(ErrorHandlerMiddleware())

    # Роутеры
    dp.include_router(common.router)
    dp.include_router(user.router)
    dp.include_router(admin.router)
    dp.include_router(super_admin.router)
    admin.router.message.filter(AdminFilter())
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            RotatingFileHandler(
                'bot.log',
                encoding='utf-8',
                maxBytes=5*1024*1024,
                backupCount=3
            ),
            logging.StreamHandler()
        ]
    )
    asyncio.run(main())