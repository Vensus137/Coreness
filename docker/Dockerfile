FROM mirror.gcr.io/library/python:3.11-slim

# Install system dependencies
# Add official PostgreSQL 18 repository
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

# Install Supervisor for process management
RUN apt-get update && apt-get install -y supervisor \
    && mkdir -p /var/log/supervisor \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /workspace

# Install dependencies DIRECTLY (standalone image)
# Step 1: Core dependencies
RUN pip install PyYAML==6.0.1 SQLAlchemy==2.0.25 python-dotenv==1.0.0

# Step 2: Utilities
RUN pip install unidecode emoji python-dateutil>=2.8.0

# Step 3: Network libraries
RUN pip install requests>=2.31.0 aiohttp>=3.8.0

# Step 4: Git
RUN pip install gitpython>=3.1.0

# Step 5: PostgreSQL driver
RUN pip install psycopg2-binary==2.9.9

# Step 6: AI and Telegram
RUN pip install openai>=2.6.0 telegramify-markdown>=0.5.1

# Step 7: Cron for scheduled scenarios
RUN pip install croniter>=2.0.0

# Step 8: Pydantic for data validation
RUN pip install pydantic>=2.0.0

# Step 9: Cryptography for SSL certificate generation
RUN pip install cryptography>=41.0.0

# Step 10: pgvector for vector data (RAG)
RUN pip install pgvector>=0.2.0

# Copy Supervisor configuration
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copy application code to image (for prod)
# For dev/test can be overridden via volume in docker-compose
COPY app/ /workspace/app/
COPY plugins/ /workspace/plugins/
COPY tools/ /workspace/tools/
COPY main.py /workspace/main.py
COPY requirements.txt /workspace/requirements.txt