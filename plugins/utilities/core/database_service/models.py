from sqlalchemy import (Boolean, Column, DateTime, Index, Integer, String,
                        Text, func)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Используем SQL-функцию для получения локального времени сервера
def dtf_now_local():
    return func.now()

class Action(Base):
    __tablename__ = 'actions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    action_type = Column(String, nullable=False)
    action_data = Column(Text, nullable=False)
    prev_data = Column(Text, nullable=True)  # JSON с информацией с предыдущих действий по цепочке
    response_data = Column(Text, nullable=True)  # JSON с результатом выполнения действия
    status = Column(String, default='pending')
    prev_action_id = Column(Integer, nullable=True)
    unlock_status = Column(Text, nullable=True)  # Ожидаемый статус предыдущего действия для разблокировки
    chain_drop_status = Column(Text, nullable=True)  # Статусы для дропа цепочки (JSON массив, например ["failed"])
    is_unlocker_checked = Column(Boolean, default=False)  # Флаг проверки анлокером
    created_at = Column(DateTime, nullable=False, default=dtf_now_local)
    processed_at = Column(DateTime, nullable=True)
    __table_args__ = (
        Index('idx_actions_status_created', 'status', 'created_at'),
        Index('idx_actions_prev_action_id', 'prev_action_id'),
        Index('idx_actions_prev_action_status', 'prev_action_id', 'status'),
        Index('idx_actions_created_at', 'created_at'),
        Index('idx_actions_unlocker_check', 'is_unlocker_checked', 'status', 'created_at'),
    )

class User(Base):
    __tablename__ = 'users'
    user_id = Column(Integer, primary_key=True)  # Telegram user_id
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    is_bot = Column(Boolean, default=False)
    created_at = Column(DateTime, nullable=False, default=dtf_now_local)
    updated_at = Column(DateTime, nullable=False, default=dtf_now_local, onupdate=dtf_now_local)
    last_activity = Column(DateTime, nullable=True)
    __table_args__ = (
        Index('idx_users_username', 'username'),
    )

class UserState(Base):
    __tablename__ = 'user_states'
    user_id = Column(Integer, primary_key=True)  # Telegram user_id
    state_type = Column(String, nullable=False)
    state_data = Column(Text, nullable=True)  # JSON с данными состояния
    updated_at = Column(DateTime, nullable=False, default=dtf_now_local, onupdate=dtf_now_local)
    expired_at = Column(DateTime, nullable=False, default=dtf_now_local)

class Request(Base):
    __tablename__ = 'requests'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)  # Telegram user_id
    request_name = Column(String, nullable=True)  # Классификатор запроса (опционально)
    request_text = Column(Text, nullable=True)  # Текст запроса пользователя (может быть None)
    attachments = Column(Text, nullable=True)  # JSON с вложениями (файлы, фото, видео и т.д.)
    request_info = Column(Text, nullable=True)  # JSON с дополнительной информацией по запросу
    created_at = Column(DateTime, nullable=False, default=dtf_now_local)
    updated_at = Column(DateTime, nullable=False, default=dtf_now_local, onupdate=dtf_now_local)
    __table_args__ = (
        Index('idx_requests_created_at', 'created_at'),
        Index('idx_requests_name_created', 'request_name', 'created_at'),
        Index('idx_requests_user_id', 'user_id'),
    )

class InviteLink(Base):
    __tablename__ = 'invite_links'
    id = Column(Integer, primary_key=True, autoincrement=True)
    invite_link = Column(String, nullable=False)  # https://t.me/+37WZrw-pREI2NWMy
    chat_id = Column(Integer, nullable=False)  # ID группы, где создана ссылка
    created_at = Column(DateTime, nullable=False, default=dtf_now_local)
    __table_args__ = (
        Index('idx_invite_links_link', 'invite_link'),
        Index('idx_invite_links_chat', 'chat_id'),
    )

class Cache(Base):
    __tablename__ = 'cache'
    id = Column(Integer, primary_key=True, autoincrement=True)
    hash_key = Column(String, nullable=False, unique=True)  # уникальный хеш
    hash_metadata = Column(Text, nullable=True)             # JSON с метаданными
    hash_file_path = Column(String, nullable=True)          # путь к файлу (может быть NULL)
    created_at = Column(DateTime, nullable=False, default=dtf_now_local)
    __table_args__ = (
        Index('idx_cache_hash_key', 'hash_key', unique=True),
        Index('idx_cache_created_at', 'created_at'),
    )