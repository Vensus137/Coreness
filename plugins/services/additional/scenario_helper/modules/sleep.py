"""
Модуль для задержек выполнения (sleep)
"""

import asyncio
from typing import Any, Dict


class SleepManager:
    """
    Класс для задержек выполнения
    """
    
    def __init__(self, logger):
        self.logger = logger
    
    async def sleep(self, data: dict) -> Dict[str, Any]:
        """
        Задержка выполнения на указанное количество секунд
        """
        try:
            if not data:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Нет данных для задержки"
                    }
                }
            
            seconds = data.get('seconds')
            
            # Валидация параметров
            if seconds is None:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Параметр seconds обязателен"
                    }
                }
            
            if not isinstance(seconds, (int, float)):
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Параметр seconds должен быть числом"
                    }
                }
            
            if seconds < 0:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Параметр seconds не может быть отрицательным"
                    }
                }
            
            # Выполняем задержку
            await asyncio.sleep(float(seconds))
            
            return {"result": "success"}
            
        except Exception as e:
            self.logger.error(f"Ошибка выполнения задержки: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
