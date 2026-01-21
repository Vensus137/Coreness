"""
CommandAction - actions with commands via Telegram API
"""

from typing import Any, Dict, List


class CommandAction:
    """Actions with commands via Telegram API"""
    
    def __init__(self, api_client, **kwargs):
        self.api_client = api_client
        self.logger = kwargs['logger']
    
    async def sync_bot_commands(self, bot_token: str, bot_id: int, command_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Sync bot commands: apply commands in Telegram"""
        try:
            if not command_list:
                # If no commands, delete all existing commands
                result = await self.api_client.make_request(bot_token, "deleteMyCommands", {})
                if result["result"] != "success":
                    return {"result": "error", "error": f"[Bot-{bot_id}] Failed to delete commands: {result.get('error', 'Unknown error')}"}
                
                return {"result": "success"}
            
            # First, forcibly clear ALL commands for all scopes (as in old code)
            # Clear errors are ignored (not critical)
            await self._clear_all_commands(bot_token, bot_id)
            
            # Split commands by action_type
            register_command = [cmd for cmd in command_list if cmd.get('action_type') == 'register']
            clear_command = [cmd for cmd in command_list if cmd.get('action_type') == 'clear']
            
            failed_commands = set()
            
            # Additionally delete commands (clear) if any
            if clear_command:
                for clear_cmd in clear_command:
                    scope_name = clear_cmd.get('scope', 'default')
                    scope = self._get_scope_object(scope_name, clear_cmd)
                    payload = {'scope': scope} if scope else {}
                    
                    result = await self.api_client.make_request(bot_token, "deleteMyCommands", payload)
                    if result["result"] != "success":
                        # On clear error, add all commands of this scope to failed list
                        for cmd in register_command:
                            if cmd.get('scope', 'default') == scope_name:
                                failed_commands.add(cmd["command"])
            
            # Then register commands (register)
            if register_command:
                # Group commands by scope
                grouped_command = self._group_command_by_scope(register_command)
                
                # Apply commands for each scope
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
                    
                    # Add scope only if it's not None
                    if scope is not None:
                        payload['scope'] = scope
                    
                    result = await self.api_client.make_request(bot_token, "setMyCommands", payload)
                    
                    if result["result"] != "success":
                        # Add all commands of this scope to failed list
                        for cmd in scope_command:
                            failed_commands.add(cmd["command"])
            
            # If there were errors - log command list and return error
            if failed_commands:
                commands_str = ', '.join(sorted(failed_commands))
                self.logger.warning(f"[Bot-{bot_id}] Failed to update commands: {commands_str}")
                return {"result": "error", "error": f"[Bot-{bot_id}] Errors during command sync"}
            
            return {"result": "success"}
            
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Error syncing commands: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def _clear_all_commands(self, bot_token: str, bot_id: int):
        """
        Forced clearing of all commands for all scopes (as in old code)
        """
        try:
            # Clear commands for all main scopes (as in old code)
            scopes_to_clear = [
                None,  # default scope
                {'type': 'all_private_chats'},
                {'type': 'all_group_chats'}
            ]
            
            for scope in scopes_to_clear:
                payload = {'scope': scope} if scope else {}
                await self.api_client.make_request(bot_token, "deleteMyCommands", payload)
                
                # Clear errors are not critical, don't log individually
                # They will be collected in a general warning if there are registration problems
            
        except Exception as e:
            self.logger.warning(f"[Bot-{bot_id}] Error clearing all commands: {e}")
            # Continue even if clearing failed
    
    def _group_command_by_scope(self, command_list: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group commands by scope for registration"""
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
        """Create scope object for Telegram API"""
        if scope_type == 'default':
            return None  # Default scope doesn't require object
        
        elif scope_type == 'chat':
            chat_id = scope_info.get('chat_id')
            if chat_id:
                return {"type": "chat", "chat_id": chat_id}
        
        elif scope_type == 'chat_member':
            chat_id = scope_info.get('chat_id')
            user_id = scope_info.get('user_id')
            if chat_id and user_id:
                return {"type": "chat_member", "chat_id": chat_id, "user_id": user_id}
        
        # If scope is not supported, return default
        return None
