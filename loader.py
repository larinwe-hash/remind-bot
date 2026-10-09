"""Общие объекты приложения: bot, dispatcher, scheduler.

Вынесены в отдельный модуль, чтобы handlers.py и tasks.py могли их
импортировать без циклических импортов.
"""

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config

bot = Bot(
    config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

dp = Dispatcher()

scheduler = AsyncIOScheduler(
    # Задачи лежат в PostgreSQL -> переживают перезапуск процесса.
    jobstores={"default": SQLAlchemyJobStore(url=config.JOBSTORE_URL)},
    # Планировщик живёт в UTC: никаких сюрпризов при переводе часов.
    # Пояс пользователя задаётся для каждой задачи отдельно.
    timezone="UTC",
    job_defaults={
        # Бот лежал и пропустил момент — всё равно отправить,
        # но только если опоздание меньше часа.
        "misfire_grace_time": 3600,
        # Несколько пропущенных срабатываний схлопнуть в одно.
        "coalesce": True,
    },
)
