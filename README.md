# Telegram-бот с напоминаниями

Разовые и регулярные напоминания с учётом часового пояса пользователя.
Задачи хранятся в PostgreSQL, поэтому переживают перезапуск бота.

**Стек:** Python 3.11+ · [aiogram 3](https://docs.aiogram.dev) · [APScheduler 3](https://apscheduler.readthedocs.io) · PostgreSQL

## Команды бота

| Команда | Что делает |
|---|---|
| `/remind 25.12 18:00 текст` | разовое напоминание на дату |
| `/remind 18:00 текст` | сегодня, а если время прошло — завтра |
| `/every 09:00 текст` | каждый день в это время |
| `/list` | список напоминаний + кнопки удаления |
| `/tz Europe/Kyiv` | задать свой часовой пояс |

## Быстрый старт

```bash
git clone https://github.com/larinwe-hash/remind-bot.git
cd remind-bot

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # и впишите туда токен и строку подключения
python bot.py
```

### Что нужно подготовить

1. **Токен бота** — напишите [@BotFather](https://t.me/BotFather), команда `/newbot`.
2. **База данных:**

```bash
psql -U postgres -f deploy/setup_db.sql
```

Скрипт создаёт базу `remind_bot`, пользователя `bot` и выдаёт права на схему
`public` (в PostgreSQL 15+ это обязательный отдельный шаг).

3. **`.env`** — заполните по образцу `.env.example`.

Таблицу `apscheduler_jobs` создаст APScheduler, таблицу `users` — сам бот при
первом запуске. Миграции не нужны.

## Проверка

После `python bot.py` в логе должно появиться `Start polling`. Дальше в Telegram:

1. `/start` → пришла справка.
2. `/tz Europe/Moscow` → бот показал ваше текущее время.
3. `/remind 18:05 тест` (на пару минут вперёд) → подтверждение.
4. **Остановите бота (Ctrl+C) и запустите заново** — напоминание всё равно
   должно прийти вовремя. Это главная проверка, что хранилище подключено.

Задачи видно и в самой базе:

```bash
psql -d remind_bot -c "SELECT id, next_run_time FROM apscheduler_jobs;"
```

## Структура

```
.
├── bot.py          точка входа
├── config.py       чтение .env
├── loader.py       объекты bot / dp / scheduler
├── db.py           таблица users (asyncpg)
├── tasks.py        функция, которую вызывает планировщик
├── handlers.py     команды
└── deploy/
    ├── setup_db.sql
    └── remind-bot.service
```

Файлов несколько, если объявить `bot` и хендлеры в одном
модуле, получится циклический импорт.

## Как это работает

Бот не держит напоминания в памяти. Каждая команда создаёт **job** в
APScheduler, который сериализуется в PostgreSQL. При старте планировщик
поднимает задачи из базы и доводит их до срабатывания.

Важные детали реализации:

- `send_reminder` лежит на верхнем уровне `tasks.py` — APScheduler сохраняет
  путь `tasks:send_reminder` строкой. Переименование файла или функции сломает
  уже сохранённые задачи.
- В `args` задачи попадают только простые типы (`chat_id`, текст): всё
  остальное не переживёт pickle.
- Планировщик живёт в UTC, часовой пояс задаётся для каждой задачи отдельно —
  так нет сюрпризов при переводе часов.
- `misfire_grace_time=3600`: если бот лежал, пропущенные за последний час
  напоминания всё равно отправятся.

## Деплой на VPS

```bash
sudo cp deploy/remind-bot.service /etc/systemd/system/
sudo nano /etc/systemd/system/remind-bot.service   # поправьте User и пути
sudo systemctl daemon-reload
sudo systemctl enable --now remind-bot
sudo journalctl -u remind-bot -f                   # логи
```

Serverless не подойдёт: боту нужен постоянно работающий процесс.
И не запускайте два экземпляра одновременно — будут дубли сообщений.

## Лицензия

MIT — см. [LICENSE](LICENSE).
