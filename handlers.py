"""Команды бота."""

import html
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, available_timezones

from aiogram import F
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from apscheduler.triggers.cron import CronTrigger

import db
from loader import dp, scheduler
from tasks import send_reminder

# Сколько активных напоминаний разрешено одному пользователю
MAX_JOBS_PER_USER = 50

HELP = (
    "Бот-напоминалка.\n\n"
    "<b>Разовое</b>\n"
    "/remind 25.12 18:00 поздравить маму\n"
    "/remind 18:00 забрать посылку — сегодня, а если время прошло, то завтра\n\n"
    "<b>Регулярное</b>\n"
    "/every 09:00 зарядка — каждый день\n\n"
    "<b>Прочее</b>\n"
    "/list — список напоминаний и удаление\n"
    "/tz Europe/Kyiv — ваш часовой пояс"
)


# ---------------------------------------------------------------- утилиты


def parse_when(raw: str, tz: ZoneInfo) -> tuple[datetime, str]:
    """'25.12 18:00 текст' или '18:00 текст' -> (когда, что).

    Любая ошибка формата вылетает как ValueError — ловим её в хендлере.
    """
    parts = raw.split(maxsplit=1)
    if len(parts) < 2:
        raise ValueError("мало аргументов")

    now = datetime.now(tz)

    if "." in parts[0]:  # указана дата
        date_s, rest = parts
        time_s, _, text = rest.partition(" ")
        day, month = (int(x) for x in date_s.split("."))
        hour, minute = (int(x) for x in time_s.split(":"))
        when = datetime(now.year, month, day, hour, minute, tzinfo=tz)
        if when <= now:  # написали 25.12, когда уже январь
            when = when.replace(year=now.year + 1)
    else:  # только время
        time_s, text = parts
        hour, minute = (int(x) for x in time_s.split(":"))
        when = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if when <= now:
            when += timedelta(days=1)

    text = text.strip()
    if not text:
        raise ValueError("пустой текст")
    if len(text) > 500:
        raise ValueError("слишком длинный текст")
    return when, text


def user_jobs(chat_id: int) -> list:
    """Задачи конкретного пользователя.

    У планировщика нельзя спросить «задачи такого-то», поэтому фильтруем
    по chat_id, который сами положили первым аргументом.
    """
    return [
        j
        for j in scheduler.get_jobs()
        if j.args and j.args[0] == chat_id and j.next_run_time
    ]


# --------------------------------------------------------------- команды


@dp.message(Command("start", "help"))
async def cmd_start(message: Message) -> None:
    await db.ensure_user(message.chat.id)
    await message.answer(HELP)


@dp.message(Command("tz"))
async def cmd_tz(message: Message, command: CommandObject) -> None:
    tz = (command.args or "").strip()
    if tz not in available_timezones():
        await message.answer(
            "Укажите пояс в формате IANA.\n"
            "Например: /tz Europe/Kyiv, /tz Asia/Almaty, /tz Europe/Moscow"
        )
        return
    await db.set_tz(message.chat.id, tz)
    now = datetime.now(ZoneInfo(tz)).strftime("%H:%M")
    await message.answer(f"Пояс сохранён: {tz}. Сейчас у вас {now}.")


@dp.message(Command("remind"))
async def cmd_remind(message: Message, command: CommandObject) -> None:
    await db.ensure_user(message.chat.id)

    if len(user_jobs(message.chat.id)) >= MAX_JOBS_PER_USER:
        await message.answer("Слишком много напоминаний. Удалите часть через /list.")
        return

    tz = ZoneInfo(await db.get_tz(message.chat.id))
    try:
        when, text = parse_when(command.args or "", tz)
    except ValueError:
        await message.answer("Формат: /remind 25.12 18:00 текст\nили: /remind 18:00 текст")
        return

    scheduler.add_job(
        send_reminder,
        trigger="date",
        run_date=when,  # datetime с поясом — сконвертируется корректно
        args=[message.chat.id, text],  # только простые типы!
        id=uuid.uuid4().hex,  # свой id, чтобы потом удалить
    )
    await message.answer("Напомню " + when.strftime("%d.%m в %H:%M"))


@dp.message(Command("every"))
async def cmd_every(message: Message, command: CommandObject) -> None:
    await db.ensure_user(message.chat.id)

    if len(user_jobs(message.chat.id)) >= MAX_JOBS_PER_USER:
        await message.answer("Слишком много напоминаний. Удалите часть через /list.")
        return

    tz_name = await db.get_tz(message.chat.id)
    parts = (command.args or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Формат: /every 09:00 текст")
        return
    try:
        hour, minute = (int(x) for x in parts[0].split(":"))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except ValueError:
        await message.answer("Формат: /every 09:00 текст")
        return

    scheduler.add_job(
        send_reminder,
        trigger="cron",
        hour=hour,
        minute=minute,
        timezone=tz_name,  # строкой — APScheduler разберёт сам
        args=[message.chat.id, parts[1].strip()],
        id=uuid.uuid4().hex,
    )
    await message.answer(f"Буду напоминать каждый день в {hour:02d}:{minute:02d}")


@dp.message(Command("list"))
async def cmd_list(message: Message) -> None:
    tz = ZoneInfo(await db.get_tz(message.chat.id))
    jobs = user_jobs(message.chat.id)
    if not jobs:
        await message.answer("Напоминаний нет.")
        return

    lines, rows = [], []
    for job in sorted(jobs, key=lambda j: j.next_run_time):
        when = job.next_run_time.astimezone(tz).strftime("%d.%m %H:%M")
        mark = "🔁" if isinstance(job.trigger, CronTrigger) else "1️⃣"
        lines.append(f"{mark} {when} — {html.escape(job.args[1])}")
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"🗑 {job.args[1][:25]}",
                    callback_data=f"del:{job.id}",
                )
            ]
        )

    await message.answer(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@dp.callback_query(F.data.startswith("del:"))
async def cb_delete(call: CallbackQuery) -> None:
    job_id = call.data.split(":", 1)[1]
    job = scheduler.get_job(job_id)

    if job is None:
        await call.answer("Уже удалено")
    elif not job.args or job.args[0] != call.message.chat.id:
        # Проверка владельца: callback_data приходит от клиента
        # и теоретически может быть подделана.
        await call.answer("Нет доступа", show_alert=True)
    else:
        job.remove()
        await call.answer("Удалено")

    await call.message.edit_reply_markup(reply_markup=None)
