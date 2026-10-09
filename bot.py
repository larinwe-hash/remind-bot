"""Точка входа. Запуск: python bot.py"""

import asyncio
import logging

import db
import handlers  # noqa: F401 — импорт регистрирует хендлеры через декораторы
from loader import bot, dp, scheduler


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    await db.init()  # пул соединений + таблица users
    scheduler.start()  # поднимает сохранённые задачи из PostgreSQL

    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
