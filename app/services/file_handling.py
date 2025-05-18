import os
import uuid
from aiogram import Bot
import logging

async def save_file(bot: Bot, file_id: str, folder: str) -> str:
    """Сохранение файлов с обработкой ошибок"""
    try:
        os.makedirs(f"static/{folder}", exist_ok=True)
        file = await bot.get_file(file_id)
        ext = file.file_path.split(".")[-1]
        filename = f"{uuid.uuid4()}.{ext}"
        path = f"static/{folder}/{filename}"
        await bot.download_file(file.file_path, path)
        return path
    except Exception as e:
        logging.error(f"Ошибка сохранения файла: {e}")
        raise