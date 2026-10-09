"""Функции, которые вызывает планировщик.

ВАЖНО. APScheduler сохраняет в базу не саму функцию, а строку-путь
"tasks:send_reminder", а аргументы — через pickle. Отсюда правила:

1. Функция лежит на верхнем уровне модуля (не вложенная, не lambda).
2. В args только простые типы: числа, строки. Объект Message передавать
   нельзя — поэтому передаём chat_id.
3. Объект bot берём импортом, а не аргументом.

Переименование этого файла или функции сломает уже сохранённые задачи.
"""

import html
import logging

from aiogram.exceptions import TelegramForbiddenError

from loader import bot

log = logging.getLogger(__name__)


async def send_reminder(chat_id: int, text: str) -> None:
    """Отправляет напоминание. Вызывается планировщиком в нужный момент."""
    try:
        # html.escape — чтобы текст пользователя со спецсимволами
        # не ломал разметку (parse_mode=HTML задан в loader.py)
        await bot.send_message(
            chat_id, f"⏰ <b>Напоминание</b>\n{html.escape(text)}"
        )
    except TelegramForbiddenError:
        # Пользователь заблокировал бота — не считаем это ошибкой.
        log.info("Пользователь %s заблокировал бота", chat_id)
