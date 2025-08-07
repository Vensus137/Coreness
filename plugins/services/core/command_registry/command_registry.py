from typing import Dict, List


class CommandRegistryService:
    """
    Сервис для регистрации команд бота в Telegram Bot API
    Выполняется однократно при запуске приложения
    """
    def __init__(self, **kwargs):
        self.plugins_manager = kwargs['plugins_manager']
        self.logger = kwargs['logger']
        self.bot_initializer = kwargs['bot_initializer']
        self.bot = self.bot_initializer.get_bot()
        self.settings_manager = kwargs['settings_manager']

    def _get_commands(self) -> List[dict]:
        """Получить список команд из bot.yaml"""
        bot_config = self.settings_manager.get_bot_config()
        return bot_config.get('commands', [])

    @staticmethod
    def _group_commands_by_scope(commands: List[dict]) -> Dict[str, List[dict]]:
        """Группировка команд по scope для регистрации"""
        grouped = {}
        for cmd in commands:
            scope = cmd.get('scope', 'default')
            key = scope
            if scope == 'chat':
                key += f"_{cmd.get('chat_id')}"
            elif scope == 'chat_member':
                key += f"_{cmd.get('chat_id')}_{cmd.get('user_id')}"
            grouped.setdefault(key, []).append(cmd)
        return grouped

    async def _register_commands(self):
        """Регистрация команд в Telegram Bot API"""
        from aiogram.types import (BotCommand, BotCommandScopeAllGroupChats,
                                   BotCommandScopeAllPrivateChats,
                                   BotCommandScopeChat,
                                   BotCommandScopeChatMember,
                                   BotCommandScopeDefault)
        
        commands = self._get_commands()
        if not commands:
            self.logger.info("Команды для регистрации не найдены в конфигурации")
            return
            
        # Сначала очищаем все команды для всех scope
        await self._clear_all_commands()
            
        grouped = self._group_commands_by_scope(commands)
        for key, cmds in grouped.items():
            scope_type = cmds[0].get('scope', 'default')
            if scope_type == 'all_private_chats':
                scope = BotCommandScopeAllPrivateChats()
            elif scope_type == 'all_group_chats':
                scope = BotCommandScopeAllGroupChats()
            elif scope_type == 'chat':
                scope = BotCommandScopeChat(chat_id=cmds[0]['chat_id'])
            elif scope_type == 'chat_member':
                scope = BotCommandScopeChatMember(chat_id=cmds[0]['chat_id'], user_id=cmds[0]['user_id'])
            else:
                scope = BotCommandScopeDefault()
            bot_commands = [BotCommand(command=cmd["command"], description=cmd["description"]) for cmd in cmds]
            await self.bot.set_my_commands(bot_commands, scope=scope)
            self.logger.info(f"Зарегистрировано {len(bot_commands)} команд в Telegram Bot API (scope: {scope_type})")

    async def _clear_all_commands(self):
        """Очищает все команды для всех scope"""
        from aiogram.types import (BotCommandScopeAllGroupChats,
                                   BotCommandScopeAllPrivateChats,
                                   BotCommandScopeDefault,
                                   BotCommandScopeChat,
                                   BotCommandScopeChatMember)
        
        try:
            # Очищаем команды для всех основных scope
            scopes_to_clear = [
                BotCommandScopeDefault(),
                BotCommandScopeAllPrivateChats(),
                BotCommandScopeAllGroupChats()
            ]
            
            for scope in scopes_to_clear:
                await self.bot.delete_my_commands(scope=scope)
            
            self.logger.info("Очищены команды для всех основных scope")
            
            # Очищаем команды для конкретных чатов и пользователей
            await self._clear_specific_commands()
            
        except Exception as e:
            self.logger.warning(f"Ошибка при очистке команд: {e}")
            # Продолжаем работу даже если очистка не удалась

    async def _clear_specific_commands(self):
        """Очищает команды для конкретных чатов и пользователей из commands_clear"""
        from aiogram.types import BotCommandScopeChat, BotCommandScopeChatMember
        
        try:
            bot_config = self.settings_manager.get_bot_config()
            commands_clear = bot_config.get('commands_clear', {})
            
            # Очищаем команды для конкретных чатов
            chats_to_clear = commands_clear.get('chats', [])
            for chat_info in chats_to_clear:
                chat_id = chat_info.get('chat_id')
                if chat_id:
                    scope = BotCommandScopeChat(chat_id=chat_id)
                    await self.bot.delete_my_commands(scope=scope)
                    self.logger.info(f"Удалены команды для чата: {chat_id}")
            
            # Очищаем команды для конкретных пользователей в чатах
            chat_members_to_clear = commands_clear.get('chat_members', [])
            for member_info in chat_members_to_clear:
                chat_id = member_info.get('chat_id')
                user_id = member_info.get('user_id')
                if chat_id and user_id:
                    scope = BotCommandScopeChatMember(chat_id=chat_id, user_id=user_id)
                    await self.bot.delete_my_commands(scope=scope)
                    self.logger.info(f"Удалены команды для пользователя {user_id} в чате {chat_id}")
            
            if chats_to_clear or chat_members_to_clear:
                self.logger.info(f"Удалены команды для {len(chats_to_clear)} чатов и {len(chat_members_to_clear)} пользователей")
            
        except Exception as e:
            self.logger.warning(f"Ошибка при очистке конкретных команд: {e}")
            # Продолжаем работу даже если очистка не удалась

    async def run(self):
        """
        Однократный запуск регистрации команд при старте приложения
        """
        self.logger.info("▶️ запуск регистрации команд...")
        try:
            await self._register_commands()
            self.logger.info("CommandRegistryService: регистрация команд завершена успешно")
        except Exception as e:
            self.logger.error(f"CommandRegistryService: ошибка при регистрации команд: {e}")
            raise 