"""
CommandAction - действия с командами через Telegram API
"""

from typing import Any, Dict, List


class CommandAction:
    """Действия с командами через Telegram API"""
    
    def __init__(self, api_client, **kwargs):
        self.api_client = api_client
        self.logger = kwargs['logger']
    
    async def sync_bot_commands(self, bot_token: str, bot_id: int, command_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Синхронизация команд бота: применение команд в Telegram"""
        try:
            if not command_list:
                # Если команд нет, удаляем все существующие команды
                result = await self.api_client.make_request(bot_token, "deleteMyCommands", {})
                if result["result"] != "success":
                    return {"result": "error", "error": f"[Bot-{bot_id}] Не удалось удалить команды: {result.get('error', 'Unknown error')}"}
                
                return {"result": "success"}
            
            # Сначала принудительно очищаем ВСЕ команды для всех scope (как в старом коде)
            # Ошибки очистки игнорируем (это не критично)
            await self._clear_all_commands(bot_token, bot_id)
            
            # Разделяем команды по action_type
            register_command = [cmd for cmd in command_list if cmd.get('action_type') == 'register']
            clear_command = [cmd for cmd in command_list if cmd.get('action_type') == 'clear']
            
            failed_commands = set()
            
            # Дополнительно удаляем команды (clear) если есть
            if clear_command:
                for clear_cmd in clear_command:
                    scope_name = clear_cmd.get('scope', 'default')
                    scope = self._get_scope_object(scope_name, clear_cmd)
                    payload = {'scope': scope} if scope else {}
                    
                    result = await self.api_client.make_request(bot_token, "deleteMyCommands", payload)
                    if result["result"] != "success":
                        # При ошибке очистки добавляем все команды этого scope в список неудачных
                        for cmd in register_command:
                            if cmd.get('scope', 'default') == scope_name:
                                failed_commands.add(cmd["command"])
            
            # Затем регистрируем команды (register)
            if register_command:
                # Группируем команды по scope
                grouped_command = self._group_command_by_scope(register_command)
                
                # Применяем команды для каждого scope
                for _scope_key, scope_command in grouped_command.items():
                    scope_type = scope_command[0].get('scope', 'default')
                    scope = self._get_scope_object(scope_type, scope_command[0])
                    
                    bot_command_list = [
                        {"command": cmd["command"], "description": cmd["description"]}
                        for cmd in scope_command
                    ]
                    
                    payload = {
                        'commands': bot_command_list
                    }
                    
                    # Добавляем scope только если он не None
                    if scope is not None:
                        payload['scope'] = scope
                    
                    result = await self.api_client.make_request(bot_token, "setMyCommands", payload)
                    
                    if result["result"] != "success":
                        # Добавляем все команды этого scope в список неудачных
                        for cmd in scope_command:
                            failed_commands.add(cmd["command"])
            
            # Если были ошибки - логируем список команд и возвращаем ошибку
            if failed_commands:
                commands_str = ', '.join(sorted(failed_commands))
                self.logger.warning(f"[Bot-{bot_id}] Не удалось обновить команды: {commands_str}")
                return {"result": "error", "error": f"[Bot-{bot_id}] Ошибки при синхронизации команд"}
            
            return {"result": "success"}
            
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Ошибка синхронизации команд: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def _clear_all_commands(self, bot_token: str, bot_id: int):
        """
        Принудительная очистка всех команд для всех scope (как в старом коде)
        """
        try:
            # Очищаем команды для всех основных scope (как в старом коде)
            scopes_to_clear = [
                None,  # default scope
                {'type': 'all_private_chats'},
                {'type': 'all_group_chats'}
            ]
            
            for scope in scopes_to_clear:
                payload = {'scope': scope} if scope else {}
                await self.api_client.make_request(bot_token, "deleteMyCommands", payload)
                
                # Ошибки очистки не критичны, не логируем индивидуально
                # Они будут собраны в общий warning если будут проблемы с регистрацией
            
        except Exception as e:
            self.logger.warning(f"[Bot-{bot_id}] Ошибка при очистке всех команд: {e}")
            # Продолжаем работу даже если очистка не удалась
    
    def _group_command_by_scope(self, command_list: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Группировка команд по scope для регистрации"""
        grouped = {}
        for cmd in command_list:
            scope = cmd.get('scope', 'default')
            key = scope
            
            if scope == 'chat':
                key += f"_{cmd.get('chat_id')}"
            elif scope == 'chat_member':
                key += f"_{cmd.get('chat_id')}_{cmd.get('user_id')}"
            
            grouped.setdefault(key, []).append(cmd)
        
        return grouped
    
    def _get_scope_object(self, scope_type: str, scope_info: Dict[str, Any]):
        """Создание объекта scope для Telegram API"""
        if scope_type == 'default':
            return None  # Default scope не требует объекта
        
        elif scope_type == 'chat':
            chat_id = scope_info.get('chat_id')
            if chat_id:
                return {"type": "chat", "chat_id": chat_id}
        
        elif scope_type == 'chat_member':
            chat_id = scope_info.get('chat_id')
            user_id = scope_info.get('user_id')
            if chat_id and user_id:
                return {"type": "chat_member", "chat_id": chat_id, "user_id": user_id}
        
        # Если scope не поддерживается, возвращаем default
        return None
