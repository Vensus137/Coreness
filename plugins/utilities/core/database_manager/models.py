from pgvector.sqlalchemy import Vector
from sqlalchemy import TIMESTAMP, BigInteger, Boolean, Column, ForeignKey, Index, Integer, PrimaryKeyConstraint, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# Используем Python datetime для получения локального времени
def dtf_now_local():
    from datetime import datetime
    return datetime.now()


# =============================================================================
# СИСТЕМНЫЕ ТАБЛИЦЫ
# =============================================================================

class ViewAccess(Base):
    """Таблица для управления доступом к view через login и tenant_id"""
    __tablename__ = 'view_access'
    
    login = Column(String(100), primary_key=True)  # Имя пользователя БД (для current_user)
    tenant_id = Column(Integer, primary_key=True)  # ID тенанта (0 = доступ ко всем тенантам, логически связан с tenant.id, но без FK для гибкости)
    
    __table_args__ = (
        Index('idx_view_access_tenant_id', 'tenant_id'),
    )

# =============================================================================
# ТЕНАНТЫ И ХРАНИЛИЩА
# =============================================================================

class Tenant(Base):
    __tablename__ = 'tenant'
    
    # Универсальная модель для обеих БД
    # PostgreSQL: использует Sequence (автоматически создается)
    # SQLite: использует автоинкремент
    id = Column(Integer, primary_key=True, autoincrement=True)
    ai_token = Column(String(500), nullable=True)                 # AI API токен для тенанта (опционально)
    processed_at = Column(TIMESTAMP, nullable=False, default=dtf_now_local)  # Дата обработки конфига
    
    # Метаинформация (НЕ используется для загрузки данных!)
    bot = relationship("Bot", back_populates="tenant", uselist=False, lazy='noload')  # 1:1 связь
    
    __table_args__ = (
        {'sqlite_autoincrement': True},  # Включаем AUTOINCREMENT для SQLite
    )

class TenantStorage(Base):
    """Хранилище key-value данных тенанта (поддерживает простые типы и сложные структуры: JSON объекты, массивы)"""
    __tablename__ = 'tenant_storage'
    
    tenant_id = Column(Integer, ForeignKey('tenant.id'), nullable=False)  # FK к tenant
    group_key = Column(String(100), nullable=False)                        # Группировка атрибутов (settings, limits, features, etc.)
    key = Column(String(100), nullable=False)                              # Ключ атрибута
    value = Column(Text, nullable=True)                                    # Значение (простые типы: строки, числа, float, bool; сложные: массивы, JSON объекты - сериализуются в JSON)
    processed_at = Column(TIMESTAMP, nullable=False, default=dtf_now_local)  # Дата обработки/обновления
    
    # Метаинформация (НЕ используется для загрузки данных!)
    tenant = relationship("Tenant", lazy='noload')  # N:1 связь
    
    __table_args__ = (
        PrimaryKeyConstraint('tenant_id', 'group_key', 'key'),
        Index('idx_tenant_storage_tenant_group', 'tenant_id', 'group_key'),
    )

class UserStorage(Base):
    """Хранилище key-value данных пользователя (привязано к тенанту, поддерживает простые типы и сложные структуры: JSON объекты, массивы)"""
    __tablename__ = 'user_storage'
    
    tenant_id = Column(Integer, ForeignKey('tenant.id'), nullable=False)  # FK к tenant
    user_id = Column(BigInteger, nullable=False)                              # Telegram user_id (64-bit)
    key = Column(String(100), nullable=False)                               # Ключ атрибута
    value = Column(Text, nullable=True)                                     # Значение (простые типы: строки, числа, float, bool; сложные: массивы, JSON объекты - сериализуются в JSON)
    processed_at = Column(TIMESTAMP, nullable=False, default=dtf_now_local)  # Дата обработки/обновления
    
    # Метаинформация (НЕ используется для загрузки данных!)
    tenant = relationship("Tenant", lazy='noload')  # N:1 связь
    
    __table_args__ = (
        PrimaryKeyConstraint('tenant_id', 'user_id', 'key'),
        Index('idx_user_storage_tenant_user', 'tenant_id', 'user_id'),
        Index('idx_user_storage_tenant_key', 'tenant_id', 'key'),
    )

class TenantUser(Base):
    """Модель пользователя Telegram (привязана к тенанту)"""
    __tablename__ = 'tenant_user'
    
    tenant_id = Column(Integer, ForeignKey('tenant.id'), nullable=False)  # FK к tenant
    user_id = Column(BigInteger, nullable=False)  # Telegram user_id (64-bit)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    language_code = Column(String(10), nullable=True)
    is_bot = Column(Boolean, default=False)
    is_premium = Column(Boolean, default=False)
    user_state = Column(String(50), nullable=True)  # Состояние пользователя ("feedback", "onboarding", etc.)
    user_state_expired_at = Column(TIMESTAMP, nullable=True)  # Время истечения состояния (NULL = ошибка, 3000 год = навсегда)
    created_at = Column(TIMESTAMP, nullable=False, default=dtf_now_local)
    updated_at = Column(TIMESTAMP, nullable=False, default=dtf_now_local)
    
    # Метаинформация (НЕ используется для загрузки данных!)
    tenant = relationship("Tenant", lazy='noload')  # N:1 связь
    
    __table_args__ = (
        PrimaryKeyConstraint('tenant_id', 'user_id'),
        Index('idx_tenant_user_tenant_user', 'tenant_id', 'user_id'),
        Index('idx_tenant_user_username', 'username'),
    )
    
# =============================================================================
# БОТЫ
# =============================================================================

class Bot(Base):
    __tablename__ = 'bot'
    id = Column(Integer, primary_key=True)
    telegram_bot_id = Column(BigInteger, nullable=True)  # Telegram Bot ID (nullable для невалидных токенов)
    tenant_id = Column(Integer, ForeignKey('tenant.id'), nullable=False, unique=True)  # FK к tenant, один бот на тенант
    bot_token = Column(Text, nullable=True)                     # Токен бота (может быть None, если не установлен)
    username = Column(String(100), nullable=True)               # Username бота (из Telegram API)
    first_name = Column(String(100), nullable=True)             # Имя бота (из Telegram API)
    is_active = Column(Boolean, default=True)                   # Активен ли бот
    processed_at = Column(TIMESTAMP, nullable=False, default=dtf_now_local)  # Дата обработки конфига
    
    # Метаинформация (НЕ используется для загрузки данных!)
    tenant = relationship("Tenant", back_populates="bot", lazy='noload')  # N:1 связь
    bot_command_list = relationship("BotCommand", back_populates="bot", lazy='noload')  # 1:N связь
    
    __table_args__ = (
        Index('idx_bot_telegram_id', 'telegram_bot_id'),
        Index('idx_bot_tenant_id', 'tenant_id'),
        Index('idx_bot_bot_token', 'bot_token'),
    )

class BotCommand(Base):
    """Команды бота для регистрации и очистки в Telegram API"""
    __tablename__ = 'bot_command'
    
    id = Column(Integer, primary_key=True)
    bot_id = Column(Integer, ForeignKey('bot.id'), nullable=False)                 # FK к bot
    action_type = Column(String(20), nullable=False)                               # 'register' или 'clear'
    command = Column(String(50), nullable=True)                                    # Название команды (NULL для clear)
    description = Column(Text, nullable=True)                                      # Описание команды (NULL для clear)
    scope = Column(String(50), nullable=False, default='default')                  # default, all_private_chats, all_group_chats, chat, chat_member
    chat_id = Column(BigInteger, nullable=True)                                       # Telegram chat_id (64-bit, для scope: chat, chat_member)
    user_id = Column(BigInteger, nullable=True)                                       # Telegram user_id (64-bit, для scope: chat_member)
    processed_at = Column(TIMESTAMP, nullable=False, default=dtf_now_local)        # Дата обработки конфига
    
    # Метаинформация (НЕ используется для загрузки данных!)
    bot = relationship("Bot", back_populates="bot_command_list", lazy='noload')  # N:1 связь
    
    __table_args__ = (
        Index('idx_bot_command_bot_id', 'bot_id'),
        Index('idx_bot_command_action_type', 'action_type'),
        Index('idx_bot_command_scope', 'scope'),
        Index('idx_bot_command_bot_action', 'bot_id', 'action_type'),
    )

# =============================================================================
# СЦЕНАРИИ
# =============================================================================

class Scenario(Base):
    __tablename__ = 'scenario'
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey('tenant.id'), nullable=False)  # FK к tenant
    scenario_name = Column(String(100), nullable=False)           # admin_panel, user_onboarding
    description = Column(Text, nullable=True)                     # Описание сценария
    schedule = Column(String(100), nullable=True)                  # Cron выражение для scheduled сценариев (например, "0 9 * * *")
    last_scheduled_run = Column(TIMESTAMP, nullable=True)         # Время последнего запуска по расписанию
    processed_at = Column(TIMESTAMP, nullable=False, default=dtf_now_local)  # Дата обработки конфига
    
    # Метаинформация (НЕ используется для загрузки данных!)
    scenario_trigger_list = relationship("ScenarioTrigger", back_populates="scenario", lazy='noload')  # 1:N связь
    scenario_step_list = relationship("ScenarioStep", back_populates="scenario", lazy='noload')  # 1:N связь
    
    __table_args__ = (
        Index('idx_scenario_tenant_id', 'tenant_id'),
        Index('idx_scenario_name', 'tenant_id', 'scenario_name', unique=True),
        Index('idx_scenario_schedule', 'schedule'),  # Индекс для быстрого поиска scheduled сценариев
    )

class ScenarioTrigger(Base):
    __tablename__ = 'scenario_trigger'
    id = Column(Integer, primary_key=True)
    scenario_id = Column(Integer, ForeignKey('scenario.id'), nullable=False)    # FK к scenario
    condition_expression = Column(Text, nullable=False)                          # Унифицированное условие триггера
    processed_at = Column(TIMESTAMP, nullable=False, default=dtf_now_local)     # Дата обработки конфига
    
    # Метаинформация (НЕ используется для загрузки данных!)
    scenario = relationship("Scenario", back_populates="scenario_trigger_list", lazy='noload')  # N:1 связь
    
    __table_args__ = (
        Index('idx_scenario_trigger_scenario_id', 'scenario_id'),
    )

class ScenarioStep(Base):
    __tablename__ = 'scenario_step'
    id = Column(Integer, primary_key=True)
    scenario_id = Column(Integer, ForeignKey('scenario.id'), nullable=False)   # FK к scenario
    step_order = Column(Integer, nullable=False)                               # Порядок выполнения шага
    action_name = Column(String(100), nullable=False)                          # Имя действия (API endpoint)
    params = Column(Text, nullable=True)                                       # JSON с параметрами
    is_async = Column(Boolean, nullable=False, default=False)                 # Флаг асинхронного выполнения действия
    action_id = Column(String(100), nullable=True)                             # Уникальный ID для отслеживания async действий
    processed_at = Column(TIMESTAMP, nullable=False, default=dtf_now_local)    # Дата обработки конфига
    
    # Метаинформация (НЕ используется для загрузки данных!)
    scenario = relationship("Scenario", back_populates="scenario_step_list", lazy='noload')  # N:1 связь
    scenario_step_transition_list = relationship("ScenarioStepTransition", back_populates="scenario_step", lazy='noload')  # 1:N связь
    
    __table_args__ = (
        Index('idx_step_scenario_order', 'scenario_id', 'step_order'),
        Index('idx_step_action', 'action_name'),
    )

class ScenarioStepTransition(Base):
    __tablename__ = 'scenario_step_transition'
    id = Column(Integer, primary_key=True)
    step_id = Column(Integer, ForeignKey('scenario_step.id'), nullable=False)  # FK к scenario_step
    action_result = Column(String(50), nullable=False)                         # success, error, timeout, not_found, etc.
    transition_action = Column(String(50), nullable=False)                     # continue, abort, jump_to_scenario, move_steps, jump_to_step
    transition_value = Column(Text, nullable=True)                             # JSON с дополнительными данными для перехода
    processed_at = Column(TIMESTAMP, nullable=False, default=dtf_now_local)    # Дата обработки конфига
    
    # Метаинформация (НЕ используется для загрузки данных!)
    scenario_step = relationship("ScenarioStep", back_populates="scenario_step_transition_list", lazy='noload')  # N:1 связь
    
    __table_args__ = (
        Index('idx_scenario_step_transition_step_id', 'step_id'),
        Index('idx_scenario_step_transition_result', 'action_result'),
    )

# =============================================================================
# ГЕНЕРАТОР УНИКАЛЬНЫХ ID
# =============================================================================

class IdSequence(Base):
    """Таблица для генерации уникальных ID через автоинкремент (детерминированная генерация по хэшу seed)"""
    __tablename__ = 'id_sequence'
    
    id = Column(Integer, primary_key=True, autoincrement=True)  # Уникальный ID, который возвращаем
    hash = Column(String(32), nullable=False, unique=True)  # MD5 хэш от seed (для поиска существующих записей)
    seed = Column(Text, nullable=True)  # Seed для дебага
    processed_at = Column(TIMESTAMP, nullable=False, default=dtf_now_local)  # Системное поле
    
    __table_args__ = (
        Index('idx_id_sequence_hash', 'hash'),  # Индекс для быстрого поиска по хэшу
        {'sqlite_autoincrement': True},  # Включаем AUTOINCREMENT для SQLite
    )

# =============================================================================
# ИНВОЙСЫ
# =============================================================================

class Invoice(Base):
    """Модель инвойса для оплаты звездами Telegram"""
    __tablename__ = 'invoice'
    
    id = Column(Integer, primary_key=True, autoincrement=True)  # Это и есть invoice_payload
    tenant_id = Column(Integer, ForeignKey('tenant.id'), nullable=False)  # FK к tenant
    user_id = Column(BigInteger, nullable=True)  # Telegram user_id (64-bit, NULL если создан как ссылка)
    title = Column(String(200), nullable=False)  # Название товара/услуги
    description = Column(Text, nullable=True)  # Описание (опционально)
    amount = Column(Integer, nullable=False)  # Количество звезд (целое число)
    link = Column(Text, nullable=True)  # Ссылка на инвойс (если создан как ссылка)
    is_cancelled = Column(Boolean, default=False)  # Для внутренней логики (пометить как неактивный)
    telegram_payment_charge_id = Column(String(100), nullable=True)  # ID платежа в Telegram (после оплаты)
    paid_at = Column(TIMESTAMP, nullable=True)  # Время оплаты (NULL если не оплачен)
    created_at = Column(TIMESTAMP, nullable=False, default=dtf_now_local)  # Время создания
    updated_at = Column(TIMESTAMP, nullable=False, default=dtf_now_local, onupdate=dtf_now_local)  # Время обновления
    
    # Метаинформация (НЕ используется для загрузки данных!)
    tenant = relationship("Tenant", lazy='noload')  # N:1 связь
    
    __table_args__ = (
        Index('idx_invoice_tenant_id', 'tenant_id'),
        Index('idx_invoice_user_id', 'tenant_id', 'user_id'),
        Index('idx_invoice_tenant_paid_at', 'tenant_id', 'paid_at'),
        Index('idx_invoice_tenant_cancelled', 'tenant_id', 'is_cancelled'),
    )

# =============================================================================
# ВЕКТОРНОЕ ХРАНИЛИЩЕ (RAG) - только для PostgreSQL с pgvector
# =============================================================================

class VectorStorage(Base):
    """
    Векторное хранилище для RAG (Retrieval-Augmented Generation)
    Только для PostgreSQL с установленным расширением pgvector
    
    Таблица создается только для PostgreSQL через миграцию.
    Для SQLite таблица не создается (проверка в миграции).
    """
    __tablename__ = 'vector_storage'
    
    tenant_id = Column(Integer, ForeignKey('tenant.id'), nullable=False)  # FK к tenant
    document_id = Column(String(255), nullable=False)  # Уникальный ID документа
    chunk_index = Column(Integer, nullable=False)  # Порядок чанка в документе (0, 1, 2...)
    document_type = Column(String(100), nullable=False)  # Тип: 'knowledge', 'prompt', 'chat_history', 'other'
    role = Column(String(20), nullable=False, default='user')  # Роль для OpenAI messages: 'system', 'user', 'assistant' (по умолчанию 'user')
    # Метаданные (JSONB для фильтрации: chat_id, username и др.)
    chunk_metadata = Column(JSONB, nullable=True)  # Метаданные чанка (chat_id, username и др.) - используется для фильтрации, не раскрывается в контексте AI
    
    # Контент
    content = Column(Text, nullable=False)  # Текст чанка
    
    # Векторное представление (только для PostgreSQL с pgvector)
    # Размерность 1024 для оптимального баланса скорости и качества
    # Поддерживает HNSW индекс (ограничение: <= 2000)
    # Совместимо с большинством моделей (OpenAI, Cohere, и др.)
    # nullable=True позволяет сохранять текст без эмбеддинга (полезно для истории)
    embedding = Column(Vector(1024), nullable=True)  # Векторное представление текста (опционально, может быть NULL для истории без поиска)
    embedding_model = Column(String(100), nullable=True)  # Модель, использованная для генерации embedding (например, "text-embedding-3-small", "text-embedding-3-large")
    
    created_at = Column(TIMESTAMP, nullable=False, default=dtf_now_local)  # Реальная дата создания (для правильной сортировки истории)
    processed_at = Column(TIMESTAMP, nullable=False, default=dtf_now_local)  # Дата обработки/обновления
    
    # Метаинформация (НЕ используется для загрузки данных!)
    tenant = relationship("Tenant", lazy='noload')  # N:1 связь
    
    __table_args__ = (
        PrimaryKeyConstraint('tenant_id', 'document_id', 'chunk_index'),
        Index('idx_vector_storage_tenant', 'tenant_id'),
        Index('idx_vector_storage_document', 'tenant_id', 'document_id'),
        Index('idx_vector_storage_type', 'tenant_id', 'document_type'),
        # HNSW индекс для векторного поиска (размерность 1024 < 2000, поэтому поддерживается)
        Index(
            'idx_vector_storage_embedding_hnsw',
            'embedding',
            postgresql_using='hnsw',
            postgresql_ops={'embedding': 'vector_cosine_ops'},
            postgresql_with={'m': 16, 'ef_construction': 64}
        ),
    )