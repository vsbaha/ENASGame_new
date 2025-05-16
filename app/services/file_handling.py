import os
import uuid
from aiogram import Bot

async def save_file(bot: Bot, file_id: str, folder: str) -> str:
    os.makedirs(f"static/{folder}", exist_ok=True)
    file = await bot.get_file(file_id)
    ext = file.file_path.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    path = f"static/{folder}/{filename}"
    await bot.download_file(file.file_path, path)
    return path