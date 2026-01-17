"""
APIClient - HTTP клиент для Telegram Bot API
"""

import json
from typing import Any, Dict

import aiohttp


class APIClient:
    """HTTP клиент для Telegram Bot API"""
    
    def __init__(self, session: aiohttp.ClientSession, rate_limiter, **kwargs):
        self.logger = kwargs['logger']
        self.session = session
        self.base_url = "https://api.telegram.org/bot"
        self.rate_limiter = rate_limiter
    
    async def make_request(self, bot_token: str, method: str, payload: dict) -> Dict[str, Any]:
        """Выполнение запроса к Telegram API без rate limiting (обычные запросы)"""
        return await self._make_http_request(bot_token, method, payload)
    
    async def make_request_with_limit(self, bot_token: str, method: str, payload: dict, bot_id: int = 0, chat_id: int = 0) -> Dict[str, Any]:
        """Выполнение запроса к Telegram API с rate limiting (для спам-действий)"""
        # Если bot_id не передан, извлекаем его из токена
        if not bot_id:
            try:
                bot_id = int(bot_token.split(':')[0])
            except (ValueError, IndexError):
                self.logger.warning("Не удалось извлечь bot_id из токена, выполняем без rate limiting")
                return await self._make_http_request(bot_token, method, payload)
        
        # Используем rate limiter для выполнения запроса
        return await self.rate_limiter.execute_with_rate_limit(
            self._make_http_request,
            token=bot_token,
            method=method,
            payload=payload,
            bot_id=bot_id,
            chat_id=chat_id
        )
    
    async def _make_http_request(self, token: str, method: str, payload: dict) -> Dict[str, Any]:
        """Выполнение HTTP запроса к Telegram API (внутренний метод)"""
        try:
            # Формируем URL
            url = f"{self.base_url}{token}/{method}"
            
            # Очищаем payload от None значений
            clean_payload = {k: v for k, v in payload.items() if v is not None}
            
            # Выполняем HTTP запрос
            async with self.session.post(
                url,
                json=clean_payload,
                headers={'Content-Type': 'application/json'}
            ) as response:
                
                # Получаем ответ
                response_data = await response.json()
                
                # Обрабатываем ответ
                return self._process_response(response.status, response_data)
                
        except aiohttp.ClientTimeout:
            self.logger.warning(f"Таймаут запроса к API: {method}")
            return {
                "result": "timeout",
                "error": {
                    "code": "TIMEOUT",
                    "message": "Request timeout"
                }
            }
            
        except aiohttp.ClientError as e:
            self.logger.error(f"Ошибка сети при запросе к API: {method} - {e}")
            return {
                "result": "timeout",
                "error": {
                    "code": "TIMEOUT",
                    "message": f"Network error: {e}"
                }
            }
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Ошибка парсинга JSON ответа: {method} - {e}")
            return {
                "result": "error",
                "error": {
                    "code": "PARSE_ERROR",
                    "message": f"Invalid JSON response: {e}"
                }
            }
            
        except Exception as e:
            self.logger.error(f"Неожиданная ошибка при запросе к API: {method} - {e}")
            return {
                "result": "error",
                "error": {
                    "code": "API_ERROR",
                    "message": f"Unexpected error: {e}"
                }
            }
    
    def _process_response(self, status_code: int, response_data: dict) -> Dict[str, Any]:
        """Обработка ответа от Telegram API"""
        
        # Успешный ответ (200)
        if status_code == 200:
            if response_data.get('ok', False):
                return {
                    "result": "success",
                    "response_data": response_data.get('result', {})
                }
            else:
                # Telegram API вернул ошибку
                error_code = response_data.get('error_code', 0)
                description = response_data.get('description', 'Unknown error')
                
                # Определяем тип ошибки
                if error_code == 401:
                    return {
                        "result": "not_found",
                        "error": {
                            "code": "NOT_FOUND",
                            "message": f"HTTP {error_code}: {description}"
                        }
                    }
                elif error_code == 429:
                    return {
                        "result": "timeout",
                        "error": {
                            "code": "TIMEOUT",
                            "message": f"HTTP {error_code}: {description}"
                        }
                    }
                else:
                    return {
                        "result": "error",
                        "error": {
                            "code": "API_ERROR",
                            "message": f"HTTP {error_code}: {description}"
                        }
                    }
        
        # HTTP ошибки
        elif status_code == 401:
            return {
                "result": "not_found",
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Unauthorized"
                }
            }
        elif status_code == 429:
            return {
                "result": "timeout",
                "error": {
                    "code": "TIMEOUT",
                    "message": "Too Many Requests"
                }
            }
        elif status_code >= 400:
            # Для HTTP ошибок пытаемся извлечь описание из response_data
            description = response_data.get('description', f'HTTP {status_code}')
            return {
                "result": "error",
                "error": {
                    "code": "API_ERROR",
                    "message": f"HTTP {status_code}: {description}"
                }
            }
        else:
            return {
                "result": "error",
                "error": {
                    "code": "API_ERROR",
                    "message": f"Unexpected status code: {status_code}"
                }
            }
