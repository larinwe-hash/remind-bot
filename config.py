"""Чтение настроек из .env / переменных окружения."""

import os

from dotenv import load_dotenv

load_dotenv()  # читает файл .env, если он есть, и кладёт значения в окружение

# Квадратные скобки, а не .get(): если переменной нет — бот упадёт сразу
# с понятной ошибкой, а не через час непредсказуемым поведением.
BOT_TOKEN = os.environ["BOT_TOKEN"]
DB_DSN = os.environ["DB_DSN"]

# APScheduler работает через синхронный SQLAlchemy и требует явного драйвера.
# asyncpg берёт DB_DSN как есть, а здесь подменяем схему на psycopg2.
JOBSTORE_URL = DB_DSN.replace("postgresql://", "postgresql+psycopg2://", 1)

# Пояс по умолчанию для тех, кто ещё не выполнил /tz
DEFAULT_TZ = os.getenv("DEFAULT_TZ", "Europe/Moscow")
