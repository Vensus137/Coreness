-- Автоматическая установка расширения pgvector при создании базы данных
-- Этот скрипт выполняется автоматически при первой инициализации PostgreSQL
-- через механизм /docker-entrypoint-initdb.d/

-- Устанавливаем расширение pgvector в базу данных core_db
-- IF NOT EXISTS предотвращает ошибку, если расширение уже установлено
CREATE EXTENSION IF NOT EXISTS vector;

