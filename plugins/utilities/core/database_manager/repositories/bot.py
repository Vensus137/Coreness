"""
BotRepository - репозиторий для работы с ботами и командами
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import delete, insert, select

from ..models import Bot, BotCommand
from .base import BaseRepository


class BotRepository(BaseRepository):
    """Репозиторий для работы с ботами и командами"""
    
    async def get_all_bots(self) -> Optional[List[Dict[str, Any]]]:
        """
        Получить всех ботов
        """
        try:
            with self._get_session() as session:
                stmt = select(Bot)
                result = session.execute(stmt).scalars().all()
                
                return await self._to_dict_list(result)
                
        except Exception as e:
            self.logger.error(f"Ошибка получения всех ботов: {e}")
            return None
    
    async def get_bot_by_id(self, bot_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить конфигурацию бота по ID
        """
        try:
            with self._get_session() as session:
                stmt = select(Bot).where(Bot.id == bot_id)
                result = session.execute(stmt).scalar_one_or_none()
                
                return await self._to_dict(result)
                
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Ошибка получения бота: {e}")
            return None
    
    async def get_bot_by_telegram_id(self, telegram_bot_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить бота по telegram_bot_id
        """
        try:
            with self._get_session() as session:
                stmt = select(Bot).where(Bot.telegram_bot_id == telegram_bot_id)
                result = session.execute(stmt).scalar_one_or_none()
                
                return await self._to_dict(result)
                
        except Exception as e:
            self.logger.error(f"[TelegramBot-{telegram_bot_id}] Ошибка получения бота: {e}")
            return None
    
    async def get_bot_by_tenant_id(self, tenant_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить бота по tenant_id
        """
        try:
            with self._get_session() as session:
                stmt = select(Bot).where(Bot.tenant_id == tenant_id)
                result = session.execute(stmt).scalar_one_or_none()
                
                return await self._to_dict(result)
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Ошибка получения бота для тенанта: {e}")
            return None
    
    async def get_commands_by_bot(self, bot_id: int) -> Optional[List[Dict[str, Any]]]:
        """
        Получить команды бота
        """
        try:
            with self._get_session() as session:
                stmt = select(BotCommand).where(BotCommand.bot_id == bot_id)
                result = session.execute(stmt).scalars().all()
                
                return await self._to_dict_list(result)
                
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Ошибка получения команд бота: {e}")
            return None
    
    async def delete_commands_by_bot(self, bot_id: int) -> Optional[bool]:
        """
        Удалить все команды бота
        """
        try:
            with self._get_session() as session:
                stmt = delete(BotCommand).where(BotCommand.bot_id == bot_id)
                session.execute(stmt)
                session.commit()
                
                return True
                
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Ошибка удаления команд бота: {e}")
            return None
    
    async def save_commands_by_bot(self, bot_id: int, command_list: List[Dict[str, Any]]) -> Optional[int]:
        """
        Сохранить команды бота
        """
        try:
            with self._get_session() as session:
                saved_count = 0
                
                for cmd_data in command_list:
                    # Подготавливаем данные для вставки через data_preparer
                    prepared_fields = await self.data_preparer.prepare_for_insert(
                        model=BotCommand,
                        fields={
                            'bot_id': bot_id,
                            'action_type': cmd_data.get('action_type', 'register'),
                            'command': cmd_data.get('command'),
                            'description': cmd_data.get('description'),
                            'scope': cmd_data.get('scope', 'default'),
                            'chat_id': cmd_data.get('chat_id'),
                            'user_id': cmd_data.get('user_id')
                        },
                        json_fields=[]
                    )
                    
                    # Вставляем команду
                    stmt = insert(BotCommand).values(**prepared_fields)
                    session.execute(stmt)
                    saved_count += 1
                
                session.commit()
                return saved_count
                
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Ошибка сохранения команд бота: {e}")
            return None
    
    async def create_bot(self, bot_data: Dict[str, Any]) -> Optional[int]:
        """
        Создать бота
        """
        try:
            with self._get_session() as session:
                # Подготавливаем данные для вставки через data_preparer
                prepared_fields = await self.data_preparer.prepare_for_insert(
                    model=Bot,
                    fields={
                        'tenant_id': bot_data.get('tenant_id'),
                        'bot_token': bot_data.get('bot_token'),
                        'telegram_bot_id': bot_data.get('telegram_bot_id'),
                        'username': bot_data.get('username'),
                        'first_name': bot_data.get('first_name'),
                        'is_active': bot_data.get('is_active', True)
                    },
                    json_fields=[]
                )
                
                stmt = insert(Bot).values(**prepared_fields)
                result = session.execute(stmt)
                session.commit()
                
                bot_id = result.inserted_primary_key[0]
                return bot_id
                
        except Exception as e:
            self.logger.error(f"Ошибка создания бота: {e}")
            return None
    
    async def update_bot(self, bot_id: int, bot_data: Dict[str, Any]) -> Optional[bool]:
        """
        Обновить бота
        """
        try:
            with self._get_session() as session:
                from sqlalchemy import update
                
                # Подготавливаем данные для обновления через data_preparer
                prepared_fields = await self.data_preparer.prepare_for_update(
                    model=Bot,
                    fields=bot_data,
                    json_fields=[]
                )
                
                if not prepared_fields:
                    self.logger.warning(f"[Bot-{bot_id}] Нет полей для обновления бота")
                    return False
                
                stmt = update(Bot).where(Bot.id == bot_id).values(**prepared_fields)
                result = session.execute(stmt)
                session.commit()
                
                if result.rowcount > 0:
                    return True
                else:
                    self.logger.warning(f"Бот {bot_id} не найден для обновления")
                    return False
                
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Ошибка обновления бота: {e}")
            return None