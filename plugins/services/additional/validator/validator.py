"""
Validator - сервис для валидации условий в сценариях
"""

from typing import Any, Dict


class Validator:
    """
    Сервис для валидации условий в сценариях
    - Принимает условие и данные события
    - Использует condition_parser для оценки
    - Возвращает результат валидации
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.condition_parser = kwargs['condition_parser']
        
        # Регистрируем себя в ActionHub
        self.action_hub = kwargs['action_hub']
        self.action_hub.register('validator', self)
    
    # === Actions для ActionHub ===
    
    async def validate(self, data: dict) -> Dict[str, Any]:
        """
        Валидация условия с возвратом результата
        """
        try:
            # Валидация выполняется централизованно в ActionRegistry
            condition = data.get('condition')
            
            # Удаляем данные условия из контекста для передачи в condition_parser
            context_data = data.copy()
            context_data.pop('condition', None)
            
            # Используем condition_parser для оценки условия
            result = await self.condition_parser.check_match(condition, context_data)
            
            if result is True:
                return {"result": "success"}
            elif result is False:
                return {"result": "failed"}
            else:
                # Если condition_parser вернул что-то неожиданное
                self.logger.error(f"Неожиданный результат оценки условия: {result} (тип: {type(result)})")
                return {
                    "result": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": f"Неожиданный результат оценки: {result}"
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Ошибка валидации условия: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
