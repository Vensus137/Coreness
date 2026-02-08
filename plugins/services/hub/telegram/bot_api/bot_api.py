"""
Telegram Bot API - service for executing bot actions via Telegram API
Handles messages, keyboards, callbacks, and other bot operations
"""

from typing import Any, Dict

from .modules.message_handler import MessageHandler
from .modules.keyboard_builder import KeyboardBuilder


class TelegramBotAPI:
    """
    Service for Telegram Bot API operations
    - Sends messages to users
    - Deletes messages
    - Builds keyboards from templates
    - Answers callback queries
    - (Future: group management, etc.)
    
    Note: Gets bot tokens through telegram_bot_manager.get_bot_info action
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.action_hub = kwargs['action_hub']
        self.telegram_api = kwargs['telegram_api']
        self.settings = kwargs['settings_manager'].get_plugin_settings('telegram_bot_api')
        
        # Initialize modules
        self.message_handler = MessageHandler(
            telegram_api=self.telegram_api,
            action_hub=self.action_hub,
            logger=self.logger
        )
        
        self.keyboard_builder = KeyboardBuilder(
            default_buttons_per_row=self.settings.get('default_buttons_per_row', 2),
            logger=self.logger
        )
        
        # Register in ActionHub
        kwargs['action_hub'].register('telegram_bot_api', self)
    
    async def run(self):
        """Service startup"""
        self.logger.info("Started")
    
    # === Actions ===
    
    async def send_message(self, data: dict) -> Dict[str, Any]:
        """Send message to user(s)"""
        try:
            return await self.message_handler.send_message(data)
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def delete_message(self, data: dict) -> Dict[str, Any]:
        """Delete message"""
        try:
            return await self.message_handler.delete_message(data)
        except Exception as e:
            self.logger.error(f"Error deleting message: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def build_keyboard(self, data: dict) -> Dict[str, Any]:
        """Build keyboard from array of items using templates"""
        try:
            return self.keyboard_builder.build(data)
        except Exception as e:
            self.logger.error(f"Error building keyboard: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def answer_callback_query(self, data: dict) -> Dict[str, Any]:
        """Answer callback query (popup/toast notification)"""
        try:
            return await self.message_handler.answer_callback_query(data)
        except Exception as e:
            self.logger.error(f"Error answering callback query: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
