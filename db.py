"""Своя таблица пользователей.

APScheduler хранит только задачи (таблица apscheduler_jobs, создаётся сам).
Часовой пояс пользователя нужно держать самостоятельно.
"""

import asyncpg

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    chat_id    BIGINT PRIMARY KEY,
    timezone   TEXT NOT NULL DEFAULT 'Europe/Moscow',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

pool: asyncpg.Pool | None = None


async def init() -> None:
    """Создаёт пул соединений и таблицу. Вызывается один раз при старте."""
    global pool
    pool = await asyncpg.create_pool(config.DB_DSN, min_size=1, max_size=5)
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA)


async def close() -> None:
    if pool is not None:
        await pool.close()


async def ensure_user(chat_id: int) -> None:
    """Регистрирует пользователя, если его ещё нет. Повторный вызов безвреден."""
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (chat_id) VALUES ($1) ON CONFLICT DO NOTHING",
            chat_id,
        )


async def get_tz(chat_id: int) -> str:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT timezone FROM users WHERE chat_id = $1", chat_id
        )
    return row["timezone"] if row else config.DEFAULT_TZ


async def set_tz(chat_id: int, tz: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (chat_id, timezone) VALUES ($1, $2) "
            "ON CONFLICT (chat_id) DO UPDATE SET timezone = EXCLUDED.timezone",
            chat_id,
            tz,
        )
