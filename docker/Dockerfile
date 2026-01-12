FROM mirror.gcr.io/library/python:3.11-slim

# Устанавливаем системные зависимости
# Добавляем официальный репозиторий PostgreSQL 18
RUN apt-get update && apt-get install -y \
    wget \
    ca-certificates \
    lsb-release \
    gnupg \
    && wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /usr/share/keyrings/postgresql-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/postgresql-archive-keyring.gpg] http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update \
    && apt-get install -y \
    git \
    curl \
    postgresql-18 \
    postgresql-contrib-18 \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем Supervisor для управления процессами
RUN apt-get update && apt-get install -y supervisor \
    && mkdir -p /var/log/supervisor \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию
WORKDIR /workspace

# Устанавливаем зависимости НАПРЯМУЮ (автономный образ)
# Шаг 1: Основные зависимости
RUN pip install PyYAML==6.0.1 SQLAlchemy==2.0.25 python-dotenv==1.0.0

# Шаг 2: Утилиты
RUN pip install unidecode emoji psutil>=5.9.0

# Шаг 3: Сетевые библиотеки
RUN pip install requests>=2.31.0 aiohttp>=3.8.0

# Шаг 4: Git
RUN pip install gitpython>=3.1.0

# Шаг 5: PostgreSQL драйвер
RUN pip install psycopg2-binary==2.9.9

# Шаг 6: AI и Telegram
RUN pip install openai>=2.6.0 telegramify-markdown>=0.5.1

# Шаг 7: Cron для scheduled сценариев
RUN pip install croniter>=2.0.0

# Шаг 8: Pydantic для валидации данных
RUN pip install pydantic>=2.0.0

# Шаг 9: Cryptography для генерации SSL-сертификатов
RUN pip install cryptography>=41.0.0

# Шаг 10: pgvector для работы с векторными данными (RAG)
RUN pip install pgvector>=0.2.0

# Копируем конфигурацию Supervisor
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Копируем код приложения в образ (для prod)
# Для dev/test можно переопределить через volume в docker-compose
COPY app/ /workspace/app/
COPY plugins/ /workspace/plugins/
COPY tools/ /workspace/tools/
COPY main.py /workspace/main.py
COPY requirements.txt /workspace/requirements.txt