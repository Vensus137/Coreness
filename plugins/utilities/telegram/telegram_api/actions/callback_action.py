"""
CallbackAction - действия с callback query через Telegram API
"""

from typing import Any, Dict


class CallbackAction:
    """Действия с callback query через Telegram API"""
    
    def __init__(self, api_client, **kwargs):
        self.api_client = api_client
        self.logger = kwargs['logger']
    
    async def answer_callback_query(self, bot_token: str, bot_id: int, data: dict) -> Dict[str, Any]:
        """
        Ответ на callback query (всплывающее уведомление или простое уведомление)
        
        Параметры:
        - callback_query_id: ID callback query (обязательно)
        - text: текст уведомления (опционально, до 200 символов)
        - show_alert: показать всплывающее окно (опционально, по умолчанию false)
        - cache_time: время кэширования ответа в секундах (опционально)
        """
        try:
            # Извлекаем параметры из плоского словаря
            callback_query_id = data.get('callback_query_id')
            
            if not callback_query_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "callback_query_id обязателен"
                    }
                }
            
            # Строим payload
            payload = {
                'callback_query_id': callback_query_id
            }
            
            # Добавляем опциональные параметры
            if 'text' in data and data['text']:
                text = data['text']
                # Ограничиваем длину текста до 200 символов (ограничение Telegram)
                if len(text) > 200:
                    text = text[:197] + "..."
                payload['text'] = text
            
            if 'show_alert' in data:
                payload['show_alert'] = bool(data['show_alert'])
            
            if 'cache_time' in data and data['cache_time'] is not None:
                cache_time = int(data['cache_time'])
                if cache_time < 0:
                    self.logger.warning(f"cache_time отрицательный ({cache_time}), игнорируем параметр")
                elif cache_time > 3600:
                    self.logger.warning(f"cache_time превышает максимум ({cache_time}), устанавливаем 3600")
                    payload['cache_time'] = 3600
                else:
                    payload['cache_time'] = cache_time
            
            # Выполняем запрос
            result = await self.api_client.make_request_with_limit(bot_token, "answerCallbackQuery", payload, bot_id)
            
            # Обрабатываем результат
            if result.get('result') == 'success':
                return {"result": "success"}
            else:
                error_data = result.get('error', {})
                if isinstance(error_data, dict):
                    error_obj = error_data
                else:
                    error_obj = {
                        "code": "API_ERROR",
                        "message": str(error_data) if error_data else "Неизвестная ошибка"
                    }
                return {
                    "result": result.get('result', 'error'),
                    "error": error_obj
                }
            
        except Exception as e:
            self.logger.error(f"Ошибка ответа на callback query: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }

