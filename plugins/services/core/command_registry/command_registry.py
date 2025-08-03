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