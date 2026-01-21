"""
Actions for working with messages through Bot Hub
"""

from typing import Any, Dict


class MessageActions:
    """Actions for working with messages"""
    
    def __init__(self, bot_info_manager, telegram_api, logger, settings=None):
        self.bot_info_manager = bot_info_manager
        self.telegram_api = telegram_api
        self.logger = logger
        self.settings = settings or {}
        # Save default value from settings on initialization
        self.default_buttons_per_row = self.settings.get('default_buttons_per_row', 2)
    
    async def send_message(self, data: dict) -> Dict[str, Any]:
        """Send message to bot"""
        try:
            bot_id = data.get('bot_id')
            
            # Get bot information
            bot_result = await self.bot_info_manager.get_bot_info(bot_id)
            if bot_result.get('result') != 'success':
                error_msg = bot_result.get('error', 'Unknown error')
                if isinstance(error_msg, dict):
                    error_msg = error_msg.get('message', 'Unknown error')
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Failed to get bot information for {bot_id}: {error_msg}"
                    }
                }
            
            bot_info = bot_result.get('response_data', {})
            if not bot_info.get('bot_token'):
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Bot token for {bot_id} not found"
                    }
                }
            
            # Send message through telegram_api (pass original data)
            result = await self.telegram_api.send_message(
                bot_info['bot_token'], 
                bot_id, 
                data
            )
            
            return result
            
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
        """Delete bot message"""
        try:
            bot_id = data.get('bot_id')
            
            # Get bot information
            bot_result = await self.bot_info_manager.get_bot_info(bot_id)
            if bot_result.get('result') != 'success':
                error_msg = bot_result.get('error', 'Unknown error')
                if isinstance(error_msg, dict):
                    error_msg = error_msg.get('message', 'Unknown error')
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Failed to get bot information for {bot_id}: {error_msg}"
                    }
                }
            
            bot_info = bot_result.get('response_data', {})
            if not bot_info.get('bot_token'):
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Bot token for {bot_id} not found"
                    }
                }
            
            # Delete message through telegram_api (pass original data)
            result = await self.telegram_api.delete_message(
                bot_info['bot_token'], 
                bot_id, 
                data
            )
            
            return result
            
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
        """
        Build keyboard from array of IDs using templates
        
        Parameters:
        - items: array of IDs (required)
        - keyboard_type: keyboard type - "inline" or "reply" (required)
        - text_template: button text template with placeholder $value$ (required)
        - callback_template: callback_data template for inline keyboard with placeholder $value$ (required for inline)
        - buttons_per_row: number of buttons per row (optional, default 1)
        
        Note: Uses $value$ syntax instead of {value} to avoid conflict
        with placeholder system that processes {value} as placeholder.
        """
        try:
            items = data.get('items')
            keyboard_type = data.get('keyboard_type')
            text_template = data.get('text_template')
            callback_template = data.get('callback_template')
            buttons_per_row = data.get('buttons_per_row', self.default_buttons_per_row)
            
            # Additional business validation: callback_template required for inline
            if keyboard_type == 'inline' and not callback_template:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "callback_template required for inline keyboard"
                    }
                }
            
            # Build keyboard
            keyboard = []
            current_row = []
            
            for item_id in items:
                # Replace $value$ in templates with current ID (use $value$ to avoid conflict with placeholders)
                text = str(text_template).replace('$value$', str(item_id))
                
                if keyboard_type == 'inline':
                    callback = str(callback_template).replace('$value$', str(item_id))
                    button = {text: callback}
                else:  # reply
                    button = text
                
                current_row.append(button)
                
                # If row is full, add it to keyboard
                if len(current_row) >= buttons_per_row:
                    keyboard.append(current_row)
                    current_row = []
            
            # Add remaining buttons
            if current_row:
                keyboard.append(current_row)
            
            return {
                "result": "success",
                "response_data": {
                    "keyboard": keyboard,
                    "keyboard_type": keyboard_type,
                    "rows_count": len(keyboard),
                    "buttons_count": len(items)
                }
            }
            
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
        """Answer callback query (popup notification or simple notification)"""
        try:
            bot_id = data.get('bot_id')
            
            # Get bot information
            bot_result = await self.bot_info_manager.get_bot_info(bot_id)
            if bot_result.get('result') != 'success':
                error_msg = bot_result.get('error', 'Unknown error')
                if isinstance(error_msg, dict):
                    error_msg = error_msg.get('message', 'Unknown error')
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Failed to get bot information for {bot_id}: {error_msg}"
                    }
                }
            
            bot_info = bot_result.get('response_data', {})
            if not bot_info.get('bot_token'):
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Bot token for {bot_id} not found"
                    }
                }
            
            # Answer callback query through telegram_api (pass original data)
            result = await self.telegram_api.answer_callback_query(
                bot_info['bot_token'], 
                bot_id, 
                data
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error answering callback query: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }