"""
Message Handler - handles message operations (send, delete, callback answers)
"""

from typing import Any, Dict, Optional


class MessageHandler:
    """Handles message operations through telegram_api"""
    
    def __init__(self, telegram_api, action_hub, logger):
        self.telegram_api = telegram_api
        self.action_hub = action_hub
        self.logger = logger
    
    async def send_message(self, data: dict) -> Dict[str, Any]:
        """
        Send message via bot
        Gets bot token through telegram_bot_manager.get_telegram_bot_info_by_id
        """
        bot_id = data.get('bot_id')
        if not bot_id:
            return self._error("VALIDATION_ERROR", "bot_id is required")
        
        # Get bot token
        bot_token = await self._get_bot_token(bot_id)
        if not bot_token:
            return self._error("NOT_FOUND", f"Bot {bot_id} token not found")
        
        # Send through telegram_api
        return await self.telegram_api.send_message(bot_token, bot_id, data)
    
    async def delete_message(self, data: dict) -> Dict[str, Any]:
        """Delete message"""
        bot_id = data.get('bot_id')
        if not bot_id:
            return self._error("VALIDATION_ERROR", "bot_id is required")
        
        bot_token = await self._get_bot_token(bot_id)
        if not bot_token:
            return self._error("NOT_FOUND", f"Bot {bot_id} token not found")
        
        return await self.telegram_api.delete_message(bot_token, bot_id, data)
    
    async def answer_callback_query(self, data: dict) -> Dict[str, Any]:
        """Answer callback query"""
        bot_id = data.get('bot_id')
        if not bot_id:
            return self._error("VALIDATION_ERROR", "bot_id is required")
        
        bot_token = await self._get_bot_token(bot_id)
        if not bot_token:
            return self._error("NOT_FOUND", f"Bot {bot_id} token not found")
        
        return await self.telegram_api.answer_callback_query(bot_token, bot_id, data)

    async def restrict_chat_member(self, data: dict) -> Dict[str, Any]:
        """Restrict a user in a supergroup (permission groups: messages, attachments, other, management)."""
        bot_id = data.get('bot_id')
        if not bot_id:
            return self._error("VALIDATION_ERROR", "bot_id is required")
        bot_token = await self._get_bot_token(bot_id)
        if not bot_token:
            return self._error("NOT_FOUND", f"Bot {bot_id} token not found")
        return await self.telegram_api.restrict_chat_member(bot_token, bot_id, data)

    async def _get_bot_token(self, bot_id: int) -> Optional[str]:
        """Get bot token through telegram_bot_manager"""
        try:
            result = await self.action_hub.execute_action(
                'get_telegram_bot_info_by_id',
                {'bot_id': bot_id}
            )
            
            if result.get('result') == 'success':
                return result['response_data'].get('bot_token')
            
            return None
            
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Error getting bot token: {e}")
            return None
    
    def _error(self, code: str, message: str) -> Dict[str, Any]:
        """Helper to create error response"""
        return {
            "result": "error",
            "error": {"code": code, "message": message}
        }
