"""
BotRepository - repository for working with bots and commands
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import delete, insert, select

from ..models import Bot, BotCommand
from .base import BaseRepository


class BotRepository(BaseRepository):
    """Repository for working with bots and commands"""
    
    async def get_all_bots(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get all bots
        """
        try:
            with self._get_session() as session:
                stmt = select(Bot)
                result = session.execute(stmt).scalars().all()
                
                return await self._to_dict_list(result)
                
        except Exception as e:
            self.logger.error(f"Error getting all bots: {e}")
            return None
    
    async def get_bot_by_id(self, bot_id: int) -> Optional[Dict[str, Any]]:
        """
        Get bot configuration by ID
        """
        try:
            with self._get_session() as session:
                stmt = select(Bot).where(Bot.id == bot_id)
                result = session.execute(stmt).scalar_one_or_none()
                
                return await self._to_dict(result)
                
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Error getting bot: {e}")
            return None
    
    async def get_bot_by_telegram_id(self, telegram_bot_id: int) -> Optional[Dict[str, Any]]:
        """
        Get bot by telegram_bot_id
        """
        try:
            with self._get_session() as session:
                stmt = select(Bot).where(Bot.telegram_bot_id == telegram_bot_id)
                result = session.execute(stmt).scalar_one_or_none()
                
                return await self._to_dict(result)
                
        except Exception as e:
            self.logger.error(f"[TelegramBot-{telegram_bot_id}] Error getting bot: {e}")
            return None
    
    async def get_bot_by_tenant_id(self, tenant_id: int) -> Optional[Dict[str, Any]]:
        """
        Get bot by tenant_id
        """
        try:
            with self._get_session() as session:
                stmt = select(Bot).where(Bot.tenant_id == tenant_id)
                result = session.execute(stmt).scalar_one_or_none()
                
                return await self._to_dict(result)
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Error getting bot for tenant: {e}")
            return None
    
    async def get_commands_by_bot(self, bot_id: int) -> Optional[List[Dict[str, Any]]]:
        """
        Get bot commands
        """
        try:
            with self._get_session() as session:
                stmt = select(BotCommand).where(BotCommand.bot_id == bot_id)
                result = session.execute(stmt).scalars().all()
                
                return await self._to_dict_list(result)
                
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Error getting bot commands: {e}")
            return None
    
    async def delete_commands_by_bot(self, bot_id: int) -> Optional[bool]:
        """
        Delete all bot commands
        """
        try:
            with self._get_session() as session:
                stmt = delete(BotCommand).where(BotCommand.bot_id == bot_id)
                session.execute(stmt)
                session.commit()
                
                return True
                
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Error deleting bot commands: {e}")
            return None
    
    async def save_commands_by_bot(self, bot_id: int, command_list: List[Dict[str, Any]]) -> Optional[int]:
        """
        Save bot commands
        """
        try:
            with self._get_session() as session:
                saved_count = 0
                
                for cmd_data in command_list:
                    # Prepare data for insertion via data_preparer
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
                    
                    # Insert command
                    stmt = insert(BotCommand).values(**prepared_fields)
                    session.execute(stmt)
                    saved_count += 1
                
                session.commit()
                return saved_count
                
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Error saving bot commands: {e}")
            return None
    
    async def create_bot(self, bot_data: Dict[str, Any]) -> Optional[int]:
        """
        Create bot
        """
        try:
            with self._get_session() as session:
                # Prepare data for insertion via data_preparer
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
            self.logger.error(f"Error creating bot: {e}")
            return None
    
    async def update_bot(self, bot_id: int, bot_data: Dict[str, Any]) -> Optional[bool]:
        """
        Update bot
        """
        try:
            with self._get_session() as session:
                from sqlalchemy import update
                
                # Prepare data for update via data_preparer
                prepared_fields = await self.data_preparer.prepare_for_update(
                    model=Bot,
                    fields=bot_data,
                    json_fields=[]
                )
                
                if not prepared_fields:
                    self.logger.warning(f"[Bot-{bot_id}] No fields to update bot")
                    return False
                
                stmt = update(Bot).where(Bot.id == bot_id).values(**prepared_fields)
                result = session.execute(stmt)
                session.commit()
                
                if result.rowcount > 0:
                    return True
                else:
                    self.logger.warning(f"Bot {bot_id} not found for update")
                    return False
                
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Error updating bot: {e}")
            return None