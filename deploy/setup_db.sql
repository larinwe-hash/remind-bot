-- Выполнять от имени суперпользователя: psql -U postgres -f setup_db.sql
-- Пароль замените на свой и тот же впишите в .env

CREATE DATABASE remind_bot;
CREATE USER bot WITH PASSWORD 'change_me';
GRANT ALL PRIVILEGES ON DATABASE remind_bot TO bot;

-- В PostgreSQL 15+ права на схему public выдаются отдельно,
-- и обязательно ВНУТРИ базы remind_bot:
\connect remind_bot
GRANT ALL ON SCHEMA public TO bot;
