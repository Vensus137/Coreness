"""
Bot Info Action - действие для получения информации о боте через Telegram API
"""

from typing import Any, Dict


class BotInfoAction:
    """Действие для получения информации о боте"""
    
    def __init__(self, api_client, **kwargs):
        self.api_client = api_client
        self.logger = kwargs['logger']
    
    def _format_token_for_logs(self, bot_token: str) -> str:
        """
        Форматирование токена для логов: первые 15 символов
        Формат токена: {bot_id}:{secret}, где bot_id можно извлечь из начала
        """
        if not bot_token:
            return "[Bot-Token: unknown]"
        
        # Берем первые 15 символов (обычно это bot_id + часть секрета)
        return f"[Bot-Token: {bot_token[:15]}...]"
    
    async def get_bot_info(self, bot_token: str) -> Dict[str, Any]:
        """
        Получение информации о боте через Telegram API метод getMe
        """
        try:
            # Выполняем запрос getMe к Telegram API
            result = await self.api_client.make_request(
                bot_token=bot_token,
                method="getMe",
                payload={}
            )
            
            # Проверяем результат
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
                error_description = result.get('error', 'Неизвестная ошибка')
                token_info = self._format_token_for_logs(bot_token)
                self.logger.warning(f"{token_info} Ошибка получения информации о боте: {error_description}")
                
                return {
                    "result": "error",
                    "error": f"Telegram API ошибка: {error_description}"
                }
                
        except Exception as e:
            token_info = self._format_token_for_logs(bot_token)
            self.logger.error(f"{token_info} Ошибка получения информации о боте: {e}")
            return {
                "result": "error",
                "error": f"Ошибка запроса: {str(e)}"
            }
