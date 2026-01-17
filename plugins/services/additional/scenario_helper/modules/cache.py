"""
Модуль для работы с временными данными кэша сценария
"""

from typing import Any, Dict


class CacheManager:
    """
    Класс для работы с временными данными кэша сценария
    """
    
    def __init__(self, logger):
        self.logger = logger
    
    async def set_cache(self, data: dict) -> Dict[str, Any]:
        """
        Установка временных данных в кэш сценария.
        
        Данные берутся из ключа 'cache' в params, что позволяет явно указать,
        какие именно данные нужно кэшировать, избегая попадания всего контекста сценария.
        
        Все переданные параметры возвращаются в response_data в предопределенном словаре `_cache`,
        что предотвращает случайную перезапись системных полей (bot_id, tenant_id и др.).
        
        Данные автоматически очищаются после завершения выполнения сценария.
        """
        try:
            # Берем данные из ключа 'cache' в params
            # Это позволяет явно указать, что именно нужно кэшировать
            cache_data = data.get('cache', {})
            
            # Если cache_data не словарь - ошибка
            if not isinstance(cache_data, dict):
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Параметр 'cache' должен быть объектом (словарем)"
                    }
                }
            
            # Возвращаем данные напрямую, они автоматически попадут в _cache[action_name] в scenario_engine
            return {
                "result": "success",
                "response_data": cache_data
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка установки кэша: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
