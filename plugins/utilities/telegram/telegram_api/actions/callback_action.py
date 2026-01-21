"""
CallbackAction - actions with callback query via Telegram API
"""

from typing import Any, Dict


class CallbackAction:
    """Actions with callback query via Telegram API"""
    
    def __init__(self, api_client, **kwargs):
        self.api_client = api_client
        self.logger = kwargs['logger']
    
    async def answer_callback_query(self, bot_token: str, bot_id: int, data: dict) -> Dict[str, Any]:
        """
        Answer callback query (popup notification or simple notification)
        """
        try:
            # Extract parameters from flat dictionary
            callback_query_id = data.get('callback_query_id')
            
            if not callback_query_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "callback_query_id is required"
                    }
                }
            
            # Build payload
            payload = {
                'callback_query_id': callback_query_id
            }
            
            # Add optional parameters
            if 'text' in data and data['text']:
                text = data['text']
                # Limit text length to 200 characters (Telegram limitation)
                if len(text) > 200:
                    text = text[:197] + "..."
                payload['text'] = text
            
            if 'show_alert' in data:
                payload['show_alert'] = bool(data['show_alert'])
            
            if 'cache_time' in data and data['cache_time'] is not None:
                cache_time = int(data['cache_time'])
                if cache_time < 0:
                    self.logger.warning(f"cache_time is negative ({cache_time}), ignoring parameter")
                elif cache_time > 3600:
                    self.logger.warning(f"cache_time exceeds maximum ({cache_time}), setting to 3600")
                    payload['cache_time'] = 3600
                else:
                    payload['cache_time'] = cache_time
            
            # Execute request
            result = await self.api_client.make_request_with_limit(bot_token, "answerCallbackQuery", payload, bot_id)
            
            # Process result
            if result.get('result') == 'success':
                return {"result": "success"}
            else:
                error_data = result.get('error', {})
                if isinstance(error_data, dict):
                    error_obj = error_data
                else:
                    error_obj = {
                        "code": "API_ERROR",
                        "message": str(error_data) if error_data else "Unknown error"
                    }
                return {
                    "result": result.get('result', 'error'),
                    "error": error_obj
                }
            
        except Exception as e:
            self.logger.error(f"Error answering callback query: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }

