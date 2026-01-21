"""
Bot Info Action - action for getting bot information via Telegram API
"""

from typing import Any, Dict


class BotInfoAction:
    """Action for getting bot information"""
    
    def __init__(self, api_client, **kwargs):
        self.api_client = api_client
        self.logger = kwargs['logger']
    
    def _format_token_for_logs(self, bot_token: str) -> str:
        """
        Format token for logs: first 15 characters
        Token format: {bot_id}:{secret}, where bot_id can be extracted from the beginning
        """
        if not bot_token:
            return "[Bot-Token: unknown]"
        
        # Take first 15 characters (usually bot_id + part of secret)
        return f"[Bot-Token: {bot_token[:15]}...]"
    
    async def get_bot_info(self, bot_token: str) -> Dict[str, Any]:
        """
        Get bot information via Telegram API getMe method
        """
        try:
            # Execute getMe request to Telegram API
            result = await self.api_client.make_request(
                bot_token=bot_token,
                method="getMe",
                payload={}
            )
            
            # Check result
            if result.get('result') == 'success':
                bot_data = result.get('response_data', {})
                
                return {
                    "result": "success",
                    "response_data": {
                        "telegram_bot_id": bot_data.get('id'),
                        "username": bot_data.get('username'),
                        "first_name": bot_data.get('first_name'),
                        "is_bot": bot_data.get('is_bot'),
                        "can_join_groups": bot_data.get('can_join_groups'),
                        "can_read_all_group_messages": bot_data.get('can_read_all_group_messages'),
                        "supports_inline_queries": bot_data.get('supports_inline_queries')
                    }
                }
            else:
                error_description = result.get('error', 'Unknown error')
                token_info = self._format_token_for_logs(bot_token)
                self.logger.warning(f"{token_info} Error getting bot information: {error_description}")
                
                return {
                    "result": "error",
                    "error": f"Telegram API error: {error_description}"
                }
                
        except Exception as e:
            token_info = self._format_token_for_logs(bot_token)
            self.logger.error(f"{token_info} Error getting bot information: {e}")
            return {
                "result": "error",
                "error": f"Request error: {str(e)}"
            }
