from pgvector.sqlalchemy import Vector
from sqlalchemy import TIMESTAMP, BigInteger, Boolean, Column, ForeignKey, Index, Integer, PrimaryKeyConstraint, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# Use Python datetime to get local time
def dtf_now_local():
    from datetime import datetime
    return datetime.now()


# =============================================================================
# SYSTEM TABLES
# =============================================================================

class ViewAccess(Base):
    """Table for managing view access via login and tenant_id"""
    __tablename__ = 'view_access'
    
    login = Column(String(100), primary_key=True)  # DB username (for current_user)
    tenant_id = Column(Integer, primary_key=True)  # Tenant ID (0 = access to all tenants, logically linked to tenant.id but without FK for flexibility)
    
    __table_args__ = (
        Index('idx_view_access_tenant_id', 'tenant_id'),
    )

# =============================================================================
# TENANTS AND STORAGES
# =============================================================================

class Tenant(Base):
    __tablename__ = 'tenant'
    
    # Universal model for both DBs
    # PostgreSQL: uses Sequence (automatically created)
    # SQLite: uses autoincrement
    id = Column(Integer, primary_key=True, autoincrement=True)
    ai_token = Column(String(500), nullable=True)                 # AI API token for tenant (optional)
    processed_at = Column(TIMESTAMP, nullable=False, default=dtf_now_local)  # Config processing date
    
    # Meta information (NOT used for data loading!)
    bot = relationship("Bot", back_populates="tenant", uselist=False, lazy='noload')  # 1:1 relationship
    
    __table_args__ = (
        {'sqlite_autoincrement': True},  # Enable AUTOINCREMENT for SQLite
    )

class TenantStorage(Base):
    """Tenant key-value data storage (supports simple types and complex structures: JSON objects, arrays)"""
    __tablename__ = 'tenant_storage'
    
    tenant_id = Column(Integer, ForeignKey('tenant.id'), nullable=False)  # FK to tenant
    group_key = Column(String(100), nullable=False)                        # Attribute grouping (settings, limits, features, etc.)
    key = Column(String(100), nullable=False)                              # Attribute key
    value = Column(Text, nullable=True)                                    # Value (simple types: strings, numbers, float, bool; complex: arrays, JSON objects - serialized to JSON)
    processed_at = Column(TIMESTAMP, nullable=False, default=dtf_now_local)  # Processing/update date
    
    # Meta information (NOT used for data loading!)
    tenant = relationship("Tenant", lazy='noload')  # N:1 relationship
    
    __table_args__ = (
        PrimaryKeyConstraint('tenant_id', 'group_key', 'key'),
        Index('idx_tenant_storage_tenant_group', 'tenant_id', 'group_key'),
    )

class UserStorage(Base):
    """User key-value data storage (linked to tenant, supports simple types and complex structures: JSON objects, arrays)"""
    __tablename__ = 'user_storage'
    
    tenant_id = Column(Integer, ForeignKey('tenant.id'), nullable=False)  # FK to tenant
    user_id = Column(BigInteger, nullable=False)                              # Telegram user_id (64-bit)
    key = Column(String(100), nullable=False)                               # Attribute key
    value = Column(Text, nullable=True)                                     # Value (simple types: strings, numbers, float, bool; complex: arrays, JSON objects - serialized to JSON)
    processed_at = Column(TIMESTAMP, nullable=False, default=dtf_now_local)  # Processing/update date
    
    # Meta information (NOT used for data loading!)
    tenant = relationship("Tenant", lazy='noload')  # N:1 relationship
    
    __table_args__ = (
        PrimaryKeyConstraint('tenant_id', 'user_id', 'key'),
        Index('idx_user_storage_tenant_user', 'tenant_id', 'user_id'),
        Index('idx_user_storage_tenant_key', 'tenant_id', 'key'),
    )

class TenantUser(Base):
    """Telegram user model (linked to tenant)"""
    __tablename__ = 'tenant_user'
    
    tenant_id = Column(Integer, ForeignKey('tenant.id'), nullable=False)  # FK to tenant
    user_id = Column(BigInteger, nullable=False)  # Telegram user_id (64-bit)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    language_code = Column(String(10), nullable=True)
    is_bot = Column(Boolean, default=False)
    is_premium = Column(Boolean, default=False)
    user_state = Column(String(50), nullable=True)  # User state ("feedback", "onboarding", etc.)
    user_state_expired_at = Column(TIMESTAMP, nullable=True)  # State expiration time (NULL = error, year 3000 = forever)
    created_at = Column(TIMESTAMP, nullable=False, default=dtf_now_local)
    updated_at = Column(TIMESTAMP, nullable=False, default=dtf_now_local)
    
    # Meta information (NOT used for data loading!)
    tenant = relationship("Tenant", lazy='noload')  # N:1 relationship
    
    __table_args__ = (
        PrimaryKeyConstraint('tenant_id', 'user_id'),
        Index('idx_tenant_user_tenant_user', 'tenant_id', 'user_id'),
        Index('idx_tenant_user_username', 'username'),
    )
    
# =============================================================================
# BOTS
# =============================================================================

class Bot(Base):
    __tablename__ = 'bot'
    id = Column(Integer, primary_key=True)
    telegram_bot_id = Column(BigInteger, nullable=True)  # Telegram Bot ID (nullable for invalid tokens)
    tenant_id = Column(Integer, ForeignKey('tenant.id'), nullable=False, unique=True)  # FK to tenant, one bot per tenant
    bot_token = Column(Text, nullable=True)                     # Bot token (can be None if not set)
    username = Column(String(100), nullable=True)               # Bot username (from Telegram API)
    first_name = Column(String(100), nullable=True)             # Bot name (from Telegram API)
    is_active = Column(Boolean, default=True)                   # Whether bot is active
    processed_at = Column(TIMESTAMP, nullable=False, default=dtf_now_local)  # Config processing date
    
    # Meta information (NOT used for data loading!)
    tenant = relationship("Tenant", back_populates="bot", lazy='noload')  # N:1 relationship
    bot_command_list = relationship("BotCommand", back_populates="bot", lazy='noload')  # 1:N relationship
    
    __table_args__ = (
        Index('idx_bot_telegram_id', 'telegram_bot_id'),
        Index('idx_bot_tenant_id', 'tenant_id'),
        Index('idx_bot_bot_token', 'bot_token'),
    )

class BotCommand(Base):
    """Bot commands for registration and clearing in Telegram API"""
    __tablename__ = 'bot_command'
    
    id = Column(Integer, primary_key=True)
    bot_id = Column(Integer, ForeignKey('bot.id'), nullable=False)                 # FK to bot
    action_type = Column(String(20), nullable=False)                               # 'register' or 'clear'
    command = Column(String(50), nullable=True)                                    # Command name (NULL for clear)
    description = Column(Text, nullable=True)                                      # Command description (NULL for clear)
    scope = Column(String(50), nullable=False, default='default')                  # default, all_private_chats, all_group_chats, chat, chat_member
    chat_id = Column(BigInteger, nullable=True)                                       # Telegram chat_id (64-bit, for scope: chat, chat_member)
    user_id = Column(BigInteger, nullable=True)                                       # Telegram user_id (64-bit, for scope: chat_member)
    processed_at = Column(TIMESTAMP, nullable=False, default=dtf_now_local)        # Config processing date
    
    # Meta information (NOT used for data loading!)
    bot = relationship("Bot", back_populates="bot_command_list", lazy='noload')  # N:1 relationship
    
    __table_args__ = (
        Index('idx_bot_command_bot_id', 'bot_id'),
        Index('idx_bot_command_action_type', 'action_type'),
        Index('idx_bot_command_scope', 'scope'),
        Index('idx_bot_command_bot_action', 'bot_id', 'action_type'),
    )

# =============================================================================
# SCENARIOS
# =============================================================================

class Scenario(Base):
    __tablename__ = 'scenario'
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey('tenant.id'), nullable=False)  # FK to tenant
    scenario_name = Column(String(100), nullable=False)           # admin_panel, user_onboarding
    description = Column(Text, nullable=True)                     # Scenario description
    schedule = Column(String(100), nullable=True)                  # Cron expression for scheduled scenarios (e.g., "0 9 * * *")
    last_scheduled_run = Column(TIMESTAMP, nullable=True)         # Last scheduled run time
    processed_at = Column(TIMESTAMP, nullable=False, default=dtf_now_local)  # Config processing date
    
    # Meta information (NOT used for data loading!)
    scenario_trigger_list = relationship("ScenarioTrigger", back_populates="scenario", lazy='noload')  # 1:N relationship
    scenario_step_list = relationship("ScenarioStep", back_populates="scenario", lazy='noload')  # 1:N relationship
    
    __table_args__ = (
        Index('idx_scenario_tenant_id', 'tenant_id'),
        Index('idx_scenario_name', 'tenant_id', 'scenario_name', unique=True),
        Index('idx_scenario_schedule', 'schedule'),  # Index for fast scheduled scenario search
    )

class ScenarioTrigger(Base):
    __tablename__ = 'scenario_trigger'
    id = Column(Integer, primary_key=True)
    scenario_id = Column(Integer, ForeignKey('scenario.id'), nullable=False)    # FK to scenario
    condition_expression = Column(Text, nullable=False)                          # Unified trigger condition
    processed_at = Column(TIMESTAMP, nullable=False, default=dtf_now_local)     # Config processing date
    
    # Meta information (NOT used for data loading!)
    scenario = relationship("Scenario", back_populates="scenario_trigger_list", lazy='noload')  # N:1 relationship
    
    __table_args__ = (
        Index('idx_scenario_trigger_scenario_id', 'scenario_id'),
    )

class ScenarioStep(Base):
    __tablename__ = 'scenario_step'
    id = Column(Integer, primary_key=True)
    scenario_id = Column(Integer, ForeignKey('scenario.id'), nullable=False)   # FK to scenario
    step_order = Column(Integer, nullable=False)                               # Step execution order
    action_name = Column(String(100), nullable=False)                          # Action name (API endpoint)
    params = Column(Text, nullable=True)                                       # JSON with parameters
    is_async = Column(Boolean, nullable=False, default=False)                 # Async action execution flag
    action_id = Column(String(100), nullable=True)                             # Unique ID for tracking async actions
    processed_at = Column(TIMESTAMP, nullable=False, default=dtf_now_local)    # Config processing date
    
    # Meta information (NOT used for data loading!)
    scenario = relationship("Scenario", back_populates="scenario_step_list", lazy='noload')  # N:1 relationship
    scenario_step_transition_list = relationship("ScenarioStepTransition", back_populates="scenario_step", lazy='noload')  # 1:N relationship
    
    __table_args__ = (
        Index('idx_step_scenario_order', 'scenario_id', 'step_order'),
        Index('idx_step_action', 'action_name'),
    )

class ScenarioStepTransition(Base):
    __tablename__ = 'scenario_step_transition'
    id = Column(Integer, primary_key=True)
    step_id = Column(Integer, ForeignKey('scenario_step.id'), nullable=False)  # FK to scenario_step
    action_result = Column(String(50), nullable=False)                         # success, error, timeout, not_found, etc.
    transition_action = Column(String(50), nullable=False)                     # continue, abort, jump_to_scenario, move_steps, jump_to_step
    transition_value = Column(Text, nullable=True)                             # JSON with additional transition data
    processed_at = Column(TIMESTAMP, nullable=False, default=dtf_now_local)    # Config processing date
    
    # Meta information (NOT used for data loading!)
    scenario_step = relationship("ScenarioStep", back_populates="scenario_step_transition_list", lazy='noload')  # N:1 relationship
    
    __table_args__ = (
        Index('idx_scenario_step_transition_step_id', 'step_id'),
        Index('idx_scenario_step_transition_result', 'action_result'),
    )

# =============================================================================
# UNIQUE ID GENERATOR
# =============================================================================

class IdSequence(Base):
    """Table for generating unique IDs via autoincrement (deterministic generation by seed hash)"""
    __tablename__ = 'id_sequence'
    
    id = Column(Integer, primary_key=True, autoincrement=True)  # Unique ID we return
    hash = Column(String(32), nullable=False, unique=True)  # MD5 hash of seed (for finding existing records)
    seed = Column(Text, nullable=True)  # Seed for debugging
    processed_at = Column(TIMESTAMP, nullable=False, default=dtf_now_local)  # System field
    
    __table_args__ = (
        Index('idx_id_sequence_hash', 'hash'),  # Index for fast hash search
        {'sqlite_autoincrement': True},  # Enable AUTOINCREMENT for SQLite
    )

# =============================================================================
# INVOICES
# =============================================================================

class Invoice(Base):
    """Invoice model for Telegram stars payment"""
    __tablename__ = 'invoice'
    
    id = Column(Integer, primary_key=True, autoincrement=True)  # This is invoice_payload
    tenant_id = Column(Integer, ForeignKey('tenant.id'), nullable=False)  # FK to tenant
    user_id = Column(BigInteger, nullable=True)  # Telegram user_id (64-bit, NULL if created as link)
    title = Column(String(200), nullable=False)  # Product/service name
    description = Column(Text, nullable=True)  # Description (optional)
    amount = Column(Integer, nullable=False)  # Number of stars (integer)
    link = Column(Text, nullable=True)  # Invoice link (if created as link)
    is_cancelled = Column(Boolean, default=False)  # For internal logic (mark as inactive)
    telegram_payment_charge_id = Column(String(100), nullable=True)  # Payment ID in Telegram (after payment)
    paid_at = Column(TIMESTAMP, nullable=True)  # Payment time (NULL if not paid)
    created_at = Column(TIMESTAMP, nullable=False, default=dtf_now_local)  # Creation time
    updated_at = Column(TIMESTAMP, nullable=False, default=dtf_now_local, onupdate=dtf_now_local)  # Update time
    
    # Meta information (NOT used for data loading!)
    tenant = relationship("Tenant", lazy='noload')  # N:1 relationship
    
    __table_args__ = (
        Index('idx_invoice_tenant_id', 'tenant_id'),
        Index('idx_invoice_user_id', 'tenant_id', 'user_id'),
        Index('idx_invoice_tenant_paid_at', 'tenant_id', 'paid_at'),
        Index('idx_invoice_tenant_cancelled', 'tenant_id', 'is_cancelled'),
    )

# =============================================================================
# VECTOR STORAGE (RAG) - PostgreSQL with pgvector only
# =============================================================================

class VectorStorage(Base):
    """
    Vector storage for RAG (Retrieval-Augmented Generation)
    PostgreSQL with pgvector extension only
    
    Table is created only for PostgreSQL via migration.
    For SQLite table is not created (check in migration).
    """
    __tablename__ = 'vector_storage'
    
    tenant_id = Column(Integer, ForeignKey('tenant.id'), nullable=False)  # FK to tenant
    document_id = Column(String(255), nullable=False)  # Unique document ID
    chunk_index = Column(Integer, nullable=False)  # Chunk order in document (0, 1, 2...)
    document_type = Column(String(100), nullable=False)  # Type: 'knowledge', 'prompt', 'chat_history', 'other'
    role = Column(String(20), nullable=False, default='user')  # Role for OpenAI messages: 'system', 'user', 'assistant' (default 'user')
    # Metadata (JSONB for filtering: chat_id, username, etc.)
    chunk_metadata = Column(JSONB, nullable=True)  # Chunk metadata (chat_id, username, etc.) - used for filtering, not exposed in AI context
    
    # Content
    content = Column(Text, nullable=False)  # Chunk text
    
    # Vector representation (PostgreSQL with pgvector only)
    # Dimension 1024 for optimal speed/quality balance
    # Supports HNSW index (limit: <= 2000)
    # Compatible with most models (OpenAI, Cohere, etc.)
    # nullable=True allows saving text without embedding (useful for history)
    embedding = Column(Vector(1024), nullable=True)  # Text vector representation (optional, can be NULL for history without search)
    embedding_model = Column(String(100), nullable=True)  # Model used for embedding generation (e.g., "text-embedding-3-small", "text-embedding-3-large")
    
    created_at = Column(TIMESTAMP, nullable=False, default=dtf_now_local)  # Real creation date (for correct history sorting)
    processed_at = Column(TIMESTAMP, nullable=False, default=dtf_now_local)  # Processing/update date
    
    # Meta information (NOT used for data loading!)
    tenant = relationship("Tenant", lazy='noload')  # N:1 relationship
    
    __table_args__ = (
        PrimaryKeyConstraint('tenant_id', 'document_id', 'chunk_index'),
        Index('idx_vector_storage_tenant', 'tenant_id'),
        Index('idx_vector_storage_document', 'tenant_id', 'document_id'),
        Index('idx_vector_storage_type', 'tenant_id', 'document_type'),
        # HNSW index for vector search (dimension 1024 < 2000, so supported)
        Index(
            'idx_vector_storage_embedding_hnsw',
            'embedding',
            postgresql_using='hnsw',
            postgresql_ops={'embedding': 'vector_cosine_ops'},
            postgresql_with={'m': 16, 'ef_construction': 64}
        ),
    )